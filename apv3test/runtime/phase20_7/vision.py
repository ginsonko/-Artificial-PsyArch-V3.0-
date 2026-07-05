from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sqlite3
from typing import Any, Sequence

import numpy as np
from PIL import Image

from apv3test.runtime.visual_receptor import SensoryCanvas, clarity_field
from runtime.cognitive.state_pool.state_pool import StatePool

from .experience_log import (
    from_json,
    insert_action_record,
    insert_experience_event,
    insert_occurrence,
    insert_payload_blob,
    insert_source_packet,
    insert_structure_edge,
    upsert_sa_type,
)
from .models import MediaInput, RuntimeTickEventV2


def run_visual_receptor_ticks(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    media_inputs: Sequence[MediaInput],
    start_tick: int,
    db_path: Path,
    max_visual_ticks: int = 3,
) -> tuple[tuple[RuntimeTickEventV2, ...], int]:
    events: list[RuntimeTickEventV2] = []
    tick = int(start_tick)
    image_inputs = [item for item in media_inputs if item.media_type == "image" and item.path]
    for media in image_inputs:
        path = Path(str(media.path))
        if not path.exists():
            continue
        image = Image.open(path).convert("RGB")
        rgb_u8 = np.asarray(image, dtype=np.uint8)
        rgb = rgb_u8.astype(np.float32) / 255.0
        source_hash = _hash_bytes(path.read_bytes())
        canvas = SensoryCanvas.from_native_image(rgb, tick=tick)
        # §16 周边采样: 焦点外的低清晰全图 gist — 人看东西时周边视野同时给出
        # 模糊的整体轮廓/配色. 存一份降采样全图 payload (低 clarity), 想象重建时
        # 画布因此有整体形状而非只有几个焦点方块. 感受器级机制, 非 label.
        gist_payload_ref = _store_gist_payload(
            conn, rgb_u8=rgb_u8, source_hash=source_hash, tick=tick
        )
        previous_focus: tuple[int, int] | None = None
        for focus_index, focus_xy in enumerate(_focus_sequence(rgb, limit=max_visual_ticks)):
            tick += 1
            canvas.update_from_native_image(rgb, focus_xy=focus_xy, tick=tick)
            evidence = _visual_evidence_from_patch(
                rgb=rgb,
                canvas=canvas,
                focus_xy=focus_xy,
                focus_index=focus_index,
            )
            payload_ref = _store_patch_payload(
                conn,
                rgb_u8=rgb_u8,
                focus_xy=focus_xy,
                source_hash=source_hash,
                tick=tick,
                focus_index=focus_index,
                evidence=evidence,
            )
            source_packet_id = insert_source_packet(
                conn,
                source_kind="visual_patch_sensor",
                source_ref=f"image_hash::{source_hash[:16]}",
                source_context="open_dialogue_vision",
                modality="vision",
                trust_snapshot=0.5,
                tick=tick,
                payload={
                    "source_hash": source_hash,
                    "focus_xy": list(focus_xy),
                    "focus_index": focus_index,
                    "visual_evidence": evidence,
                    "raw_path_stored": False,
                },
            )
            action_type = "move_focus" if previous_focus != focus_xy else "maintain_focus"
            action_record_id = insert_action_record(
                conn,
                session_id=session_id,
                tick=tick,
                action_type=action_type,
                selected=True,
                drive=0.76 if action_type == "move_focus" else 0.52,
                eligibility={
                    "saliency_without_label": True,
                    "source_hash": source_hash[:16],
                    "focus_index": focus_index,
                },
                target_refs={"focus_xy": list(focus_xy), "payload_ref": payload_ref},
            )
            event_id = insert_experience_event(
                conn,
                session_id=session_id,
                tick=tick,
                event_kind="visual_patch_sample",
                source_packet_id=source_packet_id,
                action_record_id=action_record_id,
                payload={
                    "source_hash": source_hash,
                    "payload_ref": payload_ref,
                    "peripheral_gist_payload_ref": gist_payload_ref,
                    "focus_xy": list(focus_xy),
                    "focus_index": focus_index,
                    "clarity_coverage": canvas.clarity_coverage(),
                    "visual_evidence": evidence,
                    "recognition_label": None,
                },
            )
            conn.execute(
                "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
                (event_id, action_record_id),
            )
            occurrence_ids = _write_visual_occurrences(
                conn,
                event_id=event_id,
                source_packet_id=source_packet_id,
                payload_ref=payload_ref,
                focus_xy=focus_xy,
                evidence=evidence,
                tick=tick,
                canvas=canvas,
            )
            _inject_visual_state(pool, canvas=canvas, focus_xy=focus_xy, tick=tick)
            inner_picture = _write_inner_picture(canvas, db_path=db_path, source_hash=source_hash, tick=tick)
            events.append(
                RuntimeTickEventV2(
                    tick=tick,
                    session_id=session_id,
                    external_inputs=(
                        {
                            "input_kind": "image",
                            "source_hash": source_hash,
                            "raw_path_stored": False,
                        },
                    ),
                    receptor_outputs=(
                        {
                            "receptor": "visual_patch_sensor",
                            "event_id": event_id,
                            "payload_ref": payload_ref,
                            "focus_xy": list(focus_xy),
                            "clarity_coverage": canvas.clarity_coverage(),
                            "visual_evidence": evidence,
                            "recognition_label": None,
                        },
                    ),
                    state_pool_top=pool.snapshot_top(limit=12),
                    ssp_active_summary={
                        "structure_kind": "visual_focus_patch_flow",
                        "active_occurrence_count": len(occurrence_ids),
                        "latest_occurrence_id": occurrence_ids[-1] if occurrence_ids else None,
                    },
                    action_competition=(
                        {"action_type": action_type, "drive": 0.76, "selected": True},
                        {"action_type": "widen_focus", "drive": 0.22, "selected": False},
                        {"action_type": "write_cell", "drive": 0.02, "selected": False},
                    ),
                    selected_action={
                        "action_type": action_type,
                        "focus_xy": list(focus_xy),
                        "saliency_source": "pixel_contrast_saturation_without_label",
                        "visual_evidence_signature": evidence["signature"],
                    },
                    visual_inner_picture=inner_picture,
                    experience_event_ids_written=(event_id,),
                    source_refs=({"source_packet_id": source_packet_id, "source_kind": "visual_patch_sensor"},),
                    action_record_ids=(action_record_id,),
                    timings_ms={"visual_patch_tick": 0.0},
                )
            )
            previous_focus = focus_xy
    return tuple(events), tick


