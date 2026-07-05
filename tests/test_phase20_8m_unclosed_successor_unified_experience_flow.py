from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


def test_phase20_8m_idle_successor_can_follow_short_structure_flow_next(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8m.sqlite"
    run_phase20_7_turn(
        user_text="phase20m idle unknown",
        session_id="phase20-8m-idle",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    first_idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-8m-idle",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    second_idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-8m-idle",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    assert first_idle.reply_text == ""
    assert second_idle.reply_text == ""
    event = second_idle.tick_trace[0]
    successor = event.ssp_active_summary["successor_bias"]
    assert successor["source_kind"] == "short_structure_flow_next"
    assert successor["candidate_id"].startswith("flow::short_structure_next::")
    assert successor["writes_answer_directly"] is False
    assert any(row.get("kind") == "idle_successor_continuation" for row in event.c_forward)
    continuation = next(row for row in event.c_forward if row.get("kind") == "idle_successor_continuation")
    assert continuation["source_kind"] == "short_structure_flow_next"
    assert continuation["writes_answer_directly"] is False
    assert event.ssp_active_summary["idle_narrative_flow"]["previous_occurrence_id"]


def test_phase20_8m_alignment_successor_still_competes_through_unified_query(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8m.sqlite"
    run_phase20_7_turn(
        user_text="phase20m teachable question",
        session_id="phase20-8m-open",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="phase20m teachable question",
        teacher_feedback=TeacherFeedback(feedback_text="phase20m taught answer", reward_mag=1.0),
        session_id="phase20-8m-teacher",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-8m-open",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = idle.tick_trace[0]
    assert idle.reply_text == ""
    successor = event.ssp_active_summary["successor_bias"]
    assert successor["source_kind"] == "alignment_memory"
    assert successor["output_text"] == "phase20m taught answer"
    assert successor["writes_answer_directly"] is False
    assert any(
        row.get("kind") == "idle_successor_continuation"
        and row.get("predicted_text") == "phase20m taught answer"
        and row.get("writes_answer_directly") is False
        for row in event.c_forward
    )


def test_phase20_8m_idle_successor_keeps_chat_silent_and_no_fake_b(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8m.sqlite"
    run_phase20_7_turn(
        user_text="phase20m silent unknown",
        session_id="phase20-8m-silent",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-8m-silent",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = idle.tick_trace[0]
    assert idle.committed is False
    assert idle.reply_text == ""
    assert not event.b_candidates
    assert event.selected_action["action_type"] == "idle_think"
    assert event.feelings["narrative_text"]


def test_phase20_8m_stage0_has_no_idle_successor_query(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20m boundary",
        session_id="phase20-8m-stage0",
        db_path=tmp_path / "phase20_8m.sqlite",
        runtime_stage="stage0",
    )

    event = result.tick_trace[0]
    assert result.stage_id == "20.7-stage0"
    assert event.no_write_reason == "stage0_does_not_write_experience_events"
    assert not event.c_forward
    assert not event.cstar_packet

