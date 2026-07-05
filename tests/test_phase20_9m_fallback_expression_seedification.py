from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9m_fallback_expression_seedification/v1"


def _event_with_action(result, action_type: str):
    for event in result.tick_trace:
        if event.selected_action.get("action_type") == action_type:
            return event
    raise AssertionError(f"event not found: {action_type}")


def _commit_event_id(result) -> str:
    event = _event_with_action(result, "commit_reply")
    assert event.experience_event_ids_written
    return event.experience_event_ids_written[0]


def _commit_expression_trace(result) -> dict:
    event = _event_with_action(result, "commit_reply")
    trace = event.ssp_active_summary.get("request_expression_selection")
    assert isinstance(trace, dict)
    return trace


def test_phase20_9m_feedback_ack_cold_start_uses_low_priority_innate_seed(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9m cold feedback prompt",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9m taught reply", reward_mag=1.0),
        session_id="phase20-9m-cold",
        db_path=tmp_path / "phase20_9m.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    trace = _commit_expression_trace(result)

    assert result.reply_text == "嗯,记下了。"
    assert trace["intent"] == "integrate_feedback"
    assert trace["fallback_seed_formula_id"] == FORMULA_ID
    assert trace["source_kind"] == "innate_minimal_expression"
    assert trace["fallback_used"] is True
    assert trace["innate_seed_low_priority"] is True
    assert trace["creates_answer_candidate"] is False
    assert trace["writes_answer_directly"] is False


def test_phase20_9m_taught_feedback_ack_expression_overrides_seed_without_answer_route(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "phase20_9m.sqlite"
    session_id = "phase20-9m-learned-ack"

    seed_ack = run_phase20_7_turn(
        user_text="phase20.9m first lesson",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9m first answer", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    run_phase20_7_turn(
        user_text="",
        teacher_feedback=TeacherFeedback(
            feedback_text="好,我记住啦",
            reward_mag=1.0,
            target_event_id=_commit_event_id(seed_ack),
        ),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    result = run_phase20_7_turn(
        user_text="phase20.9m second lesson",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9m second answer", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    trace = _commit_expression_trace(result)

    assert result.reply_text == "好,我记住啦"
    assert trace["intent"] == "integrate_feedback"
    assert trace["fallback_seed_formula_id"] == FORMULA_ID
    assert trace["source_kind"] == "teacher_feedback_expression"
    assert trace["selected_paradigm_slot"] == "feedback_acknowledgement"
    assert trace["fallback_used"] is False
    assert trace["learned_expression_preferred_over_seed"] is True
    assert trace["fallback_text_hash"] != trace["selected_text_hash"]
    assert trace["creates_answer_candidate"] is False
    assert trace["writes_answer_directly"] is False

