from __future__ import annotations

from pathlib import Path
import sqlite3

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


def _event_count(db_path: Path, event_kind: str | None = None) -> int:
    with sqlite3.connect(db_path) as conn:
        if event_kind is None:
            return int(conn.execute("SELECT COUNT(*) FROM phase20_7_experience_events").fetchone()[0])
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM phase20_7_experience_events WHERE event_kind=?",
                (event_kind,),
            ).fetchone()[0]
        )


def test_stage1_text_input_writes_statepool_ssp_and_minimal_experience_events(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    result = run_phase20_7_turn(
        user_text="你好啊",
        session_id="stage1-basic",
        db_path=db_path,
        post_commit_idle_ticks=0,
    )

    assert result.stage_id == "20.7-stage1"
    assert result.schema_id == "apv3_phase20_7_stage1_text_closed_loop/v1"
    assert result.tick_trace
    first = result.tick_trace[0].to_dict()
    assert first["selected_action"]["action_type"] == "observe_text"
    assert first["ssp_active_summary"]["structure_kind"] == "linear_text"
    assert first["state_pool_top"]
    assert first["experience_event_ids_written"]
    assert _event_count(db_path, "text_receptor_observation") == 1


def test_stage1_feedback_enters_unified_eventlog_and_exact_b0_recalls_same_structure(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    learned = run_phase20_7_turn(
        user_text="你好啊",
        teacher_feedback=TeacherFeedback(feedback_text="你也好", reward_mag=1.0),
        session_id="stage1-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
    )
    recalled = run_phase20_7_turn(
        user_text="你好啊",
        session_id="stage1-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
    )

    assert learned.reply_text == "嗯,记下了。"
    assert recalled.committed is True
    assert recalled.reply_text == "你也好"
    assert any(event.b_candidates for event in recalled.tick_trace)
    assert _event_count(db_path, "experience_alignment") == 1
    assert _event_count(db_path, "draft_grid_write") >= len("你也好")


def test_stage1_exact_b0_does_not_leak_feedback_to_different_input(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    run_phase20_7_turn(
        user_text="你好啊",
        teacher_feedback=TeacherFeedback(feedback_text="你也好", reward_mag=1.0),
        session_id="stage1-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
    )
    different = run_phase20_7_turn(
        user_text="你是谁",
        session_id="stage1-other",
        db_path=db_path,
        post_commit_idle_ticks=0,
    )

    assert different.reply_text == "不太会,教教"
    assert different.reply_text != "你也好"
    assert not any(event.b_candidates for event in different.tick_trace)
    assert any(event.selected_action.get("action_type") == "request_teacher" for event in different.tick_trace)


def test_stage1_draftgrid_grows_one_visible_unit_per_write_tick(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    run_phase20_7_turn(
        user_text="你好啊",
        teacher_feedback=TeacherFeedback(feedback_text="你也好", reward_mag=1.0),
        session_id="stage1-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
    )
    result = run_phase20_7_turn(
        user_text="你好啊",
        session_id="stage1-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
    )
    write_texts = [
        event.to_dict()["draft_grid"]["visible_text"]
        for event in result.tick_trace
        if event.selected_action.get("action_type") == "write_cell"
    ]

    assert write_texts == ["你", "你也", "你也好"]
    assert all(event.is_projection is False for event in result.tick_trace)
    assert all(event.experience_event_ids_written for event in result.tick_trace)


def test_stage1_records_occurrences_edges_and_action_records(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    run_phase20_7_turn(
        user_text="你好啊",
        teacher_feedback=TeacherFeedback(feedback_text="你也好", reward_mag=1.0),
        session_id="stage1-db",
        db_path=db_path,
        post_commit_idle_ticks=0,
    )

    with sqlite3.connect(db_path) as conn:
        occurrences = conn.execute("SELECT COUNT(*) FROM phase20_7_occurrences").fetchone()[0]
        edges = conn.execute("SELECT COUNT(*) FROM phase20_7_structure_edges").fetchone()[0]
        actions = conn.execute("SELECT COUNT(*) FROM phase20_7_action_records").fetchone()[0]
        packets = conn.execute("SELECT COUNT(*) FROM phase20_7_source_packets").fetchone()[0]

    assert occurrences >= 1 + len("你好啊") + len("你也好")
    assert edges >= len("你好啊") + len("你也好")
    assert actions >= len("嗯,记下了。") + 1
    assert packets >= 2
