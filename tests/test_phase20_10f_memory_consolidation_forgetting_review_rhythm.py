from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_10f_memory_consolidation_forgetting_review_rhythm/v1"


def _teach_and_recall(db_path: Path, *, session_id: str, cue: str, reply: str) -> None:
    run_phase20_7_turn(
        user_text=cue,
        teacher_feedback=TeacherFeedback(feedback_text=reply, reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    run_phase20_7_turn(
        user_text=cue,
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )


def _run_until_cold_self_test(db_path: Path, *, session_id: str, limit: int = 28):
    for _ in range(limit):
        result = run_phase20_7_turn(
            user_text="",
            session_id=session_id,
            db_path=db_path,
            post_commit_idle_ticks=0,
            runtime_stage="stage6",
        )
        event = result.tick_trace[0]
        self_test = event.feelings.get("idle_self_test") if isinstance(event.feelings, dict) else {}
        if isinstance(self_test, dict) and self_test.get("self_test_kind") == "cold_retest_self_test":
            return result
    raise AssertionError("cold_retest_self_test was not produced")


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
    assert isinstance(progression, dict), "learning stage progression should be present"
    lifecycle = progression.get("learning_object_lifecycle")
    assert isinstance(lifecycle, dict), "learning object lifecycle should be present"
    return lifecycle


def _mutate_latest_cold_self_test_to_failure(db_path: Path, *, session_id: str) -> None:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT o.occurrence_id, o.position_json
            FROM phase20_7_occurrences o
            JOIN phase20_7_experience_events e ON e.event_id=o.event_id
            WHERE e.session_id=?
              AND o.sa_type_id LIKE 'short_structure_flow::self_test::%'
            ORDER BY o.tick DESC
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        assert row is not None, "self-test occurrence should exist"
        occurrence_id, raw_position = row
        position = json.loads(str(raw_position))
        self_test = position.setdefault("idle_self_test", {})
        assert self_test.get("self_test_kind") == "cold_retest_self_test"
        self_test["self_test_grasp"] = 0.16
        self_test["match_score"] = 0.10
        self_test["recalled_text"] = "wrong recall"
        conn.execute(
            "UPDATE phase20_7_occurrences SET position_json=? WHERE occurrence_id=?",
            (json.dumps(position, ensure_ascii=False, sort_keys=True, separators=(",", ":")), occurrence_id),
        )
        conn.commit()


def test_phase20_10f_cold_success_consolidates_memory_without_new_reply_path(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_10f_success.sqlite"
    session_id = "phase20-10f-success"
    _teach_and_recall(
        db_path,
        session_id=session_id,
        cue="phase20.10f success cue",
        reply="phase20.10f success reply",
    )
    _run_until_cold_self_test(db_path, session_id=session_id)

    result = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    lifecycle = _lifecycle_from_event(result.tick_trace[0])
    rhythm = lifecycle["memory_consolidation_forgetting_rhythm"]
    deltas = lifecycle["lifecycle_action_deltas"]

    assert rhythm["formula_id"] == FORMULA_ID
    assert rhythm["active"] is True
    assert rhythm["success_count"] >= 1
    assert rhythm["memory_consolidation"] > rhythm["forgetting_pressure"]
    assert rhythm["review_rhythm_pressure"] >= 0.0
    assert rhythm["action_deltas"]["commit_reply"] >= 0.0
    assert rhythm["action_deltas"]["request_teacher"] <= 0.0
    assert deltas["commit_reply"] > 0.0
    assert deltas["request_teacher"] < 0.0
    assert rhythm["uses_existing_ap_flow"] is True
    assert rhythm["projection_only"] is True
    assert rhythm["writes_answer_directly"] is False
    assert rhythm["creates_reply_candidate"] is False


def test_phase20_10f_cold_failure_raises_forgetting_review_and_reconsolidation_pressure(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_10f_failure.sqlite"
    session_id = "phase20-10f-failure"
    _teach_and_recall(
        db_path,
        session_id=session_id,
        cue="phase20.10f failure cue",
        reply="phase20.10f failure reply",
    )
    _run_until_cold_self_test(db_path, session_id=session_id)
    _mutate_latest_cold_self_test_to_failure(db_path, session_id=session_id)

    result = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    lifecycle = _lifecycle_from_event(result.tick_trace[0])
    rhythm = lifecycle["memory_consolidation_forgetting_rhythm"]
    deltas = lifecycle["lifecycle_action_deltas"]

    assert rhythm["formula_id"] == FORMULA_ID
    assert rhythm["active"] is True
    assert rhythm["failure_count"] >= 1
    assert rhythm["forgetting_pressure"] > 0.0
    assert rhythm["review_rhythm_pressure"] > 0.0
    assert rhythm["reconsolidation_need"] > 0.0
    assert rhythm["action_deltas"]["idle_think"] > 0.0
    assert rhythm["action_deltas"]["read_draft"] > 0.0
    assert rhythm["action_deltas"]["edit_cell"] > 0.0
    assert rhythm["action_deltas"]["request_teacher"] > 0.0
    assert deltas["idle_think"] > 0.0
    assert deltas["read_draft"] > 0.0
    assert deltas["edit_cell"] > 0.0
    assert deltas["request_teacher"] > 0.0
    assert rhythm["uses_existing_ap_flow"] is True
    assert rhythm["projection_only"] is True
    assert rhythm["writes_answer_directly"] is False
    assert rhythm["creates_reply_candidate"] is False
