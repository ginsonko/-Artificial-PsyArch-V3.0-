from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


ASSET_ROOT = Path("config/curriculum/assets")
MANIFEST_PATH = ASSET_ROOT / "manifest.yaml"


def _assets() -> list[dict[str, object]]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["assets"]


def test_phase14_1_generated_png_and_wav_files_are_real_assets_not_empty_placeholders() -> None:
    assets = _assets()
    sample_png = next(asset for asset in assets if asset["media_type"] == "image/png")
    sample_wav = next(asset for asset in assets if asset["media_type"] == "audio/wav")
    png_bytes = (ASSET_ROOT / str(sample_png["path"])).read_bytes()
    wav_bytes = (ASSET_ROOT / str(sample_wav["path"])).read_bytes()

    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert wav_bytes.startswith(b"RIFF")
    assert b"WAVE" in wav_bytes[:16]
    assert len(png_bytes) > 120
    assert len(wav_bytes) > 800


def test_phase14_1_train_and_held_out_assets_do_not_share_hashes() -> None:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for asset in _assets():
        groups[str(asset["sha256"])].append(asset)

    leaking_groups = []
    for rows in groups.values():
        uses = {row["intended_use"] for row in rows}
        if "curriculum_train" in uses and "held_out" in uses:
            leaking_groups.append(rows)

    assert leaking_groups == []


def test_phase14_1_manifest_contains_expected_synthetic_modalities() -> None:
    assets = _assets()
    media_types = {asset["media_type"] for asset in assets}
    intended_uses = {asset["intended_use"] for asset in assets}

    assert media_types == {"image/png", "audio/wav"}
    assert {"curriculum_train", "held_out", "contrast"} <= intended_uses


def test_phase14_1_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "14.1"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
