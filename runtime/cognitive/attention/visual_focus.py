from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


VISUAL_FOCUS_ACTIONS = (
    "saccade_to_visual",
    "fixate_visual",
    "release_visual",
)


@dataclass(frozen=True)
class VisualFocusProposal:
    action_id: str
    action_kind: str
    target_sa_id: str
    score: float
    rationale_features: dict[str, float]


def propose_visual_focus_actions(
    items: Iterable[StateItem],
    *,
    current_focus_id: str | None = None,
) -> tuple[VisualFocusProposal, ...]:
    """@op_count: O(item_count log item_count)."""
    visual_items = tuple(item for item in items if _is_visual_item(item))
    if not visual_items:
        return ()
    ordered = sorted(visual_items, key=lambda item: (_visual_salience(item), item.sa_id), reverse=True)
    target = ordered[0]
    release_target = max(visual_items, key=lambda item: (item.fatigue, item.sa_id))
    return (
        _proposal("saccade_to_visual", target, _visual_salience(target), current_focus_id),
        _proposal("fixate_visual", target, _visual_salience(target) + target.attention_energy, current_focus_id),
        _proposal("release_visual", release_target, _release_score(release_target), current_focus_id),
    )


def apply_visual_focus_action(item: StateItem, proposal: VisualFocusProposal, *, tick: int) -> None:
    """@op_count: O(1)."""
    gain = float(load_constant("visual_attention.focus_attention_gain"))
    item.attention_energy = item.attention_energy + gain
    item.gain_ledger.inject("residual_mass", gain)
    item.last_tick = int(tick)
    item.metadata["last_visual_focus_action"] = proposal.action_kind


def visual_focus_overlay(proposals: Iterable[VisualFocusProposal]) -> tuple[dict[str, object], ...]:
    """@op_count: O(action_count log action_count)."""
    ordered = sorted(tuple(proposals), key=lambda item: (item.score, item.action_id), reverse=True)
    limit = int(load_constant("visual_attention.overlay_top_k"))
    return tuple(
        {
            "action_id": proposal.action_id,
            "action_kind": proposal.action_kind,
            "target_sa_id": proposal.target_sa_id,
            "score": proposal.score,
        }
        for proposal in ordered[:limit]
    )


def _proposal(
    action_kind: str,
    item: StateItem,
    score: float,
    current_focus_id: str | None,
) -> VisualFocusProposal:
    return VisualFocusProposal(
        action_id=f"{action_kind}::{item.sa_id}",
        action_kind=action_kind,
        target_sa_id=item.sa_id,
        score=max(0.0, float(score)),
        rationale_features={
            "R": item.real_energy,
            "A": item.attention_energy,
            "P": item.cognitive_pressure,
            "F": item.fatigue,
        },
    )


def _visual_salience(item: StateItem) -> float:
    return max(0.0, item.real_energy + item.attention_energy + item.cognitive_pressure - item.fatigue)


def _release_score(item: StateItem) -> float:
    threshold = float(load_constant("visual_attention.release_fatigue_threshold"))
    return max(0.0, item.fatigue - threshold)


def _is_visual_item(item: StateItem) -> bool:
    return "vision" in item.channel_signature
