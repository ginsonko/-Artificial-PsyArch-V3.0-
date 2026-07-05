from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Any, Mapping, Sequence

from apv3test.config.introspection_config import APV3ReplyPressureConfig


SA_KIND_SIGNS = {
    "external_demand": 1.0,
    "social_presence": 0.5,
    "internal_unfinished": 0.7,
    "temporal_idleness": 0.35,
    "recent_action": -1.0,
}


@dataclass(frozen=True)
class ReplyPressureSA:
    sa_label: str
    sa_type: str
    sa_kind: str
    real_energy: float
    cognitive_pressure: float
    tick: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "apv3_reply_pressure_sa/v1",
            "sa_label": self.sa_label,
            "sa_type": self.sa_type,
            "sa_kind": self.sa_kind,
            "real_energy": round(float(self.real_energy), 6),
            "cognitive_pressure": round(float(self.cognitive_pressure), 6),
            "tick": int(self.tick),
        }


@dataclass(frozen=True)
class ReplyPressureTrace:
    tick: int
    raw_pressure: float
    contributions: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "apv3_reply_pressure_trace/v1",
            "tick": int(self.tick),
            "raw_pressure": round(float(self.raw_pressure), 6),
            "contributions": list(self.contributions),
        }


def update_reply_pressure_state(
    state: Mapping[str, Any],
    *,
    current_tick: int,
    incoming_external_query: Sequence[str] = (),
    commit_happened: bool = False,
    config: APV3ReplyPressureConfig | None = None,
) -> dict[str, Any]:
    cfg = config or APV3ReplyPressureConfig()
    next_state = dict(state)
    tick = int(current_tick)
    inputs = _decayed_inputs(next_state.get("introspection_pressure_inputs", []), tick, cfg)
    if commit_happened:
        next_state["last_commit_tick"] = tick
        inputs = [
            item
            for item in inputs
            if str(item.get("sa_type", "")) not in {"silence", "recent_commit"}
        ]
        inputs.append(
            _pressure_input(
                sa_label=f"pressure::recent_commit::{tick}",
                sa_type="recent_commit",
                sa_kind="recent_action",
                real_energy=cfg.recent_commit_energy,
                tick=tick,
            )
        )
    if incoming_external_query:
        inputs.append(
            _pressure_input(
                sa_label=f"pressure::external_query::{tick}",
                sa_type="external_query",
                sa_kind="external_demand",
                real_energy=cfg.external_query_energy,
                tick=tick,
            )
        )
    inputs = [item for item in inputs if str(item.get("sa_type", "")) != "silence"]
    silence = _silence_input(next_state, tick, cfg)
    if silence is not None:
        inputs.append(silence)
    next_state["introspection_pressure_inputs"] = inputs
    pressure, trace = derive_reply_pressure_sa(next_state, current_tick=tick, config=cfg)
    next_state["introspection_pressure"] = [pressure.to_dict()]
    traces = list(next_state.get("reply_pressure_traces", [])) if isinstance(next_state.get("reply_pressure_traces", []), list) else []
    traces.append(trace.to_dict())
    next_state["reply_pressure_traces"] = traces[-16:]
    return next_state


def derive_reply_pressure_sa(
    state: Mapping[str, Any],
    *,
    current_tick: int,
    config: APV3ReplyPressureConfig | None = None,
) -> tuple[ReplyPressureSA, ReplyPressureTrace]:
    cfg = config or APV3ReplyPressureConfig()
    raw = 0.0
    contributions: list[dict[str, Any]] = []
    for item in _iter_pressure_items(state):
        kind = str(item.get("sa_kind", ""))
        sign = SA_KIND_SIGNS.get(kind)
        if sign is None:
            continue
        energy = max(0.0, float(item.get("real_energy", 0.0)))
        contribution = sign * energy
        raw += contribution
        contributions.append(
            {
                "sa_label": str(item.get("sa_label", "")),
                "sa_type": str(item.get("sa_type", "")),
                "sa_kind": kind,
                "contribution": round(contribution, 6),
            }
        )
    pressure_level = 1.0 / (1.0 + exp(-raw))
    pressure = ReplyPressureSA(
        sa_label="pressure::reply",
        sa_type="reply_pressure",
        sa_kind="reply_pressure",
        real_energy=pressure_level,
        cognitive_pressure=max(0.0, pressure_level - cfg.reply_pressure_neutral),
        tick=int(current_tick),
    )
    return pressure, ReplyPressureTrace(int(current_tick), raw, tuple(contributions))


def reply_pressure_requires_response(
    state: Mapping[str, Any],
    *,
    config: APV3ReplyPressureConfig | None = None,
) -> bool:
    cfg = config or APV3ReplyPressureConfig()
    items = state.get("introspection_pressure", [])
    if not isinstance(items, list) or not items:
        return False
    latest = items[-1]
    if not isinstance(latest, Mapping):
        return False
    return float(latest.get("real_energy", 0.0)) >= cfg.reply_pressure_threshold


def _decayed_inputs(items: object, current_tick: int, config: APV3ReplyPressureConfig) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    result: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        decayed = dict(item)
        age = max(1, int(current_tick) - int(decayed.get("tick", current_tick)))
        decayed["real_energy"] = max(0.0, float(decayed.get("real_energy", 0.0))) * (
            config.pressure_half_life_decay ** age
        )
        decayed["tick"] = int(current_tick)
        if decayed["real_energy"] >= config.pressure_eviction_floor:
            result.append(decayed)
    return result


def _silence_input(
    state: Mapping[str, Any],
    tick: int,
    config: APV3ReplyPressureConfig,
) -> dict[str, Any] | None:
    if "last_commit_tick" not in state:
        return None
    elapsed = max(0, int(tick) - int(state.get("last_commit_tick", tick)))
    if elapsed <= 0:
        return None
    ramp = min(1.0, elapsed / max(1, int(config.silence_normalizer_ticks)))
    decay = config.silence_half_life_decay ** max(0, elapsed - int(config.silence_normalizer_ticks))
    energy = ramp * decay
    if energy < config.pressure_eviction_floor:
        return None
    return _pressure_input(
        sa_label="pressure::silence",
        sa_type="silence",
        sa_kind="temporal_idleness",
        real_energy=energy,
        tick=tick,
    )


def _pressure_input(
    *,
    sa_label: str,
    sa_type: str,
    sa_kind: str,
    real_energy: float,
    tick: int,
) -> dict[str, Any]:
    return {
        "schema_id": "apv3_pressure_input_sa/v1",
        "sa_label": sa_label,
        "sa_type": sa_type,
        "sa_kind": sa_kind,
        "real_energy": round(max(0.0, float(real_energy)), 6),
        "tick": int(tick),
    }


def _iter_pressure_items(state: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    items: list[Mapping[str, Any]] = []
    pressure_inputs = state.get("introspection_pressure_inputs", [])
    if isinstance(pressure_inputs, list):
        items.extend(item for item in pressure_inputs if isinstance(item, Mapping))
    state_field_items = state.get("state_field_items", [])
    if isinstance(state_field_items, list):
        items.extend(item for item in state_field_items if isinstance(item, Mapping) and "sa_kind" in item)
    return tuple(items)
