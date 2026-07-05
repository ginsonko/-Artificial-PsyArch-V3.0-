from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig


@dataclass(frozen=True)
class RelationSignature:
    token: str
    features: frozenset[str]


@dataclass(frozen=True)
class ColumnCoherence:
    score: float
    pair_count: int
    signatures: tuple[RelationSignature, ...]


class RelationCoherenceScorer:
    """Read-only relation-overlap scorer for aligned paradigm columns."""

    def __init__(self, config: APV3ParadigmDiscoveryConfig | None = None) -> None:
        self.config = config or APV3ParadigmDiscoveryConfig()

    def score_column(self, sequences: Sequence[Sequence[str]], column_values: Sequence[str | None]) -> ColumnCoherence:
        relation_map = self._relation_map(sequences)
        signatures = tuple(
            RelationSignature(token, frozenset(relation_map.get(token, ())))
            for token in sorted({value for value in column_values if value is not None})
        )
        if len(signatures) <= 1:
            return ColumnCoherence(1.0 if signatures else 0.0, 0, signatures)
        scores = [_jaccard(left.features, right.features) for left, right in combinations(signatures, 2)]
        score = sum(scores) / len(scores) if scores else 0.0
        return ColumnCoherence(round(score, 6), len(scores), signatures)

    def _relation_map(self, sequences: Sequence[Sequence[str]]) -> dict[str, set[str]]:
        relation_map: dict[str, set[str]] = {}
        window = max(1, int(self.config.coherence_neighbor_window))
        for sequence in sequences:
            seq = tuple(sequence)
            for index, token in enumerate(seq):
                features = relation_map.setdefault(token, set())
                for offset in range(1, window + 1):
                    if index - offset >= 0:
                        features.add(f"prev::{offset}::{seq[index - offset]}")
                    if index + offset < len(seq):
                        features.add(f"next::{offset}::{seq[index + offset]}")
                for other in seq:
                    if other != token:
                        features.add(f"co::{other}")
        return relation_map


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)
