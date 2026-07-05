from __future__ import annotations

from pathlib import Path

import sqlite3

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.experience_log import from_json


FORMULA_ID = "apv3_phase20_9w_draftgrid_successor_from_experience_flow/v1"
READBACK_FORMULA_ID = "apv3_phase20_9q_draftgrid_readback_self_flow/v1"
LEARNING_ACK_TEXT = "\u55ef,\u8bb0\u4e0b\u4e86\u3002"


def _events_with_action(result, action_type: str):
    return [event for event in result.tick_trace if event.selected_action.get("action_type") == action_type]


def _phase20_9w_successor_trace(result) -> dict:
    for event in _events_with_action(result, "continue_writing"):
        trace = event.selected_action.get("experience_flow_successor", {})
        if isinstance(trace, dict) and trace.get("formula_id") == FORMULA_ID and trace.get("successor_text"):
            return trace
    raise AssertionError("phase20.9w experience-flow successor trace not found")


def _seed_long_then_first_fragment(db_path: Path, session_id: str) -> None:
    long_prompt = "phase20.9w long source prompt"
    long_reply = "alpha first fragment beta successor fragment"
    first_prompt = "phase20.9w first fragment prompt"
    first_reply = "alpha first fragment"

    run_phase20_7_turn(
        user_text=long_prompt,
        teacher_feedback=TeacherFeedback(feedback_text=long_reply, reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    long_result = run_phase20_7_turn(
        user_text=long_prompt,
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert long_result.committed is True
    assert long_result.reply_text == long_reply
    assert _events_with_action(long_result, "continue_writing")

    run_phase20_7_turn(
        user_text=first_prompt,
        teacher_feedback=TeacherFeedback(feedback_text=first_reply, reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )


def test_phase20_9w_draftgrid_readback_successor_extends_from_experience_flow(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9w_successor.sqlite"
    session_id = "phase20-9w-successor"
    _seed_long_then_first_fragment(db_path, session_id)

    result = run_phase20_7_turn(
        user_text="phase20.9w first fragment prompt",
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    trace = _phase20_9w_successor_trace(result)

    assert result.committed is True
    assert result.reply_text == "alpha first fragment beta successor fragment"
    assert "\n" not in result.reply_text
    assert trace["candidate_kind"] == "short_structure_flow_next"
    assert trace["source_flow_kind"] == "draft_grid_readback"
    assert trace["target_flow_kind"] == "draft_grid_readback"
    assert trace["source_intent"] == "exact_b0"
    assert trace["target_intent"] == "exact_b0"
    assert trace["successor_text"] == " beta successor fragment"
    assert trace["edge_ids"]
    assert trace["occurrence_ids"]
    assert trace["writes_answer_directly"] is False
    assert trace["creates_reply_candidate"] is False


def test_phase20_9w_uses_real_readback_ssp_edges_without_internal_text_leak(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9w_no_internal_leak.sqlite"
    session_id = "phase20-9w-no-leak"
    _seed_long_then_first_fragment(db_path, session_id)

    result = run_phase20_7_turn(
        user_text="phase20.9w first fragment prompt",
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    trace = _phase20_9w_successor_trace(result)

    forbidden_fragments = ("utterance:", "readback:", LEARNING_ACK_TEXT)
    assert not any(fragment in result.reply_text for fragment in forbidden_fragments)
    assert not any(fragment in trace["successor_text"] for fragment in forbidden_fragments)
    assert len(result.reply_text) <= len("alpha first fragment beta successor fragment")

    with sqlite3.connect(db_path) as conn:
        edge_id = trace["edge_ids"][0]
        row = conn.execute(
            """
            SELECT src.position_json, dst.position_json
            FROM phase20_7_structure_edges edge
            JOIN phase20_7_occurrences src ON src.occurrence_id=edge.src_occurrence_id
            JOIN phase20_7_occurrences dst ON dst.occurrence_id=edge.dst_occurrence_id
            WHERE edge.edge_id=? AND edge.edge_type='short_structure_next'
            """,
            (edge_id,),
        ).fetchone()
        assert row is not None
        source_position = from_json(row[0])
        target_position = from_json(row[1])
        assert source_position["formula_id"] == READBACK_FORMULA_ID
        assert target_position["formula_id"] == READBACK_FORMULA_ID
        assert source_position["source_kind"] == "draft_grid_readback"
        assert target_position["source_kind"] == "draft_grid_readback"
        assert source_position["source_intent"] == target_position["source_intent"] == "exact_b0"
