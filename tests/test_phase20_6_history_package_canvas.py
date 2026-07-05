from __future__ import annotations

from pathlib import Path
import shutil

from apv3test.runtime.phase20_memory_packages import (
    export_memory_package,
    import_memory_package,
    list_memory_view,
    uninstall_memory_package,
)
from apv3test.runtime.phase20_open_dialogue import Phase20MultimodalSession
from apv3test.web_chat import APV3WebChatApp


APPLE = Path("config/curriculum/assets/visual/clean_cards/noun_apple_held_out_0.png")


def test_phase20_6_history_replay_reads_stored_runtime_events_without_rerun(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "phase20_6_history.sqlite")
    live = app.phase20_turn({"text": "你好", "max_ticks": 6, "idle_ticks": 0})
    before_tick = app.phase20_session.chat.tick
    before_trace_count = len(app.phase20_session.chat.state.get("phase20_turn_trace", []))

    history = app.phase20_history_list({"limit": 10})
    turn_id = history["turns"][0]["turn_id"]
    replay = app.phase20_history_replay({"turn_id": turn_id})

    assert live["turn"]["workbench_tick_trace"]
    assert history["replay_policy"] == "read_stored_phase20_turn_trace_without_rerun"
    assert history["turns"][0]["user_text"] == "你好"
    assert replay["mutated_state"] is False
    assert replay["replay_source"] == "stored_runtime_tick_events"
    assert replay["turn"]["live_user_text"] == "你好"
    assert replay["turn"]["workbench_tick_trace"][0]["replay_source"] == "stored_runtime_tick_events"
    assert all(item["is_projection"] is False for item in replay["turn"]["workbench_tick_trace"])
    assert app.phase20_session.chat.tick == before_tick
    assert len(app.phase20_session.chat.state.get("phase20_turn_trace", [])) == before_trace_count


def test_phase20_6_memory_package_filters_preview_exclude_and_precise_uninstall(tmp_path: Path) -> None:
    source = Phase20MultimodalSession(state_db_path=tmp_path / "source.sqlite")
    source.turn({"text": "这是什么", "image_path": str(APPLE), "max_ticks": 8})
    source.teach_latest({"teaching_reply_text": "像苹果。"})

    phrase_view = list_memory_view(source.chat.state, query="像苹果", kinds=("expression_phrase",), limit=20)
    pair_view = list_memory_view(source.chat.state, query="像苹果", kinds=("cooccurrence_pair",), limit=20)
    assert phrase_view["memories"]
    assert pair_view["memories"]
    excluded = [phrase_view["memories"][0]["memory_id"]]
    package = export_memory_package(
        source.chat.state,
        name="苹果共现局部包",
        query="像苹果",
        exclude_memory_ids=excluded,
        kinds=("expression_phrase", "cooccurrence_pair"),
    )

    assert all(item["memory_id"] not in excluded for item in package["memories"])
    target = Phase20MultimodalSession(state_db_path=tmp_path / "target.sqlite")
    imported = import_memory_package(target.chat.state, package)
    imported_again = import_memory_package(imported.state, package)
    preview = list_memory_view(imported_again.state, package_id=imported.payload["package_id"], limit=50)
    uninstalled = uninstall_memory_package(imported_again.state, imported.payload["package_id"])
    after_uninstall = list_memory_view(uninstalled.state, package_id=imported.payload["package_id"], limit=50)

    assert imported.payload["added_count"] == len(package["memories"])
    assert imported_again.payload["dedup_count"] >= imported.payload["added_count"]
    assert preview["memories"]
    assert uninstalled.payload["removed_count"] == imported.payload["added_count"]
    assert after_uninstall["total_memories"] == 0


def test_phase20_6_canvas_image_teaching_recalls_through_visual_feature_cooccurrence(tmp_path: Path) -> None:
    first_canvas = tmp_path / "canvas_first.png"
    second_canvas = tmp_path / "canvas_second_same_pixels.png"
    shutil.copyfile(APPLE, first_canvas)
    shutil.copyfile(APPLE, second_canvas)
    session = Phase20MultimodalSession(state_db_path=tmp_path / "phase20_6_canvas.sqlite")

    first = session.turn(
        {
            "text": "这是什么",
            "image_path": str(first_canvas),
            "media_path": str(first_canvas),
            "media_type": "image/png",
            "media_source": "canvas",
            "max_ticks": 8,
            "idle_ticks": 0,
        }
    )
    taught = session.teach_latest({"teaching_reply_text": "像苹果。"})
    repeated = session.turn(
        {
            "text": "这是什么",
            "image_path": str(second_canvas),
            "media_path": str(second_canvas),
            "media_type": "image/png",
            "media_source": "canvas",
            "max_ticks": 8,
            "idle_ticks": 0,
        }
    )

    taught_ids = set(taught.teaching_trace.visual_sa_ids)
    repeated_ids = set(str(item) for item in repeated.metadata["visual_sa_ids"])
    shared_feature_ids = {
        item for item in taught_ids.intersection(repeated_ids)
        if item.startswith("visual_feature::") or item.startswith("visual_scene::")
    }
    write_events = [
        event for event in repeated.metadata["runtime_tick_events"]
        if event.get("draft_changes", {}).get("draft_action_kind") == "type_text"
    ]

    assert first.object_files
    assert repeated.object_files
    assert first.object_files[0].candidate_id != repeated.object_files[0].candidate_id
    assert shared_feature_ids
    assert repeated.reply_text == "像苹果。"
    assert repeated.metadata["teaching_candidate_applied"] is True
    assert repeated.metadata["phase20_6_sensor_actuator_context"]["canvas_image_hash"]
    assert all(event["draft_changes"]["source_kind"] == "slow_cooccurrence_teacher_phrase" for event in write_events)
    assert "image_label_map" not in repr(repeated.metadata)
    assert "direct_label_reply" not in repr(repeated.metadata)