def run_idle_visual_receptor_tick(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    start_tick: int,
    db_path: Path,
) -> tuple[RuntimeTickEventV2 | None, int]:
    """Continue visual looking from stored patch payloads, not from a label or thumbnail."""

    patch_rows = _recent_patch_payload_rows(conn, session_id=session_id, limit=18)
    if not patch_rows:
        return None, int(start_tick)
    canvas, source_hash, payload_rows = _reconstruct_canvas_from_patch_payloads(patch_rows, tick=int(start_tick))
    if canvas is None or not payload_rows:
        return None, int(start_tick)
    tick = int(start_tick) + 1
    focus_xy, focus_trace = _next_idle_focus_from_canvas(canvas, tick=tick, allow_unknown=False)
    canvas = _apply_focus_from_known_payloads(canvas, payload_rows, focus_xy=focus_xy, tick=tick)
    evidence = _visual_evidence_from_patch(
        rgb=np.clip(canvas.canvas_pixels, 0.0, 1.0),
        canvas=canvas,
        focus_xy=focus_xy,
        focus_index=int(focus_trace["idle_focus_index"]),
    )
    rgb_u8 = np.uint8(np.clip(canvas.canvas_pixels, 0.0, 1.0) * 255.0)
    payload_ref = _store_patch_payload(
        conn,
        rgb_u8=rgb_u8,
        focus_xy=focus_xy,
        source_hash=source_hash,
        tick=tick,
        focus_index=int(focus_trace["idle_focus_index"]),
        evidence=evidence,
        payload_kind="visual_idle_patch_payload",
    )
    source_packet_id = insert_source_packet(
        conn,
        source_kind="visual_idle_patch_sensor",
        source_ref=f"patch_memory_hash::{source_hash[:16]}",
        source_context="open_dialogue_idle_vision",
        modality="vision",
        trust_snapshot=0.5,
        tick=tick,
        payload={
            "source_hash": source_hash,
            "focus_xy": list(focus_xy),
            "visual_evidence": evidence,
            "raw_path_stored": False,
            "raw_source_asset_used": False,
            "reconstructed_from_payload_refs": [row["payload_ref"] for row in payload_rows[:8]],
        },
    )
    action_record_id = insert_action_record(
        conn,
        session_id=session_id,
        tick=tick,
        action_type="idle_visual_focus",
        selected=True,
        drive=float(focus_trace["drive"]),
        eligibility={
            "no_external_input": True,
            "clarity_gap": float(focus_trace["clarity_gap"]),
            "saliency_without_label": True,
            "uses_stored_patch_payload": True,
        },
        target_refs={"focus_xy": list(focus_xy), "payload_ref": payload_ref},
    )
    event_id = insert_experience_event(
        conn,
        session_id=session_id,
        tick=tick,
        event_kind="visual_patch_sample",
        source_packet_id=source_packet_id,
        action_record_id=action_record_id,
        payload={
            "source_hash": source_hash,
            "payload_ref": payload_ref,
            "focus_xy": list(focus_xy),
            "focus_index": int(focus_trace["idle_focus_index"]),
            "clarity_coverage": canvas.clarity_coverage(),
            "visual_evidence": evidence,
            "recognition_label": None,
            "idle_continuation": True,
            "raw_source_asset_used": False,
            "reconstructed_from_payload_refs": [row["payload_ref"] for row in payload_rows[:8]],
        },
    )
    conn.execute(
        "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
        (event_id, action_record_id),
    )
    occurrence_ids = _write_visual_occurrences(
        conn,
        event_id=event_id,
        source_packet_id=source_packet_id,
        payload_ref=payload_ref,
        focus_xy=focus_xy,
        evidence=evidence,
        tick=tick,
        canvas=canvas,
    )
    _inject_visual_state(pool, canvas=canvas, focus_xy=focus_xy, tick=tick)
    inner_picture = _write_inner_picture(canvas, db_path=db_path, source_hash=source_hash, tick=tick)
    event = RuntimeTickEventV2(
        tick=tick,
        session_id=session_id,
        receptor_outputs=(
            {
                "receptor": "visual_patch_sensor",
                "event_id": event_id,
                "payload_ref": payload_ref,
                "focus_xy": list(focus_xy),
                "clarity_coverage": canvas.clarity_coverage(),
                "visual_evidence": evidence,
                "recognition_label": None,
                "idle_continuation": True,
            },
        ),
        state_pool_top=pool.snapshot_top(limit=12),
        ssp_active_summary={
            "structure_kind": "visual_focus_patch_flow",
            "active_occurrence_count": len(occurrence_ids),
            "latest_occurrence_id": occurrence_ids[-1] if occurrence_ids else None,
            "idle_continuation": True,
            "focus_trace": focus_trace,
        },
        c_forward=(
            {
                "kind": "sensory_successor_prediction",
                "prediction": "continue_visual_sampling_until_clarity_or_fatigue_balances",
                "support": round(float(focus_trace["drive"]), 4),
                "clarity_gap": round(float(focus_trace["clarity_gap"]), 4),
            },
        ),
        c_backward=(
            {
                "kind": "every_tick_backward_min_error",
                "model": "b_recall_reverse_cause_slots_ssp_neutralization/v1",
                "selected_source_kind": "recent_visual_patch_payload",
                "cause_slots": [
                    {"slot_kind": "recent_fixation", "focus_xy": list(canvas.last_fixation_xy)},
                    {"slot_kind": "stored_patch_payload", "payload_ref_count": len(payload_rows)},
                ],
                "neutralized_occurrences": [
                    {"occurrence_id": occurrence_ids[-1] if occurrence_ids else None, "neutralize": round(float(focus_trace["drive"]), 4)}
                ],
                "cause_grasp": round(float(focus_trace["drive"]), 4),
                "e_backward": round(1.0 - float(focus_trace["drive"]), 4),
                "subjective": True,
                "may_be_wrong": True,
            },
        ),
        action_competition=(
            {"action_type": "idle_visual_focus", "drive": float(focus_trace["drive"]), "selected": True},
            {"action_type": "idle_think", "drive": 0.34, "selected": False},
            {"action_type": "idle_observe", "drive": 0.18, "selected": False},
        ),
        selected_action={
            "action_type": "idle_visual_focus",
            "drive": float(focus_trace["drive"]),
            "focus_xy": list(focus_xy),
            "saliency_source": "stored_patch_payload_clarity_gap_without_label",
            "visual_evidence_signature": evidence["signature"],
            "confidence_gap": float(focus_trace["confidence_gap"]),
        },
        feelings={
            "idle": True,
            "visual_clarity_gap": round(float(focus_trace["clarity_gap"]), 4),
            "attention_target": "visual_focus",
            "raw_source_asset_used_for_render": False,
        },
        visual_inner_picture=inner_picture,
        experience_event_ids_written=(event_id,),
        source_refs=({"source_packet_id": source_packet_id, "source_kind": "visual_idle_patch_sensor"},),
        action_record_ids=(action_record_id,),
        timings_ms={"idle_visual_patch_tick": 0.0},
    )
    return event, tick


