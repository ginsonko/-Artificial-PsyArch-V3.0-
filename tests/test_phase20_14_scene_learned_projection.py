"""Phase20.14 — 场景学成判据 纯派生投影.

这些测试证明 scene_learned_projection 是真实的、可在 idle review tick 出现、
合成 13c 阶梯判据与 10b lifecycle 的 teacher_exit/cold_retest 就绪度、与白皮书
EDUCATION_PROTOCOL 630 行 "keyword_organization_stage_passed=true before claiming
a scene learned" + 148-149 行 scaffold 褪除顺序 teacher_off -> cold_retest 语义对齐、
零新增实体, 且不破坏主闭环、不写答案、不改 selected、不伪学成、不 over-claim.

核心合规点 (白皮书口径):
  - 软判据: 产连续 scene_learned_confidence ∈ [0,1], **不产布尔 passed=true**,
    不声称收敛/完成 (与 13c 同 may_be_wrong).
  - 双褪除就绪: teacher_off + cold_retest 两者都高才算真褪除 (白皮书 148-149
    顺序褪除); 单教师退场不算学成 (冷重测可能暴露假学成).
  - keyword_organization 阶走完: 白皮书 630 核心条件, dominant 已到 keyword_organization
    或 grammar_refinement, 不能停前 4 阶却声称学成. 教3次通常只到 process_paradigm_binding,
    故 scene_learned_confidence 正确地为低/0 (合规, 非伪学成).
  - 三因子乘法合成: 双褪除就绪 * 阶梯就绪 * 生命周期就绪, 任一拖后腿则置信度低
    (软判据 may_be_wrong, 非硬布尔 AND).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from apv3test.runtime.phase20_7 import run_phase20_7_turn, TeacherFeedback
from apv3test.runtime.phase20_7 import runtime as _rtm

FORMULA_ID = _rtm.PHASE20_14_SCENE_LEARNED_ID
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
_SESSION = "phase20-14-seed"


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
    """一次空输入 tick, 促 idle learning review 激活 (lifecycle + ladder + scene 同此路径)."""
    return run_phase20_7_turn(
        user_text="", session_id=session, db_path=db_path,
        post_commit_idle_ticks=0, runtime_stage="stage4",
    )


def _scene_rows(result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in result.tick_trace:
        for row in event.action_competition:
            if isinstance(row, dict):
                carry = row.get("learning_loop_carryover")
                if isinstance(carry, dict):
                    sc = carry.get("scene_learned_projection")
                    if isinstance(sc, dict):
                        rows.append(dict(sc))
    return rows


def _any_scene(db_path: Path) -> dict[str, Any]:
    """教3次 + idle review, 返回首个出现的 scene_learned 投影 (不要求 active).

    教3次通常只到 process_paradigm_binding 阶, scene_learned_confidence 正确地为低/0
    (白皮书 630: 要 keyword_organization 阶过了才算学成). 故本辅助不要求 active,
    只要求投影真实出现并字段完整.
    """
    _teach(db_path, times=3)
    result = _idle_review(db_path)
    for sc in _scene_rows(result):
        return sc
    raise AssertionError(
        "no scene_learned_projection row after 3 teaches + idle review "
        "(projection must be mounted in carryover even if inactive)"
    )


def test_phase20_14_scene_projection_mounted_with_confidence(tmp_path: Path) -> None:
    db = tmp_path / "phase20_14_active.sqlite"
    sc = _any_scene(db)
    assert sc["formula_id"] == FORMULA_ID
    # 核心合规: 产连续 confidence ∈ [0,1], 不产布尔 passed
    assert "scene_learned_confidence" in sc
    conf = float(sc["scene_learned_confidence"])
    assert 0.0 <= conf <= 1.0, "scene_learned_confidence must be continuous in [0,1]"
    # 禁用串: 不存在布尔 passed/converged/complete 字段
    assert "scene_learned_pass" not in sc
    assert "passed" not in sc
    assert "converged" not in sc
    assert "complete" not in sc


def test_phase20_14_guardrails_match_other_projections(tmp_path: Path) -> None:
    db = tmp_path / "phase20_14_guard.sqlite"
    sc = _any_scene(db)
    # 与 13c ladder / 10b lifecycle 同 guardrail: 纯投影, 不写答案, 不产候选
    assert sc["projection_only"] is True
    assert sc["writes_answer_directly"] is False
    assert sc["creates_reply_candidate"] is False
    assert sc["subjective"] is True
    assert sc["may_be_wrong"] is True
    assert sc["uses_existing_ap_flow"] is True


def test_phase20_14_confidence_is_product_of_three_factors(tmp_path: Path) -> None:
    """三因子乘法合成: scene_learned_confidence = dual_fade * ladder_readiness * lifecycle_readiness."""
    db = tmp_path / "phase20_14_product.sqlite"
    sc = _any_scene(db)
    dual = float(sc["dual_fade_readiness"])
    kw = float(sc["keyword_organization_stage_readiness"])
    life = float(sc["lifecycle_fade_readiness"])
    conf = float(sc["scene_learned_confidence"])
    # 乘法合成 (软判据, 三因子皆高才高), 容忍浮点 round 误差
    assert abs(conf - min(1.0, dual * kw * life)) < 1e-3, (
        f"confidence {conf} != product dual*kw*life={dual*kw*life}"
    )
    # 三因子各自 ∈ [0,1]
    for v in (dual, kw, life):
        assert 0.0 <= v <= 1.0


def test_phase20_14_dominant_blocking_stage_is_weakest_factor(tmp_path: Path) -> None:
    """dominant_blocking_stage 必须是三因子中最低者 (派生一致性, 非硬编码)."""
    db = tmp_path / "phase20_14_blocking.sqlite"
    sc = _any_scene(db)
    factors = {
        "dual_fade_readiness": float(sc["dual_fade_readiness"]),
        "keyword_organization_stage": float(sc["keyword_organization_stage_readiness"]),
        "lifecycle_teacher_exit_or_cold_retest": float(sc["lifecycle_fade_readiness"]),
    }
    expected = min(factors, key=lambda k: factors[k])
    assert sc["dominant_blocking_stage"] == expected, (
        f"dominant_blocking {sc['dominant_blocking_stage']!r} != weakest {expected!r}"
    )


def test_phase20_14_no_active_carryover_yields_inactive(tmp_path: Path) -> None:
    """无教学/无 idle review 时, scene_learned 应 inactive (零回归, 不伪学成)."""
    db = tmp_path / "phase20_14_inactive.sqlite"
    result = run_phase20_7_turn(
        user_text="随便问问", session_id="phase20-14-fresh", db_path=db,
        post_commit_idle_ticks=0, runtime_stage="stage4",
    )
    for sc in _scene_rows(result):
        assert sc.get("active") is not True, (
            "scene_learned must not activate without active carryover/lifecycle"
        )


def test_phase20_14_far_text_does_not_fake_scene_learned(tmp_path: Path) -> None:
    """无关远输入不应激活 scene_learned (无匹配学习对象 identity, 不伪学成边界)."""
    db = tmp_path / "phase20_14_far.sqlite"
    _teach(db, times=3)
    result = _idle_review(db, session="phase20-14-far")
    actives = [sc for sc in _scene_rows(result) if sc.get("active")]
    assert not actives, (
        "far-text idle review should not activate scene_learned (no matching identity)"
    )


def test_phase20_14_runtime_does_not_claim_scene_learned_completion(tmp_path: Path) -> None:
    """禁用 over-claim 串: 不出现 scene_learned_complete / keyword_organization_converged 等."""
    db = tmp_path / "phase20_14_boundary.sqlite"
    _teach(db, times=3)
    result = _idle_review(db)
    serialized = repr(result.to_dict()).lower()
    forbidden = (
        "scene_learned_complete",
        "scene_learned_converged",
        "keyword_organization_converged",
        "ladder_complete",
        "ladder_converged",
        "l1_l2_l3_complete",
        "six_stage_learning_complete",
        "online_embedding_converged",
    )
    for token in forbidden:
        assert token not in serialized, f"forbidden over-claim token {token!r} found in turn output"


def test_phase20_14_zero_regression_to_reply_and_selected(tmp_path: Path) -> None:
    """scene_learned 是纯投影, 不改回复、不改 selected: 教后 idle review 仍只产连贯回复且单 selected."""
    db = tmp_path / "phase20_14_reg.sqlite"
    _teach(db, times=3)
    result = _idle_review(db)
    assert isinstance(result.reply_text, str)
    for event in result.tick_trace:
        if not event.action_competition:
            continue
        sel = sum(
            1 for row in event.action_competition
            if isinstance(row, dict) and row.get("selected") is True
        )
        assert sel == 1, (
            f"competition tick {event.tick} has {sel} selected rows, "
            "scene_learned must not break selection"
        )


def test_phase20_14_reached_keyword_org_flag_matches_dominant(tmp_path: Path) -> None:
    """reached_keyword_organization_or_later 必须与 dominant_ladder_stage 一致 (派生非硬编码)."""
    db = tmp_path / "phase20_14_reach.sqlite"
    sc = _any_scene(db)
    dominant = str(sc["dominant_ladder_stage"])
    reached = bool(sc["reached_keyword_organization_or_later"])
    assert reached == (dominant in ("keyword_organization", "grammar_refinement")), (
        f"reached={reached} inconsistent with dominant={dominant!r}"
    )


def test_phase20_14_low_confidence_when_ladder_not_at_keyword_org(tmp_path: Path) -> None:
    """白皮书 630 合规: 阶梯未到 keyword_organization 阶时, scene_learned_confidence 应为低/0.

    教3次通常只到 process_paradigm_binding (前4阶), 此时 reached_keyword_organization_or_later=False,
    ladder_readiness=0, 故 confidence=0 (不伪学成). 这正是白皮书"keyword_organization_stage_passed
    =true before claiming a scene learned"的软判据体现.
    """
    db = tmp_path / "phase20_14_low.sqlite"
    sc = _any_scene(db)
    dominant = str(sc["dominant_ladder_stage"])
    reached = bool(sc["reached_keyword_organization_or_later"])
    conf = float(sc["scene_learned_confidence"])
    if not reached:
        # 未到 keyword_organization 阶: confidence 必须为 0 (不伪学成)
        assert conf == 0.0, (
            f"confidence must be 0 when ladder not at keyword_organization "
            f"(dominant={dominant!r}, reached={reached}), got {conf}"
        )
        assert sc["keyword_organization_stage_readiness"] == 0.0
    # 若恰好推进到 keyword_organization/grammar_refinement, confidence 可>0 (三因子仍需都高)
