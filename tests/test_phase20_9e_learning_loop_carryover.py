from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9e_learning_loop_carryover/v1"


def _competition_row(event, action_type: str) -> dict:
    for row in event.action_competition:
        if row.get("action_type") == action_type:
            return dict(row)
    raise AssertionError(f"competition row not found: {action_type}")


def _event_with_action(result, action_type: str):
    for event in result.tick_trace:
        if event.selected_action.get("action_type") == action_type:
            return event
    raise AssertionError(f"event not found: {action_type}")


def test_phase20_9e_unknown_observation_carries_scaffold_pressure_into_request(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9e unknown carryover",
        session_id="phase20-9e-unknown",
        db_path=tmp_path / "phase20_9e.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "request_teacher")
    row = _competition_row(event, "request_teacher")
    context = row["teacher_request_drive_context"]
    carryover = context["learning_loop_carryover"]

    assert carryover["formula_id"] == FORMULA_ID
    assert carryover["active"] is True
    assert carryover["dominant_learning_tendency"] == "return_to_scaffold"
    assert carryover["request_teacher_delta"] > 0.0
    assert row["learning_loop_carryover"]["formula_id"] == FORMULA_ID
    assert row["learning_loop_carryover_delta"] > 0.0
    assert carryover["writes_answer_directly"] is False
    assert carryover["creates_reply_candidate"] is False


def test_phase20_9e_feedback_metric_carries_into_ack_writing(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9e feedback cue",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9e feedback reply", reward_mag=1.0),
        session_id="phase20-9e-feedback",
        db_path=tmp_path / "phase20_9e.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "write_cell")
    row = _competition_row(event, "write_cell")
    carryover = row["learning_loop_carryover"]

    assert carryover["formula_id"] == FORMULA_ID
    assert carryover["dominant_learning_tendency"] == "feedback_only"
    assert carryover["write_cell_delta"] > 0.0
    assert row["learning_loop_carryover_delta"] > 0.0
    assert row["drive"] > row["drive_before_learning_loop_carryover"]


def test_phase20_9e_teacher_off_metric_carries_into_later_recall_writing(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9e.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9e exact cue",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9e exact learned reply", reward_mag=1.0),
        session_id="phase20-9e-exact",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    result = run_phase20_7_turn(
        user_text="phase20.9e exact cue",
        session_id="phase20-9e-exact",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    carried = []
    for event in result.tick_trace:
        if event.selected_action.get("action_type") != "write_cell":
            continue
        row = _competition_row(event, "write_cell")
        carryover = row.get("learning_loop_carryover", {})
        if carryover.get("dominant_learning_tendency") == "teacher_off_probe":
            carried.append((event, row, carryover))

    assert carried
    _event, row, carryover = carried[0]
    assert carryover["formula_id"] == FORMULA_ID
    assert carryover["teacher_off_readiness"] > carryover["scaffold_regression_need"]
    assert carryover["write_cell_delta"] > 0.0
    assert row["learning_loop_carryover_delta"] > 0.0
    assert carryover["writes_answer_directly"] is False

