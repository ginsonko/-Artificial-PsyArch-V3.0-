from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.experience_log import from_json, initialize_phase20_7_store, upsert_unclosed_item
from apv3test.runtime.phase20_7.runtime import _decay_unclosed_for_idle, _statepool_unresolved_pressure


def _last_unclosed_reason(result: Any) -> dict[str, Any]:
    """Extract the most recent unclosed_item_update payload's reason from tick trace."""
    for tick in reversed(result.tick_trace):
        for event_id in getattr(tick, "experience_event_ids_written", ()) or ():
            pass  # events stored in db, not directly inspectable here
    # Walk action + ssp for unclosed_trace
    for tick in reversed(result.tick_trace):
        sa = tick.selected_action if isinstance(tick.selected_action, dict) else {}
        if sa.get("action_type") in {"request_teacher", "maintain_unclosed"}:
            # unclosed items may be in ssp_active_summary or as a separate field
            ssp = tick.ssp_active_summary if isinstance(tick.ssp_active_summary, dict) else {}
            if "unclosed_item" in ssp:
                return ssp["unclosed_item"]
    return {}


def _unclosed_u_values(db_path: Path, session_id: str) -> list[float]:
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT u_value FROM phase20_7_unclosed_items WHERE session_id=? AND status='active' ORDER BY u_value DESC",
            (session_id,),
        ).fetchall()
    return [float(r[0]) for r in rows]


def _unclosed_reasons(db_path: Path, session_id: str) -> list[dict]:
    import sqlite3
    from apv3test.runtime.phase20_7.experience_log import from_json
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT reason_json FROM phase20_7_unclosed_items WHERE session_id=? AND status='active' ORDER BY u_value DESC",
            (session_id,),
        ).fetchall()
    return [from_json(str(r[0])) if r[0] else {} for r in rows]


def test_phase20_7w_statepool_unresolved_pressure_returns_continuous_values() -> None:
    """单元测试: _statepool_unresolved_pressure 从 pool 取认知压 P=R-V, 返回连续涌现值.

    白皮书 §27.1: 未知形成压力; §27.3 Pressure=predicted_punish_energy;
    §30.1 惊(P>0)/违和(P<0) 通道涌现为 pressure_emergent/dissonance_emergent.
    复用既有 StateItem.cognitive_pressure (§9 状态池字段), 不新增实体.
    """
    from runtime.cognitive.state_pool.state_pool import StatePool, StateItem
    pool = StatePool()
    class _Obs:
        signature = "probe_sig"
        chars = ("你", "好")
        event_id = "probe_event"
    # 直接构造带认知压的 StateItem (P=R-V>0 → 惊→压力涌现)
    item_sa_id = "text_utterance::probe_sig"
    pool.items[item_sa_id] = StateItem(
        sa_id=item_sa_id, family="text_utterance", label="你好",
        real_energy=0.8, virtual_energy=0.2,  # P=0.6>0 → 惊/压力
        cognitive_pressure=0.6,
        source="probe",
    )
    # char-level SA (违和, P<0)
    char_sa_id = "text_unit::" + "你"  # 简化 hash
    pool.items[char_sa_id] = StateItem(
        sa_id=char_sa_id, family="text_unit", label="你",
        real_energy=0.1, virtual_energy=0.7,  # P=-0.6<0 → 违和
        cognitive_pressure=-0.6,
        source="probe",
    )
    pressure, dissonance, slots = _statepool_unresolved_pressure(pool, _Obs())
    assert 0.0 <= pressure <= 1.0
    assert 0.0 <= dissonance <= 1.0
    assert len(slots) >= 1
    assert all("P" in slot for slot in slots)


