from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from apv3test.runtime.phase20_7 import MediaInput, TeacherFeedback, run_phase20_7_turn


FORMULA_ID = "apv3_phase20_8r_current_referent_expression_binding/v1"


def _image(path: Path, *, color: tuple[int, int, int]) -> Path:
    image = Image.new("RGB", (72, 72), (8, 8, 8))
    draw = ImageDraw.Draw(image)
    draw.ellipse((18, 16, 54, 56), fill=color)
    image.save(path)
    return path


def _event_with_action(result, action_type: str):
    for event in result.tick_trace:
        if event.selected_action.get("action_type") == action_type:
            return event
    raise AssertionError(f"event not found: {action_type}")


def _commit_event_id(result) -> str:
    event = _event_with_action(result, "commit_reply")
    assert event.experience_event_ids_written
    return event.experience_event_ids_written[0]


def _compact(text: str) -> str:
    return "".join(str(text).split())


def _teach_visual_expression(
    db_path: Path,
    *,
    session_id: str,
    image_path: Path,
    feedback_text: str,
) -> None:
    seed = run_phase20_7_turn(
        user_text="",
        media_inputs=(MediaInput(media_type="image", path=str(image_path)),),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage5",
    )
    run_phase20_7_turn(
        user_text="",
        teacher_feedback=TeacherFeedback(
            feedback_text=feedback_text,
            reward_mag=1.0,
            target_event_id=_commit_event_id(seed),
        ),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage5",
    )


def _teach_text_expression(
    db_path: Path,
    *,
    session_id: str,
    seed_text: str,
    feedback_text: str,
) -> None:
    seed = run_phase20_7_turn(
        user_text=seed_text,
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    run_phase20_7_turn(
        user_text="",
        teacher_feedback=TeacherFeedback(
            feedback_text=feedback_text,
            reward_mag=1.0,
            target_event_id=_commit_event_id(seed),
        ),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )


def test_phase20_8r_expression_selection_binds_to_current_visual_or_text_referent(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8r.sqlite"
    visual = _image(tmp_path / "referent_visual.png", color=(230, 40, 35))
    _teach_visual_expression(
        db_path,
        session_id="phase20-8r-visual-teach",
        image_path=visual,
        feedback_text="visual unclear",
    )
    _teach_text_expression(
        db_path,
        session_id="phase20-8r-text-teach",
        seed_text="phase20r text seed unknown",
        feedback_text="text unclear",
    )

    visual_result = run_phase20_7_turn(
        user_text="",
        media_inputs=(MediaInput(media_type="image", path=str(visual)),),
        session_id="phase20-8r-visual-query",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage5",
    )
    visual_event = _event_with_action(visual_result, "request_teacher")
    visual_trace = visual_event.ssp_active_summary["request_expression_selection"]

    assert visual_result.reply_text == "visual unclear"
    assert visual_trace["referent_formula_id"] == FORMULA_ID
    assert visual_trace["current_referent"]["referent_kind"] == "visual_focus"
    assert tuple(visual_trace["current_referent"]["modalities"]) == ("vision",)
    assert visual_trace["selected_referent"]["referent_kind"] == "visual_focus"
    assert visual_trace["referent_binding_kind"] == "same_visual_referent"
    assert visual_trace["referent_match"] >= 0.9
    assert visual_trace["creates_answer_candidate"] is False
    assert visual_trace["writes_answer_directly"] is False
    assert not visual_event.b_candidates

    text_result = run_phase20_7_turn(
        user_text="phase20r fresh text query",
        session_id="phase20-8r-text-query",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage4",
    )
    text_event = _event_with_action(text_result, "request_teacher")
    text_trace = text_event.ssp_active_summary["request_expression_selection"]

    assert text_result.reply_text == "text unclear"
    assert text_trace["current_referent"]["referent_kind"] == "text_focus"
    assert tuple(text_trace["current_referent"]["modalities"]) == ("text",)
    assert text_trace["selected_referent"]["referent_kind"] == "text_focus"
    assert text_trace["referent_binding_kind"] == "same_referent_kind"
    assert text_trace["referent_match"] > 0.5
    assert not text_event.b_candidates


def test_phase20_8r_fragment_composition_prefers_same_visual_referent_sources(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8r.sqlite"
    visual = _image(tmp_path / "referent_visual_fragments.png", color=(240, 220, 40))
    _teach_visual_expression(
        db_path,
        session_id="phase20-8r-fragment-a",
        image_path=visual,
        feedback_text="this image",
    )
    _teach_visual_expression(
        db_path,
        session_id="phase20-8r-fragment-b",
        image_path=visual,
        feedback_text="still unclear",
    )

    result = run_phase20_7_turn(
        user_text="",
        media_inputs=(MediaInput(media_type="image", path=str(visual)),),
        session_id="phase20-8r-fragment-query",
        db_path=db_path,
        max_ticks=64,
        post_commit_idle_ticks=0,
        runtime_stage="stage5",
    )

    event = _event_with_action(result, "request_teacher")
    trace = event.ssp_active_summary["request_expression_selection"]

    assert trace["source_kind"] == "expression_fragment_composition"
    assert trace["referent_formula_id"] == FORMULA_ID
    assert trace["referent_binding_kind"] == "fragment_sources_referent_matched"
    assert trace["referent_match"] >= 0.9
    assert trace["fragment_count"] >= 2
    assert "thisimage" in _compact(result.reply_text)
    assert "stillunclear" in _compact(result.reply_text)
    assert not event.b_candidates


def test_phase20_8r_unknown_without_expression_memory_keeps_referent_trace_only(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8r.sqlite"
    visual = _image(tmp_path / "referent_fallback.png", color=(40, 220, 80))

    result = run_phase20_7_turn(
        user_text="",
        media_inputs=(MediaInput(media_type="image", path=str(visual)),),
        session_id="phase20-8r-fallback",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage5",
    )

    event = _event_with_action(result, "request_teacher")
    trace = event.ssp_active_summary["request_expression_selection"]

    assert trace["source_kind"] == "innate_minimal_expression"
    assert trace["referent_formula_id"] == FORMULA_ID
    assert trace["current_referent"]["referent_kind"] == "visual_focus"
    assert trace["selected_referent"] == {}
    assert trace["referent_match"] == 0.0
    assert trace["referent_binding_kind"] == "trace_only_without_learned_expression"
    assert trace["creates_answer_candidate"] is False
    assert trace["writes_answer_directly"] is False
