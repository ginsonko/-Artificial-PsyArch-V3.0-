from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.affect.frustration import helplessness_discount, update_frustration
from runtime.cognitive.state_pool.state_pool import StateItem, StatePool


def _task_item() -> StateItem:
    return StateItem(
        sa_id="task::hard",
        family="goal",
        label="hard task",
        real_energy=0.9,
        cognitive_pressure=0.9,
    )


def test_repeated_high_pressure_failure_emerges_frustration_and_helplessness() -> None:
    pool = StatePool()
    pool.items["task::hard"] = _task_item()

    traces = [
        update_frustration(pool, target_sa_id="task::hard", tick=tick, outcome_reward=0.0, rpe=-1.0)
        for tick in range(1, 4)
    ]

    assert traces[-1].pressure > traces[0].pressure
    assert traces[-1].failure_streak == 3
    assert traces[-1].learned_helplessness is True
    assert traces[-1].abandon_action_id == "affect_action::abandon_current_task"


def test_success_relieves_frustration_streak_without_erasing_state_item() -> None:
    pool = StatePool()
    pool.items["task::hard"] = _task_item()
    failed = update_frustration(pool, target_sa_id="task::hard", tick=1, outcome_reward=0.0, rpe=-1.0)
    relieved = update_frustration(pool, target_sa_id="task::hard", tick=2, outcome_reward=1.0, rpe=0.5)

    assert relieved.failure_streak < failed.failure_streak
    assert pool.get(relieved.frustration_sa_id) is not None
    assert pool.get(relieved.frustration_sa_id).gain_ledger.gain_by_source["feedback"] > 0.0


def test_learned_helplessness_discounts_drive_output_only_when_gate_is_active() -> None:
    pool = StatePool()
    pool.items["task::hard"] = _task_item()
    trace = None
    for tick in range(1, 4):
        trace = update_frustration(pool, target_sa_id="task::hard", tick=tick, outcome_reward=0.0, rpe=-1.0)

    assert helplessness_discount(1.0, trace) < 1.0


def test_phase9_3_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "9.3"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 9.3 deliverables present" in completed.stdout
