from __future__ import annotations

from runtime.cognitive.state_pool.state_pool import StateItem, load_constant
from runtime.cognitive.state_pool.target_cap import compute_real_evidence_cap


def compute_memory_support_v_floor(item: StateItem, *, cue_alignment: float = 0.0) -> float:
    """@op_count: O(1)."""
    if not bool(item.metadata.get("long_term_layer", False)):
        return 0.0
    ratio = float(load_constant("long_term.memory_V_admit_ratio"))
    return float(item.metadata.get("long_term_R", item.real_energy)) * float(cue_alignment) * ratio


def apply_v_double_control(
    item: StateItem,
    *,
    tick: int,
    cue_alignment: float = 0.0,
) -> tuple[float, float]:
    """@op_count: O(1)."""
    v_cap = compute_real_evidence_cap(item, tick=tick)
    v_floor = compute_memory_support_v_floor(item, cue_alignment=cue_alignment)
    if v_floor > v_cap:
        item.virtual_energy = max(item.virtual_energy, v_floor)
    else:
        item.virtual_energy = max(v_floor, min(item.virtual_energy, v_cap))
    item.cognitive_pressure = item.real_energy - item.virtual_energy
    return v_floor, v_cap

