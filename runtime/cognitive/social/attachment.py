from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.state_pool.state_pool import StateItem, StatePool, load_constant


@dataclass(frozen=True)
class AttachmentTrace:
    entity_sa_id: str
    familiarity: float
    oxy_tone: float
    preference_score: float


def observe_user_interaction(
    state_pool: StatePool,
    *,
    entity_id: str,
    tick: int,
    positive_affect: float = 1.0,
) -> AttachmentTrace:
    """@op_count: O(1)."""
    item = _ensure_user_entity(state_pool, entity_id)
    familiarity = _clamp01(
        float(item.metadata.get("familiarity", 0.0))
        * float(load_constant("attachment.familiarity_persistence"))
        + float(load_constant("attachment.interaction_gain"))
    )
    oxy = _clamp01(
        float(item.metadata.get("oxy_tone", 0.0))
        * float(load_constant("attachment.oxy_persistence"))
        + max(0.0, float(positive_affect)) * float(load_constant("attachment.positive_affect_gain"))
        + familiarity * float(load_constant("attachment.familiarity_to_oxy_gain"))
    )
    gain = oxy * float(load_constant("attachment.attention_gain_scale"))
    item.real_energy = familiarity
    item.cognitive_pressure = oxy - item.virtual_energy
    item.attention_energy = item.attention_energy + gain
    item.gain_ledger.inject("user_directed", gain)
    item.last_tick = int(tick)
    item.metadata["familiarity"] = familiarity
    item.metadata["oxy_tone"] = oxy
    return AttachmentTrace(
        entity_sa_id=item.sa_id,
        familiarity=familiarity,
        oxy_tone=oxy,
        preference_score=attachment_preference_score(item),
    )


def attachment_preference_score(item: StateItem) -> float:
    """@op_count: O(1)."""
    return (
        float(item.metadata.get("familiarity", 0.0))
        + float(item.metadata.get("oxy_tone", 0.0)) * float(load_constant("attachment.oxy_preference_weight"))
    )


def user_entity_sa_id(entity_id: str) -> str:
    """@op_count: O(1)."""
    return f"EntitySA::user::{entity_id}"


def _ensure_user_entity(state_pool: StatePool, entity_id: str) -> StateItem:
    sa_id = user_entity_sa_id(entity_id)
    item = state_pool.items.get(sa_id)
    if item is None:
        item = StateItem(
            sa_id=sa_id,
            family="entity_user",
            label=f"user::{entity_id}",
            channel_signature=("entity_user", entity_id),
            source="social_attachment",
            metadata={"entity_kind": "user", "entity_id": entity_id},
        )
        state_pool.items[sa_id] = item
    return item


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))
