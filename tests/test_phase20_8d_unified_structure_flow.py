from __future__ import annotations

from pathlib import Path
import sqlite3

from PIL import Image, ImageDraw

from apv3test.runtime.phase20_7 import MediaInput, TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.experience_log import from_json
from apv3test.runtime.phase20_7.experience_flow import query_recent_experience_flow_candidates
from apv3test.runtime.phase20_7.runtime import (
    _compose_input_signature,
    _hash_text,
    _signature_for_chars,
    _visual_signature_from_payloads,
)


def _image(path: Path, *, color: tuple[int, int, int]) -> Path:
    image = Image.new("RGB", (72, 72), (8, 8, 8))
    draw = ImageDraw.Draw(image)
    draw.ellipse((10, 8, 48, 50), fill=color)
    draw.rectangle((50, 46, 68, 68), fill=(40, 120, 245))
    image.save(path)
    return path


def test_phase20_8d_recent_reference_attribution_uses_unified_flow_candidate(tmp_path: Path) -> None:
    db_path = tmp_path / "flow.sqlite"
    apple = _image(tmp_path / "apple.png", color=(230, 40, 35))

    run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="image", path=str(apple)),),
        session_id="phase20-8d-reference",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    taught = run_phase20_7_turn(
        user_text="刚刚图片是啥",
        teacher_feedback=TeacherFeedback(feedback_text="红色苹果", reward_mag=1.0),
        session_id="phase20-8d-reference",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    slots = [slot for tick in taught.tick_trace for row in tick.c_backward for slot in row.get("cause_slots", ())]
    flow_slots = [slot for slot in slots if slot.get("slot_kind") == "unified_experience_flow_candidate"]
    assert flow_slots
    assert any(slot.get("candidate_kind") == "recent_visual_window" for slot in flow_slots)
    assert any(slot.get("payload_ref_count", 0) > 0 for slot in flow_slots)


def test_phase20_8d_recent_reference_attribution_is_not_chinese_cue_route(tmp_path: Path) -> None:
    db_path = tmp_path / "flow.sqlite"
    apple = _image(tmp_path / "apple.png", color=(230, 40, 35))

    run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="image", path=str(apple)),),
        session_id="phase20-8d-reference-neutral",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    taught = run_phase20_7_turn(
        user_text="what was that",
        teacher_feedback=TeacherFeedback(feedback_text="red apple", reward_mag=1.0),
        session_id="phase20-8d-reference-neutral",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    slots = [slot for tick in taught.tick_trace for row in tick.c_backward for slot in row.get("cause_slots", ())]
    flow_slots = [slot for slot in slots if slot.get("slot_kind") == "unified_experience_flow_candidate"]
    assert flow_slots
    assert any(slot.get("candidate_kind") == "recent_visual_window" for slot in flow_slots)
    assert any(slot.get("payload_ref_count", 0) > 0 for slot in flow_slots)


def test_phase20_8d_flow_candidates_include_occurrences_edges_and_visual_payload_refs(tmp_path: Path) -> None:
    db_path = tmp_path / "flow.sqlite"
    apple = _image(tmp_path / "apple.png", color=(230, 40, 35))

    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple)),),
        teacher_feedback=TeacherFeedback(feedback_text="红色苹果", reward_mag=1.0),
        session_id="phase20-8d-candidate",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    with sqlite3.connect(db_path) as conn:
        candidates = query_recent_experience_flow_candidates(
            conn,
            session_id="phase20-8d-candidate",
            from_json=from_json,
            hash_text=_hash_text,
            signature_for_chars=_signature_for_chars,
            compose_input_signature=_compose_input_signature,
            visual_tokens_from_payloads=_visual_signature_from_payloads,
            limit=12,
        )

    assert candidates
    visual_candidates = [candidate for candidate in candidates if candidate.candidate_kind == "recent_visual_window"]
    text_candidates = [candidate for candidate in candidates if candidate.candidate_kind == "recent_text_window"]
    assert visual_candidates
    assert text_candidates
    assert any(candidate.payload_refs for candidate in visual_candidates)
    assert any(candidate.occurrence_ids for candidate in visual_candidates + text_candidates)
    assert any(candidate.edge_ids for candidate in visual_candidates + text_candidates)
