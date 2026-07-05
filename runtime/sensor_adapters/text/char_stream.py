from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TextCharEvent:
    tick: int
    char: str
    index: int
    utterance_id: str
    origin: str
    sa_id: str
    family: str = "text_char"
    label: str = ""
    real_energy: float = 1.0
    channel_signature: tuple[str, ...] = ("text", "char")
    metadata: dict[str, object] = field(default_factory=dict)


class TextCharStream:
    """Sparse text burst adapter that emits one normalized char SA per tick."""

    def events_from_text(
        self,
        text: str,
        *,
        start_tick: int = 0,
        utterance_id: str = "utterance",
        origin: str = "user_text",
        chars_per_tick: int = 1,
    ) -> tuple[TextCharEvent, ...]:
        chars = tuple(text)
        step = max(1, int(chars_per_tick))
        events: list[TextCharEvent] = []
        for index, char in enumerate(chars):
            tick = int(start_tick) + index // step
            events.append(
                TextCharEvent(
                    tick=tick,
                    char=char,
                    index=index,
                    utterance_id=utterance_id,
                    origin=origin,
                    sa_id=f"text_char::{char}",
                    label=char,
                    metadata={
                        "utterance_id": utterance_id,
                        "char_index": index,
                        "origin": origin,
                    },
                )
            )
        return tuple(events)

