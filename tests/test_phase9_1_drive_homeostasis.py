from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.drive.homeostatic_drive import (
    DriveSatisfaction,
    DriveTickInput,
    drive_sa_id,
    step_drive_homeostasis,
)
from runtime.cognitive.state_pool.state_pool import StatePool


def test_drive_sas_are_first_class_entity_items_with_ledger_pressure() -> None:
    pool = StatePool()

    trace = step_drive_homeostasis(
        pool,
        DriveTickInput(
            tick=1,
            body_deficit=0.9,
            novelty_gap=0.4,
            unexplored_mass=0.3,
            social_absence_ticks=30,
            unfinished_pressure=0.8,
        ),
    )

    assert set(trace.pressure_by_drive) == {
        "hunger",
        "curiosity",
        "exploration",
        "social",
        "completion",
    }
    hunger = pool.get(drive_sa_id("hunger"))
    assert hunger is not None
    assert hunger.family == "entity"
    assert hunger.sa_id == "EntitySA::drive::hunger"
    assert hunger.channel_signature == ("drive", "hunger")
    assert hunger.metadata["entity_kind"] == "drive"
    assert hunger.gain_ledger.gain_by_source["drive_pressure"] > 0.0
    assert any(row["sa_id"] == hunger.sa_id for row in pool.snapshot_top())


def test_idle_without_external_input_can_raise_spontaneous_drive_proposals() -> None:
    pool = StatePool()

    trace = step_drive_homeostasis(pool, DriveTickInput(tick=1, idle_ticks=12))

    proposed_kinds = {proposal.drive_kind for proposal in trace.proposals}
    assert {"curiosity", "exploration"} <= proposed_kinds
    assert all(proposal.action_id == "drive_action::satisfy_drive" for proposal in trace.proposals)
    assert pool.get(drive_sa_id("curiosity")).gain_ledger.endogenous_share() > 0.0


def test_satisfaction_reduces_matching_drive_without_erasing_other_drives() -> None:
    pool = StatePool()
    first = step_drive_homeostasis(
        pool,
        DriveTickInput(tick=1, body_deficit=1.0, idle_ticks=12),
    )
    hunger_before = first.pressure_by_drive["hunger"]
    curiosity_before = first.pressure_by_drive["curiosity"]

    second = step_drive_homeostasis(
        pool,
        DriveTickInput(
            tick=2,
            idle_ticks=12,
            satisfaction_events=(DriveSatisfaction("hunger", 1.0),),
        ),
    )

    assert second.pressure_by_drive["hunger"] < hunger_before
    assert second.pressure_by_drive["curiosity"] > curiosity_before
    assert pool.get(drive_sa_id("hunger")).metadata["last_satisfaction"] > 0.0
    assert pool.get(drive_sa_id("curiosity")).metadata["last_satisfaction"] == 0.0


def test_completion_drive_uses_unfinished_pressure_not_text_keywords() -> None:
    pool = StatePool()

    trace = step_drive_homeostasis(
        pool,
        DriveTickInput(tick=1, unfinished_pressure=0.7),
    )

    assert trace.pressure_by_drive["completion"] > trace.pressure_by_drive["social"]
    assert trace.proposals[0].drive_kind == "completion"


def test_phase9_1_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "9.1"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 9.1 deliverables present" in completed.stdout
