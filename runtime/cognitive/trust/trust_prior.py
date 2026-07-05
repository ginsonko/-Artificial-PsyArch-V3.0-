from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.social.attachment import attachment_preference_score
from runtime.cognitive.state_pool.state_pool import StateItem, StatePool, load_constant


@dataclass(frozen=True)
class TrustTrace:
    entity_sa_id: str
    trust_score: float
    promoted_marker: MarkerEvent | None
    downgraded: bool


def update_teaching_accuracy(entity: StateItem, *, correct: bool) -> float:
    """@op_count: O(1)."""
    total = float(entity.metadata.get("teaching_total", 0.0)) + 1.0
    good = float(entity.metadata.get("teaching_correct", 0.0)) + (1.0 if correct else 0.0)
    entity.metadata["teaching_total"] = total
    entity.metadata["teaching_correct"] = good
    entity.metadata["teaching_accuracy"] = good / max(total, 1.0)
    return float(entity.metadata["teaching_accuracy"])


def trust_score(entity: StateItem) -> float:
    """@op_count: O(1)."""
    accuracy = float(entity.metadata.get("teaching_accuracy", 0.0))
    return (
        attachment_preference_score(entity) * float(load_constant("trust.attachment_weight"))
        + accuracy * float(load_constant("trust.accuracy_weight"))
    )


def evaluate_trust_promotion(
    state_pool: StatePool,
    *,
    entity_sa_id: str,
    evidence_target_sa_id: str,
    tick: int,
    delta_p: float,
) -> TrustTrace:
    """@op_count: O(1)."""
    entity = state_pool.get(entity_sa_id)
    if entity is None:
        raise KeyError(entity_sa_id)
    score = trust_score(entity)
    downgraded = float(delta_p) < -float(load_constant("trust.downgrade_delta_p_threshold"))
    if downgraded:
        entity.metadata["trust_downgraded"] = True
        entity.metadata["teaching_accuracy"] = float(entity.metadata.get("teaching_accuracy", 0.0)) * float(load_constant("trust.downgrade_accuracy_decay"))
        return TrustTrace(entity_sa_id=entity_sa_id, trust_score=trust_score(entity), promoted_marker=None, downgraded=True)
    if score < float(load_constant("trust.promote_threshold")):
        return TrustTrace(entity_sa_id=entity_sa_id, trust_score=score, promoted_marker=None, downgraded=False)
    marker = MarkerEvent(
        tick=int(tick),
        kind="TRUST_PROMOTED",
        target_sa_id=evidence_target_sa_id,
        real_energy=min(1.0, score),
        origin="trust_prior",
        metadata={
            "entity_sa_id": entity_sa_id,
            "ledger_source": "user_directed",
        },
    )
    state_pool.observe_external(marker, tick=tick)
    return TrustTrace(entity_sa_id=entity_sa_id, trust_score=score, promoted_marker=marker, downgraded=False)
