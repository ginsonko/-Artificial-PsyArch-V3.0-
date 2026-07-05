from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.curriculum.content_curriculum import evaluate_radical_prototype_generalization


def test_phase13_2_radical_generalizes_by_prototype_not_string_oracle() -> None:
    trace = evaluate_radical_prototype_generalization(
        "radical::water_like",
        (0.9, 0.1, 0.2),
        (
            (0.88, 0.12, 0.22),
            (0.91, 0.08, 0.20),
            (0.84, 0.14, 0.25),
        ),
        (
            (0.1, 0.9, 0.1),
            (0.2, 0.1, 0.9),
        ),
    )

    assert trace.accepted is True
    assert trace.positive_score > trace.negative_score


def test_phase13_2_radical_rejects_close_negative_without_label_fallback() -> None:
    trace = evaluate_radical_prototype_generalization(
        "radical::ambiguous",
        (0.5, 0.5, 0.0),
        ((0.51, 0.49, 0.0),),
        ((0.52, 0.48, 0.0),),
    )

    assert trace.accepted is False


def test_phase13_2_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "13.2"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr

