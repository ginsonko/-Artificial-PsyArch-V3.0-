from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9h_self_test_feedback/v1"


def _make_self_test_sequence(db_path: Path, *, session_id: str):
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
    return review, self_test


def test_phase20_9h_successful_self_test_stabilizes_next_teacher_off_review(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9h.sqlite"
    review, self_test = _make_self_test_sequence(db_path, session_id="phase20-9h-success")

    feedback = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9h-success",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    event = feedback.tick_trace[0]
    metric = event.feelings["idle_learning_review"]
    feedback_packet = metric["self_test_feedback"]

    assert review.tick_trace[0].selected_action["idle_learning_review"] is True
    assert self_test.tick_trace[0].selected_action["idle_self_test"] is True
    assert event.selected_action["idle_learning_review"] is True
    assert event.selected_action.get("idle_self_test") is not True
    assert feedback_packet["formula_id"] == FORMULA_ID
    assert feedback_packet["feedback_kind"] == "self_test_success"
    assert feedback_packet["self_test_grasp"] > 0.68
    assert metric["teacher_off_readiness"] > review.tick_trace[0].feelings["idle_learning_review"]["teacher_off_readiness"]
    assert metric["scaffold_regression_need"] <= review.tick_trace[0].feelings["idle_learning_review"]["scaffold_regression_need"]
    assert feedback.reply_text == ""
    assert feedback_packet["writes_answer_directly"] is False
    assert feedback_packet["creates_reply_candidate"] is False


def test_phase20_9h_failed_self_test_raises_scaffold_pressure(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9h.sqlite"
    _review, self_test = _make_self_test_sequence(db_path, session_id="phase20-9h-failure")
    occurrence_id = self_test.tick_trace[0].ssp_active_summary["idle_narrative_flow"]["occurrence_id"]

    with sqlite3.connect(db_path) as conn:
        raw = conn.execute(
            "SELECT position_json FROM phase20_7_occurrences WHERE occurrence_id=?",
            (occurrence_id,),
        ).fetchone()[0]
        position = json.loads(str(raw))
        position["idle_self_test"]["self_test_grasp"] = 0.22
        position["idle_self_test"]["match_score"] = 0.18
        position["idle_self_test"]["recalled_text"] = "wrong recall"
        conn.execute(
            "UPDATE phase20_7_occurrences SET position_json=? WHERE occurrence_id=?",
            (json.dumps(position, ensure_ascii=False, sort_keys=True, separators=(",", ":")), occurrence_id),
        )
        conn.commit()

    feedback = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9h-failure",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    event = feedback.tick_trace[0]
    metric = event.feelings["idle_learning_review"]
    feedback_packet = metric["self_test_feedback"]

    assert event.selected_action["idle_learning_review"] is True
    assert event.selected_action.get("idle_self_test") is not True
    assert feedback_packet["formula_id"] == FORMULA_ID
    assert feedback_packet["feedback_kind"] == "self_test_failure"
    assert feedback_packet["mismatch_pressure"] > 0.7
    assert metric["scaffold_regression_need"] > 0.50
    assert metric["teacher_off_readiness"] < 0.60
    assert feedback.reply_text == ""
    assert feedback_packet["writes_answer_directly"] is False


def test_phase20_9h_stage_with_no_self_test_has_no_feedback_packet(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9h.sqlite"
    run_phase20_7_turn(
        user_text="phase20-9h-none cue",
        teacher_feedback=TeacherFeedback(feedback_text="phase20-9h-none reply", reward_mag=1.0),
        session_id="phase20-9h-none",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-9h-none",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    metric = idle.tick_trace[0].feelings["idle_learning_review"]

    assert metric["self_test_feedback"] == {}
    assert idle.reply_text == ""

