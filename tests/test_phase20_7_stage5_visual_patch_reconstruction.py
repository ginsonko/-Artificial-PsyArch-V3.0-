from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from PIL import Image, ImageDraw

from apv3test.runtime.phase20_7 import MediaInput, TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.experience_log import from_json


def _make_salient_image(path: Path, *, primary: tuple[int, int, int] = (240, 30, 30)) -> Path:
    image = Image.new("RGB", (72, 72), (8, 8, 8))
    draw = ImageDraw.Draw(image)
    draw.rectangle((4, 4, 24, 24), fill=primary)
    draw.rectangle((48, 48, 68, 68), fill=(40, 120, 245))
    draw.line((0, 71, 71, 0), fill=(250, 250, 250), width=2)
    image.save(path)
    return path


def _alignment_ids_containing(conn: sqlite3.Connection, text: str) -> set[str]:
    rows = conn.execute(
        """
        SELECT event_id, payload_json
        FROM phase20_7_experience_events
        WHERE event_kind='experience_alignment'
        """
    ).fetchall()
    out: set[str] = set()
    for event_id, payload_json in rows:
        payload = from_json(str(payload_json))
        if not isinstance(payload, dict):
            continue
        output_text = "".join(str(ch) for ch in payload.get("output_chars", ()))
        if text in output_text:
            out.add(str(event_id))
    return out


def _visual_imagination_alignment_ids(result: Any) -> set[str]:
    alignment_ids: set[str] = set()
    for tick in result.tick_trace:
        inner = tick.visual_inner_picture
        if inner and inner.get("source") == "visual_imagination_recall":
            for ref in inner.get("source_alignment_ids", ()):
                alignment_ids.add(str(ref))
    return alignment_ids


def _latest_visual_imagination_patch_refs(result: Any) -> set[str]:
    for tick in reversed(result.tick_trace):
        inner = tick.visual_inner_picture
        if inner and inner.get("source") == "visual_imagination_recall":
            refs = inner.get("borrowed_patch_payload_refs", ())
            return {str(ref) for ref in refs}
    return set()


def test_stage5_visual_patch_ticks_write_payloads_and_inner_picture(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    image_path = _make_salient_image(tmp_path / "visual_input.png")

    result = run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="image", path=str(image_path)),),
        session_id="stage5-vision",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage5",
    )
    visual_events = [event for event in result.tick_trace if event.visual_inner_picture]

    assert result.stage_id == "20.7-stage5"
    assert result.committed is True
    assert result.reply_text == "不太会,教教"
    assert len(visual_events) >= 2
    assert all(event.selected_action["action_type"] in {"move_focus", "maintain_focus"} for event in visual_events)
    assert all(event.experience_event_ids_written for event in visual_events)
    for event in visual_events:
        inner_path = Path(str(event.visual_inner_picture["path"]))
        assert inner_path.exists()
        assert max(Image.open(inner_path).convert("RGB").getextrema()[0]) > 0
        assert event.visual_inner_picture["rendered_from_state_pool_canvas"] is True
        assert event.visual_inner_picture["raw_source_asset_used_for_render"] is False

    with sqlite3.connect(db_path) as conn:
        payload_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM phase20_7_payload_blobs
            WHERE payload_kind IN ('visual_patch_payload', 'visual_idle_patch_payload')
            """
        ).fetchone()[0]
        environment_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM phase20_7_payload_blobs
            WHERE payload_kind='visual_environment_frame_payload'
            """
        ).fetchone()[0]
        visual_event_count = conn.execute(
            "SELECT COUNT(*) FROM phase20_7_experience_events WHERE event_kind='visual_patch_sample'"
        ).fetchone()[0]
    assert payload_count == len(visual_events)
    assert environment_count == 0
    assert visual_event_count == len(visual_events)


