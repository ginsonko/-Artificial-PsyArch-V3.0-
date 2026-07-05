from __future__ import annotations

import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any


class SQLiteAuditStore:
    """Bounded white-box audit trace store.

    Audit rows are useful for inspection, but AP runtime must never depend on
    them. The payload is JSON text by design because it is not the authoritative
    compressed runtime ontology.
    """

    def __init__(self, db_path: str | Path, budget_bytes: int | None = None) -> None:
        self.db_path = Path(db_path)
        self.budget_bytes = budget_bytes

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    event_kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_events_created_at "
                "ON audit_events(created_at)"
            )
            conn.commit()

    def append_event(self, event_kind: str, payload: dict[str, Any]) -> int:
        self.initialize()
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with closing(self._connect()) as conn:
            cur = conn.execute(
                """
                INSERT INTO audit_events (created_at, event_kind, payload_json)
                VALUES (?, ?, ?)
                """,
                (time.time(), str(event_kind), payload_json),
            )
            conn.commit()
        self.prune_to_budget()
        return int(cur.lastrowid)

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        self.initialize()
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT event_id, created_at, event_kind, payload_json
                FROM audit_events
                ORDER BY event_id DESC
                LIMIT ?
                """,
                (max(0, int(limit)),),
            ).fetchall()
        return [
            {
                "event_id": int(row["event_id"]),
                "created_at": float(row["created_at"]),
                "event_kind": str(row["event_kind"]),
                "payload": json.loads(str(row["payload_json"])),
            }
            for row in rows
        ]

    def prune_to_budget(self) -> None:
        if self.budget_bytes is None or self.budget_bytes <= 0:
            return
        if not self.db_path.exists() or self.db_path.stat().st_size <= self.budget_bytes:
            return
        with closing(self._connect()) as conn:
            while self.db_path.exists() and self.db_path.stat().st_size > self.budget_bytes:
                row = conn.execute(
                    "SELECT event_id FROM audit_events ORDER BY event_id ASC LIMIT 1"
                ).fetchone()
                if row is None:
                    break
                conn.execute("DELETE FROM audit_events WHERE event_id = ?", (int(row["event_id"]),))
                conn.execute("PRAGMA incremental_vacuum(1)")
                conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
