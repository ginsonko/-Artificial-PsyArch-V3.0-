from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.curriculum.action_social import validate_social_pattern


def test_phase13_8_social_pattern_requires_multiple_sources() -> None:
    accepted = validate_social_pattern("soft_correction", ("teacher_demo", "user_feedback"))
    rejected = validate_social_pattern("single_story", ("one_example",))

    assert accepted.accepted is True
    assert rejected.accepted is False


def test_phase13_8_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "13.8"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr

