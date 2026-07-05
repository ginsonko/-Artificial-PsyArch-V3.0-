from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Iterable, Mapping

from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig
from apv3test.runtime.alignment import AlignmentColumn, AnchorRelativeAligner
from apv3test.runtime.learning_writer import (
    LearnedBnCandidate,
    LearnedParadigm,
    LearnedToken,
    LearnedTransition,
    LearningEpisode,
)


@dataclass(frozen=True)
class ParadigmObservation:
    case_name: str
    cue_tokens: tuple[str, ...]
    reply_tokens: tuple[str, ...]


@dataclass(frozen=True)
class DiscoveredParadigm:
    case_name: str
    cue_text: str
    fixed_prefix: tuple[str, ...]
    shared_suffix: tuple[str, ...]
    slot_spans: tuple[tuple[str, ...], ...]
    support: int
    conf: float
    columns: tuple[AlignmentColumn, ...] = ()

    @property
    def pid(self) -> str:
        return f"p:discovered:{self.case_name}"

    @property
    def candidate_id(self) -> str:
        return f"memory:discovered:{self.case_name}"

    @property
    def canonical_reply(self) -> str:
        if self.slot_spans:
            filler = self.slot_spans[0]
            return "".join((*self.fixed_prefix, *filler, *self.shared_suffix))
        return "".join((*self.fixed_prefix, *self.shared_suffix))


class ParadigmDiscoveryEngine:
    """Minimal self-discovery preflight for APV3.0 paradigms.

    The engine consumes observation sequences and emits AP-native learning
    evidence. It does not inspect specific words, dispatch by labels, or call a
    solver. Full v2.1 anchor-relative DP remains a later, larger milestone.
    """

    def __init__(
        self,
        config: APV3ParadigmDiscoveryConfig | None = None,
        transition_bias: Mapping[tuple[str, str], float] | None = None,
    ) -> None:
        self.config = config or APV3ParadigmDiscoveryConfig()
        self.aligner = AnchorRelativeAligner(self.config, transition_bias=transition_bias)

    def discover(self, observations: Iterable[ParadigmObservation]) -> list[DiscoveredParadigm]:
        grouped: dict[tuple[str, tuple[str, ...]], list[ParadigmObservation]] = {}
        for obs in observations:
            grouped.setdefault((obs.case_name, obs.cue_tokens), []).append(obs)
        discovered = []
        for (case_name, cue_tokens), group in sorted(grouped.items(), key=lambda item: item[0]):
            if len(group) < self.config.min_support:
                continue
            replies = [obs.reply_tokens for obs in group]
            alignment = self.aligner.align(replies)
            prefix = _fixed_prefix_from_columns(alignment.columns)
            suffix = _shared_suffix_from_columns(alignment.columns, prefix_len=len(prefix))
            slot_spans = _slot_spans_from_columns(alignment.columns, len(prefix), len(suffix))
            has_slot = any(slot_spans)
            conf = self._confidence(len(group), columns=alignment.columns, has_slot=has_slot)
            discovered.append(
                DiscoveredParadigm(
                    case_name=case_name,
                    cue_text="".join(cue_tokens),
                    fixed_prefix=prefix,
                    shared_suffix=suffix,
                    slot_spans=slot_spans if has_slot else (),
                    support=len(group),
                    conf=conf,
                    columns=alignment.columns,
                )
            )
        return discovered

    def to_learning_episode(self, episode_id: str, paradigms: Iterable[DiscoveredParadigm]) -> LearningEpisode:
        tokens: list[LearnedToken] = []
        transitions: list[LearnedTransition] = []
        learned_paradigms: list[LearnedParadigm] = []
        candidates: list[LearnedBnCandidate] = []
        for item in paradigms:
            cue_vector = _stable_vector(item.cue_text)
            reply_text = item.canonical_reply
            tokens.append(LearnedToken(item.cue_text, cue_vector, float(item.support)))
            tokens.append(LearnedToken(reply_text, _stable_vector(reply_text), max(1.0, float(item.support) - 0.5)))
            transitions.append(LearnedTransition(item.cue_text, reply_text, float(item.support)))
            column_roles = _unique_preserve_order(column.role for column in item.columns)
            slot_types = ("cue", *column_roles) if column_roles else ("cue", "reply")
            learned_paradigms.append(
                LearnedParadigm(
                    item.pid,
                    support_delta=float(item.support),
                    conf=item.conf,
                    slot_types=slot_types,
                    probe_tags=(item.case_name,),
                )
            )
            candidates.append(
                LearnedBnCandidate(
                    item.candidate_id,
                    "discovered_paradigm",
                    {item.case_name: _candidate_features(item.conf)},
                )
            )
        return LearningEpisode(
            episode_id=episode_id,
            tokens=tuple(tokens),
            transitions=tuple(transitions),
            paradigms=tuple(learned_paradigms),
            bn_candidates=tuple(candidates),
        )

    def _confidence(self, support: int, *, columns: tuple[AlignmentColumn, ...], has_slot: bool) -> float:
        evidence = 1.0 - exp(-max(0.0, float(support)) / max(1e-6, self.config.support_half_life))
        anchor_quality = _anchor_quality(columns, default=self.config.anchor_quality_default)
        slot_quality = _slot_quality(columns, default=self.config.slot_quality_default) if has_slot else 1.0
        conf = (
            evidence ** self.config.confidence_evidence_gamma
            * anchor_quality ** self.config.confidence_anchor_gamma
            * slot_quality ** self.config.confidence_slot_gamma
        )
        return round(conf, 6)


