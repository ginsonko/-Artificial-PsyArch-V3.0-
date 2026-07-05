from __future__ import annotations

from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


def has_live_external_evidence_this_tick(item: StateItem, *, tick: int) -> bool:
    """@op_count: O(1)."""
    return int(item.metadata.get("live_external_tick", -1)) == int(tick)


def compute_real_evidence_cap(item: StateItem, *, tick: int) -> float:
    """@op_count: O(1)."""
    if has_live_external_evidence_this_tick(item, tick=tick):
        ruler = item.real_energy
    else:
        ruler = 0.0
    ratio = float(load_constant("composed_vocab.target_cap_ratio"))
    return max(0.0, ruler * ratio)


def apply_real_evidence_cap(item: StateItem, *, tick: int) -> float:
    """@op_count: O(1)."""
    cap = compute_real_evidence_cap(item, tick=tick)
    item.virtual_energy = min(item.virtual_energy, cap)
    item.cognitive_pressure = item.real_energy - item.virtual_energy
    return cap

