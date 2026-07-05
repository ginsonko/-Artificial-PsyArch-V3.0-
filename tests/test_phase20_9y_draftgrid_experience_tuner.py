from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


OUTCOME_FORMULA_ID = "apv3_phase20_9x_draftgrid_successor_action_outcome_modulation/v1"
TUNER_FORMULA_ID = "apv3_phase20_9y_draftgrid_experience_tuner_projection/v1"


def _events_with_action(result, action_type: str):
    return [event for event in result.tick_trace if event.selected_action.get("action_type") == action_type]


def _successor_modulation_from_continue_event(result) -> dict:
    for event in _events_with_action(result, "continue_writing"):
        selection = event.selected_action.get("draftgrid_next_action_selection", {})
        modulation = selection.get("successor_action_outcome_modulation", {}) if isinstance(selection, dict) else {}
        if isinstance(modulation, dict) and modulation.get("formula_id") == OUTCOME_FORMULA_ID:
            return modulation
    raise AssertionError("phase20.9y successor modulation not found")


def _seed_successor_history(
    *,
    db_path: Path,
    session_id: str,
    prefix: str,
    long_reward: float,
    long_punish: float,
    replay_count: int = 1,
) -> None:
    long_prompt = f"{prefix} long source prompt"
    first_prompt = f"{prefix} first fragment prompt"
    long_reply = "alpha first fragment beta successor fragment"
    first_reply = "alpha first fragment"

    run_phase20_7_turn(
        user_text=long_prompt,
        teacher_feedback=TeacherFeedback(feedback_text=long_reply, reward_mag=long_reward, punish_mag=long_punish),
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    for _ in range(max(1, int(replay_count))):
        result = run_phase20_7_turn(
            user_text=long_prompt,
            session_id=session_id,
            db_path=db_path,
            max_ticks=128,
            post_commit_idle_ticks=0,
            runtime_stage="stage6",
        )
        assert result.reply_text == long_reply

    run_phase20_7_turn(
        user_text=first_prompt,
        teacher_feedback=TeacherFeedback(feedback_text=first_reply, reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )


def test_phase20_9y_rewarded_history_projects_more_boldness(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9y_reward.sqlite"
    session_id = "phase20-9y-reward"
    prefix = "phase20.9y rewarded tuner"
    _seed_successor_history(
        db_path=db_path,
        session_id=session_id,
        prefix=prefix,
        long_reward=1.0,
        long_punish=0.0,
        replay_count=2,
    )

    result = run_phase20_7_turn(
        user_text=f"{prefix} first fragment prompt",
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    modulation = _successor_modulation_from_continue_event(result)
    tuner = modulation["experience_tuner_projection"]

    assert result.reply_text == "alpha first fragment beta successor fragment"
    assert tuner["formula_id"] == TUNER_FORMULA_ID
    assert tuner["active"] is True
    assert tuner["projection_only"] is True
    assert tuner["reward_total"] > 0.0
    assert tuner["boldness_multiplier"] > 1.0
    assert modulation["continue_writing_delta"] > modulation["base_continue_writing_delta"]
    assert modulation["commit_reply_delta"] > modulation["base_commit_reply_delta"]
    assert modulation["writes_answer_directly"] is False
    assert modulation["creates_reply_candidate"] is False
    assert tuner["writes_answer_directly"] is False
    assert tuner["creates_reply_candidate"] is False


def test_phase20_9y_punished_history_projects_caution_and_fatigue(tmp_path: Path) -> None:
    """P0-1 (2026-07-02) 更新: punish 主导教学是 counter_evidence 不可召回.

    旧种子直接用 punish=1.0 教 long_reply 且断言它仍被复述 — 触 E4/C21 红线.
    合规的"被惩罚历史"种子: 先 reward 教学(可召回), 复述一次后再对该输出 punish.
    此后 9y tuner 对该输出 hash 的 punish_total>0, 投影 caution/verification 乘子;
    且被惩罚的后继不再被复述 (9j counter 通道收紧泛化).
    """
    db_path = tmp_path / "phase20_9y_punish.sqlite"
    session_id = "phase20-9y-punish"
    prefix = "phase20.9y punished tuner"
    long_prompt = f"{prefix} long source prompt"
    first_prompt = f"{prefix} first fragment prompt"
    long_reply = "alpha first fragment beta successor fragment"
    first_reply = "alpha first fragment"

    # 先 reward 教学 → 可召回
    run_phase20_7_turn(
        user_text=long_prompt,
        teacher_feedback=TeacherFeedback(feedback_text=long_reply, reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    replay = run_phase20_7_turn(
        user_text=long_prompt,
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert replay.reply_text == long_reply
    # 再惩罚该输出 → 经验流留下 punish 记录 (9y punish_total 的数据源)
    run_phase20_7_turn(
        user_text=long_prompt,
        teacher_feedback=TeacherFeedback(feedback_text=long_reply, reward_mag=0.0, punish_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    run_phase20_7_turn(
        user_text=first_prompt,
        teacher_feedback=TeacherFeedback(feedback_text=first_reply, reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    result = run_phase20_7_turn(
        user_text=first_prompt,
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    # 惩罚后的谨慎: exact 教过的 first_reply 被复述, 但被惩罚的后继片段不复现
    assert result.reply_text == first_reply
    assert "beta successor fragment" not in result.reply_text
