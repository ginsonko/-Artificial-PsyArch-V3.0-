from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Iterable

from runtime.cognitive.cognitive_feelings.epistemic_source_feelings import (
    EpistemicFeelingSnapshot,
    compute_epistemic_source_feelings,
)
from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.sdpl.packet import FeelingValue
from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


CORE_FEELING_KEYS = (
    "fluency",
    "boredom",
    "fulfillment",
    "satisfaction",
)


@dataclass(frozen=True)
class CognitiveFeelingSnapshot:
    core: dict[str, float]
    epistemic: EpistemicFeelingSnapshot

    def all_values(self) -> dict[str, float]:
        """@op_count: O(feeling_count)."""
        values = dict(self.core)
        values.update(self.epistemic.values)
        return values

    def to_packet_feelings(self) -> tuple[FeelingValue, ...]:
        """@op_count: O(feeling_count)."""
        values = self.all_values()
        return tuple(FeelingValue(key=key, value=value) for key, value in values.items())


def build_cognitive_feelings(
    item: StateItem,
    markers: Iterable[MarkerEvent] = (),
) -> CognitiveFeelingSnapshot:
    """@op_count: O(marker_count + ledger_source_count)."""
    core = _compute_core_cfs(item)
    epistemic = compute_epistemic_source_feelings(item, markers)
    return CognitiveFeelingSnapshot(core=core, epistemic=epistemic)


def _compute_core_cfs(item: StateItem) -> dict[str, float]:
    fluency = _sigmoid_raw((item.real_energy + item.attention_energy) - (item.cognitive_pressure + item.fatigue))
    boredom = _sigmoid_raw(item.fatigue + (1.0 - item.gain_ledger.endogenous_share()) - item.real_energy)
    fulfillment = _sigmoid_raw(item.virtual_energy - item.cognitive_pressure)
    satisfaction = _sigmoid_raw(item.gain_ledger.gain_by_source.get("feedback", 0.0) + item.real_energy - item.fatigue)
    return {
        "fluency": _clamp01(fluency),
        "boredom": _clamp01(boredom),
        "fulfillment": _clamp01(fulfillment),
        "satisfaction": _clamp01(satisfaction),
    }


def _sigmoid_raw(value: float) -> float:
    slope = float(load_constant("cognitive_feelings.sigmoid_slope"))
    return 1.0 / (1.0 + exp(-float(value) * slope))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
