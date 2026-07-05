from __future__ import annotations

from pathlib import Path
import sqlite3

from apv3test.runtime.phase20_open_dialogue import Phase20MultimodalSession


APPLE = Path("config/curriculum/assets/visual/clean_cards/noun_apple_held_out_0.png")
APPLE_TRAIN = Path("config/curriculum/assets/visual/clean_cards/noun_apple_train_0.png")
BANANA_TRAIN = Path("config/curriculum/assets/visual/clean_cards/noun_banana_train_0.png")


def _teach_short_reply(session: Phase20MultimodalSession, *, prompt: str = "hello", reply: str = "OK.") -> None:
    session.turn({"text": prompt, "max_ticks": 8})
    session.teach_latest({"teaching_reply_text": reply})


def test_phase20_6_runtime_boundary_commits_from_draftgrid(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6.sqlite")
    _teach_short_reply(session)

    result = session.turn({"text": "hello", "max_ticks": 8, "idle_ticks": 1})
    events = tuple(result.metadata["runtime_tick_events"])
    commit_events = [
        event for event in events
        if event.get("draft_changes", {}).get("draft_action_kind") == "commit"
    ]

    assert result.metadata["schema_id"] == "apv3_phase20_6_turn/v1"
    assert result.metadata["runtime_tick_event_source"] == "phase20_6_true_runtime_boundary"
    assert result.metadata["runtime_tick_projection"] is False
    assert events
    assert all(event["is_projection"] is False for event in events)
    assert all(event["source"] in {"phase20_6_true_runtime_boundary", "phase20_6_system_boundary"} for event in events)
    assert commit_events
    assert result.reply_text == "OK."
    assert result.reply_text == commit_events[-1]["draft_changes"]["committed_text"]
    assert any(
        event["draft_changes"].get("draft_action_kind") == "type_text"
        and event["action_chosen"]["outcome_kind"] == "write_cell"
        for event in events
    )


def test_phase20_6_teacher_phrase_can_be_added_after_readonly_style_seed(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6.sqlite")

    state = dict(session.chat.state)
    state["expression_phrase_memory"] = {**dict(state["expression_phrase_memory"]), "allow_new_phrases": False}
    session.chat.state = state
    session.chat.store.save_state(state)
    first = session.turn({"text": "你好啊", "max_ticks": 8, "idle_ticks": 0})
    assert session.chat.state["expression_phrase_memory"]["allow_new_phrases"] is False
    session.teach_latest(
        {
            "teaching_reply_text": "你也好",
            "target_tick": first.tick,
            "target_context_signature": first.metadata["context_signature"],
        }
    )
    second = session.turn({"text": "你好啊", "max_ticks": 8, "idle_ticks": 0})

    assert second.reply_text == "你也好"
    assert second.metadata["teaching_candidate_applied"] is True
    assert any(
        row.get("phrase_id", "").startswith("teacher_phrase::") and row.get("tokens") == ["你也好"]
        for row in session.chat.state["expression_phrase_memory"]["records"]
    )


def test_phase20_6_write_ticks_are_rebuilt_from_current_draft_prefix(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6.sqlite")
    _teach_short_reply(session)

    result = session.turn({"text": "hello", "max_ticks": 8, "idle_ticks": 0})
    write_events = [
        event for event in tuple(result.metadata["runtime_tick_events"])
        if event.get("draft_changes", {}).get("draft_action_kind") == "type_text"
    ]

    assert [event["action_chosen"]["payload"]["prefix_length"] for event in write_events] == [0, 1, 2]
    for event in write_events:
        draft = event["draft_changes"]
        chosen_payload = event["action_chosen"]["payload"]
        assert draft["next_token_candidate_count"] >= 1
        assert chosen_payload["next_token"]
        assert "visible_text_before_hash" in chosen_payload
        assert "candidate_text" not in chosen_payload
        assert "reply_text" not in chosen_payload


def test_phase20_6_tick_event_exposes_native_candidates_competition_and_cloud(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6.sqlite")
    _teach_short_reply(session, reply="Hi.")

    result = session.turn({"text": "hello", "max_ticks": 8, "idle_ticks": 0})
    event = next(
        item for item in tuple(result.metadata["runtime_tick_events"])
        if item.get("draft_changes", {}).get("draft_action_kind") == "type_text"
    )

    assert event["recall_candidates"]
    assert event["recall_candidates"][0]["schema_id"] == "apv3_phase20_6_recall_candidate/v1"
    assert event["recall_candidates"][0]["source_phrase_hash"]
    assert "candidate_text" not in event["recall_candidates"][0]
    assert event["action_competition"]["schema_id"] == "apv3_phase20_6_action_competition/v1"
    assert event["action_competition"]["selected_action_id"] == event["action_chosen"]["action_id"]
    assert event["draft_grid_snapshot"]["visible_text"] == event["draft_changes"]["draft_buffer"]
    assert event["draft_grid_snapshot"]["visible_text_hash"]
    assert event["thought_cloud_items"]
    assert event["thought_cloud_items"][0]["schema_id"] == "apv3_phase20_6_thought_cloud_item/v1"


def test_phase20_6_visual_path_is_class_agnostic_candidate_only(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6.sqlite")

    result = session.turn({"text": "what is this", "image_path": str(APPLE), "max_ticks": 8})
    events = tuple(result.metadata["runtime_tick_events"])

    assert result.object_files
    assert events[0]["action_chosen"]["outcome_kind"] == "move_focus"
    assert {item.top_visible_label for item in result.object_files} == {"visual_candidate"}
    assert {item.decision_tier for item in result.object_files} == {"candidate_only"}
    assert all(item.focus_xy is not None for item in result.object_files)
    assert "apple" not in repr(result.metadata["runtime_tick_events"]).lower()
    assert "\u82f9\u679c" not in repr(result.metadata["runtime_tick_events"])


def test_phase20_6_visual_teaching_uses_strong_visual_sa_without_cross_talk(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6_visual.sqlite")

    apple_first = session.turn({"text": "what is this?", "image_path": str(APPLE_TRAIN), "max_ticks": 16, "idle_ticks": 2})
    session.teach_latest({
        "teaching_reply_text": "apple",
        "target_tick": apple_first.tick,
        "target_context_signature": apple_first.metadata["context_signature"],
    })
    banana_before = session.turn({"text": "what is this?", "image_path": str(BANANA_TRAIN), "max_ticks": 16, "idle_ticks": 2})
    session.teach_latest({
        "teaching_reply_text": "banana",
        "target_tick": banana_before.tick,
        "target_context_signature": banana_before.metadata["context_signature"],
    })
    apple_after = session.turn({"text": "what is this?", "image_path": str(APPLE_TRAIN), "max_ticks": 16, "idle_ticks": 2})
    banana_after = session.turn({"text": "what is this?", "image_path": str(BANANA_TRAIN), "max_ticks": 16, "idle_ticks": 2})

    apple_visual_ids = set(apple_first.metadata["visual_sa_ids"])
    banana_visual_ids = set(banana_before.metadata["visual_sa_ids"])
    assert any(item.startswith("visual_signature::foveated_sketch::") for item in apple_visual_ids)
    assert any(item.startswith("visual_signature::receptor_profile::") for item in apple_visual_ids)
    assert any(item.startswith("visual_signature::foveated_sketch::") for item in banana_visual_ids)
    assert apple_visual_ids != banana_visual_ids
    assert banana_before.metadata["teaching_candidate_applied"] is False
    assert banana_before.reply_text != "apple"
    assert apple_after.metadata["teaching_candidate_applied"] is True
    assert banana_after.metadata["teaching_candidate_applied"] is True
    assert apple_after.reply_text == "apple"
    assert banana_after.reply_text == "banana"
    assert apple_after.metadata["teaching_id"] != banana_after.metadata["teaching_id"]


def test_phase20_6_image_turn_observes_before_writing_and_reconstructs_visual_state(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6_visual.sqlite")

    result = session.turn({"text": "what is this?", "image_path": str(APPLE_TRAIN), "max_ticks": 16, "idle_ticks": 2})
    events = tuple(result.metadata["runtime_tick_events"])
    first_actions = [event["action_chosen"]["outcome_kind"] for event in events[:3]]
    inner = events[0].get("inner_picture_state") or {}
    samples = inner.get("samples") or []
    focus = inner.get("focus_xy") or [50, 50]

    assert first_actions == ["move_focus", "move_focus", "move_focus"]
    assert all(event["draft_grid_snapshot"]["visible_text"] == "" for event in events[:3])
    assert inner["source"] == "state_pool_visual_receptor_sketch_samples"
    assert inner["enabled"] is True
    assert samples
    assert any(item["source"] == "visual_receptor_sketch_native_pixel" for item in samples)
    assert any(item["kind"] == "foveal_native" for item in samples)
    assert all("image_path" not in repr(item).lower() for item in samples)
    near = [
        item for item in samples
        if ((float(item["x"]) - float(focus[0])) ** 2 + (float(item["y"]) - float(focus[1])) ** 2) ** 0.5 <= 18
    ]
    far = [
        item for item in samples
        if ((float(item["x"]) - float(focus[0])) ** 2 + (float(item["y"]) - float(focus[1])) ** 2) ** 0.5 >= 35
    ]
    assert near and far
    assert sum(float(item["clarity"]) for item in near) / len(near) > sum(float(item["clarity"]) for item in far) / len(far)
    assert sum(float(item["opacity"]) for item in near) / len(near) > sum(float(item["opacity"]) for item in far) / len(far)


def test_phase20_6_inner_picture_reveals_new_foveal_samples_across_focus_ticks(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6_visual.sqlite")

    result = session.turn({"text": "what is this?", "image_path": str(APPLE_TRAIN), "max_ticks": 16, "idle_ticks": 0})
    events = tuple(result.metadata["runtime_tick_events"])
    focus_points = [tuple(event["focus_xy"]) for event in events[:3]]
    sample_counts = [int((event.get("inner_picture_state") or {}).get("sample_count", 0)) for event in events[:3]]
    focus_indexes = [
        {
            item.get("focus_index")
            for item in ((event.get("inner_picture_state") or {}).get("samples") or [])
            if item.get("kind") == "foveal_native"
        }
        for event in events[:3]
    ]

    assert len(set(focus_points)) >= 3
    assert sample_counts[1] >= sample_counts[0]
    assert sample_counts[2] >= sample_counts[1]
    assert 0 in focus_indexes[0]
    assert 1 in focus_indexes[1]
    assert 2 in focus_indexes[2]


def test_phase20_6_teaching_target_mismatch_is_rejected(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6_visual.sqlite")

    first = session.turn({"text": "what is this?", "image_path": str(APPLE_TRAIN), "max_ticks": 16, "idle_ticks": 2})
    session.turn({"text": "hello", "max_ticks": 8, "idle_ticks": 0})

    try:
        session.teach_latest({
            "teaching_reply_text": "apple",
            "target_tick": first.tick,
            "target_context_signature": first.metadata["context_signature"],
        })
    except ValueError as exc:
        assert "phase20_teaching_target_context_changed" in str(exc) or "phase20_teaching_target_tick_changed" in str(exc)
    else:
        raise AssertionError("teaching should reject stale UI target context")


def test_phase20_6_teaching_recall_is_draftgrid_write_not_direct_override(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6.sqlite")

    _teach_short_reply(session, prompt="who", reply="AP.")
    result = session.turn({"text": "who", "max_ticks": 8})
    events = tuple(result.metadata["runtime_tick_events"])
    write_events = [
        event for event in events
        if event.get("draft_changes", {}).get("draft_action_kind") == "type_text"
    ]

    assert result.metadata["teaching_candidate_applied"] is True
    assert result.reply_text == "AP."
    assert write_events
    assert all(
        event["draft_changes"]["source_kind"] == "slow_cooccurrence_teacher_phrase"
        for event in write_events
    )
    assert result.reply_text == next(
        event["draft_changes"]["committed_text"]
        for event in events
        if event.get("draft_changes", {}).get("draft_action_kind") == "commit"
    )


def test_phase20_6_fast_slow_memory_persists_without_answer_table(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_6.sqlite"
    session = Phase20MultimodalSession(state_db_path=db_path)
    _teach_short_reply(session, prompt="ping", reply="P.")

    first = session.turn({"text": "ping", "max_ticks": 8})
    second = session.turn({"text": "ping", "max_ticks": 8})
    fast_store = session.chat.state["phase20_6_fast_action_chains"]
    slow_store = session.chat.state["phase20_6_slow_memory"]

    assert fast_store["schema_id"] == "apv3_phase20_6_fast_action_chain_store/v1"
    assert slow_store["schema_id"] == "apv3_phase20_6_slow_memory_store/v1"
    tick_store = session.chat.state["phase20_6_tick_memories"]
    assert tick_store["schema_id"] == "apv3_phase20_6_tick_memory_store/v1"
    assert fast_store["chains"]
    assert slow_store["memories"]
    assert tick_store["memories"]
    assert any(row["memory_tier"] == "fast" for row in tick_store["memories"])
    assert any(row["memory_tier"] == "slow" for row in tick_store["memories"])
    assert first.reply_text == "P."
    assert second.metadata["phase20_6_fast_hint_count"] >= 1
    assert second.metadata["phase20_6_slow_hint_count"] >= 1
    assert "reply_text" not in repr(fast_store)
    assert "reply_text" not in repr(slow_store)
    assert all(row["stores_surface_phrase"] is False for row in fast_store["chains"])
    assert all(row["stores_surface_phrase"] is False for row in slow_store["memories"])
    with sqlite3.connect(db_path) as conn:
        fast_count = conn.execute("SELECT COUNT(*) FROM phase20_6_fast_action_chains").fetchone()[0]
        slow_count = conn.execute("SELECT COUNT(*) FROM phase20_6_slow_memory").fetchone()[0]
    assert fast_count >= 1
    assert slow_count >= 1


def test_phase20_6_active_stop_is_separate_from_commit(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6.sqlite")
    _teach_short_reply(session, prompt="stop", reply="S.")

    result = session.turn({"text": "stop", "max_ticks": 8, "idle_ticks": 0})
    events = tuple(result.metadata["runtime_tick_events"])
    kinds = [event["action_chosen"]["outcome_kind"] for event in events]

    assert "commit_reply" in kinds
    assert "stop_generating" in kinds
    stop_event = next(event for event in events if event["action_chosen"]["outcome_kind"] == "stop_generating")
    assert stop_event["draft_changes"]["committed_text"] == "S."
    assert stop_event["action_chosen"]["payload"]["commit_already_done"] is True


def test_phase20_6_unresolved_carry_reenters_next_turn_state_pool(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6.sqlite")
    _teach_short_reply(session, prompt="long", reply="abcdefghi")

    first = session.turn({"text": "long", "max_ticks": 4, "idle_ticks": 0})
    assert first.metadata["phase20_6_unresolved_carry_out"]
    second = session.turn({"text": "next", "max_ticks": 8, "idle_ticks": 0})
    events = tuple(second.metadata["runtime_tick_events"])

    assert second.metadata["phase20_6_unresolved_carry_in_count"] >= 1
    assert any(
        item.get("family") == "unresolved_carry"
        for event in events
        for item in event.get("state_pool_top12", [])
    )


def test_phase20_6_affect_evidence_is_state_pool_modulator_not_reply_route(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6.sqlite")

    result = session.turn({"text": "I feel sad today", "max_ticks": 8, "idle_ticks": 0})
    events = tuple(result.metadata["runtime_tick_events"])
    affect = result.metadata["phase20_6_affect_evidence"]

    assert affect["bucket"] == "warm"
    assert affect["direct_reply_authority"] is False
    assert result.styled_response.affect_bucket == "warm"
    assert any(
        item.get("family") == "affect_evidence"
        for event in events
        for item in event.get("state_pool_top12", [])
    )
    assert "if sad" not in repr(events).lower()


def test_phase20_6_teacher_focus_and_tts_are_ap_native_event_fields(tmp_path: Path) -> None:
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6.sqlite")

    result = session.turn(
        {
            "text": "look",
            "image_path": str(APPLE),
            "media_path": str(APPLE),
            "media_type": "image/png",
            "media_source": "canvas",
            "teacher_focus_boxes": [{"x": 20, "y": 30, "w": 40, "h": 20}],
            "tts_enabled": True,
            "max_ticks": 8,
            "idle_ticks": 0,
        }
    )
    events = tuple(result.metadata["runtime_tick_events"])
    first = events[0]

    assert first["focus_xy"] == [40, 40]
    assert first["draft_changes"]["sensor_actuator_context"]["teacher_focus_semantic_authority"] is False
    assert first["draft_changes"]["sensor_actuator_context"]["canvas_image_hash"]
    assert any(
        item.get("family") == "teacher_guided_focus"
        and "no_label" in item.get("channel_signature", [])
        for item in first["state_pool_top12"]
    )
    assert any(
        event["action_chosen"]["outcome_kind"] == "reply_tts_audio"
        and event["reply_tts_request"]["local_only"] is True
        and event["reply_tts_request"]["not_inner_voice"] is True
        for event in events
    )
    assert "semantic_label_authority" in repr(events)
    assert "direct_label_reply" not in repr(events)


def test_phase20_6_audio_recording_enters_audit_sensor_not_recognition(tmp_path: Path) -> None:
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6.sqlite")

    result = session.turn(
        {
            "text": "listen",
            "media_path": str(audio_path),
            "media_type": "audio/wav",
            "max_ticks": 6,
        }
    )
    events = tuple(result.metadata["runtime_tick_events"])

    assert result.metadata["phase20_6_sensor_actuator_context"]["audio_mode"] == "audio_audit_only"
    assert events[0]["inner_audio_state"]["enabled"] is True
    assert events[0]["inner_audio_state"]["source"] == "audio_sensor_audit_only_not_recognition"
    assert any(item.get("family") == "audio_audit_sensor" for item in events[0]["state_pool_top12"])
    assert "audio_recognition_label" not in repr(events)


def test_phase20_6_stage0_redline_scan_runtime_paths() -> None:
    runtime = Path("apv3test/runtime/phase20_open_dialogue.py").read_text(encoding="utf-8")
    runtime_6 = Path("apv3test/runtime/phase20_6_runtime.py").read_text(encoding="utf-8")
    web_chat = Path("apv3test/web_chat.py").read_text(encoding="utf-8")
    app_js = Path("apv3test/web/static/app.js").read_text(encoding="utf-8")
    combined = "\n".join((runtime, runtime_6, web_chat, app_js))

    forbidden = (
        "enumerate_objects_in_image",
        "reply_text = taught.response_text",
        "_phase20_5a2",
        "_build_phase20_5a2_workbench_ticks",
        "Phase20MultimodalSession.turn =",
        "\u547d\u4e2d\u6559\u5b66",
        "\u6559\u5b66\u547d\u4e2d",
        "\u672a\u547d\u4e2d\u6559\u5e08",
        "teaching_hit",
        "taught_answer",
        "direct_label_reply",
        "image_label_map",
        "_select_visible_token_source",
        "writable_count",
        "candidate_text",
        "fast_direct_reply",
        "answer_text",
        "workbench_projection_over_phase20_runtime_events",
    )
    for token in forbidden:
        assert token not in combined
