from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_10d_long_interval_cold_retest_window/v1"


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


def _teach(db_path: Path, *, session_id: str, cue: str, reply: str) -> None:
    run_phase20_7_turn(
        user_text=cue,
        teacher_feedback=TeacherFeedback(feedback_text=reply, reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text=cue,
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )


def test_phase20_10d_long_interval_reselects_older_learning_object_for_cold_retest(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_10d_long_interval.sqlite"
    session_id = "phase20-10d-long-interval"
    old_cue = "phase20.10d old cue"
    old_reply = "phase20.10d old reply"
    fresh_cue = "phase20.10d fresh cue"
    fresh_reply = "phase20.10d fresh reply"
    _teach(db_path, session_id=session_id, cue=old_cue, reply=old_reply)

    for _ in range(4):
        run_phase20_7_turn(
            user_text="",
            session_id=session_id,
            db_path=db_path,
            post_commit_idle_ticks=0,
            runtime_stage="stage4",
        )

    _teach(db_path, session_id=session_id, cue=fresh_cue, reply=fresh_reply)

    cold_review = None
    cold_self_test = None
    for _ in range(14):
        result = run_phase20_7_turn(
            user_text="",
            session_id=session_id,
            db_path=db_path,
            post_commit_idle_ticks=0,
            runtime_stage="stage4",
        )
        event = result.tick_trace[0]
        review = event.feelings.get("idle_learning_review") if isinstance(event.feelings, dict) else {}
        self_test = event.feelings.get("idle_self_test") if isinstance(event.feelings, dict) else {}
        if isinstance(review, dict) and review.get("source_text") == old_cue and review.get("evidence", {}).get("long_interval_cold_retest"):
            cold_review = event
        if isinstance(self_test, dict) and self_test.get("source_text") == old_cue and self_test.get("self_test_kind") == "cold_retest_self_test":
            cold_self_test = event
            break

    assert cold_review is not None
    assert cold_self_test is not None
    self_test = cold_self_test.feelings["idle_self_test"]
    long_interval = self_test["long_interval_cold_retest"]

    assert self_test["formula_id"] == "apv3_phase20_9g_idle_self_test/v1"
    assert long_interval["formula_id"] == FORMULA_ID
    assert long_interval["score"] >= 0.20
    assert long_interval["alignment_age_ticks"] >= 8
    assert self_test["expected_text"] == old_reply
    assert self_test["recalled_text"] == old_reply
    assert self_test["writes_answer_directly"] is False
    assert self_test["creates_reply_candidate"] is False


def test_phase20_10d_lifecycle_exposes_cold_window_without_new_reply_path(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_10d_lifecycle.sqlite"
    session_id = "phase20-10d-lifecycle"
    cue = "phase20.10d lifecycle cue"
    reply = "phase20.10d lifecycle reply"
    _teach(db_path, session_id=session_id, cue=cue, reply=reply)

    lifecycle = {}
    for _ in range(14):
        result = run_phase20_7_turn(
            user_text="",
            session_id=session_id,
            db_path=db_path,
            post_commit_idle_ticks=0,
            runtime_stage="stage4",
        )
        event = result.tick_trace[0]
        candidate = _lifecycle_from_event(event)
        window = candidate.get("long_interval_cold_retest_window")
        if isinstance(window, dict) and window.get("active"):
            lifecycle = candidate
            break

    assert lifecycle
    window = lifecycle["long_interval_cold_retest_window"]
    assert window["formula_id"] == FORMULA_ID
    assert window["active"] is True
    assert window["alignment_age_ticks"] >= 8
    assert window["retest_need"] > 0.0
    assert lifecycle["current_lifecycle_stage"] in {"adjusted_after_feedback", "retested", "teacher_exit_ready", "cold_retest_ready"}
    assert lifecycle["cold_retest_pressure"] >= window["retest_need"] * 0.20
    assert lifecycle["lifecycle_action_deltas"]["idle_think"] > 0.0
    assert window["uses_existing_ap_flow"] is True
    assert window["projection_only"] is True
    assert window["writes_answer_directly"] is False
    assert window["creates_reply_candidate"] is False
