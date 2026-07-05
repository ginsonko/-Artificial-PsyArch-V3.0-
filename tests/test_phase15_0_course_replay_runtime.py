from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from apv3test.runtime.course_replay import CourseReplayRuntime


def test_phase15_0_lists_five_manifest_backed_demos() -> None:
    runtime = CourseReplayRuntime()
    payload = runtime.list_demos()
    synthetic = [demo for demo in payload["demos"] if demo.get("demo_group") == "synthetic"]

    assert payload["schema_id"] == "apv3_course_replay_demo_list/v1"
    assert len(synthetic) == 5
    assert {demo["demo_id"] for demo in synthetic} == {
        "demo_color_yellow",
        "demo_shape_triangle",
        "demo_noun_apple",
        "demo_audio_soft_call",
        "demo_feedback_correct",
    }
    assert {"demo_clean_card_apple", "demo_clean_card_banana", "demo_clean_card_orange"} <= {
        demo["demo_id"] for demo in payload["demos"]
    }


def test_phase15_0_run_demo_emits_six_tick_runtime_trace_from_manifest_assets() -> None:
    runtime = CourseReplayRuntime()
    payload = runtime.run_demo("demo_color_yellow")
    ticks = payload["ticks"]
    manifest_ids = set(runtime.assets_by_id)

    assert payload["summary"]["runtime_generated"] is True
    assert payload["summary"]["tick_count"] == 6
    assert len(ticks) == 6
    assert all(asset_id in manifest_ids for tick in ticks for asset_id in tick["asset_refs"])
    assert ticks[0]["title"] == "课程材料进入"
    assert ticks[1]["packet"]["source_key"]
    assert ticks[2]["mind"]["marker"] == "PERCEIVED"
    assert ticks[2]["mind"]["source"] == "COURSE_REPLAY_ASSET"
    assert ticks[5]["ap_output"] == payload["summary"]["final_output"]
    assert ticks[5]["ap_output"].startswith("像是 ")


def test_phase15_0_held_out_probe_keeps_course_tendency_above_contrast() -> None:
    runtime = CourseReplayRuntime()
    payload = runtime.run_demo("demo_color_yellow")
    by_tick = {tick["tick"]: tick for tick in payload["ticks"]}

    assert by_tick[3]["asset_refs"][0].endswith("held_out::0")
    assert by_tick[4]["asset_refs"][0].endswith("contrast::0")
    assert by_tick[3]["q_score"] > by_tick[4]["q_score"]
    assert by_tick[5]["q_score"] == by_tick[6]["q_score"]


def test_phase15_0_persists_course_trace_only_to_explicit_tmp_db(tmp_path: Path) -> None:
    db_path = tmp_path / "course_replay.sqlite"
    runtime = CourseReplayRuntime(state_db_path=db_path)
    payload = runtime.run_demo("demo_shape_triangle")

    assert db_path.exists()
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT demo_id, payload_json FROM course_replay_trace").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "demo_shape_triangle"
    saved = json.loads(rows[0][1])
    assert saved["summary"]["final_output"] == payload["summary"]["final_output"]
    assert not (Path.cwd() / "course_replay.sqlite").exists()
