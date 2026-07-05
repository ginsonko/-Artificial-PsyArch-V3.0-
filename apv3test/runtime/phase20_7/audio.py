from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
import wave
from typing import Sequence

from runtime.cognitive.state_pool.state_pool import StatePool

from .experience_log import (
    insert_action_record,
    insert_experience_event,
    insert_payload_blob,
    insert_source_packet,
)
from .models import MediaInput, RuntimeTickEventV2


def run_audio_audit_ticks(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    media_inputs: Sequence[MediaInput],
    start_tick: int,
) -> tuple[tuple[RuntimeTickEventV2, ...], int]:
    events: list[RuntimeTickEventV2] = []
    tick = int(start_tick)
    for media in [item for item in media_inputs if item.media_type == "audio" and item.path]:
        path = Path(str(media.path))
        if not path.exists():
            continue
        data = path.read_bytes()
        source_hash = hashlib.sha256(data).hexdigest()
        duration_ms = _wav_duration_ms(path)
        tick += 1
        payload_ref = insert_payload_blob(
            conn,
            payload_kind="audio_audit_payload",
            media_type="audio",
            blob_bytes=None,
            summary={
                "source_hash": source_hash,
                "byte_length": len(data),
                "duration_ms": duration_ms,
                "audit_only": True,
                "semantic_label": None,
            },
            source_hash=source_hash,
            tick=tick,
        )
        source_packet_id = insert_source_packet(
            conn,
            source_kind="audio_audit_sensor",
            source_ref=f"audio_hash::{source_hash[:16]}",
            source_context="open_dialogue_audio",
            modality="audio",
            trust_snapshot=0.5,
            tick=tick,
            payload={"source_hash": source_hash, "duration_ms": duration_ms, "raw_path_stored": False},
        )
        action_record_id = insert_action_record(
            conn,
            session_id=session_id,
            tick=tick,
            action_type="audio_audit_sensor",
            selected=True,
            drive=0.58,
            eligibility={"audit_only": True, "local_file": True},
            target_refs={"payload_ref": payload_ref},
        )
        event_id = insert_experience_event(
            conn,
            session_id=session_id,
            tick=tick,
            event_kind="audio_audit_sample",
            source_packet_id=source_packet_id,
            action_record_id=action_record_id,
            payload={
                "payload_ref": payload_ref,
                "source_hash": source_hash,
                "duration_ms": duration_ms,
                "audit_only": True,
                "semantic_label": None,
            },
        )
        conn.execute(
            "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
            (event_id, action_record_id),
        )
        _inject_audio_state(pool, tick=tick, source_hash=source_hash, duration_ms=duration_ms)
        events.append(
            RuntimeTickEventV2(
                tick=tick,
                session_id=session_id,
                external_inputs=(
                    {
                        "input_kind": "audio",
                        "source_hash": source_hash,
                        "raw_path_stored": False,
                    },
                ),
                receptor_outputs=(
                    {
                        "receptor": "audio_audit_sensor",
                        "event_id": event_id,
                        "payload_ref": payload_ref,
                        "duration_ms": duration_ms,
                        "audit_only": True,
                    },
                ),
                state_pool_top=pool.snapshot_top(limit=12),
                audio_inner_sketch={
                    "source": "audio_audit_only",
                    "duration_ms": duration_ms,
                    "semantic_label": None,
                },
                action_competition=(
                    {"action_type": "audio_audit_sensor", "drive": 0.58, "selected": True},
                    {"action_type": "request_teacher", "drive": 0.12, "selected": False},
                ),
                selected_action={"action_type": "audio_audit_sensor", "audit_only": True},
                experience_event_ids_written=(event_id,),
                source_refs=({"source_packet_id": source_packet_id, "source_kind": "audio_audit_sensor"},),
                action_record_ids=(action_record_id,),
                timings_ms={"audio_audit_tick": 0.0},
            )
        )
    return tuple(events), tick