def run_visual_imagination_recall_tick(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    start_tick: int,
    db_path: Path,
    patch_payload_refs: Sequence[str],
    source_alignment_ids: Sequence[str],
    query_text: str,
    recall_score: float,
    reason: str,
    candidate_audit_slots: Sequence[dict[str, Any]] = (),
) -> tuple[RuntimeTickEventV2 | None, int]:
    """Rebuild an inner picture from remembered visual patch payloads.

    This is an endogenous visual recall action: it does not read the latest
    source image or filename, and it does not create a semantic label route.
    The only image material allowed here is already written patch payloads
    reached through the unified experience flow.
    """

    payload_rows = _patch_payload_rows_by_refs(conn, patch_payload_refs)
    if not payload_rows:
        return None, int(start_tick)
    tick = int(start_tick) + 1
    canvas, source_hash, valid_rows = _reconstruct_canvas_from_patch_payloads(payload_rows, tick=tick)
    if canvas is None or not valid_rows:
        return None, int(start_tick)
    imagined_hash = _hash_text("|".join(str(ref) for ref in patch_payload_refs) + "|" + str(query_text))
    canvas.source_image_hash = f"imagined::{imagined_hash}"
    focus_xy, focus_trace = _next_idle_focus_from_canvas(canvas, tick=tick, allow_unknown=False)
    canvas = _apply_focus_from_known_payloads(canvas, valid_rows, focus_xy=focus_xy, tick=tick)
    evidence = _visual_evidence_from_patch(
        rgb=np.clip(canvas.canvas_pixels, 0.0, 1.0),
        canvas=canvas,
        focus_xy=focus_xy,
        focus_index=int(focus_trace["idle_focus_index"]),
    )
    source_packet_id = insert_source_packet(
        conn,
        source_kind="visual_imagination_recall",
        source_ref=f"experience_flow::{imagined_hash}",
        source_context="open_dialogue_inner_vision",
        modality="vision",
        trust_snapshot=max(0.1, min(0.9, float(recall_score))),
        tick=tick,
        payload={
            "query_text_hash": _hash_text(query_text),
            "source_alignment_ids": list(source_alignment_ids),
            "borrowed_patch_payload_refs": [row["payload_ref"] for row in valid_rows],
            "raw_path_stored": False,
            "raw_source_asset_used": False,
            "epistemic_source": "IMAGINED_FROM_EXPERIENCE_FLOW",
            "reason": reason,
            "candidate_audit_slots": list(candidate_audit_slots),
        },
    )
    action_record_id = insert_action_record(
        conn,
        session_id=session_id,
        tick=tick,
        action_type="visual_imagination_recall",
        selected=True,
        drive=max(0.12, min(0.92, float(recall_score))),
        eligibility={
            "text_occurrence_recalled_visual_experience": True,
            "uses_stored_patch_payload": True,
            "raw_source_asset_used": False,
            "source_alignment_count": len(tuple(source_alignment_ids)),
        },
        target_refs={
            "focus_xy": list(focus_xy),
            "patch_payload_refs": [row["payload_ref"] for row in valid_rows],
        },
    )
    event_id = insert_experience_event(
        conn,
        session_id=session_id,
        tick=tick,
        event_kind="visual_imagination_recall",
        source_packet_id=source_packet_id,
        action_record_id=action_record_id,
        payload={
            "query_text_hash": _hash_text(query_text),
            "source_alignment_ids": list(source_alignment_ids),
            "borrowed_patch_payload_refs": [row["payload_ref"] for row in valid_rows],
            "focus_xy": list(focus_xy),
            "clarity_coverage": canvas.clarity_coverage(),
            "visual_evidence": evidence,
            "recognition_label": None,
            "raw_source_asset_used": False,
            "epistemic_source": "IMAGINED_FROM_EXPERIENCE_FLOW",
            "reason": reason,
            "candidate_audit_slots": list(candidate_audit_slots),
        },
    )
    conn.execute(
        "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
        (event_id, action_record_id),
    )
    occurrence_ids = _write_visual_occurrences(
        conn,
        event_id=event_id,
        source_packet_id=source_packet_id,
        payload_ref=str(valid_rows[0]["payload_ref"]),
        focus_xy=focus_xy,
        evidence=evidence,
        tick=tick,
        canvas=canvas,
    )
    _inject_visual_imagination_state(
        pool,
        canvas=canvas,
        focus_xy=focus_xy,
        tick=tick,
        recall_score=float(recall_score),
    )
    inner_picture = _write_inner_picture(canvas, db_path=db_path, source_hash=f"imagined_{imagined_hash}", tick=tick)
    inner_picture = {
        **inner_picture,
        "source": "visual_imagination_recall",
        "epistemic_source": "IMAGINED_FROM_EXPERIENCE_FLOW",
        "raw_source_asset_used_for_render": False,
        "borrowed_patch_payload_count": len(valid_rows),
        "borrowed_patch_payload_refs": [row["payload_ref"] for row in valid_rows],
        "source_alignment_ids": list(source_alignment_ids),
    }
    event = RuntimeTickEventV2(
        tick=tick,
        session_id=session_id,
        receptor_outputs=(
            {
                "receptor": "visual_memory_recall",
                "event_id": event_id,
                "focus_xy": list(focus_xy),
                "clarity_coverage": canvas.clarity_coverage(),
                "visual_evidence": evidence,
                "recognition_label": None,
                "epistemic_source": "IMAGINED_FROM_EXPERIENCE_FLOW",
            },
        ),
        state_pool_top=pool.snapshot_top(limit=12),
        ssp_active_summary={
            "structure_kind": "visual_memory_imagination_flow",
            "active_occurrence_count": len(occurrence_ids),
            "latest_occurrence_id": occurrence_ids[-1] if occurrence_ids else None,
            "source_alignment_ids": list(source_alignment_ids),
            "borrowed_patch_payload_count": len(valid_rows),
            "focus_trace": focus_trace,
        },
        c_forward=(
            {
                "kind": "remembered_visual_successor",
                "support": round(float(recall_score), 4),
                "prediction": "remembered_visual_patch_can_feed_inner_picture_and_next_attention",
            },
        ),
        c_backward=(
            {
                "kind": "every_tick_backward_min_error",
                "model": "text_occurrence_to_visual_experience_flow/v1",
                "selected_source_kind": "remembered_visual_alignment",
                "source_alignment_ids": list(source_alignment_ids),
                "cause_slots": [
                    {"slot_kind": "current_text_occurrence", "text_hash": _hash_text(query_text)},
                    {"slot_kind": "remembered_visual_patch_payloads", "payload_ref_count": len(valid_rows)},
                    *list(candidate_audit_slots),
                ],
                "neutralized_occurrences": [
                    {
                        "occurrence_id": occurrence_ids[-1] if occurrence_ids else None,
                        "neutralize_score": round(float(recall_score), 4),
                        "source_kind": "remembered_visual_alignment",
                    }
                ],
                "cause_grasp": round(float(recall_score), 4),
                "e_backward": round(max(0.0, 1.0 - float(recall_score)), 4),
                "subjective": True,
                "may_be_wrong": True,
            },
        ),
        action_competition=(
            {"action_type": "visual_imagination_recall", "drive": float(recall_score), "selected": True},
            {"action_type": "idle_visual_focus", "drive": 0.20, "selected": False},
            {"action_type": "write_cell", "drive": 0.08, "selected": False},
        ),
        selected_action={
            "action_type": "visual_imagination_recall",
            "drive": float(recall_score),
            "focus_xy": list(focus_xy),
            "source": "experience_flow_patch_payload",
            "visual_evidence_signature": evidence["signature"],
        },
        feelings={
            "imagined_visual_grasp": round(float(recall_score), 4),
            "attention_target": "remembered_visual_structure",
            "raw_source_asset_used_for_render": False,
        },
        visual_inner_picture=inner_picture,
        experience_event_ids_written=(event_id,),
        source_refs=(
            {
                "source_packet_id": source_packet_id,
                "source_kind": "visual_imagination_recall",
                "source_alignment_ids": list(source_alignment_ids),
            },
        ),
        action_record_ids=(action_record_id,),
        timings_ms={"visual_imagination_recall_tick": 0.0},
    )
    return event, tick


