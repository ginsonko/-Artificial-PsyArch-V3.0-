from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

from apv3test.runtime.course_replay import CourseReplayRuntime
from apv3test.web_chat import APV3WebChatApp, make_handler
from runtime.cognitive.curriculum.asset_governance import (
    load_asset_manifest_file,
    load_neutral_curriculum_pack_file,
    validate_asset_manifest,
)
from runtime.cognitive.curriculum.package_schema import load_curriculum_package, validate_curriculum_package


ASSET_ROOT = Path("config/curriculum/assets")
MANIFEST_PATH = ASSET_ROOT / "clean_card_manifest.yaml"
PACKAGE_PATH = Path("config/curriculum/packages/clean/clean_fruit_cards_v1.yaml")
GENERATOR = Path("scripts/curriculum/generate_clean_concept_cards.py")
SHOWCASE = Path("reports/APV3_Phase18_CleanConceptCards_Showcase_20260618.html")


def test_phase18_0_clean_card_manifest_and_package_validate_without_touching_phase17() -> None:
    clean_manifest = load_asset_manifest_file(MANIFEST_PATH)
    phase17_manifest = load_asset_manifest_file(ASSET_ROOT / "real_manifest.yaml")
    trace = validate_asset_manifest(clean_manifest, ASSET_ROOT)
    raw_package = dict(load_neutral_curriculum_pack_file(PACKAGE_PATH))
    package_trace = validate_curriculum_package(load_curriculum_package(raw_package))

    assert trace.accepted is True, trace.reasons
    assert trace.asset_count == 15
    assert trace.visual_count == 15
    assert trace.train_count == 9
    assert trace.held_out_count == 3
    assert trace.contrast_count == 3
    assert package_trace.accepted is True, package_trace.reasons
    assert len(phase17_manifest.assets) == 15


def test_phase18_0_clean_cards_are_textless_generated_cards_with_isolated_hashes() -> None:
    manifest = load_asset_manifest_file(MANIFEST_PATH)
    hashes_by_use: dict[str, set[str]] = {"curriculum_train": set(), "held_out": set(), "contrast": set()}
    source = GENERATOR.read_text(encoding="utf-8")

    assert ".text(" not in source
    assert "draw.text" not in source
    for record in manifest.assets:
        path = ASSET_ROOT / record.path
        with Image.open(path) as image:
            assert image.format == "PNG"
            assert image.size == (192, 192)
        assert path.stat().st_size > 8_000
        assert record.asset_origin == "generated_local"
        assert record.source_url.startswith("script://scripts/curriculum/generate_clean_concept_cards.py#")
        assert record.license_id == "LicenseRef-APV3-Synthetic-Generated"
        assert "clean_card" in record.semantic_tags
        hashes_by_use[record.intended_use].add(record.sha256)

    assert not (hashes_by_use["curriculum_train"] & hashes_by_use["held_out"])
    assert not (hashes_by_use["curriculum_train"] & hashes_by_use["contrast"])
    assert len(set().union(*hashes_by_use.values())) == 15


def test_phase18_0_clean_card_package_keeps_train_heldout_contrast_separated() -> None:
    raw = dict(load_neutral_curriculum_pack_file(PACKAGE_PATH))
    forbidden = {"answer", "target_class", "event_id", "private_handle", "context_tag", "style_tag"}

    assert raw["schema_id"] == "apv3_clean_card_curriculum_pack/v1"
    assert raw["package_id"] == "clean_fruit_cards_v1"
    assert len(raw["entries"]) == 3
    for entry in raw["entries"]:
        assert not (forbidden & set(entry["public_payload"]))
        assert entry["public_payload"]["teaching_intent"] == "clean_card_first_concept"
        assert len(entry["train_asset_refs"]) == 3
        assert len(entry["held_out_asset_refs"]) == 1
        assert len(entry["contrast_asset_refs"]) == 1
        assert all("::train::" in ref for ref in entry["train_asset_refs"])
        assert all("::held_out::" in ref for ref in entry["held_out_asset_refs"])
        assert all("::contrast::" in ref for ref in entry["contrast_asset_refs"])
        assert not (set(entry["train_asset_refs"]) & set(entry["held_out_asset_refs"]))


def test_phase18_0_course_replay_lists_and_runs_clean_card_demos(tmp_path: Path) -> None:
    db_path = tmp_path / "phase18_course.sqlite"
    runtime = CourseReplayRuntime(state_db_path=db_path)
    demos = runtime.list_demos()["demos"]
    clean_demo_ids = {demo["demo_id"] for demo in demos if demo.get("demo_group") == "clean_card"}
    payload = runtime.run_demo("demo_clean_card_apple")
    by_tick = {tick["tick"]: tick for tick in payload["ticks"]}

    assert clean_demo_ids == {"demo_clean_card_apple", "demo_clean_card_banana", "demo_clean_card_orange"}
    assert payload["demo"]["demo_group"] == "clean_card"
    assert payload["summary"]["manifest_ids"] == ["phase18_clean_concept_cards_v1"]
    assert payload["summary"]["asset_origins"] == ["generated_local"]
    assert payload["summary"]["tick_count"] == 6
    assert by_tick[1]["asset_refs"][0].startswith("asset::clean_card::noun_apple::train::")
    assert by_tick[3]["asset_refs"][0] == "asset::clean_card::noun_apple::held_out::0"
    assert by_tick[4]["asset_refs"][0] == "asset::clean_card::noun_apple::contrast::0"
    assert by_tick[3]["q_score"] > by_tick[4]["q_score"]
    assert payload["summary"]["final_output"] == "像是 苹果"

    with sqlite3.connect(db_path) as conn:
        saved = conn.execute("SELECT payload_json FROM course_replay_trace").fetchone()[0]
    assert json.loads(saved)["demo"]["demo_group"] == "clean_card"


def test_phase18_0_web_api_serves_clean_card_trace_and_manifest_asset(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "web.sqlite")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        demos = json.loads(urlopen(f"{base}/api/course/demos", timeout=5).read().decode("utf-8"))
        trace = _post_json(f"{base}/api/course/run", {"demo_id": "demo_clean_card_banana"})

        assert any(demo["demo_id"] == "demo_clean_card_banana" for demo in demos["demos"])
        assert trace["summary"]["manifest_ids"] == ["phase18_clean_concept_cards_v1"]
        assert trace["summary"]["final_output"] == "像是 香蕉"

        asset_id = trace["ticks"][0]["asset_refs"][0]
        asset = urlopen(Request(f"{base}/api/course/assets/{asset_id}"), timeout=5)
        raw = asset.read()
        assert raw.startswith(b"\x89PNG")
        assert asset.headers.get_content_type() == "image/png"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_phase18_0_showcase_is_readable_and_keeps_real_photos_as_later_probe() -> None:
    text = SHOWCASE.read_text(encoding="utf-8")

    assert "APV3 Phase 18：先学干净概念卡片" in text
    assert "真实照片先退到泛化探测" in text
    assert "tick 1" in text
    assert "像是 苹果" in text
    assert "像是 香蕉" in text
    assert "像是 橙子" in text
    assert "不宣称 AP 已经完成真实世界视觉识别" in text
    assert "???" not in text


def test_phase18_0_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "18.0"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr


def _post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=raw, headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urlopen(req, timeout=5).read().decode("utf-8"))
