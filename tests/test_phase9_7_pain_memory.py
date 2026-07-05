from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.affect.pain_memory import (
    decay_pain_memory,
    register_pain_event,
    should_avoid_due_to_pain,
)
from runtime.cognitive.state_pool.state_pool import StatePool, load_constant


def test_pain_event_spawns_pain_marker_state_with_feedback_ledger() -> None:
    pool = StatePool()

    trace = register_pain_event(pool, target_sa_id="touch::hot", tick=1, intensity=1.0)
    item = pool.get(trace.marker_sa_id)

    assert item is not None
    assert item.label == "PAIN"
    assert item.metadata["pain_memory"] is True
    assert item.gain_ledger.gain_by_source["feedback"] > 0.0


def test_pain_memory_decays_more_slowly_than_mismatch_marker() -> None:
    pool = StatePool()
    trace = register_pain_event(pool, target_sa_id="touch::hot", tick=1, intensity=1.0)
    item = pool.get(trace.marker_sa_id)

    after = decay_pain_memory(item)
    mismatch_decay = float(load_constant("marker.decay_rates.MISMATCH"))

    assert after > mismatch_decay


def test_persistent_pain_crosses_avoidance_gate() -> None:
    pool = StatePool()
    trace = register_pain_event(pool, target_sa_id="touch::hot", tick=1, intensity=1.0)

    assert should_avoid_due_to_pain(pool.get(trace.marker_sa_id)) is True


def test_phase9_7_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "9.7"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 9.7 deliverables present" in completed.stdout
