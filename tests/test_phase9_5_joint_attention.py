from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.social.joint_attention import FocusSignal, update_joint_attention
from runtime.cognitive.state_pool.state_pool import StateItem, StatePool


def test_shared_focus_spawns_joint_attention_marker_and_boosts_target() -> None:
    pool = StatePool()
    target = StateItem(sa_id="vision::object::apple", family="vision_percept", label="object", real_energy=0.6)
    pool.items[target.sa_id] = target

    trace = update_joint_attention(
        pool,
        self_focus=FocusSignal("self", target.sa_id, confidence=1.0),
        other_focus=FocusSignal("user", target.sa_id, confidence=1.0),
        tick=4,
    )

    assert trace.marker is not None
    assert trace.marker.kind == "JOINT_ATTENTION"
    assert pool.get(trace.marker.sa_id) is not None
    assert target.gain_ledger.gain_by_source["user_directed"] > 0.0


def test_different_focus_does_not_spawn_joint_attention() -> None:
    pool = StatePool()

    trace = update_joint_attention(
        pool,
        self_focus=FocusSignal("self", "vision::left", confidence=1.0),
        other_focus=FocusSignal("user", "vision::right", confidence=1.0),
        tick=4,
    )

    assert trace.marker is None
    assert trace.alignment == 0.0


def test_low_confidence_alignment_stays_below_marker_gate() -> None:
    pool = StatePool()

    trace = update_joint_attention(
        pool,
        self_focus=FocusSignal("self", "vision::same", confidence=0.2),
        other_focus=FocusSignal("user", "vision::same", confidence=0.2),
        tick=4,
    )

    assert trace.marker is None
    assert trace.alignment < 0.5


def test_phase9_5_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "9.5"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 9.5 deliverables present" in completed.stdout
