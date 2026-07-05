from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class LearnedToken:
    token: str
    vector: tuple[float, ...]
    support_delta: float


@dataclass(frozen=True)
class LearnedTransition:
    source: str
    target: str
    support_delta: float


@dataclass(frozen=True)
class LearnedParadigm:
    pid: str
    support_delta: float
    conf: float
    slot_types: tuple[str, ...] = ()
    probe_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class LearnedBnCandidate:
    candidate_id: str
    domain: str
    probe_features: Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class LearnedActionOutcome:
    action: str
    drive_bias_delta: float = 0.0
    reward_delta: float = 0.0
    punish_delta: float = 0.0
    support_delta: float = 0.0
    actuator_id: str = ""
    outcome_kind: str = "action"
    context_tags: tuple[str, ...] = ()
    last_tick: int | None = None


@dataclass(frozen=True)
class LearnedPerceptPrototype:
    prototype_id: str
    support_delta: float
    features: Mapping[str, Any] = field(default_factory=dict)
    probe_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class LearningEpisode:
    episode_id: str
    tokens: tuple[LearnedToken, ...] = ()
    transitions: tuple[LearnedTransition, ...] = ()
    paradigms: tuple[LearnedParadigm, ...] = ()
    bn_candidates: tuple[LearnedBnCandidate, ...] = ()
    action_outcomes: tuple[LearnedActionOutcome, ...] = ()
    percept_prototypes: tuple[LearnedPerceptPrototype, ...] = ()


