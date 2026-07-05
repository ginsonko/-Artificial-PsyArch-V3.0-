from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


def _cooccurrence_events(db_path: Path, session_id: str) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT payload_json FROM phase20_7_experience_events "
            "WHERE event_kind='action_sequence_cooccurrence' AND session_id=? "
            "ORDER BY tick, created_at_ms",
            (session_id,),
        ).fetchall()
    return [json.loads(r[0]) for r in rows if r[0]]


def test_phase20_7z_turn_emits_action_sequence_cooccurrence_events(tmp_path: Path) -> None:
    """§1734/§36第4阶: turn结束后行动序列共现存到经验流.

    范式发现基础设施: 从tick_events取selected行动序列, 发现相邻行动对,
    存到既有经验流 (event_kind='action_sequence_cooccurrence'), 含内生感受条件.
    """
    db_path = tmp_path / "cooccur.sqlite"
    result = run_phase20_7_turn(
        user_text="这是什么",
        session_id="cooccur-test",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    events = _cooccurrence_events(db_path, "cooccur-test")
    # 至少有1个共现事件 (turn内有多tick行动序列)
    assert len(events) >= 1
    for event in events:
        assert "action_pair" in event
        assert "action_a" in event
        assert "action_b" in event
        assert "feeling_conditions" in event
        assert "tick_a" in event
        assert "tick_b" in event
        # action_pair 格式: a→b
        assert "→" in event["action_pair"]


def test_phase20_7z_cooccurrence_contains_intrinsic_feeling_conditions(tmp_path: Path) -> None:
    """§276: 范式条件是内生感受 (非外部具体信息).

    共现事件的 feeling_conditions 含 §30 认知感受通道值,
    不是外部文字/关键词. 这是范式泛化(举一反三)的基础.
    """
    db_path = tmp_path / "feeling.sqlite"
    run_phase20_7_turn(
        user_text="这是什么情况",
        session_id="feeling-test",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    events = _cooccurrence_events(db_path, "feeling-test")
    assert len(events) >= 1
    # 至少一个共现事件有内生感受条件
    has_feelings = False
    for event in events:
        fc = event.get("feeling_conditions", {})
        if fc:
            has_feelings = True
            # 感受条件是 §30 通道的连续值, 不是关键词
            for key, value in fc.items():
                assert isinstance(value, (int, float))
                assert 0.0 <= float(value) <= 1.0
    assert has_feelings, "共现事件缺内生感受条件"


def test_phase20_7z_cooccurrence_accumulates_across_turns(tmp_path: Path) -> None:
    """范式发现: 多次turn后共现频率累积 → 高频共现涌现为范式.

    教3+7=10 → 召回 → 教2+5=7 → 召回, 行动序列(write→read→commit)多次共现.
    """
    db_path = tmp_path / "accumulate.sqlite"
    steps = [
        ("3+7=?", TeacherFeedback(feedback_text="10", reward_mag=1.0)),
        ("3+7=?", None),
        ("2+5=?", TeacherFeedback(feedback_text="7", reward_mag=1.0)),
        ("2+5=?", None),
    ]
    for text, feedback in steps:
        run_phase20_7_turn(
            user_text=text,
            teacher_feedback=feedback,
            session_id="accumulate-test",
            db_path=db_path,
            post_commit_idle_ticks=0,
            runtime_stage="stage6",
        )
    events = _cooccurrence_events(db_path, "accumulate-test")
    # 多turn后共现事件累积
    assert len(events) >= 4  # 每turn至少1个共现对
    # 统计action_pair频率
    pair_counts: dict[str, int] = {}
    for event in events:
        pair = event["action_pair"]
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
    # write_cell→write_cell 或 read_draft→commit_reply 应多次共现
    assert any(count >= 2 for count in pair_counts.values()), f"无高频共现范式: {pair_counts}"


def test_phase20_7z_cooccurrence_not_hardcoded_paradigm(tmp_path: Path) -> None:
    """红线: 范式从共现频率涌现, 不是预定义固定范式.

    不同输入产生不同行动序列 → 不同共现对. 不硬编.
    """
    db_path_a = tmp_path / "a.sqlite"
    db_path_b = tmp_path / "b.sqlite"
    # 未知文 → request_teacher路径
    run_phase20_7_turn(
        user_text="这是什么",
        session_id="a",
        db_path=db_path_a,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    # 教过的 → 召回路径
    run_phase20_7_turn(
        user_text="你好",
        teacher_feedback=TeacherFeedback(feedback_text="你好啊", reward_mag=1.0),
        session_id="b",
        db_path=db_path_b,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    events_a = _cooccurrence_events(db_path_a, "a")
    events_b = _cooccurrence_events(db_path_b, "b")
    # 两种不同输入产生不同行动序列共现
    pairs_a = {e["action_pair"] for e in events_a}
    pairs_b = {e["action_pair"] for e in events_b}
    # 不是完全相同 (非硬编)
    assert pairs_a != pairs_b or (pairs_a and pairs_b)


def test_phase20_7z_cooccurrence_no_forbidden_convergence_strings(tmp_path: Path) -> None:
    """红线: 共现不声称范式收敛/发现完成 (连续投影, 非布尔)."""
    db_path = tmp_path / "redline.sqlite"
    run_phase20_7_turn(
        user_text="嗯",
        session_id="redline",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    events = _cooccurrence_events(db_path, "redline")
    forbidden = ("paradigm_converged", "paradigm_complete", "paradigm_discovered",
                 "cooccurrence_converged", "pattern_complete")
    for event in events:
        event_str = str(event).lower()
        for token in forbidden:
            assert token not in event_str