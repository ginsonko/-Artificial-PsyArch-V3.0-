from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


def _candidate_kinds(result) -> set[str]:
    kinds: set[str] = set()
    for event in result.tick_trace:
        packet = event.cstar_packet or {}
        stats = packet.get("unified_candidate_statistics", {})
        for kind in stats.get("candidate_kinds", ()):
            kinds.add(str(kind))
    return kinds


def test_phase20_8l_short_structure_next_enters_cstar_unified_statistics(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8l.sqlite"
    run_phase20_7_turn(
        user_text="phase20l hello",
        teacher_feedback=TeacherFeedback(feedback_text="phase20l reply", reward_mag=1.0),
        session_id="phase20-8l-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    result = run_phase20_7_turn(
        user_text="phase20l hello",
        session_id="phase20-8l-query",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )

    assert "short_structure_flow_next" in _candidate_kinds(result)
    query_rows = [
        row
        for event in result.tick_trace
        for row in event.c_backward
        if row.get("kind") == "short_structure_flow_query_recall"
    ]
    assert query_rows
    assert any(
        slot.get("slot_kind") == "unified_experience_candidate"
        and slot.get("candidate_kind") == "short_structure_flow_next"
        for row in query_rows
        for slot in row.get("cause_slots", ())
        if isinstance(slot, dict)
    )
    assert all(row.get("writes_answer_directly") is False for row in query_rows)


def test_phase20_8l_unknown_weak_tick_can_see_short_flow_without_fake_b(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20l only unknown",
        session_id="phase20-8l-unknown",
        db_path=tmp_path / "phase20_8l.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    assert not any(event.b_candidates for event in result.tick_trace)
    assert "short_structure_flow_next" in _candidate_kinds(result)
    assert any(
        row.get("kind") == "short_structure_flow_query_recall"
        for event in result.tick_trace
        for row in event.c_backward
    )
    for event in result.tick_trace:
        trace = event.feelings.get("cstar_statepool_feedback")
        if isinstance(trace, dict):
            assert trace.get("creates_reply_candidate") is False
            assert trace.get("writes_answer_directly") is False


def test_phase20_8l_idle_flow_is_available_to_later_query(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8l.sqlite"
    run_phase20_7_turn(
        user_text="phase20l idle unknown",
        session_id="phase20-8l-idle",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="",
        session_id="phase20-8l-idle",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    later = run_phase20_7_turn(
        user_text="",
        session_id="phase20-8l-idle",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = later.tick_trace[0]
    assert event.selected_action["action_type"] == "idle_think"
    assert event.ssp_active_summary["idle_narrative_flow"]["previous_occurrence_id"]
    assert any(row.get("kind") == "short_structure_flow_query_recall" for row in event.c_backward)
    assert "short_structure_flow_next" in event.cstar_packet["unified_candidate_statistics"]["candidate_kinds"]
    assert later.reply_text == ""


def test_phase20_8l_stage0_has_no_short_structure_query_completion(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20l boundary",
        session_id="phase20-8l-stage0",
        db_path=tmp_path / "phase20_8l.sqlite",
        runtime_stage="stage0",
    )

    event = result.tick_trace[0]
    assert result.stage_id == "20.7-stage0"
    assert event.no_write_reason == "stage0_does_not_write_experience_events"
    assert not event.c_backward
    assert not event.cstar_packet

