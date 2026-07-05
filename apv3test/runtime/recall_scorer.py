from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from apv3test.config.scorer_config import (
    APV3RecallConfig,
    APV3ScoreWeights,
    APV3ScorerPreset,
)


FEATURE_ORDER = (
    "label",
    "display",
    "bigram",
    "focus",
    "state_match",
    "energy",
    "sequence",
    "posting",
    "vector",
    "numeric",
    "relation",
    "learned_similarity",
    "learned_vector",
)


@dataclass(frozen=True)
class ScoreBreakdown:
    preset_name: str
    total: float
    components: dict[str, dict[str, float | bool]]
    trace_only: dict[str, float]


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _weight_for(weights: APV3ScoreWeights, feature: str) -> float:
    return float(getattr(weights, feature))


def score_recall_candidate(
    features: Mapping[str, object],
    *,
    config: APV3RecallConfig | None = None,
    preset: APV3ScorerPreset | None = None,
) -> ScoreBreakdown:
    """Single pure recall scorer for runtime and audit presets.

    This function is deliberately boring: no lexical shortcut, no literal
    response lookup, no hidden learned-vector bridge. All differences are
    visible through the supplied preset and the returned breakdown.
    """

    cfg = config or APV3RecallConfig()
    active_preset = preset or cfg.default_preset
    total = 0.0
    components: dict[str, dict[str, float | bool]] = {}
    trace_only: dict[str, float] = {}

    for feature in FEATURE_ORDER:
        value = _as_float(features.get(feature, 0.0))
        weight = _weight_for(cfg.weights, feature)
        enabled = active_preset.enables(feature)
        if feature == "learned_vector" and active_preset.learned_vector_trace_only:
            enabled = False
            trace_only[feature] = round(value, 6)
        contribution = value * weight if enabled else 0.0
        total += contribution
        components[feature] = {
            "value": round(value, 6),
            "weight": round(weight, 6),
            "enabled": bool(enabled),
            "contribution": round(contribution, 6),
        }

    return ScoreBreakdown(
        preset_name=active_preset.name,
        total=round(total, 6),
        components=components,
        trace_only=trace_only,
    )
