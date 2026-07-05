from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any, Callable, Sequence

from .experience_candidate import compute_unified_experience_support


@dataclass(frozen=True)
class ExperienceFlowCandidate:
    candidate_id: str
    candidate_kind: str
    event_id: str
    tick: int
    source_packet_id: str
    source_kind: str
    text: str
    text_signature: str | None
    visual_signature: str | None
    occurrence_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    payload_refs: tuple[str, ...]
    alignment_event_id: str | None
    support: float
    support_terms: tuple[tuple[str, float], ...]
    cause_slots: tuple[dict[str, Any], ...]
    payload: dict[str, Any]


def query_recent_experience_flow_candidates(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    from_json: Callable[[str], Any],
    hash_text: Callable[[str], str],
    signature_for_chars: Callable[[tuple[str, ...]], str],
    compose_input_signature: Callable[[str, str | None], str],
    visual_tokens_from_payloads: Callable[[Sequence[dict[str, Any]]], tuple[str, str]],
    limit: int = 24,
) -> tuple[ExperienceFlowCandidate, ...]:
    # §185 性能护栏: 同一 tick 内该窗口被召回/归因/成功者/外显等 100+ 处消费, 但
    # 窗口内容只随经验流写入变化 — 以 (session, limit, 最新 rowid) 为键做进程内
    # memo. 任何新事件写入 → max(rowid) 变化 → 自动失效, 结果与不缓存完全一致
    # (纯读派生, §132 可重建; 不是答案缓存 — 缓存的是"最近经验窗口"这一确定性投影).
    cache_key = None
    cache = getattr(conn, "_apv3_flow_window_cache", None)
    row = conn.execute(
        "SELECT MAX(rowid), COUNT(*) FROM phase20_7_experience_events WHERE session_id=?",
        (session_id,),
    ).fetchone()
    latest_marker = (int(row[0] or 0), int(row[1] or 0)) if row else (0, 0)
    cache_key = (str(session_id), int(limit), latest_marker)
    if isinstance(cache, dict) and cache.get("key") == cache_key:
        return cache["value"]
    result = _query_recent_experience_flow_candidates_uncached(
        conn,
        session_id=session_id,
        from_json=from_json,
        hash_text=hash_text,
        signature_for_chars=signature_for_chars,
        compose_input_signature=compose_input_signature,
        visual_tokens_from_payloads=visual_tokens_from_payloads,
        limit=limit,
    )
    try:
        conn._apv3_flow_window_cache = {"key": cache_key, "value": result}  # type: ignore[attr-defined]
    except AttributeError:
        pass
    return result


