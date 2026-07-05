from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_memory_packages import list_memory_view
from apv3test.runtime.phase20_open_dialogue import Phase20MultimodalSession
from apv3test.web_chat import APV3WebChatApp


APPLE = "config/curriculum/assets/visual/clean_cards/noun_apple_held_out_0.png"


def test_phase20_5a_runtime_tick_events_are_real_not_projection(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_5a.sqlite")

    result = session.turn({"text": "你好", "idle_ticks": 2})

    events = list(result.metadata["runtime_tick_events"])
    stages = [str(item["stage"]) for item in events]
    assert len(events) >= 3
    assert set(stages).issubset({"ap_tick_loop", "idle_tick_loop"})
    assert "input_ingress" not in stages
    assert "visual_focus" not in stages
    assert "dialogue_runtime" not in stages
    assert "cooccurrence_recall" not in stages
    assert "style_assembly" not in stages
    assert "commit_reply" not in stages
    assert all(item["schema_id"] == "apv3_phase20_5a_runtime_tick_event/v1" for item in events)
    assert all(item["is_projection"] is False for item in events)
    assert all(item["action_chosen"]["source_system"] == "phase20_runtime_loop" for item in events)
    assert all("draft_action_kind" in item["draft_changes"] for item in events)
    assert any(item["draft_changes"]["draft_action_kind"] == "type_text" for item in events)
    assert any(item["draft_changes"]["draft_action_kind"] == "commit" for item in events)


def test_phase20_5a_web_payload_uses_runtime_events_for_replay(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "phase20_5a.sqlite")

    payload = app.phase20_turn({"text": "你好", "max_ticks": 8, "idle_ticks": 2})
    turn = payload["turn"]

    assert turn["workbench_runtime"]["schema_id"] == "apv3_phase20_5a_workbench_runtime/v1"
    assert turn["workbench_runtime"]["all_events_projection_free"] is True
    assert turn["workbench_runtime"]["boundary"] == "per_tick_ap_loop_snapshot_not_stage_pipeline"
    assert len(turn["workbench_tick_trace"]) >= 3
    assert all(item["is_projection"] is False for item in turn["workbench_tick_trace"])
    assert turn["workbench_tick_trace"][0]["action_chosen"]["action_id"].startswith("phase20_6::")
    assert turn["workbench_tick_trace"][0]["draft_snapshot"]["draft_action_kind"] == "type_text"
    assert turn["workbench_tick_trace"][0]["audit_metrics"]["state_pool_count"] >= 1
    assert "runtime_ms" in turn["workbench_tick_trace"][0]["audit_metrics"]
    assert turn["workbench_tick_trace"][0]["recall_candidates"]
    assert turn["workbench_tick_trace"][0]["action_competition"]["schema_id"] == "apv3_phase20_6_action_competition/v1"
    assert turn["workbench_tick_trace"][0]["draft_grid_snapshot"]["schema_id"] == "apv3_phase20_6_draftgrid_snapshot/v1"
    assert turn["workbench_tick_trace"][0]["thought_cloud_items"]


def test_phase20_5a_runtime_events_and_user_observation_memory_are_persisted(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_5a.sqlite")

    session.turn({"text": "你是谁?"})
    latest = session.chat.state["phase20_turn_trace"][-1]
    memory_rows = list_memory_view(session.chat.state, query="你是谁", limit=20)["memories"]

    assert "runtime_tick_events" in latest
    assert latest["runtime_tick_events"][0]["is_projection"] is False
    assert latest["runtime_tick_events"][0]["draft_changes"]["draft_action_kind"] in {"type_text", "commit"}
    assert latest["user_text_length"] == len("你是谁?")
    assert any("用户话语「你是谁?」" in row.get("display_title", "") for row in memory_rows)


def test_phase20_5a_observed_user_text_is_not_reply_template(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_5a.sqlite")

    first = session.turn({"text": "你是谁?"})
    second = session.turn({"text": "你是谁?"})

    assert first.metadata["teaching_candidate_applied"] is False
    assert second.metadata["teaching_candidate_applied"] is False
    assert second.reply_text != "你是谁?"


def test_phase20_5a_visual_tick_state_exposes_focus_layers_and_audit(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "phase20_5a.sqlite")

    payload = app.phase20_turn(
        {
            "text": "这是什么",
            "image_path": APPLE,
            "max_ticks": 8,
            "idle_ticks": 1,
        }
    )
    ticks = payload["turn"]["workbench_tick_trace"]
    focus_points = [tuple(item["focus_xy"]) for item in ticks if item.get("focus_xy")]
    inner_states = [item.get("inner_picture_state", {}) for item in ticks if item.get("inner_picture_state")]
    sample_rows = [
        sample
        for inner in inner_states
        for sample in (inner.get("samples") or [])
        if isinstance(sample, dict)
    ]

    assert len(set(focus_points)) >= 2
    assert any(inner.get("layers") or inner.get("samples") for inner in inner_states)
    assert any(inner.get("source") == "state_pool_visual_receptor_sketch_samples" for inner in inner_states)
    assert sample_rows
    assert any(sample.get("source") == "visual_receptor_sketch_native_pixel" for sample in sample_rows)
    assert all("image_path" not in repr(sample).lower() for sample in sample_rows)
    assert any(item["audit_metrics"]["visual_state_count"] >= 1 for item in ticks)


def test_phase20_5a_frontend_has_eight_panel_skeleton() -> None:
    html = Path("apv3test/web/static/index.html").read_text(encoding="utf-8")
    script = Path("apv3test/web/static/app.js").read_text(encoding="utf-8")

    for panel_id in (
        "panel0History",
        "panel1Chat",
        "panel2Replay",
        "panel3Charts",
        "panel456Inspect",
        "panel7Packages",
        "sessionHistoryList",
        "packagePanelMirror",
    ):
        assert panel_id in html
    assert "renderSessionHistory" in script
    assert "state_pool_energy_reconstruction_not_original_asset" in script
    assert "audit-grid" in script
    assert "thought-orb" in script
    assert "RecallCandidate" in script
    assert "ActionCompetition" in script
    assert "DraftGrid" in script
    assert "ThoughtCloud" in script
    assert "projection warning" in script


def test_phase20_5a_does_not_pretend_b_or_c_capabilities_are_done() -> None:
    web_chat = Path("apv3test/web_chat.py").read_text(encoding="utf-8")
    script = Path("apv3test/web/static/app.js").read_text(encoding="utf-8")
    runtime = Path("apv3test/runtime/phase20_open_dialogue.py").read_text(encoding="utf-8")

    forbidden = ("edge-tts", "Google TTS", "OpenAI TTS", "pytesseract", "easyocr", "paddleocr")
    combined = "\n".join((web_chat, script, runtime))
    for token in forbidden:
        assert token not in combined
    assert "stop_generating" not in runtime
