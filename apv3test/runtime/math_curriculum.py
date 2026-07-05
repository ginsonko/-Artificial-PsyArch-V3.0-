from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from apv3test.runtime.draft_grid import (
    CharFocusAction,
    DraftCharFocus,
    DraftGrid,
    apply_char_focus_action,
    movement_similarity,
    relative_focus_moves,
)


@dataclass
class OpaqueMathFactStore:
    facts: dict[tuple[str, ...], tuple[str, ...]] = field(default_factory=dict)
    fact_ids: dict[tuple[str, ...], str] = field(default_factory=dict)

    def teach_fact(self, operands: tuple[str, ...], result_tokens: tuple[str, ...]) -> str:
        key = tuple(str(item) for item in operands)
        self.facts[key] = tuple(str(item) for item in result_tokens)
        fact_id = "fact::" + hashlib.sha256(("|".join(key + self.facts[key])).encode("utf-8")).hexdigest()[:16]
        self.fact_ids[key] = fact_id
        return fact_id

    def recall(self, operands: tuple[str, ...]) -> tuple[str, ...]:
        return self.facts[tuple(str(item) for item in operands)]


@dataclass(frozen=True)
class VerticalTrace:
    answer: str
    grid_text: str
    focus_actions: tuple[CharFocusAction, ...]
    relative_moves: tuple[tuple[int, int], ...]
    fact_ids_used: tuple[str, ...]


def run_taught_vertical_addition(
    top_digits: tuple[str, ...],
    bottom_digits: tuple[str, ...],
    fact_store: OpaqueMathFactStore,
    *,
    origin_row: int,
    origin_col: int,
) -> VerticalTrace:
    grid = DraftGrid()
    focus = DraftCharFocus(focus_row=int(origin_row), focus_col=int(origin_col), focus_shape="column")
    actions: list[CharFocusAction] = []
    fact_ids: list[str] = []
    width = max(len(top_digits), len(bottom_digits))
    top = _left_pad(top_digits, width)
    bottom = _left_pad(bottom_digits, width)
    for index, char in enumerate(top):
        grid.write_at(int(origin_row), int(origin_col) + index, char, tick=index + 1)
    for index, char in enumerate(bottom):
        grid.write_at(int(origin_row) + 1, int(origin_col) + index, char, tick=index + 1)

    answer_cells: dict[int, str] = {}
    carry: tuple[str, ...] = ()
    for offset in range(width - 1, -1, -1):
        action = CharFocusAction(
            action_id=f"move_column::{width - 1 - offset}",
            kind="move_char_focus_to",
            row=int(origin_row),
            col=int(origin_col) + offset,
        )
        focus = apply_char_focus_action(focus, action, grid)
        actions.append(action)
        operands = tuple(item for item in (top[offset], bottom[offset], *carry) if item.strip())
        result = fact_store.recall(operands)
        fact_ids.append(fact_store.fact_ids[operands])
        answer_cells[offset] = result[-1]
        carry = result[:-1]
    if carry:
        answer_cells[-1] = carry[-1]
    for offset, char in answer_cells.items():
        grid.write_at(int(origin_row) + 2, int(origin_col) + offset, char, tick=width + offset + 3)
    answer = "".join(answer_cells[index] for index in sorted(answer_cells))
    return VerticalTrace(
        answer=answer,
        grid_text=grid.visible_text(),
        focus_actions=tuple(actions),
        relative_moves=relative_focus_moves(actions),
        fact_ids_used=tuple(fact_ids),
    )


def compare_vertical_origin_invariance(left: VerticalTrace, right: VerticalTrace) -> float:
    return movement_similarity(left.relative_moves, right.relative_moves)


def _left_pad(digits: tuple[str, ...], width: int) -> tuple[str, ...]:
    return tuple(" " for _ in range(max(0, int(width) - len(digits)))) + tuple(digits)
