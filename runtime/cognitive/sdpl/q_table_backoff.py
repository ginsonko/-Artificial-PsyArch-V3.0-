from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Hashable

from runtime.cognitive.sdpl.packet import LearningPacket
from runtime.cognitive.state_pool.state_pool import load_constant


@dataclass
class QValue:
    mean: float = 0.0
    sample_count: float = 0.0
    variance_accumulator: float = 0.0

    def update(self, outcome: float, weight: float) -> None:
        """@op_count: O(1)."""
        w = max(0.0, float(weight))
        if w <= 0.0:
            return
        old_count = self.sample_count
        self.sample_count = self.sample_count + w
        delta = float(outcome) - self.mean
        self.mean = self.mean + (w / self.sample_count) * delta
        delta_after = float(outcome) - self.mean
        self.variance_accumulator = self.variance_accumulator + w * delta * delta_after
        if old_count <= 0.0:
            self.variance_accumulator = 0.0

    def sample_count_normalized(self) -> float:
        """@op_count: O(1)."""
        floor = float(load_constant("sdpl.q_table.backoff_min_samples_for_layer.action_global"))
        return min(1.0, self.sample_count / max(floor, 1.0))


class QTableWithBackoff:
    """Five-layer SDPL action value table."""

    def __init__(self) -> None:
        self.exact_q: dict[Hashable, QValue] = {}
        self.content_source_q: dict[Hashable, QValue] = {}
        self.source_feeling_q: dict[Hashable, QValue] = {}
        self.content_q: dict[Hashable, QValue] = {}
        self.action_global_q: dict[Hashable, QValue] = {}

    def query(self, packet: LearningPacket, action: str) -> float:
        """@op_count: O(backoff_layers)."""
        layer_items = self._layer_items(packet, action)
        total_weight = 0.0
        weighted_q = 0.0
        for q_value, layer_name in layer_items:
            if q_value is None:
                continue
            if q_value.sample_count < self._min_samples(layer_name):
                continue
            effective = self._weight(layer_name) * q_value.sample_count_normalized()
            weighted_q = weighted_q + effective * q_value.mean
            total_weight = total_weight + effective
        if total_weight <= 0.0:
            return 0.0
        return weighted_q / total_weight

    def update(
        self,
        packet: LearningPacket,
        action: str,
        *,
        outcome: float,
        eligibility: float = 1.0,
    ) -> None:
        """@op_count: O(backoff_layers)."""
        keys = self._keys(packet, action)
        for layer_name, table, key in keys:
            table.setdefault(key, QValue()).update(
                outcome,
                float(eligibility) * self._weight(layer_name),
            )

    def _layer_items(self, packet: LearningPacket, action: str) -> tuple[tuple[QValue | None, str], ...]:
        keys = self._keys(packet, action)
        return tuple((table.get(key), layer_name) for layer_name, table, key in keys)

    def _keys(self, packet: LearningPacket, action: str) -> tuple[tuple[str, dict[Hashable, QValue], Hashable], ...]:
        full_key = packet.packet_key()
        content_key, source_key, _, feeling_key = full_key
        return (
            ("exact", self.exact_q, (full_key, action)),
            ("content_source", self.content_source_q, ((content_key, source_key), action)),
            ("source_feeling", self.source_feeling_q, ((source_key, feeling_key), action)),
            ("content_only", self.content_q, (content_key, action)),
            ("action_global", self.action_global_q, action),
        )

    def _weight(self, layer_name: str) -> float:
        return float(load_constant(f"sdpl.q_table.backoff_weights.{layer_name}"))

    def _min_samples(self, layer_name: str) -> float:
        return float(load_constant(f"sdpl.q_table.backoff_min_samples_for_layer.{layer_name}"))


def q_value_std(q_value: QValue) -> float:
    """@op_count: O(1)."""
    if q_value.sample_count <= 1.0:
        return 0.0
    return sqrt(max(0.0, q_value.variance_accumulator / q_value.sample_count))

