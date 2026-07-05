from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from apv3test.runtime.cooccurrence_store import CooccurrenceAssociationStore
from apv3test.runtime.expression_phrase_memory import ExpressionPhraseMemory
from apv3test.runtime.phase20_memory_packages import list_memory_view
from apv3test.runtime.phase20_open_dialogue import Phase20MultimodalSession
from apv3test.web_chat import APV3WebChatApp


APPLE = Path("config/curriculum/assets/visual/clean_cards/noun_apple_held_out_0.png")


def test_phase20_1_teaching_paradigm_is_context_bound(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_1.sqlite")

    session.turn({"text": "你好"})
    greet_teach = session.teach_latest({"teaching_reply_text": "你好。"})
    image_first = session.turn({"text": "这是什么", "image_path": str(APPLE)})
    image_teach = session.teach_latest({"teaching_reply_text": "像苹果。"})

    greet_again = session.turn({"text": "你好"})
    image_again = session.turn({"text": "这是什么", "image_path": str(APPLE)})

    assert greet_teach.teaching_trace.rewarded_teaching is True
    assert image_teach.teaching_trace.punished_previous is True
    assert image_first.metadata["context_signature"] != greet_again.metadata["context_signature"]
    assert greet_again.reply_text == "你好。"
    assert image_again.reply_text == "像苹果。"
    assert "这是什么" not in greet_again.reply_text
    assert image_again.metadata["teaching_candidate_applied"] is True


def test_phase20_1_teaching_reward_and_previous_punish_are_auditable(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_1.sqlite")
    first = session.turn({"text": "这是什么", "image_path": str(APPLE)})
    taught = session.teach_latest({"teaching_reply_text": "像苹果。"})
    state = session.chat.state

    assert first.reply_text != ""
    assert taught.teaching_trace.reward_delta > 0
    assert taught.teaching_trace.previous_reply_punish_delta > 0
    assert "phase20_teaching_paradigms" not in state
    memory = ExpressionPhraseMemory.from_state(state.get("expression_phrase_memory"))
    assoc = CooccurrenceAssociationStore.from_state(state.get("cooccurrence_associations"))
    assert memory.phrase_id_for_tokens(("像苹果。",))
    assert any(pair.key_b == memory.phrase_id_for_tokens(("像苹果。",)) for pair in assoc.pairs)
    assert state["phase20_reply_penalties"][0]["reply_text_hash"] == taught.teaching_trace.previous_reply_hash


def test_phase20_1_teaching_does_not_enter_user_query_or_store_ordinary_text(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_1.sqlite")
    session.turn({"text": "秘密问候"})
    session.teach_latest({"teaching_reply_text": "你好。"})
    repeated = session.turn({"text": "秘密问候"})
    memory_rows = list_memory_view(session.chat.state, query="秘密问候", limit=20)["memories"]
    runtime_trace = session.chat.state["minimalist_dialogue_trace"][-1]

    assert repeated.reply_text == "你好。"
    assert any("秘密问候" in row.get("display_title", "") for row in memory_rows)
    assert runtime_trace["incoming_query_total_length"] == len("秘密问候")
    assert runtime_trace["incoming_query_count"] == 1
    assert runtime_trace["incoming_query_total_length"] != len("你好。")


def test_phase20_1_styled_display_uses_natural_response_text(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_1.sqlite")
    seen = [session.turn({"text": f"看{i}", "image_path": str(APPLE)}).reply_text for i in range(12)]

    assert "嗯在" not in seen
    assert any(len(item) > 2 and ("。" in item or "," in item or "，" in item) for item in seen)


def test_phase20_1_web_teaching_api_schema(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "phase20_1_web.sqlite")
    turn = app.phase20_turn({"text": "这是什么", "image_path": str(APPLE)})
    taught = app.phase20_teach({"teaching_reply_text": "像苹果。"})
    repeated = app.phase20_turn({"text": "这是什么", "image_path": str(APPLE)})

    assert turn["turn"]["context_signature"]
    assert taught["teaching"]["trace"]["source"] == "teacher_event_cooccurrence"
    assert taught["teaching"]["source_boundary"] == "teacher_event_not_user_query"
    assert repeated["turn"]["teaching_applied"] is True
    assert repeated["turn"]["reply_text"] == "像苹果。"


def test_phase20_1_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "20.1"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 20.1 deliverables present" in completed.stdout
