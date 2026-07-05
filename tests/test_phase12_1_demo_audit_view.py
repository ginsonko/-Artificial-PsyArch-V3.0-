from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from apv3test.web_chat import APV3WebChatApp
from runtime.demo_substrate.audit_view import build_demo_audit_snapshot


def test_demo_audit_snapshot_builds_bounded_workbench_panels() -> None:
    snapshot = {
        "tick": 12,
        "mode": "uncertain",
        "chat_trace": [{"tick": tick, "reply_text": str(tick)} for tick in range(12)],
        "runtime_trace": [{"tick": tick, "candidate_count": tick} for tick in range(12)],
        "feelings": [{"tick": tick, "label": "feeling"} for tick in range(12)],
        "top_phrases": [{"text": str(tick)} for tick in range(12)],
        "chart": [{"tick": tick} for tick in range(12)],
        "metrics": {"fallback_count": 1},
        "phase8_audit": {"ledger_pie": []},
    }

    audit = build_demo_audit_snapshot(snapshot)

    assert audit["schema_id"] == "apv3_demo_audit_snapshot/v1"
    assert len(audit["conversation_panel"]["visible_turns"]) <= 5
    assert len(audit["mind_panel"]["top_phrases"]) <= 5
    assert audit["learning_panel"]["metrics"]["fallback_count"] == 1


def test_web_chat_snapshot_exposes_phase12_demo_payload(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "web.sqlite")
    payload = app.send({"text": "hello", "mode": "uncertain"})

    assert "phase12_demo" in payload["snapshot"]
    assert "conversation_panel" in payload["snapshot"]["phase12_demo"]


def test_phase12_1_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "12.1"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 12.1 deliverables present" in completed.stdout
