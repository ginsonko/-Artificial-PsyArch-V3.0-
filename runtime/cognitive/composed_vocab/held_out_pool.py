from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass(frozen=True)
class HeldOutSituation:
    situation_id: str
    items: tuple[StateItem, ...]

    def mean_recent_pressure(self) -> float:
        """@op_count: O(items)."""
        if not self.items:
            return 0.0
        total = sum(item.cognitive_pressure for item in self.items)
        return total / len(self.items)

    def clone_items(self) -> tuple[StateItem, ...]:
        """@op_count: O(items)."""
        return tuple(
            StateItem(
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
                source=item.source,
                metadata=dict(item.metadata),
            )
            for item in self.items
        )


class HeldOutPool:
    """Bounded held-out situation pool for Delta-P candidate evaluation."""

    def __init__(self) -> None:
        self.situations: list[HeldOutSituation] = []

    def add(self, situation: HeldOutSituation) -> None:
        """@op_count: O(capacity)."""
        self.situations.append(situation)
        capacity = int(load_constant("held_out.reservoir_capacity"))
        if len(self.situations) > capacity:
            self.situations = self.situations[-capacity:]

    def add_items(self, situation_id: str, items: Iterable[StateItem]) -> None:
        """@op_count: O(items)."""
        self.add(HeldOutSituation(situation_id=situation_id, items=tuple(items)))

    def find_top_k_similar(self, items: Iterable[StateItem]) -> tuple[HeldOutSituation, ...]:
        """@op_count: O(pool * items)."""
        current_ids = {item.sa_id for item in items}
        scored = []
        for situation in self.situations:
            other_ids = {item.sa_id for item in situation.items}
            union = current_ids | other_ids
            score = 0.0 if not union else len(current_ids & other_ids) / len(union)
            scored.append((score, situation.situation_id, situation))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        k = int(load_constant("composed_vocab.delta_p.n_situations_per_eval"))
        return tuple(item[2] for item in scored[:k])

    def __len__(self) -> int:
        return len(self.situations)

