from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.curriculum.content_curriculum import evaluate_vocabulary_components


def test_phase13_3_vocabulary_requires_plural_components() -> None:
    accepted = evaluate_vocabulary_components("word::gentle_reply", ("char::gentle", "use::reply"))
    rejected = evaluate_vocabulary_components("word::single_echo", ("char::only",))

    assert accepted.accepted is True
    assert rejected.accepted is False


def test_phase13_3_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "13.3"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr

