from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Iterable

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.sdpl.packet import FeelingValue
from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


EPISTEMIC_FEELING_KEYS = (
    "reality_sense",
    "imagination_sense",
    "hearsay_sense",
    "guess_sense",
    "incongruity",
)


@dataclass(frozen=True)
class EpistemicFeelingSnapshot:
    values: dict[str, float]
    features: dict[str, float]

    def to_packet_feelings(self) -> tuple[FeelingValue, ...]:
        """@op_count: O(feeling_count)."""
        return tuple(
            FeelingValue(key=key, value=self.values.get(key, 0.0))
            for key in EPISTEMIC_FEELING_KEYS
        )


def compute_epistemic_source_feelings(
    item: StateItem,
    markers: Iterable[MarkerEvent],
) -> EpistemicFeelingSnapshot:
    """@op_count: O(marker_count + ledger_source_count)."""
    marker_tuple = tuple(markers)
    perceived_signal = _marker_signal(marker_tuple, "PERCEIVED")
    imagined_signal = _marker_signal(marker_tuple, "IMAGINED")
    hearsay_signal = _marker_signal(marker_tuple, "HEARSAY")
    inferred_signal = _marker_signal(marker_tuple, "INFERRED")
    correction_signal = _marker_signal(marker_tuple, "CORRECTION")
    external_share = _external_share(item)
    endogenous_share = item.gain_ledger.endogenous_share()
    no_live_external = 1.0 - external_share
    low_grasp = _metadata_signal(item, "low_grasp_score")
    candidate_entropy = _metadata_signal(item, "candidate_entropy")
    prediction_mismatch = max(correction_signal, _metadata_signal(item, "prediction_mismatch"))

    reality = _average((perceived_signal, external_share))
    imagination = _average((imagined_signal, endogenous_share, no_live_external))
    hearsay = hearsay_signal
    guess = _average((inferred_signal, low_grasp, candidate_entropy))
    incongruity = reality * prediction_mismatch

    values = {
        "reality_sense": _clamp01(reality),
        "imagination_sense": _clamp01(imagination),
        "hearsay_sense": _clamp01(hearsay),
        "guess_sense": _clamp01(guess),
        "incongruity": _clamp01(incongruity),
    }
    features = {
        "PERCEIVED_marker_signal": perceived_signal,
        "IMAGINED_marker_signal": imagined_signal,
        "HEARSAY_marker_signal": hearsay_signal,
        "INFERRED_marker_signal": inferred_signal,
        "CORRECTION_marker_signal": correction_signal,
        "external_share": external_share,
        "endogenous_share": endogenous_share,
        "no_live_external": no_live_external,
        "low_grasp_score": low_grasp,
        "candidate_entropy": candidate_entropy,
        "prediction_mismatch": prediction_mismatch,
    }
    return EpistemicFeelingSnapshot(values=values, features=features)


def marker_energy_signal(markers: Iterable[MarkerEvent], kind: str) -> float:
    """@op_count: O(marker_count)."""
    energy = sum(marker.real_energy for marker in markers if marker.kind == kind)
    if energy <= 0.0:
        return float(load_constant("cognitive_feelings.absent_marker_signal"))
    return _sigmoid_energy(energy)


def _marker_signal(markers: tuple[MarkerEvent, ...], kind: str) -> float:
    return marker_energy_signal(markers, kind)


def _metadata_signal(item: StateItem, key: str) -> float:
    return _clamp01(float(item.metadata.get(key, 0.0)))


def _external_share(item: StateItem) -> float:
    total = item.gain_ledger.total()
    if total <= 0.0:
        return 0.0
    return _clamp01(item.gain_ledger.gain_by_source.get("external", 0.0) / total)


def _sigmoid_energy(value: float) -> float:
    slope = float(load_constant("cognitive_feelings.sigmoid_slope"))
    midpoint = float(load_constant("cognitive_feelings.sigmoid_midpoint"))
    scaled = (float(value) - midpoint) * slope
    return 1.0 / (1.0 + exp(-scaled))


def _average(values: tuple[float, ...]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
