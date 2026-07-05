from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.social.empathy import resonate_from_observed_marker
from runtime.cognitive.state_pool.state_pool import StatePool


def test_observed_pain_spawns_weak_empathy_resonance_not_state_copy() -> None:
    pool = StatePool()
    observed = MarkerEvent(tick=1, kind="PAIN", target_sa_id="user::hand", real_energy=1.0)

    trace = resonate_from_observed_marker(
        pool,
        observed_marker=observed,
        observer_entity_sa_id="EntitySA::user::user_A",
        tick=2,
    )

    assert trace.marker is not None
    assert trace.marker.kind == "EMPATHY_RESONANCE"
    assert trace.marker.target_sa_id == "EntitySA::user::user_A"
    assert 0.0 < trace.resonance_energy < observed.real_energy
    assert pool.get(trace.marker.sa_id) is not None


def test_observed_correction_can_resonate_but_unknown_marker_does_not() -> None:
    pool = StatePool()
    correction = MarkerEvent(tick=1, kind="CORRECTION", target_sa_id="user::plan", real_energy=0.8)
    novelty = MarkerEvent(tick=1, kind="NOVELTY", target_sa_id="scene", real_energy=0.8)

    yes = resonate_from_observed_marker(pool, observed_marker=correction, observer_entity_sa_id="self", tick=2)
    no = resonate_from_observed_marker(pool, observed_marker=novelty, observer_entity_sa_id="self", tick=3)

    assert yes.marker is not None
    assert no.marker is None


def test_phase9_6_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "9.6"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 9.6 deliverables present" in completed.stdout
