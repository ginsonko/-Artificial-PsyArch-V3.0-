from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml


@dataclass(frozen=True)
class AudioFrame:
    frame_id: str
    band_energies: dict[str, float]
    rhythm_bucket: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class AudioBandEvent:
    tick: int
    frame_id: str
    channel: str
    value: str
    real_energy: float
    origin: str = "audio_sensor"
    family: str = "percept"
    channel_signature: tuple[str, ...] = ("audio",)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def sa_id(self) -> str:
        return f"audio::{self.channel}::{self.value}::{self.frame_id}"

    @property
    def label(self) -> str:
        return self.value


class AudioFilterbankAdapter:
    def events_from_frames(
        self,
        frames: Iterable[AudioFrame],
        *,
        start_tick: int,
    ) -> tuple[AudioBandEvent, ...]:
        events: list[AudioBandEvent] = []
        for offset, frame in enumerate(frames):
            tick = int(start_tick) + offset
            events.extend(self._events_for_frame(frame, tick=tick))
        return tuple(events)

    def _events_for_frame(self, frame: AudioFrame, *, tick: int) -> tuple[AudioBandEvent, ...]:
        threshold = float(_load_constant("audio_sensor.active_band_threshold"))
        events = [
            AudioBandEvent(
                tick=tick,
                frame_id=frame.frame_id,
                channel="band",
                value=band,
                real_energy=energy,
                channel_signature=("audio", "band"),
                metadata=dict(frame.metadata),
            )
            for band, energy in sorted(frame.band_energies.items())
            if float(energy) > threshold
        ]
        if frame.rhythm_bucket:
            events.append(
                AudioBandEvent(
                    tick=tick,
                    frame_id=frame.frame_id,
                    channel="rhythm",
                    value=frame.rhythm_bucket,
                    real_energy=float(_load_constant("audio_sensor.default_real_energy")),
                    channel_signature=("audio", "rhythm"),
                    metadata=dict(frame.metadata),
                )
            )
        return tuple(events)


def _load_constant(path: str) -> Any:
    data = yaml.safe_load(_constants_path().read_text(encoding="utf-8"))
    node: Any = data
    for part in path.split("."):
        node = node[part]
    return node


def _constants_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "apv3_constants.yaml"
