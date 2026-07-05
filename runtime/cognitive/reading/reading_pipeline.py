from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.state_pool.state_pool import load_constant
from runtime.sensor_adapters.text.char_stream import TextCharEvent, TextCharStream


@dataclass(frozen=True)
class ReadingInput:
    text: str
    source: str
    start_tick: int = 0
    document_id: str = "document"


def emit_reading_char_events(reading: ReadingInput) -> tuple[TextCharEvent, ...]:
    """@op_count: O(chars)."""
    source = _normalized_source(reading.source)
    return TextCharStream().events_from_text(
        reading.text,
        start_tick=reading.start_tick,
        utterance_id=reading.document_id,
        origin=source,
        chars_per_tick=int(load_constant("reading.chars_per_tick")),
    )


def _normalized_source(source: str) -> str:
    allowed = tuple(load_constant("reading.allowed_sources"))
    if source in allowed:
        return source
    return "reading"
