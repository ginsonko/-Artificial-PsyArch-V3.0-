from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig
from apv3test.runtime.alignment import AlignmentColumn
from apv3test.runtime.paradigm_discovery import DiscoveredParadigm


@dataclass(frozen=True)
class FillCandidate:
    label: str
    score: float
    source: str


@dataclass(frozen=True)
class DraftCandidate:
    label: str
    role: str
    strength: float
    anchor_meta: dict[str, object]


class ParadigmSlotFiller:
    """AP-native slot filler over first-class SA candidates."""

    def __init__(self, config: APV3ParadigmDiscoveryConfig | None = None) -> None:
        self.config = config or APV3ParadigmDiscoveryConfig()

    def fill(
        self,
        paradigm: DiscoveredParadigm,
        *,
        focus_tokens: Sequence[str],
        candidate_pool: Sequence[str],
        successor_virtuals: Mapping[str, float] | None = None,
    ) -> tuple[DraftCandidate, ...]:
        if paradigm.conf <= 0.0:
            return ()
        successors = successor_virtuals or {}
        drafts: list[DraftCandidate] = []
        previous_prefix = ""
        slot_index = 0
        unresolved_slots = 0
        used_labels: set[str] = set()
        for column in paradigm.columns:
            if column.role == "slot":
                candidate = self._best_slot_candidate(
                    column,
                    focus_tokens=focus_tokens,
                    candidate_pool=candidate_pool,
                    successors=successors,
                    used_labels=used_labels,
                )
                if candidate is None:
                    unresolved_slots += 1
                    continue
                label = candidate.label
                source = candidate.source
                strength = candidate.score * max(0.0, paradigm.conf)
                slot_index += 1
                used_labels.add(label)
            elif column.anchor_label:
                label = column.anchor_label
                source = "paradigm_column"
                strength = max(0.0, paradigm.conf) * column.occupancy
            else:
                continue
            undecidable_fragment = column.role in {"fixed_anchor", "shared_fragment"} and unresolved_slots > 0
            if undecidable_fragment:
                source += "+undecidable_fragment"
            drafts.append(
                DraftCandidate(
                    label=label,
                    role=column.role,
                    strength=round(strength, 6),
                    anchor_meta={
                        "schema_id": "text_visible_draft_token/v1",
                        "previous_prefix": previous_prefix,
                        "visible_length": len(previous_prefix),
                        "column_index": column.col_index,
                        "role": column.role,
                        "source": source,
                        "slot_index": slot_index if column.role == "slot" else None,
                        "unresolved_slots_before": unresolved_slots,
                        "undecidable_fragment": undecidable_fragment,
                    },
                )
            )
            previous_prefix += label
        return tuple(drafts)

    def _best_slot_candidate(
        self,
        column: AlignmentColumn,
        *,
        focus_tokens: Sequence[str],
        candidate_pool: Sequence[str],
        successors: Mapping[str, float],
        used_labels: set[str],
    ) -> FillCandidate | None:
        pool = _unique([*candidate_pool, *successors.keys()])
        if not pool:
            return None
        focus_set = set(focus_tokens)
        relation_set = set(column.relation_signature_tokens)
        best: FillCandidate | None = None
        for label in pool:
            if label in used_labels and len(pool) > len(used_labels):
                continue
            focus_score = 1.0 if label in focus_set else 0.0
            relation_score = 1.0 if label in relation_set else 0.0
            successor_score = max(0.0, min(1.0, float(successors.get(label, 0.0))))
            if focus_score > 0.0:
                relation_score = 0.0
                successor_score = 0.0
            score = (
                self.config.slot_fill_focus_weight * focus_score
                + self.config.slot_fill_relation_weight * relation_score
                + self.config.slot_fill_successor_weight * successor_score
            )
            if score <= self.config.slot_fill_min_score:
                continue
            candidate = FillCandidate(
                label=label,
                score=round(score, 6),
                source=_source_name(focus_score, relation_score, successor_score),
            )
            if best is None or candidate.score > best.score or (
                candidate.score == best.score and _pool_order(candidate.label, pool) < _pool_order(best.label, pool)
            ):
                best = candidate
        return best


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)


def _source_name(focus_score: float, relation_score: float, successor_score: float) -> str:
    parts = []
    if focus_score > 0:
        parts.append("focus")
    if relation_score > 0:
        parts.append("relation")
    if successor_score > 0:
        parts.append("successor_virtual")
    return "+".join(parts) if parts else "candidate_pool"


def _pool_order(label: str, pool: Sequence[str]) -> int:
    try:
        return list(pool).index(label)
    except ValueError:
        return len(pool)
