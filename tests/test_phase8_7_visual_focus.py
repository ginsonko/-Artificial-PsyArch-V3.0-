from __future__ import annotations

from runtime.cognitive.attention.visual_focus import (
    VISUAL_FOCUS_ACTIONS,
    apply_visual_focus_action,
    propose_visual_focus_actions,
    visual_focus_overlay,
)
from runtime.cognitive.state_pool.state_pool import StateItem


def _visual_item(sa_id: str, *, real: float, pressure: float, fatigue: float = 0.0) -> StateItem:
    return StateItem(
        sa_id=sa_id,
        family="percept",
        label=sa_id,
        real_energy=real,
        attention_energy=real,
        cognitive_pressure=pressure,
        fatigue=fatigue,
        channel_signature=("vision", "color"),
    )


def test_visual_focus_proposes_three_attention_actions_from_sa_competition() -> None:
    yellow = _visual_item("vision::color::yellow::obj", real=0.9, pressure=0.5)
    blue = _visual_item("vision::color::blue::obj", real=0.2, pressure=0.1, fatigue=0.9)

    proposals = propose_visual_focus_actions((yellow, blue), current_focus_id=yellow.sa_id)

    assert tuple(proposal.action_kind for proposal in proposals) == VISUAL_FOCUS_ACTIONS
    assert proposals[0].target_sa_id == yellow.sa_id
    assert proposals[2].target_sa_id == blue.sa_id


def test_visual_focus_action_updates_attention_with_ledger_trace() -> None:
    item = _visual_item("vision::shape::apple::obj", real=0.5, pressure=0.4)
    proposal = propose_visual_focus_actions((item,))[0]
    before = item.attention_energy

    apply_visual_focus_action(item, proposal, tick=12)

    assert item.attention_energy > before
    assert item.gain_ledger.gain_by_source["residual_mass"] > 0.0
    assert item.metadata["last_visual_focus_action"] == proposal.action_kind


def test_visual_focus_overlay_is_renderable_trace_not_cognitive_payload() -> None:
    item = _visual_item("vision::x_bucket::left::obj", real=0.6, pressure=0.6)
    overlay = visual_focus_overlay(propose_visual_focus_actions((item,)))

    assert overlay
    assert set(overlay[0]) == {"action_id", "action_kind", "target_sa_id", "score"}