def estimate_idle_visual_drive(conn: sqlite3.Connection, *, session_id: str) -> float:
    row = conn.execute(
        """
        SELECT payload_json, tick
        FROM phase20_7_experience_events
        WHERE session_id=?
          AND event_kind IN ('visual_patch_sample', 'visual_imagination_recall')
        ORDER BY tick DESC, created_at_ms DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        return 0.0
    payload_json, event_tick = row
    payload = from_json(str(payload_json))
    if not isinstance(payload, dict):
        return 0.0
    clarity = float(payload.get("clarity_coverage", 0.0) or 0.0)
    idle_continuation = bool(payload.get("idle_continuation", False))
    recency = 1.0 / (1.0 + max(0, int(_latest_visual_tick(conn, session_id=session_id)) - int(event_tick or 0)))
    fatigue = 0.16 if idle_continuation else 0.0
    return float(np.clip(0.22 + (1.0 - clarity) * 0.52 + recency * 0.18 - fatigue, 0.0, 0.86))


def _focus_sequence(rgb: np.ndarray, *, limit: int) -> tuple[tuple[int, int], ...]:
    h, w = rgb.shape[:2]
    center = (w // 2, h // 2)
    luma = rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114
    gy, gx = np.gradient(luma)
    edge = np.sqrt(gx * gx + gy * gy)
    saturation = rgb.max(axis=2) - rgb.min(axis=2)
    saliency = edge * 0.7 + saturation * 0.3
    points: list[tuple[float, tuple[int, int]]] = [(float(saliency[h // 2, w // 2]), center)]
    grid = max(4, min(8, int(np.sqrt(h * w) // 16)))
    cell_h = max(1, h // grid)
    cell_w = max(1, w // grid)
    for row in range(grid):
        for col in range(grid):
            y1 = row * cell_h
            y2 = h if row == grid - 1 else min(h, y1 + cell_h)
            x1 = col * cell_w
            x2 = w if col == grid - 1 else min(w, x1 + cell_w)
            patch = saliency[y1:y2, x1:x2]
            if patch.size == 0:
                continue
            local = np.unravel_index(int(np.argmax(patch)), patch.shape)
            y = int(y1 + local[0])
            x = int(x1 + local[1])
            points.append((float(patch[local]), (x, y)))
    ordered: list[tuple[int, int]] = []
    for _, point in sorted(points, key=lambda item: item[0], reverse=True):
        if all(abs(point[0] - old[0]) + abs(point[1] - old[1]) > max(3, min(w, h) // 8) for old in ordered):
            ordered.append(point)
        if len(ordered) >= int(limit):
            break
    if not ordered:
        ordered.append(center)
    return tuple(ordered)


def _latest_visual_tick(conn: sqlite3.Connection, *, session_id: str) -> int:
    row = conn.execute(
        """
        SELECT COALESCE(MAX(tick), 0)
        FROM phase20_7_experience_events
        WHERE session_id=?
          AND event_kind IN ('visual_patch_sample', 'visual_imagination_recall')
        """,
        (session_id,),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _store_patch_payload(
    conn: sqlite3.Connection,
    *,
    rgb_u8: np.ndarray,
    focus_xy: tuple[int, int],
    source_hash: str,
    tick: int,
    focus_index: int,
    evidence: dict[str, object],
    payload_kind: str = "visual_patch_payload",
) -> str:
    h, w = rgb_u8.shape[:2]
    patch_size = max(12, min(w, h) // 3)
    half = patch_size // 2
    x, y = focus_xy
    x1 = max(0, x - half)
    y1 = max(0, y - half)
    x2 = min(w, x + half)
    y2 = min(h, y + half)
    patch = Image.fromarray(rgb_u8[y1:y2, x1:x2], mode="RGB")
    buf = io.BytesIO()
    patch.save(buf, format="PNG")
    patch_arr = rgb_u8[y1:y2, x1:x2].astype(np.float32) / 255.0
    return insert_payload_blob(
        conn,
        payload_kind=payload_kind,
        media_type="image",
        blob_bytes=buf.getvalue(),
        summary={
            "focus_xy": list(focus_xy),
            "focus_index": focus_index,
            "patch_box": [x1, y1, x2, y2],
            "image_size": [w, h],
            "mean_rgb": [float(value) for value in patch_arr.mean(axis=(0, 1))],
            "visual_evidence": evidence,
            "patch_native_resolution": True,
            "recognition_label": None,
        },
        source_hash=source_hash,
        tick=tick,
    )


def _recent_patch_payload_rows(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    limit: int,
) -> tuple[dict[str, object], ...]:
    anchor = conn.execute(
        """
        SELECT event_kind, payload_json
        FROM phase20_7_experience_events
        WHERE session_id=?
          AND event_kind IN ('visual_patch_sample', 'visual_imagination_recall')
        ORDER BY tick DESC, created_at_ms DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if anchor is not None and str(anchor[0]) == "visual_imagination_recall":
        anchor_payload = from_json(str(anchor[1]))
        if isinstance(anchor_payload, dict):
            refs = anchor_payload.get("borrowed_patch_payload_refs", ())
            if isinstance(refs, Sequence) and not isinstance(refs, (str, bytes, bytearray)):
                rows = _patch_payload_rows_by_refs(conn, [str(ref) for ref in refs[:limit]])
                if rows:
                    return rows
    rows = conn.execute(
        """
        SELECT e.event_id, e.tick, e.payload_json, p.payload_ref, p.bytes, p.summary_json, p.source_hash
        FROM phase20_7_experience_events e
        JOIN phase20_7_payload_blobs p
          ON p.payload_ref=json_extract(e.payload_json, '$.payload_ref')
        WHERE e.session_id=?
          AND e.event_kind='visual_patch_sample'
          AND p.media_type='image'
          AND p.bytes IS NOT NULL
        ORDER BY e.tick DESC, e.created_at_ms DESC
        LIMIT ?
        """,
        (session_id, int(limit)),
    ).fetchall()
    out: list[dict[str, object]] = []
    for event_id, event_tick, payload_json, payload_ref, blob_bytes, summary_json, source_hash in rows:
        summary = from_json(str(summary_json))
        payload = from_json(str(payload_json))
        if not isinstance(summary, dict) or not isinstance(payload, dict):
            continue
        out.append(
            {
                "event_id": str(event_id),
                "tick": int(event_tick),
                "payload_ref": str(payload_ref),
                "bytes": blob_bytes,
                "summary": summary,
                "payload": payload,
                "source_hash": str(source_hash),
            }
        )
    return tuple(out)


def _store_gist_payload(
    conn: sqlite3.Connection,
    *,
    rgb_u8: np.ndarray,
    source_hash: str,
    tick: int,
) -> str:
    """周边视野 gist (§16 周边采样): 全图降采样到 48px 短边, 低清晰整体形状/配色.

    人的周边视野同时给出模糊整体 — 没有它, 想象画布只有几个焦点方块拼不出轮廓.
    低分辨率本身就是"低清晰"的诚实表达 (不是原图缓存 — 48px 只有整体 gist 信息).
    """
    h, w = rgb_u8.shape[:2]
    short = 48
    if w <= h:
        gw, gh = short, max(1, int(h * short / max(w, 1)))
    else:
        gw, gh = max(1, int(w * short / max(h, 1))), short
    gist = Image.fromarray(rgb_u8, mode="RGB").resize((gw, gh), Image.Resampling.BILINEAR)
    buf = io.BytesIO()
    gist.save(buf, format="PNG")
    return insert_payload_blob(
        conn,
        payload_kind="visual_peripheral_gist",
        media_type="image",
        blob_bytes=buf.getvalue(),
        summary={
            "patch_box": [0, 0, w, h],
            "image_size": [w, h],
            "gist_resolution": [gw, gh],
            "peripheral_low_clarity": True,
            "recognition_label": None,
        },
        source_hash=source_hash,
        tick=tick,
    )


def _reconstruct_canvas_from_patch_payloads(
    rows: Sequence[dict[str, object]],
    *,
    tick: int,
) -> tuple[SensoryCanvas | None, str, tuple[dict[str, object], ...]]:
    if not rows:
        return None, "no_visual_patch_payload", ()
    width = 0
    height = 0
    source_hash = str(rows[0].get("source_hash") or "patch_payload")
    valid: list[dict[str, object]] = []
    for row in rows:
        summary = row.get("summary")
        if not isinstance(summary, dict):
            continue
        image_size = summary.get("image_size")
        if isinstance(image_size, Sequence) and not isinstance(image_size, (str, bytes, bytearray)) and len(image_size) >= 2:
            width = max(width, int(image_size[0]))
            height = max(height, int(image_size[1]))
        patch_box = summary.get("patch_box")
        if isinstance(patch_box, Sequence) and not isinstance(patch_box, (str, bytes, bytearray)) and len(patch_box) >= 4:
            width = max(width, int(patch_box[2]))
            height = max(height, int(patch_box[3]))
            valid.append(row)
    if width <= 0 or height <= 0 or not valid:
        return None, source_hash, ()
    canvas = SensoryCanvas(
        canvas_pixels=np.zeros((height, width, 3), dtype=np.float32),
        canvas_clarity=np.zeros((height, width), dtype=np.float32),
        canvas_confidence=np.zeros((height, width), dtype=np.float32),
        canvas_freshness=np.zeros((height, width), dtype=np.float32),
        last_fixation_xy=(width // 2, height // 2),
        tick=int(tick),
        source_image_hash=source_hash,
        first_tick=max(0, int(tick) - len(valid)),
    )
    for row in reversed(valid):
        summary = row["summary"]
        if not isinstance(summary, dict):
            continue
        if summary.get("peripheral_low_clarity"):
            # 周边 gist: 均匀低清晰铺底 (整体轮廓/配色), 不受焦点场衰减 —
            # 对应人闭眼回忆时"整体形状模糊但在"的那一层.
            canvas = _apply_gist_row_to_canvas(canvas, row, base_clarity=0.30)
            continue
        focus_xy = _summary_focus_xy(summary, fallback=canvas.last_fixation_xy)
        canvas = _apply_patch_row_to_canvas(canvas, row, focus_xy=focus_xy, tick=int(row.get("tick") or tick), base_gain=0.62)
    canvas.tick = int(tick)
    return canvas, source_hash, tuple(valid)


def _apply_gist_row_to_canvas(
    canvas: SensoryCanvas,
    row: dict[str, object],
    *,
    base_clarity: float,
) -> SensoryCanvas:
    blob = row.get("bytes")
    if blob is None:
        return canvas
    try:
        gist = Image.open(io.BytesIO(bytes(blob))).convert("RGB")
    except Exception:
        return canvas
    h, w = canvas.canvas_pixels.shape[:2]
    arr = np.asarray(gist.resize((w, h), Image.Resampling.BILINEAR), dtype=np.float32) / 255.0
    phi = np.full((h, w), float(np.clip(base_clarity, 0.0, 1.0)), dtype=np.float32)
    old = canvas.canvas_confidence
    denom = old + phi + 1e-6
    canvas.canvas_pixels = (old[..., None] * canvas.canvas_pixels + phi[..., None] * arr) / denom[..., None]
    canvas.canvas_clarity = np.maximum(canvas.canvas_clarity, phi * 0.8)
    canvas.canvas_confidence = np.maximum(canvas.canvas_confidence, phi)
    return canvas


def _apply_focus_from_known_payloads(
    canvas: SensoryCanvas,
    rows: Sequence[dict[str, object]],
    *,
    focus_xy: tuple[int, int],
    tick: int,
) -> SensoryCanvas:
    containing = [row for row in rows if _patch_box_contains(row.get("summary"), focus_xy)]
    candidates = containing or list(rows)
    for row in candidates[:3]:
        canvas = _apply_patch_row_to_canvas(canvas, row, focus_xy=focus_xy, tick=tick, base_gain=0.88)
    canvas.last_fixation_xy = (int(focus_xy[0]), int(focus_xy[1]))
    canvas.tick = int(tick)
    return canvas


def _apply_patch_row_to_canvas(
    canvas: SensoryCanvas,
    row: dict[str, object],
    *,
    focus_xy: tuple[int, int],
    tick: int,
    base_gain: float,
) -> SensoryCanvas:
    summary = row.get("summary")
    blob = row.get("bytes")
    if not isinstance(summary, dict) or blob is None:
        return canvas
    patch_box = summary.get("patch_box")
    if not isinstance(patch_box, Sequence) or isinstance(patch_box, (str, bytes, bytearray)) or len(patch_box) < 4:
        return canvas
    x1, y1, x2, y2 = [int(value) for value in patch_box[:4]]
    x1 = max(0, min(x1, canvas.canvas_pixels.shape[1] - 1))
    y1 = max(0, min(y1, canvas.canvas_pixels.shape[0] - 1))
    x2 = max(x1 + 1, min(x2, canvas.canvas_pixels.shape[1]))
    y2 = max(y1 + 1, min(y2, canvas.canvas_pixels.shape[0]))
    try:
        patch = Image.open(io.BytesIO(bytes(blob))).convert("RGB")
    except Exception:
        return canvas
    patch_arr = np.asarray(patch.resize((x2 - x1, y2 - y1), Image.Resampling.BILINEAR), dtype=np.float32) / 255.0
    phi = clarity_field(canvas.canvas_pixels.shape[:2], focus_xy)
    local_phi = phi[y1:y2, x1:x2] * float(np.clip(base_gain, 0.0, 1.0))
    old = canvas.canvas_confidence[y1:y2, x1:x2]
    denom = old + local_phi + 1e-6
    canvas.canvas_pixels[y1:y2, x1:x2] = (
        old[..., None] * canvas.canvas_pixels[y1:y2, x1:x2] + local_phi[..., None] * patch_arr
    ) / denom[..., None]
    canvas.canvas_clarity[y1:y2, x1:x2] = np.maximum(canvas.canvas_clarity[y1:y2, x1:x2] * 0.98, local_phi)
    canvas.canvas_confidence[y1:y2, x1:x2] = np.maximum(canvas.canvas_confidence[y1:y2, x1:x2] * 0.98, local_phi)
    canvas.canvas_freshness = canvas.canvas_freshness + 1.0
    canvas.canvas_freshness[y1:y2, x1:x2] = np.where(local_phi > 0.08, 0.0, canvas.canvas_freshness[y1:y2, x1:x2])
    canvas.last_fixation_xy = (int(focus_xy[0]), int(focus_xy[1]))
    canvas.tick = int(tick)
    return canvas


def _next_idle_focus_from_canvas(
    canvas: SensoryCanvas,
    *,
    tick: int,
    allow_unknown: bool = False,
) -> tuple[tuple[int, int], dict[str, object]]:
    pixels = np.clip(canvas.canvas_pixels, 0.0, 1.0)
    known = canvas.canvas_confidence > 0.015
    if not bool(known.any()):
        focus = canvas.last_fixation_xy
        return focus, {"idle_focus_index": int(tick), "drive": 0.18, "clarity_gap": 1.0, "basis": "no_known_patch"}
    luma = pixels[..., 0] * 0.299 + pixels[..., 1] * 0.587 + pixels[..., 2] * 0.114
    gy, gx = np.gradient(luma)
    edge = np.sqrt(gx * gx + gy * gy)
    saturation = pixels.max(axis=2) - pixels.min(axis=2)
    clarity_gap = np.clip(1.0 - canvas.canvas_clarity, 0.0, 1.0)
    # §16.3/§16.7 视焦点认知驱动: 把握度低的地方吸引焦点 ("我还没看清那里, 再看一眼").
    # confidence_gap 复用 canvas.canvas_confidence (§16.3 V 含预测/把握感), 不新增实体.
    # 拟人: 低把握→认知压高→眼睛被吸过去 (§24 低把握需多 tick 探索; §16 第951行 "违和被吸过去").
    confidence_gap = np.clip(1.0 - canvas.canvas_confidence, 0.0, 1.0)
    yy, xx = np.indices(canvas.canvas_clarity.shape)
    fx, fy = int(canvas.last_fixation_xy[0]), int(canvas.last_fixation_xy[1])
    distance = np.sqrt((xx - fx) ** 2 + (yy - fy) ** 2)
    distance_norm = distance / max(float(max(canvas.canvas_clarity.shape)), 1.0)
    deterministic_jitter = (((xx * 31 + yy * 17 + int(tick) * 13) % 97) / 97.0) * 0.025
    saliency = (
        edge * 0.44
        + saturation * 0.24
        + clarity_gap * 0.42
        + confidence_gap * 0.36
        + distance_norm * 0.10
        + deterministic_jitter
    )
    score_mask = np.ones_like(known, dtype=bool) if allow_unknown else known
    if allow_unknown:
        saliency = saliency + np.where(known, 0.0, 0.18)
    saliency = np.where(score_mask, saliency, -1.0)
    y, x = np.unravel_index(int(np.argmax(saliency)), saliency.shape)
    drive = float(np.clip(0.28 + saliency[y, x] * 0.72, 0.18, 0.94))
    return (
        (int(x), int(y)),
        {
            "idle_focus_index": int(tick),
            "drive": drive,
            "clarity_gap": float(clarity_gap[y, x]),
            "confidence_gap": float(confidence_gap[y, x]),
            "edge": float(edge[y, x]),
            "saturation": float(saturation[y, x]),
            "basis": "environment_saliency_plus_clarity_gap" if allow_unknown else "known_patch_saliency_plus_clarity_gap",
        },
    )


def _summary_focus_xy(summary: dict[str, object], *, fallback: tuple[int, int]) -> tuple[int, int]:
    raw = summary.get("focus_xy")
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)) and len(raw) >= 2:
        return int(raw[0]), int(raw[1])
    return fallback


