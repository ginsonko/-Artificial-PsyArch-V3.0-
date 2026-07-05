from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.composed_vocab.sparse_pairwise import SparsePairwiseGraph


@dataclass(frozen=True)
class ContrastGeneralizationTrace:
    target_pair: tuple[str, str]
    target_count: float
    strongest_distractor_count: float
    margin: float

    @property
    def separates_target(self) -> bool:
        return self.margin > 0.0


def contrast_pairwise_margin(
    graph: SparsePairwiseGraph,
    *,
    target_pair: tuple[str, str],
    distractor_pairs: tuple[tuple[str, str], ...],
) -> ContrastGeneralizationTrace:
    """@op_count: O(distractor_count)."""
    target_count = graph.pair_count(target_pair[0], target_pair[1])
    distractor_counts = tuple(graph.pair_count(left, right) for left, right in distractor_pairs)
    strongest_distractor = max(distractor_counts) if distractor_counts else 0.0
    return ContrastGeneralizationTrace(
        target_pair=tuple(sorted(target_pair)),
        target_count=target_count,
        strongest_distractor_count=strongest_distractor,
        margin=target_count - strongest_distractor,
    )
