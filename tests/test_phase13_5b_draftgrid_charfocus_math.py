from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from apv3test.runtime.draft_grid import (
    CharFocusAction,
    DraftCharFocus,
    DraftGrid,
    apply_char_focus_action,
    emit_draft_grid_percepts,
)
from apv3test.runtime.math_curriculum import (
    OpaqueMathFactStore,
    compare_vertical_origin_invariance,
    run_taught_vertical_addition,
)
from runtime.cognitive.sdpl.packet import make_packet
from runtime.cognitive.sdpl.q_table_backoff import QTableWithBackoff
from runtime.cognitive.state_pool.state_pool import StateItem


def _fact_store() -> OpaqueMathFactStore:
    store = OpaqueMathFactStore()
    store.teach_fact(("3", "7"), ("1", "0"))
    store.teach_fact(("2", "4", "1"), ("7",))
    return store


def test_phase13_5b_char_focus_modulates_grid_percepts_without_absolute_coordinate_key() -> None:
    grid = DraftGrid(rows=6, cols=8)
    grid.write_at(2, 5, "7", tick=1)
    grid.write_at(2, 4, "3", tick=1)
    focus = DraftCharFocus(focus_row=2, focus_col=5, focus_shape="column", attention_energy=1.0)
    percepts = emit_draft_grid_percepts(grid, focus, tick=2)
    packet = make_packet(
        content_sas=tuple(percept.item for percept in percepts),
        source_markers=tuple(percept.marker for percept in percepts),
        slot_context=focus.slot_context(),
    )
    key_text = str(packet.packet_key())

    assert percepts
    assert "SELF_DRAFT_GRID" in key_text
    assert "char_focus_shape:column" in key_text
    assert "(2, 5)" not in key_text
    assert "origin" not in key_text


def test_phase13_5b_substrate_isolation_keeps_content_only_backoff_transfer() -> None:
    teacher_item = StateItem(
        sa_id="percept::teacher::opaque",
        family="percept",
        label="digit",
        real_energy=0.8,
        metadata={"cognitive_content": {"char": "7"}, "perceived_substrate": "EXTERNAL_VISUAL"},
    )
    self_item = StateItem(
        sa_id="percept::self::opaque",
        family="percept",
        label="digit",
        real_energy=0.8,
        metadata={"cognitive_content": {"char": "7"}, "perceived_substrate": "SELF_DRAFT_GRID"},
    )
    teacher_packet = make_packet(content_sas=(teacher_item,))
    self_packet = make_packet(content_sas=(self_item,))
    q_table = QTableWithBackoff()

    for _ in range(12):
        q_table.update(teacher_packet, "read_digit", outcome=1.0)

    assert teacher_packet.packet_key() != self_packet.packet_key()
    assert teacher_packet.content_key() == self_packet.content_key()
    assert q_table.query(self_packet, "read_digit") > 0.0


def test_phase13_5b_vertical_addition_uses_taught_facts_and_focus_invariant_across_origins() -> None:
    store = _fact_store()
    left = run_taught_vertical_addition(("2", "3"), ("4", "7"), store, origin_row=0, origin_col=2)
    right = run_taught_vertical_addition(("2", "3"), ("4", "7"), store, origin_row=4, origin_col=5)
    similarity = compare_vertical_origin_invariance(left, right)

    assert left.answer == "70"
    assert right.answer == "70"
    assert similarity >= 0.85
    assert all(fact_id.startswith("fact::") for fact_id in left.fact_ids_used)
    assert "fact::add::" not in " ".join(left.fact_ids_used)


def test_phase13_5b_focus_actions_are_general_grid_actions_not_math_coordinate_table() -> None:
    grid = DraftGrid(rows=5, cols=5)
    focus = DraftCharFocus(focus_row=1, focus_col=1)
    shifted = apply_char_focus_action(
        focus,
        CharFocusAction(action_id="shift", kind="char_focus_shift", row_delta=0, col_delta=1),
        grid,
    )
    column = apply_char_focus_action(
        shifted,
        CharFocusAction(action_id="shape", kind="char_focus_set_shape", shape="column"),
        grid,
    )

    assert shifted.focus_col == 2
    assert column.focus_shape == "column"


def test_phase13_5b_redline_has_no_math_solver_or_direct_grid_cell_bypass() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            Path("apv3test/runtime/draft_grid.py"),
            Path("apv3test/runtime/math_curriculum.py"),
        )
    )
    for forbidden in (
        "column_sum",
        "compute_addition",
        "solve_equation",
        "expected_action_sequence",
        "read_grid_cell",
        "filter_by_similarity_to",
        "fact::add::3_7",
    ):
        assert forbidden not in combined


def test_phase13_5b_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "13.5b"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
