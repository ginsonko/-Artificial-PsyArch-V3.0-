from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class APV3DraftIntrospectionConfig:
    """Named parameters for draft-introspection prototype observation."""

    feature_width: int = 7
    theta_spawn: float = 1.35
    tau_init: float = 0.35
    tau_floor: float = 0.05
    eta_mu: float = 0.28
    half_life_decay: float = 0.9659363289248456
    eviction_floor: float = 0.01
    max_prototypes: int = 64
    alpha_real_energy: float = 1.0
    beta_pressure: float = 0.35
    phi_pooling_schema_version: str = "phi6.draft_to_vec.v1"


@dataclass(frozen=True)
class APV3CooccurrenceConfig:
    """Named parameters for sparse feeling-expression association."""

    schema_version: int = 1
    half_life_decay: float = 0.99
    eviction_floor: float = 1e-6
    cooccurrence_lr: float = 1.0
    cooccurrence_max_weight: float = 1.0
    gamma_perception_other: float = 1.0
    gamma_teacher_reply: float = 1.0
    gamma_self_emission: float = 0.0
    seed_initial_support: float = 1.0
    expression_style_bias: float = 0.3
    test_learning_delta_min: float = 0.05
    test_target_distractor_ratio_min: float = 1.5


@dataclass(frozen=True)
class APV3ReplyPressureConfig:
    """Named parameters for state-SA-derived reply pressure."""

    pressure_half_life_decay: float = 0.85
    pressure_eviction_floor: float = 0.02
    silence_normalizer_ticks: int = 6
    silence_half_life_decay: float = 0.75
    reply_pressure_threshold: float = 0.62
    reply_pressure_neutral: float = 0.5
    external_query_energy: float = 1.0
    recent_commit_energy: float = 1.0
