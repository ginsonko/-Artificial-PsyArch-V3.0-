from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.metacognition.monitor import assess_domain_grasp
from runtime.cognitive.state_pool.state_pool import StateItem, StatePool


def _pool_with_support(value: float) -> StatePool:
    pool = StatePool()
    for index in range(3):
        sa_id = f"vocab::item::{index}"
        pool.items[sa_id] = StateItem(sa_id=sa_id, family="vocab", label=sa_id, real_energy=value)
    return pool


def test_low_grasp_high_uncertainty_spawns_knowledge_gap_marker() -> None:
    pool = _pool_with_support(0.1)

    trace = assess_domain_grasp(
        pool,
        domain_id="reading",
        related_sa_ids=tuple(pool.items),
        uncertainty=0.6,
        conflict=0.4,
        tick=5,
    )

    assert trace.knowledge_gap_marker is not None
    assert trace.knowledge_gap_marker.kind == "KNOWLEDGE_GAP"
    assert pool.get(trace.knowledge_gap_marker.sa_id) is not None
    assert trace.meta_item.gain_ledger.gain_by_source["residual_mass"] > 0.0


def test_high_support_domain_does_not_spawn_false_gap() -> None:
    pool = _pool_with_support(0.9)

    trace = assess_domain_grasp(
        pool,
        domain_id="reading",
        related_sa_ids=tuple(pool.items),
        uncertainty=0.1,
        conflict=0.0,
        tick=5,
    )

    assert trace.knowledge_gap_marker is None
    assert trace.support_mean > 0.8


def test_phase11_1_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "11.1"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 11.1 deliverables present" in completed.stdout
