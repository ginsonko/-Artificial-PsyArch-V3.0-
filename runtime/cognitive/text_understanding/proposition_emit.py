from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from runtime.cognitive.marker.spawn_hearsay import spawn_hearsay


@dataclass(frozen=True)
class PropositionEvent:
    tick: int
    text: str
    utterance_id: str
    speaker_entity_id: str
    sa_id: str
    family: str = "proposition"
    origin: str = "user_text"
    real_energy: float = 1.0
    channel_signature: tuple[str, ...] = ("text", "proposition")
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return self.text


def emit_proposition_from_text_events(
    events: Sequence[object],
    *,
    speaker_entity_id: str,
) -> PropositionEvent | None:
    """@op_count: O(chars)."""
    if not events:
        return None
    text = "".join(str(getattr(event, "char")) for event in events)
    utterance_id = str(getattr(events[0], "utterance_id"))
    tick = int(getattr(events[-1], "tick"))
    return PropositionEvent(
        tick=tick,
        text=text,
        utterance_id=utterance_id,
        speaker_entity_id=speaker_entity_id,
        sa_id=f"proposition::{utterance_id}",
        metadata={
            "utterance_id": utterance_id,
            "speaker_entity_id": speaker_entity_id,
            "ledger_source": "external",
        },
    )


def emit_proposition_and_hearsay(
    events: Sequence[object],
    *,
    speaker_entity_id: str,
) -> tuple[PropositionEvent, object] | None:
    """@op_count: O(chars)."""
    proposition = emit_proposition_from_text_events(
        events,
        speaker_entity_id=speaker_entity_id,
    )
    if proposition is None:
        return None
    marker = spawn_hearsay(
        proposition,
        tick=proposition.tick,
        speaker_entity_id=speaker_entity_id,
    )
    return proposition, marker

