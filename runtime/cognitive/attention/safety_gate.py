from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass(frozen=True)
class AttentionScoreTrace:
    score: float
    external_score: float
    internal_score: float
    endogenous_share: float
    safety_gate_triggered: bool


def convex_attention_score(item: StateItem) -> AttentionScoreTrace:
    """@op_count: O(ledger_source_count)."""
    external = _external_attention_score(item)
    internal = _internal_attention_score(item)
    endogenous_share = item.gain_ledger.endogenous_share()
    mixed = (1.0 - endogenous_share) * external + endogenous_share * internal
    triggered = external_surprise_safety_gate(item)
    score = external if triggered else mixed
    return AttentionScoreTrace(
        score=score,
        external_score=external,
        internal_score=internal,
        endogenous_share=endogenous_share,
        safety_gate_triggered=triggered,
    )


def external_surprise_safety_gate(item: StateItem) -> bool:
    """@op_count: O(ledger_source_count)."""
    total = item.gain_ledger.total()
    external_share = 0.0 if total <= 0.0 else item.gain_ledger.gain_by_source.get("external", 0.0) / total
    return (
        external_share > float(load_constant("attention.external_dominance_safety_threshold"))
        and item.cognitive_pressure > float(load_constant("attention.surprise_P_threshold"))
    )


def _external_attention_score(item: StateItem) -> float:
    weights = "attention.s_attn_weights"
    return (
        float(load_constant(f"{weights}.beta_P_external")) * item.cognitive_pressure
        + float(load_constant(f"{weights}.beta_R")) * item.real_energy
        + float(load_constant(f"{weights}.beta_A")) * item.attention_energy
        - float(load_constant(f"{weights}.beta_F")) * item.fatigue
    )


def _internal_attention_score(item: StateItem) -> float:
    weights = "attention.s_attn_weights"
    return (
        float(load_constant(f"{weights}.beta_P_internal")) * item.cognitive_pressure
        + float(load_constant(f"{weights}.beta_R")) * item.real_energy
        + float(load_constant(f"{weights}.beta_A_internal")) * item.attention_energy
        - float(load_constant(f"{weights}.beta_F_internal")) * item.fatigue
    )
