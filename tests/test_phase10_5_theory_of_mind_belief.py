from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.state_pool.state_pool import StatePool
from runtime.cognitive.theory_of_mind.belief_model import (
    evaluate_false_belief,
    set_reality_location,
    update_other_belief,
)


def test_other_belief_stays_separate_from_reality_location() -> None:
    pool = StatePool()
    belief = update_other_belief(
        pool,
        entity_id="user_A",
        topic_sa_id="object::box",
        believed_location_sa_id="place::left",
        tick=1,
        confidence=1.0,
    )
    set_reality_location(pool, topic_sa_id="object::box", location_sa_id="place::right")

    trace = evaluate_false_belief(pool, entity_id="user_A", topic_sa_id="object::box")

    assert belief.sa_id == "belief::other::user_A::object::box"
    assert trace.is_false_belief is True
    assert trace.believed_location_sa_id == "place::left"
    assert trace.reality_location_sa_id == "place::right"
    assert trace.predicted_search_location_sa_id == "place::left"


def test_matching_belief_and_reality_predict_real_location() -> None:
    pool = StatePool()
    update_other_belief(
        pool,
        entity_id="user_A",
        topic_sa_id="object::cup",
        believed_location_sa_id="place::table",
        tick=1,
    )
    set_reality_location(pool, topic_sa_id="object::cup", location_sa_id="place::table")

    trace = evaluate_false_belief(pool, entity_id="user_A", topic_sa_id="object::cup")

    assert trace.is_false_belief is False
    assert trace.predicted_search_location_sa_id == "place::table"


def test_phase10_5_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "10.5"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 10.5 deliverables present" in completed.stdout
