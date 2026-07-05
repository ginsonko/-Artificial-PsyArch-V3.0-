from __future__ import annotations

from runtime.cognitive.marker.spawn_perceived import spawn_perceived
from runtime.cognitive.state_pool.state_pool import StatePool
from runtime.sensor_adapters.vision.quantized_frame import (
    VisualFrameQuantizer,
    VisualObjectObservation,
)


def test_visual_quantizer_emits_multichannel_normalized_sa_events() -> None:
    events = VisualFrameQuantizer().events_from_objects(
        (
            VisualObjectObservation(
                object_id="obj-1",
                color_bucket="yellow",
                shape_bucket="apple_like_round",
                x=0.1,
                y=0.5,
            ),
        ),
        start_tick=3,
        frame_id="frame-1",
    )

    ids = {event.sa_id for event in events}
    assert "vision::color::yellow::obj-1" in ids
    assert "vision::shape::apple_like_round::obj-1" in ids
    assert "vision::x_bucket::left::obj-1" in ids
    assert "vision::y_bucket::middle::obj-1" in ids
    assert all(event.channel_signature[0] == "vision" for event in events)


def test_visual_events_enter_state_pool_as_first_class_perceived_sa() -> None:
    state_pool = StatePool()
    events = VisualFrameQuantizer().events_from_objects(
        (
            VisualObjectObservation(
                object_id="obj-2",
                color_bucket="yellow",
                shape_bucket="apple_like_round",
                x=0.2,
                y=0.4,
            ),
        ),
        start_tick=10,
        frame_id="frame-2",
    )

    for event in events:
        item = state_pool.observe_external(event, tick=event.tick)
        marker = spawn_perceived(event, tick=event.tick)
        state_pool.observe_external(marker, tick=event.tick)
        assert item.source == "vision_sensor"

    color_item = state_pool.get("vision::color::yellow::obj-2")
    marker_item = state_pool.get("marker::PERCEIVED::vision::color::yellow::obj-2")

    assert color_item is not None
    assert marker_item is not None
    assert color_item.gain_ledger.gain_by_source["external"] > 0.0
    assert marker_item.gain_ledger.gain_by_source["external"] > 0.0
