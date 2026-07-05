from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from apv3test.config.introspection_config import APV3CooccurrenceConfig


@dataclass(frozen=True)
class ExpressionPhraseRecord:
    """Observed ordered expression tokens for one expression paradigm."""

    phrase_id: str
    tokens: tuple[str, ...]
    support: float
    last_update_tick: int
    update_count: int
    style_tier: int = 2
    phrase_kind: str = ""

    def decayed_support(self, current_tick: int, config: APV3CooccurrenceConfig) -> float:
        age = max(0, int(current_tick) - int(self.last_update_tick))
        return max(0.0, float(self.support)) * (float(config.half_life_decay) ** age)

    def to_dict(self) -> dict[str, object]:
        return {
            "phrase_id": self.phrase_id,
            "tokens": list(self.tokens),
            "style_tier": int(self.style_tier),
            "phrase_kind": self.phrase_kind,
            "support": round(float(self.support), 12),
            "last_update_tick": int(self.last_update_tick),
            "update_count": int(self.update_count),
        }


class ExpressionPhraseMemory:
    """Generic ordered-token memory for learned expression phrase paradigms."""

    def __init__(
        self,
        config: APV3CooccurrenceConfig | None = None,
        records: Iterable[ExpressionPhraseRecord] = (),
        *,
        allow_new_phrases: bool = True,
    ) -> None:
        self.config = config or APV3CooccurrenceConfig()
        self.allow_new_phrases = bool(allow_new_phrases)
        self._records: dict[str, ExpressionPhraseRecord] = {}
        for record in records:
            if record.phrase_id:
                self._records[record.phrase_id] = record

    @property
    def records(self) -> tuple[ExpressionPhraseRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def observe(
        self,
        phrase_id: str,
        tokens: Sequence[str],
        *,
        weight: float,
        current_tick: int,
        style_tier: int | None = None,
        phrase_kind: str | None = None,
        allow_new: bool | None = None,
    ) -> bool:
        pid = str(phrase_id)
        sequence = tuple(str(token) for token in tokens if str(token))
        if not pid or not sequence or weight <= 0.0:
            return False
        bounded = min(float(self.config.cooccurrence_max_weight), max(0.0, float(weight)))
        old = self._records.get(pid)
        can_add = self.allow_new_phrases if allow_new is None else bool(allow_new)
        if old is None and not can_add:
            return False
        if old is None or old.tokens != sequence:
            support = bounded
            update_count = 1
            tier = _bounded_tier(style_tier if style_tier is not None else 2)
            kind = str(phrase_kind or "")
        else:
            support = old.decayed_support(int(current_tick), self.config) + bounded
            update_count = old.update_count + 1
            tier = _bounded_tier(style_tier if style_tier is not None else old.style_tier)
            kind = old.phrase_kind if phrase_kind is None else str(phrase_kind)
        self._records[pid] = ExpressionPhraseRecord(
            phrase_id=pid,
            tokens=sequence,
            style_tier=tier,
            phrase_kind=kind,
            support=support,
            last_update_tick=int(current_tick),
            update_count=update_count,
        )
        self.compact(current_tick=current_tick)
        return True

    def tokens_for(self, phrase_id: str, *, current_tick: int) -> tuple[str, ...]:
        record = self._records.get(str(phrase_id))
        if record is None:
            return ()
        if record.decayed_support(int(current_tick), self.config) < self.config.eviction_floor:
            return ()
        return record.tokens

    def adjust_support(self, phrase_id: str, *, delta: float, current_tick: int) -> bool:
        record = self._records.get(str(phrase_id))
        if record is None:
            return False
        support = max(0.0, record.decayed_support(int(current_tick), self.config) + float(delta))
        self._records[str(phrase_id)] = ExpressionPhraseRecord(
            phrase_id=record.phrase_id,
            tokens=record.tokens,
            style_tier=record.style_tier,
            phrase_kind=record.phrase_kind,
            support=support,
            last_update_tick=int(current_tick),
            update_count=record.update_count + 1,
        )
        self.compact(current_tick=current_tick)
        return True

    def recall(
        self,
        phrase_ids: Sequence[str],
        *,
        top_k: int,
        current_tick: int,
        style_bias: float | None = None,
    ) -> tuple[ExpressionPhraseRecord, ...]:
        candidates: list[tuple[float, ExpressionPhraseRecord]] = []
        bias = self.config.expression_style_bias if style_bias is None else max(0.0, float(style_bias))
        for phrase_id in phrase_ids:
            record = self._records.get(str(phrase_id))
            if record is None:
                continue
            support = record.decayed_support(int(current_tick), self.config)
            if support >= self.config.eviction_floor:
                candidates.append((support * _style_multiplier(record.style_tier, bias), record))
        candidates.sort(key=lambda item: (-item[0], item[1].phrase_id))
        return tuple(record for _, record in candidates[: max(0, int(top_k))])

    def compact(self, *, current_tick: int) -> None:
        if not self.allow_new_phrases:
            return
        for phrase_id, record in list(self._records.items()):
            if record.decayed_support(int(current_tick), self.config) < self.config.eviction_floor:
                self._records.pop(phrase_id, None)

    def snapshot(self) -> dict[str, list[dict[str, object]]]:
        return {"records": [record.to_dict() for record in self.records]}

    def export_state(self) -> dict[str, object]:
        return {
            "schema_id": "apv3_expression_phrase_memory/v1",
            "allow_new_phrases": self.allow_new_phrases,
            "records": [record.to_dict() for record in self.records],
        }

    @classmethod
    def from_state(
        cls,
        payload: object,
        config: APV3CooccurrenceConfig | None = None,
    ) -> "ExpressionPhraseMemory":
        if not isinstance(payload, Mapping):
            return cls(config)
        records = []
        raw = payload.get("records")
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, Mapping):
                    continue
                records.append(
                    ExpressionPhraseRecord(
                        phrase_id=str(item.get("phrase_id", "")),
                        tokens=tuple(str(token) for token in item.get("tokens", ()) if str(token)),
                        style_tier=_bounded_tier(item.get("style_tier", 2)),
                        phrase_kind=str(item.get("phrase_kind", "")),
                        support=float(item.get("support", 0.0)),
                        last_update_tick=int(item.get("last_update_tick", 0)),
                        update_count=int(item.get("update_count", 0)),
                    )
                )
        return cls(config, records, allow_new_phrases=bool(payload.get("allow_new_phrases", True)))

    @classmethod
    def from_seed_corpus(
        cls,
        path: str | Path,
        config: APV3CooccurrenceConfig | None = None,
        *,
        current_tick: int = 0,
    ) -> "ExpressionPhraseMemory":
        cfg = config or APV3CooccurrenceConfig()
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        records: list[ExpressionPhraseRecord] = []
        if not isinstance(raw, list):
            raise ValueError("seed corpus must be a list")
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            phrase_id = str(item.get("phrase_id", ""))
            tokens = tuple(str(token) for token in item.get("tokens", ()) if str(token))
            if not phrase_id or not tokens:
                continue
            records.append(
                ExpressionPhraseRecord(
                    phrase_id=phrase_id,
                    tokens=tokens,
                    style_tier=_bounded_tier(item.get("style_tier", 2)),
                    phrase_kind=str(item.get("phrase_kind", "")),
                    support=float(cfg.seed_initial_support),
                    last_update_tick=int(current_tick),
                    update_count=1,
                )
            )
        return cls(cfg, records, allow_new_phrases=False)

    def phrase_id_for_tokens(self, tokens: Sequence[str]) -> str:
        sequence = tuple(str(token) for token in tokens if str(token))
        for record in self.records:
            if record.tokens == sequence:
                return record.phrase_id
        return ""


def _bounded_tier(value: object) -> int:
    try:
        tier = int(value)
    except (TypeError, ValueError):
        tier = 2
    return max(0, min(2, tier))


def _style_multiplier(style_tier: int, style_bias: float) -> float:
    tier = _bounded_tier(style_tier)
    return 1.0 + max(0.0, float(style_bias)) * (2 - tier) / 2.0
