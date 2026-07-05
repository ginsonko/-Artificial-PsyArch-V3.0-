from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from runtime.cognitive.state_pool.state_pool import load_constant


def build_demo_audit_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    top_k = int(load_constant("demo_substrate.audit_top_k"))
    window = int(load_constant("demo_substrate.timeline_window_ticks"))
    chat_trace = _rows(snapshot.get("chat_trace"))[-window:]
    runtime_trace = _rows(snapshot.get("runtime_trace"))[-window:]
    return {
        "schema_id": "apv3_demo_audit_snapshot/v1",
        "tick": int(snapshot.get("tick", 0) or 0),
        "mode": str(snapshot.get("mode", "")),
        "conversation_panel": {
            "latest_turn": chat_trace[-1] if chat_trace else {},
            "visible_turns": chat_trace[-top_k:],
        },
        "mind_panel": {
            "top_phrases": _rows(snapshot.get("top_phrases"))[:top_k],
            "feelings": _rows(snapshot.get("feelings"))[-top_k:],
            "phase8_audit": snapshot.get("phase8_audit", {}),
        },
        "learning_panel": {
            "chart": _rows(snapshot.get("chart"))[-top_k:],
            "metrics": dict(snapshot.get("metrics", {})) if isinstance(snapshot.get("metrics"), Mapping) else {},
        },
        "tick_replay_panel": {
            "runtime_trace": runtime_trace[-top_k:],
            "window_ticks": window,
        },
    }


def _rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]
