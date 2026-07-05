from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.abstract_vocab.cross_cluster_gate import spawn_abstract_vocab_from_clusters
from runtime.cognitive.state_pool.state_pool import StateItem


def _cluster(sa_id: str, slots: tuple[str, ...]) -> StateItem:
    return StateItem(
        sa_id=sa_id,
        family="anonymous_cluster",
        label="anonymous_super_cluster",
        metadata={
            "shared_slots": slots,
            "shared_channel_signature": ("comparison", "relation"),
        },
    )


def test_cross_cluster_shared_relations_spawn_abstract_vocab() -> None:
    item = spawn_abstract_vocab_from_clusters(
        (
            _cluster("cluster::fruit", ("same", "different", "category")),
            _cluster("cluster::animal", ("same", "different", "motion")),
            _cluster("cluster::tool", ("same", "different", "use")),
        ),
        abstract_label="same_different",
    )

    assert item is not None
    assert item.family == "abstract_vocab"
    assert item.source == "cross_cluster_gate"
    assert "same" in item.metadata["shared_relations"]
    assert "different" in item.metadata["shared_relations"]


def test_two_clusters_are_not_enough_for_abstract_vocab() -> None:
    item = spawn_abstract_vocab_from_clusters(
        (
            _cluster("cluster::fruit", ("same", "different")),
            _cluster("cluster::animal", ("same", "different")),
        ),
        abstract_label="same_different",
    )

    assert item is None


def test_phase11_2_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "11.2"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 11.2 deliverables present" in completed.stdout