class LearningEpisodeWriter:
    """Write AP-native learning evidence into a runtime ontology state.

    The writer only merges evidence supplied by a teaching episode. It does not
    choose replies, infer routes, or alter recall policy.
    """

    def apply(self, state: Mapping[str, Any], episode: LearningEpisode) -> dict[str, Any]:
        next_state = deepcopy(dict(state))
        next_state.setdefault("schema_id", "apv3_runtime_ontology_state/v1")
        next_state.setdefault("online_embedding", {}).setdefault("tokens", {})
        next_state.setdefault("transitions", [])
        next_state.setdefault("paradigms", [])
        next_state.setdefault("bn_candidates", [])
        next_state.setdefault("action_outcomes", {})
        next_state.setdefault("percept_prototypes", [])
        self._merge_tokens(next_state, episode)
        self._merge_transitions(next_state, episode)
        self._merge_paradigms(next_state, episode)
        self._merge_bn_candidates(next_state, episode)
        self._merge_action_outcomes(next_state, episode)
        self._merge_percept_prototypes(next_state, episode)
        receipts = next_state.setdefault("learning_receipts", [])
        if isinstance(receipts, list):
            receipts.append(
                {
                    "episode_id": episode.episode_id,
                    "tokens": len(episode.tokens),
                    "transitions": len(episode.transitions),
                    "paradigms": len(episode.paradigms),
                    "bn_candidates": len(episode.bn_candidates),
                    "action_outcomes": len(episode.action_outcomes),
                    "percept_prototypes": len(episode.percept_prototypes),
                }
            )
        return next_state

    def _merge_tokens(self, state: dict[str, Any], episode: LearningEpisode) -> None:
        tokens = state["online_embedding"]["tokens"]
        for item in episode.tokens:
            payload = tokens.get(item.token, {})
            if not isinstance(payload, dict):
                payload = {"vector": payload, "support": 0.0}
            payload["vector"] = [float(value) for value in item.vector]
            payload["support"] = _nonnegative(_as_float(payload.get("support")) + item.support_delta)
            tokens[item.token] = payload

    def _merge_transitions(self, state: dict[str, Any], episode: LearningEpisode) -> None:
        transitions = state["transitions"]
        for item in episode.transitions:
            existing = _find_transition(transitions, item.source, item.target)
            if existing is None:
                transitions.append(
                    {
                        "source": item.source,
                        "target": item.target,
                        "support": _nonnegative(item.support_delta),
                        "provenance": [episode.episode_id],
                    }
                )
            else:
                existing["support"] = _nonnegative(_as_float(existing.get("support")) + item.support_delta)
                _append_unique(existing.setdefault("provenance", []), episode.episode_id)

    def _merge_paradigms(self, state: dict[str, Any], episode: LearningEpisode) -> None:
        paradigms = state["paradigms"]
        for item in episode.paradigms:
            existing = _find_by_id(paradigms, "pid", item.pid)
            payload = {
                "pid": item.pid,
                "support": _nonnegative(item.support_delta),
                "conf": float(item.conf),
                "slot_types": list(item.slot_types),
                "probe_tags": list(item.probe_tags),
                "provenance": [episode.episode_id],
            }
            if existing is None:
                paradigms.append(payload)
            else:
                existing["support"] = _nonnegative(_as_float(existing.get("support")) + item.support_delta)
                existing["conf"] = max(_as_float(existing.get("conf")), float(item.conf))
                existing["slot_types"] = _merged_list(existing.get("slot_types"), item.slot_types)
                existing["probe_tags"] = _merged_list(existing.get("probe_tags"), item.probe_tags)
                _append_unique(existing.setdefault("provenance", []), episode.episode_id)

    def _merge_bn_candidates(self, state: dict[str, Any], episode: LearningEpisode) -> None:
        candidates = state["bn_candidates"]
        for item in episode.bn_candidates:
            payload = {
                "candidate_id": item.candidate_id,
                "domain": item.domain,
                "probe_features": {
                    str(case): {str(key): float(value) for key, value in features.items()}
                    for case, features in item.probe_features.items()
                },
                "provenance": [episode.episode_id],
            }
            existing = _find_by_id(candidates, "candidate_id", item.candidate_id)
            if existing is None:
                candidates.append(payload)
            else:
                existing["domain"] = item.domain
                existing["probe_features"] = payload["probe_features"]
                _append_unique(existing.setdefault("provenance", []), episode.episode_id)

    def _merge_action_outcomes(self, state: dict[str, Any], episode: LearningEpisode) -> None:
        outcomes = state["action_outcomes"]
        for item in episode.action_outcomes:
            payload = outcomes.get(item.action, {})
            if not isinstance(payload, dict):
                payload = {"value": payload}
            payload["drive_bias"] = _as_float(payload.get("drive_bias")) + float(item.drive_bias_delta)
            payload["reward_support"] = _nonnegative(_as_float(payload.get("reward_support")) + item.reward_delta)
            payload["punish_support"] = _nonnegative(_as_float(payload.get("punish_support")) + item.punish_delta)
            payload["support"] = _nonnegative(
                _as_float(payload.get("support"))
                + item.support_delta
                + item.reward_delta
                + item.punish_delta
            )
            if item.actuator_id:
                payload["actuator_id"] = item.actuator_id
            payload["outcome_kind"] = item.outcome_kind
            payload["context_tags"] = _merged_list(payload.get("context_tags"), item.context_tags)
            if item.last_tick is not None:
                payload["last_tick"] = int(item.last_tick)
            _append_unique(payload.setdefault("provenance", []), episode.episode_id)
            outcomes[item.action] = payload

    def _merge_percept_prototypes(self, state: dict[str, Any], episode: LearningEpisode) -> None:
        prototypes = state["percept_prototypes"]
        for item in episode.percept_prototypes:
            existing = _find_by_id(prototypes, "prototype_id", item.prototype_id)
            payload = {
                "prototype_id": item.prototype_id,
                "support": _nonnegative(item.support_delta),
                "features": dict(item.features),
                "probe_tags": list(item.probe_tags),
                "provenance": [episode.episode_id],
            }
            if existing is None:
                prototypes.append(payload)
            else:
                existing["support"] = _nonnegative(_as_float(existing.get("support")) + item.support_delta)
                existing["features"] = dict(item.features)
                existing["probe_tags"] = _merged_list(existing.get("probe_tags"), item.probe_tags)
                _append_unique(existing.setdefault("provenance", []), episode.episode_id)


def _find_transition(items: list[dict[str, Any]], source: str, target: str) -> dict[str, Any] | None:
    for item in items:
        if str(item.get("source", "")) == source and str(item.get("target", "")) == target:
            return item
    return None


def _find_by_id(items: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    for item in items:
        if str(item.get(key, "")) == value:
            return item
    return None


def _append_unique(items: Any, value: str) -> None:
    if isinstance(items, list) and value not in items:
        items.append(value)


def _merged_list(existing: object, additions: tuple[str, ...]) -> list[str]:
    merged = [str(item) for item in existing] if isinstance(existing, list) else []
    for item in additions:
        if item not in merged:
            merged.append(item)
    return merged


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _nonnegative(value: float) -> float:
    return max(0.0, float(value))
