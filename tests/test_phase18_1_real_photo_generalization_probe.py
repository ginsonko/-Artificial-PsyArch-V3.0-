from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

from apv3test.runtime.course_replay import CourseReplayRuntime
from apv3test.web_chat import APV3WebChatApp, make_handler


SHOWCASE = Path("reports/APV3_Phase18_1_RealPhotoGeneralizationProbe_Showcase_20260618.html")


def test_phase18_1_lists_three_clean_to_real_generalization_demos() -> None:
    runtime = CourseReplayRuntime()
    demos = runtime.list_demos()["demos"]
    generalization = [demo for demo in demos if demo.get("demo_group") == "real_photo_generalization"]

    assert len(generalization) == 3
    assert {demo["demo_id"] for demo in generalization} == {
        "demo_generalize_clean_to_real_apple",
        "demo_generalize_clean_to_real_banana",
        "demo_generalize_clean_to_real_orange",
    }
    assert {demo["probe_package_id"] for demo in generalization} == {"real_fruit_photos_v1"}
    assert {demo["package_id"] for demo in generalization} == {"clean_fruit_cards_v1"}


def test_phase18_1_runtime_trains_on_clean_cards_and_probes_real_photos(tmp_path: Path) -> None:
    db_path = tmp_path / "phase18_1.sqlite"
    runtime = CourseReplayRuntime(state_db_path=db_path)
    payload = runtime.run_demo("demo_generalize_clean_to_real_apple")
    ticks = {tick["tick"]: tick for tick in payload["ticks"]}

    assert payload["demo"]["demo_group"] == "real_photo_generalization"
    assert payload["summary"]["manifest_ids"] == [
        "phase17_real_visual_assets_v1",
        "phase18_clean_concept_cards_v1",
    ]
    assert "generated_local" in payload["summary"]["asset_origins"]
    assert any(origin in payload["summary"]["asset_origins"] for origin in ("cc_by", "cc0", "public_domain"))
    assert ticks[1]["asset_refs"][0].startswith("asset::clean_card::noun_apple::train::")
    assert ticks[2]["asset_refs"][0].startswith("asset::clean_card::noun_apple::train::")
    assert ticks[3]["asset_refs"][0] == "asset::real::noun_apple::held_out::0"
    assert ticks[4]["asset_refs"][0] == "asset::real::noun_apple::contrast::0"
    assert ticks[3]["q_score"] > ticks[4]["q_score"]
    assert ticks[5]["q_score"] == ticks[6]["q_score"]
    assert payload["summary"]["final_output"] == "还不能确认"
    assert payload["summary"]["visual_generalization_valid"] is False
    assert payload["summary"]["audit_status"] == "plumbing_only_label_mediated_probe"
    assert payload["summary"]["rejection_reason"] == "probe_packet_contains_curriculum_label_and_energy_bucket_confound"

    with sqlite3.connect(db_path) as conn:
        saved = conn.execute("SELECT payload_json FROM course_replay_trace").fetchone()[0]
    assert json.loads(saved)["summary"]["manifest_ids"] == payload["summary"]["manifest_ids"]


def test_phase18_1_audit_detects_label_mediated_packet_content_not_visual_generalization() -> None:
    runtime = CourseReplayRuntime()
    payload = runtime.run_demo("demo_generalize_clean_to_real_banana")
    by_tick = {tick["tick"]: tick for tick in payload["ticks"]}

    assert by_tick[2]["packet"]["content_key"] == by_tick[3]["packet"]["content_key"]
    assert "clean_card_first_concept" not in by_tick[2]["packet"]["content_key"]
    assert "real_photo_foundation" not in by_tick[3]["packet"]["content_key"]
    assert "香蕉" in by_tick[3]["packet"]["content_key"]
    assert payload["summary"]["visual_generalization_valid"] is False


def test_phase18_1_each_real_photo_probe_is_marked_not_visual_proof() -> None:
    runtime = CourseReplayRuntime()
    expected = {
        "demo_generalize_clean_to_real_apple": "noun_apple",
        "demo_generalize_clean_to_real_banana": "noun_banana",
        "demo_generalize_clean_to_real_orange": "noun_orange",
    }

    for demo_id, entry_id in expected.items():
        payload = runtime.run_demo(demo_id)
        ticks = {tick["tick"]: tick for tick in payload["ticks"]}
        assert ticks[3]["asset_refs"][0] == f"asset::real::{entry_id}::held_out::0"
        assert ticks[4]["asset_refs"][0] == f"asset::real::{entry_id}::contrast::0"
        assert ticks[3]["q_score"] > ticks[4]["q_score"]
        assert payload["summary"]["final_output"] == "还不能确认"
        assert payload["summary"]["visual_generalization_valid"] is False


def test_phase18_1_web_api_serves_generalization_trace_and_real_asset(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "web.sqlite")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        demos = json.loads(urlopen(f"{base}/api/course/demos", timeout=5).read().decode("utf-8"))
        trace = _post_json(f"{base}/api/course/run", {"demo_id": "demo_generalize_clean_to_real_orange"})

        assert any(demo["demo_id"] == "demo_generalize_clean_to_real_orange" for demo in demos["demos"])
        assert trace["summary"]["final_output"] == "还不能确认"
        assert trace["summary"]["visual_generalization_valid"] is False
        real_asset_id = trace["ticks"][2]["asset_refs"][0]
        assert real_asset_id == "asset::real::noun_orange::held_out::0"

        asset = urlopen(Request(f"{base}/api/course/assets/{real_asset_id}"), timeout=5)
        raw = asset.read()
        assert raw.startswith(b"\x89PNG")
        assert asset.headers.get_content_type() == "image/png"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_phase18_1_showcase_is_readable_and_explicit_about_boundaries() -> None:
    text = SHOWCASE.read_text(encoding="utf-8")

    assert "APV3 Phase 18.1：干净卡片到真实照片泛化探测" in text
    assert "审计纠正" in text
    assert "不是有效视觉泛化证明" in text
    assert "phase18_clean_concept_cards_v1" in text
    assert "phase17_real_visual_assets_v1" in text
    assert "还不能确认" in text
    assert "不宣称 AP 已经完成任意真实照片识别" in text
    assert "probe_packet_contains_curriculum_label_and_energy_bucket_confound" in text
    assert "???" not in text


def test_phase18_1_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "18.1"],
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
