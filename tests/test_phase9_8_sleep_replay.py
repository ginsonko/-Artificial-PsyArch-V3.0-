from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.long_term.layers import LongTermDualLayer
from runtime.cognitive.sleep.replay_consolidation import replay_for_consolidation
from runtime.cognitive.state_pool.state_pool import StateItem


def _item(sa_id: str, real: float) -> StateItem:
    return StateItem(
        sa_id=sa_id,
        family="percept",
        label=sa_id,
        real_energy=real,
        cognitive_pressure=real,
        channel_signature=("sleep", sa_id),
    )


def test_sleep_replay_rehydrates_cold_items_with_remembered_markers() -> None:
    layer = LongTermDualLayer(active_max=5, cold_capacity=10)
    layer.admit_short_term(_item("sa::day_event", 0.8))

    trace = replay_for_consolidation(layer, tick=10)

    assert trace.replayed_sa_ids == ("sa::day_event",)
    assert trace.rehydration.markers[0].kind == "REMEMBERED"
    assert "sa::day_event" in layer.active_pool


def test_sleep_replay_is_bounded_and_prefers_high_long_term_energy() -> None:
    layer = LongTermDualLayer(active_max=5, cold_capacity=10)
    for index in range(5):
        layer.admit_short_term(_item(f"sa::{index}", real=0.1 + index * 0.1))

    trace = replay_for_consolidation(layer, tick=10)

    assert len(trace.replayed_sa_ids) == 3
    assert "sa::4" in trace.replayed_sa_ids


def test_sleep_replay_increments_consolidation_count_without_external_input() -> None:
    layer = LongTermDualLayer(active_max=5, cold_capacity=10)
    layer.admit_short_term(_item("sa::quiet_learning", 0.7))

    replay_for_consolidation(layer, tick=10)
    replay_for_consolidation(layer, tick=11)

    assert layer.cold_index["sa::quiet_learning"].metadata["sleep_replay_count"] == 2


def test_phase9_8_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "9.8"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 9.8 deliverables present" in completed.stdout
