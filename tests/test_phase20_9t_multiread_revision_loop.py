from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


EDIT_FORMULA_ID = "apv3_phase20_9r_cstar_alternative_unit_edit_cell/v1"
EDIT_OUTCOME_FORMULA_ID = "apv3_phase20_9s_edit_outcome_learning_carryover/v1"


def _actions(result) -> list[str]:
    return [str(event.selected_action.get("action_type") or "") for event in result.tick_trace]


def _events_with_action(result, action_type: str):
    return [event for event in result.tick_trace if event.selected_action.get("action_type") == action_type]


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


def test_phase20_9t_edit_is_followed_by_second_readback_before_commit(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9t_second_read.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9t edit prompt",
        teacher_feedback=TeacherFeedback(feedback_text="cat", reward_mag=1.0),
        session_id="phase20-9t-second-read",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    result = run_phase20_7_turn(
        user_text="phase20.9t edit prompt",
        session_id="phase20-9t-second-read",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
        debug_draftgrid_write_mutation={0: "b"},
    )

    actions = _actions(result)
    read_events = _events_with_action(result, "read_draft")
    edit_events = _events_with_action(result, "edit_cell")
    commit_events = _events_with_action(result, "commit_reply")

    assert len(read_events) >= 2
    assert len(edit_events) == 1
    assert len(commit_events) == 1
    assert actions.index("read_draft") < actions.index("edit_cell")
    assert actions.index("edit_cell") < actions.index("commit_reply")
    assert actions[actions.index("edit_cell") + 1] == "read_draft"

    edit_event = edit_events[0]
    second_read = read_events[1]
    commit_event = commit_events[0]

    assert edit_event.draft_grid["visible_text"] == "cat"
    assert second_read.draft_grid["visible_text"] == "cat"
    assert second_read.ssp_active_summary["draftgrid_readback_self_flow"]["writes_answer_directly"] is False
    assert commit_event.draft_grid["visible_text"] == "cat"
    assert result.reply_text == "cat"

    edit_row = _competition_row(edit_event, "edit_cell")
    edit_trace = edit_row["draftgrid_action_from_ap_flow"]["edit_cell"]["cstar_alternative_unit"]
    assert edit_trace["formula_id"] == EDIT_FORMULA_ID
    assert edit_trace["old_unit"] == "b"
    assert edit_trace["alternative_unit"] == "c"

    commit_row = _competition_row(commit_event, "commit_reply")
    carryover = commit_row.get("learning_loop_carryover", {})
    nested = carryover.get("edit_outcome_carryover", carryover)
    assert nested["formula_id"] == EDIT_OUTCOME_FORMULA_ID


def test_phase20_9t_two_wrong_cells_need_two_read_edit_passes(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9t_two_edits.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9t two edit prompt",
        teacher_feedback=TeacherFeedback(feedback_text="cat", reward_mag=1.0),
        session_id="phase20-9t-two-edit",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    result = run_phase20_7_turn(
        user_text="phase20.9t two edit prompt",
        session_id="phase20-9t-two-edit",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
        debug_draftgrid_write_mutation={0: "b", 1: "o"},
    )

    actions = _actions(result)
    read_events = _events_with_action(result, "read_draft")
    edit_events = _events_with_action(result, "edit_cell")

    assert len(read_events) >= 3
    assert len(edit_events) == 2
    assert actions.count("edit_cell") == 2
    assert actions.index("edit_cell") < actions.index("commit_reply")
    assert read_events[0].draft_grid["visible_text"] == "bot"
    assert read_events[1].draft_grid["visible_text"] == "cot"
    assert read_events[2].draft_grid["visible_text"] == "cat"

    first_delta = _edit_delta(edit_events[0])
    second_delta = _edit_delta(edit_events[1])
    assert first_delta["formula_id"] == EDIT_OUTCOME_FORMULA_ID
    assert second_delta["formula_id"] == EDIT_OUTCOME_FORMULA_ID
    assert first_delta["fit_after"] > first_delta["fit_before"]
    assert second_delta["fit_after"] > second_delta["fit_before"]
    assert result.reply_text == "cat"


def test_phase20_9t_matching_readback_does_not_create_fake_extra_loop(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9t_no_fake_loop.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9t no fake loop prompt",
        teacher_feedback=TeacherFeedback(feedback_text="cat", reward_mag=1.0),
        session_id="phase20-9t-no-fake-loop",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    result = run_phase20_7_turn(
        user_text="phase20.9t no fake loop prompt",
        session_id="phase20-9t-no-fake-loop",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    read_events = _events_with_action(result, "read_draft")
    edit_events = _events_with_action(result, "edit_cell")
    commit_events = _events_with_action(result, "commit_reply")

    assert len(read_events) == 1
    assert len(edit_events) == 0
    assert len(commit_events) == 1
    assert read_events[0].draft_grid["visible_text"] == "cat"
    assert commit_events[0].draft_grid["visible_text"] == "cat"
    assert result.reply_text == "cat"
