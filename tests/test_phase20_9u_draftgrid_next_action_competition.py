from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9p_draftgrid_action_competition_from_ap_flow/v1"


def _events_with_action(result, action_type: str):
    return [event for event in result.tick_trace if event.selected_action.get("action_type") == action_type]


def _competition_row(event, action_type: str) -> dict:
    for row in event.action_competition:
        if row.get("action_type") == action_type:
            return dict(row)
    raise AssertionError(f"competition row not found: {action_type}")


def _next_selection_from_commit_event(event) -> dict:
    selection = event.selected_action.get("draftgrid_next_action_selection")
    assert isinstance(selection, dict)
    return selection


def test_phase20_9u_commit_happens_only_after_draftgrid_next_action_competition(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9u_commit.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9u commit competition prompt",
        teacher_feedback=TeacherFeedback(feedback_text="cat", reward_mag=1.0),
        session_id="phase20-9u-commit",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    result = run_phase20_7_turn(
        user_text="phase20.9u commit competition prompt",
        session_id="phase20-9u-commit",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    commit_event = _events_with_action(result, "commit_reply")[0]
    selection = _next_selection_from_commit_event(commit_event)
    rows = list(selection["candidate_rows"])
    by_action = {row["action_type"]: row for row in rows}

    assert selection["formula_id"] == FORMULA_ID
    assert selection["source"] == "draftgrid_existing_action_competition_after_self_readback"
    assert selection["selected_action_type"] == "commit_reply"
    assert by_action["commit_reply"]["eligible"] is True
    assert by_action["edit_cell"]["eligible"] is False
    assert by_action["continue_writing"]["eligible"] is False
    assert commit_event.selected_action["draftgrid_next_action_selection"]["selected_action_type"] == "commit_reply"

    commit_row = _competition_row(commit_event, "commit_reply")
    trace = commit_row["commit_reply_drive_from_ap_flow"]
    assert trace["selected_by_draftgrid_next_action"] is True
    assert trace["draftgrid_next_action_selection"]["selected_action_type"] == "commit_reply"
    assert result.committed is True
    assert result.reply_text == "cat"


def test_phase20_9u_edit_wins_before_commit_when_cstar_alternative_exists(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9u_edit_before_commit.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9u edit competition prompt",
        teacher_feedback=TeacherFeedback(feedback_text="cat", reward_mag=1.0),
        session_id="phase20-9u-edit",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    result = run_phase20_7_turn(
        user_text="phase20.9u edit competition prompt",
        session_id="phase20-9u-edit",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
        debug_draftgrid_write_mutation={0: "b"},
    )

    edit_event = _events_with_action(result, "edit_cell")[0]
    edit_selection = edit_event.selected_action["draftgrid_next_action_selection"]
    assert edit_selection["formula_id"] == FORMULA_ID
    assert edit_selection["selected_action_type"] == "edit_cell"
    assert any(row["action_type"] == "edit_cell" and row["eligible"] for row in edit_selection["candidate_rows"])

    commit_event = _events_with_action(result, "commit_reply")[0]
    commit_selection = _next_selection_from_commit_event(commit_event)
    assert commit_selection["selected_action_type"] == "commit_reply"
    assert result.reply_text == "cat"


def test_phase20_9u_stop_generating_can_win_without_committing_when_stop_drive_is_high(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9u_stop.sqlite"
    session_id = "phase20-9u-stop"
    run_phase20_7_turn(
        user_text="phase20.9u stop fatigue lesson",
        teacher_feedback=TeacherFeedback(feedback_text="cat", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    result = None
    for _index in range(24):
        result = run_phase20_7_turn(
            user_text="phase20.9u stop fatigue lesson",
            session_id=session_id,
            db_path=db_path,
            max_ticks=32,
            post_commit_idle_ticks=0,
            runtime_stage="stage6",
        )
        if _events_with_action(result, "stop_generating"):
            break
    assert result is not None

    stop_events = _events_with_action(result, "stop_generating")
    assert stop_events, "stop_generating should eventually win as fatigue accumulates (24 attempts)"
    stop_event = stop_events[0]
    selection = stop_event.selected_action["draftgrid_next_action_selection"]
    assert selection["selected_action_type"] == "stop_generating"
    assert any(row["action_type"] == "stop_generating" and row["eligible"] for row in selection["candidate_rows"])
    assert result.committed is False
    assert result.reply_text == ""
