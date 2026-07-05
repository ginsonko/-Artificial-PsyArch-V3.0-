from __future__ import annotations

from pathlib import Path
import sqlite3

from apv3test.runtime.phase20_7 import (
    MediaInput,
    SourceTrustKey,
    initialize_phase20_7_store,
    phase20_7_schema_status,
    phase20_7_table_names,
    run_phase20_7_turn,
)
from apv3test.runtime.phase20_7.models import REQUIRED_PHASE20_7_TABLES


def test_phase20_7_store_initializes_truth_source_and_provenance_tables(tmp_path: Path) -> None:
    db_path = initialize_phase20_7_store(tmp_path / "phase20_7.sqlite")
    tables = set(phase20_7_table_names(db_path))
    status = phase20_7_schema_status(db_path)

    assert status["ready"] is True
    assert status["truth_source"] == "phase20_7_experience_events"
    assert status["derived_snapshots_are_rebuildable"] is True
    assert set(REQUIRED_PHASE20_7_TABLES).issubset(tables)
    assert "phase20_7_source_packets" in tables
    assert "phase20_7_action_records" in tables
    assert "phase20_7_package_memberships" in tables


def test_phase20_7_stage0_turn_is_boundary_only_without_commit(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="你好",
        media_inputs=(MediaInput(media_type="image", path="demo.png"),),
        session_id="stage0-demo",
        db_path=tmp_path / "phase20_7.sqlite",
        runtime_stage="stage0",
    )
    payload = result.to_dict()
    event = payload["tick_trace"][0]

    assert payload["schema_id"] == "apv3_phase20_7_stage0_boundary/v1"
    assert payload["stage_id"] == "20.7-stage0"
    assert payload["committed"] is False
    assert payload["reply_text"] == ""
    assert event["schema_id"] == "apv3_phase20_7_runtime_tick_event/v2"
    assert event["is_projection"] is False
    assert event["selected_action"]["action_type"] == "stage0_boundary_only"
    assert event["experience_event_ids_written"] == []
    assert event["no_write_reason"] == "stage0_does_not_write_experience_events"


def test_phase20_7_stage0_does_not_write_experience_events(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    run_phase20_7_turn(user_text="hello", session_id="no-write", db_path=db_path, runtime_stage="stage0")

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM phase20_7_experience_events").fetchone()[0]

    assert count == 0


def test_phase20_7_runtime_event_v2_exposes_audit_chain_fields(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="audit",
        session_id="audit",
        db_path=tmp_path / "phase20_7.sqlite",
        runtime_stage="stage0",
    )
    event = result.tick_trace[0].to_dict()

    for key in (
        "source_refs",
        "action_record_ids",
        "rejected_candidates",
        "index_query_trace",
        "package_delta_refs",
        "timings_ms",
    ):
        assert key in event
    assert event["source_refs"]
    assert event["timings_ms"]["stage0_boundary"] == 0.0


def test_phase20_7_source_trust_key_is_context_and_modality_local() -> None:
    visual_key = SourceTrustKey(source_ref="teacher::local", context="fruit", modality="vision")
    text_key = SourceTrustKey(source_ref="teacher::local", context="fruit", modality="text")
    math_key = SourceTrustKey(source_ref="teacher::local", context="math", modality="text")

    assert visual_key.storage_key() != text_key.storage_key()
    assert text_key.storage_key() != math_key.storage_key()
    assert visual_key.storage_key().startswith("teacher::local|fruit|")