def _query_recent_experience_flow_candidates_uncached(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    from_json: Callable[[str], Any],
    hash_text: Callable[[str], str],
    signature_for_chars: Callable[[tuple[str, ...]], str],
    compose_input_signature: Callable[[str, str | None], str],
    visual_tokens_from_payloads: Callable[[Sequence[dict[str, Any]]], tuple[str, str]],
    limit: int = 24,
) -> tuple[ExperienceFlowCandidate, ...]:
    rows = conn.execute(
        """
        SELECT event_id, source_packet_id, event_kind, payload_json, reward, punish, tick, created_at_ms
        FROM phase20_7_experience_events
        WHERE session_id=?
          AND event_kind IN (
            'text_receptor_observation',
            'visual_patch_sample',
            'visual_imagination_recall',
            'audio_audit_sample',
            'audio_inner_rehearsal',
            'idle_think',
            'idle_observe'
          )
        ORDER BY created_at_ms DESC, tick DESC
        LIMIT ?
        """,
        (session_id, int(limit)),
    ).fetchall()
    candidates: list[ExperienceFlowCandidate] = []
    visual_cluster: list[tuple[str, str, dict[str, Any], int]] = []
    for row in rows:
        event_id, source_packet_id, event_kind, payload_json, reward, punish, tick, _created_at = row
        payload = from_json(str(payload_json))
        if not isinstance(payload, dict):
            continue
        kind = str(event_kind)
        if kind in {"visual_patch_sample", "visual_imagination_recall"}:
            visual_cluster.append((str(event_id), str(source_packet_id or ""), payload, int(tick)))
            continue
        if visual_cluster:
            candidates.append(
                _visual_cluster_candidate(
                    conn,
                    visual_cluster,
                    from_json=from_json,
                    hash_text=hash_text,
                    signature_for_chars=signature_for_chars,
                    compose_input_signature=compose_input_signature,
                    visual_tokens_from_payloads=visual_tokens_from_payloads,
                    recency_rank=len(candidates),
                )
            )
            visual_cluster = []
        candidates.append(
            _event_candidate(
                conn,
                event_id=str(event_id),
                source_packet_id=str(source_packet_id or ""),
                event_kind=kind,
                payload=payload,
                tick=int(tick),
                reward=float(reward or 0.0),
                punish=float(punish or 0.0),
                recency_rank=len(candidates),
                from_json=from_json,
                hash_text=hash_text,
                signature_for_chars=signature_for_chars,
                compose_input_signature=compose_input_signature,
            )
        )
    if visual_cluster:
        candidates.append(
            _visual_cluster_candidate(
                conn,
                visual_cluster,
                from_json=from_json,
                hash_text=hash_text,
                signature_for_chars=signature_for_chars,
                compose_input_signature=compose_input_signature,
                visual_tokens_from_payloads=visual_tokens_from_payloads,
                recency_rank=len(candidates),
            )
        )
    candidates.extend(
        _short_structure_next_candidates(
            conn,
            session_id=session_id,
            from_json=from_json,
            hash_text=hash_text,
            signature_for_chars=signature_for_chars,
            recency_start=len(candidates),
            limit=max(1, int(limit)),
        )
    )
    return tuple(candidate for candidate in candidates if candidate.event_id)


