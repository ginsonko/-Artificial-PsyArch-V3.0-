from __future__ import annotations

from pathlib import Path
import math
import sqlite3
import struct
import wave

from apv3test.runtime.phase20_7 import MediaInput, TeacherFeedback, run_phase20_7_turn


def _make_wav(path: Path) -> Path:
    rate = 8000
    samples = []
    for index in range(rate // 10):
        value = int(12000 * math.sin(2 * math.pi * 440 * index / rate))
        samples.append(struct.pack("<h", value))
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(b"".join(samples))
    return path


def test_stage6_audio_input_is_audit_sensor_not_recognition(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    wav_path = _make_wav(tmp_path / "voice.wav")

    result = run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="audio", path=str(wav_path)),),
        session_id="stage6-audio",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    audio_events = [event for event in result.tick_trace if event.audio_inner_sketch]

    assert result.stage_id == "20.7-stage6"
    assert audio_events
    assert audio_events[0].selected_action["action_type"] == "audio_audit_sensor"
    assert audio_events[0].audio_inner_sketch["source"] == "audio_audit_only"
    assert audio_events[0].audio_inner_sketch["semantic_label"] is None
    assert any(item["family"] == "audio_audit" for item in audio_events[0].state_pool_top)
    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM phase20_7_experience_events WHERE event_kind='audio_audit_sample'"
        ).fetchone()[0]
    assert count == 1


def test_stage6_reply_commit_creates_local_xiaoyi_tts_actuator_intent(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    run_phase20_7_turn(
        user_text="你好啊",
        teacher_feedback=TeacherFeedback(feedback_text="你也好", reward_mag=1.0),
        session_id="stage6-seed",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    result = run_phase20_7_turn(
        user_text="你好啊",
        session_id="stage6-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    tts_events = [event for event in result.tick_trace if event.selected_action.get("action_type") == "reply_tts_audio"]

    assert result.reply_text == "你也好"
    assert tts_events
    assert tts_events[0].selected_action["voice_preference"] == "xiaoyi"
    assert tts_events[0].selected_action["local_only"] is True
    assert any(item["family"] == "tts_actuator" for item in tts_events[0].state_pool_top)
    with sqlite3.connect(db_path) as conn:
        payload = conn.execute(
            "SELECT payload_json FROM phase20_7_experience_events WHERE event_kind='reply_tts_audio'"
        ).fetchone()[0]
    assert "xiaoyi" in payload.lower()
    assert "local_only" in payload


def test_stage6_idle_audio_focus_rehearses_recent_audio_without_semantic_label(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_7.sqlite"
    wav_path = _make_wav(tmp_path / "voice.wav")

    run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="audio", path=str(wav_path)),),
        session_id="stage6-idle-audio",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    idle = run_phase20_7_turn(
        user_text="",
        session_id="stage6-idle-audio",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    event = idle.tick_trace[0]

    assert event.selected_action["action_type"] == "idle_audio_focus"
    assert event.audio_inner_sketch
    assert event.audio_inner_sketch["source"] == "recent_audio_audit_trace"
    assert event.audio_inner_sketch["semantic_label"] is None
    assert event.audio_inner_sketch["raw_audio_played"] is False
    assert event.c_forward and event.c_backward
    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM phase20_7_experience_events WHERE event_kind='audio_inner_rehearsal'"
        ).fetchone()[0]
    assert count == 1
