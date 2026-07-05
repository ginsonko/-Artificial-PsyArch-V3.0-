from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Mapping, Sequence

from runtime.cognitive.state_pool.state_pool import load_constant


@dataclass(frozen=True)
class PrototypeTrace:
    target_id: str
    positive_score: float
    negative_score: float
    accepted: bool


@dataclass(frozen=True)
class ComponentTrace:
    vocab_id: str
    component_count: int
    accepted: bool


@dataclass(frozen=True)
class ContrastTrace:
    target_score: float
    strongest_distractor_score: float
    margin: float
    accepted: bool


def evaluate_radical_prototype_generalization(
    target_id: str,
    prototype_vector: Sequence[float],
    held_out_positive_vectors: Sequence[Sequence[float]],
    held_out_negative_vectors: Sequence[Sequence[float]],
) -> PrototypeTrace:
    """@op_count: O(samples * vector_dims)."""
    positive = _mean(_cosine(prototype_vector, item) for item in held_out_positive_vectors)
    negative = _mean(_cosine(prototype_vector, item) for item in held_out_negative_vectors)
    threshold = float(load_constant("curriculum.content.radical_similarity_min"))
    margin = float(load_constant("curriculum.content.radical_margin_min"))
    return PrototypeTrace(
        target_id=target_id,
        positive_score=positive,
        negative_score=negative,
        accepted=positive >= threshold and (positive - negative) >= margin,
    )


def evaluate_vocabulary_components(vocab_id: str, components: Sequence[str]) -> ComponentTrace:
    """@op_count: O(components)."""
    unique_components = {str(item) for item in components if str(item)}
    minimum = int(load_constant("curriculum.content.vocabulary_component_min"))
    return ComponentTrace(
        vocab_id=vocab_id,
        component_count=len(unique_components),
        accepted=len(unique_components) >= minimum,
    )


def evaluate_visual_contrast(
    target_pair: tuple[str, str],
    pair_support: Mapping[tuple[str, str], float],
    distractor_pairs: Sequence[tuple[str, str]],
) -> ContrastTrace:
    """@op_count: O(distractors)."""
    target_score = float(pair_support.get(tuple(target_pair), 0.0))
    strongest = max((float(pair_support.get(tuple(pair), 0.0)) for pair in distractor_pairs), default=0.0)
    margin = target_score - strongest
    threshold = float(load_constant("curriculum.content.visual_contrast_margin_min"))
    return ContrastTrace(
        target_score=target_score,
        strongest_distractor_score=strongest,
        margin=margin,
        accepted=margin >= threshold,
    )


def evaluate_audio_pattern_contrast(
    target_signature: Sequence[float],
    positive_signatures: Sequence[Sequence[float]],
    distractor_signatures: Sequence[Sequence[float]],
) -> ContrastTrace:
    """@op_count: O(samples * dims)."""
    positive = _mean(_cosine(target_signature, item) for item in positive_signatures)
    distractor = max((_cosine(target_signature, item) for item in distractor_signatures), default=0.0)
    margin = positive - distractor
    threshold = float(load_constant("curriculum.content.audio_pattern_margin_min"))
    return ContrastTrace(
        target_score=positive,
        strongest_distractor_score=distractor,
        margin=margin,
        accepted=margin >= threshold,
    )


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """@op_count: O(vector_dims)."""
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = sqrt(sum(float(a) * float(a) for a in left))
    right_norm = sqrt(sum(float(b) * float(b) for b in right))
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _mean(values: Sequence[float] | object) -> float:
    """@op_count: O(values)."""
    rows = tuple(float(item) for item in values)
    if not rows:
        return 0.0
    return sum(rows) / max(1, len(rows))
