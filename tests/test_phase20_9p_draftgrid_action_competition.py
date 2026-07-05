from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9p_draftgrid_action_competition_from_ap_flow/v1"


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


def _draftgrid_trace(row: dict) -> dict:
    trace = row.get("draftgrid_action_from_ap_flow")
    assert isinstance(trace, dict)
    return trace


def test_phase20_9p_writes_then_really_reads_draft_before_commit(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9p feedback prompt",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9p feedback reply", reward_mag=1.0),
        session_id="phase20-9p-readback",
        db_path=tmp_path / "phase20_9p.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    actions = [event.selected_action.get("action_type") for event in result.tick_trace]
    read_event = _event_with_action(result, "read_draft")
    commit_event = _event_with_action(result, "commit_reply")

    assert actions.index("read_draft") < actions.index("commit_reply")
    assert read_event.experience_event_ids_written
    assert read_event.draft_grid["visible_text"] == result.reply_text
    assert read_event.selected_action["readback"] is True
    assert read_event.feelings["draftgrid_action_drive_context"]["formula_id"] == FORMULA_ID
    assert read_event.feelings["readback_need"] > 0.0


def test_phase20_9p_draftgrid_candidates_share_one_ap_flow_context(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9p exact prompt",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9p exact reply", reward_mag=1.0),
        session_id="phase20-9p-candidates",
        db_path=tmp_path / "phase20_9p.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    event = _event_with_action(result, "read_draft")
    traces = []
    for action_type in ("continue_writing", "read_draft", "edit_cell", "stop_generating"):
        row = _competition_row(event, action_type)
        trace = _draftgrid_trace(row)
        traces.append(trace)
        assert trace["formula_id"] == FORMULA_ID
        assert trace["has_visible_text"] is True
        assert trace["writes_answer_directly"] is False
        assert trace["creates_reply_candidate"] is False

    assert len({id(trace) for trace in traces}) == 1
    assert traces[0]["visible_text_hash"] == traces[1]["visible_text_hash"]
    assert _competition_row(event, "read_draft")["drive"] >= _competition_row(event, "continue_writing")["drive"]
    assert _competition_row(event, "stop_generating")["drive"] != 0.12


def test_phase20_9p_edit_cell_is_audited_candidate_not_fake_revision(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9p unknown prompt",
        session_id="phase20-9p-edit",
        db_path=tmp_path / "phase20_9p.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "read_draft")
    edit_row = _competition_row(event, "edit_cell")
    trace = _draftgrid_trace(edit_row)

    assert edit_row["selected"] is False
    assert trace["edit_cell"]["candidate_only_no_alternative_unit"] is True
    assert trace["edit_cell"]["writes_answer_directly"] is False
    assert not any(item.selected_action.get("action_type") == "edit_cell" for item in result.tick_trace)


def test_phase20_9p_commit_tick_keeps_draftgrid_readiness_trace(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9p commit prompt",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9p commit reply", reward_mag=1.0),
        session_id="phase20-9p-commit",
        db_path=tmp_path / "phase20_9p.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    commit_event = _event_with_action(result, "commit_reply")
    read_row = _competition_row(commit_event, "read_draft")
    write_row = _competition_row(commit_event, "write_cell")

    assert commit_event.feelings["commit_readiness"] > 0.0
    assert commit_event.feelings["draftgrid_action_drive_context"]["formula_id"] == FORMULA_ID
    assert _draftgrid_trace(read_row)["formula_id"] == FORMULA_ID
    assert write_row["drive"] < _competition_row(commit_event, "commit_reply")["drive"]
    assert write_row["drive"] != 0.12
