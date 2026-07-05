from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.play.exploratory_play import propose_exploratory_play
from runtime.cognitive.state_pool.state_pool import StateItem


def _item(sa_id: str, *, pressure: float, boredom: float, attention: float = 0.0) -> StateItem:
    return StateItem(
        sa_id=sa_id,
        family="vocab",
        label=sa_id,
        cognitive_pressure=pressure,
        attention_energy=attention,
        metadata={"boredom": boredom},
    )


def test_low_pressure_high_boredom_proposes_exploratory_play() -> None:
    proposals = propose_exploratory_play((_item("vocab::unused", pressure=0.0, boredom=0.8),))

    assert proposals
    assert proposals[0].action_id == "play_action::explore_variant"
    assert proposals[0].target_sa_id == "vocab::unused"


def test_high_pressure_suppresses_play_even_when_bored() -> None:
    proposals = propose_exploratory_play((_item("goal::urgent", pressure=1.0, boredom=0.9),))

    assert proposals == ()


def test_play_proposals_rank_by_boredom_and_attention_without_external_reward() -> None:
    proposals = propose_exploratory_play(
        (
            _item("vocab::low", pressure=0.0, boredom=0.5),
            _item("vocab::high", pressure=0.0, boredom=0.7, attention=0.5),
        )
    )

    assert proposals[0].target_sa_id == "vocab::high"


def test_phase9_9_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "9.9"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 9.9 deliverables present" in completed.stdout
