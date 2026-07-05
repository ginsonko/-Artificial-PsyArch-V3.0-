from __future__ import annotations

from math import exp, sqrt
from typing import Protocol

from runtime.cognitive.state_pool.state_pool import load_constant


class DraftFocusLike(Protocol):
    focus_row: int
    focus_col: int
    focus_span: int
    focus_shape: str
    attention_energy: float


def compute_cell_percept_r_with_char_focus(
    *,
    cell_row: int,
    cell_col: int,
    focus: DraftFocusLike,
    base_r: float,
) -> float:
    """@op_count: O(1)."""
    dr = abs(int(cell_row) - int(focus.focus_row))
    dc = abs(int(cell_col) - int(focus.focus_col))
    shape = str(focus.focus_shape)
    if shape == "column":
        distance = float(dc)
    elif shape == "row":
        distance = float(dr)
    elif shape == "rect":
        distance = float(max(dr, dc))
    else:
        distance = sqrt(float(dr * dr + dc * dc))
    span = max(1.0, float(focus.focus_span))
    if distance <= span:
        modulation = 1.0
    else:
        sigma = max(1.0, span * float(load_constant("curriculum.draft_grid.focus_sigma_multiplier")))
        decay_distance = distance - span
        modulation = exp(-((decay_distance * decay_distance) / (float(2) * sigma * sigma)))
        modulation = max(float(load_constant("curriculum.draft_grid.focus_min_modulation")), modulation)
    return float(base_r) * modulation * max(0.0, float(focus.attention_energy))
