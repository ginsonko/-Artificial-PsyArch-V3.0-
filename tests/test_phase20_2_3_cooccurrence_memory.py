from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

from apv3test.runtime.cooccurrence_store import CooccurrenceAssociationStore
from apv3test.runtime.expression_phrase_memory import ExpressionPhraseMemory
from apv3test.runtime.phase20_memory_packages import (
    delete_memories,
    export_memory_package,
    import_memory_package,
    list_memory_view,
    uninstall_memory_package,
)
from apv3test.runtime.phase20_open_dialogue import Phase20MultimodalSession


APPLE = Path("config/curriculum/assets/visual/clean_cards/noun_apple_held_out_0.png")


def test_phase20_2_style_corpus_is_imported_into_ap_memory(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_2.sqlite")
    state = session.chat.state
    memory = ExpressionPhraseMemory.from_state(state.get("expression_phrase_memory"))
    assoc = CooccurrenceAssociationStore.from_state(state.get("cooccurrence_associations"))

    assert state["phase20_style_corpus_import"]["imported_count"] >= 1000
    assert len([record for record in memory.records if record.phrase_kind == "styled_curriculum_example"]) >= 1000
    assert any(pair.key_a.startswith("style_paradigm::") for pair in assoc.pairs)


def test_phase20_2_teaching_uses_cooccurrence_not_independent_table(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_2.sqlite")
    session.turn({"text": "这是什么", "image_path": str(APPLE)})
    taught = session.teach_latest({"teaching_reply_text": "像苹果。"})
    repeated = session.turn({"text": "这是什么", "image_path": str(APPLE)})
    state = session.chat.state
    memory = ExpressionPhraseMemory.from_state(state.get("expression_phrase_memory"))
    assoc = CooccurrenceAssociationStore.from_state(state.get("cooccurrence_associations"))
    phrase_id = memory.phrase_id_for_tokens(("像苹果。",))

    assert repeated.reply_text == "像苹果。"
    assert taught.teaching_trace.source == "teacher_event_cooccurrence"
    assert taught.teaching_trace.visual_sa_ids
    assert phrase_id
    assert any(pair.key_b == phrase_id and pair.key_a.startswith("visual_") for pair in assoc.pairs)
    assert "phase20_teaching_paradigms" not in state
    source = inspect.getsource(Phase20MultimodalSession)
    assert "phase20_teaching_paradigms" not in source


def test_phase20_2_demo_bug_greeting_and_image_question_do_not_cross_contaminate(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_2.sqlite")
    session.turn({"text": "你好"})
    session.teach_latest({"teaching_reply_text": "你好。"})
    session.turn({"text": "这是什么", "image_path": str(APPLE)})
    session.teach_latest({"teaching_reply_text": "像苹果。"})

    image_again = session.turn({"text": "这是什么", "image_path": str(APPLE)})
    greet_again = session.turn({"text": "你好"})

    assert image_again.reply_text == "像苹果。"
    assert greet_again.reply_text == "你好。"
    assert "这是什么" not in greet_again.reply_text


def test_phase20_3_memory_package_import_dedup_list_uninstall_and_delete(tmp_path: Path) -> None:
    source = Phase20MultimodalSession(state_db_path=tmp_path / "source.sqlite")
    source.turn({"text": "这是什么", "image_path": str(APPLE)})
    source.teach_latest({"teaching_reply_text": "像苹果。"})
    view = list_memory_view(source.chat.state, query="像苹果", limit=20)
    selected = [item["memory_id"] for item in view["memories"]]
    package = export_memory_package(source.chat.state, name="苹果共现教学包", include_memory_ids=selected)

    target = Phase20MultimodalSession(state_db_path=tmp_path / "target.sqlite")
    imported = import_memory_package(target.chat.state, package)
    imported_again = import_memory_package(imported.state, package)
    package_id = imported.payload["package_id"]
    after_import = list_memory_view(imported_again.state, package_id=package_id, limit=20)

    assert imported.payload["added_count"] >= 1
    assert imported_again.payload["dedup_count"] >= imported.payload["added_count"]
    assert after_import["packages"]
    assert after_import["packages"][0]["name"] == "苹果共现教学包"
    assert after_import["memories"]

    uninstalled = uninstall_memory_package(imported_again.state, package_id)
    after_uninstall = list_memory_view(uninstalled.state, query="像苹果", limit=20)
    assert uninstalled.payload["removed_count"] == imported.payload["added_count"]
    assert after_uninstall["total_memories"] == 0

    reimported = import_memory_package(target.chat.state, package)
    phrase_memories = [item["memory_id"] for item in list_memory_view(reimported.state, query="像苹果", limit=20)["memories"]]
    deleted = delete_memories(reimported.state, phrase_memories)
    assert deleted.payload["removed_count"] == len(phrase_memories)
    assert list_memory_view(deleted.state, query="像苹果", limit=20)["total_memories"] == 0


def test_phase20_3_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "20.2_20.3"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 20.2_20.3 deliverables present" in completed.stdout