def _fixed_prefix_from_columns(columns: tuple[AlignmentColumn, ...]) -> tuple[str, ...]:
    result: list[str] = []
    for column in columns:
        if column.role != "fixed_anchor" or column.anchor_label is None:
            break
        result.append(column.anchor_label)
    return tuple(result)


def _shared_suffix_from_columns(columns: tuple[AlignmentColumn, ...], *, prefix_len: int) -> tuple[str, ...]:
    result: list[str] = []
    stop_at = max(0, prefix_len - 1)
    for index in range(len(columns) - 1, stop_at, -1):
        column = columns[index]
        if column.role not in {"fixed_anchor", "shared_fragment"} or column.anchor_label is None:
            break
        result.append(column.anchor_label)
    return tuple(reversed(result))


def _slot_spans_from_columns(
    columns: tuple[AlignmentColumn, ...],
    prefix_len: int,
    suffix_len: int,
) -> tuple[tuple[str, ...], ...]:
    if not columns:
        return ()
    end = len(columns) - suffix_len if suffix_len else len(columns)
    span_columns = columns[prefix_len:end]
    if not span_columns:
        return tuple(() for _ in columns[0].values)
    spans: list[list[str]] = [[] for _ in columns[0].values]
    for column in span_columns:
        for seq_index, value in enumerate(column.values):
            if value is not None:
                spans[seq_index].append(value)
    return tuple(tuple(span) for span in spans)


def _unique_preserve_order(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)


def _anchor_quality(columns: tuple[AlignmentColumn, ...], *, default: float) -> float:
    anchor_columns = [
        column
        for column in columns
        if column.role in {"fixed_anchor", "shared_fragment"} and column.anchor_label is not None
    ]
    if not anchor_columns:
        return default
    return sum(column.occupancy for column in anchor_columns) / len(anchor_columns)


def _slot_quality(columns: tuple[AlignmentColumn, ...], *, default: float) -> float:
    slot_columns = [column for column in columns if column.role == "slot" and column.relation_pair_count > 0]
    if not slot_columns:
        return default
    return sum(column.relation_coherence for column in slot_columns) / len(slot_columns)


def _candidate_features(conf: float) -> dict[str, float]:
    c = max(0.0, min(1.0, float(conf)))
    return {
        "label": c,
        "display": c * 0.7,
        "bigram": c * 0.6,
        "focus": c,
        "state_match": c,
        "energy": c * 0.8,
        "sequence": c * 0.9,
        "posting": c * 0.4,
        "vector": c * 0.8,
        "learned_similarity": c * 0.85,
    }


def _stable_vector(text: str) -> tuple[float, float, float]:
    total = sum(ord(ch) for ch in text)
    length = max(1, len(text))
    return (
        round((total % 97) / 97.0, 6),
        round((length % 17) / 17.0, 6),
        round(((total // length) % 89) / 89.0, 6),
    )
