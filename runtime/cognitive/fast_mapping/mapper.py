from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass(frozen=True)
class FastMappingCandidate:
    label_sa_id: str
    target_sa_id: str
    score: float
    channel: str


@dataclass(frozen=True)
class FastMappingResult:
    label_sa_id: str
    candidates: tuple[FastMappingCandidate, ...]

    @property
    def best(self) -> FastMappingCandidate | None:
        return self.candidates[0] if self.candidates else None


def fast_map_label_to_candidates(
    label_item: StateItem,
    candidates: Iterable[StateItem],
) -> FastMappingResult:
    """@op_count: O(candidate_count log candidate_count)."""
    scored = tuple(
        FastMappingCandidate(
            label_sa_id=label_item.sa_id,
            target_sa_id=item.sa_id,
            score=_candidate_score(item),
            channel=_dominant_channel(item),
        )
        for item in candidates
    )
    ordered = tuple(sorted(scored, key=lambda item: (item.score, item.target_sa_id), reverse=True))
    return FastMappingResult(label_sa_id=label_item.sa_id, candidates=ordered)


def inject_epistemic_drive_for_mapping_gap(item: StateItem, *, known_support: float) -> float:
    """@op_count: O(1)."""
    gap = max(0.0, 1.0 - float(known_support))
    gain = gap * float(load_constant("fast_mapping.epistemic_drive_gain"))
    item.cognitive_pressure = item.cognitive_pressure + gain
    item.attention_energy = item.attention_energy + gain
    item.gain_ledger.inject("unfinished_pressure", gain)
    return gain


def reverse_imagine_from_mapping(mapping: FastMappingCandidate, *, support: float) -> StateItem | None:
    """@op_count: O(1)."""
    if float(support) < float(load_constant("fast_mapping.reverse_imagination_min_support")):
        return None
    item = StateItem(
        sa_id=f"imagined::{mapping.target_sa_id}",
        family="percept",
        label=mapping.target_sa_id,
        real_energy=float(support),
        attention_energy=float(support),
        cognitive_pressure=max(0.0, 1.0 - float(support)),
        channel_signature=("vision", "imagined"),
        source="reverse_imagination",
        metadata={
            "label_sa_id": mapping.label_sa_id,
            "target_sa_id": mapping.target_sa_id,
        },
    )
    item.gain_ledger.inject("imagination", float(support))
    return item


def _candidate_score(item: StateItem) -> float:
    return item.real_energy * _channel_weight(item) + item.attention_energy - item.fatigue


def _channel_weight(item: StateItem) -> float:
    channel = _dominant_channel(item)
    if channel == "shape":
        return float(load_constant("fast_mapping.shape_bias_weight"))
    if channel == "color":
        return float(load_constant("fast_mapping.color_bias_weight"))
    if channel in {"x_bucket", "y_bucket", "position"}:
        return float(load_constant("fast_mapping.position_bias_weight"))
    return float(load_constant("fast_mapping.color_bias_weight"))


def _dominant_channel(item: StateItem) -> str:
    for part in item.channel_signature:
        if part != "vision":
            return part
    return ""
