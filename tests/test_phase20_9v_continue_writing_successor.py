from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9p_draftgrid_action_competition_from_ap_flow/v1"


def _events_with_action(result, action_type: str):
    return [event for event in result.tick_trace if event.selected_action.get("action_type") == action_type]


def test_phase20_9v_continue_writing_wins_from_pending_successor_units(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9v_continue.sqlite"
    session_id = "phase20-9v-continue"
    prompt = "phase20.9v long successor prompt"
    reply = "ap writes a first visible row then keeps writing the successor row"

    run_phase20_7_turn(
        user_text=prompt,
        teacher_feedback=TeacherFeedback(feedback_text=reply, reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        max_ticks=96,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    result = run_phase20_7_turn(
        user_text=prompt,
        session_id=session_id,
        db_path=db_path,
        max_ticks=96,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    continue_events = _events_with_action(result, "continue_writing")
    assert continue_events
    continue_event = continue_events[0]
    selection = continue_event.selected_action["draftgrid_next_action_selection"]
    rows = {row["action_type"]: row for row in selection["candidate_rows"]}

    assert selection["formula_id"] == FORMULA_ID
    assert selection["selected_action_type"] == "continue_writing"
    assert selection["pending_output_units"] is True
    assert rows["continue_writing"]["eligible"] is True
    assert rows["continue_writing"]["drive"] > rows["commit_reply"]["drive"]
    assert continue_event.experience_event_ids_written
    assert continue_event.ssp_active_summary["draftgrid_write_self_flow"]["writes_answer_directly"] is False


def test_phase20_9v_continued_successor_is_read_back_before_commit(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9v_read_commit.sqlite"
    session_id = "phase20-9v-read-commit"
    prompt = "phase20.9v read after successor prompt"
    reply = "draftgrid successor fragments become one external reply after reread"

    run_phase20_7_turn(
        user_text=prompt,
        teacher_feedback=TeacherFeedback(feedback_text=reply, reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        max_ticks=96,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    result = run_phase20_7_turn(
        user_text=prompt,
        session_id=session_id,
        db_path=db_path,
        max_ticks=96,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    actions = [event.selected_action.get("action_type") for event in result.tick_trace]
    continue_index = actions.index("continue_writing")
    later_read_index = actions.index("read_draft", continue_index + 1)
    commit_index = actions.index("commit_reply")
    commit_event = _events_with_action(result, "commit_reply")[0]
    selection = commit_event.selected_action["draftgrid_next_action_selection"]
    rows = {row["action_type"]: row for row in selection["candidate_rows"]}

    assert continue_index < later_read_index < commit_index
    assert selection["selected_action_type"] == "commit_reply"
    assert selection["pending_output_units"] is False
    assert rows["continue_writing"]["eligible"] is False
    assert result.committed is True
    assert result.reply_text == reply
    assert "\n" not in result.reply_text


def test_phase20_9v_short_reply_keeps_existing_single_fragment_path(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9v_short.sqlite"
    session_id = "phase20-9v-short"
    prompt = "phase20.9v short prompt"
    reply = "cat"

    run_phase20_7_turn(
        user_text=prompt,
        teacher_feedback=TeacherFeedback(feedback_text=reply, reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    result = run_phase20_7_turn(
        user_text=prompt,
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    commit_event = _events_with_action(result, "commit_reply")[0]
    selection = commit_event.selected_action["draftgrid_next_action_selection"]
    rows = {row["action_type"]: row for row in selection["candidate_rows"]}

    assert not _events_with_action(result, "continue_writing")
    assert selection["selected_action_type"] == "commit_reply"
    assert rows["continue_writing"]["eligible"] is False
    assert result.reply_text == reply
