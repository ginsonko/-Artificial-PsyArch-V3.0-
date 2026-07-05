from __future__ import annotations

import sqlite3
from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9f_idle_learning_review/v1"


def _row(event, action_type: str) -> dict:
    for item in event.action_competition:
        if item.get("action_type") == action_type:
            return dict(item)
    raise AssertionError(f"competition row not found: {action_type}")


def _learning_review(event) -> dict:
    review = event.feelings.get("idle_learning_review", {})
    assert isinstance(review, dict)
    return review


def test_phase20_9f_feedback_alignment_drives_private_idle_review(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9f.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9f feedback cue",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9f feedback reply", reward_mag=1.0),
        session_id="phase20-9f-feedback",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9f-feedback",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    event = idle.tick_trace[0]
    review = _learning_review(event)
    row = _row(event, "idle_think")

    assert idle.reply_text == ""
    assert idle.committed is False
    assert event.selected_action["action_type"] == "idle_think"
    assert event.selected_action["private_thought"] is True
    assert event.selected_action["idle_learning_review"] is True
    assert review["formula_id"] == FORMULA_ID
    assert review["dominant_learning_tendency"] == "feedback_only"
    assert review["source_text"] == "phase20.9f feedback cue"
    assert review["target_text"] == "phase20.9f feedback reply"
    assert "先整理" in event.feelings["narrative_text"]
    assert row["learning_loop_carryover"]["idle_review_formula_id"] == FORMULA_ID
    assert row["learning_loop_carryover_delta"] > 0.0
    assert event.c_forward[0]["kind"] == "idle_learning_review_continuation"
    assert event.c_forward[0]["writes_answer_directly"] is False
    assert review["creates_reply_candidate"] is False
    assert review["writes_answer_directly"] is False
    assert event.ssp_active_summary["idle_narrative_flow"]["source_kind"] == "learning_review"

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            """
            SELECT COUNT(*) FROM phase20_7_occurrences
            WHERE sa_type_id LIKE 'short_structure_flow::learning_review::%'
            """
        ).fetchone()[0]
    assert count >= 1


def test_phase20_9f_teacher_off_recall_drives_idle_self_probe(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9f.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9f exact cue",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9f exact reply", reward_mag=1.0),
        session_id="phase20-9f-teacher-off",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="phase20.9f exact cue",
        session_id="phase20-9f-teacher-off",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9f-teacher-off",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    event = idle.tick_trace[0]
    review = _learning_review(event)
    row = _row(event, "idle_think")

    assert event.selected_action["action_type"] == "idle_think"
    assert review["formula_id"] == FORMULA_ID
    assert review["dominant_learning_tendency"] == "teacher_off_probe"
    assert review["teacher_off_readiness"] > review["scaffold_regression_need"]
    assert review["recent_output_intent"] == "exact_b0"
    assert "试着自己" in event.feelings["narrative_text"]
    assert row["learning_loop_carryover"]["teacher_off_readiness"] > 0.0
    assert row["learning_loop_carryover_delta"] > 0.0
    assert idle.reply_text == ""


def test_phase20_9f_no_experience_keeps_idle_observe_without_fake_review(tmp_path: Path) -> None:
    idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9f-empty",
        db_path=tmp_path / "phase20_9f.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    event = idle.tick_trace[0]

    assert event.selected_action["action_type"] == "idle_observe"
    assert event.feelings.get("idle_learning_review") in (None, {})
    assert idle.reply_text == ""
    assert not any("learning_loop_carryover" in row for row in event.action_competition)