def _short_structure_next_candidates(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    from_json: Callable[[str], Any],
    hash_text: Callable[[str], str],
    signature_for_chars: Callable[[tuple[str, ...]], str],
    recency_start: int,
    limit: int,
) -> tuple[ExperienceFlowCandidate, ...]:
    rows = conn.execute(
        """
        SELECT
          edge.edge_id, edge.src_occurrence_id, edge.dst_occurrence_id,
          edge.weight, edge.learned_weight, edge.updated_tick,
          src_event.event_id, src_event.source_packet_id, src_event.payload_json,
          dst_event.event_id, dst_event.source_packet_id, dst_event.payload_json,
          src_type.canonical_hint, dst_type.canonical_hint,
          src.R, src.V, src.A, src.P, src.clarity,
          dst.R, dst.V, dst.A, dst.P, dst.clarity,
          src.position_json, dst.position_json
        FROM phase20_7_structure_edges edge
        JOIN phase20_7_occurrences src ON src.occurrence_id=edge.src_occurrence_id
        JOIN phase20_7_occurrences dst ON dst.occurrence_id=edge.dst_occurrence_id
        JOIN phase20_7_experience_events src_event ON src_event.event_id=src.event_id
        JOIN phase20_7_experience_events dst_event ON dst_event.event_id=dst.event_id
        JOIN phase20_7_sa_types src_type ON src_type.sa_type_id=src.sa_type_id
        JOIN phase20_7_sa_types dst_type ON dst_type.sa_type_id=dst.sa_type_id
        WHERE edge.edge_type='short_structure_next'
          AND dst_event.session_id=?
          AND dst.sa_type_id >= 'short_structure_flow::'
          AND dst.sa_type_id < 'short_structure_flow:;'
        ORDER BY edge.updated_tick DESC
        LIMIT ?
        """,
        (session_id, int(limit)),
    ).fetchall()
    out: list[ExperienceFlowCandidate] = []
    for rank, row in enumerate(rows):
        (
            edge_id,
            src_occurrence_id,
            dst_occurrence_id,
            weight,
            learned_weight,
            updated_tick,
            src_event_id,
            src_packet_id,
            src_payload_json,
            dst_event_id,
            dst_packet_id,
            dst_payload_json,
            src_hint,
            dst_hint,
            src_r,
            src_v,
            src_a,
            src_p,
            src_clarity,
            dst_r,
            dst_v,
            dst_a,
            dst_p,
            dst_clarity,
            src_position_json,
            dst_position_json,
        ) = row
        src_payload = from_json(str(src_payload_json))
        dst_payload = from_json(str(dst_payload_json))
        src_position = from_json(str(src_position_json))
        dst_position = from_json(str(dst_position_json))
        src_text = _flow_hint_text(str(src_hint or ""), src_payload if isinstance(src_payload, dict) else {}, src_position if isinstance(src_position, dict) else {})
        dst_text = _flow_hint_text(str(dst_hint or ""), dst_payload if isinstance(dst_payload, dict) else {}, dst_position if isinstance(dst_position, dict) else {})
        text = " -> ".join(part for part in (src_text, dst_text) if part).strip()
        if not text:
            text = "short_structure_next"
        chars = tuple(text)
        text_signature = signature_for_chars(chars) if chars else None
        src_energy = _row_energy(src_r, src_v, src_a, src_p, src_clarity)
        dst_energy = _row_energy(dst_r, dst_v, dst_a, dst_p, dst_clarity)
        edge_support = max(0.0, min(1.0, float(weight or 0.0) * 0.45 + float(learned_weight or 0.0) * 0.25))
        support, support_terms = compute_unified_experience_support(
            structural_similarity=edge_support,
            occurrence_energy=max(src_energy, dst_energy),
            recency=1.0 / (1.0 + recency_start + rank),
            modality_match=1.0,
        )
        source_kind = "short_structure_flow_next"
        source_flow_kind = str((src_position if isinstance(src_position, dict) else {}).get("source_kind") or "")
        target_flow_kind = str((dst_position if isinstance(dst_position, dict) else {}).get("source_kind") or "")
        source_intent = str((src_position if isinstance(src_position, dict) else {}).get("source_intent") or "")
        target_intent = str((dst_position if isinstance(dst_position, dict) else {}).get("source_intent") or "")
        src_draft_context = (
            dict(src_payload.get("draftgrid_action_drive_context"))
            if isinstance(src_payload, dict) and isinstance(src_payload.get("draftgrid_action_drive_context"), dict)
            else {}
        )
        dst_draft_context = (
            dict(dst_payload.get("draftgrid_action_drive_context"))
            if isinstance(dst_payload, dict) and isinstance(dst_payload.get("draftgrid_action_drive_context"), dict)
            else {}
        )
        source_pending_output_count = _safe_int(src_draft_context.get("pending_output_unit_count"))
        target_pending_output_count = _safe_int(dst_draft_context.get("pending_output_unit_count"))
        source_pending_successor_pressure = _safe_float(src_draft_context.get("pending_successor_pressure"))
        target_pending_successor_pressure = _safe_float(dst_draft_context.get("pending_successor_pressure"))
        cause_slots = (
            {"slot_kind": "experience_flow_candidate", "source_kind": source_kind},
            {
                "slot_kind": "short_structure_next_edge",
                "edge_id": str(edge_id),
                "src_occurrence_id": str(src_occurrence_id),
                "dst_occurrence_id": str(dst_occurrence_id),
                "edge_support": round(edge_support, 4),
            },
            {
                "slot_kind": "short_structure_flow_text",
                "source_text": src_text,
                "target_text": dst_text,
                "source_flow_kind": source_flow_kind,
                "target_flow_kind": target_flow_kind,
                "source_intent": source_intent,
                "target_intent": target_intent,
                "source_pending_output_unit_count": source_pending_output_count,
                "target_pending_output_unit_count": target_pending_output_count,
                "source_pending_successor_pressure": round(source_pending_successor_pressure, 4),
                "target_pending_successor_pressure": round(target_pending_successor_pressure, 4),
                "private_thought": bool(_position_private(dst_position if isinstance(dst_position, dict) else {})),
            },
        )
        out.append(
            ExperienceFlowCandidate(
                candidate_id=f"flow::short_structure_next::{edge_id}",
                candidate_kind=source_kind,
                event_id=str(dst_event_id),
                tick=int(updated_tick),
                source_packet_id=str(dst_packet_id or src_packet_id or ""),
                source_kind=source_kind,
                text=text,
                text_signature=text_signature,
                visual_signature=None,
                occurrence_ids=(str(src_occurrence_id), str(dst_occurrence_id)),
                edge_ids=(str(edge_id),),
                payload_refs=(),
                alignment_event_id=None,
                support=support,
                support_terms=support_terms + (("short_structure_edge_support", edge_support),),
                cause_slots=cause_slots,
                payload={
                    "flow_edge_type": "short_structure_next",
                    "source_occurrence_id": str(src_occurrence_id),
                    "target_occurrence_id": str(dst_occurrence_id),
                    "source_event_id": str(src_event_id),
                    "target_event_id": str(dst_event_id),
                    "source_text": src_text,
                    "target_text": dst_text,
                    "source_flow_kind": source_flow_kind,
                    "target_flow_kind": target_flow_kind,
                    "source_intent": source_intent,
                    "target_intent": target_intent,
                    "source_pending_output_unit_count": source_pending_output_count,
                    "target_pending_output_unit_count": target_pending_output_count,
                    "source_pending_successor_pressure": round(source_pending_successor_pressure, 4),
                    "target_pending_successor_pressure": round(target_pending_successor_pressure, 4),
                    "text": text,
                    "private_thought": bool(_position_private(dst_position if isinstance(dst_position, dict) else {})),
                },
            )
        )
    return tuple(out)