def run_idle_audio_focus_tick(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    start_tick: int,
) -> tuple[RuntimeTickEventV2 | None, int]:
    row = conn.execute(
        """
        SELECT e.event_id, e.payload_json, e.tick
        FROM phase20_7_experience_events e
        WHERE e.session_id=? AND e.event_kind='audio_audit_sample'
        ORDER BY e.tick DESC, e.created_at_ms DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        return None, int(start_tick)
    event_ref, payload_json, source_tick = row
    from .experience_log import from_json

    payload = from_json(str(payload_json))
    if not isinstance(payload, dict):
        return None, int(start_tick)
    tick = int(start_tick) + 1
    duration_ms = payload.get("duration_ms")
    source_hash = str(payload.get("source_hash", "") or "audio_patch")
    elapsed = max(0, tick - int(source_tick or 0))
    inner_energy = max(0.12, min(0.62, 0.48 * (0.94 ** min(elapsed, 40))))
    _inject_audio_state(pool, tick=tick, source_hash=source_hash, duration_ms=float(duration_ms) if duration_ms else None)
    action_record_id = insert_action_record(
        conn,
        session_id=session_id,
        tick=tick,
        action_type="idle_audio_focus",
        selected=True,
        drive=inner_energy,
        eligibility={
            "no_external_input": True,
            "recent_audio_trace": True,
            "semantic_label_used": False,
        },
        target_refs={"source_event_id": str(event_ref), "payload_ref": str(payload.get("payload_ref", "") or "")},
    )
    event_id = insert_experience_event(
        conn,
        session_id=session_id,
        tick=tick,
        event_kind="audio_inner_rehearsal",
        action_record_id=action_record_id,
        payload={
            "source_event_id": str(event_ref),
            "source_hash": source_hash,
            "duration_ms": duration_ms,
            "inner_energy": inner_energy,
            "semantic_label": None,
            "raw_audio_played": False,
        },
    )
    conn.execute(
        "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
        (event_id, action_record_id),
    )
    event = RuntimeTickEventV2(
        tick=tick,
        session_id=session_id,
        receptor_outputs=(
            {
                "receptor": "audio_inner_focus",
                "event_id": event_id,
                "source_event_id": str(event_ref),
                "duration_ms": duration_ms,
                "semantic_label": None,
            },
        ),
        state_pool_top=pool.snapshot_top(limit=12),
        ssp_active_summary={
            "structure_kind": "audio_temporal_focus_flow",
            "source_event_id": str(event_ref),
            "inner_energy": inner_energy,
        },
        c_forward=(
            {
                "kind": "audio_temporal_prediction",
                "prediction": "recent_sound_trace_decays_unless_refocused_or_reheard",
                "support": round(inner_energy, 4),
            },
        ),
        c_backward=(
            {
                "kind": "every_tick_backward_min_error",
                "selected_source_kind": "recent_audio_audit_sample",
                "cause_slots": [{"slot_kind": "recent_audio_trace", "source_event_id": str(event_ref)}],
                "neutralized_occurrences": [{"occurrence_id": f"audio_audit::{source_hash[:16]}", "neutralize": round(inner_energy, 4)}],
                "cause_grasp": round(inner_energy, 4),
                "e_backward": round(1.0 - inner_energy, 4),
                "subjective": True,
                "may_be_wrong": True,
            },
        ),
        selected_action={"action_type": "idle_audio_focus", "private_inner_audio": True},
        action_competition=(
            {"action_type": "idle_audio_focus", "drive": inner_energy, "selected": True},
            {"action_type": "idle_think", "drive": 0.28, "selected": False},
            {"action_type": "idle_observe", "drive": 0.18, "selected": False},
        ),
        audio_inner_sketch={
            "source": "recent_audio_audit_trace",
            "duration_ms": duration_ms,
            "inner_energy": inner_energy,
            "semantic_label": None,
            "raw_audio_played": False,
        },
        feelings={"idle": True, "attention_target": "audio_focus", "inner_audio_energy": inner_energy},
        experience_event_ids_written=(event_id,),
        action_record_ids=(action_record_id,),
        timings_ms={"idle_audio_focus_tick": 0.0},
    )
    return event, tick


def estimate_idle_audio_drive(conn: sqlite3.Connection, *, session_id: str) -> float:
    row = conn.execute(
        """
        SELECT e.tick
        FROM phase20_7_experience_events e
        WHERE e.session_id=? AND e.event_kind IN ('audio_audit_sample', 'audio_inner_rehearsal')
        ORDER BY e.tick DESC, e.created_at_ms DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        return 0.0
    latest_tick = int(row[0] or 0)
    kind_row = conn.execute(
        """
        SELECT event_kind
        FROM phase20_7_experience_events
        WHERE session_id=? AND tick=?
        ORDER BY created_at_ms DESC
        LIMIT 1
        """,
        (session_id, latest_tick),
    ).fetchone()
    fatigue = 0.14 if kind_row and str(kind_row[0]) == "audio_inner_rehearsal" else 0.0
    return max(0.0, min(0.58, 0.52 - fatigue))


def record_tts_actuator_tick(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    tick: int,
    reply_text: str,
) -> RuntimeTickEventV2:
    voice = select_xiaoyi_voice()
    action_record_id = insert_action_record(
        conn,
        session_id=session_id,
        tick=tick,
        action_type="reply_tts_audio",
        selected=True,
        drive=0.62,
        eligibility={"local_only": True, "reply_text_present": bool(reply_text)},
        target_refs={"reply_text_hash": _hash_text(reply_text), "voice_id": voice["voice_id"]},
    )
    event_id = insert_experience_event(
        conn,
        session_id=session_id,
        tick=tick,
        event_kind="reply_tts_audio",
        action_record_id=action_record_id,
        payload={
            "reply_text_hash": _hash_text(reply_text),
            "voice_preference": "xiaoyi",
            "voice_id": voice["voice_id"],
            "voice_name": voice["voice_name"],
            "local_only": True,
            "synthesized_now": False,
        },
    )
    conn.execute(
        "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
        (event_id, action_record_id),
    )
    _inject_tts_state(pool, tick=tick, voice_name=voice["voice_name"])
    return RuntimeTickEventV2(
        tick=tick,
        session_id=session_id,
        state_pool_top=pool.snapshot_top(limit=12),
        selected_action={
            "action_type": "reply_tts_audio",
            "voice_preference": "xiaoyi",
            "voice_id": voice["voice_id"],
            "local_only": True,
        },
        action_competition=(
            {"action_type": "reply_tts_audio", "drive": 0.62, "selected": True},
            {"action_type": "stop_generating", "drive": 0.2, "selected": False},
        ),
        audio_inner_sketch=None,
        experience_event_ids_written=(event_id,),
        action_record_ids=(action_record_id,),
        timings_ms={"reply_tts_audio": 0.0},
    )


def select_xiaoyi_voice() -> dict[str, str]:
    voices = _pyttsx3_voices()
    for voice in voices:
        joined = f"{voice.get('id', '')} {voice.get('name', '')}".lower()
        if "xiaoyi" in joined or "xiao yi" in joined or "晓伊" in joined or "晓艺" in joined:
            return {"voice_id": str(voice.get("id", "xiaoyi")), "voice_name": str(voice.get("name", "xiaoyi"))}
    return {"voice_id": "xiaoyi_not_available_in_local_sapi", "voice_name": "xiaoyi"}


def synthesize_xiaoyi_tts(reply_text: str, *, out_dir: str | Path) -> dict[str, str | bool | int]:
    """Create a local playback file for a reply_tts_audio actuator request."""

    text = str(reply_text or "").strip()
    if not text:
        raise ValueError("empty_reply_text")
    if len(text) > 240:
        text = text[:240]
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    voice = select_xiaoyi_voice()
    digest = hashlib.sha256(f"{voice['voice_id']}|{text}".encode("utf-8")).hexdigest()[:16]
    wav_path = out_path / f"phase20_7_xiaoyi_{digest}.wav"
    if wav_path.exists() and wav_path.stat().st_size > 0:
        return {
            "path": str(wav_path),
            "voice_id": voice["voice_id"],
            "voice_name": voice["voice_name"],
            "local_only": True,
            "bytes": wav_path.stat().st_size,
        }
    try:
        import pyttsx3
    except Exception as exc:  # pragma: no cover - depends on local Windows voices.
        raise RuntimeError("pyttsx3_unavailable") from exc
    try:
        engine = pyttsx3.init()
        if voice["voice_id"] == "xiaoyi_not_available_in_local_sapi":
            raise RuntimeError("xiaoyi_voice_not_available_in_local_sapi")
        engine.setProperty("voice", voice["voice_id"])
        engine.save_to_file(text, str(wav_path))
        engine.runAndWait()
    except Exception as exc:  # pragma: no cover - depends on local SAPI state.
        raise RuntimeError("local_tts_failed") from exc
    if not wav_path.exists() or wav_path.stat().st_size <= 0:
        raise RuntimeError("local_tts_no_output")
    return {
        "path": str(wav_path),
        "voice_id": voice["voice_id"],
        "voice_name": voice["voice_name"],
        "local_only": True,
        "bytes": wav_path.stat().st_size,
    }


def _pyttsx3_voices() -> list[dict[str, str]]:
    try:
        import pyttsx3
    except Exception:
        return []
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices") or []
        return [{"id": str(getattr(voice, "id", "")), "name": str(getattr(voice, "name", ""))} for voice in voices]
    except Exception:
        return []


def _wav_duration_ms(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as reader:
            frames = reader.getnframes()
            rate = reader.getframerate()
            if rate <= 0:
                return None
            return round(frames / rate * 1000.0, 3)
    except Exception:
        return None


def _inject_audio_state(pool: StatePool, *, tick: int, source_hash: str, duration_ms: float | None) -> None:
    pool.observe_external(
        {
            "sa_id": f"audio_audit::{source_hash[:16]}",
            "family": "audio_audit",
            "label": "audio_audit_only",
            "channel_signature": ("audio", "audit"),
            "origin": "audio_audit_sensor",
            "real_energy": 0.34,
            "metadata": {"ledger_source": "external", "duration_ms": duration_ms},
        },
        tick=tick,
    )


def _inject_tts_state(pool: StatePool, *, tick: int, voice_name: str) -> None:
    pool.observe_external(
        {
            "sa_id": f"tts_voice::{_hash_text(voice_name)}",
            "family": "tts_actuator",
            "label": "xiaoyi",
            "channel_signature": ("audio", "actuator"),
            "origin": "reply_tts_audio",
            "real_energy": 0.26,
            "metadata": {"ledger_source": "user_directed", "voice_name": voice_name},
        },
        tick=tick,
    )
    # P5: feeling::present — AP "hears itself speaking" (AU-2 fix: TTS self-loop)
    pool.observe_external(
        {
            "sa_id": "feeling::present",
            "family": "feeling",
            "label": "present",
            "channel_signature": ("feeling", "audio"),
            "origin": "tts_self_loop",
            "real_energy": 0.15,
            "metadata": {"ledger_source": "residual_mass", "source_voice": voice_name},
        },
        tick=tick,
    )
    # Re-inject TTS output as audio receptor input (AU-2 fix: self-listening loop).
    # This creates an audio_unit SA so AP's state pool reflects "I heard myself say this".
    pool.observe_external(
        {
            "sa_id": f"audio_unit::tts_self::{_hash_text(voice_name)}",
            "family": "audio_unit",
            "label": "tts_self_output",
            "channel_signature": ("audio", "receptor", "mid_band"),
            "origin": "tts_self_loop",
            "real_energy": 0.18,
            "metadata": {
                "ledger_source": "residual_mass",
                "band": "mid_band",
                "source": "tts_self",
                "voice_name": voice_name,
            },
        },
        tick=tick,
    )


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
