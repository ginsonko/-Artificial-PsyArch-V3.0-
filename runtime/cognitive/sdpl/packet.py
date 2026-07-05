from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Iterable

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass(frozen=True)
class FeelingValue:
    key: str
    value: float


@dataclass(frozen=True)
class LearningPacket:
    content_sas: tuple[StateItem, ...] = ()
    source_markers: tuple[MarkerEvent, ...] = ()
    feeling_sas: tuple[FeelingValue, ...] = ()
    slot_context: tuple[str, ...] = ()

    def packet_key(self) -> tuple[object, object, object, object]:
        """@op_count: O(content + source + feeling)."""
        content_with_bucket = frozenset(
            (_content_identity(item), _quantize_r(item.real_energy))
            for item in self.content_sas
        )
        source_energy = _source_energy(self.source_markers)
        source_with_bucket = frozenset(
            (kind, _quantize_r(energy))
            for kind, energy in source_energy.items()
        )
        source_with_bucket = source_with_bucket | frozenset(
            ("SUBSTRATE", str(item.metadata.get("perceived_substrate") or item.metadata.get("substrate")), 1)
            for item in self.content_sas
            if item.metadata.get("perceived_substrate") or item.metadata.get("substrate")
        )
        if self.slot_context:
            source_with_bucket = source_with_bucket | frozenset(
                ("SLOT_CONTEXT", str(item), 1) for item in self.slot_context
            )
        dominant = _dominant_source(source_energy)
        feeling_with_bucket = frozenset(
            (feeling.key, _quantize_feeling(feeling.value))
            for feeling in self.feeling_sas
        )
        return (content_with_bucket, source_with_bucket, dominant, feeling_with_bucket)

    def content_key(self) -> object:
        """@op_count: O(content)."""
        return self.packet_key()[0]

    def source_key(self) -> object:
        """@op_count: O(source)."""
        return self.packet_key()[1]

    def feeling_key(self) -> object:
        """@op_count: O(feeling)."""
        return self.packet_key()[3]


def make_packet(
    *,
    content_sas: Iterable[StateItem] = (),
    source_markers: Iterable[MarkerEvent] = (),
    feeling_sas: Iterable[FeelingValue] = (),
    slot_context: Iterable[str] = (),
) -> LearningPacket:
    """@op_count: O(content + source + feeling)."""
    return LearningPacket(
        content_sas=tuple(content_sas),
        source_markers=tuple(source_markers),
        feeling_sas=tuple(feeling_sas),
        slot_context=tuple(slot_context),
    )


def _source_energy(markers: tuple[MarkerEvent, ...]) -> dict[str, float]:
    result: dict[str, float] = {}
    for marker in markers:
        substrate = str(marker.metadata.get("substrate", "unspecified"))
        key = f"{marker.kind}:{substrate}"
        result[key] = result.get(key, 0.0) + marker.real_energy
    return result


def _content_identity(item: StateItem) -> str:
    """@op_count: O(metadata_size)."""
    content = item.metadata.get("cognitive_content", item.sa_id)
    payload: dict[str, object] = {
        "content": content,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _dominant_source(source_energy: dict[str, float]) -> str | None:
    if not source_energy:
        return None
    return max(source_energy.items(), key=lambda item: (item[1], item[0]))[0]


def _quantize_r(value: float) -> int:
    low = float(load_constant("sdpl.packet_key.R_bucket_low_threshold"))
    high = float(load_constant("sdpl.packet_key.R_bucket_high_threshold"))
    return _quantize_three_bins(value, low, high)


def _quantize_feeling(value: float) -> int:
    low = float(load_constant("sdpl.packet_key.feeling_bucket_low_threshold"))
    high = float(load_constant("sdpl.packet_key.feeling_bucket_high_threshold"))
    return _quantize_three_bins(value, low, high)


def _quantize_three_bins(value: float, low: float, high: float) -> int:
    if value < low:
        return 0
    if value < high:
        return 1
    return 2
