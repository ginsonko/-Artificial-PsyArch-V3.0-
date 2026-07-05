from __future__ import annotations

from apv3test.runtime import RuntimeStateCodec


def test_runtime_state_roundtrip_preserves_authoritative_memory() -> None:
    state = {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {"tokens": {"你": [1.0, 0.0], "好": [0.9, 0.1]}},
        "transitions": [{"source": "你好", "target": "我在", "support": 3.0}],
        "paradigms": [{"pid": "p:greeting", "support": 4.0, "columns": ["你好", "我在"]}],
        "action_outcomes": {"commit_reply": {"drive_bias": 0.4}},
    }
    codec = RuntimeStateCodec()

    envelope = codec.encode(state)
    restored = codec.decode(envelope)

    assert restored == state
    assert envelope["stored_bytes"] < envelope["raw_bytes"]


def test_runtime_state_does_not_require_audit_payload() -> None:
    state = {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {},
        "transitions": [],
        "paradigms": [],
        "audit_db_path": None,
    }
    codec = RuntimeStateCodec()

    restored = codec.decode(codec.encode(state))

    assert restored["schema_id"] == "apv3_runtime_ontology_state/v1"
    assert restored["audit_db_path"] is None

