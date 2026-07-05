from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.state_pool.state_pool import load_constant


@dataclass(frozen=True)
class PromotionEvidence:
    effect_size: float
    p_value: float
    held_out_observations: int
    effect_source: str
    training_effect_size: float | None = None


@dataclass(frozen=True)
class TrustGateDecision:
    passed: bool
    status: str
    effect_size: float
    p_value_threshold: float
    min_observations: int
    effect_source: str


def trust_promote_gate(evidence: PromotionEvidence, *, trust_score: float) -> TrustGateDecision:
    """@op_count: O(1)."""
    trust_norm = _clamp01(float(trust_score))
    p_threshold = _interpolate(
        float(load_constant("curriculum.trust_gate.p_value_base_threshold")),
        float(load_constant("curriculum.trust_gate.p_value_trusted_threshold")),
        trust_norm,
    )
    min_observations = int(
        round(
            _interpolate(
                float(load_constant("curriculum.trust_gate.min_observations_base")),
                float(load_constant("curriculum.trust_gate.min_observations_trusted")),
                trust_norm,
            )
        )
    )
    hard_floor = float(load_constant("curriculum.trust_gate.effect_size_hard_min"))
    if evidence.effect_source != "held_out_cold_fork":
        return _decision(evidence, "reject_effect_source_not_held_out", p_threshold, min_observations)
    if float(evidence.effect_size) < hard_floor:
        return _decision(evidence, "reject_effect_size_below_hard_floor", p_threshold, min_observations)
    if int(evidence.held_out_observations) < min_observations:
        return _decision(evidence, "reject_insufficient_held_out", p_threshold, min_observations)
    if float(evidence.p_value) > p_threshold:
        return _decision(evidence, "reject_p_value", p_threshold, min_observations)
    return _decision(evidence, "promoted", p_threshold, min_observations, passed=True)


def _decision(
    evidence: PromotionEvidence,
    status: str,
    p_threshold: float,
    min_observations: int,
    *,
    passed: bool = False,
) -> TrustGateDecision:
    """@op_count: O(1)."""
    return TrustGateDecision(
        passed=passed,
        status=status,
        effect_size=float(evidence.effect_size),
        p_value_threshold=float(p_threshold),
        min_observations=int(min_observations),
        effect_source=evidence.effect_source,
    )


def _interpolate(start: float, end: float, amount: float) -> float:
    """@op_count: O(1)."""
    return float(start) + (float(end) - float(start)) * _clamp01(amount)


def _clamp01(value: float) -> float:
    """@op_count: O(1)."""
    return max(0.0, min(1.0, float(value)))

