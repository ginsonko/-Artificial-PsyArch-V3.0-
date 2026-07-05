from __future__ import annotations

from pathlib import Path

import apv3test.web_chat as web_chat


def _app_with_tmp_db(tmp_path: Path, monkeypatch) -> web_chat.APV3WebChatApp:
    monkeypatch.setattr(web_chat, "PHASE20_7_DB_PATH", tmp_path / "phase20_9i_workbench.sqlite")
    return web_chat.APV3WebChatApp()


def _turn(app: web_chat.APV3WebChatApp, payload: dict[str, object]) -> list[dict[str, object]]:
    base = {
        "session_id": "phase20-9i-lifecycle",
        "runtime_stage": "stage6",
        "post_commit_idle_ticks": 0,
        "max_ticks": 32,
    }
    result = app.phase20_7_turn({**base, **payload})
    return list(result["turn"]["tick_trace"])


def _learning_reviews(ticks: list[dict[str, object]]) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for tick in ticks:
        feelings = tick.get("feelings", {})
        if isinstance(feelings, dict) and isinstance(feelings.get("idle_learning_review"), dict):
            review = dict(feelings["idle_learning_review"])
            if review:
                found.append(review)
    return found


def _self_tests(ticks: list[dict[str, object]]) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for tick in ticks:
        feelings = tick.get("feelings", {})
        if isinstance(feelings, dict) and isinstance(feelings.get("idle_self_test"), dict):
            test = dict(feelings["idle_self_test"])
            if test:
                found.append(test)
    return found


def test_phase20_9i_workbench_static_reads_learning_lifecycle_from_runtime_ticks() -> None:
    static_root = Path("apv3test/web/static")
    html = (static_root / "phase20_7_workbench.html").read_text(encoding="utf-8")
    js = (static_root / "phase20_7_workbench.js").read_text(encoding="utf-8")
    css = (static_root / "phase20_7_workbench.css").read_text(encoding="utf-8")

    assert "learningLifecyclePanel" in html
    assert "学习生命周期验收" in html
    assert "renderLearningLifecycle" in js
    assert "learningLifecycleState" in js
    assert "alignmentWrittenDelta" in js
    assert "idleLearningReview" in js
    assert "idleSelfTest" in js
    assert "selfTestFeedback" in js
    assert "self_test_grasp" in js
    assert "自测把握" in js
    assert "反馈稳定" in js
    assert ".learning-lifecycle" in css
    assert ".lifecycle-step" in css
    assert "answer" + "_table" not in js
    assert "hidden" + "_solver" not in js
    assert "keyword" + "_route" not in js
    assert "direct" + "_reply" not in js


def test_phase20_9i_turn_api_exposes_full_learning_lifecycle_for_workbench(tmp_path: Path, monkeypatch) -> None:
    app = _app_with_tmp_db(tmp_path, monkeypatch)
    all_ticks: list[dict[str, object]] = []

    all_ticks.extend(
        _turn(
            app,
            {
                "text": "phase20.9i lifecycle cue",
                "teacher_feedback": "phase20.9i lifecycle reply",
            },
        )
    )
    all_ticks.extend(_turn(app, {"text": "phase20.9i lifecycle cue"}))
    all_ticks.extend(_turn(app, {}))
    all_ticks.extend(_turn(app, {}))
    all_ticks.extend(_turn(app, {}))

    feedback_ticks = [
        tick
        for tick in all_ticks
        if any(
            isinstance(delta, dict) and delta.get("delta_kind") == "experience_alignment_written"
            for delta in tick.get("learning_deltas", [])
        )
    ]
    reviews = _learning_reviews(all_ticks)
    self_tests = _self_tests(all_ticks)
    stable_reviews = [
        review for review in reviews if isinstance(review.get("self_test_feedback"), dict) and review["self_test_feedback"]
    ]

    assert feedback_ticks
    assert reviews
    assert self_tests
    assert stable_reviews
    assert reviews[-1]["source_text"] == "phase20.9i lifecycle cue"
    assert reviews[-1]["target_text"] == "phase20.9i lifecycle reply"
    assert self_tests[-1]["expected_text"] == "phase20.9i lifecycle reply"
    assert self_tests[-1]["recalled_text"] == "phase20.9i lifecycle reply"
    assert self_tests[-1]["self_test_grasp"] > 0.68

    feedback = stable_reviews[-1]["self_test_feedback"]
    assert feedback["feedback_kind"] == "self_test_success"
    assert feedback["writes_answer_directly"] is False
    assert feedback["creates_reply_candidate"] is False
