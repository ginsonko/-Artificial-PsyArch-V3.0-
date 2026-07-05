from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(".")


def test_stage8_release_demo_artifacts_exist_and_manifest_is_coherent() -> None:
    manifest_path = ROOT / "reports" / "Phase20_7_release_demo_manifest_20260626.json"
    performance_path = ROOT / "reports" / "Phase20_7_performance_report_20260626.json"
    html_path = ROOT / "reports" / "APV3_Phase20_7_ReleaseDemo_20260626.html"
    zip_path = ROOT / "reports" / "APV3_Phase20_7_ReleaseDemo_Package_20260626.zip"

    for path in (manifest_path, performance_path, html_path, zip_path):
        assert path.exists(), path

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    performance = json.loads(performance_path.read_text(encoding="utf-8"))

    assert manifest["schema_id"] == "apv3_phase20_7_release_demo_manifest/v1"
    assert manifest["flows"]["text_learning"]["recall_reply"] == "你也好"
    assert manifest["flows"]["unclosed_idle"]["cat_recall_reply"] == "猫是一种动物"
    assert manifest["flows"]["visual_patch_reconstruction"]["visual_tick_count"] >= 2
    assert manifest["flows"]["audio_tts"]["tts_action"]["voice_preference"] == "xiaoyi"
    assert performance["schema_id"] == "apv3_phase20_7_performance_report/v1"

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
    assert "docs/UserGuide_Phase20_7_ReleaseDemo_20260626.md" in names
    assert "reports/APV3_Phase20_7_ReleaseDemo_20260626.html" in names
    assert "reports/Phase20_7_redline_report_20260626.txt" in names


def test_stage8_release_demo_verifier_passes() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/verify_phase20_7_release_demo.py"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase20.7 release demo package verified" in completed.stdout
