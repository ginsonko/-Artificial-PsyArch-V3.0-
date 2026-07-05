from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.cognitive_cycle import CSTAR_MIN_ERROR_FORMULA_ID
from apv3test.runtime.phase20_7.experience_candidate import UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID


def _cognitive_packets(result) -> list[dict]:
    return [event.cstar_packet for event in result.tick_trace if event.cstar_packet]


def _assert_integrated_cstar(packet: dict) -> None:
    assert packet["cstar_formula_id"] == CSTAR_MIN_ERROR_FORMULA_ID
    assert packet["cstar_model"] == "phase20_8h_unified_min_error_integration/v1"
    assert packet["completed_by"] == "phase20_8h_unified_cstar_min_error"
    integration = packet["cstar_min_error_integration"]
    assert integration["formula_id"] == CSTAR_MIN_ERROR_FORMULA_ID
    assert 0.0 <= integration["e_total"] <= 1.0
    assert 0.0 <= packet["grasp"] <= 1.0
    assert packet["grasp"] == integration["grasp"]
    assert packet["e_total"] == integration["e_total"]
    assert packet["writes_answer_directly"] is False
    assert integration["writes_answer_directly"] is False
    assert "unified_candidate_statistics" in packet
    assert "alpha_forward" in packet
    assert "alpha_backward" in packet
    assert "cstar_virtual_energy" in packet


def test_phase20_8h_exact_b0_tick_uses_unified_cstar_min_error_formula(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8h.sqlite"
    run_phase20_7_turn(
        user_text="phase20h hello",
        teacher_feedback=TeacherFeedback(feedback_text="phase20h hi", reward_mag=1.0),
        session_id="phase20-8h-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    result = run_phase20_7_turn(
        user_text="phase20h hello",
        session_id="phase20-8h-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )

    exact_ticks = [
        event for event in result.tick_trace if event.b_candidates and event.b_candidates[0].get("kind") == "exact_b0"
    ]
    assert exact_ticks
    packet = exact_ticks[0].cstar_packet
    _assert_integrated_cstar(packet)
    assert packet["unified_candidate_statistics"]["candidate_count"] >= 1
    assert UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID in packet["unified_candidate_statistics"]["support_formulas"]
    assert packet["cstar_min_error_integration"]["backward_grasp"] > 0.0


def test_phase20_8h_structural_b_keeps_candidate_support_and_gets_unified_cstar(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "phase20_8h.sqlite"
    run_phase20_7_turn(
        user_text="phase20h structural source",
        teacher_feedback=TeacherFeedback(feedback_text="phase20h structural reply", reward_mag=1.0),
        session_id="phase20-8h-structural-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    result = run_phase20_7_turn(
        user_text="phase20h structural source!",
        session_id="phase20-8h-structural-query",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    structural_ticks = [
        event for event in result.tick_trace if event.b_candidates and event.b_candidates[0].get("kind") == "structural_b"
    ]
    assert structural_ticks
    packet = structural_ticks[0].cstar_packet
    _assert_integrated_cstar(packet)
    assert packet["kind"] == "bccstar_stage3_packet"
    assert packet["support_formula"] == UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID
    assert packet["unified_candidate_statistics"]["candidate_count"] >= 1
    assert packet["cstar_min_error_integration"]["forward_support"] > 0.0
    assert packet["cstar_min_error_integration"]["backward_grasp"] > 0.0


def test_phase20_8h_unknown_weak_tick_has_cstar_error_without_fake_b(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20h unknown input",
        session_id="phase20-8h-unknown",
        db_path=tmp_path / "phase20_8h.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    assert not any(event.b_candidates for event in result.tick_trace)
    packets = _cognitive_packets(result)
    assert packets
    for packet in packets:
        _assert_integrated_cstar(packet)
        assert set(packet["unified_candidate_statistics"]["candidate_kinds"]).issubset({"short_structure_flow_next"})
        assert packet["cstar_min_error_integration"]["e_b"] < 1.0
        assert packet["cstar_min_error_integration"]["e_total"] > 0.0


def test_phase20_8h_stage0_still_has_no_cstar_completion(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20h boundary",
        session_id="phase20-8h-stage0",
        db_path=tmp_path / "phase20_8h.sqlite",
        runtime_stage="stage0",
    )

    assert result.stage_id == "20.7-stage0"
    event = result.tick_trace[0]
    assert event.no_write_reason == "stage0_does_not_write_experience_events"
    assert not event.cstar_packet
