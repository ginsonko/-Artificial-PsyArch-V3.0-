from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import (
    TeacherFeedback,
    list_active_unclosed_items,
    run_phase20_7_turn,
)


def test_stage4_unknown_input_creates_unclosed_item_and_request_teacher_action(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"

    result = run_phase20_7_turn(
        user_text="猫是什么",
        session_id="stage4-unknown",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    active = list_active_unclosed_items(db_path)

    assert result.stage_id == "20.7-stage4"
    assert result.reply_text == "不太会,教教"
    assert active
    assert active[0]["source_text"] == "猫是什么"
    assert active[0]["u_value"] > 0
    assert any(event.selected_action.get("action_type") == "request_teacher" for event in result.tick_trace)
    assert any(event.unclosed_items for event in result.tick_trace)


def test_stage4_repeated_unknown_maintains_unclosed_instead_of_reasking(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    run_phase20_7_turn(
        user_text="猫是什么",
        session_id="stage4-first",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    second = run_phase20_7_turn(
        user_text="猫是什么",
        session_id="stage4-second",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    active = list_active_unclosed_items(db_path)

    assert second.reply_text == "不太会,教教"
    assert any(event.selected_action.get("action_type") == "maintain_unclosed" for event in second.tick_trace)
    assert active[0]["attempt_count"] >= 2


def test_stage4_idle_think_recalls_active_unclosed_without_committing_reply(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    run_phase20_7_turn(
        user_text="猫是什么",
        session_id="stage4-idle",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    idle = run_phase20_7_turn(
        user_text="",
        session_id="stage4-idle",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    event = idle.tick_trace[0]

    assert idle.committed is False
    assert idle.reply_text == ""
    assert event.selected_action["action_type"] == "idle_think"
    assert event.tick > 1
    assert event.unclosed_items
    assert event.unclosed_items[0]["source_text"] == "猫是什么"
    assert event.feelings["unclosed_pull"] > 0
    assert event.feelings["narrative_text"]


def test_stage4_idle_does_not_pull_unclosed_from_other_session(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    run_phase20_7_turn(
        user_text="猫是什么",
        session_id="stage4-other-session",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    idle = run_phase20_7_turn(
        user_text="",
        session_id="stage4-clean-session",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    assert idle.tick_trace[0].selected_action["action_type"] == "idle_observe"
    assert idle.tick_trace[0].unclosed_items == ()


def test_stage4_teacher_feedback_resolves_matching_unclosed_item(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    run_phase20_7_turn(
        user_text="猫是什么",
        session_id="stage4-unknown",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    learned = run_phase20_7_turn(
        user_text="猫是什么",
        teacher_feedback=TeacherFeedback(feedback_text="猫是一种动物", reward_mag=1.0),
        session_id="stage4-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    recalled = run_phase20_7_turn(
        user_text="猫是什么",
        session_id="stage4-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    assert learned.reply_text == "嗯,记下了。"
    assert list_active_unclosed_items(db_path) == ()
    assert recalled.reply_text == "猫是一种动物"
