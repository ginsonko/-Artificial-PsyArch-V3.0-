from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from apv3test.runtime.phase20_7 import MediaInput, TeacherFeedback, run_phase20_7_turn


def _image(path: Path) -> Path:
    image = Image.new("RGB", (64, 64), (8, 8, 8))
    draw = ImageDraw.Draw(image)
    draw.ellipse((10, 8, 44, 46), fill=(230, 40, 35))
    draw.rectangle((42, 42, 60, 60), fill=(250, 210, 40))
    image.save(path)
    return path


def _assert_completed_cycle(result) -> None:
    assert result.stage_id != "20.7-stage0"
    assert result.tick_trace
    for event in result.tick_trace:
        assert event.c_forward, event.selected_action
        assert event.c_backward, event.selected_action
        assert event.cstar_packet.get("kind") in {"every_tick_min_error_cycle", "bccstar_stage3_packet"}
        assert event.cstar_packet.get("completed_by")
        assert event.cstar_packet.get("prediction_count", len(event.c_forward)) >= 1
        assert event.cstar_packet.get("attribution_count", len(event.c_backward)) >= 1


def test_phase20_8b_text_unknown_has_cycle_without_fake_b_candidate(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="你是谁",
        session_id="phase20-8b-unknown",
        db_path=tmp_path / "cycle.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    assert result.reply_text == "不太会,教教"
    assert not any(event.b_candidates for event in result.tick_trace)
    _assert_completed_cycle(result)
    assert any(event.cstar_packet.get("tick_evidence_b") for event in result.tick_trace)


def test_phase20_8b_visual_audio_idle_and_tts_ticks_share_cycle(tmp_path: Path) -> None:
    db_path = tmp_path / "cycle.sqlite"
    image_path = _image(tmp_path / "visual.png")

    learned = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(image_path)),),
        teacher_feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0),
        session_id="phase20-8b-multimodal",
        db_path=db_path,
        post_commit_idle_ticks=1,
        runtime_stage="stage6",
    )
    recalled = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(image_path)),),
        session_id="phase20-8b-multimodal",
        db_path=db_path,
        post_commit_idle_ticks=1,
        runtime_stage="stage6",
    )
    idle = run_phase20_7_turn(
        user_text="",
        session_id="phase20-8b-multimodal",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    _assert_completed_cycle(learned)
    _assert_completed_cycle(recalled)
    _assert_completed_cycle(idle)
    assert any(event.selected_action.get("action_type") in {"move_focus", "maintain_focus"} for event in recalled.tick_trace)
    assert any(event.selected_action.get("action_type") == "reply_tts_audio" for event in recalled.tick_trace)
    assert idle.tick_trace[0].selected_action.get("action_type") in {"idle_visual_focus", "idle_audio_focus", "idle_think", "idle_observe"}


def test_phase20_8b_stage0_boundary_is_not_reclassified_as_cognitive_tick(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="你好",
        session_id="phase20-8b-stage0",
        db_path=tmp_path / "cycle.sqlite",
        runtime_stage="stage0",
    )

    assert result.stage_id == "20.7-stage0"
    event = result.tick_trace[0]
    assert event.no_write_reason == "stage0_does_not_write_experience_events"
    assert not event.c_forward
    assert not event.c_backward
    assert not event.cstar_packet
