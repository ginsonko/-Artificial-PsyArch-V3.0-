from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Iterable, Protocol

import numpy as np

from runtime.cognitive.percept_vector.vector_substrate import Layer1PerceptVectorStore, PerceptVector
from runtime.cognitive.state_pool.state_pool import load_constant


@dataclass(frozen=True)
class RecallFilter:
    epistemic_source: str
    substrate: str
    receptor_version: str


@dataclass(frozen=True)
class RecallHit:
    vector_uuid: str
    score: float
    epistemic_source: str
    substrate: str
    receptor_version: str
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RecallIndexStats:
    backend: str
    indexed_count: int
    fallback_available: bool
    rebuildable_from_truth: bool


class _Backend(Protocol):
    name: str

    def build(self, vectors: Iterable[PerceptVector]) -> None:
        ...

    def query(self, query_signature: tuple[int, ...], *, top_k: int) -> tuple[tuple[str, float], ...]:
        ...

    def clear(self) -> None:
        ...


class Layer1RecallIndex:
    def __init__(
        self,
        truth_store: Layer1PerceptVectorStore,
        *,
        index_root: Path | str,
        prefer_zvec: bool = True,
    ) -> None:
        self.truth_store = truth_store
        self.index_root = Path(index_root)
        self.index_root.mkdir(parents=True, exist_ok=True)
        self.backend: _Backend = _make_backend(self.index_root, prefer_zvec=prefer_zvec)
        self._indexed_count = 0

    def rebuild_from_truth(self) -> RecallIndexStats:
        """@op_count: O(records * signature_dim)."""
        vectors = [vector for vector in (self.truth_store.get(vector_id) for vector_id in self.truth_store.list_ids()) if vector is not None]
        self.backend.clear()
        self.backend.build(vectors)
        self._indexed_count = len(vectors)
        return self.stats()

    def c_recall(
        self,
        query_signature: tuple[int, ...],
        *,
        recall_filter: RecallFilter,
        top_k: int | None = None,
    ) -> tuple[RecallHit, ...]:
        """@op_count: O(index_query + candidates)."""
        top_k = int(top_k or load_constant("phase19_9.recall.default_top_k"))
        oversample = max(top_k, top_k * int(load_constant("phase19_9.recall.filter_oversample_factor")))
        candidate_pairs = self.backend.query(query_signature, top_k=oversample)
        if not candidate_pairs:
            candidate_pairs = _brute_force_pairs(self.truth_store, query_signature, top_k=oversample)
        candidate_scores = {vector_uuid: score for vector_uuid, score in candidate_pairs}
        hits: list[RecallHit] = []
        for vector in self._filtered_ranked_truth_vectors(
            candidate_scores.keys(),
            query_signature,
            recall_filter,
        ):
            raw_backend_score = float(candidate_scores.get(vector.vector_uuid, 0.0))
            score = signature_similarity(query_signature, vector.signature)
            hits.append(
                RecallHit(
                    vector_uuid=vector.vector_uuid,
                    score=float(score),
                    epistemic_source=vector.epistemic_source,
                    substrate=vector.substrate,
                    receptor_version=vector.receptor_version,
                    metadata={
                        "backend": self.backend.name,
                        "label_returned": False,
                        "source_of_truth": "Layer1PerceptVectorStore",
                        "score_source": "truth_signature_similarity",
                        "raw_backend_score": raw_backend_score,
                    },
                )
            )
            if len(hits) >= top_k:
                break
        if len(hits) < top_k:
            for vector in self._filtered_ranked_truth_vectors(
                self.truth_store.list_ids(),
                query_signature,
                recall_filter,
            ):
                if any(hit.vector_uuid == vector.vector_uuid for hit in hits):
                    continue
                score = signature_similarity(query_signature, vector.signature)
                hits.append(
                    RecallHit(
                        vector_uuid=vector.vector_uuid,
                        score=float(score),
                        epistemic_source=vector.epistemic_source,
                        substrate=vector.substrate,
                        receptor_version=vector.receptor_version,
                        metadata={
                            "backend": self.backend.name,
                            "label_returned": False,
                            "source_of_truth": "Layer1PerceptVectorStore",
                            "score_source": "truth_signature_similarity",
                            "raw_backend_score": None,
                        },
                    )
                )
                if len(hits) >= top_k:
                    break
        return tuple(hits)

    def _filtered_ranked_truth_vectors(
        self,
        vector_ids: Iterable[str],
        query_signature: tuple[int, ...],
        recall_filter: RecallFilter,
    ) -> tuple[PerceptVector, ...]:
        """@op_count: O(candidates * signature_dim)."""
        vectors: list[tuple[PerceptVector, float]] = []
        for vector_uuid in vector_ids:
            vector = self.truth_store.get(vector_uuid)
            if vector is None:
                continue
            if not _matches_filter(vector, recall_filter):
                continue
            vectors.append((vector, signature_similarity(query_signature, vector.signature)))
        vectors.sort(key=lambda item: (item[1], item[0].vector_uuid), reverse=True)
        return tuple(vector for vector, _score in vectors)

    def brute_force_recall(
        self,
        query_signature: tuple[int, ...],
        *,
        recall_filter: RecallFilter,
        top_k: int | None = None,
    ) -> tuple[RecallHit, ...]:
        """@op_count: O(records * signature_dim)."""
        top_k = int(top_k or load_constant("phase19_9.recall.default_top_k"))
        pairs = _brute_force_pairs(self.truth_store, query_signature, top_k=max(top_k, self.truth_store.count()))
        hits: list[RecallHit] = []
        for vector_uuid, score in pairs:
            vector = self.truth_store.get(vector_uuid)
            if vector is None or not _matches_filter(vector, recall_filter):
                continue
            hits.append(
                RecallHit(
                    vector_uuid=vector.vector_uuid,
                    score=float(score),
                    epistemic_source=vector.epistemic_source,
                    substrate=vector.substrate,
                    receptor_version=vector.receptor_version,
                    metadata={
                        "backend": "brute_force_truth",
                        "label_returned": False,
                        "source_of_truth": "Layer1PerceptVectorStore",
                    },
                )
            )
            if len(hits) >= top_k:
                break
        return tuple(hits)

    def stats(self) -> RecallIndexStats:
        """@op_count: O(1)."""
        return RecallIndexStats(
            backend=self.backend.name,
            indexed_count=self._indexed_count,
            fallback_available=True,
            rebuildable_from_truth=True,
        )


