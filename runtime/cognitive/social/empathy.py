from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StatePool, load_constant


@dataclass(frozen=True)
class EmpathyTrace:
    marker: MarkerEvent | None
    resonance_energy: float


def resonate_from_observed_marker(
    state_pool: StatePool,
    *,
    observed_marker: MarkerEvent,
    observer_entity_sa_id: str,
    tick: int,
) -> EmpathyTrace:
    """@op_count: O(1)."""
    if observed_marker.kind not in tuple(load_constant("empathy.resonant_marker_kinds")):
        return EmpathyTrace(marker=None, resonance_energy=0.0)
    energy = min(
        float(load_constant("empathy.max_resonance")),
        max(0.0, observed_marker.real_energy) * float(load_constant("empathy.resonance_gain")),
    )
    if energy < float(load_constant("empathy.min_resonance")):
        return EmpathyTrace(marker=None, resonance_energy=energy)
    marker = MarkerEvent(
        tick=int(tick),
        kind="EMPATHY_RESONANCE",
        target_sa_id=observer_entity_sa_id,
        real_energy=energy,
        origin="social_observation",
        metadata={
            "observed_kind": observed_marker.kind,
            "observed_target_sa_id": observed_marker.target_sa_id,
            "ledger_source": "user_directed",
        },
    )
    state_pool.observe_external(marker, tick=tick)
    return EmpathyTrace(marker=marker, resonance_energy=energy)
