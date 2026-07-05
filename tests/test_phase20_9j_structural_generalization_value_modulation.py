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


def test_phase20_9j_rewarded_subsequence_can_generalize_without_answer_table(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9j_reward.sqlite"
    session_id = "phase20-9j-reward"

    run_phase20_7_turn(
        user_text="\u6ca1\u9519,\u4f60\u597d\u806a\u660e",
        teacher_feedback=TeacherFeedback(feedback_text="\u8c22\u8c22", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    result = run_phase20_7_turn(
        user_text="\u4f60\u597d\u806a\u660e",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    b = _first_structural_b(result)
    assert _u(result.reply_text) == _u("\u8c22\u8c22")
    assert b is not None
    assert b["support"] >= 0.55
    assert b["shared_unit_count"] == 4
    assert b["residual_unit_count"] == 0
    assert b["support_terms"]["structural_query_coverage"] == 1.0
    assert b["support_terms"]["value_reward_boost"] > 0.0
    assert b["support_terms"]["phase20_9j_formula_active"] == 1.0
    assert any(slot.get("formula_id") == FORMULA_ID for slot in b["candidate_audit_slots"])
    assert any(
        event.cstar_packet.get("writes_answer_directly") is False
        for event in result.tick_trace
        if event.cstar_packet
    )


def test_phase20_9j_action_competition_drive_reads_structural_value_trace(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9j_drive.sqlite"
    session_id = "phase20-9j-drive"

    run_phase20_7_turn(
        user_text="\u6ca1\u9519,\u4f60\u597d\u806a\u660e",
        teacher_feedback=TeacherFeedback(feedback_text="\u8c22\u8c22", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    result = run_phase20_7_turn(
        user_text="\u4f60\u597d\u806a\u660e",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    trace = _first_write_drive_trace(result)
    b = _first_structural_b(result)

    assert _u(result.reply_text) == _u("\u8c22\u8c22")
    assert b is not None
    assert trace is not None
    assert trace["source"] == "structural_b_support_reward_punish_residual"
    assert trace["formula_id"] == FORMULA_ID
    assert trace["reward_delta"] > 0.0
    assert abs(float(trace["support"]) - float(b["support"])) < 0.001
    assert trace["writes_answer_directly"] is False


def test_phase20_9j_far_text_still_requests_teacher_not_memory_leak(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9j_far.sqlite"
    session_id = "phase20-9j-far"

    run_phase20_7_turn(
        user_text="\u6ca1\u9519,\u4f60\u597d\u806a\u660e",
        teacher_feedback=TeacherFeedback(feedback_text="\u8c22\u8c22", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    result = run_phase20_7_turn(
        user_text="\u4f60\u662f\u8c01",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    assert _u(result.reply_text) == _u("\u4e0d\u592a\u4f1a,\u6559\u6559")
    assert _first_structural_b(result) is None
    assert any(event.selected_action.get("action_type") == "request_teacher" for event in result.tick_trace)


def test_phase20_9j_punished_subsequence_returns_to_teacher_request(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9j_punish.sqlite"
    session_id = "phase20-9j-punish"

    run_phase20_7_turn(
        user_text="\u6ca1\u9519,\u4f60\u597d\u806a\u660e",
        teacher_feedback=TeacherFeedback(feedback_text="\u8c22\u8c22", punish_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    result = run_phase20_7_turn(
        user_text="\u4f60\u597d\u806a\u660e",
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    assert _u(result.reply_text) == _u("\u4e0d\u592a\u4f1a,\u6559\u6559")
    assert _first_structural_b(result) is None
    assert any(event.selected_action.get("action_type") == "request_teacher" for event in result.tick_trace)
