from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from runtime.cognitive.percept_vector.vector_substrate import (
    ConceptPrototype,
    Layer1PerceptVectorStore,
    Layer2PartPrototypeStore,
    Layer3ConceptPrototypeStore,
    PacketKeyFields,
    PartAssociation,
    PartPrototype,
    PerceptVector,
    TemporalEventBinding,
    b_recall_schema_skeleton,
    c_recall_schema_skeleton,
    make_packet_key,
)
from runtime.cognitive.state_pool.state_pool import load_constant


def _signature(fill: int = 7) -> tuple[int, ...]:
    return tuple([fill] * int(load_constant("phase19.vector.layer1_signature_dim")))


def test_packet_key_keeps_source_substrate_and_receptor_version_separate() -> None:
    base = {
        "sensory_feature_signature": _signature(),
        "epistemic_source": "PERCEIVED",
        "substrate": "EXTERNAL_VISUAL",
        "receptor_version": "phase19_0a_foveated",
    }

    perceived = make_packet_key(**base)
    imagined = make_packet_key(**{**base, "epistemic_source": "IMAGINED"})
    draft = make_packet_key(**{**base, "substrate": "SELF_DRAFT_GRID"})
    old_version = make_packet_key(**{**base, "receptor_version": "phase19_0_substrate"})

    assert len({perceived, imagined, draft, old_version}) == 4
    assert PacketKeyFields(**base).packet_key() == perceived


def test_layer1_schema_store_rejects_old_runtime_writes_but_allows_schema_fixture(tmp_path: Path) -> None:
    store = Layer1PerceptVectorStore(tmp_path / "layer1")
    old_vector = PerceptVector(
        vector_uuid="pv_schema_a",
        signature=_signature(),
        full_vec_path=None,
        epistemic_source="PERCEIVED",
        substrate="EXTERNAL_VISUAL",
        receptor_version="phase19_0_substrate",
        tick_acquired=19,
        importance=0.5,
        metadata={"purpose": "schema_crud_only"},
    )

    with pytest.raises(ValueError):
        store.put(old_vector)

    store.put(old_vector, write_mode=str(load_constant("phase19.vector.schema_fixture_write_mode")))
    assert store.count() == 1
    loaded = store.get("pv_schema_a")
    assert loaded is not None
    assert loaded.packet_key() == old_vector.packet_key()
    assert loaded.metadata["purpose"] == "schema_crud_only"


def test_layer1_runtime_write_accepts_only_foveated_receptor_version(tmp_path: Path) -> None:
    store = Layer1PerceptVectorStore(tmp_path / "layer1")
    vector = PerceptVector(
        vector_uuid="pv_runtime_a",
        signature=_signature(11),
        full_vec_path="data/layer1/full/pv_runtime_a.npy",
        epistemic_source="PERCEIVED",
        substrate="EXTERNAL_VISUAL",
        receptor_version=str(load_constant("phase19.vector.min_runtime_receptor_version")),
        tick_acquired=20,
        importance=0.8,
        metadata={"record_kind": "runtime"},
    )

    store.put(vector)

    assert store.list_ids() == ("pv_runtime_a",)
    assert store.get("pv_runtime_a") == vector


def test_layer2_part_prototype_is_true_medoid_with_opaque_exemplar(tmp_path: Path) -> None:
    store = Layer2PartPrototypeStore(tmp_path / "layer2")
    part = PartPrototype(
        part_uuid="part_4f2a",
        channel="V7",
        patch_signature=(1, 2, 3),
        exemplar_id="exemplar_9c0d",
        activation_count=3,
    )

    store.put(part)

    assert store.get("part_4f2a") == part
    with pytest.raises(ValueError):
        store.put(PartPrototype("tentative_part", "V7", (1,), "exemplar_ok"))


def test_layer3_concept_and_temporal_event_schema_are_persistent(tmp_path: Path) -> None:
    store = Layer3ConceptPrototypeStore(tmp_path / "layer3")
    concept = ConceptPrototype(
        concept_uuid="c_3f1a9b",
        lifecycle_status="promoted",
        part_weights=(PartAssociation("part_4f2a", 0.7),),
        vocab_associations=("vocab_sa_opaque",),
        epistemic_source="PERCEIVED",
        lifetime_observations=5,
    )
    event = TemporalEventBinding(
        event_uuid="event_7b2c",
        percept_uuids=("pv_runtime_a", "aud_runtime_a"),
        tick_window=(10, 13),
        source_markers=("PERCEIVED", "HEARSAY"),
        lifetime_cooccurrence_count=4,
    )

    store.put_concept(concept)
    store.put_temporal_event(event)

    assert store.get_concept("c_3f1a9b") == concept
    assert store.get_temporal_event("event_7b2c") == event


def test_tentative_concept_spawns_with_initial_part_associations_without_semantic_uuid(tmp_path: Path) -> None:
    store = Layer3ConceptPrototypeStore(tmp_path / "layer3")

    concept = store.spawn_tentative_concept(
        (PartAssociation("part_4f2a", 0.6), PartAssociation("part_8b21", 0.4)),
        epistemic_source="PERCEIVED_UNNAMED",
    )

    assert concept.lifecycle_status == str(load_constant("phase19.vector.tentative_lifecycle_status"))
    assert concept.concept_uuid.startswith("c_")
    assert "tentative" not in concept.concept_uuid
    assert tuple(item.part_uuid for item in concept.part_weights) == ("part_4f2a", "part_8b21")
    assert store.get_concept(concept.concept_uuid) == concept


def test_recall_skeleton_mock_is_explicitly_schema_only_and_not_quality_evidence() -> None:
    c_result = c_recall_schema_skeleton(
        allow_mock=str(load_constant("phase19.vector.schema_fixture_write_mode"))
    )
    b_result = b_recall_schema_skeleton(
        allow_mock=str(load_constant("phase19.vector.schema_fixture_write_mode"))
    )

    assert c_result.status == "schema_only_mock"
    assert b_result.status == "schema_only_mock"
    assert "not recall quality" in c_result.boundary_note
    assert "not B recall quality" in b_result.boundary_note
    assert c_recall_schema_skeleton().status == "empty_schema_skeleton"


def test_phase19_0b0_final_report_keeps_schema_boundary_clear() -> None:
    text = Path("docs/FinalReport_Phase19_0b0_VectorSubstrateSchema_20260619.md").read_text(
        encoding="utf-8"
    )

    assert "schema/skeleton only" in text
    assert "does not prove recall quality" in text
    assert "does not prove visual generalization" in text


def test_phase19_0b0_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "19.0b0"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 19.0b0 deliverables present" in completed.stdout

