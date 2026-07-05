from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_8p_expression_paradigm_slots/v1"


def _event_with_action(result, action_type: str):
    for event in result.tick_trace:
        if event.selected_action.get("action_type") == action_type:
            return event
    raise AssertionError(f"event not found: {action_type}")


def _commit_event_id(result) -> str:
    event = _event_with_action(result, "commit_reply")
    assert event.experience_event_ids_written
    return event.experience_event_ids_written[0]


def _expression_alignment_payloads(db_path: Path) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT payload_json
            FROM phase20_7_experience_events
            WHERE event_kind='experience_alignment'
            ORDER BY created_at_ms ASC
            """
        ).fetchall()
    out: list[dict] = []
    for (payload_json,) in rows:
        payload = json.loads(str(payload_json))
        if payload.get("expression_role"):
            out.append(payload)
    return out


def test_phase20_8p_targeted_expression_feedback_stores_paradigm_slot(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8p.sqlite"
    first = run_phase20_7_turn(
        user_text="phase20p slot seed",
        session_id="phase20-8p-slot",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    target_event_id = _commit_event_id(first)
    run_phase20_7_turn(
        user_text="",
        teacher_feedback=TeacherFeedback(
            feedback_text="teach me this part",
            reward_mag=1.0,
            target_event_id=target_event_id,
        ),
        session_id="phase20-8p-slot",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    payloads = _expression_alignment_payloads(db_path)

    assert payloads
    payload = payloads[-1]
    assert payload["expression_role"] == "request_teacher"
    assert payload["expression_paradigm_formula_id"] == FORMULA_ID
    assert payload["expression_paradigm_slot"] in {"low_grasp_pressure_request", "low_grasp_request"}
    assert payload["expression_target_trace"]["formula_id"] == "apv3_phase20_8o_request_expression_from_experience_flow/v1"


def test_phase20_8p_request_expression_prefers_matching_current_paradigm_slot(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8p.sqlite"
    low_seed = run_phase20_7_turn(
        user_text="phase20p low seed",
        session_id="phase20-8p-match",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="",
        teacher_feedback=TeacherFeedback(
            feedback_text="low grasp phrase",
            reward_mag=1.0,
            target_event_id=_commit_event_id(low_seed),
        ),
        session_id="phase20-8p-match",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="phase20p flow seed",
        session_id="phase20-8p-match",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="",
        session_id="phase20-8p-match",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    flow_target = run_phase20_7_turn(
        user_text="phase20p flow target",
        session_id="phase20-8p-match",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    flow_trace = _event_with_action(flow_target, "request_teacher").ssp_active_summary["request_expression_selection"]
    assert flow_trace["current_paradigm_slot"] == "flow_continuation_request"
    run_phase20_7_turn(
        user_text="",
        teacher_feedback=TeacherFeedback(
            feedback_text="flow phrase",
            reward_mag=1.0,
            target_event_id=_commit_event_id(flow_target),
        ),
        session_id="phase20-8p-match",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    result = run_phase20_7_turn(
        user_text="phase20p another flow unknown",
        session_id="phase20-8p-match",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "request_teacher")
    trace = event.ssp_active_summary["request_expression_selection"]

    assert result.reply_text == "flow phrase"
    assert trace["paradigm_formula_id"] == FORMULA_ID
    assert trace["current_paradigm_slot"] == "flow_continuation_request"
    assert trace["selected_paradigm_slot"] == "flow_continuation_request"
    assert trace["paradigm_match"] == 1.0
    assert trace["support_terms"]["expression_paradigm_match"] > 0.0
    assert not event.b_candidates


def test_phase20_8p_maintain_unclosed_uses_unclosed_maintenance_slot(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8p.sqlite"
    run_phase20_7_turn(
        user_text="phase20p maintain slot",
        session_id="phase20-8p-maintain",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    second = run_phase20_7_turn(
        user_text="phase20p maintain slot",
        session_id="phase20-8p-maintain",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="",
        teacher_feedback=TeacherFeedback(
            feedback_text="still working on it",
            reward_mag=1.0,
            target_event_id=_commit_event_id(second),
        ),
        session_id="phase20-8p-maintain",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    result = run_phase20_7_turn(
        user_text="phase20p maintain slot",
        session_id="phase20-8p-maintain",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "maintain_unclosed")
    trace = event.ssp_active_summary["request_expression_selection"]

    assert result.reply_text == "still working on it"
    assert trace["current_paradigm_slot"] == "unclosed_maintenance"
    assert trace["selected_paradigm_slot"] == "unclosed_maintenance"
    assert trace["paradigm_match"] == 1.0
