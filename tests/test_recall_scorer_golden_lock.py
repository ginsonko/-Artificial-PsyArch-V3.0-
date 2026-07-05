from __future__ import annotations

from apv3test.config import APV3_NATIVE_PRESET, LEGACY_AUDIT_PRESET, LEGACY_RUNTIME_PRESET
from apv3test.runtime import score_recall_candidate


def _candidate_features() -> dict[str, float]:
    return {
        "label": 0.8,
        "display": 0.2,
        "bigram": 0.3,
        "focus": 0.4,
        "state_match": 0.5,
        "energy": 0.6,
        "sequence": 0.7,
        "posting": 0.9,
        "vector": 0.25,
        "numeric": 0.11,
        "relation": 0.12,
        "learned_similarity": 0.13,
        "learned_vector": 0.14,
    }


def test_legacy_runtime_preset_matches_named_weight_sum() -> None:
    result = score_recall_candidate(_candidate_features(), preset=LEGACY_RUNTIME_PRESET)

    expected = (
        0.8 * 1.15
        + 0.2 * 0.45
        + 0.3 * 0.90
        + 0.4 * 0.70
        + 0.5 * 0.55
        + 0.6 * 1.35
        + 0.7 * 0.80
        + 0.9 * 0.35
        + 0.25 * 0.40
        + 0.11 * 1.00
        + 0.12 * 1.00
        + 0.13 * 1.00
        + 0.14 * 4.50
    )
    assert result.preset_name == "legacy_runtime_compat"
    assert result.total == round(expected, 6)
    assert result.components["learned_vector"]["enabled"] is True


def test_legacy_audit_preset_is_explicit_not_forked_magic_zero() -> None:
    result = score_recall_candidate(_candidate_features(), preset=LEGACY_AUDIT_PRESET)

    assert result.preset_name == "legacy_audit_exact_compat"
    assert result.components["posting"]["enabled"] is False
    assert result.components["numeric"]["enabled"] is False
    assert result.components["relation"]["enabled"] is False
    assert result.components["learned_vector"]["enabled"] is False
    assert result.trace_only["learned_vector"] == 0.14


def test_apv3_native_keeps_learned_vector_trace_only() -> None:
    result = score_recall_candidate(_candidate_features(), preset=APV3_NATIVE_PRESET)

    without_learned_vector = score_recall_candidate(
        {**_candidate_features(), "learned_vector": 999.0},
        preset=APV3_NATIVE_PRESET,
    )
    assert result.components["learned_vector"]["enabled"] is False
    assert without_learned_vector.total == result.total
    assert without_learned_vector.trace_only["learned_vector"] == 999.0
