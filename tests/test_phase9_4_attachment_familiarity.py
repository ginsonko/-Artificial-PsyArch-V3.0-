from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.social.attachment import (
    attachment_preference_score,
    observe_user_interaction,
    user_entity_sa_id,
)
from runtime.cognitive.state_pool.state_pool import StatePool


def test_repeated_user_interaction_builds_entity_user_attachment_sa() -> None:
    pool = StatePool()

    trace = observe_user_interaction(pool, entity_id="user_A", tick=1, positive_affect=1.0)
    item = pool.get(user_entity_sa_id("user_A"))

    assert item is not None
    assert item.family == "entity_user"
    assert item.metadata["entity_kind"] == "user"
    assert trace.familiarity > 0.0
    assert trace.oxy_tone > 0.0
    assert item.gain_ledger.gain_by_source["user_directed"] > 0.0


def test_familiar_user_scores_above_new_user_without_identity_route() -> None:
    pool = StatePool()
    for tick in range(1, 8):
        observe_user_interaction(pool, entity_id="user_A", tick=tick, positive_affect=1.0)
    observe_user_interaction(pool, entity_id="user_B", tick=8, positive_affect=1.0)

    old_user = pool.get(user_entity_sa_id("user_A"))
    new_user = pool.get(user_entity_sa_id("user_B"))

    assert attachment_preference_score(old_user) > attachment_preference_score(new_user)
    assert old_user.real_energy > new_user.real_energy


def test_positive_affect_raises_oxy_tone_more_than_neutral_contact() -> None:
    pool = StatePool()
    warm = observe_user_interaction(pool, entity_id="warm", tick=1, positive_affect=1.0)
    neutral = observe_user_interaction(pool, entity_id="neutral", tick=2, positive_affect=0.0)

    assert warm.oxy_tone > neutral.oxy_tone


def test_phase9_4_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "9.4"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 9.4 deliverables present" in completed.stdout
