from __future__ import annotations

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StateItem, StatePool, load_constant


def reify_deliberative_conclusion(
    state_pool: StatePool,
    *,
    conclusion_sa_id: str,
    support: float,
    tick: int,
    source_hypothesis_ids: tuple[str, ...],
) -> StateItem | None:
    """@op_count: O(1)."""
    existing = state_pool.get(conclusion_sa_id)
    current_r = 0.0 if existing is None else existing.real_energy
    support_value = max(0.0, float(support))
    if support_value - current_r < float(load_constant("deliberative.conclusion_R_delta_threshold")):
        return None
    real_energy = max(
        float(load_constant("deliberative.conclusion_R_floor")),
        min(1.0, support_value * float(load_constant("deliberative.virtual_to_main_dilution"))),
    )
    item = existing or StateItem(
        sa_id=conclusion_sa_id,
        family="hypothesis",
        label="deliberative_conclusion",
        channel_signature=("deliberative",),
        source="deliberative_virtual_track",
        metadata={},
    )
    item.real_energy = real_energy
    item.cognitive_pressure = real_energy - item.virtual_energy
    item.last_tick = int(tick)
    item.metadata["source_hypothesis_ids"] = source_hypothesis_ids
    item.metadata["framework"] = "deliberative_virtual_track"
    state_pool.items[item.sa_id] = item
    marker = MarkerEvent(
        tick=int(tick),
        kind="INFERRED",
        target_sa_id=item.sa_id,
        real_energy=real_energy,
        origin="deliberative_virtual_track",
        metadata={
            "ledger_source": "imagination",
            "source_hypothesis_ids": source_hypothesis_ids,
        },
    )
    state_pool.observe_external(marker, tick=tick)
    return item
