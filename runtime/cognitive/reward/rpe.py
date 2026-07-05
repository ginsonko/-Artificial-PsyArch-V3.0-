from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.sdpl.packet import LearningPacket
from runtime.cognitive.sdpl.q_table_backoff import QTableWithBackoff
from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass(frozen=True)
class RPETrace:
    action_id: str
    predicted_reward: float
    actual_reward: float
    rpe: float
    dopamine_delta: float
    learning_eligibility: float


def apply_rpe_learning(
    q_table: QTableWithBackoff,
    packet: LearningPacket,
    action_id: str,
    *,
    actual_reward: float,
    target_item: StateItem | None = None,
) -> RPETrace:
    """@op_count: O(backoff_layers)."""
    predicted = q_table.query(packet, action_id)
    rpe = float(actual_reward) - predicted
    dopamine_delta = rpe * _dopamine_gain(rpe)
    eligibility = min(
        float(load_constant("rpe.learning_eligibility_max")),
        float(load_constant("rpe.learning_eligibility_base"))
        + abs(rpe) * float(load_constant("rpe.learning_eligibility_rpe_gain")),
    )
    q_table.update(packet, action_id, outcome=float(actual_reward), eligibility=eligibility)
    if target_item is not None:
        gain = abs(rpe) * float(load_constant("rpe.attention_gain_scale"))
        target_item.attention_energy = target_item.attention_energy + gain
        target_item.gain_ledger.inject("rpe_signal", gain)
        target_item.metadata["last_rpe"] = rpe
        target_item.metadata["last_dopamine_delta"] = dopamine_delta
    return RPETrace(
        action_id=action_id,
        predicted_reward=predicted,
        actual_reward=float(actual_reward),
        rpe=rpe,
        dopamine_delta=dopamine_delta,
        learning_eligibility=eligibility,
    )


def _dopamine_gain(rpe: float) -> float:
    if rpe >= 0.0:
        return float(load_constant("rpe.positive_dopamine_gain"))
    return float(load_constant("rpe.negative_dopamine_gain"))
