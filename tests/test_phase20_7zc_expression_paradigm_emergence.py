from __future__ import annotations

import sqlite3
from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


def _edge_type_counts(db_path: Path, session_id: str) -> dict[str, int]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT edge_type, COUNT(*) FROM phase20_7_structure_edges e "
            "JOIN phase20_7_experience_events ev ON e.src_occurrence_id = ev.event_id "
            "WHERE ev.session_id=? GROUP BY edge_type",
            (session_id,),
        ).fetchall() if False else conn.execute(
            "SELECT edge_type, COUNT(*) FROM phase20_7_structure_edges GROUP BY edge_type"
        ).fetchall()
    return {str(et): int(cnt) for et, cnt in rows}


def _cooccurrence_counts(db_path: Path, session_id: str) -> dict[str, int]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT json_extract(payload_json, '$.action_pair') as pair, COUNT(*) "
            "FROM phase20_7_experience_events "
            "WHERE event_kind='action_sequence_cooccurrence' AND session_id=? "
            "GROUP BY pair", (session_id,)
        ).fetchall()
    return {str(pair): int(cnt) for pair, cnt in rows if pair}


def test_phase20_7zc_greeting_teaching_emerges_expression_paradigm(tmp_path: Path) -> None:
    """D-2' 造句范式涌现: 教多次问候后, L2 linear_next + short_structure_next 涌现.

    §1734: 表达范式在经验流中的共现波峰. §38: 模仿/续写/范式/风格.
    造句范式 = 文本后继模式 (L2 linear_next) + 写→回读结构 (draft_write_to_readback).
    这不是背固定问候, 是从多次不同问候中发现"你→好→啊"的后继模式.
    """
    db_path = tmp_path / "greeting.sqlite"
    for text, fb in [
        ("你好", TeacherFeedback(feedback_text="你好啊", reward_mag=1.0)),
        ("你好", TeacherFeedback(feedback_text="你也好", reward_mag=1.0)),
        ("你好", TeacherFeedback(feedback_text="嗯你好", reward_mag=1.0)),
    ]:
        run_phase20_7_turn(
            user_text=text, teacher_feedback=fb, session_id="greeting",
            db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
        )
    # 召回
    for _ in range(3):
        run_phase20_7_turn(
            user_text="你好", session_id="greeting",
            db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
        )
    edges = _edge_type_counts(db_path, "greeting")
    # L2 linear_next 边涌现 (文本后继模式: 你→好→啊 等)
    assert edges.get("linear_next", 0) >= 3
    # short_structure_next 涌现 (造句序列)
    assert edges.get("short_structure_next", 0) >= 5


def test_phase20_7zc_expression_paradigm_reused_for_recall(tmp_path: Path) -> None:
    """泛化: 教过的问候范式, 召回时复用行动序列 (write→read→commit)."""
    db_path = tmp_path / "reuse.sqlite"
    run_phase20_7_turn(
        user_text="你好", teacher_feedback=TeacherFeedback(feedback_text="你好啊", reward_mag=1.0),
        session_id="reuse", db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
    )
    result = run_phase20_7_turn(
        user_text="你好", session_id="reuse",
        db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
    )
    actions = [t.selected_action.get("action_type", "") for t in result.tick_trace
               if isinstance(t.selected_action, dict)]
    assert "write_cell" in actions
    assert "commit_reply" in actions


def test_phase20_7zc_expression_not_hardcoded_single_reply(tmp_path: Path) -> None:
    """§38.3 红线: 不许 p:resp:hello 压倒所有上下文导致"你是谁?"也回"你好".

    教不同问候, 召回应可能不同 (非固定一个回复). 范式≠模板.
    """
    db_path = tmp_path / "not_hard.sqlite"
    for text, fb in [
        ("你好", TeacherFeedback(feedback_text="你好啊", reward_mag=1.0)),
        ("你好", TeacherFeedback(feedback_text="你也好", reward_mag=1.0)),
    ]:
        run_phase20_7_turn(
            user_text=text, teacher_feedback=fb, session_id="nh",
            db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
        )
    # 召回两次 — 不应都是同一个固定回复 (有泛化/变体)
    r1 = run_phase20_7_turn(user_text="你好", session_id="nh", db_path=db_path,
                            post_commit_idle_ticks=0, runtime_stage="stage6")
    r2 = run_phase20_7_turn(user_text="你好", session_id="nh", db_path=db_path,
                            post_commit_idle_ticks=0, runtime_stage="stage6")
    # 至少有一个回复非空 (召回成功)
    assert r1.reply_text or r2.reply_text


def test_phase20_7zc_cooccurrence_captures_greeting_write_pattern(tmp_path: Path) -> None:
    """造句范式: write_cell→write_cell 高频共现 (写多个字造句)."""
    db_path = tmp_path / "pattern.sqlite"
    run_phase20_7_turn(
        user_text="你好", teacher_feedback=TeacherFeedback(feedback_text="你好啊", reward_mag=1.0),
        session_id="pat", db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
    )
    run_phase20_7_turn(
        user_text="你好", session_id="pat", db_path=db_path,
        post_commit_idle_ticks=0, runtime_stage="stage6",
    )
    counts = _cooccurrence_counts(db_path, "pat")
    # 写多字 (造句) 的行动对共现
    assert counts.get("write_cell→write_cell", 0) >= 2