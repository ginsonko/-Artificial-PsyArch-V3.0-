from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.state_pool.state_pool import StateItem, StatePool, load_constant


@dataclass(frozen=True)
class SelfHeartbeatTrace:
    self_sa_id: str
    reactivated: bool
    heartbeat_due: bool
    real_energy: float


def ensure_self_model(state_pool: StatePool, *, identity_id: str = "ap_self") -> StateItem:
    """@op_count: O(1)."""
    sa_id = f"EntitySA::self::{identity_id}"
    item = state_pool.items.get(sa_id)
    if item is None:
        item = StateItem(
            sa_id=sa_id,
            family="self_model",
            label="persistent_self",
            real_energy=float(load_constant("self_model.reactivation_target_R")),
            channel_signature=("self_model", identity_id),
            source="self_model",
            metadata={
                "identity_id": identity_id,
                "heartbeat_count": 0,
                "last_heartbeat_tick": 0,
            },
        )
        state_pool.items[sa_id] = item
    return item


def heartbeat_self_model(state_pool: StatePool, *, identity_id: str = "ap_self", tick: int) -> SelfHeartbeatTrace:
    """@op_count: O(1)."""
    item = ensure_self_model(state_pool, identity_id=identity_id)
    interval = int(load_constant("self_model.heartbeat_interval_ticks"))
    last = int(item.metadata.get("last_heartbeat_tick", 0))
    heartbeat_due = int(tick) - last >= interval
    reactivated = False
    if item.real_energy < float(load_constant("self_model.decay_low_threshold")) or heartbeat_due:
        target = float(load_constant("self_model.reactivation_target_R"))
        pullback = float(load_constant("self_model.reactivation_pullback_rate"))
        item.real_energy = min(1.0, item.real_energy + (target - item.real_energy) * pullback)
        item.attention_energy = min(float(load_constant("self_model.attention_cap_percent")), item.attention_energy + pullback)
        item.gain_ledger.inject("residual_mass", pullback)
        item.metadata["heartbeat_count"] = int(item.metadata.get("heartbeat_count", 0)) + 1
        item.metadata["last_heartbeat_tick"] = int(tick)
        reactivated = True
    item.cognitive_pressure = item.real_energy - item.virtual_energy
    item.last_tick = int(tick)
    return SelfHeartbeatTrace(
        self_sa_id=item.sa_id,
        reactivated=reactivated,
        heartbeat_due=heartbeat_due,
        real_energy=item.real_energy,
    )
