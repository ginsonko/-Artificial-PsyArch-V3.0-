from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import list_active_unclosed_items, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_8n_request_teacher_unified_drive/v1"


def _selected_competition_row(result, action_type: str) -> dict:
    for event in result.tick_trace:
        if event.selected_action.get("action_type") == action_type:
            for row in event.action_competition:
                if row.get("action_type") == action_type and row.get("selected") is True:
                    return dict(row)
    raise AssertionError(f"selected action row not found: {action_type}")


def _first_event_with_action(result, action_type: str):
    for event in result.tick_trace:
        if event.selected_action.get("action_type") == action_type:
            return event
    raise AssertionError(f"event not found: {action_type}")


def _drive_before_cstar(row: dict) -> float:
    return row.get("drive_before_cstar_carryover", row["drive"])


def _drive_after_learning_loop(row: dict, base_drive: float) -> float:
    return round(base_drive + row.get("learning_loop_carryover_delta", 0.0), 4)


def test_phase20_8n_unknown_request_teacher_uses_unified_drive_context(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8n.sqlite"
    result = run_phase20_7_turn(
        user_text="phase20n unknown question",
        session_id="phase20-8n-request",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _first_event_with_action(result, "request_teacher")
    row = _selected_competition_row(result, "request_teacher")
    context = row["teacher_request_drive_context"]
    active = list_active_unclosed_items(db_path)

    assert context["formula_id"] == FORMULA_ID
    assert context["intent"] == "request_teacher"
    assert context["low_grasp"] > 0.0
    assert _drive_before_cstar(row) == _drive_after_learning_loop(row, context["request_drive"])
    assert row["drive"] >= context["request_drive"]
    assert event.feelings["source"] == "unified_teacher_request_drive"
    assert event.feelings["teacher_request_drive_context"] == context
    assert active
    assert active[0]["reason"]["teacher_request_drive_context"]["formula_id"] == FORMULA_ID
    assert not event.b_candidates
    assert context["creates_reply_candidate"] is False
    assert context["writes_answer_directly"] is False


def test_phase20_8n_repeated_unknown_maintains_unclosed_from_same_drive_context(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8n.sqlite"
    run_phase20_7_turn(
        user_text="phase20n repeated unknown",
        session_id="phase20-8n-repeat-a",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    second = run_phase20_7_turn(
        user_text="phase20n repeated unknown",
        session_id="phase20-8n-repeat-b",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _first_event_with_action(second, "maintain_unclosed")
    row = _selected_competition_row(second, "maintain_unclosed")
    context = row["teacher_request_drive_context"]

    assert context["formula_id"] == FORMULA_ID
    assert context["intent"] == "maintain_unclosed"
    assert context["unclosed_pull"] > 0.0
    assert _drive_before_cstar(row) == _drive_after_learning_loop(row, context["maintain_drive"])
    assert row["drive"] >= context["maintain_drive"]
    assert event.feelings["source"] == "unified_unclosed_request_drive"
    assert event.feelings["teacher_request_drive_context"] == context
    assert not event.b_candidates


def test_phase20_8n_short_structure_flow_support_can_join_request_drive(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8n.sqlite"
    run_phase20_7_turn(
        user_text="phase20n flow seed",
        session_id="phase20-8n-flow",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="",
        session_id="phase20-8n-flow",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    result = run_phase20_7_turn(
        user_text="phase20n another unknown",
        session_id="phase20-8n-flow",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    row = _selected_competition_row(result, "request_teacher")
    context = row["teacher_request_drive_context"]

    assert context["formula_id"] == FORMULA_ID
    assert context["short_structure_flow_support"] > 0.0
    assert "short_structure_flow_next" in context["source_kinds"]


def test_phase20_8n_stage0_has_no_teacher_request_drive_context(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20n boundary",
        session_id="phase20-8n-stage0",
        db_path=tmp_path / "phase20_8n.sqlite",
        runtime_stage="stage0",
    )

    event = result.tick_trace[0]
    assert result.stage_id == "20.7-stage0"
    assert event.no_write_reason == "stage0_does_not_write_experience_events"
    assert not any("teacher_request_drive_context" in row for row in event.action_competition)
