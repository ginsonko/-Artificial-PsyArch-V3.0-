from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

from apv3test.web_chat import APV3WebChatApp, make_handler


def test_phase8_11_web_snapshot_exposes_render_only_cognitive_audit(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "web.sqlite")
    payload = app.send({"text": "hello", "mode": "uncertain"})
    audit = payload["snapshot"]["phase8_audit"]

    assert audit["ledger_pie"]
    assert "reality_sense" in audit["feelings_display"]
    assert audit["endogenous_chain"]
    assert audit["visual_focus_overlay"]


def test_phase8_11_web_api_serves_phase8_audit_payload(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "web-api.sqlite")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        _post_json(f"{base}/api/message", {"text": "hello", "mode": "uncertain"})
        snapshot = json.loads(urlopen(f"{base}/api/state", timeout=5).read().decode("utf-8"))
        html = urlopen(f"{base}/", timeout=5).read().decode("utf-8")

        assert "phase8_audit" in snapshot
        assert "visual_focus_overlay" in snapshot["phase8_audit"]
        assert "Phase20.6" in html
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=raw, headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urlopen(req, timeout=5).read().decode("utf-8"))
