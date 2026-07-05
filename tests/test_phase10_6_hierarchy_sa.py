from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.hierarchy.anonymous_cluster import VocabProfile, spawn_anonymous_super_cluster
from runtime.cognitive.hierarchy.hierarchy_sa import bind_name_to_cluster, part_of_relation
from runtime.cognitive.state_pool.state_pool import StateItem


def _cluster() -> StateItem:
    cluster = spawn_anonymous_super_cluster(
        (
            VocabProfile("vocab::apple", ("round", "edible", "object"), ("vision", "object")),
            VocabProfile("vocab::pear", ("round", "edible", "object"), ("vision", "object")),
            VocabProfile("vocab::orange", ("round", "edible", "object"), ("vision", "object")),
        )
    )
    assert cluster is not None
    return cluster


def test_name_binding_turns_anonymous_cluster_into_named_hierarchy_sa() -> None:
    named = bind_name_to_cluster(_cluster(), name_sa_id="word::fruit")

    assert named is not None
    assert named.family == "hierarchy"
    assert named.source == "name_binding"
    assert named.metadata["name_sa_id"] == "word::fruit"
    assert named.metadata["relation"] == "is_a_cluster"
    assert "vocab::apple" in named.metadata["member_sa_ids"]


def test_non_cluster_cannot_be_named_as_hierarchy_shortcut() -> None:
    item = StateItem(sa_id="vocab::apple", family="vocab", label="apple")

    assert bind_name_to_cluster(item, name_sa_id="word::fruit") is None


def test_part_of_relation_records_part_whole_metadata() -> None:
    relation = part_of_relation("part::wheel", "whole::car", confidence=1.0)

    assert relation.family == "hierarchy"
    assert relation.label == "part_of"
    assert relation.metadata["relation"] == "part_of"
    assert relation.metadata["part_sa_id"] == "part::wheel"
    assert relation.metadata["whole_sa_id"] == "whole::car"


def test_phase10_6_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "10.6"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 10.6 deliverables present" in completed.stdout
