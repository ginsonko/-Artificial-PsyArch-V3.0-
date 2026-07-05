from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_10e_cold_retest_generalization_confidence_tuning/v1"


def _u(value: str) -> str:
    return value.encode("unicode_escape").decode("ascii")


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


def _run_until_cold_self_test(db_path: Path, *, session_id: str, limit: int = 24):
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


def _first_structural_b(result) -> dict:
    for event in result.tick_trace:
        for candidate in event.b_candidates:
            if candidate.get("kind") == "structural_b":
                return dict(candidate)
    raise AssertionError("structural_b candidate not found")


def _cold_tuning_from_structural_b(candidate: dict) -> dict:
    for slot in candidate.get("candidate_audit_slots", ()):
        if isinstance(slot, dict) and isinstance(slot.get("cold_retest_generalization_tuning"), dict):
            return dict(slot["cold_retest_generalization_tuning"])
    raise AssertionError("cold retest generalization tuning not found")


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
        self_test["self_test_grasp"] = 0.18
        self_test["match_score"] = 0.12
        self_test["recalled_text"] = "wrong recall"
        conn.execute(
            "UPDATE phase20_7_occurrences SET position_json=? WHERE occurrence_id=?",
            (json.dumps(position, ensure_ascii=False, sort_keys=True, separators=(",", ":")), occurrence_id),
        )
        conn.commit()


def test_phase20_10e_cold_success_makes_similar_recall_bolder_without_direct_reply_path(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_10e_success.sqlite"
    session_id = "phase20-10e-success"
    cue = "\u6ca1\u9519,\u4f60\u597d\u806a\u660e"
    partial = "\u4f60\u597d\u806a\u660e"
    reply = "\u8c22\u8c22"
    _teach_and_recall(db_path, session_id=session_id, cue=cue, reply=reply)
    _run_until_cold_self_test(db_path, session_id=session_id)

    lifecycle_result = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    lifecycle = _lifecycle_from_event(lifecycle_result.tick_trace[0])
    lifecycle_tuning = lifecycle["cold_retest_generalization_tuning"]

    assert lifecycle_tuning["formula_id"] == FORMULA_ID
    assert lifecycle_tuning["active"] is True
    assert lifecycle_tuning["cold_success_count"] >= 1
    assert lifecycle_tuning["generalization_courage"] > lifecycle_tuning["generalization_caution"]
    assert lifecycle_tuning["action_deltas"]["commit_reply"] > 0.0
    assert lifecycle_tuning["action_deltas"]["request_teacher"] < 0.0
    assert lifecycle_tuning["writes_answer_directly"] is False
    assert lifecycle_tuning["creates_reply_candidate"] is False

    result = run_phase20_7_turn(
        user_text=partial,
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    b = _first_structural_b(result)
    tuning = _cold_tuning_from_structural_b(b)

    assert _u(result.reply_text) == _u(reply)
    assert tuning["formula_id"] == FORMULA_ID
    assert tuning["active"] is True
    assert tuning["cold_success_count"] >= 1
    assert tuning["generalization_courage"] > 0.0
    assert tuning["generalization_caution"] == 0.0
    assert b["support_terms"]["cold_retest_generalization_boost"] > 0.0
    assert b["support_terms"]["cold_retest_caution_penalty"] == 0.0
    assert any(
        slot.get("cold_generalization_boost", 0.0) > 0.0 and slot.get("writes_answer_directly") is False
        for slot in b["candidate_audit_slots"]
        if isinstance(slot, dict)
    )


def test_phase20_10e_cold_failure_increases_review_request_and_revision_pressure(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_10e_failure.sqlite"
    session_id = "phase20-10e-failure"
    cue = "phase20.10e fail old cue"
    partial = "phase20.10e fail cue"
    reply = "phase20.10e fail old reply"
    _teach_and_recall(db_path, session_id=session_id, cue=cue, reply=reply)
    _run_until_cold_self_test(db_path, session_id=session_id)
    _mutate_latest_cold_self_test_to_failure(db_path, session_id=session_id)

    lifecycle_result = run_phase20_7_turn(
        user_text="",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    lifecycle = _lifecycle_from_event(lifecycle_result.tick_trace[0])
    lifecycle_tuning = lifecycle["cold_retest_generalization_tuning"]
    lifecycle_deltas = lifecycle["lifecycle_action_deltas"]

    assert lifecycle_tuning["formula_id"] == FORMULA_ID
    assert lifecycle_tuning["active"] is True
    assert lifecycle_tuning["cold_failure_count"] >= 1
    assert lifecycle_tuning["generalization_caution"] > lifecycle_tuning["generalization_courage"]
    assert lifecycle_tuning["action_deltas"]["request_teacher"] > 0.0
    assert lifecycle_tuning["action_deltas"]["read_draft"] > 0.0
    assert lifecycle_tuning["action_deltas"]["edit_cell"] > 0.0
    assert lifecycle_tuning["action_deltas"]["commit_reply"] < 0.0
    assert lifecycle_deltas["request_teacher"] > 0.0
    assert lifecycle_deltas["read_draft"] > 0.0
    assert lifecycle_deltas["edit_cell"] > 0.0
    assert lifecycle_deltas["commit_reply"] < 0.0
    assert lifecycle_tuning["writes_answer_directly"] is False
    assert lifecycle_tuning["creates_reply_candidate"] is False

    result = run_phase20_7_turn(
        user_text=partial,
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    b = _first_structural_b(result)
    tuning = _cold_tuning_from_structural_b(b)

    assert tuning["cold_failure_count"] >= 1
    assert tuning["generalization_caution"] > 0.0
    assert tuning["generalization_courage"] == 0.0
    assert b["support_terms"]["cold_retest_caution_penalty"] < 0.0
    assert any(
        slot.get("cold_caution_penalty", 0.0) > 0.0 and slot.get("creates_reply_candidate") is False
        for slot in b["candidate_audit_slots"]
        if isinstance(slot, dict)
    )
