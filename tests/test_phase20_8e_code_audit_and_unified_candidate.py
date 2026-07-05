from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from PIL import Image, ImageDraw

from apv3test.runtime.phase20_7 import MediaInput, TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.experience_candidate import UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID
from apv3test.runtime.phase20_7.experience_log import from_json
from apv3test.runtime.phase20_7.runtime import (
    _RecoveredObservation,
    _compose_input_signature,
    _hash_text,
    _signature_for_chars,
    _unified_experience_candidates_for_observation,
)


def _image(path: Path, *, primary: tuple[int, int, int]) -> Path:
    image = Image.new("RGB", (72, 72), (8, 8, 8))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 6, 48, 50), fill=primary)
    draw.rectangle((48, 46, 68, 68), fill=(40, 120, 245))
    image.save(path)
    return path


def _query_observation(text: str) -> _RecoveredObservation:
    chars = tuple(text)
    text_signature = _signature_for_chars(chars)
    return _RecoveredObservation(
        event_id="test-query",
        source_packet_id="test-source",
        occurrence_ids=(),
        signature=_compose_input_signature(text_signature, None),
        text_signature=text_signature,
        chars=chars,
        text_hash=_hash_text(text),
        visual_signature=None,
        recovery_kind="test_query",
    )


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


def _slots(result: Any) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for tick in result.tick_trace:
        for row in tick.c_backward:
            raw_slots = row.get("cause_slots", ())
            if isinstance(raw_slots, list | tuple):
                slots.extend(slot for slot in raw_slots if isinstance(slot, dict))
    return slots


def test_phase20_8e_unified_query_merges_alignment_and_recent_flow_candidates(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8e.sqlite"
    apple = _image(tmp_path / "apple.png", primary=(230, 40, 35))

    run_phase20_7_turn(
        user_text="what is this",
        media_inputs=(MediaInput(media_type="image", path=str(apple)),),
        teacher_feedback=TeacherFeedback(feedback_text="red apple", reward_mag=1.0),
        session_id="phase20-8e-unified",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    with sqlite3.connect(db_path) as conn:
        candidates = _unified_experience_candidates_for_observation(
            conn,
            _query_observation("apple"),
            session_id="phase20-8e-unified",
        )

    assert candidates
    assert any(candidate.candidate_kind == "experience_alignment" for candidate in candidates)
    assert any(candidate.candidate_kind == "recent_visual_window" for candidate in candidates)
    assert all(candidate.support_formula == UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID for candidate in candidates)
    assert all(candidate.support_terms for candidate in candidates)
    assert candidates == tuple(sorted(candidates, key=lambda item: item.support, reverse=True))


def test_phase20_8e_visual_imagination_audits_unified_candidate_not_last_asset(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8e.sqlite"
    apple = _image(tmp_path / "apple_memory.png", primary=(230, 40, 35))
    banana = _image(tmp_path / "banana_memory.png", primary=(245, 220, 35))

    run_phase20_7_turn(
        user_text="what is this",
        media_inputs=(MediaInput(media_type="image", path=str(apple)),),
        teacher_feedback=TeacherFeedback(feedback_text="red apple", reward_mag=1.0),
        session_id="phase20-8e-apple",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    run_phase20_7_turn(
        user_text="what is this",
        media_inputs=(MediaInput(media_type="image", path=str(banana)),),
        teacher_feedback=TeacherFeedback(feedback_text="yellow banana", reward_mag=1.0),
        session_id="phase20-8e-banana",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="image", path=str(banana)),),
        session_id="phase20-8e-last-banana",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    with sqlite3.connect(db_path) as conn:
        apple_alignment_ids = _alignment_ids_containing(conn, "apple")
        banana_alignment_ids = _alignment_ids_containing(conn, "banana")

    imagined = run_phase20_7_turn(
        user_text="apple",
        session_id="phase20-8e-query-apple",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    imagination_ticks = [
        tick for tick in imagined.tick_trace if tick.selected_action.get("action_type") == "visual_imagination_recall"
    ]
    assert imagination_ticks
    inner = imagination_ticks[-1].visual_inner_picture
    assert inner is not None
    assert inner["source"] == "visual_imagination_recall"
    assert inner["raw_source_asset_used_for_render"] is False
    recalled_alignment_ids = {str(item) for item in inner.get("source_alignment_ids", ())}
    assert recalled_alignment_ids & apple_alignment_ids
    assert not (recalled_alignment_ids & banana_alignment_ids)

    unified_slots = [slot for slot in _slots(imagined) if slot.get("slot_kind") == "unified_experience_candidate"]
    assert unified_slots
    assert any(slot.get("candidate_kind") == "experience_alignment" for slot in unified_slots)
    assert all(slot.get("support_formula") == UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID for slot in unified_slots)


def test_phase20_8e_recent_reference_attribution_exposes_unified_candidate_slot(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_8e.sqlite"
    apple = _image(tmp_path / "recent_apple.png", primary=(230, 40, 35))

    run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="image", path=str(apple)),),
        session_id="phase20-8e-reference",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    taught = run_phase20_7_turn(
        user_text="\u521a\u521a\u56fe\u7247\u662f\u5565",
        teacher_feedback=TeacherFeedback(feedback_text="\u7ea2\u8272\u82f9\u679c", reward_mag=1.0),
        session_id="phase20-8e-reference",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    unified_slots = [slot for slot in _slots(taught) if slot.get("slot_kind") == "unified_experience_candidate"]
    assert unified_slots
    assert any(slot.get("candidate_kind") == "recent_visual_window" for slot in unified_slots)
    assert any(slot.get("payload_ref_count", 0) > 0 for slot in unified_slots)


def test_phase20_8e_runtime_does_not_claim_unimplemented_six_stage_or_l123(tmp_path: Path) -> None:
    result = run_phase20_7_turn(
        user_text="unknown thing",
        session_id="phase20-8e-boundary",
        db_path=tmp_path / "phase20_8e.sqlite",
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    serialized = repr(result.to_dict()).lower()
    assert "six_stage_learning_complete" not in serialized
    assert "online_embedding_converged" not in serialized
    assert "l1_l2_l3_complete" not in serialized
    assert "l1_vector_converged" not in serialized
    assert "l2_vector_converged" not in serialized
    assert all("six_stage_complete" not in repr(delta).lower() for tick in result.tick_trace for delta in tick.learning_deltas)
