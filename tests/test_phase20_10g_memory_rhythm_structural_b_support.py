from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_10g_memory_rhythm_structural_b_support/v1"


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


def _first_structural_b(result) -> dict:
    for event in result.tick_trace:
        for candidate in event.b_candidates:
            if candidate.get("kind") == "structural_b":
                return dict(candidate)
    raise AssertionError("structural_b candidate not found")


def _memory_support_from_structural_b(candidate: dict) -> dict:
    for slot in candidate.get("candidate_audit_slots", ()):
        if isinstance(slot, dict) and isinstance(slot.get("memory_rhythm_structural_b_support"), dict):
            return dict(slot["memory_rhythm_structural_b_support"])
    raise AssertionError("memory rhythm structural B support slot not found")


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
        self_test["self_test_grasp"] = 0.14
        self_test["match_score"] = 0.10
        self_test["recalled_text"] = "wrong recall"
        conn.execute(
            "UPDATE phase20_7_occurrences SET position_json=? WHERE occurrence_id=?",
            (json.dumps(position, ensure_ascii=False, sort_keys=True, separators=(",", ":")), occurrence_id),
        )
        conn.commit()


def test_phase20_10g_consolidated_memory_relieves_structural_b_support_without_reply_route(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_10g_success.sqlite"
    session_id = "phase20-10g-success"
    cue = "phase20.10g consolidated cue alpha"
    partial = "10g consolidated cue alpha"
    reply = "phase20.10g consolidated reply"
    _teach_and_recall(db_path, session_id=session_id, cue=cue, reply=reply)
    _run_until_cold_self_test(db_path, session_id=session_id)

    result = run_phase20_7_turn(
        user_text=partial,
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    b = _first_structural_b(result)
    memory_support = _memory_support_from_structural_b(b)

    assert memory_support["formula_id"] == FORMULA_ID
    assert memory_support["active"] is True
    assert memory_support["memory_consolidation"] > memory_support["forgetting_pressure"]
    assert memory_support["memory_rhythm_support_boost"] > 0.0
    assert memory_support["memory_rhythm_guard_penalty"] == 0.0
    assert b["support_terms"]["memory_rhythm_support_boost"] > 0.0
    assert b["support_terms"]["memory_rhythm_guard_penalty"] == 0.0
    assert b["candidate_audit_slots"][1]["acceptance_threshold_terms"]["memory_rhythm_relief"] < 0.0
    assert memory_support["uses_existing_ap_flow"] is True
    assert memory_support["projection_only"] is True
    assert memory_support["writes_answer_directly"] is False
    assert memory_support["creates_reply_candidate"] is False


def test_phase20_10g_forgetting_pressure_guards_structural_b_generalization_without_fake_answer(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_10g_failure.sqlite"
    session_id = "phase20-10g-failure"
    cue = "phase20.10g forgetting cue beta"
    partial = "10g forgetting cue beta"
    reply = "phase20.10g forgetting reply"
    _teach_and_recall(db_path, session_id=session_id, cue=cue, reply=reply)
    _run_until_cold_self_test(db_path, session_id=session_id)
    _mutate_latest_cold_self_test_to_failure(db_path, session_id=session_id)

    result = run_phase20_7_turn(
        user_text=partial,
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    b = _first_structural_b(result)
    memory_support = _memory_support_from_structural_b(b)

    assert memory_support["formula_id"] == FORMULA_ID
    assert memory_support["active"] is True
    assert memory_support["forgetting_pressure"] > 0.0
    assert memory_support["review_rhythm_pressure"] > 0.0
    assert memory_support["reconsolidation_need"] > 0.0
    assert memory_support["memory_rhythm_guard_penalty"] > 0.0
    assert b["support_terms"]["memory_rhythm_guard_penalty"] < 0.0
    assert b["candidate_audit_slots"][1]["acceptance_threshold_terms"]["memory_rhythm_guard"] > 0.0
    assert any(
        slot.get("memory_rhythm_guard_penalty", 0.0) > 0.0 and slot.get("writes_answer_directly") is False
        for slot in b["candidate_audit_slots"]
        if isinstance(slot, dict)
    )
    assert memory_support["uses_existing_ap_flow"] is True
    assert memory_support["projection_only"] is True
    assert memory_support["writes_answer_directly"] is False
    assert memory_support["creates_reply_candidate"] is False
