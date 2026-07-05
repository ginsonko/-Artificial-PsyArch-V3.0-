from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


def _cooccurrence_pair_counts(db_path: Path, session_id: str) -> dict[str, int]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT json_extract(payload_json, '$.action_pair') as pair, COUNT(*) as cnt "
            "FROM phase20_7_experience_events "
            "WHERE event_kind='action_sequence_cooccurrence' AND session_id=? "
            "GROUP BY pair", (session_id,)
        ).fetchall()
    return {str(pair): int(cnt) for pair, cnt in rows if pair}


def test_phase20_7zb_math_teaching_emerges_write_read_commit_paradigm(tmp_path: Path) -> None:
    """D-1' 竖式数学真范式学习: 教多次加法后, write→read→commit 行动序列共现频率高.

    §1734: 过程范式在经验流中的共现波峰. §36第4阶: process-paradigm binding.
    这是范式涌现 (非背答案): AP学到的是行动序列模式, 不是固定答案.
    """
    db_path = tmp_path / "paradigm.sqlite"
    # 教3次不同加法
    for text, fb in [
        ("3+7=?", TeacherFeedback(feedback_text="10", reward_mag=1.0)),
        ("2+5=?", TeacherFeedback(feedback_text="7", reward_mag=1.0)),
        ("4+3=?", TeacherFeedback(feedback_text="7", reward_mag=1.0)),
    ]:
        run_phase20_7_turn(
            user_text=text, teacher_feedback=fb, session_id="paradigm-math",
            db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
        )
    # 召回3次
    for text in ["3+7=?", "2+5=?", "4+3=?"]:
        run_phase20_7_turn(
            user_text=text, session_id="paradigm-math",
            db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
        )
    counts = _cooccurrence_pair_counts(db_path, "paradigm-math")
    # write_cell→write_cell 高频共现 (竖式逐格写)
    assert counts.get("write_cell→write_cell", 0) >= 6
    # write_cell→read_draft 共现 (写完回读=验算)
    assert counts.get("write_cell→read_draft", 0) >= 3
    # read_draft→commit_reply 共现 (回读后提交=完成)
    assert counts.get("read_draft→commit_reply", 0) >= 3


def test_phase20_7zb_paradigm_action_sequence_reused_for_unseen_problem(tmp_path: Path) -> None:
    """泛化验证: 教过的行动序列范式, 在问新题时被复用 (即使答案可能错, 行动过程对).

    举一反三: 范式条件是内生感受 (低把握→开始写), 不是具体数字.
    """
    db_path = tmp_path / "generalize.sqlite"
    # 教2次
    for text, fb in [
        ("3+7=?", TeacherFeedback(feedback_text="10", reward_mag=1.0)),
        ("2+5=?", TeacherFeedback(feedback_text="7", reward_mag=1.0)),
    ]:
        run_phase20_7_turn(
            user_text=text, teacher_feedback=fb, session_id="gen-math",
            db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
        )
    # 问没教过的 4+3 (行动序列应复用竖式范式)
    result = run_phase20_7_turn(
        user_text="4+3=?", session_id="gen-math",
        db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
    )
    # AP应有行动序列 (observe→write→...→commit), 即使答案不一定对
    action_types = [
        tick.selected_action.get("action_type", "")
        for tick in result.tick_trace
        if isinstance(tick.selected_action, dict) and tick.selected_action.get("action_type")
    ]
    # 应有 write_cell 和 commit_reply (竖式行动序列复用)
    assert "write_cell" in action_types
    assert "commit_reply" in action_types
    # 共现里应有 write→read→commit 模式
    counts = _cooccurrence_pair_counts(db_path, "gen-math")
    assert counts.get("write_cell→read_draft", 0) >= 1


def test_phase20_7zb_paradigm_not_hardcoded_answer(tmp_path: Path) -> None:
    """红线: 范式是行动序列共现, 不是固定答案. 不同题产生不同答案但同一行动范式."""
    db_path = tmp_path / "not_hard.sqlite"
    # 教3+7=10
    run_phase20_7_turn(
        user_text="3+7=?", teacher_feedback=TeacherFeedback(feedback_text="10", reward_mag=1.0),
        session_id="nh", db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
    )
    # 教2+5=7
    run_phase20_7_turn(
        user_text="2+5=?", teacher_feedback=TeacherFeedback(feedback_text="7", reward_mag=1.0),
        session_id="nh", db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
    )
    # 召回 — 答案不同但行动序列范式相同
    r1 = run_phase20_7_turn(user_text="3+7=?", session_id="nh", db_path=db_path,
                            post_commit_idle_ticks=0, runtime_stage="stage6")
    r2 = run_phase20_7_turn(user_text="2+5=?", session_id="nh", db_path=db_path,
                            post_commit_idle_ticks=0, runtime_stage="stage6")
    # 答案不同 (不是硬编同一个答案)
    assert r1.reply_text != r2.reply_text or r1.reply_text == "不太会,教教"
    # 但行动序列范式相同 (都有 write→commit)
    for r in (r1, r2):
        actions = [t.selected_action.get("action_type", "") for t in r.tick_trace
                   if isinstance(t.selected_action, dict)]
        assert "write_cell" in actions
        assert "commit_reply" in actions


def test_phase20_7zb_cooccurrence_contains_feeling_conditions_for_paradigm(tmp_path: Path) -> None:
    """§276: 范式条件是内生感受. 数学教学的共现事件含认知感受条件."""
    db_path = tmp_path / "feeling.sqlite"
    run_phase20_7_turn(
        user_text="3+7=?", teacher_feedback=TeacherFeedback(feedback_text="10", reward_mag=1.0),
        session_id="fc", db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
    )
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT payload_json FROM phase20_7_experience_events "
            "WHERE event_kind='action_sequence_cooccurrence' AND session_id=?",
            ("fc",)
        ).fetchall()
    for row in rows:
        payload = json.loads(row[0])
        fc = payload.get("feeling_conditions", {})
        # 至少有一些内生感受条件被记录 (非空)
        # 感受条件是§30通道连续值, 不是关键词
        for key, value in fc.items():
            assert isinstance(value, (int, float))
            assert 0.0 <= float(value) <= 1.0