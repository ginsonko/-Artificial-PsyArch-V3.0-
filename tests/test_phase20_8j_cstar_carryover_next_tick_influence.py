from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


def _support_terms(event) -> dict:
    if not event.b_candidates:
        return {}
    terms = event.b_candidates[0].get("support_terms", {})
    return dict(terms) if isinstance(terms, dict) else {}


def _carryover(event) -> dict:
    value = event.feelings.get("cstar_statepool_carryover", {})
    return dict(value) if isinstance(value, dict) else {}


def test_phase20_8j_cstar_feedback_modulates_b_support_then_next_tick_cstar(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "phase20_8j.sqlite"
    run_phase20_7_turn(
        user_text="phase20j hello",
        teacher_feedback=TeacherFeedback(feedback_text="phase20j reply", reward_mag=1.0),
        session_id="phase20-8j-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    result = run_phase20_7_turn(
        user_text="phase20j hello",
        session_id="phase20-8j-query",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )

    exact_ticks = [
        event for event in result.tick_trace if event.b_candidates and event.b_candidates[0].get("kind") == "exact_b0"
    ]
    assert exact_ticks
    assert _support_terms(exact_ticks[0]).get("statepool_cstar_observation_bias", 0.0) > 0.0

    next_tick_events = [
        event for event in result.tick_trace if _carryover(event).get("prediction_unit_count", 0) > 0
    ]
    assert next_tick_events
    event = next_tick_events[0]
    assert any(row.get("kind") == "statepool_virtual_prediction_carryover" for row in event.c_forward)
    assert any(row.get("kind") == "statepool_virtual_pressure_carryover" for row in event.c_backward)
    assert event.cstar_packet["cstar_min_error_integration"]["forward_support"] > 0.0
    selected_rows = [row for row in event.action_competition if row.get("selected")]
    assert selected_rows
    assert any(float(row.get("cstar_carryover_drive_delta", 0.0) or 0.0) > 0.0 for row in selected_rows)
    assert float(event.selected_action.get("cstar_carryover_drive_delta", 0.0) or 0.0) > 0.0


def test_phase20_8j_structural_b_support_records_statepool_observation_bias(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "phase20_8j.sqlite"
    run_phase20_7_turn(
        user_text="phase20j structural source",
        teacher_feedback=TeacherFeedback(feedback_text="phase20j structural reply", reward_mag=1.0),
        session_id="phase20-8j-structural-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    result = run_phase20_7_turn(
        user_text="phase20j structural source!",
        session_id="phase20-8j-structural-query",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    structural_ticks = [
        event for event in result.tick_trace if event.b_candidates and event.b_candidates[0].get("kind") == "structural_b"
    ]
    assert structural_ticks
    terms = _support_terms(structural_ticks[0])
    assert terms.get("statepool_cstar_observation_bias", 0.0) > 0.0
    assert structural_ticks[0].b_candidates[0].get("support", 0.0) >= terms["structural_sequence_fit"]


def test_phase20_8j_unknown_tick_uses_carryover_without_fake_b(
    tmp_path: Path,
) -> None:
    result = run_phase20_7_turn(
        user_text="phase20j unknown input",
        session_id="phase20-8j-unknown",
        db_path=tmp_path / "phase20_8j.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    assert not any(event.b_candidates for event in result.tick_trace)
    assert any(_carryover(event).get("active") for event in result.tick_trace[1:])
    for event in result.tick_trace:
        trace = event.feelings.get("cstar_statepool_feedback")
        if isinstance(trace, dict):
            assert trace.get("creates_reply_candidate") is False
            assert trace.get("writes_answer_directly") is False


def test_phase20_8j_stage0_has_no_carryover_completion(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20j boundary",
        session_id="phase20-8j-stage0",
        db_path=tmp_path / "phase20_8j.sqlite",
        runtime_stage="stage0",
    )

    event = result.tick_trace[0]
    assert result.stage_id == "20.7-stage0"
    assert event.no_write_reason == "stage0_does_not_write_experience_events"
    assert "cstar_statepool_carryover" not in event.feelings