def _event_candidate(
    conn: sqlite3.Connection,
    *,
    event_id: str,
    source_packet_id: str,
    event_kind: str,
    payload: dict[str, Any],
    tick: int,
    reward: float,
    punish: float,
    recency_rank: int,
    from_json: Callable[[str], Any],
    hash_text: Callable[[str], str],
    signature_for_chars: Callable[[tuple[str, ...]], str],
    compose_input_signature: Callable[[str, str | None], str],
) -> ExperienceFlowCandidate:
    text = str(payload.get("text") or payload.get("source_text") or payload.get("narrative_text") or "")
    chars = tuple(text)
    text_signature = str(payload.get("text_signature") or signature_for_chars(chars)) if chars else None
    visual_signature = str(payload.get("visual_signature") or "") or None
    occurrence_ids = _occurrence_ids(conn, event_id)
    edge_ids = _edge_ids(conn, occurrence_ids)
    payload_refs = _payload_refs(conn, event_id, payload)
    source_kind = {
        "text_receptor_observation": "recent_text_window",
        "audio_audit_sample": "recent_audio_window",
        "audio_inner_rehearsal": "recent_audio_window",
        "idle_think": "idle_think_window",
        "idle_observe": "idle_observe_window",
    }.get(event_kind, event_kind)
    support, support_terms = _support_from_occurrences(
        conn,
        occurrence_ids,
        recency_rank=recency_rank,
        reward=reward,
        punish=punish,
        payload_refs=payload_refs,
        has_text=bool(text),
        has_visual=bool(visual_signature),
    )
    cause_slots = _cause_slots(
        text_signature=text_signature,
        visual_signature=visual_signature,
        occurrence_ids=occurrence_ids,
        payload_refs=payload_refs,
        source_kind=source_kind,
    )
    return ExperienceFlowCandidate(
        candidate_id=f"flow::{event_id}",
        candidate_kind=source_kind,
        event_id=event_id,
        tick=tick,
        source_packet_id=source_packet_id,
        source_kind=source_kind,
        text=text,
        text_signature=text_signature,
        visual_signature=visual_signature,
        occurrence_ids=occurrence_ids,
        edge_ids=edge_ids,
        payload_refs=payload_refs,
        alignment_event_id=None,
        support=support,
        support_terms=support_terms,
        cause_slots=cause_slots,
        payload=payload,
    )


