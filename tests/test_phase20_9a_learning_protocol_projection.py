from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from apv3test.runtime.phase20_7 import MediaInput, TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.cognitive_cycle import PHASE20_9A_LEARNING_PROTOCOL_PROJECTION_ID


def _image(path: Path) -> Path:
    image = Image.new("RGB", (72, 72), (8, 8, 8))
    draw = ImageDraw.Draw(image)
    draw.ellipse((16, 16, 54, 56), fill=(230, 40, 35))
    image.save(path)
    return path


def _projection(event) -> dict:
    matches = [
        dict(delta)
        for delta in event.learning_deltas
        if delta.get("delta_kind") == "learning_protocol_projection"
        and delta.get("formula_id") == PHASE20_9A_LEARNING_PROTOCOL_PROJECTION_ID
    ]
    assert len(matches) == 1
    return matches[0]


def _event_with_action(result, action_type: str):
    for event in result.tick_trace:
        if event.selected_action.get("action_type") == action_type:
            return event
    raise AssertionError(f"event not found: {action_type}")


def test_phase20_9a_unknown_request_projects_weak_scaffold_without_fake_answer(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9a unknown",
        session_id="phase20-9a-unknown",
        db_path=tmp_path / "phase20_9a.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "request_teacher")
    projection = _projection(event)

    assert projection["current_protocol_stage"] == "weak_scaffold"
    assert projection["stage_scores"]["weak_scaffold"] > 0.5
    assert projection["evidence"]["request_scaffold_signal"] > 0.0
    assert projection["projection_only"] is True
    assert projection["creates_reply_candidate"] is False
    assert projection["writes_answer_directly"] is False
    assert not event.b_candidates


def test_phase20_9a_teacher_feedback_projects_strong_scaffold(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9a teach prompt",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9a taught reply", reward_mag=1.0),
        session_id="phase20-9a-teach",
        db_path=tmp_path / "phase20_9a.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = _event_with_action(result, "integrate_feedback")
    projection = _projection(event)

    assert projection["current_protocol_stage"] == "strong_scaffold"
    assert projection["evidence"]["teacher_signal"] == 1.0
    assert projection["stage_scores"]["strong_scaffold"] > projection["stage_scores"]["feedback_only"]
    assert any(delta.get("delta_kind") == "experience_alignment_written" for delta in event.learning_deltas)
    assert projection["writes_answer_directly"] is False


def test_phase20_9a_exact_recall_projects_teacher_off(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_9a.sqlite"
    run_phase20_7_turn(
        user_text="phase20.9a exact cue",
        teacher_feedback=TeacherFeedback(feedback_text="phase20.9a exact reply", reward_mag=1.0),
        session_id="phase20-9a-exact-learn",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    result = run_phase20_7_turn(
        user_text="phase20.9a exact cue",
        session_id="phase20-9a-exact-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )

    event = next(event for event in result.tick_trace if event.b_candidates)
    projection = _projection(event)

    assert event.b_candidates[0]["kind"] == "exact_b0"
    assert projection["current_protocol_stage"] == "teacher_off"
    assert projection["evidence"]["teacher_signal"] == 0.0
    assert projection["evidence"]["b_candidate_count"] >= 1
    assert projection["stage_scores"]["teacher_off"] > 0.0
    assert projection["writes_answer_directly"] is False


def test_phase20_9a_visual_observation_projects_demonstrate(tmp_path: Path) -> None:
    image_path = _image(tmp_path / "phase20_9a_visual.png")
    result = run_phase20_7_turn(
        user_text="",
        media_inputs=(MediaInput(media_type="image", path=str(image_path)),),
        session_id="phase20-9a-visual",
        db_path=tmp_path / "phase20_9a.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage5",
    )

    event = _event_with_action(result, "move_focus")
    projection = _projection(event)

    assert projection["current_protocol_stage"] == "demonstrate"
    assert projection["evidence"]["receptor_signal"] > 0.0
    assert projection["evidence"]["selected_action"] == "move_focus"
    assert projection["writes_answer_directly"] is False


def test_phase20_9a_stage0_keeps_no_learning_protocol_projection(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="phase20.9a boundary",
        session_id="phase20-9a-stage0",
        db_path=tmp_path / "phase20_9a.sqlite",
        runtime_stage="stage0",
    )

    event = result.tick_trace[0]
    assert result.stage_id == "20.7-stage0"
    assert event.no_write_reason == "stage0_does_not_write_experience_events"
    assert not event.learning_deltas
