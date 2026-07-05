from __future__ import annotations

from pathlib import Path
import sqlite3

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


def _count(conn: sqlite3.Connection, sql: str) -> int:
    return int(conn.execute(sql).fetchone()[0])


def test_phase20_8k_cstar_carryover_writes_ssp_occurrences_and_edges(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8k.sqlite"
    run_phase20_7_turn(
        user_text="phase20k hello",
        teacher_feedback=TeacherFeedback(feedback_text="phase20k reply", reward_mag=1.0),
        session_id="phase20-8k-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    result = run_phase20_7_turn(
        user_text="phase20k hello",
        session_id="phase20-8k-query",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )

    flow_ticks = [event for event in result.tick_trace if event.ssp_active_summary.get("cstar_carryover_flow")]
    assert flow_ticks
    flow = flow_ticks[0].ssp_active_summary["cstar_carryover_flow"]
    assert flow["flow_occurrence_id"]
    assert flow["source_occurrence_ids"]
    assert flow["edge_ids"]
    assert flow["writes_answer_directly"] is False
    assert flow["creates_reply_candidate"] is False

    with sqlite3.connect(db_path) as conn:
        assert _count(conn, "SELECT COUNT(*) FROM phase20_7_occurrences WHERE sa_type_id LIKE 'short_structure_flow::cstar_carryover::%'") >= 1
        assert _count(conn, "SELECT COUNT(*) FROM phase20_7_structure_edges WHERE edge_type='cstar_carryover_to_short_flow'") >= 1
        assert _count(conn, "SELECT COUNT(*) FROM phase20_7_structure_edges WHERE edge_type='short_structure_next'") >= 1


def test_phase20_8k_idle_think_narrative_becomes_short_structure_flow(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8k.sqlite"
    run_phase20_7_turn(
        user_text="phase20k idle unknown",
        session_id="phase20-8k-idle",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    idle1 = run_phase20_7_turn(
        user_text="",
        session_id="phase20-8k-idle",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    idle2 = run_phase20_7_turn(
        user_text="",
        session_id="phase20-8k-idle",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    first_flow = idle1.tick_trace[0].ssp_active_summary["idle_narrative_flow"]
    second_flow = idle2.tick_trace[0].ssp_active_summary["idle_narrative_flow"]
    assert first_flow["occurrence_id"]
    assert second_flow["occurrence_id"]
    assert second_flow["previous_occurrence_id"] == first_flow["occurrence_id"]
    assert second_flow["edge_ids"]
    assert idle2.tick_trace[0].ssp_active_summary["short_structure_flow_attention_bias"]["active"] is True
    assert idle2.tick_trace[0].ssp_active_summary["short_structure_flow_attention_bias"]["idle_think_drive_delta"] > 0
    assert idle2.reply_text == ""

    with sqlite3.connect(db_path) as conn:
        assert _count(conn, "SELECT COUNT(*) FROM phase20_7_occurrences WHERE sa_type_id LIKE 'short_structure_flow::idle::%'") >= 2
        assert _count(conn, "SELECT COUNT(*) FROM phase20_7_structure_edges WHERE edge_type='short_structure_next'") >= 2


def test_phase20_8k_unknown_carryover_flow_does_not_create_fake_b(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20k unknown input",
        session_id="phase20-8k-unknown",
        db_path=tmp_path / "phase20_8k.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    assert not any(event.b_candidates for event in result.tick_trace)
    assert any(event.ssp_active_summary.get("cstar_carryover_flow") for event in result.tick_trace[1:])
    for event in result.tick_trace:
        trace = event.feelings.get("cstar_statepool_feedback")
        if isinstance(trace, dict):
            assert trace.get("creates_reply_candidate") is False
            assert trace.get("writes_answer_directly") is False


def test_phase20_8k_stage0_has_no_ssp_carryover_flow(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20k boundary",
        session_id="phase20-8k-stage0",
        db_path=tmp_path / "phase20_8k.sqlite",
        runtime_stage="stage0",
    )

    event = result.tick_trace[0]
    assert result.stage_id == "20.7-stage0"
    assert event.no_write_reason == "stage0_does_not_write_experience_events"
    assert "cstar_carryover_flow" not in event.ssp_active_summary

