from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import exp
from typing import Any, Mapping, Sequence

from apv3test.config.work_memory_config import APV3WorkMemoryConfig
from apv3test.runtime.paradigm_stats import promoted_context_similarity


@dataclass(frozen=True)
class WorkMemoryTickInput:
    tick: int
    focus_tokens: tuple[str, ...] = ()
    pressure: float = 0.0
    closure: float = 0.0
    surprise: float = 0.0
    idle: bool = False


@dataclass(frozen=True)
class WorkMemoryItem:
    item_id: str
    sa_bundle: tuple[str, ...]
    start_tick: int
    last_tick: int
    pressure: float
    closure: float
    closed: bool
    interrupted_by: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkMemoryTickResult:
    state: dict[str, Any]
    active_item: WorkMemoryItem | None
    recalled_item: WorkMemoryItem | None
    interrupted_item: WorkMemoryItem | None


class APV3WorkMemoryRuntime:
    """Pressure-driven working memory over generic first-class SA tokens."""

    def __init__(self, config: APV3WorkMemoryConfig | None = None) -> None:
        self.config = config or APV3WorkMemoryConfig()

    def run_tick(
        self,
        state: Mapping[str, Any],
        tick_input: WorkMemoryTickInput,
    ) -> WorkMemoryTickResult:
        next_state = _ensure_work_memory_state(deepcopy(dict(state)))
        if tick_input.idle:
            recalled = self._idle_recall(next_state, tick_input.tick)
            _record_trace(next_state, tick_input, active=None, recalled=recalled, interrupted=None)
            return WorkMemoryTickResult(next_state, None, recalled, None)

        interrupted = self._interrupted_item(next_state, tick_input)
        active = self._upsert_focus(next_state, tick_input)
        _record_trace(next_state, tick_input, active=active, recalled=None, interrupted=interrupted)
        return WorkMemoryTickResult(next_state, active, None, interrupted)

    def _upsert_focus(self, state: dict[str, Any], tick_input: WorkMemoryTickInput) -> WorkMemoryItem | None:
        if not tick_input.focus_tokens:
            return None
        bundle = tuple(str(token) for token in tick_input.focus_tokens)
        closure = _clamp01(tick_input.closure)
        pressure = max(float(tick_input.pressure), 0.0)
        closed = closure >= self.config.closure_threshold
        item_id = _item_id(bundle)
        rows = state["working_memory_items"]
        row = _find_item(rows, item_id) or _find_open_overlapping_item(state, rows, bundle, self.config)
        if row is None:
            row = {
                "item_id": item_id,
                "sa_bundle": list(bundle),
                "start_tick": int(tick_input.tick),
                "last_tick": int(tick_input.tick),
                "pressure": pressure,
                "closure": closure,
                "closed": closed,
                "interrupted_by": [],
            }
            rows.insert(0, row)
        else:
            merged = _merge_bundle(_string_tuple(row.get("sa_bundle")), bundle)
            row["item_id"] = _item_id(merged)
            row["sa_bundle"] = list(merged)
            row["last_tick"] = int(tick_input.tick)
            row["pressure"] = max(_as_float(row.get("pressure")), pressure)
            row["closure"] = max(_as_float(row.get("closure")), closure)
            row["closed"] = bool(row.get("closed", False)) or closed
        _upsert_state_field_item(state, row)
        _prune_items(state, tick_input.tick, self.config)
        return _item_from_row(row)

    def _interrupted_item(
        self,
        state: dict[str, Any],
        tick_input: WorkMemoryTickInput,
    ) -> WorkMemoryItem | None:
        if tick_input.surprise < self.config.interruption_surprise_min or not tick_input.focus_tokens:
            return None
        incoming = set(str(token) for token in tick_input.focus_tokens)
        best_row: dict[str, Any] | None = None
        best_pressure = 0.0
        for row in state["working_memory_items"]:
            if not isinstance(row, dict) or bool(row.get("closed", False)):
                continue
            bundle = set(_string_tuple(row.get("sa_bundle")))
            if bundle & incoming:
                continue
            pressure = self._current_pressure(row, tick_input.tick)
            if pressure > best_pressure:
                best_row = row
                best_pressure = pressure
        if best_row is None:
            return None
        best_row["interrupted_by"] = list(tick_input.focus_tokens)
        return _item_from_row(best_row)

    def _idle_recall(self, state: dict[str, Any], tick: int) -> WorkMemoryItem | None:
        best_row: dict[str, Any] | None = None
        best_score = 0.0
        for row in state["working_memory_items"]:
            if not isinstance(row, dict) or bool(row.get("closed", False)):
                continue
            pressure = self._current_pressure(row, tick)
            if pressure < self.config.idle_recall_pressure_min:
                continue
            score = pressure * _recency_gain(row.get("last_tick"), tick, self.config.recency_half_life_ticks)
            if score > best_score:
                best_row = row
                best_score = score
        if best_row is None:
            return None
        best_row["last_tick"] = int(tick)
        best_row["last_recalled_tick"] = int(tick)
        _upsert_state_field_item(state, best_row)
        return _item_from_row(best_row)

    def _current_pressure(self, row: Mapping[str, Any], tick: int) -> float:
        age = max(0, int(tick) - int(_as_float(row.get("last_tick"))))
        return max(0.0, _as_float(row.get("pressure"))) * (self.config.pressure_decay_per_tick ** age)


