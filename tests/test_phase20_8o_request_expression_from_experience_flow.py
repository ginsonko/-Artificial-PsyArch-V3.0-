from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_8o_request_expression_from_experience_flow/v1"


def _event_with_action(result, action_type: str):
    for event in result.tick_trace:
        if event.selected_action.get("action_type") == action_type:
            return event
    raise AssertionError(f"event not found: {action_type}")


def _commit_event_id(result) -> str:
    event = _event_with_action(result, "commit_reply")
    assert event.experience_event_ids_written
    return event.experience_event_ids_written[0]


def test_phase20_8o_cold_start_request_expression_is_audited_as_innate_fallback(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20o cold unknown",
        session_id="phase20-8o-cold",
        db_path=tmp_path / "phase20_8o.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "request_teacher")
    trace = event.ssp_active_summary["request_expression_selection"]

    assert trace["formula_id"] == FORMULA_ID
    assert trace["intent"] == "request_teacher"
    assert trace["source_kind"] == "innate_minimal_expression"
    assert trace["candidate_count"] == 0
    assert trace["selected_text"] == result.reply_text
    assert trace["creates_answer_candidate"] is False
    assert trace["writes_answer_directly"] is False


def test_phase20_8o_targeted_feedback_teaches_request_expression_without_reply_shortcut(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8o.sqlite"
    first = run_phase20_7_turn(
        user_text="phase20o target request seed",
        session_id="phase20-8o-request",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    target_event_id = _commit_event_id(first)
    run_phase20_7_turn(
        user_text="",
        teacher_feedback=TeacherFeedback(
            feedback_text="please teach me",
            reward_mag=1.0,
            target_event_id=target_event_id,
        ),
        session_id="phase20-8o-request",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    result = run_phase20_7_turn(
        user_text="phase20o fresh request unknown",
        session_id="phase20-8o-request",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "request_teacher")
    trace = event.ssp_active_summary["request_expression_selection"]

    assert result.reply_text == "please teach me"
    assert trace["formula_id"] == FORMULA_ID
    assert trace["source_kind"] == "teacher_feedback_expression"
    assert trace["candidate_count"] >= 1
    assert trace["selected_text"] == "please teach me"
    assert not event.b_candidates


def test_phase20_8o_ordinary_knowledge_feedback_does_not_pollute_request_expression(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8o.sqlite"
    run_phase20_7_turn(
        user_text="phase20o knowledge question",
        teacher_feedback=TeacherFeedback(feedback_text="red apple", reward_mag=1.0),
        session_id="phase20-8o-knowledge",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    result = run_phase20_7_turn(
        user_text="phase20o unrelated unknown",
        session_id="phase20-8o-knowledge",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "request_teacher")
    trace = event.ssp_active_summary["request_expression_selection"]

    assert result.reply_text != "red apple"
    assert trace["source_kind"] != "teacher_feedback_expression"
    assert trace["selected_text"] != "red apple"
    assert not event.b_candidates


def test_phase20_8o_targeted_feedback_teaches_maintain_unclosed_expression(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8o.sqlite"
    run_phase20_7_turn(
        user_text="phase20o maintain seed",
        session_id="phase20-8o-maintain",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    second = run_phase20_7_turn(
        user_text="phase20o maintain seed",
        session_id="phase20-8o-maintain",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    target_event_id = _commit_event_id(second)
    run_phase20_7_turn(
        user_text="",
        teacher_feedback=TeacherFeedback(
            feedback_text="still thinking",
            reward_mag=1.0,
            target_event_id=target_event_id,
        ),
        session_id="phase20-8o-maintain",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    result = run_phase20_7_turn(
        user_text="phase20o maintain seed",
        session_id="phase20-8o-maintain",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "maintain_unclosed")
    trace = event.ssp_active_summary["request_expression_selection"]

    assert result.reply_text == "still thinking"
    assert trace["formula_id"] == FORMULA_ID
    assert trace["intent"] == "maintain_unclosed"
    assert trace["source_kind"] == "teacher_feedback_expression"
    assert trace["selected_text"] == "still thinking"
    assert not event.b_candidates
