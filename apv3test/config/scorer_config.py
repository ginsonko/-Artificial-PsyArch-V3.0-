from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class APV3ScoreWeights:
    """Named recall score weights.

    The default values mirror the legacy APV2.1 scorer so Phase0.2 can build a
    golden-lock without changing behavior. APV3 strategy code should select a
    preset explicitly instead of relying on hidden inline constants.
    """

    label: float = 1.15
    display: float = 0.45
    bigram: float = 0.90
    focus: float = 0.70
    state_match: float = 0.55
    energy: float = 1.35
    sequence: float = 0.80
    posting: float = 0.35
    vector: float = 0.40
    numeric: float = 1.00
    relation: float = 1.00
    learned_similarity: float = 1.00
    learned_vector: float = 4.50


@dataclass(frozen=True)
class APV3ScorerPreset:
    """Feature policy for the single recall scorer.

    A disabled feature is not a magic zero. It is an explicit policy decision
    recorded in the preset name and included in the score breakdown.
    """

    name: str
    enabled_features: frozenset[str]
    learned_vector_trace_only: bool = True
    notes: tuple[str, ...] = ()

    def enables(self, feature: str) -> bool:
        return feature in self.enabled_features


CORE_FEATURES = frozenset(
    {
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
    }
)


APV3_NATIVE_PRESET = APV3ScorerPreset(
    name="apv3_native",
    enabled_features=CORE_FEATURES - {"learned_vector"},
    learned_vector_trace_only=True,
    notes=(
        "learned_vector is visible in breakdown but cannot define policy",
        "Cn successor evidence must still come from explicit successor edges",
    ),
)


LEGACY_RUNTIME_PRESET = APV3ScorerPreset(
    name="legacy_runtime_compat",
    enabled_features=CORE_FEATURES,
    learned_vector_trace_only=False,
    notes=("compatibility preset for golden-lock only",),
)


LEGACY_AUDIT_PRESET = APV3ScorerPreset(
    name="legacy_audit_exact_compat",
    enabled_features=CORE_FEATURES - {"posting", "numeric", "relation", "learned_vector"},
    learned_vector_trace_only=True,
    notes=(
        "audit exact compatibility must be explicit, not a forked scorer",
        "posting/numeric/relation are disabled by preset policy",
    ),
)


@dataclass(frozen=True)
class APV3RecallConfig:
    weights: APV3ScoreWeights = field(default_factory=APV3ScoreWeights)
    default_preset: APV3ScorerPreset = APV3_NATIVE_PRESET

