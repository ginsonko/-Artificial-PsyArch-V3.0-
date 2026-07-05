from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.cognitive_cycle import (
    PHASE20_9C_LEARNING_LOOP_METRICS_ID,
    complete_every_tick_cognitive_cycle,
)
from apv3test.runtime.phase20_7.models import RuntimeTickEventV2


def _metric(event) -> dict:
    matches = [
        dict(delta)
        for delta in event.learning_deltas
        if delta.get("delta_kind") == "learning_loop_metrics"
        and delta.get("formula_id") == PHASE20_9C_LEARNING_LOOP_METRICS_ID
    ]
    assert len(matches) == 1
    return matches[0]


def _event_with_action(result, action_type: str):
    for event in result.tick_trace:
        if event.selected_action.get("action_type") == action_type:
            return event
    raise AssertionError(f"event not found: {action_type}")


def test_phase20_9c_first_unknown_marks_scaffold_regression_without_fake_reply(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9c first unknown",
        session_id="phase20-9c-unknown",
        db_path=tmp_path / "phase20_9c.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "request_teacher")
    metric = _metric(event)

    assert metric["dominant_learning_tendency"] == "return_to_scaffold"
    assert metric["scaffold_regression_need"] > metric["teacher_off_readiness"]
    assert metric["evidence"]["request_scaffold_signal"] > 0.0
    assert metric["projection_only"] is True
    assert metric["creates_reply_candidate"] is False
    assert metric["writes_answer_directly"] is False


def test_phase20_9c_teacher_feedback_raises_feedback_only_readiness(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9c feedback prompt",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9c feedback reply", reward_mag=1.0),
        session_id="phase20-9c-feedback",
        db_path=tmp_path / "phase20_9c.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "integrate_feedback")
    metric = _metric(event)

    assert metric["feedback_only_readiness"] > 0.35
    assert metric["feedback_only_readiness"] > metric["teacher_off_readiness"]
    assert metric["evidence"]["teacher_signal"] == 1.0
    assert metric["writes_answer_directly"] is False


def test_phase20_9c_exact_recall_raises_teacher_off_readiness(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9c.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9c exact cue",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9c exact reply", reward_mag=1.0),
        session_id="phase20-9c-exact",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    result = run_phase20_7_turn(
        user_text="phase20.9c exact cue",
        session_id="phase20-9c-exact",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = next(event for event in result.tick_trace if event.b_candidates)
    metric = _metric(event)

    assert event.b_candidates[0]["kind"] == "exact_b0"
    assert metric["dominant_learning_tendency"] == "teacher_off_probe"
    assert metric["teacher_off_readiness"] > 0.70
    assert metric["teacher_off_readiness"] > metric["scaffold_regression_need"]
    assert metric["evidence"]["teacher_signal"] == 0.0


def test_phase20_9c_late_teacher_absent_memory_tick_exposes_cold_retest_pressure() -> None:
    event = RuntimeTickEventV2(
        tick=64,
        session_id="phase20-9c-cold",
        selected_action={"action_type": "commit_reply", "drive": 0.82},
        b_candidates=(
            {
                "kind": "exact_b0",
                "support": 0.84,
                "candidate_audit_slots": (
                    {
                        "slot_kind": "unified_experience_candidate",
                        "candidate_id": "cold-memory-1",
                        "candidate_kind": "exact_b0",
                        "support": 0.84,
                        "support_formula": "test_memory_support",
                    },
                ),
                "writes_answer_directly": False,
            },
        ),
        action_competition=(
            {"action_type": "commit_reply", "drive": 0.82, "selected": True},
            {"action_type": "request_teacher", "drive": 0.10, "selected": False},
        ),
    )
    completed = complete_every_tick_cognitive_cycle(event)
    metric = _metric(completed)

    assert metric["cold_retest_readiness"] > 0.50
    assert metric["teacher_off_readiness"] > 0.60
    assert metric["evidence"]["cold_retest_hint"] > 0.0
    assert metric["writes_answer_directly"] is False

