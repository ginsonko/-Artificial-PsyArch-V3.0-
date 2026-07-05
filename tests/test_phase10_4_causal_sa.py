from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.causal.causal_sa import spawn_causal_sa
from runtime.cognitive.counterfactual.simulator import CounterfactualModel
from runtime.cognitive.state_pool.state_pool import StateItem, StatePool


def _trace(effect: float):
    pool = StatePool()
    pool.items["event::touch"] = StateItem(sa_id="event::touch", family="event", label="touch", real_energy=1.0)
    pool.items["event::light"] = StateItem(sa_id="event::light", family="event", label="light", real_energy=0.2)
    model = CounterfactualModel()
    model.set_direct_effect("event::touch", "event::light", effect)
    return model.estimate_controlled_direct_effect(pool, source_sa_id="event::touch", target_sa_id="event::light")


def test_causal_sa_spawns_only_from_passing_cde_trace() -> None:
    item = spawn_causal_sa(_trace(0.4))

    assert item is not None
    assert item.family == "causal"
    assert item.source == "controlled_direct_effect"
    assert item.metadata["framework"] == "controlled_direct_effect"
    assert item.metadata["source_sa_id"] == "event::touch"
    assert item.metadata["target_sa_id"] == "event::light"


def test_failed_cde_trace_does_not_become_causal_relation() -> None:
    assert spawn_causal_sa(_trace(0.0)) is None


def test_phase10_4_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "10.4"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 10.4 deliverables present" in completed.stdout
