from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.attention.safety_gate import convex_attention_score
from runtime.cognitive.endogenous.step import (
    compute_sleep_dilation_factor,
    habituate_item,
    step_endogenous_drive,
    update_prediction_pi,
)
from runtime.cognitive.state_pool.state_pool import StateItem


def _item(sa_id: str) -> StateItem:
    return StateItem(
        sa_id=sa_id,
        family="percept",
        label=sa_id,
        real_energy=0.9,
        virtual_energy=0.4,
        attention_energy=0.3,
        cognitive_pressure=0.5,
        fatigue=0.1,
    )


def test_endogenous_drive_injects_three_ledger_sources_and_attention() -> None:
    item = _item("sa::unfinished")
    before = item.attention_energy

    trace = step_endogenous_drive((item,), tick=20, idle_score=0.8)

    assert item.attention_energy > before
    assert trace.injected_by_sa[item.sa_id]["unfinished_pressure"] > 0.0
    assert item.gain_ledger.gain_by_source["unfinished_pressure"] > 0.0
    assert item.gain_ledger.gain_by_source["expectation_pressure"] > 0.0
    assert item.gain_ledger.gain_by_source["residual_mass"] > 0.0


def test_pi_converges_when_occurring_and_decays_when_absent_without_zeroing() -> None:
    item = _item("sa::pi")
    values = [
        update_prediction_pi(item, observed_next_r=1.0, currently_occurring=True)
        for _ in range(8)
    ]
    absent = update_prediction_pi(item, currently_occurring=False)

    assert values[-1] > values[0]
    assert absent > 0.0
    assert absent < values[-1]


def test_habituation_and_sleep_dilation_are_continuous_not_state_machine() -> None:
    item = _item("sa::fan")
    before_score = convex_attention_score(item).score
    fatigue = habituate_item(item)
    after_score = convex_attention_score(item).score
    sleepy = _item("sa::sleepy")
    sleepy.fatigue = 0.95

    assert fatigue > 0.1
    assert after_score < before_score
    assert compute_sleep_dilation_factor((sleepy,)) > compute_sleep_dilation_factor((item,))


def test_external_surprise_safety_gate_overrides_endogenous_mix() -> None:
    item = _item("sa::surprise")
    item.gain_ledger.inject("imagination", 1.0)
    item.gain_ledger.inject("external", 4.0)
    item.cognitive_pressure = 0.9

    trace = convex_attention_score(item)

    assert trace.safety_gate_triggered is True
    assert trace.score == trace.external_score


def test_phase8_10_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "8.10"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 8.10 deliverables present" in completed.stdout
