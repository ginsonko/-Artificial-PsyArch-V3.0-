from __future__ import annotations

from pathlib import Path


STATIC = Path("apv3test/web/static")


def test_phase15_2_course_page_loads_dedicated_renderer_and_controls() -> None:
    html = (STATIC / "course.html").read_text(encoding="utf-8")

    assert "APV3 课程回放工作台" in html
    assert '<script src="/course.js"></script>' in html
    assert 'id="demoSelect"' in html
    assert 'id="tickTimeline"' in html
    assert 'id="courseTickSlider"' in html
    assert 'data-course-tab="packet"' in html
    assert 'data-course-tab="mind"' in html
    assert 'data-course-tab="summary"' in html


def test_phase15_2_frontend_fetches_runtime_trace_instead_of_hardcoding_outputs() -> None:
    js = (STATIC / "course.js").read_text(encoding="utf-8")

    assert 'courseApi("/api/course/demos")' in js
    assert 'courseApi("/api/course/run"' in js
    assert "/api/course/assets/" not in js
    assert "tick.ap_output" in js
    assert "tick.packet?.content_key" in js
    assert "summary.final_output" in js
    for forbidden in ("像是 黄", "像是 三角", "像是 苹果", "answerTable", "switch (demoId)"):
        assert forbidden not in js


def test_phase15_2_course_css_has_stable_three_pane_layout_and_mobile_fallback() -> None:
    css = (STATIC / "styles.css").read_text(encoding="utf-8")

    assert ".course-workspace" in css
    assert "grid-template-columns: minmax(320px" in css
    assert ".course-asset img" in css
    assert "height: 116px" in css
    assert ".tick-pill" in css
    assert "@media (max-width: 1080px)" in css
