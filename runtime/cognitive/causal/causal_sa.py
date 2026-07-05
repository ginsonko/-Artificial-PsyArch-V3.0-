from __future__ import annotations

from runtime.cognitive.counterfactual.simulator import ControlledDirectEffectTrace
from runtime.cognitive.state_pool.state_pool import StateItem


def spawn_causal_sa(trace: ControlledDirectEffectTrace) -> StateItem | None:
    """@op_count: O(1)."""
    if not trace.passes_threshold:
        return None
    return StateItem(
        sa_id=f"VocabSA::causal::{trace.source_sa_id}->{trace.target_sa_id}",
        family="causal",
        label="causal_relation",
        real_energy=trace.causal_strength_relative,
        cognitive_pressure=trace.causal_strength_absolute,
        channel_signature=("causal",),
        source=trace.framework,
        metadata={
            "source_sa_id": trace.source_sa_id,
            "target_sa_id": trace.target_sa_id,
            "framework": trace.framework,
            "causal_strength_relative": trace.causal_strength_relative,
            "causal_strength_absolute": trace.causal_strength_absolute,
        },
    )
