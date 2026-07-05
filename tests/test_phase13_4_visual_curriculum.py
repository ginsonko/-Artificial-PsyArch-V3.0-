from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.curriculum.content_curriculum import evaluate_visual_contrast


def test_phase13_4_visual_contrast_promotes_target_pair_over_distractors() -> None:
    target = ("color::yellow", "shape::apple")
    trace = evaluate_visual_contrast(
        target,
        {
            target: 0.82,
            ("color::yellow", "shape::banana"): 0.38,
            ("color::red", "shape::apple"): 0.41,
        },
        (("color::yellow", "shape::banana"), ("color::red", "shape::apple")),
    )

    assert trace.accepted is True
    assert trace.margin > 0.2


def test_phase13_4_visual_contrast_rejects_weak_ablation_margin() -> None:
    trace = evaluate_visual_contrast(
        ("color::yellow", "shape::apple"),
        {
            ("color::yellow", "shape::apple"): 0.52,
            ("color::yellow", "shape::banana"): 0.48,
        },
        (("color::yellow", "shape::banana"),),
    )

    assert trace.accepted is False


def test_phase13_4_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "13.4"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr

