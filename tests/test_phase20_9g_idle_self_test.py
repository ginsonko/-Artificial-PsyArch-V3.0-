from __future__ import annotations

import sqlite3
from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9g_idle_self_test/v1"


def _row(event, action_type: str) -> dict:
    for item in event.action_competition:
        if item.get("action_type") == action_type:
            return dict(item)
    raise AssertionError(f"competition row not found: {action_type}")


def test_phase20_9g_second_idle_after_teacher_off_review_creates_private_self_test(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9g.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9g exact cue",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9g exact reply", reward_mag=1.0),
        session_id="phase20-9g-self-test",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="phase20.9g exact cue",
        session_id="phase20-9g-self-test",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    first_idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9g-self-test",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    second_idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9g-self-test",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    first_event = first_idle.tick_trace[0]
    event = second_idle.tick_trace[0]
    self_test = event.feelings["idle_self_test"]
    row = _row(event, "idle_think")

    assert first_event.selected_action["idle_learning_review"] is True
    assert "idle_self_test" not in first_event.selected_action
    assert second_idle.reply_text == ""
    assert second_idle.committed is False
    assert event.selected_action["action_type"] == "idle_think"
    assert event.selected_action["private_thought"] is True
    assert event.selected_action["idle_self_test"] is True
    assert self_test["formula_id"] == FORMULA_ID
    assert self_test["self_test_kind"] in {"teacher_off_self_test", "cold_retest_self_test"}
    assert self_test["source_review_occurrence_id"] == first_event.ssp_active_summary["idle_narrative_flow"]["occurrence_id"]
    assert self_test["expected_text"] == "phase20.9g exact reply"
    assert self_test["recalled_text"] == "phase20.9g exact reply"
    assert self_test["self_test_grasp"] > 0.7
    assert self_test["writes_answer_directly"] is False
    assert self_test["creates_reply_candidate"] is False
    assert row["learning_loop_carryover_delta"] > 0.0
    assert event.ssp_active_summary["idle_narrative_flow"]["source_kind"] == "self_test"
    assert event.c_forward[0]["kind"] == "idle_learning_self_test_recall"
    assert event.c_forward[0]["formula_id"] == FORMULA_ID
    assert event.c_forward[0]["writes_answer_directly"] is False
    assert event.c_backward[0]["kind"] == "idle_learning_self_test_source_trace"
    assert event.c_backward[0]["formula_id"] == FORMULA_ID

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            """
            SELECT COUNT(*) FROM phase20_7_occurrences
            WHERE sa_type_id LIKE 'short_structure_flow::self_test::%'
            """
        ).fetchone()[0]
    assert count >= 1


def test_phase20_9g_first_idle_still_reviews_before_self_testing(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9g.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9g review first",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9g review reply", reward_mag=1.0),
        session_id="phase20-9g-review-first",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="phase20.9g review first",
        session_id="phase20-9g-review-first",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    first_idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9g-review-first",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    event = first_idle.tick_trace[0]

    assert event.selected_action["idle_learning_review"] is True
    assert "idle_self_test" not in event.selected_action
    assert event.feelings["idle_learning_review"]["formula_id"] == "apv3_phase20_9f_idle_learning_review/v1"
    assert event.feelings.get("idle_self_test") in (None, {})


def test_phase20_9g_feedback_only_review_does_not_force_self_test(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9g.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9g feedback only",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9g feedback reply", reward_mag=1.0),
        session_id="phase20-9g-feedback-only",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    first_idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9g-feedback-only",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    second_idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9g-feedback-only",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    assert first_idle.tick_trace[0].selected_action["idle_learning_review"] is True
    assert second_idle.tick_trace[0].selected_action.get("idle_self_test") is not True
    assert second_idle.reply_text == ""
    assert second_idle.tick_trace[0].feelings.get("idle_self_test") in (None, {})

