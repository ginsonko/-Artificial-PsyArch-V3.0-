from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SHOWCASE = Path("reports/APV3_Phase14_PublicReadable_Showcase_20260618.html")


def test_phase14_3_public_showcase_is_utf8_readable_and_explains_phase14() -> None:
    text = SHOWCASE.read_text(encoding="utf-8")

    assert "AP 开始有第一批干净、可审计、可复现的课程材料了" in text
    assert "题目内容" in text
    assert "AP 输出过程" in text
    assert "黄" in text
    assert "轻声呼唤" in text
    assert "???" not in text


def test_phase14_3_public_showcase_references_real_generated_assets() -> None:
    text = SHOWCASE.read_text(encoding="utf-8")
    referenced = (
        "config/curriculum/assets/visual/synthetic/color_yellow_train_0.png",
        "config/curriculum/assets/visual/synthetic/shape_triangle_train_0.png",
        "config/curriculum/assets/visual/synthetic/noun_apple_train_0.png",
        "config/curriculum/assets/audio/synthetic/audio_soft_call_train_0.wav",
    )

    for rel in referenced:
        assert rel in text
        assert Path(rel).exists()


def test_phase14_3_public_showcase_records_positive_metrics_and_boundaries() -> None:
    text = SHOWCASE.read_text(encoding="utf-8")

    assert "200" in text
    assert "175" in text
    assert "25" in text
    assert "8" in text
    assert "不宣称 3500 字全集" in text
    assert "不宣称真实外部图像/音频大库已经接入" in text


def test_phase14_3_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "14.3"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
