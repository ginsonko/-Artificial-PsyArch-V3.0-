from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from runtime.cognitive.deliberative.conclusion_reify import reify_deliberative_conclusion
from runtime.cognitive.state_pool.state_pool import StatePool, load_constant


@dataclass(frozen=True)
class VirtualHypothesis:
    hypothesis_sa_id: str
    conclusion_sa_id: str
    support: float


@dataclass(frozen=True)
class DeliberativeTrace:
    entered: bool
    virtual_steps: int
    conclusion_sa_id: str
    reified: bool
    inferred_marker_spawned: bool


def run_deliberative_virtual_track(
    state_pool: StatePool,
    hypotheses: Iterable[VirtualHypothesis],
    *,
    tick: int,
) -> DeliberativeTrace:
    """@op_count: O(hypothesis_count log hypothesis_count)."""
    ordered = sorted(tuple(hypotheses), key=lambda item: (item.support, item.hypothesis_sa_id), reverse=True)
    if not ordered:
        return DeliberativeTrace(False, 0, "", False, False)
    best = ordered[0]
    if best.support < float(load_constant("deliberative.enter_threshold")):
        return DeliberativeTrace(False, 0, best.conclusion_sa_id, False, False)
    max_steps = int(load_constant("deliberative.max_virtual_steps_per_turn"))
    visited = ordered[:max_steps]
    item = reify_deliberative_conclusion(
        state_pool,
        conclusion_sa_id=best.conclusion_sa_id,
        support=best.support,
        tick=tick,
        source_hypothesis_ids=tuple(hypothesis.hypothesis_sa_id for hypothesis in visited),
    )
    marker_id = f"marker::INFERRED::{best.conclusion_sa_id}"
    return DeliberativeTrace(
        entered=True,
        virtual_steps=len(visited),
        conclusion_sa_id=best.conclusion_sa_id,
        reified=item is not None,
        inferred_marker_spawned=state_pool.get(marker_id) is not None,
    )