def test_stage5_focus_moves_and_clarity_accumulates_across_visual_ticks(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    image_path = _make_salient_image(tmp_path / "visual_input.png")

    result = run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="image", path=str(image_path)),),
        session_id="stage5-focus",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage5",
    )
    visual_events = [event for event in result.tick_trace if event.visual_inner_picture]
    focus_points = [tuple(event.selected_action["focus_xy"]) for event in visual_events]
    clarity = [float(event.visual_inner_picture["clarity_coverage"]) for event in visual_events]

    assert len(set(focus_points)) >= 2
    assert clarity[-1] >= clarity[0]
    assert any(item["family"] == "sensory_canvas" for event in visual_events for item in event.state_pool_top)
    assert any(item["family"] == "visual_focus" for event in visual_events for item in event.state_pool_top)


def test_stage5_inner_picture_is_not_raw_source_thumbnail(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    image_path = _make_salient_image(tmp_path / "visual_input.png")

    result = run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="image", path=str(image_path)),),
        session_id="stage5-inner-not-raw",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage5",
    )
    visual_event = next(event for event in result.tick_trace if event.visual_inner_picture)
    source = Image.open(image_path).convert("RGB")
    inner = Image.open(Path(str(visual_event.visual_inner_picture["path"]))).convert("RGB")

    assert inner.size == source.size
    assert inner.tobytes() != source.tobytes()


def test_stage5_visual_path_does_not_use_filename_as_label(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    image_path = _make_salient_image(tmp_path / "apple_banana_demo.png")

    result = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(image_path)),),
        session_id="stage5-no-label",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage5",
    )
    joined_trace = str(result.to_dict()).lower()
    with sqlite3.connect(db_path) as conn:
        payloads = " ".join(row[0] for row in conn.execute("SELECT summary_json FROM phase20_7_payload_blobs"))

    assert "apple" not in joined_trace
    assert "banana" not in joined_trace
    assert "apple" not in payloads.lower()
    assert "banana" not in payloads.lower()
    assert result.reply_text != "apple"
    assert result.reply_text != "banana"


def test_stage5_visual_teaching_binds_to_visual_evidence_not_text_only(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    apple_like = _make_salient_image(tmp_path / "same_question_a.png", primary=(240, 30, 30))
    banana_like = _make_salient_image(tmp_path / "same_question_b.png", primary=(240, 220, 40))

    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0),
        session_id="stage5-visual-teach-a",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    apple_recall = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple_like)),),
        session_id="stage5-visual-recall-a",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    banana_recall_before = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        session_id="stage5-visual-recall-b0",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    assert apple_recall.reply_text == "是苹果"
    assert banana_recall_before.reply_text != "是苹果"
    assert any(
        (tick.query_structures and tick.query_structures[0].get("visual_signature"))
        for tick in apple_recall.tick_trace
    )

    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="是香蕉", reward_mag=1.0),
        session_id="stage5-visual-teach-b",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    apple_recall_after = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple_like)),),
        session_id="stage5-visual-recall-a2",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    banana_recall_after = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        session_id="stage5-visual-recall-b2",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    assert apple_recall_after.reply_text == "是苹果"
    assert banana_recall_after.reply_text == "是香蕉"


def test_stage5_visual_teaching_keeps_same_text_queries_separated_by_backward_neutralization(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    apple_like = _make_salient_image(tmp_path / "same_prompt_apple.png", primary=(240, 30, 30))
    banana_like = _make_salient_image(tmp_path / "same_prompt_banana.png", primary=(240, 220, 40))

    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0),
        session_id="stage5-same-text-a-teach",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="是香蕉", reward_mag=1.0),
        session_id="stage5-same-text-b-teach",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    apple_recall = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple_like)),),
        session_id="stage5-same-text-a-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    banana_recall = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        session_id="stage5-same-text-b-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    assert apple_recall.reply_text == "是苹果"
    assert banana_recall.reply_text == "是香蕉"
    assert any(
        candidate.get("kind") == "every_tick_backward_min_error"
        and candidate.get("modality_mix") == ("text", "vision")
        and candidate.get("cause_grasp", 0) >= 0.68
        for tick in apple_recall.tick_trace
        for candidate in tick.c_backward
    )
    assert any(
        candidate.get("kind") == "every_tick_backward_min_error"
        and candidate.get("modality_mix") == ("text", "vision")
        and candidate.get("cause_grasp", 0) >= 0.68
        for tick in banana_recall.tick_trace
        for candidate in tick.c_backward
    )


