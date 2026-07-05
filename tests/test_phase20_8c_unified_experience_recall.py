from __future__ import annotations

from pathlib import Path
import sqlite3

from PIL import Image, ImageDraw

from apv3test.runtime.phase20_7 import MediaInput, TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.experience_log import from_json, is_tombstoned
from apv3test.runtime.phase20_7.experience_recall import (
    ExperienceRecallQuery,
    query_experience_alignment_candidates,
)
from apv3test.runtime.phase20_7.runtime import (
    _input_payload_for_alignment,
    _semantic_text_overlap_with_units,
    _visual_signature_similarity,
)


def _image(path: Path, *, color: tuple[int, int, int]) -> Path:
    image = Image.new("RGB", (72, 72), (8, 8, 8))
    draw = ImageDraw.Draw(image)
    draw.ellipse((10, 8, 48, 50), fill=color)
    draw.rectangle((50, 46, 68, 68), fill=(40, 120, 245))
    image.save(path)
    return path


def test_phase20_8c_candidate_layer_reads_alignment_once_for_text_and_visual(tmp_path: Path) -> None:
    db_path = tmp_path / "recall.sqlite"
    apple = _image(tmp_path / "a.png", color=(230, 40, 35))

    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple)),),
        teacher_feedback=TeacherFeedback(feedback_text="红色苹果", reward_mag=1.0),
        session_id="phase20-8c-candidates",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    with sqlite3.connect(db_path) as conn:
        candidates = query_experience_alignment_candidates(
            conn,
            ExperienceRecallQuery(query_text="苹果"),
            from_json=from_json,
            is_tombstoned=is_tombstoned,
            input_payload_for_alignment=_input_payload_for_alignment,
            semantic_text_overlap_with_units=_semantic_text_overlap_with_units,
            visual_similarity=_visual_signature_similarity,
        )

    assert candidates
    best = max(candidates, key=lambda item: item.support)
    assert "苹果" in best.output_text
    assert best.text_score > 0
    assert best.text_coverage_units
    assert best.output_chars


def test_phase20_8c_structural_visual_and_imagination_paths_share_candidate_layer(tmp_path: Path) -> None:
    db_path = tmp_path / "recall.sqlite"
    apple = _image(tmp_path / "apple.png", color=(230, 40, 35))
    banana = _image(tmp_path / "banana.png", color=(240, 220, 40))

    run_phase20_7_turn(
        user_text="你好啊",
        teacher_feedback=TeacherFeedback(feedback_text="你也好", reward_mag=1.0),
        session_id="phase20-8c-text-seed",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )
    structural = run_phase20_7_turn(
        user_text="你好呀",
        session_id="phase20-8c-text-structural",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple)),),
        teacher_feedback=TeacherFeedback(feedback_text="红色苹果", reward_mag=1.0),
        session_id="phase20-8c-vision-seed-a",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(banana)),),
        teacher_feedback=TeacherFeedback(feedback_text="黄色香蕉", reward_mag=1.0),
        session_id="phase20-8c-vision-seed-b",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    imagined = run_phase20_7_turn(
        user_text="黄色苹果",
        session_id="phase20-8c-imagined",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    visual_recall = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple)),),
        session_id="phase20-8c-visual-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    assert any(event.b_candidates and event.b_candidates[0]["kind"] == "structural_b" for event in structural.tick_trace)
    assert any(event.selected_action.get("action_type") == "visual_imagination_recall" for event in imagined.tick_trace)
    assert visual_recall.reply_text == "红色苹果"
    assert any(
        row.get("selected_source_kind") == "remembered_visual_alignment"
        for event in imagined.tick_trace
        for row in event.c_backward
    )
