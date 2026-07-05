from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

from runtime.cognitive.curriculum.asset_governance import (
    load_asset_manifest_file,
    load_neutral_curriculum_pack_file,
    validate_asset_manifest,
)
from runtime.cognitive.curriculum.package_schema import load_curriculum_package, validate_curriculum_package


ASSET_ROOT = Path("config/curriculum/assets")
MANIFEST_PATH = ASSET_ROOT / "real_manifest.yaml"
PACKAGE_PATH = Path("config/curriculum/packages/real/real_fruit_photos_v1.yaml")
SOURCE_SIDECAR = ASSET_ROOT / "visual/real/_sources.json"
SHOWCASE = Path("reports/APV3_Phase17_RealVisualAssets_Showcase_20260618.html")


def test_phase17_0_real_manifest_validates_and_keeps_phase14_manifest_unchanged() -> None:
    real_manifest = load_asset_manifest_file(MANIFEST_PATH)
    trace = validate_asset_manifest(real_manifest, ASSET_ROOT)
    phase14_manifest = load_asset_manifest_file(ASSET_ROOT / "manifest.yaml")

    assert trace.accepted is True, trace.reasons
    assert trace.asset_count == 15
    assert trace.visual_count == 15
    assert trace.audio_count == 0
    assert trace.train_count == 9
    assert trace.held_out_count == 3
    assert trace.contrast_count == 3
    assert len(phase14_manifest.assets) == 200


def test_phase17_0_real_assets_are_allowlisted_commons_not_generated_placeholders() -> None:
    manifest = load_asset_manifest_file(MANIFEST_PATH)
    allowed_licenses = {"CC0-1.0", "CC-BY-2.0", "CC-BY-3.0", "CC-BY-4.0", "PDM-1.0"}

    assert {record.asset_origin for record in manifest.assets} <= {"cc0", "cc_by", "public_domain"}
    assert {record.license_id for record in manifest.assets} <= allowed_licenses
    assert all(record.source_url.startswith("https://commons.wikimedia.org/wiki/File:") for record in manifest.assets)
    assert all(not record.source_url.startswith("script://") for record in manifest.assets)
    assert all(record.content_safety_review == "pass" for record in manifest.assets)
    assert all("real_photo" in record.semantic_tags for record in manifest.assets)


def test_phase17_0_real_png_assets_are_decodable_and_not_tiny_schematics() -> None:
    manifest = load_asset_manifest_file(MANIFEST_PATH)

    for record in manifest.assets:
        path = ASSET_ROOT / record.path
        with Image.open(path) as image:
            assert image.format == "PNG"
            width, height = image.size
        assert width >= 100
        assert height >= 100
        assert path.stat().st_size > 20_000


def test_phase17_0_real_package_has_train_heldout_contrast_refs_without_private_fields() -> None:
    manifest = load_asset_manifest_file(MANIFEST_PATH)
    asset_by_id = {record.asset_id: record for record in manifest.assets}
    raw = dict(load_neutral_curriculum_pack_file(PACKAGE_PATH))
    package = load_curriculum_package(raw)
    trace = validate_curriculum_package(package)
    forbidden = {"answer", "target_class", "event_id", "private_handle", "context_tag", "style_tag"}

    assert trace.accepted is True, trace.reasons
    assert package.package_id == "real_fruit_photos_v1"
    assert len(package.entries) == 3
    for entry in raw["entries"]:
        payload = entry["public_payload"]
        assert not (forbidden & set(payload))
        assert len(entry["train_asset_refs"]) == 3
        assert len(entry["held_out_asset_refs"]) == 1
        assert len(entry["contrast_asset_refs"]) == 1
        assert not (set(entry["train_asset_refs"]) & set(entry["held_out_asset_refs"]))
        for ref in entry["train_asset_refs"]:
            assert asset_by_id[ref].intended_use == "curriculum_train"
        for ref in entry["held_out_asset_refs"]:
            assert asset_by_id[ref].intended_use == "held_out"
        for ref in entry["contrast_asset_refs"]:
            assert asset_by_id[ref].intended_use == "contrast"


def test_phase17_0_source_sidecar_is_auditable_and_filters_non_photo_contexts() -> None:
    sidecar = json.loads(SOURCE_SIDECAR.read_text(encoding="utf-8"))
    bad_title_tokens = ("vendor", "cards", "still life", "painting", "drawing", "illustration", "moth", "skies")

    assert sidecar["schema_id"] == "apv3_real_asset_sources/v1"
    assert len(sidecar["sources"]) == 15
    for source in sidecar["sources"]:
        text = f"{source['commons_title']} {source['attribution']}".lower()
        assert source["description_url"].startswith("https://commons.wikimedia.org/wiki/File:")
        assert source["download_url"].startswith("https://upload.wikimedia.org/")
        assert source["license_id"] in {"CC0-1.0", "CC-BY-2.0", "CC-BY-3.0", "CC-BY-4.0", "PDM-1.0"}
        assert not any(token in text for token in bad_title_tokens)


def test_phase17_0_downloader_summary_is_offline_and_matches_manifest_counts() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "scripts.curriculum.download_real_visual_assets", "--summary-only"],
        cwd=".",
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    summary = json.loads(completed.stdout)

    assert summary == {"assets": 15, "audio": 0, "contrast": 3, "held_out": 3, "train": 9, "visual": 15}


def test_phase17_0_public_showcase_is_readable_and_references_real_assets() -> None:
    text = SHOWCASE.read_text(encoding="utf-8")

    assert "APV3 Phase 17：第一批真实照片资产" in text
    assert "15 张真实照片" in text
    assert "不收 CC-BY-SA" in text
    assert "不宣称 AP 已经完整学会视觉识别" in text
    for rel in (
        "config/curriculum/assets/visual/real/noun_apple_train_0.png",
        "config/curriculum/assets/visual/real/noun_banana_train_0.png",
        "config/curriculum/assets/visual/real/noun_orange_train_0.png",
    ):
        assert rel in text
        assert Path(rel).exists()
    assert "???" not in text


def test_phase17_0_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "17.0"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
