from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_8q_draftgrid_expression_fragment_composition/v1"


def _event_with_action(result, action_type: str):
    for event in result.tick_trace:
        if event.selected_action.get("action_type") == action_type:
            return event
    raise AssertionError(f"event not found: {action_type}")


def _commit_event_id(result) -> str:
    event = _event_with_action(result, "commit_reply")
    assert event.experience_event_ids_written
    return event.experience_event_ids_written[0]


def _flat(text: str) -> str:
    return " ".join(str(text).split())


def _compact(text: str) -> str:
    return "".join(str(text).split())


def _teach_request_expression(db_path: Path, *, session_id: str, seed_text: str, feedback_text: str) -> None:
    seed = run_phase20_7_turn(
        user_text=seed_text,
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
            target_event_id=_commit_event_id(seed),
        ),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )


def _teach_maintain_expression(db_path: Path, *, session_id: str, seed_text: str, feedback_text: str) -> None:
    run_phase20_7_turn(
        user_text=seed_text,
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    maintain = run_phase20_7_turn(
        user_text=seed_text,
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


def test_phase20_8q_request_expression_combines_two_learned_fragments(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8q.sqlite"
    _teach_request_expression(
        db_path,
        session_id="phase20-8q-request-a",
        seed_text="phase20q request seed a",
        feedback_text="I am not sure",
    )
    _teach_request_expression(
        db_path,
        session_id="phase20-8q-request-b",
        seed_text="phase20q request seed b",
        feedback_text="please teach me",
    )
    result = run_phase20_7_turn(
        user_text="phase20q request fresh unknown",
        session_id="phase20-8q-request-c",
        db_path=db_path,
        max_ticks=64,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "request_teacher")
    trace = event.ssp_active_summary["request_expression_selection"]

    assert trace["source_kind"] == "expression_fragment_composition"
    assert trace["composition_formula_id"] == FORMULA_ID
    assert trace["composition_kind"] == "draftgrid_fragment_combination"
    assert trace["fragment_count"] >= 2
    assert len(trace["source_event_ids"]) >= 2
    assert "I am not sure" in _flat(result.reply_text)
    assert "please teach me" in _flat(result.reply_text)
    assert _compact(trace["selected_text"]) == _compact(result.reply_text)
    assert trace["creates_answer_candidate"] is False
    assert trace["writes_answer_directly"] is False
    assert not event.b_candidates


def test_phase20_8q_single_expression_candidate_still_uses_whole_expression(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8q.sqlite"
    _teach_request_expression(
        db_path,
        session_id="phase20-8q-single-a",
        seed_text="phase20q single seed",
        feedback_text="one learned phrase",
    )
    result = run_phase20_7_turn(
        user_text="phase20q single fresh",
        session_id="phase20-8q-single-b",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "request_teacher")
    trace = event.ssp_active_summary["request_expression_selection"]

    assert result.reply_text == "one learned phrase"
    assert trace["source_kind"] == "teacher_feedback_expression"
    assert "composition_formula_id" not in trace
    assert not event.b_candidates


def test_phase20_8q_maintain_expression_combines_maintain_fragments(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8q.sqlite"
    _teach_maintain_expression(
        db_path,
        session_id="phase20-8q-maintain-a",
        seed_text="phase20q maintain seed a",
        feedback_text="still thinking",
    )
    _teach_maintain_expression(
        db_path,
        session_id="phase20-8q-maintain-b",
        seed_text="phase20q maintain seed b",
        feedback_text="not finished yet",
    )
    run_phase20_7_turn(
        user_text="phase20q maintain fresh",
        session_id="phase20-8q-maintain-c",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    result = run_phase20_7_turn(
        user_text="phase20q maintain fresh",
        session_id="phase20-8q-maintain-c",
        db_path=db_path,
        max_ticks=64,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "maintain_unclosed")
    trace = event.ssp_active_summary["request_expression_selection"]

    assert trace["source_kind"] == "expression_fragment_composition"
    assert trace["composition_formula_id"] == FORMULA_ID
    assert trace["current_paradigm_slot"] == "unclosed_maintenance"
    assert trace["fragment_count"] >= 2
    assert "stillthinking" in _compact(result.reply_text)
    assert "notfinishedyet" in _compact(result.reply_text)
    assert not event.b_candidates
