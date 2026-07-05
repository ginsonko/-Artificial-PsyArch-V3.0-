from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from runtime.cognitive.curriculum.asset_governance import (
    load_asset_manifest_file,
    validate_asset_manifest,
)


ASSET_ROOT = Path("config/curriculum/assets")
MANIFEST_PATH = ASSET_ROOT / "manifest.yaml"


def test_phase14_0_manifest_schema_hash_license_and_safety_pass() -> None:
    manifest = load_asset_manifest_file(MANIFEST_PATH)
    trace = validate_asset_manifest(manifest, ASSET_ROOT)

    assert trace.accepted is True
    assert trace.asset_count == 200
    assert trace.visual_count == 175
    assert trace.audio_count == 25
    assert trace.train_count == 120
    assert trace.held_out_count == 40
    assert trace.contrast_count == 40


def test_phase14_0_manifest_rejects_hash_mismatch_and_unsupported_license() -> None:
    manifest = load_asset_manifest_file(MANIFEST_PATH)
    bad_record = replace(manifest.assets[0], sha256="0" * 64, license_id="LicenseRef-UNKNOWN")
    bad_manifest = replace(manifest, assets=(bad_record,) + manifest.assets[1:])
    trace = validate_asset_manifest(bad_manifest, ASSET_ROOT)

    assert trace.accepted is False
    assert any("sha256_mismatch" in reason for reason in trace.reasons)
    assert any("unsupported_license" in reason for reason in trace.reasons)


def test_phase14_0_synthetic_assets_have_no_external_source_or_pii_review_gap() -> None:
    manifest = load_asset_manifest_file(MANIFEST_PATH)

    assert all(record.asset_origin == "generated_local" for record in manifest.assets)
    assert all(record.source_url.startswith("script://") for record in manifest.assets)
    assert all(record.content_safety_review == "pass" for record in manifest.assets)
    assert all(record.license_id == "LicenseRef-APV3-Synthetic-Generated" for record in manifest.assets)


def test_phase14_0_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "14.0"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
