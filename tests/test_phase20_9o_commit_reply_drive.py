from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9o_commit_reply_drive_from_ap_flow/v1"


def _u(value: str) -> str:
    return value.encode("unicode_escape").decode("ascii")


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


def _commit_trace(result) -> dict:
    event = _event_with_action(result, "commit_reply")
    row = _competition_row(event, "commit_reply")
    trace = row.get("commit_reply_drive_from_ap_flow")
    assert isinstance(trace, dict)
    return trace


def test_phase20_9o_commit_reply_drive_is_from_ap_flow_not_fixed_constant(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9o feedback prompt",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9o feedback reply", reward_mag=1.0),
        session_id="phase20-9o-drive",
        db_path=tmp_path / "phase20_9o.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    event = _event_with_action(result, "commit_reply")
    row = _competition_row(event, "commit_reply")
    trace = row["commit_reply_drive_from_ap_flow"]

    assert trace["formula_id"] == FORMULA_ID
    assert trace["draft_has_visible_text"] is True
    assert trace["draft_completeness"] > 0.0
    assert trace["reply_pressure"] > 0.0
    assert trace["drive"] == row["drive_before_learning_loop_carryover"]
    assert row["drive"] != 0.95
    assert trace["drive"] != 0.95
    assert event.feelings["commit_readiness"] == trace["drive"]
    assert event.feelings["commit_reply_drive_context"]["formula_id"] == FORMULA_ID
    assert trace["writes_answer_directly"] is False
    assert trace["creates_reply_candidate"] is False


def test_phase20_9o_structural_generalization_raises_commit_source_support(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9o_structural.sqlite"
    session_id = "phase20-9o-structural"

    run_phase20_7_turn(
        user_text="\u6ca1\u9519,\u4f60\u597d\u806a\u660e",
        teacher_feedback=TeacherFeedback(feedback_text="\u8c22\u8c22", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    result = run_phase20_7_turn(
        user_text="\u4f60\u597d\u806a\u660e",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    trace = _commit_trace(result)

    assert _u(result.reply_text) == _u("\u8c22\u8c22")
    assert trace["source_kind"] == "structural_bccstar"
    assert trace["source_support"] >= 0.55
    assert trace["conflict_penalty"] == 0.0
    assert trace["writes_answer_directly"] is False


def test_phase20_9o_repeated_same_commit_accumulates_fatigue(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9o_fatigue.sqlite"
    session_id = "phase20-9o-fatigue"

    first = run_phase20_7_turn(
        user_text="phase20.9o fatigue lesson",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9o answer", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    second = run_phase20_7_turn(
        user_text="phase20.9o fatigue lesson",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9o answer", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    third = run_phase20_7_turn(
        user_text="phase20.9o fatigue lesson",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9o answer", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    first_trace = _commit_trace(first)
    second_trace = _commit_trace(second)
    third_trace = _commit_trace(third)

    assert second_trace["recent_commit_count"] > first_trace["recent_commit_count"]
    assert third_trace["repeated_reply_count"] > first_trace["repeated_reply_count"]
    assert third_trace["repetition_fatigue"] > first_trace["repetition_fatigue"]
    assert third_trace["drive"] < 1.0
    assert third_trace["creates_reply_candidate"] is False
