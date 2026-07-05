from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.state_pool.state_pool import StateItem, StatePool, load_constant


@dataclass(frozen=True)
class FrustrationTrace:
    target_sa_id: str
    frustration_sa_id: str
    pressure: float
    failure_streak: int
    learned_helplessness: bool
    abandon_action_id: str | None


def update_frustration(
    state_pool: StatePool,
    *,
    target_sa_id: str,
    tick: int,
    outcome_reward: float,
    rpe: float,
) -> FrustrationTrace:
    """@op_count: O(1)."""
    target = state_pool.get(target_sa_id)
    frustration = _ensure_frustration_item(state_pool, target_sa_id)
    target_pressure = 0.0 if target is None else max(0.0, target.cognitive_pressure)
    poor_outcome = (
        float(outcome_reward) <= float(load_constant("frustration.low_reward_threshold"))
        or float(rpe) <= -float(load_constant("frustration.negative_rpe_threshold"))
    )
    high_pressure = target_pressure >= float(load_constant("frustration.high_pressure_threshold"))
    previous_streak = int(frustration.metadata.get("failure_streak", 0))
    streak = previous_streak + 1 if poor_outcome and high_pressure else max(0, previous_streak - 1)
    pressure = _clamp01(
        float(frustration.cognitive_pressure) * float(load_constant("frustration.persistence"))
        + target_pressure * float(load_constant("frustration.pressure_gain"))
        + (float(load_constant("frustration.failure_gain")) if poor_outcome else -float(load_constant("frustration.relief_gain")))
    )
    gain = pressure * float(load_constant("frustration.attention_gain_scale"))
    frustration.real_energy = pressure
    frustration.cognitive_pressure = pressure
    frustration.attention_energy = frustration.attention_energy + gain
    frustration.gain_ledger.inject("feedback", gain)
    frustration.last_tick = int(tick)
    frustration.metadata["failure_streak"] = streak
    frustration.metadata["last_target_pressure"] = target_pressure
    helpless = streak >= int(load_constant("frustration.helplessness_streak_threshold"))
    action_id = "affect_action::abandon_current_task" if pressure >= float(load_constant("frustration.abandon_threshold")) or helpless else None
    return FrustrationTrace(
        target_sa_id=target_sa_id,
        frustration_sa_id=frustration.sa_id,
        pressure=pressure,
        failure_streak=streak,
        learned_helplessness=helpless,
        abandon_action_id=action_id,
    )


def helplessness_discount(value: float, frustration: FrustrationTrace) -> float:
    """@op_count: O(1)."""
    if not frustration.learned_helplessness:
        return float(value)
    return float(value) * float(load_constant("frustration.helplessness_drive_discount"))


def _ensure_frustration_item(state_pool: StatePool, target_sa_id: str) -> StateItem:
    sa_id = f"cognitive_feeling::frustration::{target_sa_id}"
    item = state_pool.items.get(sa_id)
    if item is None:
        item = StateItem(
            sa_id=sa_id,
            family="feeling",
            label="frustration",
            channel_signature=("affect", "frustration"),
            source="frustration_runtime",
            metadata={"target_sa_id": target_sa_id},
        )
        state_pool.items[sa_id] = item
    return item


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))