def _patch_box_contains(summary: object, focus_xy: tuple[int, int]) -> bool:
    if not isinstance(summary, dict):
        return False
    patch_box = summary.get("patch_box")
    if not isinstance(patch_box, Sequence) or isinstance(patch_box, (str, bytes, bytearray)) or len(patch_box) < 4:
        return False
    x1, y1, x2, y2 = [int(value) for value in patch_box[:4]]
    return x1 <= int(focus_xy[0]) < x2 and y1 <= int(focus_xy[1]) < y2


def _write_visual_occurrences(
    conn: sqlite3.Connection,
    *,
    event_id: str,
    source_packet_id: str,
    payload_ref: str,
    focus_xy: tuple[int, int],
    evidence: dict[str, object],
    tick: int,
    canvas: SensoryCanvas,
) -> tuple[str, ...]:
    evidence_hash = _hash_text(str(evidence.get("signature", "")) + "|" + "|".join(str(item) for item in evidence.get("tokens", ())))
    focus_sa = f"vision_focus::{evidence_hash[:12]}::{focus_xy[0]}:{focus_xy[1]}"
    patch_sa = f"vision_patch::{evidence_hash[:12]}::{tick}"
    upsert_sa_type(conn, sa_type_id=focus_sa, substrate="vision", modality="vision", canonical_hint="focus_xy", tick=tick)
    upsert_sa_type(
        conn,
        sa_type_id=patch_sa,
        substrate="vision",
        modality="vision",
        canonical_hint="patch_payload",
        tick=tick,
    )
    focus_occ = insert_occurrence(
        conn,
        event_id=event_id,
        sa_type_id=focus_sa,
        tick=tick,
        substrate="vision",
        position={"space": "image_xy", "x": focus_xy[0], "y": focus_xy[1]},
        r=0.48,
        v=0.0,
        a=0.48,
        p=0.48,
        clarity=1.0,
        source_ref=source_packet_id,
        payload_ref=payload_ref,
    )
    patch_occ = insert_occurrence(
        conn,
        event_id=event_id,
        sa_type_id=patch_sa,
        tick=tick,
        substrate="vision",
        position={"space": "foveated_patch", "focus_x": focus_xy[0], "focus_y": focus_xy[1]},
        r=float(canvas.canvas_confidence.mean()),
        v=0.0,
        a=float(canvas.canvas_clarity.mean()),
        p=1.0 - float(canvas.canvas_confidence.mean()),
        clarity=canvas.clarity_coverage(),
        source_ref=source_packet_id,
        payload_ref=payload_ref,
    )
    insert_structure_edge(
        conn,
        src_occurrence_id=focus_occ,
        dst_occurrence_id=patch_occ,
        edge_type="focus_samples_patch",
        weight=1.0,
        learned_weight=0.0,
        tick=tick,
    )
    return (focus_occ, patch_occ)


