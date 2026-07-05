from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Mapping, Sequence

from runtime.cognitive.state_pool.state_pool import load_constant


@dataclass(frozen=True)
class ConsistencyTrace:
    vocab_id: str
    similarity: float
    accepted: bool


def validate_cross_course_consistency(
    vocab_id: str,
    recall_vectors: Mapping[str, Sequence[float]],
) -> ConsistencyTrace:
    """@op_count: O(course_pairs * vector_dims)."""
    vectors = [tuple(float(v) for v in values) for values in recall_vectors.values()]
    if len(vectors) < 2:
        return ConsistencyTrace(vocab_id=vocab_id, similarity=1.0, accepted=True)
    scores: list[float] = []
    for left_index, left in enumerate(vectors):
        for right in vectors[left_index + 1 :]:
            scores.append(_cosine(left, right))
    similarity = sum(scores) / max(1, len(scores))
    threshold = float(load_constant("curriculum.substrate.consistency_min_similarity"))
    return ConsistencyTrace(vocab_id=vocab_id, similarity=similarity, accepted=similarity >= threshold)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """@op_count: O(vector_dims)."""
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = sqrt(sum(float(a) * float(a) for a in left))
    right_norm = sqrt(sum(float(b) * float(b) for b in right))
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / (left_norm * right_norm)

