from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9s_edit_outcome_learning_carryover/v1"


def _event_with_action(result, action_type: str):
    for event in result.tick_trace:
        if event.selected_action.get("action_type") == action_type:
            return event
    raise AssertionError(f"event not found: {action_type}")


def _competition_row(event, action_type: str) -> dict:
    for row in event.action_competition:
        if row.get("action_type") == action_type:
            return dict(row)
    raise AssertionError(f"competition row not found: {action_type}")


def _edit_delta(event) -> dict:
    for delta in event.learning_deltas:
        if isinstance(delta, dict) and delta.get("delta_kind") == "draftgrid_edit_outcome_learning":
            return dict(delta)
    raise AssertionError("edit outcome learning delta not found")


def _edit_outcome_carryover(row: dict) -> dict:
    carryover = row.get("learning_loop_carryover", {})
    if carryover.get("formula_id") == FORMULA_ID:
        return dict(carryover)
    nested = carryover.get("edit_outcome_carryover", {})
    assert nested.get("formula_id") == FORMULA_ID
    return dict(nested)


def test_phase20_9s_edit_success_modulates_commit_and_readback_actions(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9s.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9s edit prompt",
        teacher_feedback=TeacherFeedback(feedback_text="猫好", reward_mag=1.0),
        session_id="phase20-9s",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    result = run_phase20_7_turn(
        user_text="phase20.9s edit prompt",
        session_id="phase20-9s",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
        debug_draftgrid_write_mutation={0: "狗"},
    )

    edit_event = _event_with_action(result, "edit_cell")
    commit_event = _event_with_action(result, "commit_reply")
    delta = _edit_delta(edit_event)

    assert delta["formula_id"] == FORMULA_ID
    assert delta["fit_after"] > delta["fit_before"]
    assert delta["fit_improvement"] > 0.0
    assert delta["edit_success"] > 0.0
    assert delta["writes_answer_directly"] is False
    assert edit_event.draft_grid["visible_text"] == "猫好"

    commit_row = _competition_row(commit_event, "commit_reply")
    read_row = _competition_row(commit_event, "read_draft")
    edit_row = _competition_row(commit_event, "edit_cell")

    carryover = _edit_outcome_carryover(commit_row)
    assert carryover["formula_id"] == FORMULA_ID
    assert carryover["commit_reply_delta"] > 0.0
    assert commit_row.get("learning_loop_carryover_delta", 0.0) > 0.0
    assert read_row.get("learning_loop_carryover", {}).get("edit_outcome_carryover", carryover)["formula_id"] == FORMULA_ID
    assert edit_row.get("learning_loop_carryover", {}).get("edit_outcome_carryover", carryover)["formula_id"] == FORMULA_ID
    assert commit_event.draft_grid["visible_text"] == "猫好"
    assert result.reply_text == "猫好"
