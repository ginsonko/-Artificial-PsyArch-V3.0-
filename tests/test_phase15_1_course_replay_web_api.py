from __future__ import annotations

import json
import sqlite3
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from apv3test.web_chat import APV3WebChatApp, make_handler


def test_phase15_1_web_api_serves_course_page_demos_trace_and_assets(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "web.sqlite")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        html = urlopen(f"{base}/course.html", timeout=5).read().decode("utf-8")
        demos = json.loads(urlopen(f"{base}/api/course/demos", timeout=5).read().decode("utf-8"))
        trace = _post_json(f"{base}/api/course/run", {"demo_id": "demo_color_yellow"})
        synthetic = [demo for demo in demos["demos"] if demo.get("demo_group") == "synthetic"]

        assert "APV3 课程回放工作台" in html
        assert len(synthetic) == 5
        assert any(demo.get("demo_group") == "clean_card" for demo in demos["demos"])
        assert trace["summary"]["runtime_generated"] is True
        assert trace["summary"]["tick_count"] == 6
        assert trace["ticks"][0]["asset_refs"][0].startswith("asset::color_yellow::train::")

        asset_id = trace["ticks"][0]["asset_refs"][0]
        req = Request(f"{base}/api/course/assets/{asset_id}")
        asset = urlopen(req, timeout=5)
        raw = asset.read()
        assert raw.startswith(b"\x89PNG")
        assert asset.headers.get_content_type() == "image/png"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_phase15_1_asset_route_rejects_non_manifest_or_path_like_ids(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "web.sqlite")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        for suffix in ("../../README.md", "asset::does_not_exist::train::0"):
            try:
                urlopen(f"{base}/api/course/assets/{suffix}", timeout=5).read()
            except HTTPError as exc:
                assert exc.code == 404
            else:
                raise AssertionError(f"unsafe asset id unexpectedly served: {suffix}")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_phase15_1_course_replay_uses_separate_sqlite_from_chat_db(tmp_path: Path) -> None:
    chat_db = tmp_path / "web.sqlite"
    app = APV3WebChatApp(state_db_path=chat_db)
    payload = app.course_run({"demo_id": "demo_feedback_correct"})
    course_db = tmp_path / "web_course_replay.sqlite"

    assert payload["summary"]["runtime_generated"] is True
    assert course_db.exists()
    with sqlite3.connect(course_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM course_replay_trace").fetchone()[0]
    assert count == 1

    if chat_db.exists():
        with sqlite3.connect(chat_db) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "course_replay_trace" not in tables


def _post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=raw, headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urlopen(req, timeout=5).read().decode("utf-8"))
