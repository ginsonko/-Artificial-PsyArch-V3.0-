from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StateItem, StatePool, load_constant


@dataclass(frozen=True)
class PainTrace:
    target_sa_id: str
    marker_sa_id: str
    pain_energy: float


def register_pain_event(
    state_pool: StatePool,
    *,
    target_sa_id: str,
    tick: int,
    intensity: float,
) -> PainTrace:
    """@op_count: O(1)."""
    marker = MarkerEvent(
        tick=int(tick),
        kind="PAIN",
        target_sa_id=target_sa_id,
        real_energy=max(0.0, float(intensity)),
        origin="feedback",
        metadata={"target_sa_id": target_sa_id, "ledger_source": "feedback"},
    )
    item = state_pool.observe_external(marker, tick=tick)
    item.metadata["pain_memory"] = True
    item.metadata["long_decay_marker"] = "PAIN"
    return PainTrace(target_sa_id=target_sa_id, marker_sa_id=item.sa_id, pain_energy=item.real_energy)


def decay_pain_memory(item: StateItem) -> float:
    """@op_count: O(1)."""
    decay = float(load_constant("marker.decay_rates.PAIN"))
    item.real_energy = item.real_energy * decay
    item.attention_energy = item.attention_energy * decay
    item.gain_ledger.step_decay(decay)
    item.cognitive_pressure = item.real_energy - item.virtual_energy
    return item.real_energy


def should_avoid_due_to_pain(item: StateItem) -> bool:
    """@op_count: O(1)."""
    return item.real_energy >= float(load_constant("pain_memory.avoidance_threshold"))
