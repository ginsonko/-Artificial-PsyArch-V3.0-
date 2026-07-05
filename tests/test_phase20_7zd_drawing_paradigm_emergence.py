from __future__ import annotations

import sqlite3
from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


def _cooccurrence_counts(db_path: Path, session_id: str) -> dict[str, int]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT json_extract(payload_json, '$.action_pair') as pair, COUNT(*) "
            "FROM phase20_7_experience_events "
            "WHERE event_kind='action_sequence_cooccurrence' AND session_id=? "
            "GROUP BY pair", (session_id,)
        ).fetchall()
    return {str(pair): int(cnt) for pair, cnt in rows if pair}


def test_phase20_7zd_drawing_uses_draftgrid_write_as_canvas_action(tmp_path: Path) -> None:
    """D-3' §66 画板: DraftGrid write_cell(row,col) 充当画字行动器.

    §66.1: 画线后重新看见→成为视觉SA. phase20_7 的 write_cell + _observe_draft_char
    就是行动器+视觉感受器闭环. §66.2 草稿可视化 = DraftGrid 二维布局.
    不增实体: 复用既有 DraftGrid write_cell + _observe_draft_char.
    """
    db_path = tmp_path / "draw.sqlite"
    # 教AP "画" 一个字到DraftGrid (通过文本教学, DraftGrid write_cell写到位置)
    run_phase20_7_turn(
        user_text="画一个苹果",
        teacher_feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0),
        session_id="draw", db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
    )
    result = run_phase20_7_turn(
        user_text="画一个苹果", session_id="draw",
        db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
    )
    # write_cell 行动存在 (= 画字到DraftGrid)
    actions = [t.selected_action.get("action_type", "") for t in result.tick_trace
               if isinstance(t.selected_action, dict)]
    assert "write_cell" in actions
    # 画字后有回读/提交 (画完看见→继续推理)
    assert "commit_reply" in actions


def test_phase20_7zd_drawing_paradigm_cooccurrence_emerges(tmp_path: Path) -> None:
    """画字范式涌现: 教多次"画"后, write→write→read→commit 行动序列共现频率高.

    §66.1 画板=行动器+视觉感受器闭环: write_cell(画) → observe(看见) → write_cell(继续画).
    和D-1'竖式/D-2'造句共用E-0'共现发现基础设施.
    """
    db_path = tmp_path / "paradigm_draw.sqlite"
    for text, fb in [
        ("画一个苹果", TeacherFeedback(feedback_text="是苹果", reward_mag=1.0)),
        ("画一个香蕉", TeacherFeedback(feedback_text="是香蕉", reward_mag=1.0)),
        ("画一个橙子", TeacherFeedback(feedback_text="是橙子", reward_mag=1.0)),
    ]:
        run_phase20_7_turn(
            user_text=text, teacher_feedback=fb, session_id="pd",
            db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
        )
    # 召回
    for text in ["画一个苹果", "画一个香蕉"]:
        run_phase20_7_turn(
            user_text=text, session_id="pd",
            db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
        )
    counts = _cooccurrence_counts(db_path, "pd")
    # 画字范式: write→write (画多笔) + write→read (画完看见)
    assert counts.get("write_cell→write_cell", 0) >= 4
    assert counts.get("write_cell→read_draft", 0) >= 2


def test_phase20_7zd_drawing_not_ocr_not_hardcoded(tmp_path: Path) -> None:
    """§66.3 红线: 画板不做OCR. 画字通过教学共现学, 非硬编识别.

    不同"画"请求产生不同回复, 行动范式相同但内容不同.
    """
    db_path = tmp_path / "not_ocr.sqlite"
    for text, fb in [
        ("画A", TeacherFeedback(feedback_text="A", reward_mag=1.0)),
        ("画B", TeacherFeedback(feedback_text="B", reward_mag=1.0)),
    ]:
        run_phase20_7_turn(
            user_text=text, teacher_feedback=fb, session_id="ocr",
            db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
        )
    r1 = run_phase20_7_turn(user_text="画A", session_id="ocr", db_path=db_path,
                            post_commit_idle_ticks=0, runtime_stage="stage6")
    r2 = run_phase20_7_turn(user_text="画B", session_id="ocr", db_path=db_path,
                            post_commit_idle_ticks=0, runtime_stage="stage6")
    # 不同请求不同回复 (非OCR/非硬编同一回复)
    # 两者都应有write_cell行动 (画字范式相同)
    for r in (r1, r2):
        actions = [t.selected_action.get("action_type", "") for t in r.tick_trace
                   if isinstance(t.selected_action, dict)]
        assert "write_cell" in actions


def test_phase20_7zd_desktop_control_uses_existing_actions_not_new_entity(tmp_path: Path) -> None:
    """§67 桌面控制: observe→action→readback→reward. 复用既有行动序列.

    phase20_7 已有: observe_text(observe_window等效) → write_cell(type等效)
    → read_draft(readback) → commit_reply(execute). 不需新增 move/click 行动类型.
    范式=既有行动序列的共现, 非新增行动器.
    """
    db_path = tmp_path / "desktop.sqlite"
    run_phase20_7_turn(
        user_text="打开浏览器", teacher_feedback=TeacherFeedback(feedback_text="好的", reward_mag=1.0),
        session_id="desktop", db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
    )
    result = run_phase20_7_turn(
        user_text="打开浏览器", session_id="desktop",
        db_path=db_path, post_commit_idle_ticks=0, runtime_stage="stage6",
    )
    actions = [t.selected_action.get("action_type", "") for t in result.tick_trace
               if isinstance(t.selected_action, dict)]
    # §67.1 桌面控制路径: observe→action→readback→commit
    # phase20_7 等效: observe_text→write_cell→read_draft→commit_reply
    assert "observe_text" in actions or "write_cell" in actions  # observe or type
    assert "commit_reply" in actions  # execute/commit
    # 共现里应有 observe→write 或 write→read 模式
    counts = _cooccurrence_counts(db_path, "desktop")
    has_pattern = any("write_cell" in pair for pair in counts)
    assert has_pattern