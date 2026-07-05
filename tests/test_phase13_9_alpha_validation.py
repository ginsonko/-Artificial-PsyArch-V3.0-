from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.curriculum.alpha_validation import evaluate_phase13_alpha
from runtime.demo_substrate.profile import default_demo_profile


def test_phase13_9_alpha_validation_accepts_eight_curriculum_phases_and_four_scenarios() -> None:
    trace = evaluate_phase13_alpha(
        default_demo_profile(),
        curriculum_phases=("13.1", "13.2", "13.3", "13.4", "13.5", "13.6", "13.7", "13.8"),
        capability_tags=(
            "chat",
            "reward",
            "memory",
            "audit",
            "vision",
            "audio",
            "goal",
            "deliberative",
            "trust",
            "action",
            "joint_attention",
        ),
    )

    assert trace.accepted is True
    assert trace.demo_readiness.supported_count == 4


def test_phase13_9_alpha_validation_rejects_missing_curriculum_coverage() -> None:
    trace = evaluate_phase13_alpha(
        default_demo_profile(),
        curriculum_phases=("13.1", "13.2"),
        capability_tags=("chat", "audit", "vision"),
    )

    assert trace.accepted is False


def test_phase13_9_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "13.9"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
