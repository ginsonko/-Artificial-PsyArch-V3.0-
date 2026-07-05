from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


def _seed(db_path: Path) -> None:
    run_phase20_7_turn(
        user_text="你好啊",
        teacher_feedback=TeacherFeedback(feedback_text="你也好", reward_mag=1.0),
        session_id="stage3-seed",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )


def test_stage3_structural_b_recalls_near_text_without_exact_signature(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    _seed(db_path)

    result = run_phase20_7_turn(
        user_text="你好呀",
        session_id="stage3-near",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    assert result.stage_id == "20.7-stage3"
    assert result.reply_text == "你也好"
    structural_events = [
        event.to_dict()
        for event in result.tick_trace
        if event.b_candidates and event.b_candidates[0]["kind"] == "structural_b"
    ]
    assert structural_events
    assert structural_events[0]["b_candidates"][0]["support"] >= 0.55
    assert structural_events[0]["c_forward"]
    assert structural_events[0]["c_backward"]
    assert structural_events[0]["cstar_packet"]["writes_answer_directly"] is False


def test_stage3_far_text_still_requests_teacher_instead_of_leaking_memory(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    _seed(db_path)

    result = run_phase20_7_turn(
        user_text="你是谁",
        session_id="stage3-far",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    assert result.reply_text == "不太会,教教"
    assert not any(event.b_candidates for event in result.tick_trace)
    assert any(event.selected_action.get("action_type") == "request_teacher" for event in result.tick_trace)


def test_stage3_exact_b0_still_wins_over_structural_b(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    _seed(db_path)

    result = run_phase20_7_turn(
        user_text="你好啊",
        session_id="stage3-exact",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )
    kinds = [event.b_candidates[0]["kind"] for event in result.tick_trace if event.b_candidates]

    assert result.reply_text == "你也好"
    assert kinds
    assert set(kinds) == {"exact_b0"}


def test_stage3_cstar_virtual_energy_enters_state_pool_trace(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    _seed(db_path)

    result = run_phase20_7_turn(
        user_text="你好呀",
        session_id="stage3-cstar",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )
    top_items = [item for event in result.tick_trace for item in event.to_dict()["state_pool_top"]]

    assert any(item["family"] == "memory_prediction" for item in top_items)
    assert any(float(item["V"]) > 0 for item in top_items if item["family"] == "memory_prediction")
