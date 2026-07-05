from __future__ import annotations

from runtime.cognitive.marker.events import MarkerEvent, event_value


def spawn_hearsay(
    proposition_event: object,
    *,
    tick: int,
    speaker_entity_id: str,
) -> MarkerEvent:
    """@op_count: O(1)."""
    target_sa_id = str(event_value(proposition_event, "sa_id"))
    energy = float(event_value(proposition_event, "real_energy"))
    return MarkerEvent(
        tick=int(tick),
        kind="HEARSAY",
        target_sa_id=target_sa_id,
        real_energy=energy,
        metadata={
            "target_sa_id": target_sa_id,
            "source_entity_id": speaker_entity_id,
            "ledger_source": "external",
        },
    )

