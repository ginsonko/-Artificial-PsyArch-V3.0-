from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from runtime.cognitive.curriculum.consistency_validator import validate_cross_course_consistency
from runtime.cognitive.curriculum.loader import install_curriculum_package, load_curriculum_package_file
from runtime.cognitive.curriculum.package_schema import load_curriculum_package, validate_curriculum_package
from runtime.cognitive.curriculum.progress_backup import build_progress_backup


def test_phase13_1_curriculum_package_loader_accepts_governed_seed() -> None:
    package = load_curriculum_package_file("apv3test/data/curriculum/phase13_alpha_seed.json")
    trace = validate_curriculum_package(package)
    state = install_curriculum_package({}, package)
    backup = build_progress_backup(state)

    assert trace.accepted is True
    assert trace.entry_count == 8
    assert "phase13_alpha_seed" in backup.accepted_packages
    assert "chat" in backup.capability_tags
    assert "vision" in backup.capability_tags


def test_phase13_1_loader_rejects_runtime_llm_or_private_payload_fields() -> None:
    raw = {
        "schema_id": "apv3_curriculum_package/v1",
        "package_id": "bad",
        "phase_id": "13.1",
        "governance": {
            "trust_tier": "official",
            "license_id": "local",
            "author_id": "tester",
            "source_policy": "runtime_llm",
            "review_status": "draft",
        },
        "entries": [
            {
                "entry_id": "leaky",
                "content_kind": "visual",
                "public_payload": {"answer": "cat"},
                "governance_tags": ["vision"],
            }
        ],
    }
    package = load_curriculum_package(raw)
    trace = validate_curriculum_package(package)

    assert trace.accepted is False
    assert "runtime_llm_source_forbidden" in trace.reasons
    assert "leaky:private_field_in_public_payload" in trace.reasons


def test_phase13_1_cross_course_consistency_gate_rejects_drift() -> None:
    accepted = validate_cross_course_consistency(
        "vocab::quiet",
        {"char": (1.0, 0.0, 0.0), "word": (0.9, 0.1, 0.0)},
    )
    rejected = validate_cross_course_consistency(
        "vocab::drift",
        {"char": (1.0, 0.0, 0.0), "visual": (0.0, 1.0, 0.0)},
    )

    assert accepted.accepted is True
    assert rejected.accepted is False


def test_phase13_1_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "13.1"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr

