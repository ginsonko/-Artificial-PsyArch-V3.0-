from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.composed_vocab.held_out_pool import HeldOutPool, HeldOutSituation
from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass(frozen=True)
class VocabCandidate:
    candidate_id: str
    component_ids: tuple[str, ...]
    predicted_pressure_reduction: float = 0.0


@dataclass(frozen=True)
class DeltaPEvaluation:
    passes: bool
    mean_delta_p: float
    positive_situations: int
    reason: str = ""


def evaluate_delta_p_incremental(
    candidate: VocabCandidate,
    current_items: tuple[StateItem, ...],
    held_out_pool: HeldOutPool,
) -> DeltaPEvaluation:
    """@op_count: O(situations * items)."""
    min_components = int(load_constant("composed_vocab.delta_p.min_components_for_candidate"))
    if len(candidate.component_ids) < min_components:
        return DeltaPEvaluation(
            passes=False,
            mean_delta_p=0.0,
            positive_situations=0,
            reason="insufficient_components",
        )
    cold_min = int(load_constant("composed_vocab.delta_p.cold_start_skip_until_held_out"))
    if len(held_out_pool) < cold_min:
        return DeltaPEvaluation(
            passes=False,
            mean_delta_p=0.0,
            positive_situations=0,
            reason="insufficient_held_out",
        )
    situations = held_out_pool.find_top_k_similar(current_items)
    deltas = tuple(_delta_for_situation(candidate, situation) for situation in situations)
    if not deltas:
        return DeltaPEvaluation(False, 0.0, 0, "no_similar_situations")
    mean_delta = sum(deltas) / len(deltas)
    positive = sum(1 for value in deltas if value > 0.0)
    required = len(deltas) * float(load_constant("composed_vocab.delta_p.positive_ratio_min"))
    passes = (
        mean_delta > float(load_constant("composed_vocab.delta_p.promote_dP_min"))
        and positive >= required
    )
    return DeltaPEvaluation(
        passes=passes,
        mean_delta_p=mean_delta,
        positive_situations=positive,
        reason="short_term_value_add",
    )


def _delta_for_situation(candidate: VocabCandidate, situation: HeldOutSituation) -> float:
    before = situation.mean_recent_pressure()
    component_overlap = sum(
        1.0 for item in situation.items if item.sa_id in candidate.component_ids
    )
    if component_overlap < len(candidate.component_ids):
        return 0.0
    reduction = candidate.predicted_pressure_reduction * component_overlap
    after = max(0.0, before - reduction)
    return before - after
