from __future__ import annotations

from pathlib import Path

import sqlite3

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.experience_log import from_json


READBACK_FORMULA = "apv3_phase20_9q_draftgrid_readback_self_flow/v1"
ATTRIBUTION_FORMULA = "apv3_phase20_9q_reward_punish_backward_attribution_consolidation/v1"


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


def _attribution_delta(result) -> dict:
    for event in result.tick_trace:
        for delta in event.learning_deltas:
            if isinstance(delta, dict) and delta.get("delta_kind") == "reward_punish_backward_attribution_consolidation":
                return dict(delta)
    raise AssertionError("attribution consolidation delta not found")


def _attribution_carryover(row: dict) -> dict:
    carryover = row.get("learning_loop_carryover", {})
    if carryover.get("formula_id") == ATTRIBUTION_FORMULA:
        return dict(carryover)
    nested = carryover.get("attribution_consolidation_carryover", {})
    assert nested.get("formula_id") == ATTRIBUTION_FORMULA
    return dict(nested)


def test_phase20_9q_draft_readback_writes_self_draftgrid_occurrence_and_edges(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9q_readback.sqlite"
    result = run_phase20_7_turn(
        user_text="phase20.9q readback prompt",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9q readback reply", reward_mag=1.0),
        session_id="phase20-9q-readback",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    read_event = _event_with_action(result, "read_draft")
    flow = read_event.ssp_active_summary["draftgrid_readback_self_flow"]

    assert flow["formula_id"] == READBACK_FORMULA
    assert flow["substrate"] == "SELF_DRAFT_GRID"
    assert flow["occurrence_id"]
    assert flow["source_write_occurrence_ids"]
    assert flow["edge_ids"]
    assert flow["writes_answer_directly"] is False

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT substrate, sa_type_id, position_json FROM phase20_7_occurrences WHERE occurrence_id=?",
            (flow["occurrence_id"],),
        ).fetchone()
        assert row is not None
        substrate, sa_type_id, position_json = row
        position = from_json(position_json)
        assert substrate == "SELF_DRAFT_GRID"
        assert str(sa_type_id).startswith("self_draft_grid_readback::")
        assert position["formula_id"] == READBACK_FORMULA

        edge_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM phase20_7_structure_edges
            WHERE dst_occurrence_id=? AND edge_type='draft_write_to_readback'
            """,
            (flow["occurrence_id"],),
        ).fetchone()[0]
        assert edge_count >= 1


def test_phase20_9q_reward_consolidation_modulates_following_actions(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9q reward prompt",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9q reward reply", reward_mag=1.0),
        session_id="phase20-9q-reward",
        db_path=tmp_path / "phase20_9q_reward.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    delta = _attribution_delta(result)
    assert delta["formula_id"] == ATTRIBUTION_FORMULA
    assert delta["reward"] == 1.0
    assert delta["expected_reward_delta"] > 0.0
    assert delta["attention_bias_delta"] > 0.0
    assert delta["eligible_occurrences"]
    assert delta["may_be_wrong"] is True
    assert delta["writes_answer_directly"] is False

    read_event = _event_with_action(result, "read_draft")
    commit_event = _event_with_action(result, "commit_reply")

    read_commit_row = _competition_row(read_event, "commit_reply")
    assert _attribution_carryover(read_commit_row)["formula_id"] == ATTRIBUTION_FORMULA
    assert read_commit_row.get("learning_loop_carryover_delta", 0.0) > 0.0
    commit_row = _competition_row(commit_event, "commit_reply")
    write_row = _competition_row(commit_event, "write_cell")
    assert _attribution_carryover(commit_row)["formula_id"] == ATTRIBUTION_FORMULA
    assert commit_row.get("learning_loop_carryover_delta", 0.0) > 0.0
    assert _attribution_carryover(write_row).get("expected_reward_delta", 0.0) > 0.0


def test_phase20_9q_punish_consolidation_keeps_recall_but_raises_caution(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9q punish prompt",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9q corrected reply", punish_mag=1.0),
        session_id="phase20-9q-punish",
        db_path=tmp_path / "phase20_9q_punish.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    delta = _attribution_delta(result)
    assert delta["formula_id"] == ATTRIBUTION_FORMULA
    assert delta["punish"] == 1.0
    assert delta["expected_punish_delta"] > 0.0
    assert delta["inhibition_delta"] > 0.0
    assert delta["alternative_search_delta"] > 0.0
    assert delta["eligible_occurrences"]
    assert delta["may_be_wrong"] is True

    read_event = _event_with_action(result, "read_draft")
    request_row = _competition_row(read_event, "request_teacher")
    edit_row = _competition_row(read_event, "edit_cell")
    read_row = _competition_row(read_event, "read_draft")

    assert _attribution_carryover(request_row)["formula_id"] == ATTRIBUTION_FORMULA
    assert request_row.get("learning_loop_carryover_delta", 0.0) > 0.0
    assert edit_row.get("learning_loop_carryover_delta", 0.0) > 0.0
    assert read_row.get("learning_loop_carryover_delta", 0.0) > 0.0
    assert edit_row["draftgrid_action_from_ap_flow"]["edit_cell"]["candidate_only_no_alternative_unit"] is True
