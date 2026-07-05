from __future__ import annotations

from pathlib import Path

import apv3test.web_chat as web_chat


def _app_with_tmp_db(tmp_path: Path, monkeypatch) -> web_chat.APV3WebChatApp:
    monkeypatch.setattr(web_chat, "PHASE20_7_DB_PATH", tmp_path / "phase20_9d_workbench.sqlite")
    return web_chat.APV3WebChatApp()


def _learning_loop_metrics(tick: dict[str, object]) -> list[dict[str, object]]:
    return [
        dict(delta)
        for delta in tick.get("learning_deltas", [])
        if isinstance(delta, dict) and delta.get("delta_kind") == "learning_loop_metrics"
    ]


def test_phase20_9d_workbench_static_reads_learning_loop_from_runtime_ticks() -> None:
    static_root = Path("apv3test/web/static")
    html = (static_root / "phase20_7_workbench.html").read_text(encoding="utf-8")
    js = (static_root / "phase20_7_workbench.js").read_text(encoding="utf-8")
    css = (static_root / "phase20_7_workbench.css").read_text(encoding="utf-8")

    assert "learningLoopPanel" in html
    assert "学习闭环" in html
    assert "renderLearningLoop" in js
    assert "learningLoopMetric" in js
    assert 'action_type !== "reply_tts_audio"' in js
    assert "learning_loop_metrics" in js
    assert "feedback_only_readiness" in js
    assert "teacher_off_readiness" in js
    assert "cold_retest_readiness" in js
    assert "scaffold_regression_need" in js
    assert "学习:退场" in js
    assert ".learning-loop" in css
    assert ".learning-bar" in css
    assert "answer" + "_table" not in js
    assert "hidden" + "_solver" not in js
    assert "keyword" + "_route" not in js


def test_phase20_9d_turn_api_exposes_learning_loop_metrics_for_workbench(tmp_path: Path, monkeypatch) -> None:
    app = _app_with_tmp_db(tmp_path, monkeypatch)

    result = app.phase20_7_turn(
        {
            "text": "phase20.9d workbench unknown",
            "runtime_stage": "stage6",
            "post_commit_idle_ticks": 0,
        }
    )
    ticks = result["turn"]["tick_trace"]
    request_tick = next(tick for tick in ticks if tick["selected_action"].get("action_type") == "request_teacher")
    metrics = _learning_loop_metrics(request_tick)

    assert len(metrics) == 1
    metric = metrics[0]
    assert metric["dominant_learning_tendency"] == "return_to_scaffold"
    assert metric["scaffold_regression_need"] > metric["teacher_off_readiness"]
    assert metric["creates_reply_candidate"] is False
    assert metric["writes_answer_directly"] is False


def test_phase20_9d_workbench_can_show_teacher_off_after_teaching(tmp_path: Path, monkeypatch) -> None:
    app = _app_with_tmp_db(tmp_path, monkeypatch)
    app.phase20_7_turn(
        {
            "text": "phase20.9d learned cue",
            "teacher_feedback": "phase20.9d learned reply",
            "runtime_stage": "stage6",
            "post_commit_idle_ticks": 0,
        }
    )
    result = app.phase20_7_turn(
        {
            "text": "phase20.9d learned cue",
            "runtime_stage": "stage6",
            "post_commit_idle_ticks": 0,
        }
    )
    b_tick = next(tick for tick in result["turn"]["tick_trace"] if tick["b_candidates"])
    metric = _learning_loop_metrics(b_tick)[0]

    assert b_tick["b_candidates"][0]["kind"] == "exact_b0"
    assert metric["dominant_learning_tendency"] == "teacher_off_probe"
    assert metric["teacher_off_readiness"] > metric["scaffold_regression_need"]
    assert metric["writes_answer_directly"] is False
