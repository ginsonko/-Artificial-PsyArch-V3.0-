from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Hashable, Iterable

from runtime.cognitive.sdpl.packet import LearningPacket
from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass
class PairStats:
    count: float = 0.0
    packet_counts: dict[Hashable, float] = field(default_factory=dict)

    def observe(self, packet_key: Hashable) -> None:
        """@op_count: O(1)."""
        self.count = self.count + 1.0
        self.packet_counts[packet_key] = self.packet_counts.get(packet_key, 0.0) + 1.0


class SparsePairwiseGraph:
    """Top-k sparse pairwise co-occurrence graph under SDPL packet keys."""

    def __init__(self) -> None:
        self.edges: dict[tuple[str, str], PairStats] = {}

    def observe_packet(self, packet: LearningPacket) -> None:
        """@op_count: O(content^2)."""
        packet_key = packet.packet_key()
        for left, right in combinations(_sorted_items(packet.content_sas), 2):
            self.observe_pair(left.sa_id, right.sa_id, packet_key)
        self._compact()

    def observe_pair(self, left: str, right: str, packet_key: Hashable) -> None:
        """@op_count: O(1)."""
        key = tuple(sorted((left, right)))
        self.edges.setdefault(key, PairStats()).observe(packet_key)

    def top_partners(self, sa_id: str) -> tuple[tuple[str, float], ...]:
        """@op_count: O(edge_count log edge_count)."""
        partners: list[tuple[str, float]] = []
        for (left, right), stats in self.edges.items():
            if left == sa_id:
                partners.append((right, stats.count))
            elif right == sa_id:
                partners.append((left, stats.count))
        partners.sort(key=lambda item: (item[1], item[0]), reverse=True)
        limit = int(load_constant("composed_vocab.pairwise.max_partners_per_sa"))
        return tuple(partners[:limit])

    def pair_count(self, left: str, right: str) -> float:
        """@op_count: O(1)."""
        return self.edges.get(tuple(sorted((left, right))), PairStats()).count

    def _compact(self) -> None:
        limit = int(load_constant("composed_vocab.pairwise.max_partners_per_sa"))
        if limit <= 0:
            self.edges.clear()
            return
        allowed: set[tuple[str, str]] = set()
        all_ids = {sa_id for edge in self.edges for sa_id in edge}
        for sa_id in all_ids:
            for partner, _ in self.top_partners(sa_id):
                allowed.add(tuple(sorted((sa_id, partner))))
        for key in tuple(self.edges):
            if key not in allowed:
                del self.edges[key]


def _sorted_items(items: Iterable[StateItem]) -> tuple[StateItem, ...]:
    return tuple(sorted(items, key=lambda item: item.sa_id))

