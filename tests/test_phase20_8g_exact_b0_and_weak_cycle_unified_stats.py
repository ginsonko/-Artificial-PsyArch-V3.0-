from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.experience_candidate import UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID


def test_phase20_8g_exact_b0_index_hit_returns_through_unified_candidate(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8g.sqlite"
    run_phase20_7_turn(
        user_text="phase20g hello",
        teacher_feedback=TeacherFeedback(feedback_text="phase20g hi", reward_mag=1.0),
        session_id="phase20-8g-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    result = run_phase20_7_turn(
        user_text="phase20g hello",
        session_id="phase20-8g-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )

    assert result.reply_text == "phase20g hi"
    exact_ticks = [
        tick for tick in result.tick_trace if tick.b_candidates and tick.b_candidates[0].get("kind") == "exact_b0"
    ]
    assert exact_ticks
    exact_candidate = exact_ticks[0].b_candidates[0]
    assert exact_candidate["support_formula"] == UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID
    assert exact_candidate["support_terms"]["exact_b0_index_support"] > 0.0
    assert exact_candidate["support_terms"]["unified_candidate_support"] > 0.0
    assert any(
        slot.get("slot_kind") == "unified_experience_candidate"
        for slot in exact_candidate["candidate_audit_slots"]
    )
    stats = exact_ticks[0].cstar_packet["unified_candidate_statistics"]
    assert stats["candidate_count"] >= 1
    assert UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID in stats["support_formulas"]


def test_phase20_8g_weak_b_and_default_cstar_expose_empty_unified_statistics_without_fake_b(
    tmp_path: Path,
) -> None:
    result = run_phase20_7_turn(
        user_text="phase20g unknown input",
        session_id="phase20-8g-unknown",
        db_path=tmp_path / "phase20_8g.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    assert not any(event.b_candidates for event in result.tick_trace)
    cycle_events = [event for event in result.tick_trace if event.cstar_packet]
    assert cycle_events
    for event in cycle_events:
        evidence_stats = event.cstar_packet["tick_evidence_b"]["unified_candidate_statistics"]
        cstar_stats = event.cstar_packet["unified_candidate_statistics"]
        assert set(evidence_stats["candidate_kinds"]).issubset({"short_structure_flow_next"})
        assert set(cstar_stats["candidate_kinds"]).issubset({"short_structure_flow_next"})
        assert evidence_stats["creates_candidate"] is False
        assert cstar_stats["creates_candidate"] is False
        assert any(
            slot.get("slot_kind") == "unified_candidate_statistics"
            for row in event.c_backward
            for slot in row.get("cause_slots", ())
            if isinstance(slot, dict)
        )


def test_phase20_8g_stage0_boundary_still_has_no_cognitive_completion(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20g boundary",
        session_id="phase20-8g-stage0",
        db_path=tmp_path / "phase20_8g.sqlite",
        runtime_stage="stage0",
    )

    assert result.stage_id == "20.7-stage0"
    event = result.tick_trace[0]
    assert event.no_write_reason == "stage0_does_not_write_experience_events"
    assert not event.c_forward
    assert not event.c_backward
    assert not event.cstar_packet
