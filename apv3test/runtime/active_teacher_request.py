from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from apv3test.config.active_learning_config import APV3ActiveLearningConfig


@dataclass(frozen=True)
class TeacherRequestSignal:
    tick: int
    cue_tokens: tuple[str, ...] = ()
    context_tokens: tuple[str, ...] = ()
    cognitive_pressure: float = 0.0
    recall_failed: bool = False
    remediation_need: float = 0.0
    expected_pid: str = ""


@dataclass(frozen=True)
class TeacherRequestSA:
    request_id: str
    cue_tokens: tuple[str, ...]
    context_tokens: tuple[str, ...]
    tick: int
    reason: str
    cognitive_pressure: float
    failure_count: int
    remediation_need: float


@dataclass(frozen=True)
class TeacherRequestResult:
    state: dict[str, Any]
    request: TeacherRequestSA | None
    suppressed_reason: str = ""


class APV3ActiveTeacherRequestRuntime:
    """Create teacher_request SA when AP-native uncertainty stays unresolved."""

    def __init__(self, config: APV3ActiveLearningConfig | None = None) -> None:
        self.config = config or APV3ActiveLearningConfig()

    def observe(
        self,
        state: Mapping[str, Any],
        signal: TeacherRequestSignal,
    ) -> TeacherRequestResult:
        next_state = _ensure_active_learning_state(deepcopy(dict(state)))
        key = _signal_key(signal)
        failure_count = _update_failure_count(next_state, key, signal)

        if signal.expected_pid and _expected_paradigm_is_exposed(next_state, signal.expected_pid):
            return TeacherRequestResult(next_state, None, "mastered_expected_pid")
        if _within_cooldown(next_state, key, signal.tick, self.config.request_cooldown_ticks):
            return TeacherRequestResult(next_state, None, "request_cooldown")

        reason = self._request_reason(signal, failure_count)
        if not reason:
            return TeacherRequestResult(next_state, None, "below_request_threshold")

        request = TeacherRequestSA(
            request_id=f"teacher_request:{key}:{int(signal.tick)}",
            cue_tokens=tuple(signal.cue_tokens),
            context_tokens=tuple(signal.context_tokens),
            tick=int(signal.tick),
            reason=reason,
            cognitive_pressure=float(signal.cognitive_pressure),
            failure_count=failure_count,
            remediation_need=float(signal.remediation_need),
        )
        _append_teacher_request(next_state, request, self.config.max_teacher_requests)
        _upsert_request_pool_entry(next_state, request)
        return TeacherRequestResult(next_state, request, "")

    def _request_reason(self, signal: TeacherRequestSignal, failure_count: int) -> str:
        if float(signal.remediation_need) >= self.config.remediation_need_threshold:
            return "remediation_needed"
        if failure_count >= self.config.repeated_failure_threshold:
            return "repeated_recall_failure"
        if float(signal.cognitive_pressure) >= self.config.pressure_request_threshold:
            return "high_cognitive_pressure"
        return ""


def _ensure_active_learning_state(state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("schema_id", "apv3_runtime_ontology_state/v1")
    state.setdefault("active_learning_failures", {})
    state.setdefault("teacher_requests", [])
    state.setdefault("state_field_items", [])
    if not isinstance(state["active_learning_failures"], dict):
        state["active_learning_failures"] = {}
    if not isinstance(state["teacher_requests"], list):
        state["teacher_requests"] = []
    if not isinstance(state["state_field_items"], list):
        state["state_field_items"] = []
    return state


def _update_failure_count(state: dict[str, Any], key: str, signal: TeacherRequestSignal) -> int:
    rows = state["active_learning_failures"]
    payload = rows.get(key, {}) if isinstance(rows, dict) else {}
    if not isinstance(payload, dict):
        payload = {}
    count = int(_as_float(payload.get("failure_count")))
    count = count + 1 if signal.recall_failed else max(0, count - 1)
    payload.update(
        {
            "key": key,
            "cue_tokens": list(signal.cue_tokens),
            "context_tokens": list(signal.context_tokens),
            "failure_count": count,
            "last_tick": int(signal.tick),
            "last_pressure": float(signal.cognitive_pressure),
            "last_remediation_need": float(signal.remediation_need),
        }
    )
    rows[key] = payload
    return count


def _append_teacher_request(state: dict[str, Any], request: TeacherRequestSA, limit: int) -> None:
    rows = state["teacher_requests"]
    rows.insert(
        0,
        {
            "schema_id": "apv3_teacher_request/v1",
            "request_id": request.request_id,
            "cue_tokens": list(request.cue_tokens),
            "context_tokens": list(request.context_tokens),
            "tick": int(request.tick),
            "reason": request.reason,
            "cognitive_pressure": float(request.cognitive_pressure),
            "failure_count": int(request.failure_count),
            "remediation_need": float(request.remediation_need),
        },
    )
    del rows[max(1, int(limit)) :]


def _upsert_request_pool_entry(state: dict[str, Any], request: TeacherRequestSA) -> None:
    items = state["state_field_items"]
    pressure = max(float(request.cognitive_pressure), request.failure_count / 2.0, float(request.remediation_need))
    payload = {
        "item_id": request.request_id,
        "sa_type": "teacher_request",
        "ref": request.request_id,
        "cue_tokens": list(request.cue_tokens),
        "context_tokens": list(request.context_tokens),
        "reason": request.reason,
        "energy": {
            "R": round(min(1.0, pressure), 6),
            "V": 0.0,
            "P": round(min(1.0, pressure), 6),
            "A": round(min(1.0, pressure), 6),
            "F": 0.0,
        },
        "anchor_meta": {"stats_ref": f"teacher_requests:{request.request_id}"},
    }
    existing = _find_state_item(items, request.request_id)
    if existing is None:
        items.append(payload)
    else:
        existing.update(payload)


def _within_cooldown(state: Mapping[str, Any], key: str, tick: int, cooldown: int) -> bool:
    rows = state.get("teacher_requests", [])
    if not isinstance(rows, list):
        return False
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_key = _tokens_key(_string_tuple(row.get("cue_tokens")), _string_tuple(row.get("context_tokens")))
        if row_key != key:
            continue
        if int(tick) - int(_as_float(row.get("tick"))) <= max(0, int(cooldown)):
            return True
    return False


def _expected_paradigm_is_exposed(state: Mapping[str, Any], expected_pid: str) -> bool:
    rows = state.get("paradigms", [])
    if not isinstance(rows, list):
        return False
    for row in rows:
        if isinstance(row, dict) and str(row.get("pid", "")) == expected_pid:
            return bool(row.get("exposed", False))
    return False


def _signal_key(signal: TeacherRequestSignal) -> str:
    return _tokens_key(signal.cue_tokens, signal.context_tokens)


def _tokens_key(cue_tokens: Sequence[str], context_tokens: Sequence[str]) -> str:
    return "cue=" + " ".join(str(token) for token in cue_tokens) + "|ctx=" + " ".join(str(token) for token in context_tokens)


def _find_state_item(items: Sequence[Any], item_id: str) -> dict[str, Any] | None:
    for item in items:
        if isinstance(item, dict) and str(item.get("item_id", "")) == item_id:
            return item
    return None


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value)


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
