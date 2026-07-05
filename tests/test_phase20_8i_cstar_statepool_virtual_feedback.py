from __future__ import annotations

from pathlib import Path

from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


def _state_items(result) -> list[dict]:
    return [item for event in result.tick_trace for item in event.to_dict()["state_pool_top"]]


def _feedback_traces(result) -> list[dict]:
    traces: list[dict] = []
    for event in result.tick_trace:
        trace = event.feelings.get("cstar_statepool_feedback")
        if isinstance(trace, dict):
            traces.append(trace)
    return traces


def _has_replay_v(item: dict) -> bool:
    ledger = item.get("gain_ledger", {})
    replay = ledger.get("replay", 0.0) if isinstance(ledger, dict) else 0.0
    return float(item.get("V", 0.0) or 0.0) > 0.0 and float(replay or 0.0) > 0.0


def test_phase20_8i_structural_b_cstar_feedback_reaches_statepool_v(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8i.sqlite"
    run_phase20_7_turn(
        user_text="phase20i structural source",
        teacher_feedback=TeacherFeedback(feedback_text="phase20i structural reply", reward_mag=1.0),
        session_id="phase20-8i-structural-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    result = run_phase20_7_turn(
        user_text="phase20i structural source!",
        session_id="phase20-8i-structural-query",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    assert any(event.b_candidates and event.b_candidates[0].get("kind") == "structural_b" for event in result.tick_trace)
    traces = _feedback_traces(result)
    assert any(trace.get("forward_target_count", 0) > 0 for trace in traces)
    assert any(trace.get("backward_target_count", 0) > 0 for trace in traces)
    assert any(item.get("family") == "memory_prediction" and _has_replay_v(item) for item in _state_items(result))


def test_phase20_8i_exact_b0_also_feeds_prediction_sa_without_reply_shortcut(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8i.sqlite"
    run_phase20_7_turn(
        user_text="phase20i hello",
        teacher_feedback=TeacherFeedback(feedback_text="phase20i hi", reward_mag=1.0),
        session_id="phase20-8i-exact-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    result = run_phase20_7_turn(
        user_text="phase20i hello",
        session_id="phase20-8i-exact-query",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    assert result.reply_text == "phase20i hi"
    assert any(event.b_candidates and event.b_candidates[0].get("kind") == "exact_b0" for event in result.tick_trace)
    traces = _feedback_traces(result)
    assert any(trace.get("forward_target_count", 0) > 0 for trace in traces)
    assert all(trace.get("writes_answer_directly") is False for trace in traces)
    assert all(trace.get("creates_reply_candidate") is False for trace in traces)
    assert any(item.get("family") == "memory_prediction" and _has_replay_v(item) for item in _state_items(result))


def test_phase20_8i_unknown_weak_tick_feeds_current_text_sa_without_fake_b(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20i unknown input",
        session_id="phase20-8i-unknown",
        db_path=tmp_path / "phase20_8i.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    assert not any(event.b_candidates for event in result.tick_trace)
    traces = _feedback_traces(result)
    assert any(trace.get("backward_target_count", 0) > 0 for trace in traces)
    assert not any(trace.get("forward_target_count", 0) > 0 for trace in traces)
    assert all(trace.get("creates_reply_candidate") is False for trace in traces)
    assert any(item.get("family") == "text" and _has_replay_v(item) for item in _state_items(result))


def test_phase20_8i_stage0_still_has_no_cstar_statepool_feedback(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20i boundary",
        session_id="phase20-8i-stage0",
        db_path=tmp_path / "phase20_8i.sqlite",
        runtime_stage="stage0",
    )

    event = result.tick_trace[0]
    assert result.stage_id == "20.7-stage0"
    assert event.no_write_reason == "stage0_does_not_write_experience_events"
    assert "cstar_statepool_feedback" not in event.feelings
