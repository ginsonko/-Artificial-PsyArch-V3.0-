from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.reading.reading_pipeline import ReadingInput, emit_reading_char_events
from runtime.sensor_adapters.text.char_stream import TextCharStream


def test_reading_pipeline_reuses_text_char_stream_with_reading_origin() -> None:
    events = emit_reading_char_events(ReadingInput(text="AP", source="reading", start_tick=5, document_id="doc1"))

    assert tuple(event.char for event in events) == ("A", "P")
    assert tuple(event.tick for event in events) == (5, 6)
    assert all(event.origin == "reading" for event in events)
    assert all(event.family == "text_char" for event in events)
    assert events[0].metadata["utterance_id"] == "doc1"


def test_streaming_and_reading_share_same_char_sa_ids_but_keep_origin_metadata() -> None:
    reading = emit_reading_char_events(ReadingInput(text="AP", source="reading", start_tick=1, document_id="doc"))
    streaming = TextCharStream().events_from_text("AP", start_tick=1, utterance_id="stream", origin="streaming")

    assert tuple(event.sa_id for event in reading) == tuple(event.sa_id for event in streaming)
    assert tuple(event.origin for event in reading) == ("reading", "reading")
    assert tuple(event.origin for event in streaming) == ("streaming", "streaming")


def test_unknown_reading_source_normalizes_to_reading_not_new_channel() -> None:
    events = emit_reading_char_events(ReadingInput(text="A", source="unknown", start_tick=1))

    assert events[0].origin == "reading"
    assert events[0].metadata["origin"] == "reading"


def test_phase10_8_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "10.8"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 10.8 deliverables present" in completed.stdout
