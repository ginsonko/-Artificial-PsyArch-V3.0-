from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.self_model.heartbeat import ensure_self_model, heartbeat_self_model
from runtime.cognitive.state_pool.state_pool import StatePool


def test_self_model_exists_as_persistent_entity_sa() -> None:
    pool = StatePool()
    item = ensure_self_model(pool)

    assert item.family == "self_model"
    assert item.metadata["identity_id"] == "ap_self"
    assert pool.get(item.sa_id) is item


def test_low_self_energy_reactivates_through_heartbeat_without_new_marker_kind() -> None:
    pool = StatePool()
    item = ensure_self_model(pool)
    item.real_energy = 0.0

    trace = heartbeat_self_model(pool, tick=1)

    assert trace.reactivated is True
    assert trace.real_energy > 0.0
    assert item.gain_ledger.gain_by_source["residual_mass"] > 0.0


def test_phase11_5_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "11.5"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 11.5 deliverables present" in completed.stdout
