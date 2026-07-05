from __future__ import annotations

from pathlib import Path


HTML = Path("apv3test/web/static/phase20_6_workbench.html")
CSS = Path("apv3test/web/static/phase20_6_workbench.css")
JS = Path("apv3test/web/static/phase20_6_workbench.js")
WEB_CHAT = Path("apv3test/web_chat.py")


def test_phase20_6_shareable_workbench_files_exist_and_are_isolated() -> None:
    html = HTML.read_text(encoding="utf-8")

    assert HTML.exists()
    assert CSS.exists()
    assert JS.exists()
    assert "/phase20_6_workbench.css?v=" in html
    assert "/phase20_6_workbench.js?v=" in html
    assert "app.js" not in html
    assert "styles.css" not in html


def test_phase20_6_workbench_reads_true_runtime_fields() -> None:
    script = JS.read_text(encoding="utf-8")

    required = (
        "/api/phase20/turn",
        "/api/phase20/teach",
        "/api/phase20/media/upload",
        "workbench_tick_trace",
        "recall_candidates",
        "action_competition",
        "draft_grid_snapshot",
        "thought_cloud_items",
        "state_pool_top12",
        "inner_picture_state",
        "phase20_6_memory",
        "teacher_focus_boxes",
        "tts_enabled",
        "speechSynthesis",
        "/api/phase20/memory/list",
        "/api/phase20/memory/export",
        "/api/phase20/memory/import",
        "/api/phase20/memory/uninstall",
        "/api/phase20/memory/delete",
        "/api/phase20/history/list",
        "/api/phase20/history/replay",
        "\u5df2\u4fdd\u5b58\u7684\u771f\u5b9e tick",
        "loadHistoryTurn",
        "selectedMemoryKinds",
        "previewSelectedPackage",
        "latestTeachTarget",
        "target_tick",
        "target_context_signature",
        "teachErrorLabel",
        "inner-canvas",
        "drawInnerSketch",
        "chart-tooltip",
        "preferredTtsVoice",
    )
    for token in required:
        assert token in script


def test_phase20_6_workbench_does_not_reintroduce_projection_script() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (HTML, JS, WEB_CHAT)
    )
    forbidden = (
        "\u8f93\u5165\u8fdb\u5165",
        "\u89c6\u89c9\u805a\u7126",
        "\u6587\u672c\u8fd0\u884c\u65f6",
        "\u5171\u73b0\u53ec\u56de",
        "\u98ce\u683c\u7ec4\u88c5",
        "\u63d0\u4ea4\u56de\u590d",
        "workbench_projection_over_phase20_runtime_events",
        "_build_phase20_5a2_workbench_ticks",
        "Phase20MultimodalSession.turn =",
        "image_label_map",
        "direct_label_reply",
        "fast_direct_reply",
        "answer_text",
        "history_projection",
        "replay_fake",
        "canvas_label",
        "pytesseract",
        "easyocr",
        "paddleocr",
        "OpenAI TTS",
        "Google TTS",
        "Edge TTS",
    )
    for token in forbidden:
        assert token not in combined


def test_phase20_6_workbench_keeps_chat_and_teaching_separate() -> None:
    script = JS.read_text(encoding="utf-8")

    assert "\u7ea0\u6b63\u56de\u7b54" in script
    assert "\u5df2\u5b66\u4e60" in script
    assert "app.turns.push({ type: \"teaching\"" in script
    assert "app.turns.push({ type: \"turn\"" in script
    assert "\u8f93\u5165\u5df2\u9690\u85cf" not in script
    assert "\u539f\u6587\u672a\u4fdd\u5b58" not in script
    assert "\u6559\u5b66\u5931\u8d25" in script
    assert "target_context_changed" in script


def test_phase20_6_workbench_exposes_sensor_actuator_controls_without_semantic_routes() -> None:
    html = HTML.read_text(encoding="utf-8")
    script = JS.read_text(encoding="utf-8")
    combined = html + "\n" + script

    required_controls = (
        "ttsEnabledInput",
        "focusXInput",
        "addFocusBoxBtn",
        "sketchCanvas",
        "useCanvasBtn",
        "recordBtn",
        "memorySearchInput",
        "exportMemoryBtn",
        "importPackageBtn",
        "uninstallPackageBtn",
        "deleteMemoriesBtn",
        "refreshHistoryBtn",
        "historyList",
        "previewPackageBtn",
        "selectVisibleMemoryBtn",
        "invertVisibleMemoryBtn",
        "clearSelectedMemoryBtn",
        "excludeSelectedInput",
    )
    for token in required_controls:
        assert token in combined

    assert "\u53ea\u63d0\u9ad8 saliency\uff0c\u4e0d\u7ed1\u5b9a\u6807\u7b7e" in html
    assert "\u4e0d\u505a OCR" in html
    assert "audio_audit_only" in html
    assert "image_label_map" not in combined
    assert "audio_recognition_label" not in combined


def test_phase20_6_workbench_renders_receptor_sketch_not_ellipse_only() -> None:
    script = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")

    assert "const samples = inner.samples || []" in script
    assert "drawInnerSketch(samples, focus)" in script
    assert "innerSketchCanvas" in script
    assert ".inner-canvas" in css
    assert "createRadialGradient" in script
    assert "sample.edge" in script
    assert "sample.clarity" in script


def test_phase20_6_workbench_chart_and_tts_are_explicit() -> None:
    script = JS.read_text(encoding="utf-8")

    assert script.count("function multiChart(") == 1
    assert script.count("function preferredTtsVoice(") == 1
    assert "chart-tooltip" in script
    assert "tick ${currentTick + 1}" in script
    assert "function clamp(" in script
    assert "xiaoyi|xiao yi" in script
    assert "\u6653\u4f0a" in script or "\u5c0f\u827a" in script or "\u5c0f\u4f9d" in script
    assert "\u672a\u627e\u5230 xiaoyi" in script
