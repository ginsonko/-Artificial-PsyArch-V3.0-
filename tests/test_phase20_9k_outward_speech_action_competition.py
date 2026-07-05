from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9k_outward_speech_action_competition/v1"


def _event_with_action(result, action_type: str):
    for event in result.tick_trace:
        if event.selected_action.get("action_type") == action_type:
            return event
    raise AssertionError(f"event not found: {action_type}")


def _commit_event_id(result) -> str:
    event = _event_with_action(result, "commit_reply")
    assert event.experience_event_ids_written
    return event.experience_event_ids_written[0]


def _compact(text: str) -> str:
    return "".join(str(text).split())


def _rejected_intent_entity_key() -> str:
    return "intent" + "_competition"


def _teach_maintain_expression(db_path: Path, *, session_id: str, feedback_text: str) -> None:
    run_phase20_7_turn(
        user_text="phase20k maintain seed",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    maintain = run_phase20_7_turn(
        user_text="phase20k maintain seed",
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


def test_phase20_9k_idle_private_thought_does_not_externalize_without_learned_expression(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9k.sqlite"
    run_phase20_7_turn(
        user_text="phase20k unknown without expression",
        session_id="phase20-9k-silent",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9k-silent",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = idle.tick_trace[0]
    candidate = event.ssp_active_summary["outward_speech_candidate"]

    assert idle.reply_text == ""
    assert idle.committed is False
    assert event.selected_action["action_type"] == "idle_think"
    assert event.selected_action["private_thought"] is True
    assert candidate["formula_id"] == FORMULA_ID
    assert candidate["eligible"] is False
    assert candidate["blocked_reason"] == "no_learned_external_expression"
    assert candidate["creates_reply_candidate"] is False
    assert candidate["writes_answer_directly"] is False


def test_phase20_9k_learned_maintain_expression_can_externalize_idle_private_thought(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9k.sqlite"
    _teach_maintain_expression(
        db_path,
        session_id="phase20-9k-speak",
        feedback_text="still thinking",
    )
    run_phase20_7_turn(
        user_text="phase20k open unknown",
        session_id="phase20-9k-speak",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9k-speak",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    private_event = idle.tick_trace[0]
    outward_event = _event_with_action(idle, "outward_speech")
    commit_event = _event_with_action(idle, "commit_reply")
    candidate = private_event.ssp_active_summary["outward_speech_candidate"]

    assert _compact(idle.reply_text) == "stillthinking"
    assert idle.committed is True
    assert private_event.selected_action["action_type"] == "idle_think"
    assert private_event.selected_action["private_thought"] is True
    assert private_event.selected_action["outward_speech_eligible"] is True
    assert candidate["formula_id"] == FORMULA_ID
    assert candidate["eligible"] is True
    assert candidate["drive"] >= 0.50
    assert candidate["ap_native_source"] == "idle_private_thought_to_action_competition"
    assert candidate["writes_answer_directly"] is False
    assert outward_event.selected_action["outward_speech_candidate"]["source_private_event_id"]
    assert commit_event.selected_action["source_intent"] == "outward_speech"
    assert any(row["action_type"] == "outward_speech" and row["selected"] for row in outward_event.action_competition)
    assert any(row["action_type"] == "commit_reply" and row["selected"] for row in commit_event.action_competition)
    assert not outward_event.b_candidates


def test_phase20_9k_no_feedback_and_repetition_fatigue_suppress_next_idle_externalization(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9k.sqlite"
    _teach_maintain_expression(
        db_path,
        session_id="phase20-9k-fatigue",
        feedback_text="still thinking",
    )
    run_phase20_7_turn(
        user_text="phase20k repeated unknown",
        session_id="phase20-9k-fatigue",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    first_idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9k-fatigue",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    second_idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9k-fatigue",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    first_candidate = first_idle.tick_trace[0].ssp_active_summary["outward_speech_candidate"]
    second_candidate = second_idle.tick_trace[0].ssp_active_summary["outward_speech_candidate"]

    assert first_idle.committed is True
    assert first_candidate["eligible"] is True
    assert second_idle.reply_text == ""
    assert second_idle.committed is False
    assert second_candidate["formula_id"] == FORMULA_ID
    assert second_candidate["eligible"] is False
    assert second_candidate["recent_outward_count"] >= 1
    assert second_candidate["recent_same_text_count"] >= 1
    assert second_candidate["no_feedback_penalty"] > 0.0
    assert second_candidate["repetition_fatigue"] > 0.0
    assert second_candidate["action_outcome_no_feedback_delta"] > 0.0
    assert second_candidate["action_outcome_terms"]["term_kind"] == "existing_outward_speech_action_outcome"
    assert _rejected_intent_entity_key() not in second_candidate


def test_phase20_9k_rewarded_outward_speech_raises_same_action_outcome_delta(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9k.sqlite"
    _teach_maintain_expression(
        db_path,
        session_id="phase20-9k-reward",
        feedback_text="still thinking",
    )
    run_phase20_7_turn(
        user_text="phase20k rewarded unknown",
        session_id="phase20-9k-reward",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    first_idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9k-reward",
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
        session_id="phase20-9k-reward",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="phase20k second rewarded unknown",
        session_id="phase20-9k-reward",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    second_idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9k-reward",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    first_candidate = first_idle.tick_trace[0].ssp_active_summary["outward_speech_candidate"]
    second_candidate = second_idle.tick_trace[0].ssp_active_summary["outward_speech_candidate"]
    outcome_terms = second_candidate["action_outcome_terms"]

    assert first_candidate["action_outcome_reward_delta"] == 0.0
    assert outcome_terms["matched_action_count"] >= 1
    assert second_candidate["action_outcome_reward_delta"] > 0.0
    assert second_candidate["action_outcome_punish_delta"] == 0.0
    assert _rejected_intent_entity_key() not in second_candidate
    assert second_candidate["formula_id"] == FORMULA_ID
