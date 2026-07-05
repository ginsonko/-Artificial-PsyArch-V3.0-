from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StateItem, StatePool, load_constant


@dataclass(frozen=True)
class DomainGraspTrace:
    domain_id: str
    support_mean: float
    uncertainty_pressure: float
    knowledge_gap_marker: MarkerEvent | None
    meta_item: StateItem


def assess_domain_grasp(
    state_pool: StatePool,
    *,
    domain_id: str,
    related_sa_ids: Iterable[str],
    uncertainty: float,
    conflict: float,
    tick: int,
) -> DomainGraspTrace:
    """@op_count: O(domain_items)."""
    ids = tuple(related_sa_ids)
    support_values = tuple(
        max(0.0, item.real_energy)
        for item in (state_pool.get(sa_id) for sa_id in ids)
        if item is not None
    )
    support_mean = sum(support_values) / max(float(len(support_values)), 1.0)
    conflict_pressure = max(0.0, float(conflict)) * float(load_constant("metacognition.conflict_weight"))
    uncertainty_pressure = min(1.0, max(0.0, float(uncertainty) + conflict_pressure))
    meta_item = _ensure_meta_item(state_pool, domain_id)
    meta_item.real_energy = 1.0 - min(1.0, support_mean)
    meta_item.cognitive_pressure = uncertainty_pressure
    gain = uncertainty_pressure * float(load_constant("metacognition.attention_gain_scale"))
    meta_item.attention_energy = meta_item.attention_energy + gain
    meta_item.gain_ledger.inject("residual_mass", gain)
    meta_item.last_tick = int(tick)
    meta_item.metadata["related_sa_ids"] = ids
    meta_item.metadata["support_mean"] = support_mean
    meta_item.metadata["uncertainty_pressure"] = uncertainty_pressure
    marker = None
    if _should_spawn_gap(ids, support_mean, uncertainty_pressure):
        marker = MarkerEvent(
            tick=int(tick),
            kind="KNOWLEDGE_GAP",
            target_sa_id=meta_item.sa_id,
            real_energy=uncertainty_pressure,
            origin="metacognition",
            metadata={
                "domain_id": domain_id,
                "ledger_source": "residual_mass",
            },
        )
        state_pool.observe_external(marker, tick=tick)
    return DomainGraspTrace(
        domain_id=domain_id,
        support_mean=support_mean,
        uncertainty_pressure=uncertainty_pressure,
        knowledge_gap_marker=marker,
        meta_item=meta_item,
    )


def _ensure_meta_item(state_pool: StatePool, domain_id: str) -> StateItem:
    sa_id = f"EntitySA::metacognition::{domain_id}"
    item = state_pool.items.get(sa_id)
    if item is None:
        item = StateItem(
            sa_id=sa_id,
            family="self_model",
            label="domain_grasp",
            channel_signature=("metacognition", domain_id),
            source="metacognitive_monitor",
            metadata={"domain_id": domain_id},
        )
        state_pool.items[sa_id] = item
    return item


def _should_spawn_gap(ids: tuple[str, ...], support_mean: float, uncertainty_pressure: float) -> bool:
    return (
        len(ids) >= int(load_constant("metacognition.domain_min_items"))
        and support_mean < float(load_constant("metacognition.low_grasp_threshold"))
        and uncertainty_pressure >= float(load_constant("metacognition.high_uncertainty_threshold"))
    )
