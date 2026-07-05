from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class DeferredIntention:
    action_id: str
    cue_sa_ids: tuple[str, ...]
    support: float
    created_tick: int


class DeferredIntentionMemory:
    def __init__(self, intentions: Iterable[DeferredIntention] = ()) -> None:
        self.intentions = list(intentions)

    def learn_intention(
        self,
        *,
        action_id: str,
        cue_sa_ids: Iterable[str],
        support: float = 1.0,
        created_tick: int = 0,
    ) -> DeferredIntention:
        """@op_count: O(cue_count)."""
        intention = DeferredIntention(
            action_id=action_id,
            cue_sa_ids=tuple(cue_sa_ids),
            support=float(support),
            created_tick=int(created_tick),
        )
        self.intentions.append(intention)
        return intention

    def recall_for_cues(self, cue_sa_ids: Iterable[str]) -> tuple[DeferredIntention, ...]:
        """@op_count: O(intentions * cue_count)."""
        cue_set = set(cue_sa_ids)
        matched = tuple(
            intention
            for intention in self.intentions
            if cue_set.intersection(intention.cue_sa_ids)
        )
        return tuple(sorted(matched, key=lambda item: (item.support, item.created_tick), reverse=True))

    def to_state(self) -> list[dict[str, object]]:
        """@op_count: O(intentions)."""
        return [
            {**asdict(intention), "cue_sa_ids": list(intention.cue_sa_ids)}
            for intention in self.intentions
        ]

    @classmethod
    def from_state(cls, state: object) -> DeferredIntentionMemory:
        """@op_count: O(intentions)."""
        rows = state if isinstance(state, list) else []
        intentions = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            intentions.append(
                DeferredIntention(
                    action_id=str(row.get("action_id", "")),
                    cue_sa_ids=tuple(str(item) for item in row.get("cue_sa_ids", ())),
                    support=float(row.get("support", 0.0)),
                    created_tick=int(row.get("created_tick", 0)),
                )
            )
        return cls(intentions)

    def save_sqlite(self, path: str | Path) -> None:
        """@op_count: O(intentions)."""
        payload = json.dumps(self.to_state(), ensure_ascii=False, sort_keys=True)
        with sqlite3.connect(Path(path)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS deferred_intentions (key TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            conn.execute(
                "REPLACE INTO deferred_intentions(key, payload) VALUES (?, ?)",
                ("default", payload),
            )

    @classmethod
    def load_sqlite(cls, path: str | Path) -> DeferredIntentionMemory:
        """@op_count: O(intentions)."""
        if not Path(path).exists():
            return cls()
        with sqlite3.connect(Path(path)) as conn:
            row = conn.execute(
                "SELECT payload FROM deferred_intentions WHERE key = ?",
                ("default",),
            ).fetchone()
        if row is None:
            return cls()
        return cls.from_state(json.loads(str(row[0])))
