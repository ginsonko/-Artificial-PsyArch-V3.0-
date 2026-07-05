from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9b_learning_protocol_drive_modulation/v1"


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


def test_phase20_9b_repeated_unanswered_unclosed_cools_request_drive(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9b.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9b repeated unknown",
        session_id="phase20-9b-repeat",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    second = run_phase20_7_turn(
        user_text="phase20.9b repeated unknown",
        session_id="phase20-9b-repeat",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(second, "maintain_unclosed")
    row = _competition_row(event, "maintain_unclosed")
    context = row["teacher_request_drive_context"]
    modulation = context["learning_protocol_drive_modulation"]

    assert modulation["formula_id"] == FORMULA_ID
    assert modulation["recent_request_count"] >= 1
    assert modulation["unclosed_attempt_count"] >= 1
    assert modulation["request_frequency_cooldown"] > 0.0
    assert modulation["maintain_drive_after"] < modulation["base_maintain_drive"]
    assert context["maintain_drive_before_action_experience_tuner"] == modulation["maintain_drive_after"]
    assert context["action_experience_tuner_projection"]["formula_id"] == "apv3_phase20_9z_unified_action_experience_tuner_projection/v1"
    assert context["maintain_drive"] >= context["maintain_drive_before_action_experience_tuner"]
    assert context["writes_answer_directly"] is False
    assert modulation["writes_answer_directly"] is False


def test_phase20_9b_teacher_off_exact_recall_fades_request_teacher_competition(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9b.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9b exact cue",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9b exact reply", reward_mag=1.0),
        session_id="phase20-9b-exact",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    result = run_phase20_7_turn(
        user_text="phase20.9b exact cue",
        session_id="phase20-9b-exact",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = next(event for event in result.tick_trace if event.b_candidates)
    request_row = _competition_row(event, "request_teacher")
    modulation = request_row["learning_protocol_drive_modulation"]

    assert event.b_candidates[0]["kind"] == "exact_b0"
    assert modulation["formula_id"] == FORMULA_ID
    assert modulation["modulation_kind"] == "teacher_off_exact_recall_fades_request"
    assert request_row["drive"] < request_row["drive_before_learning_protocol_modulation"]
    # P1-1 (2026-07-02): 竞争行现在显示真实计算的 request drive (不再是未选中时
    # 硬编 0.18 的占位). fade 的语义断言改为: 请求驱动被压到明显低于获胜的
    # write 行 — 教师退场由竞争差距体现, 不锚定旧硬编常数.
    write_row = _competition_row(event, "write_cell")
    assert request_row["drive"] < float(write_row["drive"]) * 0.72
    assert modulation["creates_reply_candidate"] is False
    assert modulation["writes_answer_directly"] is False


def test_phase20_9b_feedback_integration_holds_new_teacher_request(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9b feedback prompt",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9b feedback reply", reward_mag=1.0),
        session_id="phase20-9b-feedback",
        db_path=tmp_path / "phase20_9b.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "integrate_feedback")
    request_row = _competition_row(event, "request_teacher")
    modulation = request_row["learning_protocol_drive_modulation"]

    assert modulation["formula_id"] == FORMULA_ID
    assert modulation["modulation_kind"] == "feedback_integration_holds_new_request"
    assert request_row["drive"] < request_row["drive_before_learning_protocol_modulation"]
    assert event.selected_action["action_type"] == "integrate_feedback"
    assert modulation["writes_answer_directly"] is False


def test_phase20_9b_first_unknown_keeps_request_drive_uncooldowned(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9b first unknown",
        session_id="phase20-9b-first",
        db_path=tmp_path / "phase20_9b.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "request_teacher")
    row = _competition_row(event, "request_teacher")
    context = row["teacher_request_drive_context"]
    modulation = context["learning_protocol_drive_modulation"]

    assert modulation["formula_id"] == FORMULA_ID
    assert modulation["recent_request_count"] == 0
    assert modulation["unclosed_attempt_count"] == 0
    assert modulation["request_frequency_cooldown"] == 0.0
    assert modulation["request_drive_after"] == modulation["base_request_drive"]
    assert context["request_drive"] == modulation["request_drive_after"]
