from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.deliberative.virtual_track import VirtualHypothesis, run_deliberative_virtual_track
from runtime.cognitive.state_pool.state_pool import StatePool


def test_deliberative_virtual_track_reifies_conclusion_and_spawns_inferred_marker() -> None:
    pool = StatePool()

    trace = run_deliberative_virtual_track(
        pool,
        (
            VirtualHypothesis("hyp::weak", "hypothesis::ignore", support=0.2),
            VirtualHypothesis("hyp::strong", "hypothesis::answer", support=0.9),
        ),
        tick=4,
    )

    assert trace.entered is True
    assert trace.reified is True
    assert trace.inferred_marker_spawned is True
    assert pool.get("hypothesis::answer") is not None
    assert pool.get("marker::INFERRED::hypothesis::answer") is not None


def test_low_support_hypothesis_does_not_enter_virtual_track() -> None:
    trace = run_deliberative_virtual_track(
        StatePool(),
        (VirtualHypothesis("hyp::weak", "hypothesis::ignore", support=0.1),),
        tick=4,
    )

    assert trace.entered is False
    assert trace.reified is False


def test_phase11_4_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "11.4"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 11.4 deliverables present" in completed.stdout
