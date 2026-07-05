from __future__ import annotations

from math import exp, sqrt
from typing import Any, Mapping, Sequence

from apv3test.config.habit_config import APV3HabitConfig
from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig


class RoleTransitionStats:
    """Learn Viterbi role-transition bias from AP-native use evidence."""

    def __init__(
        self,
        config: APV3ParadigmDiscoveryConfig | None = None,
        habit_config: APV3HabitConfig | None = None,
    ) -> None:
        self.config = config or APV3ParadigmDiscoveryConfig()
        self.habit_config = habit_config or APV3HabitConfig()

    def learn(
        self,
        state: dict[str, Any],
        roles: Sequence[str],
        *,
        context_tokens: Sequence[str],
        committed: bool,
        reward_delta: float,
        punish_delta: float,
        tick_id: int,
        provenance: str,
    ) -> None:
        if len(roles) < 2 or not committed:
            return
        stats = state.setdefault("role_transition_stats", [])
        if not isinstance(stats, list):
            state["role_transition_stats"] = []
            stats = state["role_transition_stats"]
        support_delta = 0.0 if float(punish_delta) > float(reward_delta) else 1.0
        for prev_role, role in zip(roles, roles[1:]):
            row = _find_transition_stat(stats, prev_role, role, tuple(context_tokens))
            if row is None:
                row = {
                    "prev_role": str(prev_role),
                    "role": str(role),
                    "context_tokens": list(context_tokens),
                    "support": 0.0,
                    "reward_support": 0.0,
                    "punish_support": 0.0,
                    "last_tick": int(tick_id),
                    "provenance": [],
                }
                stats.append(row)
            row["support"] = _nonnegative(_as_float(row.get("support")) + support_delta)
            row["reward_support"] = _nonnegative(_as_float(row.get("reward_support")) + float(reward_delta))
            row["punish_support"] = _nonnegative(_as_float(row.get("punish_support")) + float(punish_delta))
            row["last_tick"] = int(tick_id)
            _append_unique(row.setdefault("provenance", []), provenance)

    def bias_map(
        self,
        state: Mapping[str, Any],
        *,
        current_context_tokens: Sequence[str],
        current_tick: int,
    ) -> dict[tuple[str, str], float]:
        rows = state.get("role_transition_stats", [])
        if not isinstance(rows, list):
            return {}
        result: dict[tuple[str, str], float] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            learned_context = _string_tuple(row.get("context_tokens"))
            similarity = promoted_context_similarity(state, learned_context, tuple(current_context_tokens))
            if similarity < self.config.role_transition_context_similarity_min:
                continue
            recency = _recency_gain(row.get("last_tick"), current_tick, self.habit_config)
            support = bounded_evidence(row.get("support"), self.habit_config.support_half_life)
            reward = bounded_evidence(row.get("reward_support"), self.habit_config.support_half_life)
            punish = bounded_evidence(row.get("punish_support"), self.habit_config.support_half_life)
            bias = similarity * recency * (
                self.config.role_transition_support_weight * support
                + self.config.role_transition_reward_weight * reward
                - self.config.role_transition_punish_weight * punish
            )
            key = (str(row.get("prev_role", "")), str(row.get("role", "")))
            result[key] = round(result.get(key, 0.0) + bias, 6)
        return result


def promoted_context_similarity(
    state: Mapping[str, Any],
    learned_context: Sequence[str],
    current_context: Sequence[str],
) -> float:
    learned = tuple(str(item) for item in learned_context)
    current = tuple(str(item) for item in current_context)
    if learned == current:
        return 1.0
    if not learned and not current:
        return 1.0
    if not learned or not current:
        return 0.0
    left = _promoted_centroid(state, learned)
    right = _promoted_centroid(state, current)
    if left is None or right is None:
        return 0.0
    denom = _norm(left) * _norm(right)
    if denom <= 0.0:
        return 0.0
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right)) / denom))


def decayed_pressure(value: object, last_tick: object, current_tick: int, config: APV3HabitConfig) -> float:
    return bounded_evidence(value, config.support_half_life) * _recency_gain(last_tick, current_tick, config)


def bounded_evidence(value: object, half_life: float) -> float:
    scale = max(1e-6, float(half_life))
    return 1.0 - exp(-max(0.0, _as_float(value)) / scale)


def _find_transition_stat(
    rows: list[dict[str, Any]],
    prev_role: str,
    role: str,
    context_tokens: tuple[str, ...],
) -> dict[str, Any] | None:
    for row in rows:
        if (
            str(row.get("prev_role", "")) == str(prev_role)
            and str(row.get("role", "")) == str(role)
            and _string_tuple(row.get("context_tokens")) == context_tokens
        ):
            return row
    return None


def _promoted_centroid(state: Mapping[str, Any], tokens: Sequence[str]) -> tuple[float, ...] | None:
    online = state.get("online_embedding", {})
    token_payloads = online.get("tokens", {}) if isinstance(online, dict) else {}
    if not isinstance(token_payloads, dict):
        return None
    vectors: list[tuple[float, ...]] = []
    for token in tokens:
        payload = token_payloads.get(str(token), {})
        if not isinstance(payload, dict) or not bool(payload.get("promoted", False)):
            continue
        vector = _float_tuple(payload.get("vector"))
        if vector:
            vectors.append(vector)
    if not vectors:
        return None
    width = min(len(vector) for vector in vectors)
    return tuple(sum(vector[index] for vector in vectors) / len(vectors) for index in range(width))


def _recency_gain(last_tick: object, current_tick: int | None, config: APV3HabitConfig) -> float:
    if current_tick is None:
        return max(0.0, float(config.unknown_recency_gain))
    try:
        age = max(0, int(current_tick) - int(last_tick))
    except (TypeError, ValueError):
        return max(0.0, float(config.unknown_recency_gain))
    scale = max(1e-6, float(config.recency_half_life_ticks))
    return exp(-float(age) / scale)


def _norm(vector: Sequence[float]) -> float:
    return sqrt(sum(float(value) * float(value) for value in vector))


def _float_tuple(value: object) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    result: list[float] = []
    for item in value:
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            return ()
    return tuple(result)


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value)


def _append_unique(items: Any, value: str) -> None:
    if isinstance(items, list) and value not in items:
        items.append(value)


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _nonnegative(value: float) -> float:
    return max(0.0, float(value))
