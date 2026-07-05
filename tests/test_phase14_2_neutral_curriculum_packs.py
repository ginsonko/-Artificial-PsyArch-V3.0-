from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from runtime.cognitive.curriculum.asset_governance import (
    load_asset_manifest_file,
    load_neutral_curriculum_pack_file,
    validate_neutral_curriculum_packs,
)


ASSET_ROOT = Path("config/curriculum/assets")
MANIFEST_PATH = ASSET_ROOT / "manifest.yaml"
PACKAGE_ROOT = Path("config/curriculum/packages/neutral")


def _packages() -> list[dict[str, object]]:
    return [dict(load_neutral_curriculum_pack_file(path)) for path in sorted(PACKAGE_ROOT.glob("*.yaml"))]


def test_phase14_2_neutral_foundation_pack_set_passes_asset_reference_gate() -> None:
    manifest = load_asset_manifest_file(MANIFEST_PATH)
    trace = validate_neutral_curriculum_packs(manifest, _packages())

    assert trace.accepted is True
    assert trace.package_count == 8
    assert trace.entry_count == 40
    assert trace.train_ref_count == 120
    assert trace.held_out_ref_count == 40
    assert trace.contrast_ref_count == 40


def test_phase14_2_pack_categories_cover_first_neutral_curriculum_surface() -> None:
    packages = _packages()
    package_ids = {str(package["package_id"]) for package in packages}

    assert {
        "neutral_colors_v1",
        "neutral_shapes_v1",
        "neutral_numbers_v1",
        "neutral_directions_v1",
        "neutral_daily_nouns_v1",
        "neutral_basic_actions_v1",
        "neutral_feedback_symbols_v1",
        "neutral_audio_patterns_v1",
    } <= package_ids


def test_phase14_2_package_payloads_do_not_include_private_or_answer_fields() -> None:
    forbidden = {"answer", "target_class", "event_id", "private_handle", "context_tag", "style_tag"}
    for package in _packages():
        for entry in package["entries"]:
            payload = entry.get("public_payload", {})
            assert not (forbidden & set(payload))


def test_phase14_2_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "14.2"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
