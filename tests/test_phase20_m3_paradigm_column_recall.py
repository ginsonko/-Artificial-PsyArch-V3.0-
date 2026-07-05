"""M3 过程范式测试 (2026-07-04 重写 — 真实现版).

旧版测试锚定的 `_paradigm_column_recall` gate ("教过一条两位数答案对齐即可逐列")
已被撤除 — 那条路径把渲染布局冒充行动过程 (用户 2026-07-04 揭发). 新实现:
  - 过程范式必须经 demonstrate 阶段示范教学 (teach_process_paradigm_demonstration)
    或自发共现累积 — 两者写同种 action_sequence_cooccurrence 事件;
  - 执行 = 逐 tick 行动竞争 (条件=上一行动可感知结果), 内容槽=真实召回;
  - 没教过程范式, 教再多答案对齐也不会逐列 (答案≠过程).
"""
from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.runtime import teach_process_paradigm_demonstration


def _teach_fact(db: Path, sid: str, q: str, a: str) -> None:
    run_phase20_7_turn(user_text=q, session_id=sid, db_path=db, max_ticks=48,
                       post_commit_idle_ticks=0, runtime_stage="stage6")
    run_phase20_7_turn(user_text="", teacher_feedback=TeacherFeedback(feedback_text=a, reward_mag=1.0),
                       session_id=sid, db_path=db, max_ticks=48,
                       post_commit_idle_ticks=0, runtime_stage="stage6")


def _ask(db: Path, sid: str, q: str):
    return run_phase20_7_turn(user_text=q, session_id=sid, db_path=db, max_ticks=64,
                              post_commit_idle_ticks=0, runtime_stage="stage6")


def test_untaught_combination_composes_after_process_demonstration(tmp_path: Path) -> None:
    """教列事实 + 示范过程范式 → 未教组合逐 tick 执行拼出答案."""
    db = tmp_path / "m3.sqlite"
    sid = "m3"
    _teach_fact(db, sid, "1+7=?", "8")
    _teach_fact(db, sid, "5+3=?", "8")
    teach_process_paradigm_demonstration(db, session_id=sid)
    r = _ask(db, sid, "51+37=?")
    assert r.reply_text == "88"
    # 过程是真实 tick 行动: 每步带 paradigm_condition (上一行动结果) 与角色
    steps = [
        (e.selected_action.get("paradigm_condition"), e.selected_action.get("paradigm_content_source"))
        for e in r.tick_trace
        if isinstance(e.selected_action, dict) and e.selected_action.get("paradigm_step_note")
    ]
    assert len(steps) >= 6, steps
    assert steps[0] == ("process_start", "observed_run1_next")
    assert ("second_run_copied", "recalled_column_fact") in steps


def test_no_process_demo_means_no_column_execution(tmp_path: Path) -> None:
    """反测: 只教列事实和答案对齐, 不示范过程 → 不会逐列 (答案≠过程)."""
    db = tmp_path / "m3b.sqlite"
    sid = "m3b"
    _teach_fact(db, sid, "1+7=?", "8")
    _teach_fact(db, sid, "5+3=?", "8")
    _teach_fact(db, sid, "23+45=?", "68")  # 答案对齐, 非过程示范
    r = _ask(db, sid, "51+37=?")
    assert r.reply_text != "88"
    assert not any(
        isinstance(e.selected_action, dict) and e.selected_action.get("paradigm_step_note")
        for e in r.tick_trace
    )


def test_fact_gap_stays_honest_and_grid_clean(tmp_path: Path) -> None:
    """事实缺口 → 诚实不知道, 且半成品被擦掉不泄进回复."""
    db = tmp_path / "m3c.sqlite"
    sid = "m3c"
    _teach_fact(db, sid, "1+7=?", "8")  # 只教个位, 十位 9+8 缺
    teach_process_paradigm_demonstration(db, session_id=sid)
    r = _ask(db, sid, "91+87=?")
    assert r.reply_text != "8"
    assert "不太会" in r.reply_text or "不太会" in r.reply_text
    # 后续 turn 不被半成品污染
    r2 = _ask(db, sid, "在吗")
    assert "+87" not in (r2.reply_text or "")


def test_teaching_missing_fact_unlocks_execution(tmp_path: Path) -> None:
    """教缺失事实后, 同一未教组合立即可执行 (能力=事实库×过程范式)."""
    db = tmp_path / "m3d.sqlite"
    sid = "m3d"
    _teach_fact(db, sid, "1+7=?", "8")
    teach_process_paradigm_demonstration(db, session_id=sid)
    r1 = _ask(db, sid, "51+37=?")
    assert r1.reply_text != "88"  # 5+3 未教
    _teach_fact(db, sid, "5+3=?", "8")
    r2 = _ask(db, sid, "51+37=?")
    assert r2.reply_text == "88"


def test_process_audit_replayable(tmp_path: Path) -> None:
    """每列的召回事实进 audit (columns), tick trace 可回放."""
    db = tmp_path / "m3e.sqlite"
    sid = "m3e"
    _teach_fact(db, sid, "1+7=?", "8")
    _teach_fact(db, sid, "5+3=?", "8")
    teach_process_paradigm_demonstration(db, session_id=sid)
    r = _ask(db, sid, "51+37=?")
    assert r.reply_text == "88"
    columns = None
    for e in r.tick_trace:
        for b in (e.b_candidates or ()):
            if not isinstance(b, dict):
                continue
            for s in b.get("candidate_audit_slots") or ():
                if isinstance(s, dict) and s.get("columns"):
                    columns = s["columns"]
    assert columns and len(columns) == 2
    assert any("1+7" in str(c.get("subquery")) for c in columns)


def test_grid_shows_two_dimensional_process(tmp_path: Path) -> None:
    """DraftGrid 里能看到二维竖式 (加数两行+结果行) — 由真实行动写出, 非渲染."""
    db = tmp_path / "m3f.sqlite"
    sid = "m3f"
    _teach_fact(db, sid, "1+7=?", "8")
    _teach_fact(db, sid, "5+3=?", "8")
    teach_process_paradigm_demonstration(db, session_id=sid)
    r = _ask(db, sid, "51+37=?")
    grid_text = ""
    for e in reversed(r.tick_trace):
        dg = e.draft_grid if isinstance(e.draft_grid, dict) else {}
        if dg.get("cells"):
            grid_text = str(dg.get("visible_text") or "")
            break
    lines = [ln.strip() for ln in grid_text.splitlines() if ln.strip()]
    assert "51" in lines[0] and "37" in lines[1] and "88" in lines[-1], grid_text
