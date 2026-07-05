from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.narrative.lag_pmi import LagPMIGraph


def test_repeated_forward_event_chain_promotes_narrative_sa() -> None:
    graph = LagPMIGraph()
    for _ in range(6):
        graph.observe_sequence(("event::wake", "event::look", "event::ask"))

    candidate = graph.narrative_candidate(("event::wake", "event::look", "event::ask"))

    assert candidate is not None
    assert candidate.family == "narrative"
    assert candidate.source == "lag_pmi"
    assert candidate.metadata["chain_sa_ids"] == ("event::wake", "event::look", "event::ask")
    assert min(candidate.metadata["edge_scores"]) > 0.0


def test_reverse_chain_is_rejected_by_directional_margin() -> None:
    graph = LagPMIGraph()
    for _ in range(6):
        graph.observe_sequence(("event::wake", "event::look", "event::ask"))

    assert graph.narrative_candidate(("event::ask", "event::look", "event::wake")) is None


def test_insufficient_pair_count_does_not_spawn_story_from_one_example() -> None:
    graph = LagPMIGraph()
    graph.observe_sequence(("event::wake", "event::look", "event::ask"))

    assert graph.narrative_candidate(("event::wake", "event::look", "event::ask")) is None


def test_phase10_1_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "10.1"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 10.1 deliverables present" in completed.stdout
