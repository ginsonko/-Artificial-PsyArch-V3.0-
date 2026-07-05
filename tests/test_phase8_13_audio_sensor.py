from __future__ import annotations

from runtime.cognitive.marker.spawn_perceived import spawn_perceived
from runtime.cognitive.state_pool.state_pool import StatePool
from runtime.sensor_adapters.audio.filterbank import AudioFilterbankAdapter, AudioFrame


def test_audio_filterbank_emits_band_and_rhythm_sa_events() -> None:
    events = AudioFilterbankAdapter().events_from_frames(
        (
            AudioFrame(
                frame_id="a1",
                band_energies={"low": 0.2, "mid": 0.8, "high": 0.0},
                rhythm_bucket="short_pulse",
            ),
        ),
        start_tick=5,
    )

    ids = {event.sa_id for event in events}
    assert "audio::band::low::a1" in ids
    assert "audio::band::mid::a1" in ids
    assert "audio::band::high::a1" not in ids
    assert "audio::rhythm::short_pulse::a1" in ids


def test_audio_events_enter_state_pool_with_perceived_marker() -> None:
    state_pool = StatePool()
    events = AudioFilterbankAdapter().events_from_frames(
        (AudioFrame(frame_id="a2", band_energies={"mid": 0.9}),),
        start_tick=8,
    )

    for event in events:
        state_pool.observe_external(event, tick=event.tick)
        state_pool.observe_external(spawn_perceived(event, tick=event.tick), tick=event.tick)

    audio_item = state_pool.get("audio::band::mid::a2")
    marker_item = state_pool.get("marker::PERCEIVED::audio::band::mid::a2")

    assert audio_item is not None
    assert marker_item is not None
    assert audio_item.source == "audio_sensor"
