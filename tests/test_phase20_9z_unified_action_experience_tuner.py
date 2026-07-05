from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9z_unified_action_experience_tuner_projection/v1"


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


def _commit_event_id(result) -> str:
    event = _event_with_action(result, "commit_reply")
    assert event.experience_event_ids_written
    return event.experience_event_ids_written[0]


def _teach_maintain_expression(db_path: Path, *, session_id: str, feedback_text: str) -> None:
    run_phase20_7_turn(
        user_text="phase20.9z maintain seed",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    maintain = run_phase20_7_turn(
        user_text="phase20.9z maintain seed",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="",
        teacher_feedback=TeacherFeedback(
            feedback_text=feedback_text,
            reward_mag=1.0,
            target_event_id=_commit_event_id(maintain),
        ),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )


def test_phase20_9z_request_maintain_reads_unified_action_experience(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9z_request.sqlite"
    session_id = "phase20-9z-request"
    run_phase20_7_turn(
        user_text="phase20.9z repeated unknown",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    second = run_phase20_7_turn(
        user_text="phase20.9z repeated unknown",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(second, "maintain_unclosed")
    row = _competition_row(event, "maintain_unclosed")
    context = row["teacher_request_drive_context"]
    tuner = context["action_experience_tuner_projection"]

    assert tuner["formula_id"] == FORMULA_ID
    assert tuner["active"] is True
    assert tuner["ask_pressure"] > 0.0
    assert context["maintain_drive_before_action_experience_tuner"] < context["maintain_drive"]
    assert row["action_experience_tuner_projection"]["formula_id"] == FORMULA_ID
    assert row["drive_before_action_experience_tuner"] <= row["drive"]
    assert tuner["projection_only"] is True
    assert tuner["writes_answer_directly"] is False
    assert tuner["creates_reply_candidate"] is False


def test_phase20_9z_outward_speech_drive_uses_unified_tuner(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9z_outward.sqlite"
    session_id = "phase20-9z-outward"
    _teach_maintain_expression(db_path, session_id=session_id, feedback_text="still thinking")
    run_phase20_7_turn(
        user_text="phase20.9z outward unknown",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    first_idle = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="",
        teacher_feedback=TeacherFeedback(
            feedback_text="good",
            reward_mag=1.0,
            target_event_id=_commit_event_id(first_idle),
        ),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="phase20.9z outward second unknown",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    second_idle = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    candidate = second_idle.tick_trace[0].ssp_active_summary["outward_speech_candidate"]
    tuner = candidate["action_experience_tuner_projection"]

    assert tuner["formula_id"] == FORMULA_ID
    assert tuner["active"] is True
    assert tuner["outward_count"] >= 1
    assert tuner["reward_total"] > 0.0
    assert candidate["drive_before_action_experience_tuner"] != candidate["drive"]
    assert tuner["projection_only"] is True
    assert candidate["writes_answer_directly"] is False


def test_phase20_9z_draftgrid_next_action_rows_are_experience_tuned(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9z_draftgrid.sqlite"
    session_id = "phase20-9z-draftgrid"
    run_phase20_7_turn(
        user_text="phase20.9z draftgrid lesson",
        teacher_feedback=TeacherFeedback(feedback_text="alpha first fragment beta successor fragment", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    result = run_phase20_7_turn(
        user_text="phase20.9z draftgrid lesson",
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    commit_event = _event_with_action(result, "commit_reply")
    selection = commit_event.selected_action["draftgrid_next_action_selection"]
    tuner = selection["action_experience_tuner_projection"]
    rows = list(selection["candidate_rows"])

    assert tuner["formula_id"] == FORMULA_ID
    assert tuner["active"] is True
    assert any("action_experience_tuner_multiplier" in row for row in rows)
    assert all(row["drive"] >= 0.0 for row in rows)
    assert selection["writes_answer_directly"] is False
    assert selection["creates_reply_candidate"] is False