def test_phase20_7w_unknown_text_emerges_unclosed_pressure_not_only_request_teacher(tmp_path: Path) -> None:
    """拟人行为锁定: 未知文本产生认知压 → u_value 自然涌现压力增量 (求知欲/恐惧底层).

    修复前: u_delta 只由 output_intent 决定 (0.46 request_teacher / 0.18 maintain_unclosed);
    修复后: u_delta 含 cognitive_pressure_emergent 涌现项 (来自状态池相关 SA 的 P=R-V).
    白皮书 §27.1 "未知形成压力" + 用户理论 "未知本身带惩罚信号 → 恐惧/求知欲涌现".
    """
    db_path = tmp_path / "pressure_emergent.sqlite"
    # 未知文本 (cold start, 没教过) 触发 request_teacher
    result = run_phase20_7_turn(
        user_text="这是什么情况",
        session_id="pressure-emerge",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert result.reply_text == "不太会,教教"
    # unclosed 表应有 active item, u_value > 0
    u_values = _unclosed_u_values(db_path, "pressure-emerge")
    assert len(u_values) >= 1
    assert u_values[0] > 0.0
    # reason 应含 cognitive_pressure_emergent 字段 (涌现项被记录)
    reasons = _unclosed_reasons(db_path, "pressure-emerge")
    assert len(reasons) >= 1
    assert "cognitive_pressure_emergent" in reasons[0]
    assert "pressure_emergent" in reasons[0]


def test_phase20_7w_pressure_emergent_does_not_break_teacher_feedback_closure(tmp_path: Path) -> None:
    """回归保护: 认知压涌现注入后, 教师反馈仍能闭合未闭合项 (closure 不破坏)."""
    db_path = tmp_path / "pressure_closure.sqlite"
    # 教一遍 → 形成 unclosed
    run_phase20_7_turn(
        user_text="这是什么",
        teacher_feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0),
        session_id="pressure-closure",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    # 再问一次 → 应能召回 (closure 生效后无活跃 unclosed 或 u 大幅下降)
    result = run_phase20_7_turn(
        user_text="这是什么",
        session_id="pressure-closure",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    u_values = _unclosed_u_values(db_path, "pressure-closure")
    # 教过的应不再活跃被关闭, 或 u_value 显著低于未知时
    assert len(u_values) == 0 or u_values[0] < 0.6


def test_phase20_7w_pressure_emergent_not_keyword_or_answer_route() -> None:
    """红线: 认知压涌现不是关键词/答案路由, 是状态池认知压的连续涌现."""
    from runtime.cognitive.state_pool.state_pool import StatePool
    # 空 pool → 涌现 0 (无 SA → 无认知压 → 无涌现)
    class _Obs:
        signature = "empty"
        chars = ("a",)
        event_id = "e"
    pool = StatePool()
    pressure, dissonance, slots = _statepool_unresolved_pressure(pool, _Obs())
    assert pressure == 0.0
    assert dissonance == 0.0
    # 无增实体: 函数只读 pool.items, 不写库不路由
    assert slots == ()


def test_phase20_7w_impossibility_evidence_decays_u_when_repeated_no_successor() -> None:
    """§27.6 第4项 impossibility_evidence: 多次尝试无后继→U额外衰减→放下."""
    import sqlite3
    td = Path(tempfile.mkdtemp())
    db_path = td / "impossibility.sqlite"
    initialize_phase20_7_store(db_path)
    conn = sqlite3.connect(db_path)
    try:
        unclosed_id, _ = upsert_unclosed_item(
            conn, session_id="imp", tick=1, source_event_id="e1",
            source_signature="sig1", source_text="?", u_delta=0.6,
            reason={"reason_kind": "test"},
        )
        _decay_unclosed_for_idle(conn, unclosed_id=unclosed_id, current_u=0.15, attempt_count=7, successor_found=False)
        conn.commit()
        row = conn.execute("SELECT status, u_value FROM phase20_7_unclosed_items WHERE unclosed_id=?", (unclosed_id,)).fetchone()
        assert row[0] == "resolved" or float(row[1]) == 0.0
    finally:
        conn.close()


def test_phase20_7w_impossibility_does_not_trigger_when_successor_found() -> None:
    """对抗性: 有后继时不触发impossibility (后继找到=可闭合, 不是不可能)."""
    import sqlite3
    td = Path(tempfile.mkdtemp())
    db_path = td / "imp_no.sqlite"
    initialize_phase20_7_store(db_path)
    conn = sqlite3.connect(db_path)
    try:
        unclosed_id, _ = upsert_unclosed_item(
            conn, session_id="imp-no", tick=1, source_event_id="e1",
            source_signature="sig1", source_text="?", u_delta=0.6,
            reason={"reason_kind": "test"},
        )
        _decay_unclosed_for_idle(conn, unclosed_id=unclosed_id, current_u=0.6, attempt_count=8, successor_found=True)
        conn.commit()
        row = conn.execute("SELECT reason_json FROM phase20_7_unclosed_items WHERE unclosed_id=?", (unclosed_id,)).fetchone()
        reason = from_json(str(row[0])) if row[0] else {}
        assert reason.get("impossibility_evidence", 0.0) == 0.0
    finally:
        conn.close()


def test_phase20_7w_pressure_emergent_does_not_claim_fear_or_curiosity_converged(tmp_path: Path) -> None:
    """红线: 涌现项不声称恐惧/求知欲收敛或完成 (禁用串, 软投影)."""
    db_path = tmp_path / "redline.sqlite"
    run_phase20_7_turn(
        user_text="不知道",
        session_id="redline",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    import sqlite3
    from apv3test.runtime.phase20_7.experience_log import from_json
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT reason_json FROM phase20_7_unclosed_items WHERE session_id=?",
            ("redline",),
        ).fetchall()
    forbidden = ("fear_converged", "curiosity_converged", "pressure_converged",
                 "fear_complete", "curiosity_complete", "unclosed_converged")
    for r in rows:
        reason_str = str(r[0]) if r[0] else ""
        for token in forbidden:
            assert token not in reason_str.lower()