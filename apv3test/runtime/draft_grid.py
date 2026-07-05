from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Iterable, Mapping

from runtime.cognitive.attention.draft_focus_modulation import compute_cell_percept_r_with_char_focus
from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


FOCUS_SHAPES = ("cell", "row", "column", "rect")


@dataclass
class DraftGridCell:
    char: str = " "
    written_at_tick: int = -1
    revision_count: int = 0


@dataclass
class DraftGrid:
    rows: int = field(default_factory=lambda: int(load_constant("curriculum.draft_grid.default_rows")))
    cols: int = field(default_factory=lambda: int(load_constant("curriculum.draft_grid.default_cols")))
    cells: dict[tuple[int, int], DraftGridCell] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.cells:
            for row in range(self.rows):
                for col in range(self.cols):
                    self.cells[(row, col)] = DraftGridCell()

    def write_at(self, row: int, col: int, char: str, *, tick: int) -> None:
        if not (0 <= int(row) < self.rows and 0 <= int(col) < self.cols):
            raise IndexError("draft grid position out of bounds")
        if len(str(char)) != 1:
            raise ValueError("write_at expects a single character")
        cell = self.cells[(int(row), int(col))]
        cell.char = str(char)
        cell.written_at_tick = int(tick)
        cell.revision_count += 1

    def row_text(self, row: int) -> str:
        return "".join(self.cells[(int(row), col)].char for col in range(self.cols)).rstrip()

    def visible_text(self) -> str:
        rows = [self.row_text(row) for row in range(self.rows)]
        while rows and not rows[-1]:
            rows.pop()
        return "\n".join(rows)


@dataclass
class DraftCharFocus:
    focus_row: int = 0
    focus_col: int = 0
    focus_span: int = 1
    focus_shape: str = "cell"
    attention_energy: float = 1.0

    def slot_context(self) -> tuple[str, ...]:
        return (f"char_focus_shape:{self.focus_shape}", _bucket(self.attention_energy))


@dataclass(frozen=True)
class CharFocusAction:
    action_id: str
    kind: str
    row: int = 0
    col: int = 0
    row_delta: int = 0
    col_delta: int = 0
    shape: str = "cell"
    span_delta: int = 0


@dataclass(frozen=True)
class DraftGridPercept:
    item: StateItem
    marker: MarkerEvent
    relative_row: int
    relative_col: int


def apply_char_focus_action(focus: DraftCharFocus, action: CharFocusAction, grid: DraftGrid) -> DraftCharFocus:
    if action.kind == "move_char_focus_to":
        return _bounded_focus(focus, grid, row=action.row, col=action.col)
    if action.kind == "char_focus_shift":
        return _bounded_focus(
            focus,
            grid,
            row=focus.focus_row + action.row_delta,
            col=focus.focus_col + action.col_delta,
        )
    if action.kind == "char_focus_set_shape":
        return DraftCharFocus(
            focus_row=focus.focus_row,
            focus_col=focus.focus_col,
            focus_span=focus.focus_span,
            focus_shape=action.shape if action.shape in FOCUS_SHAPES else focus.focus_shape,
            attention_energy=focus.attention_energy,
        )
    if action.kind == "char_focus_adjust_span":
        return DraftCharFocus(
            focus_row=focus.focus_row,
            focus_col=focus.focus_col,
            focus_span=max(1, focus.focus_span + int(action.span_delta)),
            focus_shape=focus.focus_shape,
            attention_energy=focus.attention_energy,
        )
    return focus


def emit_draft_grid_percepts(grid: DraftGrid, focus: DraftCharFocus, *, tick: int) -> tuple[DraftGridPercept, ...]:
    base_r = float(load_constant("curriculum.draft_grid.cell_percept_base_R"))
    threshold = float(load_constant("curriculum.draft_grid.cell_percept_emit_threshold"))
    rows: list[DraftGridPercept] = []
    for (row, col), cell in grid.cells.items():
        if not cell.char.strip():
            continue
        real_energy = compute_cell_percept_r_with_char_focus(
            cell_row=row,
            cell_col=col,
            focus=focus,
            base_r=base_r,
        )
        if real_energy < threshold:
            continue
        relative_row = int(row) - int(focus.focus_row)
        relative_col = int(col) - int(focus.focus_col)
        item = StateItem(
            sa_id=_opaque_cell_sa_id(cell.char, relative_row, relative_col, focus.focus_shape),
            family="percept",
            label="draft_grid_cell",
            real_energy=real_energy,
            attention_energy=real_energy,
            cognitive_pressure=real_energy,
            channel_signature=("text", "draft_grid"),
            source="self_draft_grid",
            metadata={
                "cognitive_content": {
                    "char": cell.char,
                    "rel_dr": _sign_bucket(relative_row),
                    "rel_dc": _sign_bucket(relative_col),
                    "focus_shape": focus.focus_shape,
                },
                "perceived_substrate": "SELF_DRAFT_GRID",
            },
        )
        marker = MarkerEvent(
            tick=int(tick),
            kind="PERCEIVED",
            target_sa_id=item.sa_id,
            real_energy=real_energy,
            metadata={
                "substrate": "SELF_DRAFT_GRID",
                "ledger_source": "self_draft",
            },
        )
        rows.append(DraftGridPercept(item=item, marker=marker, relative_row=relative_row, relative_col=relative_col))
    rows.sort(key=lambda percept: (percept.item.real_energy, percept.item.sa_id), reverse=True)
    return tuple(rows[: int(load_constant("curriculum.draft_grid.percept_top_k"))])


def relative_focus_moves(actions: Iterable[CharFocusAction]) -> tuple[tuple[int, int], ...]:
    moves = []
    last: tuple[int, int] | None = None
    for action in actions:
        if action.kind == "move_char_focus_to":
            current = (int(action.row), int(action.col))
            if last is not None:
                moves.append((current[0] - last[0], current[1] - last[1]))
            last = current
        elif action.kind == "char_focus_shift":
            moves.append((int(action.row_delta), int(action.col_delta)))
    return tuple(moves)


def movement_similarity(left: tuple[tuple[int, int], ...], right: tuple[tuple[int, int], ...]) -> float:
    if not left and not right:
        return 1.0
    total = max(len(left), len(right), 1)
    matches = sum(1 for a, b in zip(left, right) if a == b)
    return float(matches) / float(total)


def _bounded_focus(focus: DraftCharFocus, grid: DraftGrid, *, row: int, col: int) -> DraftCharFocus:
    return DraftCharFocus(
        focus_row=max(0, min(grid.rows - 1, int(row))),
        focus_col=max(0, min(grid.cols - 1, int(col))),
        focus_span=focus.focus_span,
        focus_shape=focus.focus_shape,
        attention_energy=focus.attention_energy,
    )


def _opaque_cell_sa_id(char: str, relative_row: int, relative_col: int, focus_shape: str) -> str:
    raw = f"{char}|{_sign_bucket(relative_row)}|{_sign_bucket(relative_col)}|{focus_shape}".encode("utf-8")
    return f"percept::draft_grid::{hashlib.sha256(raw).hexdigest()[:16]}"


def _sign_bucket(value: int) -> str:
    if value < 0:
        return "before"
    if value > 0:
        return "after"
    return "same"


def _bucket(value: float) -> str:
    if value < 0.3:
        return "focus_r:low"
    if value < 0.7:
        return "focus_r:mid"
    return "focus_r:high"

