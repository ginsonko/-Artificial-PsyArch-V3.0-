from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

from runtime.cognitive.state_pool.attention_gain_ledger import AttentionGainLedger


@dataclass
class StateItem:
    sa_id: str
    family: str
    label: str
    real_energy: float = 0.0
    virtual_energy: float = 0.0
    attention_energy: float = 0.0
    fatigue: float = 0.0
    cognitive_pressure: float = 0.0
    last_tick: int = 0
    channel_signature: tuple[str, ...] = ()
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    gain_ledger: AttentionGainLedger = field(default_factory=AttentionGainLedger)

    def to_trace_dict(self) -> dict[str, object]:
        """@op_count: O(1)."""
        return {
            "sa_id": self.sa_id,
            "family": self.family,
            "label": self.label,
            "R": self.real_energy,
            "V": self.virtual_energy,
            "P": self.cognitive_pressure,
            "A": self.attention_energy,
            "F": self.fatigue,
            "source": self.source,
            "channel_signature": self.channel_signature,
            "gain_ledger": self.gain_ledger.snapshot(),
        }


class StatePool:
    """Small R/V/P/A/F state pool for Phase 8.2 sensor ticks."""

    def __init__(self) -> None:
        self.items: dict[str, StateItem] = {}
        self.current_tick = 0

    def observe_external(self, event: object, *, tick: int) -> StateItem:
        """@op_count: O(1)."""
        sa_id = str(_event_value(event, "sa_id"))
        item = self.items.get(sa_id)
        if item is None:
            item = StateItem(
                sa_id=sa_id,
                family=str(_event_value(event, "family")),
                label=str(_event_value(event, "label")),
                channel_signature=tuple(_event_value(event, "channel_signature")),
                source=str(_event_value(event, "origin")),
                metadata=dict(_event_value(event, "metadata")),
            )
            self.items[sa_id] = item
        energy = float(_event_value(event, "real_energy"))
        ledger_source = str(item.metadata.get("ledger_source", "external"))
        event_metadata = dict(_event_value(event, "metadata"))
        ledger_source = str(event_metadata.get("ledger_source", ledger_source))
        item.real_energy = item.real_energy + energy
        item.attention_energy = item.attention_energy + energy
        item.gain_ledger.inject(ledger_source, energy)
        item.cognitive_pressure = item.real_energy - item.virtual_energy
        item.last_tick = tick
        item.metadata["observations"] = int(item.metadata.get("observations", 0)) + 1
        item.metadata["live_external_tick"] = tick
        item.metadata.update(event_metadata)
        return item

    def tick_decay(self, *, tick: int) -> None:
        """@op_count: O(active_sa)."""
        self.current_tick = int(tick)
        r_decay = float(load_constant("energy.R_decay_short"))
        v_decay = float(load_constant("energy.V_decay"))
        a_decay = float(load_constant("energy.A_decay"))
        f_decay = float(load_constant("energy.F_decay"))
        for item in self.items.values():
            item.real_energy = item.real_energy * r_decay
            item.virtual_energy = item.virtual_energy * v_decay
            item.attention_energy = item.attention_energy * a_decay
            item.gain_ledger.step_decay(a_decay)
            item.fatigue = item.fatigue * f_decay
            item.cognitive_pressure = item.real_energy - item.virtual_energy

    def snapshot_top(self, limit: int | None = None) -> tuple[dict[str, object], ...]:
        """@op_count: O(active_sa log active_sa)."""
        if limit is None:
            limit = int(load_constant("context_signature.top_k"))
        pressure_weight = float(load_constant("state_pool.snapshot_pressure_weight"))
        ordered = sorted(
            self.items.values(),
            key=lambda item: (
                item.real_energy
                + item.virtual_energy
                + item.attention_energy
                + abs(item.cognitive_pressure) * pressure_weight,
                item.sa_id,
            ),
            reverse=True,
        )
        return tuple(item.to_trace_dict() for item in ordered[: int(limit)])

    def get(self, sa_id: str) -> StateItem | None:
        return self.items.get(sa_id)

    def inject_virtual(
        self,
        sa_id: str,
        virtual_energy: float,
        tick: int,
        *,
        family: str = "memory_prediction",
        label: str = "",
        source: str = "residual_mass",
    ) -> StateItem:
        """@op_count: O(1). Upsert item with virtual energy; creates new item if not present."""
        item = self.items.get(sa_id)
        if item is None:
            item = StateItem(
                sa_id=sa_id,
                family=family,
                label=label or sa_id,
                source=source,
            )
            self.items[sa_id] = item
        delta = max(0.0, min(1.0, float(virtual_energy)))
        item.virtual_energy = min(1.0, item.virtual_energy + delta)
        item.cognitive_pressure = item.real_energy - item.virtual_energy
        item.last_tick = tick
        item.gain_ledger.inject(source, delta)
        return item

    def modify_occurrence(
        self,
        sa_id: str,
        *,
        delta_real: float = 0.0,
        delta_virtual: float = 0.0,
        tick: int,
    ) -> StateItem | None:
        """@op_count: O(1). Apply energy deltas to an existing item. No-op if item absent."""
        item = self.items.get(sa_id)
        if item is None:
            return None
        attention_coupling = float(load_constant("state_pool.b_recall_attention_coupling"))
        item.real_energy = max(0.0, min(1.0, item.real_energy + float(delta_real)))
        item.virtual_energy = max(0.0, min(1.0, item.virtual_energy + float(delta_virtual)))
        item.cognitive_pressure = item.real_energy - item.virtual_energy
        item.attention_energy = min(
            1.0,
            item.attention_energy + abs(float(delta_real) + float(delta_virtual)) * attention_coupling,
        )
        item.last_tick = tick
        return item

    def get_active_above_threshold(self, threshold: float) -> tuple[StateItem, ...]:
        """Return items whose real_energy + virtual_energy exceeds threshold."""
        return tuple(
            item for item in self.items.values()
            if (item.real_energy + item.virtual_energy) > float(threshold)
        )

    def __len__(self) -> int:
        return len(self.items)


def load_constant(path: str) -> Any:
    """@op_count: O(config_size) cold, O(path_parts) after cache warm."""
    data = _load_constants_data()
    node: Any = data
    for part in path.split("."):
        node = node[part]
    return node


@lru_cache(maxsize=1)
def _load_constants_data() -> Mapping[str, Any]:
    """@op_count: O(config_size) cold, O(1) warm."""
    data = yaml.safe_load(_constants_path().read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("apv3_constants.yaml must contain a mapping root")
    return data


def _constants_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "apv3_constants.yaml"


def _event_value(event: object, name: str) -> Any:
    if hasattr(event, name):
        return getattr(event, name)
    if isinstance(event, dict):
        return event[name]
    raise AttributeError(name)