def _ensure_work_memory_state(state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("schema_id", "apv3_runtime_ontology_state/v1")
    state.setdefault("working_memory_items", [])
    state.setdefault("working_memory_trace", [])
    if not isinstance(state["working_memory_items"], list):
        state["working_memory_items"] = []
    if not isinstance(state["working_memory_trace"], list):
        state["working_memory_trace"] = []
    return state


def _record_trace(
    state: dict[str, Any],
    tick_input: WorkMemoryTickInput,
    *,
    active: WorkMemoryItem | None,
    recalled: WorkMemoryItem | None,
    interrupted: WorkMemoryItem | None,
) -> None:
    state["working_memory_trace"].append(
        {
            "tick": int(tick_input.tick),
            "focus_tokens": list(tick_input.focus_tokens),
            "pressure": float(tick_input.pressure),
            "closure": float(tick_input.closure),
            "surprise": float(tick_input.surprise),
            "idle": bool(tick_input.idle),
            "active_item": active.item_id if active else "",
            "recalled_item": recalled.item_id if recalled else "",
            "interrupted_item": interrupted.item_id if interrupted else "",
        }
    )


def _item_from_row(row: Mapping[str, Any]) -> WorkMemoryItem:
    return WorkMemoryItem(
        item_id=str(row.get("item_id", "")),
        sa_bundle=_string_tuple(row.get("sa_bundle")),
        start_tick=int(_as_float(row.get("start_tick"))),
        last_tick=int(_as_float(row.get("last_tick"))),
        pressure=_as_float(row.get("pressure")),
        closure=_as_float(row.get("closure")),
        closed=bool(row.get("closed", False)),
        interrupted_by=_string_tuple(row.get("interrupted_by")),
    )


def _find_item(rows: Sequence[Any], item_id: str) -> dict[str, Any] | None:
    for row in rows:
        if isinstance(row, dict) and str(row.get("item_id", "")) == item_id:
            return row
    return None


def _find_open_overlapping_item(
    state: Mapping[str, Any],
    rows: Sequence[Any],
    bundle: Sequence[str],
    config: APV3WorkMemoryConfig,
) -> dict[str, Any] | None:
    incoming = tuple(str(token) for token in bundle)
    incoming_set = set(incoming)
    for row in rows:
        if not isinstance(row, dict) or bool(row.get("closed", False)):
            continue
        learned = _string_tuple(row.get("sa_bundle"))
        similarity = promoted_context_similarity(state, learned, incoming)
        if similarity >= config.semantic_overlap_min or set(learned) & incoming_set:
            return row
    return None


def _prune_items(state: dict[str, Any], tick: int, config: APV3WorkMemoryConfig) -> None:
    rows = state["working_memory_items"]
    if not isinstance(rows, list):
        return
    limit = max(1, int(config.max_items))
    rows.sort(key=lambda row: _retention_score(row, tick, config), reverse=True)
    del rows[limit:]


def _retention_score(row: object, tick: int, config: APV3WorkMemoryConfig) -> float:
    if not isinstance(row, dict):
        return -1.0
    if bool(row.get("closed", False)):
        return -0.5
    pressure = max(0.0, _as_float(row.get("pressure"))) * (config.pressure_decay_per_tick ** max(0, tick - int(_as_float(row.get("last_tick")))))
    return pressure * _recency_gain(row.get("last_tick"), tick, config.recency_half_life_ticks)


def _upsert_state_field_item(state: dict[str, Any], row: Mapping[str, Any]) -> None:
    items = state.setdefault("state_field_items", [])
    if not isinstance(items, list):
        state["state_field_items"] = []
        items = state["state_field_items"]
    item_id = str(row.get("item_id", ""))
    pressure = 0.0 if bool(row.get("closed", False)) else max(0.0, _as_float(row.get("pressure")))
    payload = {
        "item_id": item_id,
        "sa_type": "work_memory_unfinished",
        "ref": item_id,
        "sa_bundle": list(_string_tuple(row.get("sa_bundle"))),
        "closed": bool(row.get("closed", False)),
        "energy": {
            "R": round(pressure, 6),
            "V": 0.0,
            "P": round(pressure, 6),
            "A": round(pressure, 6),
            "F": 0.0,
        },
        "anchor_meta": {"stats_ref": f"working_memory_items:{item_id}"},
    }
    existing = _find_state_item(items, item_id)
    if existing is None:
        items.append(payload)
    else:
        existing.update(payload)


def _find_state_item(items: Sequence[Any], item_id: str) -> dict[str, Any] | None:
    for item in items:
        if isinstance(item, dict) and str(item.get("item_id", "")) == item_id:
            return item
    return None


def _merge_bundle(left: Sequence[str], right: Sequence[str]) -> tuple[str, ...]:
    merged: list[str] = []
    for token in tuple(left) + tuple(right):
        if token not in merged:
            merged.append(str(token))
    return tuple(merged)


def _item_id(bundle: Sequence[str]) -> str:
    return "wm:" + "|".join(str(token) for token in bundle)


def _recency_gain(last_tick: object, current_tick: int, half_life: float) -> float:
    age = max(0, int(current_tick) - int(_as_float(last_tick)))
    return exp(-float(age) / max(1e-6, float(half_life)))


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value)


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
