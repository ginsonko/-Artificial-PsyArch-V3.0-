from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_10a_learning_stage_runtime_progression/v1"


def _event_with_action(result, action_type: str):
    for event in result.tick_trace:
        if event.selected_action.get("action_type") == action_type:
            return event
    raise AssertionError(f"event not found: {action_type}")


def _competition_row(event, action_type: str) -> dict:
    for row in event.action_competition:
        if row.get("action_type") == action_type:
            return dict(row)
    raise AssertionError(f"competition row not found: {action_type}")


def _stage_progression(row: dict) -> dict:
    carryover = row.get("learning_loop_carryover")
    assert isinstance(carryover, dict), "row should expose learning_loop_carryover"
    progression = carryover.get("learning_stage_runtime_progression")
    assert isinstance(progression, dict), "carryover should expose 10a runtime progression"
    return progression


def _make_self_test_sequence(db_path: Path, *, session_id: str):
    run_phase20_7_turn(
        user_text=f"{session_id} cue",
        teacher_feedback=TeacherFeedback(feedback_text=f"{session_id} reply", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text=f"{session_id} cue",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    review = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    self_test = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    return review, self_test


def test_phase20_10a_teacher_feedback_advances_imitation_and_review_actions(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.10a feedback cue",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.10a feedback reply", reward_mag=1.0),
        session_id="phase20-10a-feedback",
        db_path=tmp_path / "phase20_10a_feedback.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "write_cell")
    row = _competition_row(event, "write_cell")
    progression = _stage_progression(row)
    deltas = progression["stage_action_deltas"]

    assert progression["formula_id"] == FORMULA_ID
    assert progression["active"] is True
    assert progression["dominant_runtime_stage"] in {"imitation", "review"}
    assert progression["stage_scores"]["imitation"] > progression["stage_scores"]["teacher_exit"]
    assert deltas["write_cell"] > 0.0
    assert deltas["integrate_feedback"] > 0.0
    assert row["learning_loop_carryover_delta"] > row["learning_loop_carryover"]["write_cell_delta"] - deltas["write_cell"] - 0.0001
    assert progression["uses_existing_ap_flow"] is True
    assert progression["projection_only"] is True
    assert progression["writes_answer_directly"] is False
    assert progression["creates_reply_candidate"] is False


def test_phase20_10a_teacher_off_recall_promotes_self_test_and_generalization(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_10a_teacher_off.sqlite"
    session_id = "phase20-10a-teacher-off"
    run_phase20_7_turn(
        user_text="phase20.10a exact cue",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.10a exact reply", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    result = run_phase20_7_turn(
        user_text="phase20.10a exact cue",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "write_cell")
    row = _competition_row(event, "write_cell")
    progression = _stage_progression(row)
    deltas = progression["stage_action_deltas"]

    assert progression["dominant_runtime_stage"] in {"self_test", "generalization", "teacher_exit", "cold_retest"}
    assert progression["stage_scores"]["self_test"] > progression["stage_scores"]["contact"]
    assert progression["stage_scores"]["generalization"] > progression["stage_scores"]["correction"]
    assert deltas["write_cell"] > 0.0
    assert deltas["commit_reply"] > 0.0
    assert deltas["request_teacher"] < 0.0
    assert progression["writes_answer_directly"] is False


def test_phase20_10a_failed_self_test_returns_to_correction_without_fake_reply(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_10a_selftest_failure.sqlite"
    session_id = "phase20-10a-failure"
    _review, self_test = _make_self_test_sequence(db_path, session_id=session_id)
    occurrence_id = self_test.tick_trace[0].ssp_active_summary["idle_narrative_flow"]["occurrence_id"]

    with sqlite3.connect(db_path) as conn:
        raw = conn.execute(
            "SELECT position_json FROM phase20_7_occurrences WHERE occurrence_id=?",
            (occurrence_id,),
        ).fetchone()[0]
        position = json.loads(str(raw))
        position["idle_self_test"]["self_test_grasp"] = 0.20
        position["idle_self_test"]["match_score"] = 0.15
        position["idle_self_test"]["recalled_text"] = "wrong recall"
        conn.execute(
            "UPDATE phase20_7_occurrences SET position_json=? WHERE occurrence_id=?",
            (json.dumps(position, ensure_ascii=False, sort_keys=True, separators=(",", ":")), occurrence_id),
        )
        conn.commit()

    feedback = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    event = feedback.tick_trace[0]
    idle_row = _competition_row(event, "idle_think")
    progression = _stage_progression(idle_row)
    deltas = progression["stage_action_deltas"]

    assert event.selected_action["idle_learning_review"] is True
    assert progression["self_test_feedback"]["feedback_kind"] == "self_test_failure"
    assert progression["dominant_runtime_stage"] in {"correction", "contact", "review"}
    assert progression["stage_scores"]["correction"] > progression["stage_scores"]["teacher_exit"]
    assert deltas["request_teacher"] > 0.0
    assert deltas["read_draft"] > 0.0
    assert deltas["edit_cell"] > 0.0
    assert feedback.reply_text == ""
    assert progression["writes_answer_directly"] is False
    assert progression["creates_reply_candidate"] is False
