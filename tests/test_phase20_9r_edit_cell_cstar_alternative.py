from __future__ import annotations

from pathlib import Path

import sqlite3

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.experience_log import from_json


FORMULA_ID = "apv3_phase20_9r_cstar_alternative_unit_edit_cell/v1"


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


def test_phase20_9r_normal_readback_keeps_edit_cell_audited_candidate(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9r normal prompt",
        teacher_feedback=TeacherFeedback(feedback_text="正常回复", reward_mag=1.0),
        session_id="phase20-9r-normal",
        db_path=tmp_path / "phase20_9r_normal.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    read_event = _event_with_action(result, "read_draft")
    edit_row = _competition_row(read_event, "edit_cell")
    edit_trace = edit_row["draftgrid_action_from_ap_flow"]["edit_cell"]

    assert not any(event.selected_action.get("action_type") == "edit_cell" for event in result.tick_trace)
    assert edit_trace["candidate_only_no_alternative_unit"] is True
    assert edit_trace["cstar_alternative_unit"]["formula_id"] == FORMULA_ID
    assert edit_trace["cstar_alternative_unit"]["can_edit"] is False


def test_phase20_9r_cstar_alternative_unit_executes_real_local_edit(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9r_edit.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9r edit prompt",
        teacher_feedback=TeacherFeedback(feedback_text="猫好", reward_mag=1.0),
        session_id="phase20-9r-edit",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    result = run_phase20_7_turn(
        user_text="phase20.9r edit prompt",
        session_id="phase20-9r-edit",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
        debug_draftgrid_write_mutation={0: "狗"},
    )

    actions = [event.selected_action.get("action_type") for event in result.tick_trace]
    edit_event = _event_with_action(result, "edit_cell")
    commit_event = _event_with_action(result, "commit_reply")
    edit_row = _competition_row(edit_event, "edit_cell")
    edit_trace = edit_row["draftgrid_action_from_ap_flow"]["edit_cell"]["cstar_alternative_unit"]

    assert actions.index("read_draft") < actions.index("edit_cell") < actions.index("commit_reply")
    assert edit_trace["formula_id"] == FORMULA_ID
    assert edit_trace["can_edit"] is True
    assert edit_trace["old_unit"] == "狗"
    assert edit_trace["alternative_unit"] == "猫"
    assert edit_row["selected"] is True
    assert edit_row["draftgrid_action_from_ap_flow"]["edit_cell"]["candidate_only_no_alternative_unit"] is False
    assert edit_event.draft_grid["visible_text"] == "猫好"
    assert commit_event.draft_grid["visible_text"] == "猫好"
    assert result.reply_text == "猫好"

    flow = edit_event.ssp_active_summary["draftgrid_edit_self_flow"]
    assert flow["formula_id"] == FORMULA_ID
    assert flow["substrate"] == "SELF_DRAFT_GRID"
    assert flow["edge_ids"]

    with sqlite3.connect(db_path) as conn:
        edit_payload = conn.execute(
            """
            SELECT payload_json
            FROM phase20_7_experience_events
            WHERE event_kind='draft_grid_edit'
            ORDER BY tick DESC
            LIMIT 1
            """
        ).fetchone()
        assert edit_payload is not None
        payload = from_json(str(edit_payload[0]))
        assert payload["old_unit_text"] == "狗"
        assert payload["alternative_unit_text"] == "猫"
        assert payload["cstar_alternative_unit"]["source"] == "cstar_expected_output_vs_self_draftgrid_readback"

        occurrence = conn.execute(
            "SELECT substrate, position_json FROM phase20_7_occurrences WHERE occurrence_id=?",
            (flow["occurrence_id"],),
        ).fetchone()
        assert occurrence is not None
        assert occurrence[0] == "SELF_DRAFT_GRID"
        position = from_json(str(occurrence[1]))
        assert position["formula_id"] == FORMULA_ID