def test_stage5_teacher_feedback_without_retyping_binds_previous_visual_question(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    apple_like = _make_salient_image(tmp_path / "natural_teach_visual.png", primary=(240, 30, 30))

    first = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple_like)),),
        session_id="stage5-natural-teach",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert first.reply_text == "不太会,教教"

    taught = run_phase20_7_turn(
        teacher_feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0),
        session_id="stage5-natural-teach",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert taught.reply_text == "嗯,记下了。"

    recall = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple_like)),),
        session_id="stage5-natural-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert recall.reply_text == "是苹果"
    assert any(delta.get("recovered_target") for tick in taught.tick_trace for delta in tick.learning_deltas)


def test_stage5_image_only_teaching_recovers_recent_visual_observation(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    banana_like = _make_salient_image(tmp_path / "image_only_banana.png", primary=(240, 220, 40))

    first = run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        session_id="stage5-image-only",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert first.reply_text == "不太会,教教"

    taught = run_phase20_7_turn(
        teacher_feedback=TeacherFeedback(feedback_text="是香蕉", reward_mag=1.0),
        session_id="stage5-image-only",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert taught.reply_text == "嗯,记下了。"
    assert any(
        delta.get("recovered_target_kind") == "recent_visual"
        for tick in taught.tick_trace
        for delta in tick.learning_deltas
    )

    recall = run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        session_id="stage5-image-only-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert recall.reply_text == "是香蕉"


def test_stage5_text_reference_can_trace_back_to_recent_visual(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    orange_like = _make_salient_image(tmp_path / "recent_visual_orange.png", primary=(40, 220, 80))

    run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="image", path=str(orange_like)),),
        session_id="stage5-reference",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    taught = run_phase20_7_turn(
        user_text="刚刚图片是啥",
        teacher_feedback=TeacherFeedback(feedback_text="绿色橙子", reward_mag=1.0),
        session_id="stage5-reference",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert taught.reply_text == "嗯,记下了。"
    assert any(
        (tick.ssp_active_summary or {}).get("backward_reference") == "experience_window_attribution"
        and (tick.ssp_active_summary or {}).get("selected_source_kind") == "recent_visual_window"
        for tick in taught.tick_trace
    )
    assert any(
        candidate.get("kind") == "every_tick_backward_min_error"
        and candidate.get("selected_source_kind") == "recent_visual_window"
        and candidate.get("cause_grasp", 0) > 0
        for tick in taught.tick_trace
        for candidate in tick.c_backward
    )

    recall = run_phase20_7_turn(
        user_text="这个是什么",
        media_inputs=(MediaInput(media_type="image", path=str(orange_like)),),
        session_id="stage5-reference-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert recall.reply_text == "绿色橙子"


def test_stage5_visual_signature_uses_patch_evidence_not_source_hash(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    image_path = _make_salient_image(tmp_path / "visual_input.png")

    result = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(image_path)),),
        session_id="stage5-no-source-hash-signature",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    visual_signature = next(
        tick.query_structures[0]["visual_signature"]
        for tick in result.tick_trace
        if tick.query_structures and tick.query_structures[0].get("visual_signature")
    )
    assert "visual_patch_evidence::" in visual_signature
    assert "image::" not in visual_signature
    assert "focus::" not in visual_signature


def test_stage5_idle_visual_focus_continues_sampling_without_new_image_input(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    image_path = _make_salient_image(tmp_path / "visual_idle_input.png")

    first = run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="image", path=str(image_path)),),
        session_id="stage5-idle-vision",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    idle = run_phase20_7_turn(
        user_text="",
        session_id="stage5-idle-vision",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    first_visual = [event for event in first.tick_trace if event.visual_inner_picture]
    idle_event = idle.tick_trace[0]
    assert idle_event.selected_action["action_type"] == "idle_visual_focus"
    assert idle_event.visual_inner_picture
    assert idle_event.visual_inner_picture["rendered_from_state_pool_canvas"] is True
    assert idle_event.visual_inner_picture["raw_source_asset_used_for_render"] is False
    assert float(idle_event.visual_inner_picture["clarity_coverage"]) > 0
    assert float(idle_event.visual_inner_picture["clarity_coverage"]) <= float(first_visual[-1].visual_inner_picture["clarity_coverage"])
    assert idle_event.ssp_active_summary["focus_trace"]["basis"] == "known_patch_saliency_plus_clarity_gap"
    assert any(row.get("action_type") == "idle_visual_focus" and row.get("selected") for row in idle_event.action_competition)
    assert idle_event.c_forward and idle_event.c_backward

    with sqlite3.connect(db_path) as conn:
        idle_events = conn.execute(
            "SELECT COUNT(*) FROM phase20_7_experience_events WHERE event_kind='visual_patch_sample' AND json_extract(payload_json, '$.idle_continuation')=1"
        ).fetchone()[0]
        inner_rehearsal = conn.execute(
            "SELECT COUNT(*) FROM phase20_7_experience_events WHERE event_kind='audio_inner_rehearsal'"
        ).fetchone()[0]
    assert idle_events == 1
    assert inner_rehearsal == 0


def test_stage5_text_can_recall_visual_inner_picture_from_experience_flow(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    apple_like = _make_salient_image(tmp_path / "visual_memory_apple.png", primary=(240, 30, 30))
    banana_like = _make_salient_image(tmp_path / "visual_memory_banana.png", primary=(240, 220, 40))

    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="是红色苹果", reward_mag=1.0),
        session_id="stage5-imagine-teach-apple",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="是黄色香蕉", reward_mag=1.0),
        session_id="stage5-imagine-teach-banana",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    imagined = run_phase20_7_turn(
        user_text="苹果",
        session_id="stage5-imagine-text-apple",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    imagination_ticks = [
        tick
        for tick in imagined.tick_trace
        if tick.selected_action.get("action_type") == "visual_imagination_recall"
    ]

    assert imagination_ticks
    inner = imagination_ticks[-1].visual_inner_picture
    assert inner is not None
    assert inner["source"] == "visual_imagination_recall"
    assert inner["epistemic_source"] == "IMAGINED_FROM_EXPERIENCE_FLOW"
    assert inner["raw_source_asset_used_for_render"] is False
    assert int(inner["borrowed_patch_payload_count"]) > 0
    assert Path(str(inner["path"])).exists()
    assert any(
        row.get("selected_source_kind") == "remembered_visual_alignment"
        for tick in imagined.tick_trace
        for row in tick.c_backward
    )

    with sqlite3.connect(db_path) as conn:
        environment_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM phase20_7_payload_blobs
            WHERE payload_kind='visual_environment_frame_payload'
            """
        ).fetchone()[0]
        imagined_event_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM phase20_7_experience_events
            WHERE event_kind='visual_imagination_recall'
            """
        ).fetchone()[0]
    assert environment_count == 0
    assert imagined_event_count >= 1


def test_stage5_text_visual_imagination_is_not_the_last_seen_image(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    apple_like = _make_salient_image(tmp_path / "memory_source_a.png", primary=(240, 30, 30))
    banana_like = _make_salient_image(tmp_path / "memory_source_b.png", primary=(240, 220, 40))

    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="是红色苹果", reward_mag=1.0),
        session_id="stage5-last-image-teach-apple",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="是黄色香蕉", reward_mag=1.0),
        session_id="stage5-last-image-teach-banana",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        session_id="stage5-last-image-current-banana",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    with sqlite3.connect(db_path) as conn:
        apple_alignment_ids = _alignment_ids_containing(conn, "苹果")
        banana_alignment_ids = _alignment_ids_containing(conn, "香蕉")

    imagined = run_phase20_7_turn(
        user_text="苹果",
        session_id="stage5-last-image-query-apple",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    recalled_alignment_ids = _visual_imagination_alignment_ids(imagined)

    assert recalled_alignment_ids
    assert recalled_alignment_ids & apple_alignment_ids
    assert not (recalled_alignment_ids & banana_alignment_ids)
    assert any(
        tick.visual_inner_picture
        and tick.visual_inner_picture.get("source") == "visual_imagination_recall"
        and tick.visual_inner_picture.get("raw_source_asset_used_for_render") is False
        for tick in imagined.tick_trace
    )


def test_stage5_idle_visual_focus_follows_latest_visual_imagination_not_last_image(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    apple_like = _make_salient_image(tmp_path / "idle_memory_a.png", primary=(240, 30, 30))
    banana_like = _make_salient_image(tmp_path / "idle_memory_b.png", primary=(240, 220, 40))

    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="是红色苹果", reward_mag=1.0),
        session_id="stage5-idle-imagination-flow",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="是黄色香蕉", reward_mag=1.0),
        session_id="stage5-idle-imagination-flow",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    imagined = run_phase20_7_turn(
        user_text="苹果",
        session_id="stage5-idle-imagination-flow",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    imagined_refs = _latest_visual_imagination_patch_refs(imagined)
    assert imagined_refs

    idle = run_phase20_7_turn(
        user_text="",
        session_id="stage5-idle-imagination-flow",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert idle.tick_trace
    idle_event = idle.tick_trace[0]
    assert idle_event.selected_action["action_type"] == "idle_visual_focus"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT payload_json
            FROM phase20_7_experience_events
            WHERE session_id=? AND event_kind='visual_patch_sample'
              AND json_extract(payload_json, '$.idle_continuation')=1
            ORDER BY tick DESC, created_at_ms DESC
            LIMIT 1
            """,
            ("stage5-idle-imagination-flow",),
        ).fetchone()
    assert row is not None
    payload = from_json(str(row[0]))
    assert isinstance(payload, dict)
    idle_refs = {str(ref) for ref in payload.get("reconstructed_from_payload_refs", ())}
    assert idle_refs
    assert idle_refs <= imagined_refs


def test_stage5_mixed_text_can_borrow_multiple_visual_experience_sources(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    apple_like = _make_salient_image(tmp_path / "mixed_memory_a.png", primary=(240, 30, 30))
    banana_like = _make_salient_image(tmp_path / "mixed_memory_b.png", primary=(240, 220, 40))

    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="红色苹果", reward_mag=1.0),
        session_id="stage5-mixed-teach-apple",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="黄色香蕉", reward_mag=1.0),
        session_id="stage5-mixed-teach-banana",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    imagined = run_phase20_7_turn(
        user_text="黄色苹果",
        session_id="stage5-mixed-query-yellow-apple",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    imagination_ticks = [
        tick
        for tick in imagined.tick_trace
        if tick.selected_action.get("action_type") == "visual_imagination_recall"
    ]

    assert imagination_ticks
    inner = imagination_ticks[-1].visual_inner_picture
    assert inner is not None
    assert int(inner["borrowed_patch_payload_count"]) > 1
    assert len(set(inner["source_alignment_ids"])) >= 2
    assert any(row.get("visual_signature_count", 0) >= 2 for tick in imagined.tick_trace for row in tick.c_backward)
