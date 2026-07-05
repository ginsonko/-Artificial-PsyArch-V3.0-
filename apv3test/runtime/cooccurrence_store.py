from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import sqlite3
from typing import Iterable, Mapping, Sequence

from apv3test.config.introspection_config import APV3CooccurrenceConfig


@dataclass(frozen=True)
class AssociationPair:
    key_a: str
    key_b: str
    cumulative_weight: float
    last_update_tick: int
    update_count: int

    def decayed_weight(self, current_tick: int, config: APV3CooccurrenceConfig) -> float:
        age = max(0, int(current_tick) - int(self.last_update_tick))
        return max(0.0, float(self.cumulative_weight)) * (float(config.half_life_decay) ** age)


class CooccurrenceAssociationStore:
    """Sparse AP-native association table for feeling-expression cooccurrence."""

    def __init__(
        self,
        config: APV3CooccurrenceConfig | None = None,
        pairs: Iterable[AssociationPair] = (),
        paradigm_pairs: Iterable[AssociationPair] = (),
    ) -> None:
        self.config = config or APV3CooccurrenceConfig()
        self._pairs: dict[tuple[str, str], AssociationPair] = {}
        self._by_a: dict[str, set[str]] = defaultdict(set)
        self._by_b: dict[str, set[str]] = defaultdict(set)
        self._paradigm_pairs: dict[tuple[str, str], AssociationPair] = {}
        self._paradigms_by_a: dict[str, set[str]] = defaultdict(set)
        self._labels_by_paradigm: dict[str, set[str]] = defaultdict(set)
        for pair in pairs:
            self._insert_pair(pair, paradigm=False)
        for pair in paradigm_pairs:
            self._insert_pair(pair, paradigm=True)

    @property
    def pairs(self) -> tuple[AssociationPair, ...]:
        return tuple(self._pairs[key] for key in sorted(self._pairs))

    @property
    def paradigm_pairs(self) -> tuple[AssociationPair, ...]:
        return tuple(self._paradigm_pairs[key] for key in sorted(self._paradigm_pairs))

    def observe(
        self,
        key_a: str,
        key_b: str,
        *,
        weight: float,
        current_tick: int,
        paradigm_id: str | None = None,
    ) -> None:
        self._observe_pair(
            self._pairs,
            key_a,
            key_b,
            weight=float(weight),
            current_tick=int(current_tick),
            paradigm=False,
        )
        if paradigm_id:
            self.observe_paradigm(key_a, paradigm_id, weight=weight, current_tick=current_tick)
        self._compact_label(key_a, current_tick=int(current_tick))

    def observe_paradigm(self, key_a: str, paradigm_id: str, *, weight: float, current_tick: int) -> None:
        self._observe_pair(
            self._paradigm_pairs,
            key_a,
            paradigm_id,
            weight=float(weight),
            current_tick=int(current_tick),
            paradigm=True,
        )
        self._compact_label(key_a, current_tick=int(current_tick))

    def similarity(self, key_a: str, key_b: str, current_tick: int) -> float:
        pair = self._pairs.get((str(key_a), str(key_b)))
        if pair is None:
            return 0.0
        return pair.decayed_weight(int(current_tick), self.config)

    def similarity_paradigm(self, key_a: str, paradigm_id: str, current_tick: int) -> float:
        pair = self._paradigm_pairs.get((str(key_a), str(paradigm_id)))
        if pair is None:
            return 0.0
        return pair.decayed_weight(int(current_tick), self.config)

    def nearest_by_label(self, labels: Sequence[str], *, top_k: int, current_tick: int) -> tuple[str, ...]:
        scores: dict[str, float] = defaultdict(float)
        for label in labels:
            for key_b in self._by_a.get(str(label), set()):
                scores[key_b] += self.similarity(str(label), key_b, current_tick)
        return _ranked_keys(scores, top_k)

    def nearest_paradigms_by_label(self, labels: Sequence[str], *, top_k: int, current_tick: int) -> tuple[str, ...]:
        scores: dict[str, float] = defaultdict(float)
        for label in labels:
            for paradigm_id in self._paradigms_by_a.get(str(label), set()):
                scores[paradigm_id] += self.similarity_paradigm(str(label), paradigm_id, current_tick)
        return _ranked_keys(scores, top_k)

    def compact(self, *, current_tick: int) -> None:
        for key_a in sorted(set(self._by_a) | set(self._paradigms_by_a)):
            self._compact_label(key_a, current_tick=int(current_tick))

    def retire_label(self, key_a: str, current_tick: int | None = None) -> None:
        label = str(key_a)
        for key_b in list(self._by_a.get(label, ())):
            self._pairs.pop((label, key_b), None)
            self._by_b[key_b].discard(label)
            if not self._by_b[key_b]:
                self._by_b.pop(key_b, None)
        self._by_a.pop(label, None)
        for paradigm_id in list(self._paradigms_by_a.get(label, ())):
            self._paradigm_pairs.pop((label, paradigm_id), None)
            self._labels_by_paradigm[paradigm_id].discard(label)
            if not self._labels_by_paradigm[paradigm_id]:
                self._labels_by_paradigm.pop(paradigm_id, None)
        self._paradigms_by_a.pop(label, None)

    def export_to_sqlite(self, conn: sqlite3.Connection) -> None:
        self._ensure_schema(conn)
        conn.execute("DELETE FROM cooccurrence_meta")
        conn.execute("INSERT INTO cooccurrence_meta(schema_version) VALUES (?)", (int(self.config.schema_version),))
        conn.execute("DELETE FROM cooccurrence_assoc")
        conn.execute("DELETE FROM cooccurrence_assoc_by_paradigm")
        conn.executemany(
            """
            INSERT OR REPLACE INTO cooccurrence_assoc
            (key_a, key_b, cumulative_weight, last_update_tick, update_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (pair.key_a, pair.key_b, pair.cumulative_weight, pair.last_update_tick, pair.update_count)
                for pair in self.pairs
            ],
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO cooccurrence_assoc_by_paradigm
            (key_a, paradigm_id, cumulative_weight, last_update_tick, update_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (pair.key_a, pair.key_b, pair.cumulative_weight, pair.last_update_tick, pair.update_count)
                for pair in self.paradigm_pairs
            ],
        )
        conn.commit()

    def import_from_sqlite(self, conn: sqlite3.Connection, *, current_tick: int) -> None:
        self._ensure_schema(conn)
        self._pairs.clear()
        self._by_a.clear()
        self._by_b.clear()
        self._paradigm_pairs.clear()
        self._paradigms_by_a.clear()
        self._labels_by_paradigm.clear()
        rows = conn.execute(
            """
            SELECT key_a, key_b, cumulative_weight, last_update_tick, update_count
            FROM cooccurrence_assoc
            ORDER BY key_a, key_b
            """
        ).fetchall()
        for row in rows:
            pair = AssociationPair(
                key_a=str(row["key_a"] if isinstance(row, sqlite3.Row) else row[0]),
                key_b=str(row["key_b"] if isinstance(row, sqlite3.Row) else row[1]),
                cumulative_weight=float(row["cumulative_weight"] if isinstance(row, sqlite3.Row) else row[2]),
                last_update_tick=int(row["last_update_tick"] if isinstance(row, sqlite3.Row) else row[3]),
                update_count=int(row["update_count"] if isinstance(row, sqlite3.Row) else row[4]),
            )
            if pair.decayed_weight(int(current_tick), self.config) >= self.config.eviction_floor:
                self._insert_pair(pair, paradigm=False)
        paradigm_rows = conn.execute(
            """
            SELECT key_a, paradigm_id, cumulative_weight, last_update_tick, update_count
            FROM cooccurrence_assoc_by_paradigm
            ORDER BY key_a, paradigm_id
            """
        ).fetchall()
        for row in paradigm_rows:
            pair = AssociationPair(
                key_a=str(row["key_a"] if isinstance(row, sqlite3.Row) else row[0]),
                key_b=str(row["paradigm_id"] if isinstance(row, sqlite3.Row) else row[1]),
                cumulative_weight=float(row["cumulative_weight"] if isinstance(row, sqlite3.Row) else row[2]),
                last_update_tick=int(row["last_update_tick"] if isinstance(row, sqlite3.Row) else row[3]),
                update_count=int(row["update_count"] if isinstance(row, sqlite3.Row) else row[4]),
            )
            if pair.decayed_weight(int(current_tick), self.config) >= self.config.eviction_floor:
                self._insert_pair(pair, paradigm=True)

    def snapshot(self) -> dict[str, list[dict[str, object]]]:
        return {
            "pairs": [_pair_payload(pair) for pair in self.pairs],
            "paradigm_pairs": [_pair_payload(pair) for pair in self.paradigm_pairs],
        }

    def export_state(self) -> dict[str, object]:
        return {
            "schema_id": "apv3_cooccurrence_association_store/v1",
            "pairs": [_pair_payload(pair) for pair in self.pairs],
            "paradigm_pairs": [_pair_payload(pair) for pair in self.paradigm_pairs],
        }

    @classmethod
    def from_state(
        cls,
        payload: object,
        config: APV3CooccurrenceConfig | None = None,
    ) -> "CooccurrenceAssociationStore":
        if not isinstance(payload, Mapping):
            return cls(config)
        pairs = _pairs_from_payload(payload.get("pairs"))
        paradigm_pairs = _pairs_from_payload(payload.get("paradigm_pairs"))
        return cls(config, pairs, paradigm_pairs)

    def _observe_pair(
        self,
        table: dict[tuple[str, str], AssociationPair],
        key_a: str,
        key_b: str,
        *,
        weight: float,
        current_tick: int,
        paradigm: bool,
    ) -> None:
        if weight <= 0.0:
            return
        left = str(key_a)
        right = str(key_b)
        bounded = min(float(self.config.cooccurrence_max_weight), max(0.0, float(weight)))
        old = table.get((left, right))
        if old is None:
            pair = AssociationPair(left, right, bounded, int(current_tick), 1)
        else:
            pair = AssociationPair(
                left,
                right,
                old.decayed_weight(int(current_tick), self.config) + bounded,
                int(current_tick),
                old.update_count + 1,
            )
        self._insert_pair(pair, paradigm=paradigm)

    def _insert_pair(self, pair: AssociationPair, *, paradigm: bool) -> None:
        if paradigm:
            self._paradigm_pairs[(pair.key_a, pair.key_b)] = pair
            self._paradigms_by_a[pair.key_a].add(pair.key_b)
            self._labels_by_paradigm[pair.key_b].add(pair.key_a)
        else:
            self._pairs[(pair.key_a, pair.key_b)] = pair
            self._by_a[pair.key_a].add(pair.key_b)
            self._by_b[pair.key_b].add(pair.key_a)

    def _compact_label(self, key_a: str, *, current_tick: int) -> None:
        label = str(key_a)
        for key_b in list(self._by_a.get(label, ())):
            if self.similarity(label, key_b, current_tick) < self.config.eviction_floor:
                self._pairs.pop((label, key_b), None)
                self._by_a[label].discard(key_b)
                self._by_b[key_b].discard(label)
                if not self._by_b[key_b]:
                    self._by_b.pop(key_b, None)
        if label in self._by_a and not self._by_a[label]:
            self._by_a.pop(label, None)
        for paradigm_id in list(self._paradigms_by_a.get(label, ())):
            if self.similarity_paradigm(label, paradigm_id, current_tick) < self.config.eviction_floor:
                self._paradigm_pairs.pop((label, paradigm_id), None)
                self._paradigms_by_a[label].discard(paradigm_id)
                self._labels_by_paradigm[paradigm_id].discard(label)
                if not self._labels_by_paradigm[paradigm_id]:
                    self._labels_by_paradigm.pop(paradigm_id, None)
        if label in self._paradigms_by_a and not self._paradigms_by_a[label]:
            self._paradigms_by_a.pop(label, None)

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cooccurrence_assoc (
                key_a TEXT NOT NULL,
                key_b TEXT NOT NULL,
                cumulative_weight REAL NOT NULL,
                last_update_tick INTEGER NOT NULL,
                update_count INTEGER NOT NULL,
                PRIMARY KEY (key_a, key_b)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assoc_by_a ON cooccurrence_assoc(key_a)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assoc_by_b ON cooccurrence_assoc(key_b)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cooccurrence_assoc_by_paradigm (
                key_a TEXT NOT NULL,
                paradigm_id TEXT NOT NULL,
                cumulative_weight REAL NOT NULL,
                last_update_tick INTEGER NOT NULL,
                update_count INTEGER NOT NULL,
                PRIMARY KEY (key_a, paradigm_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_assoc_paradigm_by_a ON cooccurrence_assoc_by_paradigm(key_a)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_assoc_paradigm_by_pid ON cooccurrence_assoc_by_paradigm(paradigm_id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cooccurrence_meta (
                schema_version INTEGER NOT NULL
            )
            """
        )


def _ranked_keys(scores: Mapping[str, float], top_k: int) -> tuple[str, ...]:
    rows = [(key, value) for key, value in scores.items() if value > 0.0]
    rows.sort(key=lambda item: (-item[1], item[0]))
    return tuple(key for key, _ in rows[: max(0, int(top_k))])


def _pair_payload(pair: AssociationPair) -> dict[str, object]:
    return {
        "key_a": pair.key_a,
        "key_b": pair.key_b,
        "cumulative_weight": round(pair.cumulative_weight, 12),
        "last_update_tick": pair.last_update_tick,
        "update_count": pair.update_count,
    }


def _pairs_from_payload(payload: object) -> tuple[AssociationPair, ...]:
    if not isinstance(payload, list):
        return ()
    result: list[AssociationPair] = []
    for item in payload:
        if not isinstance(item, Mapping):
            continue
        result.append(
            AssociationPair(
                key_a=str(item.get("key_a", "")),
                key_b=str(item.get("key_b", "")),
                cumulative_weight=float(item.get("cumulative_weight", 0.0)),
                last_update_tick=int(item.get("last_update_tick", 0)),
                update_count=int(item.get("update_count", 0)),
            )
        )
    return tuple(result)
