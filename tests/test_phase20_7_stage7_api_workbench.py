from __future__ import annotations

from pathlib import Path

import apv3test.web_chat as web_chat


def _app_with_tmp_db(tmp_path: Path, monkeypatch) -> web_chat.APV3WebChatApp:
    monkeypatch.setattr(web_chat, "PHASE20_7_DB_PATH", tmp_path / "phase20_7_workbench.sqlite")
    return web_chat.APV3WebChatApp()


def test_stage7_phase20_7_turn_api_uses_runtime_tick_event_and_memory_view(tmp_path: Path, monkeypatch) -> None:
    app = _app_with_tmp_db(tmp_path, monkeypatch)

    learned = app.phase20_7_turn({"text": "你好啊", "teacher_feedback": "你也好", "runtime_stage": "stage6"})
    recalled = app.phase20_7_turn({"text": "你好啊", "runtime_stage": "stage6"})

    assert learned["turn"]["stage_id"] == "20.7-stage6"
    assert recalled["turn"]["reply_text"] == "你也好"
    assert recalled["turn"]["tick_trace"]
    assert all(tick["schema_id"] == "apv3_phase20_7_runtime_tick_event/v2" for tick in recalled["turn"]["tick_trace"])
    assert any(item["display_text"] == "你好啊 -> 你也好" for item in recalled["memory"])


def test_stage7_phase20_7_memory_delete_api_removes_recall_driver(tmp_path: Path, monkeypatch) -> None:
    app = _app_with_tmp_db(tmp_path, monkeypatch)
    app.phase20_7_turn({"text": "你好啊", "teacher_feedback": "你也好", "runtime_stage": "stage6"})
    memory = app.phase20_7_memory_list({"limit": 50})["items"]
    target = next(item for item in memory if item["source_event_kind"] == "experience_alignment")

    deleted = app.phase20_7_memory_delete({"memory_entry_id": target["memory_entry_id"]})
    recalled = app.phase20_7_turn({"text": "你好啊", "runtime_stage": "stage6"})

    assert deleted["tombstone_id"]
    assert recalled["turn"]["reply_text"] == "不太会,教教"


def test_stage7_xiaoyi_tts_playback_api_is_local_and_patchable(tmp_path: Path, monkeypatch) -> None:
    app = _app_with_tmp_db(tmp_path, monkeypatch)
    tts_path = Path(web_chat.PROJECT_ROOT) / "data" / "phase20_7_tts" / "unit_test.wav"
    tts_path.parent.mkdir(parents=True, exist_ok=True)
    tts_path.write_bytes(b"RIFFunit-test")

    def _stub(reply_text: str, *, out_dir: str | Path) -> dict[str, object]:
        assert reply_text == "你也好"
        return {
            "path": str(tts_path),
            "voice_id": "xiaoyi-unit",
            "voice_name": "xiaoyi",
            "local_only": True,
            "bytes": tts_path.stat().st_size,
        }

    monkeypatch.setattr(web_chat, "synthesize_xiaoyi_tts", _stub)

    result = app.phase20_7_tts_synthesize({"reply_text": "你也好"})

    assert result["ok"] is True
    assert result["local_only"] is True
    assert result["voice_name"] == "xiaoyi"
    assert "/api/phase20/media?path=" in result["url"]


def test_stage7_xiaoyi_tts_playback_api_reports_local_unavailable(tmp_path: Path, monkeypatch) -> None:
    app = _app_with_tmp_db(tmp_path, monkeypatch)

    def _missing(reply_text: str, *, out_dir: str | Path) -> dict[str, object]:
        raise RuntimeError("xiaoyi_voice_not_available_in_local_sapi")

    monkeypatch.setattr(web_chat, "synthesize_xiaoyi_tts", _missing)

    result = app.phase20_7_tts_synthesize({"reply_text": "你也好"})

    assert result["ok"] is False
    assert result["local_only"] is True
    assert result["error"] == "xiaoyi_voice_not_available_in_local_sapi"
    assert "不伪造音频" in result["message"]


def test_stage7_workbench_static_files_are_runtime_event_view_only() -> None:
    static_root = Path("apv3test/web/static")
    html = (static_root / "phase20_7_workbench.html").read_text(encoding="utf-8")
    js = (static_root / "phase20_7_workbench.js").read_text(encoding="utf-8")
    css = (static_root / "phase20_7_workbench.css").read_text(encoding="utf-8")

    assert "RuntimeTickEvent" in html
    assert "/api/phase20_7/turn" in js
    assert "/api/phase20_7/tts/synthesize" not in js
    assert "innerPicture" in html
    assert "thoughtCloud" in html
    assert "auditCharts" in html
    assert "innerAudio" in html
    assert "tickReason" in html
    assert "structureStream" in html
    assert "memoryPanel" in html
    assert "unclosedPanel" in html
    assert "autoIdle" in html
    assert "userText\").value = \"\"" in js
    assert "addMediaMessage" in js
    assert "speakWithBrowserXiaoyi" in js
    assert "speechSynthesis" in js
    assert "appendStructureStream" in js
    assert "idle_visual_focus" in js
    assert "idle_audio_focus" in js
    assert "renderInnerAudio" in js
    assert "tab-button" in css
    assert "（闲时想到）" not in js
    assert "workbench controller preview" not in js.lower()
    assert "fake" not in js.lower()
    assert "phase20_6" not in html
    assert "grid-template-columns" in css
    assert "overflow: hidden" in css
