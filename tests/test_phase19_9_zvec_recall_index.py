from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

from runtime.cognitive.percept_vector.phase19_runtime import EXTERNAL_VISUAL, PERCEIVED, RECEPTOR_VERSION_VISUAL
from runtime.cognitive.percept_vector.recall_index import Layer1RecallIndex, RecallFilter
from runtime.cognitive.percept_vector.vector_substrate import Layer1PerceptVectorStore, PerceptVector
from runtime.cognitive.state_pool.state_pool import load_constant


def _signature(seed: int) -> tuple[int, ...]:
    width = int(load_constant("phase19.vector.layer1_signature_dim"))
    return tuple((seed * 17 + index * 13) % 256 for index in range(width))


def _put_vectors(store: Layer1PerceptVectorStore, *, count: int = 12) -> tuple[PerceptVector, ...]:
    vectors = []
    for index in range(count):
        source = PERCEIVED if index % 2 == 0 else "IMAGINED"
        substrate = EXTERNAL_VISUAL if index % 3 else "SELF_DRAFT_GRID"
        version = RECEPTOR_VERSION_VISUAL if index % 5 else "phase19_old"
        vector = PerceptVector(
            vector_uuid=f"pv_{index:04x}",
            signature=_signature(index),
            full_vec_path=None,
            epistemic_source=source,
            substrate=substrate,
            receptor_version=version,
            tick_acquired=index,
            importance=1.0,
            metadata={
                "used_filename_label": False,
                "audit_note": "truth_store_only",
            },
        )
        store.put(vector, write_mode=str(load_constant("phase19.vector.schema_fixture_write_mode")))
        vectors.append(vector)
    return tuple(vectors)


def test_phase19_9_rebuildable_index_returns_same_topk_as_bruteforce(tmp_path: Path) -> None:
    store = Layer1PerceptVectorStore(tmp_path / "truth" / "layer1")
    vectors = _put_vectors(store, count=24)
    index = Layer1RecallIndex(store, index_root=tmp_path / "zvec", prefer_zvec=True)
    stats = index.rebuild_from_truth()
    query = vectors[2]
    recall_filter = RecallFilter(query.epistemic_source, query.substrate, query.receptor_version)

    indexed = index.c_recall(query.signature, recall_filter=recall_filter, top_k=5)
    brute = index.brute_force_recall(query.signature, recall_filter=recall_filter, top_k=5)

    assert stats.rebuildable_from_truth is True
    assert stats.fallback_available is True
    assert stats.indexed_count == 24
    assert [hit.vector_uuid for hit in indexed] == [hit.vector_uuid for hit in brute]


def test_phase19_9_source_substrate_version_filters_do_not_cross_paths(tmp_path: Path) -> None:
    store = Layer1PerceptVectorStore(tmp_path / "truth" / "layer1")
    vectors = _put_vectors(store, count=18)
    index = Layer1RecallIndex(store, index_root=tmp_path / "zvec", prefer_zvec=True)
    index.rebuild_from_truth()
    query = vectors[2]
    recall_filter = RecallFilter(PERCEIVED, EXTERNAL_VISUAL, RECEPTOR_VERSION_VISUAL)
    hits = index.c_recall(query.signature, recall_filter=recall_filter, top_k=10)

    assert hits
    assert all(hit.epistemic_source == PERCEIVED for hit in hits)
    assert all(hit.substrate == EXTERNAL_VISUAL for hit in hits)
    assert all(hit.receptor_version == RECEPTOR_VERSION_VISUAL for hit in hits)


def test_phase19_9_recall_hits_do_not_return_labels_or_private_metadata(tmp_path: Path) -> None:
    store = Layer1PerceptVectorStore(tmp_path / "truth" / "layer1")
    vectors = _put_vectors(store, count=10)
    index = Layer1RecallIndex(store, index_root=tmp_path / "zvec", prefer_zvec=False)
    index.rebuild_from_truth()
    query = vectors[2]
    hits = index.c_recall(
        query.signature,
        recall_filter=RecallFilter(query.epistemic_source, query.substrate, query.receptor_version),
        top_k=3,
    )

    assert hits
    for hit in hits:
        joined = repr(hit.metadata).lower()
        assert "label" not in joined.replace("label_returned", "")
        assert "source_url" not in joined
        assert "user_text" not in joined
        assert hit.metadata["label_returned"] is False


def test_phase19_9_deleting_index_and_rebuilding_preserves_results(tmp_path: Path) -> None:
    store = Layer1PerceptVectorStore(tmp_path / "truth" / "layer1")
    vectors = _put_vectors(store, count=20)
    query = vectors[4]
    recall_filter = RecallFilter(query.epistemic_source, query.substrate, query.receptor_version)

    first = Layer1RecallIndex(store, index_root=tmp_path / "zvec_a", prefer_zvec=True)
    first.rebuild_from_truth()
    first_ids = [hit.vector_uuid for hit in first.c_recall(query.signature, recall_filter=recall_filter, top_k=5)]

    second = Layer1RecallIndex(store, index_root=tmp_path / "zvec_b", prefer_zvec=True)
    second.rebuild_from_truth()
    second_ids = [hit.vector_uuid for hit in second.c_recall(query.signature, recall_filter=recall_filter, top_k=5)]

    assert first_ids == second_ids


def test_phase19_9_runtime_redlines_keep_zvec_out_of_recognizers() -> None:
    import runtime.cognitive.percept_vector.object_looking as object_looking
    import runtime.cognitive.percept_vector.phase19_runtime as phase19_runtime
    import runtime.cognitive.percept_vector.recall_index as recall_index

    assert "zvec" not in inspect.getsource(phase19_runtime.visual_recognize_v1_7)
    assert "zvec" not in inspect.getsource(object_looking.enumerate_objects_in_image)
    assert "visible_teacher_label" not in inspect.getsource(recall_index.Layer1RecallIndex.c_recall)


def test_phase19_9_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "19.9"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 19.9 deliverables present" in completed.stdout
