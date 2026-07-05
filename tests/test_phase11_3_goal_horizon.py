from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.goal.horizon import create_goal_sa, update_goal_progress
from runtime.cognitive.state_pool.state_pool import StatePool


def test_goal_sa_keeps_long_horizon_pressure_until_completed() -> None:
    pool = StatePool()
    goal = create_goal_sa(pool, goal_id="learn_chars", target_sa_id="curriculum::chars", tick=1)

    first = update_goal_progress(goal, evidence_strength=1.0, tick=2)

    assert pool.get(goal.sa_id) is goal
    assert goal.family == "goal"
    assert first.completed is False
    assert goal.cognitive_pressure > 0.0


def test_goal_completion_lowers_pressure_after_enough_progress() -> None:
    pool = StatePool()
    goal = create_goal_sa(pool, goal_id="learn_chars", target_sa_id="curriculum::chars", tick=1)

    trace = None
    for tick in range(2, 6):
        trace = update_goal_progress(goal, evidence_strength=1.0, tick=tick)

    assert trace is not None
    assert trace.completed is True
    assert goal.metadata["completed"] is True
    assert goal.cognitive_pressure == 0.0


def test_phase11_3_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "11.3"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 11.3 deliverables present" in completed.stdout
