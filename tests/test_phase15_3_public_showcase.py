from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SHOWCASE = Path("reports/APV3_Phase15_WebCourseReplay_Showcase_20260618.html")


def test_phase15_3_public_showcase_is_utf8_readable_and_explains_course_replay() -> None:
    text = SHOWCASE.read_text(encoding="utf-8")

    assert "APV3 Phase 15：让人看见 AP 是怎么学的" in text
    assert "题目内容" in text
    assert "AP 内部过程" in text
    assert "SDPL LearningPacket" in text
    assert "held-out 与 contrast 对照" in text
    assert "???" not in text


def test_phase15_3_public_showcase_contains_five_real_demo_outputs() -> None:
    text = SHOWCASE.read_text(encoding="utf-8")

    for output in ("像是 黄", "像是 三角", "像是 苹果", "像是 轻声呼唤", "像是 对"):
        assert output in text
    assert text.count("Q 倾向") >= 5
    assert text.count("<tr><td>") >= 30


def test_phase15_3_public_showcase_references_existing_phase14_assets() -> None:
    text = SHOWCASE.read_text(encoding="utf-8")
    referenced = (
        "config/curriculum/assets/visual/synthetic/color_yellow_train_0.png",
        "config/curriculum/assets/visual/synthetic/shape_triangle_held_out_0.png",
        "config/curriculum/assets/visual/synthetic/noun_apple_train_0.png",
        "config/curriculum/assets/audio/synthetic/audio_soft_call_train_0.wav",
        "config/curriculum/assets/visual/synthetic/feedback_correct_held_out_0.png",
    )

    for rel in referenced:
        assert rel in text
        assert Path(rel).exists()


def test_phase15_3_public_showcase_records_metrics_and_boundaries() -> None:
    text = SHOWCASE.read_text(encoding="utf-8")

    assert "5 个课程 demo" in text
    assert "每个 6 tick 回放" in text
    assert "10/10" in text
    assert "不宣称 AP 已经掌握全部基础词汇" in text
    assert "真实外部素材库" in text


def test_phase15_3_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "15.3"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
