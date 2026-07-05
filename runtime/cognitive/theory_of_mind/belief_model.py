from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.state_pool.state_pool import StateItem, StatePool, load_constant


@dataclass(frozen=True)
class FalseBeliefTrace:
    belief_sa_id: str
    entity_id: str
    topic_sa_id: str
    believed_location_sa_id: str
    reality_location_sa_id: str
    is_false_belief: bool
    predicted_search_location_sa_id: str


def update_other_belief(
    state_pool: StatePool,
    *,
    entity_id: str,
    topic_sa_id: str,
    believed_location_sa_id: str,
    tick: int,
    confidence: float = 1.0,
) -> StateItem:
    """@op_count: O(1)."""
    item = _ensure_belief_item(state_pool, entity_id, topic_sa_id)
    confidence_value = min(1.0, max(0.0, float(confidence)))
    item.real_energy = confidence_value
    item.cognitive_pressure = confidence_value - item.virtual_energy
    item.last_tick = int(tick)
    item.metadata["believed_location_sa_id"] = believed_location_sa_id
    item.metadata["belief_confidence"] = confidence_value
    return item


def set_reality_location(
    state_pool: StatePool,
    *,
    topic_sa_id: str,
    location_sa_id: str,
) -> StateItem:
    """@op_count: O(1)."""
    item = state_pool.items.get(topic_sa_id)
    if item is None:
        item = StateItem(
            sa_id=topic_sa_id,
            family="percept",
            label=topic_sa_id,
            real_energy=1.0,
            source="reality_location",
            metadata={},
        )
        state_pool.items[topic_sa_id] = item
    item.metadata["reality_location_sa_id"] = location_sa_id
    return item


def evaluate_false_belief(
    state_pool: StatePool,
    *,
    entity_id: str,
    topic_sa_id: str,
) -> FalseBeliefTrace:
    """@op_count: O(1)."""
    belief = _ensure_belief_item(state_pool, entity_id, topic_sa_id)
    reality = state_pool.get(topic_sa_id)
    believed = str(belief.metadata.get("believed_location_sa_id", ""))
    real = "" if reality is None else str(reality.metadata.get("reality_location_sa_id", ""))
    false_belief = bool(believed and real and believed != real)
    return FalseBeliefTrace(
        belief_sa_id=belief.sa_id,
        entity_id=entity_id,
        topic_sa_id=topic_sa_id,
        believed_location_sa_id=believed,
        reality_location_sa_id=real,
        is_false_belief=false_belief,
        predicted_search_location_sa_id=believed if false_belief else real,
    )


def _ensure_belief_item(state_pool: StatePool, entity_id: str, topic_sa_id: str) -> StateItem:
    sa_id = f"belief::other::{entity_id}::{topic_sa_id}"
    item = state_pool.items.get(sa_id)
    if item is None:
        item = StateItem(
            sa_id=sa_id,
            family="belief_model",
            label="other_belief",
            channel_signature=("belief_model", entity_id),
            source="theory_of_mind",
            metadata={
                "entity_id": entity_id,
                "topic_sa_id": topic_sa_id,
                "belief_model": True,
                "counterfactual_dependency": bool(load_constant("theory_of_mind.requires_counterfactual_context")),
            },
        )
        state_pool.items[sa_id] = item
    return item
