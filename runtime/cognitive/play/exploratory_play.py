from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass(frozen=True)
class PlayProposal:
    action_id: str
    target_sa_id: str
    boredom: float
    score: float


def propose_exploratory_play(items: Iterable[StateItem]) -> tuple[PlayProposal, ...]:
    """@op_count: O(active_sa log active_sa)."""
    item_tuple = tuple(items)
    if not item_tuple:
        return ()
    mean_pressure = sum(max(0.0, item.cognitive_pressure) for item in item_tuple) / max(1.0, float(len(item_tuple)))
    if mean_pressure > float(load_constant("play.low_pressure_threshold")):
        return ()
    proposals = []
    for item in item_tuple:
        boredom = _boredom_signal(item)
        if boredom < float(load_constant("play.boredom_threshold")):
            continue
        proposals.append(
            PlayProposal(
                action_id="play_action::explore_variant",
                target_sa_id=item.sa_id,
                boredom=boredom,
                score=boredom + item.attention_energy * float(load_constant("play.attention_weight")),
            )
        )
    return tuple(sorted(proposals, key=lambda proposal: (proposal.score, proposal.target_sa_id), reverse=True))


def _boredom_signal(item: StateItem) -> float:
    metadata_boredom = float(item.metadata.get("boredom", 0.0))
    marker_boredom = item.real_energy if item.sa_id.startswith("marker::BOREDOM::") else 0.0
    return min(1.0, max(metadata_boredom, marker_boredom))
