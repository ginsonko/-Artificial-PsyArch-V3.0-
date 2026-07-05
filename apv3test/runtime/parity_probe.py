from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from apv3test.config import APV3_NATIVE_PRESET, APV3RecallConfig, APV3ScorerPreset
from apv3test.runtime.recall_scorer import score_recall_candidate


@dataclass(frozen=True)
class ParityProbeCase:
    name: str
    transition_source: str
    action: str
    focus_tokens: tuple[str, ...] = ()
    expected_top_bn: str | None = None
    expected_successor: str | None = None
    expected_paradigm: str | None = None


@dataclass(frozen=True)
class ProbeResult:
    case_name: str
    bn_top: list[dict[str, Any]]
    cn_successors: list[dict[str, Any]]
    learned_tokens: list[dict[str, Any]]
    paradigms: list[dict[str, Any]]
    action_outcome: dict[str, Any]
    percept_prototypes: list[dict[str, Any]]


def run_parity_probe(
    state: Mapping[str, Any],
    cases: Iterable[ParityProbeCase],
    *,
    config: APV3RecallConfig | None = None,
    preset: APV3ScorerPreset = APV3_NATIVE_PRESET,
    top_k: int = 3,
) -> list[ProbeResult]:
    return [
        _run_case(state, case, config=config, preset=preset, top_k=top_k)
        for case in cases
    ]


def assert_probe_parity(left: list[ProbeResult], right: list[ProbeResult]) -> None:
    left_canon = [_canonical_result(result) for result in left]
    right_canon = [_canonical_result(result) for result in right]
    if left_canon != right_canon:
        raise AssertionError({"left": left_canon, "right": right_canon})


def _run_case(
    state: Mapping[str, Any],
    case: ParityProbeCase,
    *,
    config: APV3RecallConfig | None,
    preset: APV3ScorerPreset,
    top_k: int,
) -> ProbeResult:
    return ProbeResult(
        case_name=case.name,
        bn_top=_bn_top(state, case, config=config, preset=preset, top_k=top_k),
        cn_successors=_successors(state, case.transition_source),
        learned_tokens=_learned_tokens(state, case.focus_tokens),
        paradigms=_paradigms(state, case.name),
        action_outcome=_action_outcome(state, case.action),
        percept_prototypes=_percept_prototypes(state, case.name),
    )


def _bn_top(
    state: Mapping[str, Any],
    case: ParityProbeCase,
    *,
    config: APV3RecallConfig | None,
    preset: APV3ScorerPreset,
    top_k: int,
) -> list[dict[str, Any]]:
    rows = []
    for candidate in _list_of_dicts(state.get("bn_candidates")):
        probe_features = candidate.get("probe_features", {})
        if not isinstance(probe_features, dict) or case.name not in probe_features:
            continue
        features = probe_features[case.name]
        if not isinstance(features, dict):
            continue
        score = score_recall_candidate(features, config=config, preset=preset)
        rows.append(
            {
                "candidate_id": str(candidate.get("candidate_id", "")),
                "domain": str(candidate.get("domain", "")),
                "score": score.total,
                "preset": score.preset_name,
                "trace_only": score.trace_only,
            }
        )
    return sorted(rows, key=lambda row: (-float(row["score"]), str(row["candidate_id"])))[: max(0, int(top_k))]


def _successors(state: Mapping[str, Any], source: str) -> list[dict[str, Any]]:
    rows = []
    for item in _list_of_dicts(state.get("transitions")):
        if str(item.get("source", "")) != source:
            continue
        rows.append(
            {
                "source": str(item.get("source", "")),
                "target": str(item.get("target", "")),
                "support": _round_float(item.get("support")),
            }
        )
    return sorted(rows, key=lambda row: (-float(row["support"]), row["target"]))


def _learned_tokens(state: Mapping[str, Any], tokens: tuple[str, ...]) -> list[dict[str, Any]]:
    online_embedding = state.get("online_embedding", {})
    token_payloads = online_embedding.get("tokens", {}) if isinstance(online_embedding, dict) else {}
    if not isinstance(token_payloads, dict):
        return []
    rows = []
    for token in tokens:
        payload = token_payloads.get(token)
        if isinstance(payload, dict):
            rows.append(
                {
                    "token": token,
                    "support": _round_float(payload.get("support")),
                    "vector": [_round_float(value) for value in payload.get("vector", [])],
                }
            )
        elif payload is not None:
            rows.append({"token": token, "support": 0.0, "vector": [_round_float(value) for value in payload]})
    return rows


def _paradigms(state: Mapping[str, Any], case_name: str) -> list[dict[str, Any]]:
    rows = []
    for item in _list_of_dicts(state.get("paradigms")):
        if case_name not in _probe_tags(item):
            continue
        rows.append(
            {
                "pid": str(item.get("pid", "") or item.get("id", "")),
                "support": _round_float(item.get("support")),
                "conf": _round_float(item.get("conf")),
                "slot_types": list(item.get("slot_types", [])) if isinstance(item.get("slot_types", []), list) else [],
            }
        )
    return sorted(rows, key=lambda row: (-float(row["support"]), row["pid"]))


def _action_outcome(state: Mapping[str, Any], action: str) -> dict[str, Any]:
    outcomes = state.get("action_outcomes", {})
    if not isinstance(outcomes, dict):
        return {}
    payload = outcomes.get(action, {})
    if not isinstance(payload, dict):
        return {"action": action, "value": payload}
    return {
        "action": action,
        "drive_bias": _round_float(payload.get("drive_bias")),
        "reward_support": _round_float(payload.get("reward_support")),
        "punish_support": _round_float(payload.get("punish_support")),
    }


def _percept_prototypes(state: Mapping[str, Any], case_name: str) -> list[dict[str, Any]]:
    rows = []
    for item in _list_of_dicts(state.get("percept_prototypes")):
        if case_name not in _probe_tags(item):
            continue
        rows.append(
            {
                "prototype_id": str(item.get("prototype_id", "") or item.get("id", "")),
                "support": _round_float(item.get("support")),
                "features": item.get("features", {}),
            }
        )
    return sorted(rows, key=lambda row: row["prototype_id"])


def _probe_tags(item: Mapping[str, Any]) -> set[str]:
    tags = item.get("probe_tags", [])
    if not isinstance(tags, list):
        return set()
    return {str(tag) for tag in tags}


def _list_of_dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _round_float(value: object) -> float:
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return 0.0


def _canonical_result(result: ProbeResult) -> dict[str, Any]:
    return {
        "case_name": result.case_name,
        "bn_top": result.bn_top,
        "cn_successors": result.cn_successors,
        "learned_tokens": result.learned_tokens,
        "paradigms": result.paradigms,
        "action_outcome": result.action_outcome,
        "percept_prototypes": result.percept_prototypes,
    }

