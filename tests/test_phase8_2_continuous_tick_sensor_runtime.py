from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.runtime.tick_loop import ContinuousTickRuntime, phase8_2_trace_summary
from runtime.cognitive.state_pool.state_pool import StatePool
from runtime.sensor_adapters.text.char_stream import TextCharStream


def test_text_char_stream_emits_sparse_micro_events_one_char_per_tick() -> None:
    events = TextCharStream().events_from_text("你好", start_tick=10, utterance_id="u1")

    assert tuple(event.tick for event in events) == (10, 11)
    assert tuple(event.char for event in events) == ("你", "好")
    assert tuple(event.sa_id for event in events) == ("text_char::你", "text_char::好")
    assert all(event.channel_signature == ("text", "char") for event in events)


def test_continuous_tick_runtime_keeps_idle_ticks_after_sparse_text_input() -> None:
    result = ContinuousTickRuntime().run_text_message(
        "你好",
        start_tick=5,
        utterance_id="u2",
        idle_ticks_after=2,
    )
    summary = phase8_2_trace_summary(result)

    assert summary["ticks"] == (5, 6, 7, 8)
    assert summary["input_event_counts"] == (1, 1, 0, 0)
    assert summary["idle_ticks"] == (7, 8)
    assert result.traces[0].draft_action == "noop"
    assert result.traces[-1].idle is True


def test_state_pool_tracks_text_sa_energy_and_decays_on_idle_tick() -> None:
    runtime = ContinuousTickRuntime(state_pool=StatePool())
    result = runtime.run_text_message("你", start_tick=1, idle_ticks_after=1)
    item = result.state_pool.get("text_char::你")

    assert item is not None
    assert item.real_energy > 0.0
    assert item.cognitive_pressure == item.real_energy - item.virtual_energy
    assert result.traces[0].state_pool_top[0]["sa_id"] == "text_char::你"
    assert result.traces[1].state_pool_top[0]["R"] < result.traces[0].state_pool_top[0]["R"]


def test_phase8_2_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "8.2"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 8.2 deliverables present" in completed.stdout

