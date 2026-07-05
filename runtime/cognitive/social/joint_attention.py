from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StatePool, load_constant


@dataclass(frozen=True)
class FocusSignal:
    holder_entity_id: str
    target_sa_id: str
    confidence: float = 1.0


@dataclass(frozen=True)
class JointAttentionTrace:
    marker: MarkerEvent | None
    alignment: float


def update_joint_attention(
    state_pool: StatePool,
    *,
    self_focus: FocusSignal,
    other_focus: FocusSignal,
    tick: int,
) -> JointAttentionTrace:
    """@op_count: O(1)."""
    alignment = _alignment(self_focus, other_focus)
    if alignment < float(load_constant("joint_attention.min_alignment")):
        return JointAttentionTrace(marker=None, alignment=alignment)
    marker = MarkerEvent(
        tick=int(tick),
        kind="JOINT_ATTENTION",
        target_sa_id=self_focus.target_sa_id,
        real_energy=alignment * float(load_constant("joint_attention.marker_gain")),
        origin="social_focus",
        metadata={
            "self_entity_id": self_focus.holder_entity_id,
            "other_entity_id": other_focus.holder_entity_id,
            "ledger_source": "user_directed",
        },
    )
    state_pool.observe_external(marker, tick=tick)
    target = state_pool.get(self_focus.target_sa_id)
    if target is not None:
        gain = alignment * float(load_constant("joint_attention.focus_attention_gain"))
        target.attention_energy = target.attention_energy + gain
        target.gain_ledger.inject("user_directed", gain)
    return JointAttentionTrace(marker=marker, alignment=alignment)


def _alignment(self_focus: FocusSignal, other_focus: FocusSignal) -> float:
    if self_focus.target_sa_id != other_focus.target_sa_id:
        return 0.0
    return min(1.0, max(0.0, self_focus.confidence * other_focus.confidence))
