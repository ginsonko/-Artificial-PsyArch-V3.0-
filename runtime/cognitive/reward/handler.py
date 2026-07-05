from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StatePool


@dataclass(frozen=True)
class FeedbackResult:
    target_sa_id: str
    marker: MarkerEvent | None


def apply_reward(
    state_pool: StatePool,
    *,
    target_sa_id: str,
    tick: int,
    amount: float = 1.0,
) -> FeedbackResult:
    """@op_count: O(1)."""
    item = state_pool.get(target_sa_id)
    if item is not None:
        item.real_energy = item.real_energy + float(amount)
        item.attention_energy = item.attention_energy + float(amount)
        item.gain_ledger.inject("feedback", float(amount))
        item.cognitive_pressure = item.real_energy - item.virtual_energy
    return FeedbackResult(target_sa_id=target_sa_id, marker=None)


def apply_punishment(
    state_pool: StatePool,
    *,
    target_sa_id: str,
    tick: int,
    amount: float = 1.0,
) -> FeedbackResult:
    """@op_count: O(1)."""
    item = state_pool.get(target_sa_id)
    if item is not None:
        item.real_energy = max(0.0, item.real_energy - float(amount))
        item.gain_ledger.inject("feedback", float(amount))
        item.cognitive_pressure = item.real_energy - item.virtual_energy
    marker = MarkerEvent(
        tick=int(tick),
        kind="CORRECTION",
        target_sa_id=target_sa_id,
        real_energy=float(amount),
        origin="feedback",
        metadata={
            "target_sa_id": target_sa_id,
            "ledger_source": "feedback",
        },
    )
    state_pool.observe_external(marker, tick=tick)
    return FeedbackResult(target_sa_id=target_sa_id, marker=marker)
