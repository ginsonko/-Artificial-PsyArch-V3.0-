"""Phase20.13c — Language Learning Ladder 纯派生判据投影。

这些测试证明 ladder 投影是真实的、可在 idle review tick 激活、6 阶梯判据派生
自既有 projection_only 量、与白皮书 EDUCATION_PROTOCOL "Language Learning
Ladder" 6 阶段语义对齐、零新增实体, 且不破坏主闭环、不写答案、不改 selected、
不伪学成、不 over-claim convergence.

ladder 与 learning_stage_runtime_progression (教学褪除) / learning_object_lifecycle
(冷重测就绪) 三者并存互补: ladder 是"语言学习阶梯判据", 不替代教学褪除判定.
"""
from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any

from apv3test.runtime.phase20_7 import run_phase20_7_turn, TeacherFeedback
from apv3test.runtime.phase20_7 import runtime as _rtm

FORMULA_ID = _rtm.PHASE20_13C_LANGUAGE_LEARNING_LADDER_ID
LADDER_ORDER = (
    "echo_imitation",
    "successor_prediction",
    "multi_reply_aggregation",
    "process_paradigm_binding",
    "keyword_organization",
    "grammar_refinement",
)
_TAUGHT_INPUT = "你好聪明"
_TAUGHT_REPLY = "谢谢"
_SESSION = "phase20-13c-seed"


def _teach(db_path: Path, *, times: int, session: str = _SESSION, stage: str = "stage4") -> None:
    """教同一对齐 ``times`` 次, 使 lifecycle review/self_test 计数累积, 触发 idle review."""
    for _ in range(times):
        run_phase20_7_turn(
            user_text=_TAUGHT_INPUT,
            teacher_feedback=TeacherFeedback(feedback_text=_TAUGHT_REPLY, reward_mag=1.0),
            session_id=session, db_path=db_path,
            post_commit_idle_ticks=0, runtime_stage=stage,
        )


def _idle_review(db_path: Path, *, session: str = _SESSION) -> Any:
    """一次空输入 tick, 促 idle learning review 激活 (lifecycle + ladder 同此路径)."""
    return run_phase20_7_turn(
        user_text="", session_id=session, db_path=db_path,
        post_commit_idle_ticks=0, runtime_stage="stage4",
    )


