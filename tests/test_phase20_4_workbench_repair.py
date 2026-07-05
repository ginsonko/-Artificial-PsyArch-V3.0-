from __future__ import annotations

import base64
from pathlib import Path
import subprocess
import sys

from apv3test.runtime.phase20_memory_packages import list_memory_view
from apv3test.runtime.phase20_open_dialogue import Phase20MultimodalSession
from apv3test.web_chat import APV3WebChatApp


APPLE = Path("config/curriculum/assets/visual/clean_cards/noun_apple_held_out_0.png")


def test_phase20_4_api_echoes_live_text_and_observes_it_as_local_memory(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "phase20_4.sqlite")

    payload = app.phase20_turn({"text": "你是谁?", "max_ticks": 9, "idle_ticks": 2})
    memory_rows = list_memory_view(app.phase20_session.chat.state, query="你是谁", limit=20)["memories"]

    assert payload["turn"]["live_user_text"] == "你是谁?"
    assert payload["turn"]["live_user_text_persisted"] is False
    assert payload["turn"]["workbench_runtime"]["max_ticks_if_no_commit"] == 9
    assert payload["turn"]["workbench_tick_trace"]
    assert payload["turn"]["workbench_runtime"]["boundary"] == "per_tick_ap_loop_snapshot_not_stage_pipeline"
    assert all("draft_snapshot" in item for item in payload["turn"]["workbench_tick_trace"])
    assert any("用户话语「你是谁?」" in row.get("display_title", "") for row in memory_rows)


def test_phase20_4_main_workbench_teaching_does_not_contaminate_unrelated_text(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_4.sqlite")

    session.turn({"text": "你好"})
    session.teach_latest({"teaching_reply_text": "你好。"})
    unrelated = session.turn({"text": "你是谁?"})
    greeting = session.turn({"text": "你好"})

    assert unrelated.metadata["teaching_candidate_applied"] is False
    assert unrelated.reply_text != "你好。"
    assert greeting.metadata["teaching_candidate_applied"] is True
    assert greeting.reply_text == "你好。"


def test_phase20_4_memory_view_resolves_readable_teacher_and_style_text(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_4.sqlite")
    session.turn({"text": "这是什么", "image_path": str(APPLE)})
    session.teach_latest({"teaching_reply_text": "像苹果。"})

    teacher_rows = list_memory_view(session.chat.state, query="像苹果", limit=20)["memories"]
    style_rows = list_memory_view(session.chat.state, query="风格", limit=5)["memories"]

    assert any("像苹果。" in row.get("display_title", "") for row in teacher_rows)
    assert any(row.get("kind") in {"expression_phrase", "cooccurrence_pair", "paradigm_pair"} for row in teacher_rows)
    assert style_rows
    assert all("style_paradigm::" not in row.get("display_title", "") for row in style_rows)


def test_phase20_4_media_upload_is_project_local(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "phase20_4.sqlite")
    raw = b"RIFF\x24\x00\x00\x00WAVEfmt "
    data_url = "data:audio/wav;base64," + base64.b64encode(raw).decode("ascii")

    uploaded = app.phase20_media_upload({"name": "tone.wav", "data_url": data_url})

    path = Path(uploaded["path"])
    assert path.exists()
    assert "phase20_workbench_media" in path.as_posix()
    assert uploaded["media_type"] == "audio/wav"
    assert uploaded["raw_user_text_persisted"] is False


def test_phase20_4_static_workbench_no_longer_uses_legacy_message_route() -> None:
    script = Path("apv3test/web/static/app.js").read_text(encoding="utf-8")
    html = Path("apv3test/web/static/index.html").read_text(encoding="utf-8")

    assert 'api("/api/message"' not in script
    assert "teachingReplyInput" in html
    assert "phase20SendBtn" in html
    assert "原文未保存" not in script
    assert "teaching trace" not in script


def test_phase20_4_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "20.4"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 20.4 deliverables present" in completed.stdout
