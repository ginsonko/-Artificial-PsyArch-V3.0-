from __future__ import annotations

from runtime.cognitive.marker.events import MarkerEvent, event_value


def spawn_perceived(event: object, *, tick: int) -> MarkerEvent:
    """@op_count: O(1)."""
    target_sa_id = str(event_value(event, "sa_id"))
    energy = float(event_value(event, "real_energy"))
    return MarkerEvent(
        tick=int(tick),
        kind="PERCEIVED",
        target_sa_id=target_sa_id,
        real_energy=energy,
        metadata={
            "target_sa_id": target_sa_id,
            "ledger_source": "external",
        },
    )

