from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9j_structural_generalization_value_modulation/v1"


def _u(value: str) -> str:
    return value.encode("unicode_escape").decode("ascii")


def _first_structural_b(result):
    for event in result.tick_trace:
        if event.b_candidates and event.b_candidates[0].get("kind") == "structural_b":
            return event.b_candidates[0]
    return None


def _first_write_drive_trace(result):
    for event in result.tick_trace:
        for row in event.action_competition:
            if row.get("action_type") != "write_cell":
                continue
            trace = row.get("write_drive_from_recall_state")
            if isinstance(trace, dict) and trace:
                return trace
    return None


def _teach_then_query(*, db_path: Path, session_id: str, reward_mag: float, punish_mag: float):
    run_phase20_7_turn(
        user_text="没错,你好聪明",
        teacher_feedback=TeacherFeedback(
            feedback_text="谢谢", reward_mag=reward_mag, punish_mag=punish_mag
        ),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    return run_phase20_7_turn(
        user_text="你好聪明",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )


def test_phase20_9j_grasp_rewarded_generalization_keeps_write_drive_healthy(tmp_path: Path) -> None:
    """奖励确认后, 泛化仍应能落笔(reply=谢谢), 且 write drive 经 grasp 门控后保持合理.

    锁定: reward=1.0 时 grasp 高 -> support 斜率不被过度压制 -> 仍泛化出"谢谢".
    这是 9j 已验证的合规泛化(替代答案表), 本测试确认 grasp 门控不破坏它.
    """
    result = _teach_then_query(
        db_path=tmp_path / "grasp_reward.sqlite",
        session_id="grasp-reward",
        reward_mag=1.0,
        punish_mag=0.0,
    )
    b = _first_structural_b(result)
    trace = _first_write_drive_trace(result)

    assert _u(result.reply_text) == _u("谢谢")
    assert b is not None
    assert trace is not None
    assert trace["source"] == "structural_b_support_reward_punish_residual"
    assert trace["generalization_grasp"] > 0.0
    assert trace["reward_delta"] > 0.0
    assert trace["writes_answer_directly"] is False


def test_phase20_9j_grasp_zero_reward_generalization_drive_is_grasp_gated(tmp_path: Path) -> None:
    """无结果证据(reward=0)时, 泛化候选仍可能形成, 但 write drive 经 grasp 门控软化.

    锁定 codex 审查核实的真问题修复: 结构相似度先验不应单独驱动"敢写",
    "敢泛化"必须是经验结果(§173.5 grasp)而非默认冲动. reward=0 sc=0 时
    grasp=底噪(0.34), write drive 显著低于有奖励场景.
    """
    result_no_reward = _teach_then_query(
        db_path=tmp_path / "grasp_zero.sqlite",
        session_id="grasp-zero",
        reward_mag=0.0,
        punish_mag=0.0,
    )
    result_reward = _teach_then_query(
        db_path=tmp_path / "grasp_reward_cmp.sqlite",
        session_id="grasp-reward-cmp",
        reward_mag=1.0,
        punish_mag=0.0,
    )
    trace_zero = _first_write_drive_trace(result_no_reward)
    trace_reward = _first_write_drive_trace(result_reward)

    assert trace_zero is not None and trace_reward is not None
    # grasp 门控: 无奖励 grasp 显著低于有奖励
    assert float(trace_zero["generalization_grasp"]) < float(trace_reward["generalization_grasp"])
    # write drive: 无奖励时显著软化(经验结果门控, 不是结构先验默认冲动)
    assert float(trace_zero["drive"]) < float(trace_reward["drive"])
    # 无奖励时 write drive 不应碾压式高(软化效果): base+低grasp贡献
    assert float(trace_zero["drive"]) < 0.55
    assert trace_zero["writes_answer_directly"] is False


def test_phase20_9j_grasp_generalization_grasp_is_outcome_anchored_not_structural_prior(tmp_path: Path) -> None:
    """grasp 来自结果锚定(_support_from_reward_punish), 不是结构相似度.

    对抗性锁定: 确认 grasp 是经验结果, 而非把 structural similarity 当把握感.
    同样的结构相似度(query=你好聪明, shared=4), reward=1 与 reward=0 应产出不同 grasp.
    """
    result_no_reward = _teach_then_query(
        db_path=tmp_path / "grasp_anchor_zero.sqlite",
        session_id="grasp-anchor-zero",
        reward_mag=0.0,
        punish_mag=0.0,
    )
    result_reward = _teach_then_query(
        db_path=tmp_path / "grasp_anchor_reward.sqlite",
        session_id="grasp-anchor-reward",
        reward_mag=1.0,
        punish_mag=0.0,
    )
    b_zero = _first_structural_b(result_no_reward)
    b_reward = _first_structural_b(result_reward)

    assert b_zero is not None and b_reward is not None
    # 结构相似度层面: 两者接近(同一 query 同一源)
    assert abs(float(b_zero["support"]) - float(b_reward["support"])) < 0.15
    # 但 audit_slot 里的 grasp 因结果不同而不同
    grasp_zero = None
    grasp_reward = None
    for slot in b_zero.get("candidate_audit_slots", ()):
        if slot.get("formula_id") == FORMULA_ID:
            grasp_zero = float(slot.get("generalization_grasp", 0.0))
    for slot in b_reward.get("candidate_audit_slots", ()):
        if slot.get("formula_id") == FORMULA_ID:
            grasp_reward = float(slot.get("generalization_grasp", 0.0))
    assert grasp_zero is not None and grasp_reward is not None
    assert grasp_zero < grasp_reward


def test_phase20_9j_grasp_punished_generalization_grasp_below_floor(tmp_path: Path) -> None:
    """纯惩罚(reward=0, punish=1)时 grasp 应低于底噪, 保守退缩."""
    result = _teach_then_query(
        db_path=tmp_path / "grasp_punish.sqlite",
        session_id="grasp-punish",
        reward_mag=0.0,
        punish_mag=1.0,
    )
    b = _first_structural_b(result)
    trace = _first_write_drive_trace(result)
    # 惩罚后泛化候选可能不过阈值(structural_b is None)或过但 grasp 极低
    if b is not None and trace is not None:
        assert float(trace["generalization_grasp"]) < 0.34
        assert trace["writes_answer_directly"] is False
    # 无论候选是否形成, 不应直接写出"谢谢"作为确定答案
    assert _u(result.reply_text) != _u("谢谢") or b is None


def test_phase20_9j_grasp_gating_does_not_claim_convergence_or_completion(tmp_path: Path) -> None:
    """红线: grasp 门控不引入"学成/收敛"布尔断言, 保持连续投影."""
    result = _teach_then_query(
        db_path=tmp_path / "grasp_redline.sqlite",
        session_id="grasp-redline",
        reward_mag=1.0,
        punish_mag=0.0,
    )
    trace = _first_write_drive_trace(result)
    assert trace is not None
    # 禁用串: grasp 是连续值, 不声称学成
    forbidden = (
        "generalization_converged",
        "generalization_complete",
        "grasp_converged",
        "grasp_complete",
        "scene_learned_complete",
    )
    for token in forbidden:
        assert token not in str(trace)
