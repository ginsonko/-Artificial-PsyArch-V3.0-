from __future__ import annotations

from pathlib import Path

from apv3test.runtime import SQLiteAuditStore, SQLiteRuntimeStore


def _runtime_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "三": {"vector": [1.0, 0.0], "support": 2.0},
                "顾": {"vector": [0.8, 0.2], "support": 1.5},
            }
        },
        "transitions": [{"source": "三顾", "target": "茅庐", "support": 6.0}],
        "paradigms": [{"pid": "p:idiom_successor", "support": 5.0}],
        "action_outcomes": {"type_char": {"drive_bias": 0.3}},
        "percept_prototypes": [{"prototype_id": "visual:yellow_apple", "support": 1.0}],
    }


def test_runtime_store_roundtrips_authoritative_state(tmp_path: Path) -> None:
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(_runtime_state())
    restored = store.load_state(state_id)

    assert restored == _runtime_state()


def test_runtime_store_projects_ontology_tables(tmp_path: Path) -> None:
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(_runtime_state())
    counts = store.ontology_counts(state_id)
    projection = store.load_ontology_projection(state_id)

    assert counts == {
        "online_embedding_tokens": 2,
        "explicit_transitions": 1,
        "paradigm_sa": 1,
        "action_outcomes": 1,
        "percept_prototypes": 1,
        "phase20_6_fast_action_chains": 0,
        "phase20_6_slow_memory": 0,
    }
    assert projection["online_embedding_tokens"][0]["support"] > 0.0
    assert projection["explicit_transitions"][0]["target"] == "茅庐"
    assert projection["action_outcomes"]["type_char"]["drive_bias"] == 0.3


def test_runtime_does_not_depend_on_audit_db(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime.sqlite"
    audit_path = tmp_path / "audit.sqlite"
    runtime_store = SQLiteRuntimeStore(runtime_path)
    audit_store = SQLiteAuditStore(audit_path)

    runtime_store.save_state(_runtime_state())
    audit_store.append_event("score_breakdown", {"candidate": "茅庐", "score": 0.9})
    audit_path.unlink()

    restored = SQLiteRuntimeStore(runtime_path).load_state()

    assert restored["transitions"][0]["target"] == "茅庐"


def test_audit_store_payload_is_not_runtime_state(tmp_path: Path) -> None:
    audit_store = SQLiteAuditStore(tmp_path / "audit.sqlite")

    audit_store.append_event("explanation_pass", {"residual_pressure": 0.4})
    events = audit_store.list_events()

    assert events[0]["event_kind"] == "explanation_pass"
    assert "schema_id" not in events[0]["payload"]