def _visual_cluster_candidate(
    conn: sqlite3.Connection,
    rows: Sequence[tuple[str, str, dict[str, Any], int]],
    *,
    from_json: Callable[[str], Any],
    hash_text: Callable[[str], str],
    signature_for_chars: Callable[[tuple[str, ...]], str],
    compose_input_signature: Callable[[str, str | None], str],
    visual_tokens_from_payloads: Callable[[Sequence[dict[str, Any]]], tuple[str, str]],
    recency_rank: int,
) -> ExperienceFlowCandidate:
    event_ids = tuple(row[0] for row in rows)
    payloads = tuple(row[2] for row in rows)
    text = "visual_focus_anchor"
    text_signature = signature_for_chars(tuple(text))
    visual_signature, token_text = visual_tokens_from_payloads(payloads)
    occurrence_ids: list[str] = []
    payload_refs: list[str] = []
    for event_id, _packet_id, payload, _tick in rows:
        occurrence_ids.extend(_occurrence_ids(conn, event_id))
        payload_refs.extend(_payload_refs(conn, event_id, payload))
    edge_ids = _edge_ids(conn, tuple(occurrence_ids))
    source_packet_id = rows[-1][1]
    support, support_terms = _support_from_occurrences(
        conn,
        tuple(occurrence_ids),
        recency_rank=recency_rank,
        reward=0.0,
        punish=0.0,
        payload_refs=tuple(payload_refs),
        has_text=bool(text),
        has_visual=bool(visual_signature),
    )
    cause_slots = _cause_slots(
        text_signature=text_signature,
        visual_signature=visual_signature,
        occurrence_ids=tuple(occurrence_ids),
        payload_refs=tuple(payload_refs),
        source_kind="recent_visual_window",
    )
    return ExperienceFlowCandidate(
        candidate_id="flow::visual_cluster::" + hash_text("|".join(event_ids)),
        candidate_kind="recent_visual_window",
        event_id=event_ids[-1],
        tick=int(rows[-1][3]),
        source_packet_id=source_packet_id,
        source_kind="recent_visual_window",
        text=text,
        text_signature=text_signature,
        visual_signature=visual_signature,
        occurrence_ids=tuple(occurrence_ids),
        edge_ids=edge_ids,
        payload_refs=tuple(dict.fromkeys(payload_refs)),
        alignment_event_id=None,
        support=support,
        support_terms=support_terms,
        cause_slots=cause_slots + ({"slot_kind": "visual_tokens", "tokens": token_text.split(",")[:12]},),
        payload={"event_ids": list(event_ids), "visual_signature": visual_signature},
    )


