from __future__ import annotations

import sqlite3
import time
from contextlib import closing
import json
from pathlib import Path
from typing import Any

from apv3test.runtime.runtime_state_codec import RuntimeStateCodec


class SQLiteRuntimeStore:
    """SQLite persistence for AP-native runtime ontology state.

    This store is intentionally narrow: it persists the authoritative runtime
    state envelope and does not read audit traces, score breakdowns, or display
    payloads. Retrieval must therefore remain valid after the audit database is
    deleted.
    """

    def __init__(self, db_path: str | Path, codec: RuntimeStateCodec | None = None) -> None:
        self.db_path = Path(db_path)
        self.codec = codec or RuntimeStateCodec()

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_states (
                    state_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schema_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    codec TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    raw_bytes INTEGER NOT NULL,
                    stored_bytes INTEGER NOT NULL,
                    blob BLOB NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_runtime_states_created_at "
                "ON runtime_states(created_at)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS online_embedding_tokens (
                    state_id INTEGER NOT NULL,
                    token TEXT NOT NULL,
                    vector_json TEXT NOT NULL,
                    support REAL NOT NULL DEFAULT 0.0,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (state_id, token)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS explicit_transitions (
                    state_id INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    support REAL NOT NULL DEFAULT 0.0,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paradigm_sa (
                    state_id INTEGER NOT NULL,
                    pid TEXT NOT NULL,
                    support REAL NOT NULL DEFAULT 0.0,
                    conf REAL NOT NULL DEFAULT 0.0,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (state_id, pid)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS action_outcomes (
                    state_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    drive_bias REAL NOT NULL DEFAULT 0.0,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (state_id, action)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS percept_prototypes (
                    state_id INTEGER NOT NULL,
                    prototype_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (state_id, prototype_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paradigm_observations (
                    state_id INTEGER NOT NULL,
                    observation_id TEXT NOT NULL,
                    bucket TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (state_id, observation_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paradigm_stats (
                    state_id INTEGER NOT NULL,
                    bucket TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (state_id, bucket)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS role_transition_stats (
                    state_id INTEGER NOT NULL,
                    stat_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (state_id, stat_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_explicit_transitions_source "
                "ON explicit_transitions(state_id, source)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS phase20_6_fast_action_chains (
                    state_id INTEGER NOT NULL,
                    chain_id TEXT NOT NULL,
                    context_signature TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    next_outcome_kind TEXT NOT NULL,
                    support REAL NOT NULL DEFAULT 0.0,
                    update_count INTEGER NOT NULL DEFAULT 0,
                    last_tick INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (state_id, chain_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_phase20_6_fast_context
                ON phase20_6_fast_action_chains(state_id, context_signature)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS phase20_6_slow_memory (
                    state_id INTEGER NOT NULL,
                    memory_id TEXT NOT NULL,
                    source_candidate_id TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    support REAL NOT NULL DEFAULT 0.0,
                    update_count INTEGER NOT NULL DEFAULT 0,
                    last_tick INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (state_id, memory_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_phase20_6_slow_source
                ON phase20_6_slow_memory(state_id, source_candidate_id)
                """
            )
            conn.commit()

    def save_state(self, state: dict[str, Any]) -> int:
        self.initialize()
        envelope = self.codec.encode(state)
        schema_id = str(state.get("schema_id", "apv3_runtime_ontology_state/v1") or "")
        with closing(self._connect()) as conn:
            cur = conn.execute(
                """
                INSERT INTO runtime_states
                (schema_id, created_at, codec, sha256, raw_bytes, stored_bytes, blob)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    schema_id,
                    time.time(),
                    str(envelope["codec"]),
                    str(envelope["sha256"]),
                    int(envelope["raw_bytes"]),
                    int(envelope["stored_bytes"]),
                    sqlite3.Binary(envelope["blob"]),
                ),
            )
            conn.commit()
            state_id = int(cur.lastrowid)
        self._write_projection(state_id, state)
        return state_id

    def load_state(self, state_id: int | None = None) -> dict[str, Any]:
        self.initialize()
        if state_id is None:
            query = (
                "SELECT codec, sha256, raw_bytes, stored_bytes, blob "
                "FROM runtime_states ORDER BY state_id DESC LIMIT 1"
            )
            params: tuple[object, ...] = ()
        else:
            query = (
                "SELECT codec, sha256, raw_bytes, stored_bytes, blob "
                "FROM runtime_states WHERE state_id = ?"
            )
            params = (int(state_id),)
        with closing(self._connect()) as conn:
            row = conn.execute(query, params).fetchone()
        if row is None:
            raise KeyError("runtime state not found")
        envelope = {
            "codec": row["codec"],
            "sha256": row["sha256"],
            "raw_bytes": row["raw_bytes"],
            "stored_bytes": row["stored_bytes"],
            "blob": bytes(row["blob"]),
        }
        return self.codec.decode(envelope)

    def ontology_counts(self, state_id: int | None = None) -> dict[str, int]:
        self.initialize()
        resolved_state_id = self._resolve_state_id(state_id)
        tables = {
            "online_embedding_tokens": "online_embedding_tokens",
            "explicit_transitions": "explicit_transitions",
            "paradigm_sa": "paradigm_sa",
            "action_outcomes": "action_outcomes",
            "percept_prototypes": "percept_prototypes",
            "phase20_6_fast_action_chains": "phase20_6_fast_action_chains",
            "phase20_6_slow_memory": "phase20_6_slow_memory",
        }
        counts: dict[str, int] = {}
        with closing(self._connect()) as conn:
            for key, table in tables.items():
                row = conn.execute(
                    f"SELECT COUNT(*) AS n FROM {table} WHERE state_id = ?",
                    (resolved_state_id,),
                ).fetchone()
                counts[key] = int(row["n"])
        return counts

    def load_ontology_projection(self, state_id: int | None = None) -> dict[str, Any]:
        self.initialize()
        resolved_state_id = self._resolve_state_id(state_id)
        with closing(self._connect()) as conn:
            token_rows = conn.execute(
                """
                SELECT token, vector_json, support, payload_json
                FROM online_embedding_tokens
                WHERE state_id = ?
                ORDER BY token
                """,
                (resolved_state_id,),
            ).fetchall()
            transition_rows = conn.execute(
                """
                SELECT source, target, support, payload_json
                FROM explicit_transitions
                WHERE state_id = ?
                ORDER BY source, target
                """,
                (resolved_state_id,),
            ).fetchall()
            paradigm_rows = conn.execute(
                """
                SELECT pid, support, conf, payload_json
                FROM paradigm_sa
                WHERE state_id = ?
                ORDER BY pid
                """,
                (resolved_state_id,),
            ).fetchall()
            outcome_rows = conn.execute(
                """
                SELECT action, drive_bias, payload_json
                FROM action_outcomes
                WHERE state_id = ?
                ORDER BY action
                """,
                (resolved_state_id,),
            ).fetchall()
            prototype_rows = conn.execute(
                """
                SELECT prototype_id, payload_json
                FROM percept_prototypes
                WHERE state_id = ?
                ORDER BY prototype_id
                """,
                (resolved_state_id,),
            ).fetchall()
            observation_rows = conn.execute(
                """
                SELECT observation_id, bucket, payload_json
                FROM paradigm_observations
                WHERE state_id = ?
                ORDER BY observation_id
                """,
                (resolved_state_id,),
            ).fetchall()
            paradigm_stat_rows = conn.execute(
                """
                SELECT bucket, payload_json
                FROM paradigm_stats
                WHERE state_id = ?
                ORDER BY bucket
                """,
                (resolved_state_id,),
            ).fetchall()
            role_transition_rows = conn.execute(
                """
                SELECT stat_id, payload_json
                FROM role_transition_stats
                WHERE state_id = ?
                ORDER BY stat_id
                """,
                (resolved_state_id,),
            ).fetchall()
        return {
            "state_id": resolved_state_id,
            "online_embedding_tokens": [
                {
                    "token": row["token"],
                    "vector": json.loads(row["vector_json"]),
                    "support": float(row["support"]),
                    "payload": json.loads(row["payload_json"]),
                }
                for row in token_rows
            ],
            "explicit_transitions": [json.loads(row["payload_json"]) for row in transition_rows],
            "paradigm_sa": [json.loads(row["payload_json"]) for row in paradigm_rows],
            "action_outcomes": {
                str(row["action"]): json.loads(row["payload_json"]) for row in outcome_rows
            },
            "percept_prototypes": [json.loads(row["payload_json"]) for row in prototype_rows],
            "paradigm_observations": [json.loads(row["payload_json"]) for row in observation_rows],
            "paradigm_stats": {
                str(row["bucket"]): json.loads(row["payload_json"]) for row in paradigm_stat_rows
            },
            "role_transition_stats": [json.loads(row["payload_json"]) for row in role_transition_rows],
        }

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _resolve_state_id(self, state_id: int | None) -> int:
        if state_id is not None:
            return int(state_id)
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT state_id FROM runtime_states ORDER BY state_id DESC LIMIT 1").fetchone()
        if row is None:
            raise KeyError("runtime state not found")
        return int(row["state_id"])

    def _write_projection(self, state_id: int, state: dict[str, Any]) -> None:
        with closing(self._connect()) as conn:
            self._clear_projection(conn, state_id)
            self._insert_online_embedding(conn, state_id, state.get("online_embedding", {}))
            self._insert_transitions(conn, state_id, state.get("transitions", []))
            self._insert_paradigms(conn, state_id, state.get("paradigms", []))
            self._insert_action_outcomes(conn, state_id, state.get("action_outcomes", {}))
            self._insert_percept_prototypes(conn, state_id, state.get("percept_prototypes", []))
            self._insert_paradigm_observations(conn, state_id, state.get("paradigm_observations", []))
            self._insert_paradigm_stats(conn, state_id, state.get("paradigm_stats", {}))
            self._insert_role_transition_stats(conn, state_id, state.get("role_transition_stats", []))
            self._insert_phase20_6_fast_action_chains(conn, state_id, state.get("phase20_6_fast_action_chains", {}))
            self._insert_phase20_6_slow_memory(conn, state_id, state.get("phase20_6_slow_memory", {}))
            conn.commit()

    def _clear_projection(self, conn: sqlite3.Connection, state_id: int) -> None:
        for table in (
            "online_embedding_tokens",
            "explicit_transitions",
            "paradigm_sa",
            "action_outcomes",
            "percept_prototypes",
            "paradigm_observations",
            "paradigm_stats",
            "role_transition_stats",
            "phase20_6_fast_action_chains",
            "phase20_6_slow_memory",
        ):
            conn.execute(f"DELETE FROM {table} WHERE state_id = ?", (state_id,))

    def _insert_online_embedding(self, conn: sqlite3.Connection, state_id: int, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        tokens = payload.get("tokens", {})
        if not isinstance(tokens, dict):
            return
        for token, token_payload in tokens.items():
            if isinstance(token_payload, dict):
                vector = token_payload.get("vector", [])
                support = _as_float(token_payload.get("support"))
                full_payload = token_payload
            else:
                vector = token_payload
                support = 0.0
                full_payload = {"vector": vector, "support": support}
            conn.execute(
                """
                INSERT INTO online_embedding_tokens
                (state_id, token, vector_json, support, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    state_id,
                    str(token),
                    _json_dump(vector),
                    support,
                    _json_dump(full_payload),
                ),
            )

    def _insert_transitions(self, conn: sqlite3.Connection, state_id: int, payload: object) -> None:
        if not isinstance(payload, list):
            return
        for item in payload:
            if not isinstance(item, dict):
                continue
            conn.execute(
                """
                INSERT INTO explicit_transitions
                (state_id, source, target, support, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    state_id,
                    str(item.get("source", "")),
                    str(item.get("target", "")),
                    _as_float(item.get("support")),
                    _json_dump(item),
                ),
            )

    def _insert_paradigms(self, conn: sqlite3.Connection, state_id: int, payload: object) -> None:
        if not isinstance(payload, list):
            return
        for item in payload:
            if not isinstance(item, dict):
                continue
            pid = str(item.get("pid", "") or item.get("id", ""))
            if not pid:
                continue
            conn.execute(
                """
                INSERT INTO paradigm_sa
                (state_id, pid, support, conf, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    state_id,
                    pid,
                    _as_float(item.get("support")),
                    _as_float(item.get("conf")),
                    _json_dump(item),
                ),
            )

    def _insert_action_outcomes(self, conn: sqlite3.Connection, state_id: int, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        for action, item in payload.items():
            item_payload = item if isinstance(item, dict) else {"value": item}
            conn.execute(
                """
                INSERT INTO action_outcomes
                (state_id, action, drive_bias, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    state_id,
                    str(action),
                    _as_float(item_payload.get("drive_bias")),
                    _json_dump(item_payload),
                ),
            )

    def _insert_percept_prototypes(self, conn: sqlite3.Connection, state_id: int, payload: object) -> None:
        if not isinstance(payload, list):
            return
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                continue
            prototype_id = str(item.get("prototype_id", "") or item.get("id", "") or f"prototype:{index}")
            conn.execute(
                """
                INSERT INTO percept_prototypes
                (state_id, prototype_id, payload_json)
                VALUES (?, ?, ?)
                """,
                (state_id, prototype_id, _json_dump(item)),
            )

    def _insert_paradigm_observations(self, conn: sqlite3.Connection, state_id: int, payload: object) -> None:
        if not isinstance(payload, list):
            return
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                continue
            observation_id = str(item.get("observation_id", "") or f"observation:{index}")
            bucket = str(item.get("bucket", ""))
            conn.execute(
                """
                INSERT INTO paradigm_observations
                (state_id, observation_id, bucket, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (state_id, observation_id, bucket, _json_dump(item)),
            )

    def _insert_paradigm_stats(self, conn: sqlite3.Connection, state_id: int, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        for bucket, item in payload.items():
            if not isinstance(item, dict):
                continue
            conn.execute(
                """
                INSERT INTO paradigm_stats
                (state_id, bucket, payload_json)
                VALUES (?, ?, ?)
                """,
                (state_id, str(bucket), _json_dump(item)),
            )

    def _insert_role_transition_stats(self, conn: sqlite3.Connection, state_id: int, payload: object) -> None:
        if not isinstance(payload, list):
            return
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                continue
            stat_id = ":".join(
                (
                    str(item.get("prev_role", "")),
                    str(item.get("role", "")),
                    str(index),
                )
            )
            conn.execute(
                """
                INSERT INTO role_transition_stats
                (state_id, stat_id, payload_json)
                VALUES (?, ?, ?)
                """,
                (state_id, stat_id, _json_dump(item)),
            )

    def _insert_phase20_6_fast_action_chains(self, conn: sqlite3.Connection, state_id: int, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        rows = payload.get("chains", [])
        if not isinstance(rows, list):
            return
        for item in rows:
            if not isinstance(item, dict):
                continue
            chain_id = str(item.get("chain_id", ""))
            if not chain_id:
                continue
            conn.execute(
                """
                INSERT INTO phase20_6_fast_action_chains
                (state_id, chain_id, context_signature, step_index, next_outcome_kind,
                 support, update_count, last_tick, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state_id,
                    chain_id,
                    str(item.get("context_signature", "")),
                    int(item.get("step_index", 0) or 0),
                    str(item.get("next_outcome_kind", "")),
                    _as_float(item.get("support")),
                    int(item.get("update_count", 0) or 0),
                    int(item.get("last_tick", 0) or 0),
                    _json_dump(item),
                ),
            )

    def _insert_phase20_6_slow_memory(self, conn: sqlite3.Connection, state_id: int, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        rows = payload.get("memories", [])
        if not isinstance(rows, list):
            return
        for item in rows:
            if not isinstance(item, dict):
                continue
            memory_id = str(item.get("memory_id", ""))
            if not memory_id:
                continue
            conn.execute(
                """
                INSERT INTO phase20_6_slow_memory
                (state_id, memory_id, source_candidate_id, source_kind,
                 support, update_count, last_tick, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state_id,
                    memory_id,
                    str(item.get("source_candidate_id", "")),
                    str(item.get("source_kind", "")),
                    _as_float(item.get("support")),
                    int(item.get("update_count", 0) or 0),
                    int(item.get("last_tick", 0) or 0),
                    _json_dump(item),
                ),
            )


def _json_dump(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
