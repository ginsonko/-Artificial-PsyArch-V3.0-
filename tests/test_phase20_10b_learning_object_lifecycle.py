from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_10b_learning_object_lifecycle_projection/v1"


def _carryover_from_event(event) -> dict:
    for row in event.action_competition:
        carryover = row.get("learning_loop_carryover")
        if isinstance(carryover, dict) and carryover.get("learning_stage_runtime_progression"):
            return carryover
    carryover = event.feelings.get("learning_loop_carryover") if isinstance(event.feelings, dict) else {}
    return dict(carryover) if isinstance(carryover, dict) else {}


def _lifecycle_from_event(event) -> dict:
    carryover = _carryover_from_event(event)
    progression = carryover.get("learning_stage_runtime_progression")
    assert isinstance(progression, dict), "10a progression should be present"
    lifecycle = progression.get("learning_object_lifecycle")
    assert isinstance(lifecycle, dict), "10b lifecycle should be present"
    return lifecycle


def _teach_and_recall(db_path: Path, *, session_id: str) -> None:
    run_phase20_7_turn(
        user_text=f"{session_id} cue",
        teacher_feedback=TeacherFeedback(feedback_text=f"{session_id} reply", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text=f"{session_id} cue",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )


def test_phase20_10b_same_learning_object_advances_across_review_and_self_test(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_10b_lifecycle.sqlite"
    session_id = "phase20-10b-life"
    _teach_and_recall(db_path, session_id=session_id)

    review = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    self_test = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    later_review = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    first_lifecycle = _lifecycle_from_event(review.tick_trace[0])
    second_lifecycle = _lifecycle_from_event(self_test.tick_trace[0])
    third_lifecycle = _lifecycle_from_event(later_review.tick_trace[0])

    assert first_lifecycle["formula_id"] == FORMULA_ID
    assert first_lifecycle["active"] is True
    assert first_lifecycle["learning_object_id"] == second_lifecycle["learning_object_id"] == third_lifecycle["learning_object_id"]
    assert first_lifecycle["review_count"] == 0
    assert second_lifecycle["review_count"] >= 1
    assert third_lifecycle["self_test_count"] >= 1
    assert third_lifecycle["self_test_success_count"] >= 1
    assert third_lifecycle["lifecycle_stage_index"] >= second_lifecycle["lifecycle_stage_index"]
    assert third_lifecycle["current_lifecycle_stage"] in {"retested", "teacher_exit_ready", "cold_retest_ready"}
    assert third_lifecycle["lifecycle_action_deltas"]["commit_reply"] > 0.0
    assert third_lifecycle["lifecycle_action_deltas"]["request_teacher"] < 0.0
    assert third_lifecycle["uses_existing_ap_flow"] is True
    assert third_lifecycle["projection_only"] is True
    assert third_lifecycle["writes_answer_directly"] is False
    assert third_lifecycle["creates_reply_candidate"] is False


def test_phase20_10b_failed_self_test_regresses_lifecycle_to_adjustment(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_10b_failure.sqlite"
    session_id = "phase20-10b-failure"
    _teach_and_recall(db_path, session_id=session_id)
    run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    self_test = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    occurrence_id = self_test.tick_trace[0].ssp_active_summary["idle_narrative_flow"]["occurrence_id"]
    with sqlite3.connect(db_path) as conn:
        raw = conn.execute(
            "SELECT position_json FROM phase20_7_occurrences WHERE occurrence_id=?",
            (occurrence_id,),
        ).fetchone()[0]
        position = json.loads(str(raw))
        position["idle_self_test"]["self_test_grasp"] = 0.18
        position["idle_self_test"]["match_score"] = 0.12
        position["idle_self_test"]["recalled_text"] = "wrong recall"
        conn.execute(
            "UPDATE phase20_7_occurrences SET position_json=? WHERE occurrence_id=?",
            (json.dumps(position, ensure_ascii=False, sort_keys=True, separators=(",", ":")), occurrence_id),
        )
        conn.commit()

    feedback_review = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    lifecycle = _lifecycle_from_event(feedback_review.tick_trace[0])
    deltas = lifecycle["lifecycle_action_deltas"]

    assert lifecycle["self_test_failure_count"] >= 1
    assert lifecycle["self_test_success_count"] == 0
    assert lifecycle["current_lifecycle_stage"] in {"adjusted_after_feedback", "reviewed", "self_tested"}
    assert lifecycle["regression"] > lifecycle["stability"]
    assert deltas["request_teacher"] > 0.0
    assert deltas["read_draft"] > 0.0
    assert deltas["edit_cell"] > 0.0
    assert feedback_review.reply_text == ""
    assert lifecycle["writes_answer_directly"] is False
    assert lifecycle["creates_reply_candidate"] is False
