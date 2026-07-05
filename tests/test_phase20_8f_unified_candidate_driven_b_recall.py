from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from apv3test.runtime.phase20_7 import MediaInput, TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.experience_candidate import UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID


def _image(path: Path, *, primary: tuple[int, int, int] = (230, 40, 35)) -> Path:
    image = Image.new("RGB", (72, 72), (8, 8, 8))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 6, 48, 50), fill=primary)
    draw.rectangle((48, 46, 68, 68), fill=(40, 120, 245))
    image.save(path)
    return path


def _cause_slots(result: Any) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for tick in result.tick_trace:
        for row in tick.c_backward:
            raw_slots = row.get("cause_slots", ())
            if isinstance(raw_slots, (list, tuple)):
                slots.extend(slot for slot in raw_slots if isinstance(slot, dict))
    return slots


def test_phase20_8f_structural_b_is_selected_from_unified_candidate_pool(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8f.sqlite"
    run_phase20_7_turn(
        user_text="hello there",
        teacher_feedback=TeacherFeedback(feedback_text="hi", reward_mag=1.0),
        session_id="phase20-8f-structural-seed",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )

    result = run_phase20_7_turn(
        user_text="hello there!",
        session_id="phase20-8f-structural-query",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )
    structural_ticks = [
        tick for tick in result.tick_trace if tick.b_candidates and tick.b_candidates[0].get("kind") == "structural_b"
    ]

    assert result.reply_text == "hi"
    assert structural_ticks
    candidate = structural_ticks[0].b_candidates[0]
    assert candidate["support_formula"] == UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID
    assert candidate["support_terms"]["structural_sequence_fit"] > 0.55
    assert any(slot.get("slot_kind") == "unified_experience_candidate" for slot in candidate["candidate_audit_slots"])
    assert structural_ticks[0].cstar_packet["support_formula"] == UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID
    assert structural_ticks[0].cstar_packet["unified_candidate_count"] >= 1


def test_phase20_8f_visual_exact_b0_exposes_unified_candidate_cause_slot(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8f.sqlite"
    apple = _image(tmp_path / "apple.png")

    run_phase20_7_turn(
        user_text="what is this",
        media_inputs=(MediaInput(media_type="image", path=str(apple)),),
        teacher_feedback=TeacherFeedback(feedback_text="red apple", reward_mag=1.0),
        session_id="phase20-8f-visual",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    result = run_phase20_7_turn(
        user_text="what is this",
        media_inputs=(MediaInput(media_type="image", path=str(apple)),),
        session_id="phase20-8f-visual",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    assert result.reply_text == "red apple"
    exact_ticks = [
        tick for tick in result.tick_trace if tick.b_candidates and tick.b_candidates[0].get("kind") == "exact_b0"
    ]
    assert exact_ticks
    exact_candidate = exact_ticks[0].b_candidates[0]
    assert exact_candidate["support_formula"] == UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID
    assert exact_candidate["support_terms"]["visual_similarity"] > 0.0
    unified_slots = [slot for slot in _cause_slots(result) if slot.get("slot_kind") == "unified_experience_candidate"]
    assert unified_slots
    assert any(slot.get("candidate_kind") == "experience_alignment" for slot in unified_slots)
