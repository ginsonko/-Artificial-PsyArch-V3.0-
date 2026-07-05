from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.counterfactual.simulator import CounterfactualModel
from runtime.cognitive.state_pool.state_pool import StateItem, StatePool


def _pool() -> StatePool:
    pool = StatePool()
    pool.items["event::push"] = StateItem(sa_id="event::push", family="event", label="push", real_energy=1.0)
    pool.items["event::move"] = StateItem(sa_id="event::move", family="event", label="move", real_energy=0.2)
    return pool


def test_controlled_direct_effect_trace_passes_for_monotonic_intervention_response() -> None:
    model = CounterfactualModel()
    model.set_direct_effect("event::push", "event::move", 0.4)

    trace = model.estimate_controlled_direct_effect(
        _pool(),
        source_sa_id="event::push",
        target_sa_id="event::move",
    )

    assert trace.framework == "controlled_direct_effect"
    assert trace.passes_threshold is True
    assert trace.monotonic is True
    assert trace.causal_strength_relative > 0.0
    assert trace.means_by_level[1.0] > trace.means_by_level[0.0]


def test_zero_direct_effect_is_rejected_even_when_events_exist() -> None:
    trace = CounterfactualModel().estimate_controlled_direct_effect(
        _pool(),
        source_sa_id="event::push",
        target_sa_id="event::move",
    )

    assert trace.framework == "controlled_direct_effect"
    assert trace.passes_threshold is False
    assert trace.causal_strength_absolute == 0.0


def test_phase10_3_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "10.3"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 10.3 deliverables present" in completed.stdout
