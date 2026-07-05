from __future__ import annotations

import tempfile
from pathlib import Path

from apv3test.runtime.phase20_7 import run_phase20_7_turn
from apv3test.runtime.phase20_7.runtime import _innate_rules_audit


def test_phase20_7za_innate_rules_audit_returns_explicit_dna() -> None:
    """§29 先天编码: InnateRule=(condition,effect,strength,decay,source) 显式可审计.

    白皮书 §29.3: AP的DNA不直接给答案, 规定哪些状态产生哪些感受/奖惩/行动倾向.
    """
    audit = _innate_rules_audit()
    assert audit["schema_id"] == "apv3_innate_rules_audit/v1"
    assert audit["rule_count"] >= 5  # 至少5条核心先天规则
    assert audit["projection_only"] is True  # 纯投影不增实体
    assert audit["may_be_tuned_by_adapter"] is True  # §33未来可调
    for rule in audit["rules"]:
        assert "rule_id" in rule
        assert "condition" in rule
        assert "effect" in rule
        assert "strength" in rule
        assert "decay" in rule
        assert "source" in rule
        # effect 必须是 §29.3 的合法类型
        assert any(eff in rule["effect"] for eff in (
            "feeling_SA", "reward", "punish", "action_bias", "emotion_delta", "attention_bias"
        ))


def test_phase20_7za_innate_rules_not_answer_table() -> None:
    """§29.1 红线: 先天编码不直接给答案. 每条规则是感受/倾向, 不是答案内容."""
    audit = _innate_rules_audit()
    forbidden = ("answer", "result", "solution", "eval", "solver", "计算器")
    for rule in audit["rules"]:
        rule_str = str(rule).lower()
        for token in forbidden:
            assert token not in rule_str, f"先天规则含答案类词 {token}: {rule['rule_id']}"


def test_phase20_7za_innate_rules_emitted_in_turn_result(tmp_path: Path) -> None:
    """集成: turn结果含 innate_rules 审计字段, 小白/审计可看AP的DNA."""
    db_path = tmp_path / "innate.sqlite"
    result = run_phase20_7_turn(
        user_text="嗯",
        session_id="innate-turn",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    ir = result.innate_rules if isinstance(result.innate_rules, dict) else {}
    assert "rules" in ir
    assert ir["rule_count"] >= 5
    # to_dict 也能输出
    result_dict = result.to_dict()
    assert "innate_rules" in result_dict
    assert result_dict["innate_rules"]["rule_count"] >= 5


def test_phase20_7za_innate_rules_no_forbidden_convergence() -> None:
    """红线: 先天编码不声称DNA收敛/完成 (可调, 非固定)."""
    audit = _innate_rules_audit()
    forbidden = ("dna_converged", "innate_complete", "rules_finalized", "dna_complete")
    for token in forbidden:
        assert token not in str(audit).lower()


def test_phase20_7za_innate_rules_cover_core_feelings() -> None:
    """§29.1: 冷启动对惊/违和/奖惩/疲劳/未闭合有反应 — 先天规则覆盖这些核心."""
    audit = _innate_rules_audit()
    effects_str = " ".join(rule["effect"] for rule in audit["rules"]).lower()
    # 至少覆盖 惊/违和/奖惩/疲劳/未闭合 中的4个
    core_covered = sum(1 for key in ("surprise", "dissonance", "reward", "fatigue", "unclosed") if key in effects_str)
    assert core_covered >= 4