from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Iterable

from runtime.cognitive.long_term.rehydration import spawn_remembered
from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass(frozen=True)
class RehydrationResult:
    items: tuple[StateItem, ...]
    markers: tuple[MarkerEvent, ...]


class LongTermDualLayer:
    def __init__(self, *, active_max: int | None = None, cold_capacity: int | None = None) -> None:
        self.active_pool: OrderedDict[str, StateItem] = OrderedDict()
        self.cold_index: OrderedDict[str, StateItem] = OrderedDict()
        self.active_max = int(active_max) if active_max is not None else int(load_constant("long_term.active_pool_max_from_long"))
        self.cold_capacity = int(cold_capacity) if cold_capacity is not None else int(load_constant("long_term.cold_index_capacity"))

    def admit_short_term(self, item: StateItem) -> None:
        """@op_count: O(capacity)."""
        cold = _clone_for_cold(item)
        self.cold_index[cold.sa_id] = cold
        self.cold_index.move_to_end(cold.sa_id)
        self._compact_cold()

    def rehydrate_by_cues(self, cue_ids: Iterable[str], *, tick: int) -> RehydrationResult:
        """@op_count: O(cue_count * cold_index)."""
        cue_set = set(cue_ids)
        activated: list[StateItem] = []
        markers: list[MarkerEvent] = []
        for item in self.cold_index.values():
            if item.sa_id not in cue_set and not cue_set.intersection(item.channel_signature):
                continue
            active = _clone_for_active(item)
            self.active_pool[active.sa_id] = active
            self.active_pool.move_to_end(active.sa_id)
            activated.append(active)
            markers.append(spawn_remembered(active, tick=tick, cue_alignment=1.0))
        self._compact_active()
        return RehydrationResult(items=tuple(activated), markers=tuple(markers))

    def _compact_active(self) -> None:
        while len(self.active_pool) > self.active_max:
            _, evicted = self.active_pool.popitem(last=False)
            self.cold_index[evicted.sa_id] = _clone_for_cold(evicted)
            self._compact_cold()

    def _compact_cold(self) -> None:
        while len(self.cold_index) > self.cold_capacity:
            self.cold_index.popitem(last=False)


def _clone_for_cold(item: StateItem) -> StateItem:
    return StateItem(
        sa_id=item.sa_id,
        family=item.family,
        label=item.label,
        real_energy=item.real_energy,
        virtual_energy=item.virtual_energy,
        attention_energy=0.0,
        fatigue=item.fatigue,
        cognitive_pressure=item.cognitive_pressure,
        last_tick=item.last_tick,
        channel_signature=item.channel_signature,
        source="long_term_cold",
        metadata={**item.metadata, "long_term_layer": True, "long_term_R": item.real_energy},
    )


def _clone_for_active(item: StateItem) -> StateItem:
    return StateItem(
        sa_id=item.sa_id,
        family=item.family,
        label=item.label,
        real_energy=item.real_energy,
        virtual_energy=item.virtual_energy,
        attention_energy=item.attention_energy,
        fatigue=item.fatigue,
        cognitive_pressure=item.cognitive_pressure,
        last_tick=item.last_tick,
        channel_signature=item.channel_signature,
        source="long_term_active",
        metadata=dict(item.metadata),
    )
