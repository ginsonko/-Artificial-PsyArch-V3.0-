from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml


@dataclass(frozen=True)
class VisualObjectObservation:
    object_id: str
    color_bucket: str
    shape_bucket: str
    x: float
    y: float
    intensity: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class VisualQuantizedEvent:
    tick: int
    frame_id: str
    object_id: str
    channel: str
    value: str
    real_energy: float
    origin: str = "vision_sensor"
    family: str = "percept"
    channel_signature: tuple[str, ...] = ("vision",)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def sa_id(self) -> str:
        return f"vision::{self.channel}::{self.value}::{self.object_id}"

    @property
    def label(self) -> str:
        return self.value


class VisualFrameQuantizer:
    def events_from_objects(
        self,
        objects: Iterable[VisualObjectObservation],
        *,
        start_tick: int,
        frame_id: str,
    ) -> tuple[VisualQuantizedEvent, ...]:
        events: list[VisualQuantizedEvent] = []
        for offset, obj in enumerate(objects):
            tick = int(start_tick) + offset
            events.extend(self._events_for_object(obj, tick=tick, frame_id=frame_id))
        return tuple(events)

    def _events_for_object(
        self,
        obj: VisualObjectObservation,
        *,
        tick: int,
        frame_id: str,
    ) -> tuple[VisualQuantizedEvent, ...]:
        energy = (
            float(obj.intensity)
            if obj.intensity is not None
            else float(_load_constant("vision_sensor.default_real_energy"))
        )
        x_bucket = _x_bucket(float(obj.x))
        y_bucket = _y_bucket(float(obj.y))
        base = {
            "frame_id": frame_id,
            "object_id": obj.object_id,
            **obj.metadata,
        }
        return (
            _event(tick, frame_id, obj.object_id, "color", obj.color_bucket, energy, base),
            _event(tick, frame_id, obj.object_id, "shape", obj.shape_bucket, energy, base),
            _event(tick, frame_id, obj.object_id, "x_bucket", x_bucket, energy, base),
            _event(tick, frame_id, obj.object_id, "y_bucket", y_bucket, energy, base),
        )


def _event(
    tick: int,
    frame_id: str,
    object_id: str,
    channel: str,
    value: str,
    energy: float,
    metadata: dict[str, object],
) -> VisualQuantizedEvent:
    return VisualQuantizedEvent(
        tick=tick,
        frame_id=frame_id,
        object_id=object_id,
        channel=channel,
        value=value,
        real_energy=energy,
        channel_signature=("vision", channel),
        metadata=dict(metadata),
    )


def _x_bucket(value: float) -> str:
    if value < float(_load_constant("vision_sensor.x_left_threshold")):
        return "left"
    if value > float(_load_constant("vision_sensor.x_right_threshold")):
        return "right"
    return "center"


def _y_bucket(value: float) -> str:
    if value < float(_load_constant("vision_sensor.y_top_threshold")):
        return "top"
    if value > float(_load_constant("vision_sensor.y_bottom_threshold")):
        return "bottom"
    return "middle"


def _load_constant(path: str) -> Any:
    data = yaml.safe_load(_constants_path().read_text(encoding="utf-8"))
    node: Any = data
    for part in path.split("."):
        node = node[part]
    return node


def _constants_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "apv3_constants.yaml"
