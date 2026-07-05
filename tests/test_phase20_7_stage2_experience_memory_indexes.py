from __future__ import annotations

from pathlib import Path
import sqlite3

from apv3test.runtime.phase20_7 import (
    TeacherFeedback,
    attach_package_membership,
    create_import_batch,
    list_unified_memory_entries,
    rebuild_phase20_7_indexes,
    run_phase20_7_turn,
    tombstone_memory_entry,
    unload_import_batch,
)


def _seed_alignment(db_path: Path, *, user_text: str = "你好啊", feedback_text: str = "你也好") -> str:
    run_phase20_7_turn(
        user_text=user_text,
        teacher_feedback=TeacherFeedback(feedback_text=feedback_text, reward_mag=1.0),
        session_id="stage2-seed",
        db_path=db_path,
        post_commit_idle_ticks=0,
    )
    entries = list_unified_memory_entries(db_path)
    fast_entries = [entry for entry in entries if entry["source_event_kind"] == "experience_alignment"]
    assert fast_entries
    return str(fast_entries[0]["memory_entry_id"])


def test_stage2_exact_b0_index_is_rebuildable_from_experience_log(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    _seed_alignment(db_path)

    with sqlite3.connect(db_path) as conn:
        before = conn.execute("SELECT COUNT(*) FROM phase20_7_exact_b0_index").fetchone()[0]
        conn.execute("DELETE FROM phase20_7_exact_b0_index")
        conn.commit()
    assert before >= 1

    status = rebuild_phase20_7_indexes(db_path)
    recalled = run_phase20_7_turn(
        user_text="你好啊",
        session_id="stage2-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
    )

    assert status["indexed_rows"] == 1
    assert recalled.reply_text == "你也好"
    assert any(event.b_candidates for event in recalled.tick_trace)


def test_stage2_unified_memory_view_contains_continuous_support_entries_with_text(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    _seed_alignment(db_path)
    run_phase20_7_turn(
        user_text="你是谁",
        session_id="stage2-unknown",
        db_path=db_path,
        post_commit_idle_ticks=0,
    )

    entries = list_unified_memory_entries(db_path)
    display_texts = [str(entry["display_text"]) for entry in entries]
    tendencies = {str(entry["processing_tendency"]) for entry in entries}
    supports = [float(entry["support"]) for entry in entries]

    assert any("你好啊 -> 你也好" == text for text in display_texts)
    assert any("你是谁" == text for text in display_texts)
    assert all(t.startswith("support_") for t in tendencies)
    # §173.5 退火后验: 教过的 alignment(reward=1.0, support_count>=1)把握应明显高于
    # 底噪(0.72 > 0.52, 这是退火公式推出的真实值, 非随意魔数); 未学习观察
    # (text_receptor_observation)是先验底噪 _SUPPORT_BASE=0.34, 明显低于教过的.
    # 这断言的是"教过 > 未学"这一真正不变量, 不是某个魔数边界.
    assert any(s > 0.52 for s in supports), f"taught alignment support should exceed 0.52, got {supports}"
    assert any(s <= 0.40 for s in supports), f"unlearned observation should be near base 0.34, got {supports}"
    assert all(entry["memory_view"] == "local_memory_package_unified" for entry in entries)


def test_stage2_tombstone_memory_entry_disables_future_exact_b0_recall(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    memory_entry_id = _seed_alignment(db_path)

    tombstone_memory_entry(db_path, memory_entry_id=memory_entry_id, reason="user_delete")
    recalled = run_phase20_7_turn(
        user_text="你好啊",
        session_id="stage2-after-delete",
        db_path=db_path,
        post_commit_idle_ticks=0,
    )
    active_entries = list_unified_memory_entries(db_path)
    all_entries = list_unified_memory_entries(db_path, include_inactive=True)

    assert recalled.reply_text == "不太会,教教"
    assert not any(event.b_candidates for event in recalled.tick_trace)
    assert not any(entry["memory_entry_id"] == memory_entry_id for entry in active_entries)
    assert any(entry["memory_entry_id"] == memory_entry_id and entry["active"] is False for entry in all_entries)


def test_stage2_package_unload_tombstones_new_package_members(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    memory_entry_id = _seed_alignment(db_path, user_text="再见", feedback_text="下次见")
    import_batch_id = create_import_batch(
        db_path,
        package_id="demo-pack",
        package_name="演示包",
        source_hash="sha256-demo",
    )
    attach_package_membership(
        db_path,
        import_batch_id=import_batch_id,
        object_kind="event",
        object_ref=memory_entry_id,
        event_id=memory_entry_id,
        was_new=True,
    )

    result = unload_import_batch(db_path, import_batch_id=import_batch_id)
    recalled = run_phase20_7_turn(
        user_text="再见",
        session_id="stage2-after-unload",
        db_path=db_path,
        post_commit_idle_ticks=0,
    )

    assert result["tombstoned_count"] == 1
    assert recalled.reply_text == "不太会,教教"
    assert not any(event.b_candidates for event in recalled.tick_trace)
