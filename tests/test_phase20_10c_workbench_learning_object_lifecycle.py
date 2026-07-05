from __future__ import annotations

from pathlib import Path

import apv3test.web_chat as web_chat


FORMULA_10A = "apv3_phase20_10a_learning_stage_runtime_progression/v1"
FORMULA_10B = "apv3_phase20_10b_learning_object_lifecycle_projection/v1"


def _app_with_tmp_db(tmp_path: Path, monkeypatch) -> web_chat.APV3WebChatApp:
    monkeypatch.setattr(web_chat, "PHASE20_7_DB_PATH", tmp_path / "phase20_10c_workbench.sqlite")
    return web_chat.APV3WebChatApp()


def _turn(app: web_chat.APV3WebChatApp, payload: dict[str, object]) -> list[dict[str, object]]:
    base = {
        "session_id": "phase20-10c-workbench",
        "runtime_stage": "stage4",
        "post_commit_idle_ticks": 0,
        "max_ticks": 32,
    }
    result = app.phase20_7_turn({**base, **payload})
    return list(result["turn"]["tick_trace"])


def _progressions(tick: dict[str, object]) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for row in tick.get("action_competition", []):
        if not isinstance(row, dict):
            continue
        carryover = row.get("learning_loop_carryover")
        if not isinstance(carryover, dict):
            continue
        progression = carryover.get("learning_stage_runtime_progression")
        if isinstance(progression, dict) and progression.get("active"):
            found.append(progression)
    return found


def _lifecycles(ticks: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for tick in ticks:
        for progression in _progressions(tick):
            lifecycle = progression.get("learning_object_lifecycle")
            if isinstance(lifecycle, dict) and lifecycle.get("active"):
                out.append(lifecycle)
    return out


def test_phase20_10c_workbench_static_reads_10a_10b_trace_without_new_entity() -> None:
    static_root = Path("apv3test/web/static")
    html = (static_root / "phase20_7_workbench.html").read_text(encoding="utf-8")
    js = (static_root / "phase20_7_workbench.js").read_text(encoding="utf-8")
    css = (static_root / "phase20_7_workbench.css").read_text(encoding="utf-8")

    assert "learningLifecyclePanel" in html
    assert "renderLearningLifecycle" in js
    assert "learningStageRuntime" in js
    assert "learningObjectLifecycle" in js
    assert "learningObjectLifecycleSummaryHtml" in js
    assert "learning_stage_runtime_progression" in js
    assert "learning_object_lifecycle" in js
    assert "current_lifecycle_stage" in js
    assert "review_count" in js
    assert "self_test_count" in js
    assert "stability" in js
    assert "regression" in js
    assert "RuntimeTickEvent / ExperienceFlow / SSP trace" in js
    assert ".lifecycle-object-summary" in css
    assert ".lifecycle-stage-rail" in css
    assert ".lifecycle-pressure" in css
    assert "answer" + "_table" not in js
    assert "hidden" + "_solver" not in js
    assert "keyword" + "_route" not in js
    assert "direct" + "_reply" not in js
    assert "learning_lifecycle_table" not in js


def test_phase20_10c_web_api_exposes_learning_object_lifecycle_for_replay(tmp_path: Path, monkeypatch) -> None:
    app = _app_with_tmp_db(tmp_path, monkeypatch)
    all_ticks: list[dict[str, object]] = []

    all_ticks.extend(
        _turn(
            app,
            {
                "text": "phase20.10c lifecycle cue",
                "teacher_feedback": "phase20.10c lifecycle reply",
            },
        )
    )
    all_ticks.extend(_turn(app, {"text": "phase20.10c lifecycle cue"}))
    all_ticks.extend(_turn(app, {}))
    all_ticks.extend(_turn(app, {}))
    all_ticks.extend(_turn(app, {}))
    all_ticks.extend(_turn(app, {}))

    progressions = [progression for tick in all_ticks for progression in _progressions(tick)]
    lifecycles = _lifecycles(all_ticks)

    assert progressions
    assert lifecycles
    assert any(progression["formula_id"] == FORMULA_10A for progression in progressions)
    assert all(lifecycle["formula_id"] == FORMULA_10B for lifecycle in lifecycles)
    assert len({lifecycle["learning_object_id"] for lifecycle in lifecycles}) == 1
    assert max(int(lifecycle["review_count"]) for lifecycle in lifecycles) >= 1
    assert max(int(lifecycle["self_test_count"]) for lifecycle in lifecycles) >= 1
    assert lifecycles[-1]["current_lifecycle_stage"] in {
        "self_tested",
        "adjusted_after_feedback",
        "retested",
        "teacher_exit_ready",
        "cold_retest_ready",
    }
    assert "lifecycle_action_deltas" in lifecycles[-1]
    assert isinstance(lifecycles[-1]["recent_review_ticks"], (list, tuple))
    assert isinstance(lifecycles[-1]["recent_self_test_ticks"], (list, tuple))
    assert all(lifecycle["uses_existing_ap_flow"] is True for lifecycle in lifecycles)
    assert all(lifecycle["projection_only"] is True for lifecycle in lifecycles)
    assert all(lifecycle["writes_answer_directly"] is False for lifecycle in lifecycles)
    assert all(lifecycle["creates_reply_candidate"] is False for lifecycle in lifecycles)
