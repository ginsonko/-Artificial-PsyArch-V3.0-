from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.social.attachment import observe_user_interaction, user_entity_sa_id
from runtime.cognitive.state_pool.state_pool import StatePool
from runtime.cognitive.trust.trust_prior import evaluate_trust_promotion, trust_score, update_teaching_accuracy


def _trusted_pool() -> StatePool:
    pool = StatePool()
    for tick in range(1, 8):
        observe_user_interaction(pool, entity_id="teacher_A", tick=tick, positive_affect=1.0)
    entity = pool.get(user_entity_sa_id("teacher_A"))
    assert entity is not None
    for _ in range(4):
        update_teaching_accuracy(entity, correct=True)
    return pool


def test_repeated_positive_teaching_and_attachment_promote_trust_marker() -> None:
    pool = _trusted_pool()
    entity_id = user_entity_sa_id("teacher_A")

    trace = evaluate_trust_promotion(
        pool,
        entity_sa_id=entity_id,
        evidence_target_sa_id="vocab::new_fact",
        tick=9,
        delta_p=0.2,
    )

    assert trace.promoted_marker is not None
    assert trace.promoted_marker.kind == "TRUST_PROMOTED"
    assert trace.promoted_marker.metadata["entity_sa_id"] == entity_id
    assert pool.get(trace.promoted_marker.sa_id) is not None


def test_negative_delta_p_downgrades_trust_without_promoting_evidence() -> None:
    pool = _trusted_pool()
    entity = pool.get(user_entity_sa_id("teacher_A"))
    assert entity is not None
    before = trust_score(entity)

    trace = evaluate_trust_promotion(
        pool,
        entity_sa_id=entity.sa_id,
        evidence_target_sa_id="vocab::bad_fact",
        tick=10,
        delta_p=-0.2,
    )

    assert trace.downgraded is True
    assert trace.promoted_marker is None
    assert trust_score(entity) < before
    assert entity.metadata["trust_downgraded"] is True


def test_phase10_7_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "10.7"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 10.7 deliverables present" in completed.stdout
