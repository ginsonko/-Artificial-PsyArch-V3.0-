from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.hierarchy.anonymous_cluster import VocabProfile, spawn_anonymous_super_cluster


def test_shared_slot_and_channel_preferences_spawn_anonymous_super_cluster() -> None:
    profiles = (
        VocabProfile("vocab::apple", ("round", "edible", "object"), ("vision", "object")),
        VocabProfile("vocab::pear", ("round", "edible", "object"), ("vision", "object")),
        VocabProfile("vocab::orange", ("round", "edible", "object"), ("vision", "object")),
    )

    cluster = spawn_anonymous_super_cluster(profiles)

    assert cluster is not None
    assert cluster.family == "anonymous_cluster"
    assert cluster.metadata["shared_slots"] == ("edible", "object", "round")
    assert cluster.metadata["shared_channel_signature"] == ("object", "vision")
    assert set(cluster.metadata["member_sa_ids"]) == {"vocab::apple", "vocab::pear", "vocab::orange"}


def test_two_members_are_below_super_cluster_gate() -> None:
    profiles = (
        VocabProfile("vocab::apple", ("round", "edible"), ("vision",)),
        VocabProfile("vocab::pear", ("round", "edible"), ("vision",)),
    )

    assert spawn_anonymous_super_cluster(profiles) is None


def test_low_similarity_profiles_do_not_merge_into_fake_super_cluster() -> None:
    profiles = (
        VocabProfile("vocab::apple", ("round", "edible"), ("vision",)),
        VocabProfile("sound::bell", ("ring", "loud"), ("audio",)),
        VocabProfile("action::run", ("fast", "body"), ("motor",)),
    )

    assert spawn_anonymous_super_cluster(profiles) is None


def test_phase10_2_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "10.2"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 10.2 deliverables present" in completed.stdout
