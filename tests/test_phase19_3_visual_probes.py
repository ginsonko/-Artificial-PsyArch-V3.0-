from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from runtime.cognitive.percept_vector.phase19_runtime import VisualTeachingExample, visual_loo_probe


def _clean_examples() -> tuple[VisualTeachingExample, ...]:
    root = Path("config/curriculum/assets/visual/clean_cards")
    return (
        VisualTeachingExample(root / "noun_apple_train_0.png", "apple_visible_teacher", "train", 200),
        VisualTeachingExample(root / "noun_apple_held_out_0.png", "apple_visible_teacher", "held_out", 201),
        VisualTeachingExample(root / "noun_banana_train_0.png", "banana_visible_teacher", "train", 202),
        VisualTeachingExample(root / "noun_banana_held_out_0.png", "banana_visible_teacher", "held_out", 203),
        VisualTeachingExample(root / "noun_orange_train_0.png", "orange_visible_teacher", "train", 204),
        VisualTeachingExample(root / "noun_orange_held_out_0.png", "orange_visible_teacher", "held_out", 205),
    )


def _real_examples() -> tuple[VisualTeachingExample, ...]:
    root = Path("真实图片测试资产")
    return (
        VisualTeachingExample(root / "真实苹果1.jpeg", "apple_visible_teacher", "real_probe", 210),
        VisualTeachingExample(root / "真实苹果2.jpg", "apple_visible_teacher", "real_probe", 211),
        VisualTeachingExample(root / "真实香蕉1.webp", "banana_visible_teacher", "real_probe", 212),
        VisualTeachingExample(root / "真实香蕉2.webp", "banana_visible_teacher", "real_probe", 213),
        VisualTeachingExample(root / "真实橙子1.webp", "orange_visible_teacher", "real_probe", 214),
        VisualTeachingExample(root / "真实橙子2.webp", "orange_visible_teacher", "real_probe", 215),
    )


def test_phase19_3a_clean_card_leave_one_out_probe_uses_no_filename_oracle() -> None:
    results = visual_loo_probe(_clean_examples())

    assert len(results) == 6
    assert all(result.used_filename_label is False for result in results)
    assert all(0.0 <= result.raw_confidence <= 1.0 for result in results)
    assert all(result.decision_tier in {"firm", "soft", "ambig", "no_call"} for result in results)


def test_phase19_3b_real_photo_probe_is_uncertainty_honest_and_source_clean() -> None:
    results = visual_loo_probe(_real_examples())

    assert len(results) == 6
    assert all(result.used_filename_label is False for result in results)
    assert any(result.decision_tier in {"soft", "ambig", "no_call"} for result in results)
    joined = " ".join(result.top_concept_uuid for result in results).lower()
    assert "apple" not in joined and "banana" not in joined and "orange" not in joined


def test_phase19_3a_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "19.3a"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_phase19_3b_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "19.3b"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
