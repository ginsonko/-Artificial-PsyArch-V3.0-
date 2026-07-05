from __future__ import annotations

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StateItem


def spawn_novelty(item: StateItem, *, tick: int, surprise_pressure: float) -> MarkerEvent:
    """@op_count: O(1)."""
    return MarkerEvent(
        tick=int(tick),
        kind="NOVELTY",
        target_sa_id=item.sa_id,
        real_energy=max(0.0, float(surprise_pressure)),
        metadata={
            "target_sa_id": item.sa_id,
            "ledger_source": "external",
        },
    )
