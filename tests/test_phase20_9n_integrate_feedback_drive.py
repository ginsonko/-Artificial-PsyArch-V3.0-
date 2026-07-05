from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9n_integrate_feedback_drive_from_ap_flow/v1"


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


def _integrate_trace(result) -> dict:
    event = _event_with_action(result, "integrate_feedback")
    row = _competition_row(event, "integrate_feedback")
    trace = row.get("integrate_feedback_drive_from_ap_flow")
    assert isinstance(trace, dict)
    return trace


def test_phase20_9n_integrate_feedback_drive_is_from_ap_flow_not_fixed_high_constant(
    tmp_path: Path,
) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9n feedback prompt",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9n feedback reply", reward_mag=1.0),
        session_id="phase20-9n-drive",
        db_path=tmp_path / "phase20_9n.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    event = _event_with_action(result, "integrate_feedback")
    row = _competition_row(event, "integrate_feedback")
    trace = row["integrate_feedback_drive_from_ap_flow"]

    assert trace["formula_id"] == FORMULA_ID
    assert trace["feedback_evidence"] > 0.0
    assert trace["target_grasp"] > 0.0
    assert trace["value_signal"] > 0.0
    assert trace["drive"] == row["drive_before_learning_loop_carryover"]
    assert row["drive"] >= trace["drive"]
    assert row["cstar_carryover_drive_delta"] > 0.0
    assert row["drive"] != 0.9
    assert trace["writes_answer_directly"] is False
    assert trace["creates_reply_candidate"] is False
    assert event.feelings["source"] == "integrate_feedback_drive_from_ap_flow"


def test_phase20_9n_learned_ack_expression_raises_feedback_expression_readiness(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "phase20_9n.sqlite"
    session_id = "phase20-9n-expression"

    first = run_phase20_7_turn(
        user_text="phase20.9n first lesson",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9n first answer", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    cold_trace = _integrate_trace(first)
    run_phase20_7_turn(
        user_text="",
        teacher_feedback=TeacherFeedback(
            feedback_text="好,我记住啦",
            reward_mag=1.0,
            target_event_id=_commit_event_id(first),
        ),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    second = run_phase20_7_turn(
        user_text="phase20.9n second lesson",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9n second answer", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    learned_trace = _integrate_trace(second)

    assert cold_trace["learned_expression"] is False
    assert learned_trace["learned_expression"] is True
    assert learned_trace["expression_readiness"] > cold_trace["expression_readiness"]
    assert learned_trace["drive"] >= cold_trace["drive"] - 0.08
    assert learned_trace["writes_answer_directly"] is False


def test_phase20_9n_repeated_feedback_ack_adds_fatigue_without_suppressing_learning(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "phase20_9n.sqlite"
    session_id = "phase20-9n-fatigue"

    first = run_phase20_7_turn(
        user_text="phase20.9n fatigue lesson 1",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9n answer 1", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    first_trace = _integrate_trace(first)
    second = run_phase20_7_turn(
        user_text="phase20.9n fatigue lesson 2",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9n answer 2", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    second_trace = _integrate_trace(second)

    assert second_trace["recent_feedback_actions"] > first_trace["recent_feedback_actions"]
    assert second_trace["repeated_expression_count"] >= first_trace["repeated_expression_count"]
    assert second_trace["repetition_fatigue"] > first_trace["repetition_fatigue"]
    assert second_trace["drive"] < 1.0
    assert second_trace["drive"] > 0.35
    assert second_trace["creates_reply_candidate"] is False
