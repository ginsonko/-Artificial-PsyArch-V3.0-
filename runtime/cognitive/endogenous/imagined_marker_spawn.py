from __future__ import annotations

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


def spawn_imagined(item: StateItem, *, tick: int) -> MarkerEvent | None:
    """@op_count: O(1)."""
    share = item.gain_ledger.endogenous_share()
    threshold = float(load_constant("imagined_pathway.immediate_recall_threshold"))
    if share < threshold:
        return None
    return MarkerEvent(
        tick=int(tick),
        kind="IMAGINED",
        target_sa_id=item.sa_id,
        real_energy=share,
        metadata={
            "target_sa_id": item.sa_id,
            "ledger_source": "imagination",
        },
    )