def _occurrence_ids(conn: sqlite3.Connection, event_id: str) -> tuple[str, ...]:
    rows = conn.execute(
        "SELECT occurrence_id FROM phase20_7_occurrences WHERE event_id=? ORDER BY tick ASC",
        (event_id,),
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _edge_ids(conn: sqlite3.Connection, occurrence_ids: Sequence[str]) -> tuple[str, ...]:
    if not occurrence_ids:
        return ()
    placeholders = ",".join("?" for _ in occurrence_ids)
    rows = conn.execute(
        f"""
        SELECT edge_id
        FROM phase20_7_structure_edges
        WHERE src_occurrence_id IN ({placeholders})
           OR dst_occurrence_id IN ({placeholders})
        ORDER BY updated_tick ASC
        """,
        tuple(occurrence_ids) + tuple(occurrence_ids),
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _payload_refs(conn: sqlite3.Connection, event_id: str, payload: dict[str, Any]) -> tuple[str, ...]:
    refs: list[str] = []
    for key in ("payload_ref", "peripheral_gist_payload_ref", "borrowed_patch_payload_refs", "reconstructed_from_payload_refs"):
        value = payload.get(key)
        if isinstance(value, str):
            refs.append(value)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            refs.extend(str(item) for item in value if str(item))
    rows = conn.execute(
        """
        SELECT payload_ref
        FROM phase20_7_occurrences
        WHERE event_id=? AND payload_ref IS NOT NULL
        ORDER BY tick ASC
        """,
        (event_id,),
    ).fetchall()
    refs.extend(str(row[0]) for row in rows if row[0])
    return tuple(dict.fromkeys(refs))


def _row_energy(r: Any, v: Any, a: Any, p: Any, clarity: Any) -> float:
    values: list[float] = []
    for value in (r, v, a, p, clarity):
        try:
            values.append(abs(float(value or 0.0)))
        except (TypeError, ValueError):
            values.append(0.0)
    return max(0.0, min(1.0, sum(values) / 5.0))


def _flow_hint_text(hint: str, payload: dict[str, Any], position: dict[str, Any]) -> str:
    for key in ("narrative_text", "text", "source_text", "target_text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    text_hash = position.get("text_hash")
    if hint.strip():
        return hint.strip()
    return str(text_hash or "").strip()


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _position_private(position: dict[str, Any]) -> bool:
    value = position.get("private_thought")
    if isinstance(value, bool):
        return value
    metadata = position.get("metadata")
    if isinstance(metadata, dict):
        return bool(metadata.get("private_thought", False))
    return False


def _support_from_occurrences(
    conn: sqlite3.Connection,
    occurrence_ids: Sequence[str],
    *,
    recency_rank: int,
    reward: float,
    punish: float,
    payload_refs: Sequence[str],
    has_text: bool,
    has_visual: bool,
) -> tuple[float, tuple[tuple[str, float], ...]]:
    if occurrence_ids:
        placeholders = ",".join("?" for _ in occurrence_ids)
        rows = conn.execute(
            f"""
            SELECT AVG(ABS(R) + ABS(V) + ABS(A) + ABS(P) + ABS(clarity))
            FROM phase20_7_occurrences
            WHERE occurrence_id IN ({placeholders})
            """,
            tuple(occurrence_ids),
        ).fetchone()
        energy = float(rows[0] or 0.0) / 5.0 if rows else 0.0
    else:
        energy = 0.12
    recency = 1.0 / (1.0 + max(0, int(recency_rank)))
    return compute_unified_experience_support(
        occurrence_energy=energy,
        recency=recency,
        payload_presence=1.0 if payload_refs else 0.0,
        modality_match=1.0 if has_text or has_visual else 0.0,
        reward=reward,
        punish=punish,
    )


def _cause_slots(
    *,
    text_signature: str | None,
    visual_signature: str | None,
    occurrence_ids: Sequence[str],
    payload_refs: Sequence[str],
    source_kind: str,
) -> tuple[dict[str, Any], ...]:
    slots: list[dict[str, Any]] = [{"slot_kind": "experience_flow_candidate", "source_kind": source_kind}]
    if text_signature:
        slots.append({"slot_kind": "text_structure_before_current", "signature": text_signature, "virtual_energy": 0.32})
    if visual_signature:
        slots.append({"slot_kind": "visual_structure_before_current", "signature": visual_signature, "virtual_energy": 0.48})
    if occurrence_ids:
        slots.append({"slot_kind": "occurrence_trace", "count": len(tuple(occurrence_ids))})
    if payload_refs:
        slots.append({"slot_kind": "payload_trace", "payload_ref_count": len(tuple(payload_refs))})
    return tuple(slots)