def _visual_evidence_from_patch(
    *,
    rgb: np.ndarray,
    canvas: SensoryCanvas,
    focus_xy: tuple[int, int],
    focus_index: int,
) -> dict[str, object]:
    h, w = rgb.shape[:2]
    x, y = int(focus_xy[0]), int(focus_xy[1])
    patch_size = max(12, min(w, h) // 3)
    half = patch_size // 2
    x1 = max(0, x - half)
    y1 = max(0, y - half)
    x2 = min(w, x + half)
    y2 = min(h, y + half)
    patch = rgb[y1:y2, x1:x2]
    if patch.size == 0:
        patch = rgb
    luma = patch[..., 0] * 0.299 + patch[..., 1] * 0.587 + patch[..., 2] * 0.114
    gy, gx = np.gradient(luma)
    edge = np.sqrt(gx * gx + gy * gy)
    saturation = patch.max(axis=2) - patch.min(axis=2)
    mean_rgb = patch.mean(axis=(0, 1))
    dominant = _dominant_color_bucket(mean_rgb)
    tokens = (
        f"xy:{_bucket(x / max(w - 1, 1), 4)}:{_bucket(y / max(h - 1, 1), 4)}",
        f"rgb:{dominant}",
        f"sat:{_bucket(float(saturation.mean()), 5)}",
        f"luma:{_bucket(float(luma.mean()), 5)}",
        f"edge:{_bucket(float(edge.mean()), 5)}",
        f"clarity:{_bucket(float(canvas.clarity_coverage()), 5)}",
    )
    return {
        "signature": "visual_patch_evidence::" + _hash_text("|".join(tokens)),
        "tokens": list(tokens),
        "focus_index": int(focus_index),
        "focus_xy_norm": [
            round(x / max(w - 1, 1), 4),
            round(y / max(h - 1, 1), 4),
        ],
        "dominant_color_bucket": dominant,
        "saturation_bucket": _bucket(float(saturation.mean()), 5),
        "luma_bucket": _bucket(float(luma.mean()), 5),
        "edge_bucket": _bucket(float(edge.mean()), 5),
        "clarity_bucket": _bucket(float(canvas.clarity_coverage()), 5),
    }


def _dominant_color_bucket(mean_rgb: np.ndarray) -> str:
    r, g, b = [float(value) for value in mean_rgb[:3]]
    if max(r, g, b) - min(r, g, b) < 0.08:
        return "gray"
    if r >= g and r >= b:
        return "red" if g < r * 0.78 else "yellow_or_orange"
    if g >= r and g >= b:
        return "green" if r < g * 0.82 else "yellow_green"
    return "blue"


def _bucket(value: float, buckets: int) -> int:
    return int(np.clip(np.floor(float(value) * int(buckets)), 0, int(buckets) - 1))


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _inject_visual_state(pool: StatePool, *, canvas: SensoryCanvas, focus_xy: tuple[int, int], tick: int) -> None:
    item = canvas.to_state_item()
    pool.items[item.sa_id] = item
    pool.observe_external(
        {
            "sa_id": f"vision_focus::{focus_xy[0]}:{focus_xy[1]}::{tick}",
            "family": "visual_focus",
            "label": f"focus:{focus_xy[0]},{focus_xy[1]}",
            "channel_signature": ("vision", "focus"),
            "origin": "visual_patch_sensor",
            "real_energy": 0.42,
            "metadata": {"ledger_source": "external"},
        },
        tick=tick,
    )
    # P5: feeling::curious — FOC-coupled visual novelty (v≠0.0)
    foc_energy = 0.12  # base coupling; elevated when focus moves
    pool.observe_external(
        {
            "sa_id": "feeling::curious",
            "family": "feeling",
            "label": "curious",
            "channel_signature": ("feeling", "visual"),
            "origin": "visual_receptor",
            "real_energy": foc_energy,
            "metadata": {
                "ledger_source": "residual_mass",
                "virtual_energy_hint": round(foc_energy * 0.6, 4),
            },
        },
        tick=tick,
    )
    pool.observe_external(
        {
            "sa_id": "feeling::present",
            "family": "feeling",
            "label": "present",
            "channel_signature": ("feeling", "visual"),
            "origin": "visual_receptor",
            "real_energy": 0.08,
            "metadata": {"ledger_source": "residual_mass"},
        },
        tick=tick,
    )


def _inject_visual_imagination_state(
    pool: StatePool,
    *,
    canvas: SensoryCanvas,
    focus_xy: tuple[int, int],
    tick: int,
    recall_score: float,
) -> None:
    item = canvas.to_state_item()
    item.family = "inner_visual_imagination"
    item.label = "remembered_visual_canvas"
    item.virtual_energy = max(item.virtual_energy, float(recall_score) * 0.52)
    item.attention_energy = max(item.attention_energy, float(canvas.canvas_clarity.mean()) + float(recall_score) * 0.18)
    item.cognitive_pressure = item.real_energy - item.virtual_energy
    item.source = "experience_flow_visual_recall"
    item.channel_signature = ("vision", "imagined", "canvas")
    item.metadata = {
        **item.metadata,
        "epistemic_source": "IMAGINED_FROM_EXPERIENCE_FLOW",
        "raw_source_asset_used": False,
        "recall_score": float(recall_score),
    }
    pool.items[item.sa_id] = item
    pool.observe_external(
        {
            "sa_id": f"vision_imagined_focus::{focus_xy[0]}:{focus_xy[1]}::{tick}",
            "family": "visual_focus",
            "label": f"imagined_focus:{focus_xy[0]},{focus_xy[1]}",
            "channel_signature": ("vision", "imagined", "focus"),
            "origin": "experience_flow_visual_recall",
            "real_energy": max(0.12, min(0.42, float(recall_score) * 0.42)),
            "metadata": {"ledger_source": "replay", "epistemic_source": "IMAGINED_FROM_EXPERIENCE_FLOW"},
        },
        tick=tick,
    )


def _write_inner_picture(canvas: SensoryCanvas, *, db_path: Path, source_hash: str, tick: int) -> dict[str, object]:
    out_dir = db_path.parent / "phase20_7_inner_pictures"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"inner_{source_hash[:16]}_{tick:04d}.png"
    image = _render_inner_picture_from_canvas_state(canvas)
    image.save(path)
    return {
        "source": "sensory_canvas_patch_payload",
        "path": str(path),
        "focus_xy": list(canvas.last_fixation_xy),
        "clarity_coverage": canvas.clarity_coverage(),
        "rendered_from_state_pool_canvas": True,
        "raw_source_asset_used_for_render": False,
        "source_image_hash": source_hash,
        "recognition_label": None,
    }


def _render_inner_picture_from_canvas_state(canvas: SensoryCanvas) -> Image.Image:
    pixels = np.clip(canvas.canvas_pixels, 0.0, 1.0)
    clarity = np.clip(canvas.canvas_clarity, 0.0, 1.0)
    confidence = np.clip(canvas.canvas_confidence, 0.0, 1.0)
    yy, xx = np.indices(clarity.shape)
    fx, fy = int(canvas.last_fixation_xy[0]), int(canvas.last_fixation_xy[1])
    dist = np.sqrt((xx - fx) ** 2 + (yy - fy) ** 2)
    foveal = np.exp(-(dist * dist) / max(2.0 * (max(8.0, min(clarity.shape) / 8.0) ** 2), 1e-6))
    sample_gate = (clarity > 0.36) | ((clarity > 0.09) & (((xx + yy + int(canvas.tick)) % 4) == 0))
    alpha = np.clip((confidence * 1.72 + clarity * 0.56) * (0.44 + 0.66 * foveal), 0.0, 0.98)
    alpha = np.where(sample_gate, alpha, alpha * 0.22)
    neutral = np.full_like(pixels, 0.90, dtype=np.float32)
    rendered = neutral * (1.0 - alpha[..., None]) + pixels * alpha[..., None]
    rendered = np.where(sample_gate[..., None], rendered, neutral * 0.88 + pixels * 0.12)
    rendered = np.uint8(np.clip(rendered, 0.0, 1.0) * 255.0)
    image = Image.fromarray(rendered, mode="RGB")
    _draw_focus_marker(image, canvas.last_fixation_xy)
    return image


def _draw_focus_marker(image: Image.Image, focus_xy: tuple[int, int]) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    x, y = int(focus_xy[0]), int(focus_xy[1])
    radius = max(4, min(image.size) // 22)
    color = (29, 63, 95)
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, width=2)
    draw.line((x - radius * 2, y, x - radius, y), fill=color, width=1)
    draw.line((x + radius, y, x + radius * 2, y), fill=color, width=1)
    draw.line((x, y - radius * 2, x, y - radius), fill=color, width=1)
    draw.line((x, y + radius, x, y + radius * 2), fill=color, width=1)


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _patch_payload_rows_by_refs(
    conn: sqlite3.Connection,
    payload_refs: Sequence[str],
) -> tuple[dict[str, object], ...]:
    ordered_refs = [str(ref) for ref in payload_refs if str(ref)]
    if not ordered_refs:
        return ()
    placeholders = ",".join("?" for _ in ordered_refs)
    rows = conn.execute(
        f"""
        SELECT payload_ref, bytes, summary_json, source_hash, created_tick
        FROM phase20_7_payload_blobs
        WHERE payload_ref IN ({placeholders})
          AND media_type='image'
          AND bytes IS NOT NULL
        """,
        tuple(ordered_refs),
    ).fetchall()
    by_ref: dict[str, dict[str, object]] = {}
    for payload_ref, blob_bytes, summary_json, source_hash, created_tick in rows:
        summary = from_json(str(summary_json))
        if not isinstance(summary, dict):
            continue
        by_ref[str(payload_ref)] = {
            "event_id": "",
            "tick": int(created_tick),
            "payload_ref": str(payload_ref),
            "bytes": blob_bytes,
            "summary": summary,
            "payload": {"payload_ref": str(payload_ref)},
            "source_hash": str(source_hash),
        }
    return tuple(by_ref[ref] for ref in ordered_refs if ref in by_ref)
