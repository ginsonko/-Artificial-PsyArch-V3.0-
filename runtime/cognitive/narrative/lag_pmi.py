from __future__ import annotations

from dataclasses import dataclass, field
from math import log
from typing import Iterable

from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass
class LagPMIGraph:
    total_positions: float = 0.0
    event_counts: dict[str, float] = field(default_factory=dict)
    pair_counts: dict[tuple[str, str, int], float] = field(default_factory=dict)

    def observe_sequence(self, event_sa_ids: Iterable[str]) -> None:
        """@op_count: O(events * max_lag)."""
        sequence = tuple(event_sa_ids)
        max_lag = int(load_constant("narrative.max_lag"))
        self.total_positions = self.total_positions + float(len(sequence))
        for event_id in sequence:
            self.event_counts[event_id] = self.event_counts.get(event_id, 0.0) + 1.0
        for index, source_id in enumerate(sequence):
            for lag in range(1, max_lag + 1):
                target_index = index + lag
                if target_index >= len(sequence):
                    continue
                target_id = sequence[target_index]
                key = (source_id, target_id, lag)
                self.pair_counts[key] = self.pair_counts.get(key, 0.0) + 1.0

    def lag_pmi(self, source_id: str, target_id: str, *, lag: int = 1) -> float:
        """@op_count: O(1)."""
        pair = self.pair_counts.get((source_id, target_id, int(lag)), 0.0)
        source = self.event_counts.get(source_id, 0.0)
        target = self.event_counts.get(target_id, 0.0)
        if pair <= 0.0 or source <= 0.0 or target <= 0.0 or self.total_positions <= 0.0:
            return 0.0
        smoothing = float(load_constant("narrative.pmi_smoothing"))
        numerator = (pair + smoothing) * (self.total_positions + smoothing)
        denominator = (source + smoothing) * (target + smoothing)
        return log(numerator / denominator)

    def narrative_candidate(self, chain_sa_ids: Iterable[str]) -> StateItem | None:
        """@op_count: O(chain_length)."""
        chain = tuple(chain_sa_ids)
        min_length = int(load_constant("narrative.min_chain_length"))
        if len(chain) < min_length:
            return None
        scores: list[float] = []
        for left, right in zip(chain, chain[1:]):
            forward = self.lag_pmi(left, right)
            reverse = self.lag_pmi(right, left)
            if forward < float(load_constant("narrative.min_lag_pmi")):
                return None
            if forward - reverse < float(load_constant("narrative.reverse_margin")):
                return None
            if self.pair_counts.get((left, right, 1), 0.0) < float(load_constant("narrative.min_pair_count")):
                return None
            scores.append(forward)
        score = min(scores) if scores else 0.0
        return StateItem(
            sa_id="VocabSA::narrative::" + "->".join(chain),
            family="narrative",
            label="narrative_chain",
            real_energy=score,
            cognitive_pressure=score,
            channel_signature=("narrative",),
            source="lag_pmi",
            metadata={
                "chain_sa_ids": chain,
                "edge_scores": tuple(scores),
                "lag": 1,
            },
        )