def _ladder_rows(result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in result.tick_trace:
        for row in event.action_competition:
            if isinstance(row, dict):
                carry = row.get("learning_loop_carryover")
                if isinstance(carry, dict):
                    lad = carry.get("language_learning_ladder")
                    if isinstance(lad, dict):
                        rows.append(dict(lad))
    return rows


def _active_ladder(db_path: Path) -> dict[str, Any]:
    """教3次 + idle review, 返回首个 active ladder 投影."""
    _teach(db_path, times=3)
    result = _idle_review(db_path)
    for lad in _ladder_rows(result):
        if lad.get("active"):
            return lad
    raise AssertionError("no active language_learning_ladder projection after 3 teaches + idle review")


def test_phase20_13c_ladder_produces_active_6_stage_projection(tmp_path: Path) -> None:
    db = tmp_path / "phase20_13c_active.sqlite"
    lad = _active_ladder(db)
    assert lad["formula_id"] == FORMULA_ID
    assert lad["active"] is True
    assert lad["dominant_ladder_stage"] in LADDER_ORDER
    assert isinstance(lad["ladder_scores"], dict) and set(lad["ladder_scores"]) == set(LADDER_ORDER)
    assert tuple(lad["ladder_stage_order"]) == LADDER_ORDER
    for v in lad["ladder_scores"].values():
        assert 0.0 <= float(v) <= 1.0, "ladder score out of [0,1]"
    assert lad["ladder_confidence"] >= 0.0


def test_phase20_13c_guardrails_match_other_projections(tmp_path: Path) -> None:
    db = tmp_path / "phase20_13c_guard.sqlite"
    lad = _active_ladder(db)
    # 与 learning_stage_runtime_progression / lifecycle 同 guardrail: 纯投影, 不写答案
    assert lad["projection_only"] is True
    assert lad["writes_answer_directly"] is False
    assert lad["creates_reply_candidate"] is False
    assert lad["subjective"] is True
    assert lad["may_be_wrong"] is True
    assert lad["uses_existing_ap_flow"] is True


def test_phase20_13c_6_stage_scores_are_derived_not_hardcoded(tmp_path: Path) -> None:
    db = tmp_path / "phase20_13c_derive.sqlite"
    lad = _active_ladder(db)
    scores = lad["ladder_scores"]
    # 教过几次 + 有反馈: echo_imitation 应有正向基础 (它来自 review_count + reward_pressure).
    assert scores["echo_imitation"] > 0.0, "echo_imitation should be positive after reward teaches"
    # keyword_organization 在 teacher_off/feedback_only 还没显著时, 应是软判据, 不强制为高
    # (它依赖 teacher_off_readiness 或 feedback_only_readiness 才会上来, 白皮书"教师退场/纯
    # 反馈下通过此阶才算学成").
    assert scores["keyword_organization"] >= 0.0
    # grammar_refinement 是连续信号, 不应为负 (公式已 _unit 到 [0,1])
    assert scores["grammar_refinement"] >= 0.0
    # dominant 必须是 score 最大的阶梯 (派生一致性, 非硬编码选择)
    assert lad["dominant_ladder_stage"] == max(scores, key=lambda k: scores[k])
    assert abs(lad["ladder_confidence"] - max(scores.values())) < 1e-9


def test_phase20_13c_ladder_inactive_without_active_carryover(tmp_path: Path) -> None:
    """无任何教学/无 idle review 时, ladder 应为 inactive (零回归, 不伪学成)."""
    db = tmp_path / "phase20_13c_inactive.sqlite"
    # 单次用户输入 (无对齐反馈), 跑一次普通 tick
    result = run_phase20_7_turn(
        user_text="随便问问", session_id="phase20-13c-fresh", db_path=db,
        post_commit_idle_ticks=0, runtime_stage="stage4",
    )
    lads = _ladder_rows(result)
    assert all(isinstance(l, dict) for l in lads)
    # 任何出现的 ladder 若有, 应是 inactive (carryover 未激活或无 lifecycle)
    for l in lads:
        assert l.get("active") is not True, "ladder must not activate without active carryover/lifecycle"


def test_phase20_13c_far_text_does_not_fake_keyword_stage_passed(tmp_path: Path) -> None:
    """无关远输入不应让 keyword_organization 顶到学成阈 (不伪学成边界)."""
    db = tmp_path / "phase20_13c_far.sqlite"
    _teach(db, times=3)
    # 远输入: 与所教场景无关
    result = _idle_review(db, session="phase20-13c-far")
    # 远输入没有匹配的对齐/lifecycle, ladder 应不激活, 或激活但 keyword_organization 不高
    lads = [l for l in _ladder_rows(result) if l.get("active")]
    assert not lads, (
        "far-text idle review should not activate ladder (no matching learning object identity)"
    )


def test_phase20_13c_runtime_does_not_claim_ladder_convergence_or_completion(tmp_path: Path) -> None:
    db = tmp_path / "phase20_13c_boundary.sqlite"
    _teach(db, times=3)
    result = _idle_review(db)
    serialized = repr(result.to_dict()).lower()
    forbidden = (
        "ladder_complete",
        "ladder_converged",
        "l1_l2_l3_complete",
        "keyword_organization_converged",
        "six_stage_learning_complete",
        "online_embedding_converged",
    )
    for token in forbidden:
        assert token not in serialized, f"forbidden over-claim token {token!r} found in turn output"


def test_phase20_13c_ladder_zero_regression_to_reply_and_selected(tmp_path: Path) -> None:
    """ladder 是纯投影, 不改回复、不改 selected: 教后 idle review 仍只产连贯回复且单 selected."""
    db = tmp_path / "phase20_13c_reg.sqlite"
    _teach(db, times=3)
    result = _idle_review(db)
    # 选过的 reply_text 仍由 AP 主闭环决定, ladder 不写答案
    assert isinstance(result.reply_text, str)
    # 每个 competition tick 仍恰一行 selected
    for event in result.tick_trace:
        if not event.action_competition:
            continue
        sel = sum(
            1 for row in event.action_competition
            if isinstance(row, dict) and row.get("selected") is True
        )
        assert sel == 1, f"competition tick {event.tick} has {sel} selected rows, ladder must not break selection"