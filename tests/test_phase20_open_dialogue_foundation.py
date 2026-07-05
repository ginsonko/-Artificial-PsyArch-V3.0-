from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

from apv3test.runtime.phase20_open_dialogue import (
    Phase20MultimodalSession,
    StyledCorpusIndex,
    ap_perceive_and_reply,
)
from apv3test.runtime.phase20_memory_packages import list_memory_view
from apv3test.web_chat import APV3WebChatApp


IMAGE = Path("config/curriculum/assets/visual/clean_cards/noun_apple_held_out_0.png")


def test_phase20_text_and_image_keep_source_boundaries(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20.sqlite")
    result = session.turn({"text": "这是什么", "image_path": str(IMAGE)})
    state = session.chat.state
    runtime_trace = state["minimalist_dialogue_trace"][-1]
    phase20_trace = state["phase20_turn_trace"][-1]

    assert result.object_files
    assert runtime_trace["incoming_query_total_length"] == len("这是什么")
    assert result.object_files[0].top_visible_label not in repr(runtime_trace)
    assert phase20_trace["source_boundary"] == "user_text_not_augmented_by_visual_label"


def test_phase20_privacy_persists_hash_not_user_text_or_image_path(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20.sqlite")
    result = session.turn({"text": "秘密测试句", "image_path": str(IMAGE)})
    trace = session.chat.state["phase20_turn_trace"][-1]
    memory_rows = list_memory_view(session.chat.state, query="秘密测试句", limit=20)["memories"]

    assert trace["user_text_hash"] == result.user_text_hash
    assert trace["user_text_length"] == len("秘密测试句")
    assert "秘密测试句" not in repr(trace)
    assert IMAGE.name not in repr(trace)
    assert trace["image_sha16"] == result.image_sha16
    assert trace["raw_image_persisted"] is False
    assert any("用户话语「秘密测试句」" in row.get("display_title", "") for row in memory_rows)


def test_phase20_styled_response_is_loaded_from_yaml(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20.sqlite")
    result = session.turn({"text": "你好"})
    styled = result.styled_response

    assert styled is not None
    assert styled.source_path.endswith(".yaml")
    assert "config/curriculum/packages/styled" in styled.source_path
    assert styled.entry_id


def test_phase20_feedback_targets_only_previous_turn_and_emits_credit(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20.sqlite")
    first = session.turn({"text": "", "image_path": str(IMAGE)})
    second = session.turn(
        {
            "text": "",
            "feedback_kind": "explicit_label",
            "feedback_target_object_index": 0,
            "feedback_explicit_label": "苹果",
        }
    )

    assert first.object_files
    assert second.feedback_trace is not None
    assert second.feedback_trace.target_object_index == 0
    assert second.feedback_trace.correction_total_outcome < 0
    source = inspect.getsource(Phase20MultimodalSession._process_feedback)
    assert ".weights" not in source
    assert "part_weights" not in source


def test_phase20_agent_tool_schema_and_web_api(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "phase20_web.sqlite")
    payload = app.phase20_agent({"text": "看看", "image_path": str(IMAGE)})
    direct = ap_perceive_and_reply("看看", IMAGE)

    assert payload["reply"]
    assert isinstance(payload["object_files"], list)
    assert "decision_tier" in payload
    assert direct.trace["label_returned_by_zvec"] is False


def test_phase20_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "20.0"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 20.0 deliverables present" in completed.stdout
