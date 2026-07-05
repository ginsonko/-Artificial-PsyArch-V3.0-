from __future__ import annotations

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StateItem


def spawn_remembered(item: StateItem, *, tick: int, cue_alignment: float) -> MarkerEvent:
    """@op_count: O(1)."""
    energy = float(item.metadata.get("long_term_R", item.real_energy)) * float(cue_alignment)
    return MarkerEvent(
        tick=int(tick),
        kind="REMEMBERED",
        target_sa_id=item.sa_id,
        real_energy=energy,
        metadata={
            "target_sa_id": item.sa_id,
            "ledger_source": "replay",
        },
    )
