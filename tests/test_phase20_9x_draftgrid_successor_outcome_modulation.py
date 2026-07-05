from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_9x_draftgrid_successor_action_outcome_modulation/v1"


def _events_with_action(result, action_type: str):
    return [event for event in result.tick_trace if event.selected_action.get("action_type") == action_type]


def _successor_modulation_from_continue_event(result) -> dict:
    for event in _events_with_action(result, "continue_writing"):
        selection = event.selected_action.get("draftgrid_next_action_selection", {})
        modulation = selection.get("successor_action_outcome_modulation", {}) if isinstance(selection, dict) else {}
        if isinstance(modulation, dict) and modulation.get("formula_id") == FORMULA_ID:
            return modulation
    raise AssertionError("phase20.9x successor outcome modulation not found")


def _candidate_row(result, action_type: str) -> dict:
    for event in _events_with_action(result, "continue_writing"):
        selection = event.selected_action.get("draftgrid_next_action_selection", {})
        if not isinstance(selection, dict):
            continue
        for row in selection.get("candidate_rows", ()):
            if row.get("action_type") == action_type:
                return dict(row)
    raise AssertionError(f"candidate row not found: {action_type}")


def _seed_successor_history(
    *,
    db_path: Path,
    session_id: str,
    prefix: str,
    long_reward: float,
    long_punish: float,
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
    long_result = run_phase20_7_turn(
        user_text=long_prompt,
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert long_result.reply_text == long_reply

    run_phase20_7_turn(
        user_text=first_prompt,
        teacher_feedback=TeacherFeedback(feedback_text=first_reply, reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )


def test_phase20_9x_rewarded_successor_biases_continue_and_commit(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9x_reward.sqlite"
    session_id = "phase20-9x-reward"
    prefix = "phase20.9x rewarded successor"
    _seed_successor_history(
        db_path=db_path,
        session_id=session_id,
        prefix=prefix,
        long_reward=1.0,
        long_punish=0.0,
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
    continue_row = _candidate_row(result, "continue_writing")
    commit_row = _candidate_row(result, "commit_reply")

    assert result.reply_text == "alpha first fragment beta successor fragment"
    assert modulation["reward"] == 1.0
    assert modulation["punish"] == 0.0
    assert modulation["continue_writing_delta"] > 0.18
    assert modulation["commit_reply_delta"] > 0.09
    assert modulation["read_draft_delta"] < 0.0
    assert modulation["stop_generating_delta"] < 0.0
    assert continue_row["successor_action_outcome_modulation"]["formula_id"] == FORMULA_ID
    assert commit_row["successor_action_outcome_modulation"]["formula_id"] == FORMULA_ID
    assert modulation["writes_answer_directly"] is False
    assert modulation["creates_reply_candidate"] is False


def test_phase20_9x_punished_successor_biases_read_edit_stop_and_suppresses_commit(tmp_path: Path) -> None:
    """P0-1 (2026-07-02) 更新: punish 主导的教学是 counter_evidence, 不再可召回.

    旧断言要求被惩罚的 long_reply 仍被完整复述 (reply == long_reply) 再由 9x 调制
    压 commit — 那正是 E4/C21 "惩罚文本变答案"红线 (审查探针4实证). 现在的合规
    行为: punish 主导教学不进 exact_b0_index, 问 long_prompt 得到诚实的未知回复;
    问 first_prompt 得到 reward 教的 first_reply, 且不会续写出被惩罚的 long_reply.
    """
    db_path = tmp_path / "phase20_9x_punish.sqlite"
    session_id = "phase20-9x-punish"
    prefix = "phase20.9x punished successor"
    long_prompt = f"{prefix} long source prompt"
    first_prompt = f"{prefix} first fragment prompt"
    long_reply = "alpha first fragment beta successor fragment"
    first_reply = "alpha first fragment"

    # punish 主导教学: 记为 counter_evidence, 不可召回
    run_phase20_7_turn(
        user_text=long_prompt,
        teacher_feedback=TeacherFeedback(feedback_text=long_reply, reward_mag=0.0, punish_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    punished_recall = run_phase20_7_turn(
        user_text=long_prompt,
        session_id=session_id,
        db_path=db_path,
        max_ticks=128,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    # 红线: 被惩罚的文本绝不作为答案复述
    assert punished_recall.reply_text != long_reply

    # reward 教学 first_reply 仍正常可召回
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
    assert result.reply_text == first_reply
    # 不续写出被惩罚的后继片段
    assert "beta successor fragment" not in result.reply_text

    # exact_b0_index 无被惩罚文本行 (P0-1 索引门)
    import json as _json
    import sqlite3 as _sqlite3

    with _sqlite3.connect(db_path) as conn:
        outputs = [
            "".join(_json.loads(str(row[0])))
            for row in conn.execute("SELECT output_json FROM phase20_7_exact_b0_index").fetchall()
        ]
    assert long_reply not in outputs