class _BruteForceBackend:
    name = "brute_force"

    def __init__(self, truth_store: Layer1PerceptVectorStore | None = None) -> None:
        self._vectors: dict[str, tuple[int, ...]] = {}

    def build(self, vectors: Iterable[PerceptVector]) -> None:
        """@op_count: O(records * signature_dim)."""
        self._vectors = {vector.vector_uuid: vector.signature for vector in vectors}

    def query(self, query_signature: tuple[int, ...], *, top_k: int) -> tuple[tuple[str, float], ...]:
        """@op_count: O(records * signature_dim)."""
        ranked = [
            (vector_uuid, signature_similarity(query_signature, signature))
            for vector_uuid, signature in self._vectors.items()
        ]
        ranked.sort(key=lambda item: (item[1], item[0]), reverse=True)
        return tuple(ranked[: int(top_k)])

    def clear(self) -> None:
        self._vectors = {}


class _ZvecBackend:
    name = "zvec"

    def __init__(self, index_root: Path) -> None:
        self.index_root = index_root
        self.collection = None

    def build(self, vectors: Iterable[PerceptVector]) -> None:
        """@op_count: O(records * signature_dim)."""
        import zvec

        vector_list = list(vectors)
        schema = zvec.CollectionSchema(
            name="layer1_percept_vectors",
            vectors=zvec.VectorSchema(
                "signature",
                zvec.DataType.VECTOR_FP32,
                int(load_constant("phase19.vector.layer1_signature_dim")),
            ),
        )
        self.collection = zvec.create_and_open(path=str(self.index_root / "layer1_zvec"), schema=schema)
        if not vector_list:
            return
        docs = [
            zvec.Doc(id=vector.vector_uuid, vectors={"signature": _signature_to_float32(vector.signature).tolist()})
            for vector in vector_list
        ]
        self.collection.insert(docs)

    def query(self, query_signature: tuple[int, ...], *, top_k: int) -> tuple[tuple[str, float], ...]:
        """@op_count: O(index_query)."""
        if self.collection is None:
            return ()
        import zvec

        results = self.collection.query(
            zvec.Query("signature", vector=_signature_to_float32(query_signature).tolist()),
            topk=int(top_k),
        )
        return tuple((str(item.id), float(item.score)) for item in results)

    def clear(self) -> None:
        if self.collection is not None:
            try:
                self.collection.destroy()
            except Exception:
                pass
        self.collection = None


def _make_backend(index_root: Path, *, prefer_zvec: bool) -> _Backend:
    if prefer_zvec:
        try:
            import zvec  # noqa: F401

            return _ZvecBackend(index_root)
        except Exception:
            return _BruteForceBackend()
    return _BruteForceBackend()


def _brute_force_pairs(
    truth_store: Layer1PerceptVectorStore,
    query_signature: tuple[int, ...],
    *,
    top_k: int,
) -> tuple[tuple[str, float], ...]:
    ranked: list[tuple[str, float]] = []
    for vector_id in truth_store.list_ids():
        vector = truth_store.get(vector_id)
        if vector is None:
            continue
        ranked.append((vector.vector_uuid, signature_similarity(query_signature, vector.signature)))
    ranked.sort(key=lambda item: (item[1], item[0]), reverse=True)
    return tuple(ranked[: int(top_k)])


def _matches_filter(vector: PerceptVector, recall_filter: RecallFilter) -> bool:
    return (
        vector.epistemic_source == recall_filter.epistemic_source
        and vector.substrate == recall_filter.substrate
        and vector.receptor_version == recall_filter.receptor_version
    )


def signature_similarity(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    """@op_count: O(signature_dim)."""
    a = _signature_to_float32(left)
    b = _signature_to_float32(right)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= float(load_constant("phase19.confidence.denominator_epsilon")):
        return 0.0
    return float(np.dot(a, b) / denom)


def _signature_to_float32(signature: tuple[int, ...]) -> np.ndarray:
    values = np.asarray(tuple(int(value) for value in signature), dtype=np.float32)
    return values / float(load_constant("phase19.vector.signature_max_value"))
