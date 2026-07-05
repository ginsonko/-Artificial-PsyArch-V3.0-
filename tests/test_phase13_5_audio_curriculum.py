from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.curriculum.content_curriculum import evaluate_audio_pattern_contrast


def test_phase13_5_audio_pattern_contrast_separates_soft_call_from_noise() -> None:
    trace = evaluate_audio_pattern_contrast(
        (0.2, 0.8, 0.4),
        ((0.22, 0.78, 0.42), (0.18, 0.82, 0.38)),
        ((0.8, 0.2, 0.2), (0.1, 0.1, 0.9)),
    )

    assert trace.accepted is True


def test_phase13_5_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "13.5"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
