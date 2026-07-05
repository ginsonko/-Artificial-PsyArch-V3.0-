from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Any, Mapping, Sequence

from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig
from apv3test.runtime.alignment import AlignmentColumn
from apv3test.runtime.paradigm_discovery import DiscoveredParadigm
from apv3test.runtime.incremental_paradigm import promoted_context_similarity


@dataclass(frozen=True)
class BnParadigmCandidate:
    pid: str
    bucket: str
    cue_tokens: tuple[str, ...]
    bn_score: float
    cue_score: float
    context_score: float
    support_score: float
    conf: float
    energy_attention: float
    paradigm: DiscoveredParadigm | None


@dataclass(frozen=True)
class CnSuccessorCandidate:
    pid: str
    bucket: str
    successor_tokens: tuple[str, ...]
    cn_score: float
    observation_score: float
    transition_score: float
    source: str


@dataclass(frozen=True)
class AttentionFocusCandidate:
    pid: str
    bucket: str
    focus_score: float
    bn: BnParadigmCandidate
    cn: CnSuccessorCandidate | None
    evidence_tags: tuple[str, ...]


@dataclass(frozen=True)
class ParadigmRecallResult:
    bn_candidates: tuple[BnParadigmCandidate, ...]
    cn_candidates: tuple[CnSuccessorCandidate, ...]
    focus: AttentionFocusCandidate | None


class ParadigmRecallAttention:
    """Read Bn/Cn candidates and choose an attention focus over ParadigmSA."""

    def __init__(self, config: APV3ParadigmDiscoveryConfig | None = None) -> None:
        self.config = config or APV3ParadigmDiscoveryConfig()

    def recall(
        self,
        state: Mapping[str, Any],
        *,
        cue_tokens: Sequence[str],
        context_tokens: Sequence[str] = (),
    ) -> ParadigmRecallResult:
        bn = self.bn_candidates(state, cue_tokens=cue_tokens, context_tokens=context_tokens)
        cn = tuple(self.cn_candidate(state, item, cue_tokens=cue_tokens) for item in bn)
        cn = tuple(item for item in cn if item is not None)
        focus = self.attention_focus(bn, cn)
        return ParadigmRecallResult(bn, cn, focus)

    def bn_candidates(
        self,
        state: Mapping[str, Any],
        *,
        cue_tokens: Sequence[str],
        context_tokens: Sequence[str] = (),
    ) -> tuple[BnParadigmCandidate, ...]:
        rows = state.get("paradigms", [])
        if not isinstance(rows, list):
            return ()
        result: list[BnParadigmCandidate] = []
        for row in rows:
            if not isinstance(row, dict) or str(row.get("entry_kind", "")) != "ParadigmSA":
                continue
            if not bool(row.get("exposed", True)):
                continue
            bucket = _bucket_from_paradigm(row)
            if not bucket:
                continue
            bucket_cue = _cue_from_bucket(bucket)
            cue_score = _sequence_similarity(tuple(cue_tokens), bucket_cue)
            if cue_score <= 0.0:
                continue
            context_score = _context_score(state, bucket, tuple(context_tokens))
            support_score = _support_score(row.get("support"))
            conf = _bounded(row.get("conf"))
            energy_attention = _energy_attention(row.get("energy"))
            score = (
                self.config.bn_recall_cue_weight * cue_score
                + self.config.bn_recall_context_weight * context_score
                + self.config.bn_recall_conf_weight * conf
                + self.config.bn_recall_support_weight * support_score
                + self.config.attention_energy_weight * energy_attention
            )
            if score <= 0.0:
                continue
            result.append(
                BnParadigmCandidate(
                    pid=str(row.get("pid", "")),
                    bucket=bucket,
                    cue_tokens=bucket_cue,
                    bn_score=round(score, 6),
                    cue_score=round(cue_score, 6),
                    context_score=round(context_score, 6),
                    support_score=round(support_score, 6),
                    conf=round(conf, 6),
                    energy_attention=round(energy_attention, 6),
                    paradigm=_paradigm_from_state(state, row, bucket),
                )
            )
        return tuple(sorted(result, key=lambda item: (-item.bn_score, item.pid)))

    def cn_candidate(
        self,
        state: Mapping[str, Any],
        bn: BnParadigmCandidate,
        *,
        cue_tokens: Sequence[str],
    ) -> CnSuccessorCandidate | None:
        observed_tokens, observed_score = _observed_successor(state, bn.bucket)
        transition_tokens, transition_score = _transition_successor(state, cue_tokens)
        if observed_score <= 0.0 and transition_score <= 0.0:
            return None
        if observed_score >= transition_score:
            tokens = observed_tokens
            source = "paradigm_observation"
        else:
            tokens = transition_tokens
            source = "explicit_transition"
        score = (
            self.config.cn_successor_observation_weight * observed_score
            + self.config.cn_successor_transition_weight * transition_score
        )
        return CnSuccessorCandidate(
            pid=bn.pid,
            bucket=bn.bucket,
            successor_tokens=tokens,
            cn_score=round(score, 6),
            observation_score=round(observed_score, 6),
            transition_score=round(transition_score, 6),
            source=source,
        )

    def attention_focus(
        self,
        bn_candidates: Sequence[BnParadigmCandidate],
        cn_candidates: Sequence[CnSuccessorCandidate],
    ) -> AttentionFocusCandidate | None:
        by_pid = {item.pid: item for item in cn_candidates}
        best: AttentionFocusCandidate | None = None
        for bn in bn_candidates:
            cn = by_pid.get(bn.pid)
            cn_score = cn.cn_score if cn is not None else 0.0
            score = (
                self.config.attention_bn_weight * bn.bn_score
                + self.config.attention_cn_weight * cn_score
                + self.config.attention_energy_weight * bn.energy_attention
            )
            candidate = AttentionFocusCandidate(
                pid=bn.pid,
                bucket=bn.bucket,
                focus_score=round(score, 6),
                bn=bn,
                cn=cn,
                evidence_tags=("bn_recall", "cn_successor" if cn is not None else "no_cn"),
            )
            if best is None or candidate.focus_score > best.focus_score or (
                candidate.focus_score == best.focus_score and candidate.pid < best.pid
            ):
                best = candidate
        return best


def _paradigm_from_state(
    state: Mapping[str, Any],
    row: Mapping[str, Any],
    bucket: str,
) -> DiscoveredParadigm | None:
    stats = state.get("paradigm_stats", {})
    payload = stats.get(bucket, {}) if isinstance(stats, dict) else {}
    if not isinstance(payload, dict):
        return None
    columns_payload = payload.get("columns", [])
    if not isinstance(columns_payload, list) or not columns_payload:
        return None
    columns = tuple(_column_from_payload(item) for item in columns_payload if isinstance(item, dict))
    reply = _token_level_successor_from_columns(columns)
    return DiscoveredParadigm(
        case_name=str(payload.get("case_name", "")),
        cue_text="".join(_cue_from_bucket(bucket)),
        fixed_prefix=reply,
        shared_suffix=(),
        slot_spans=(),
        support=int(float(payload.get("support", row.get("support", 0.0)))),
        conf=float(payload.get("conf", row.get("conf", 0.0))),
        columns=columns,
    )


def _column_from_payload(item: Mapping[str, Any]) -> AlignmentColumn:
    return AlignmentColumn(
        col_index=int(float(item.get("col_index", 0))),
        values=tuple(str(value) if value is not None else None for value in _list(item.get("values"))),
        occupancy=float(item.get("occupancy", 0.0)),
        distinct_tokens=tuple(str(value) for value in _list(item.get("distinct_tokens"))),
        role=str(item.get("role", "slot")),
        anchor_label=str(item.get("anchor_label")) if item.get("anchor_label") is not None else None,
        relation_coherence=float(item.get("relation_coherence", 0.0)),
        relation_pair_count=int(float(item.get("relation_pair_count", 0))),
        relation_signature_tokens=tuple(str(value) for value in _list(item.get("relation_signature_tokens"))),
    )


def _observed_successor(state: Mapping[str, Any], bucket: str) -> tuple[tuple[str, ...], float]:
    stats = state.get("paradigm_stats", {})
    payload = stats.get(bucket, {}) if isinstance(stats, dict) else {}
    columns_payload = payload.get("columns", []) if isinstance(payload, dict) else []
    if isinstance(columns_payload, list) and columns_payload:
        columns = tuple(_column_from_payload(item) for item in columns_payload if isinstance(item, dict))
        tokens = _token_level_successor_from_columns(columns)
        if tokens:
            support = _as_float(payload.get("support"))
            return tokens, 1.0 - exp(-support / 3.0)
    return (), 0.0


def _token_level_successor_from_columns(columns: Sequence[AlignmentColumn]) -> tuple[str, ...]:
    tokens: list[str] = []
    for column in columns:
        if column.role in {"fixed_anchor", "shared_fragment"} and column.anchor_label:
            tokens.append(column.anchor_label)
    return tuple(tokens)


def _transition_successor(state: Mapping[str, Any], cue_tokens: Sequence[str]) -> tuple[tuple[str, ...], float]:
    transitions = state.get("transitions", [])
    if not isinstance(transitions, list):
        return (), 0.0
    cue_text = "".join(str(token) for token in cue_tokens)
    best_tokens: tuple[str, ...] = ()
    best_support = 0.0
    for item in transitions:
        if not isinstance(item, dict) or str(item.get("source", "")) != cue_text:
            continue
        support = _as_float(item.get("support"))
        if support > best_support:
            best_support = support
            best_tokens = (str(item.get("target", "")),)
    if not best_tokens:
        return (), 0.0
    return best_tokens, 1.0 - exp(-best_support / 3.0)


def _context_score(state: Mapping[str, Any], bucket: str, context_tokens: tuple[str, ...]) -> float:
    rows = state.get("paradigm_observations", [])
    if not isinstance(rows, list):
        return 0.0
    best = 0.0
    for row in rows:
        if not isinstance(row, dict) or str(row.get("bucket", "")) != bucket:
            continue
        learned_context = tuple(str(value) for value in _list(row.get("context_tokens")))
        best = max(best, promoted_context_similarity(state, learned_context, context_tokens))
    return best


def _sequence_similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    if left == right:
        return 1.0
    if not left or not right:
        return 0.0
    left_set = set(left)
    right_set = set(right)
    overlap = len(left_set & right_set) / max(1, len(left_set | right_set))
    aligned = sum(1 for a, b in zip(left, right) if a == b) / max(len(left), len(right))
    return max(0.0, min(1.0, (overlap + aligned) / 2.0))


def _bucket_from_paradigm(row: Mapping[str, Any]) -> str:
    anchor = row.get("anchor_meta", {})
    if not isinstance(anchor, dict):
        return ""
    return str(anchor.get("bucket", ""))


def _cue_from_bucket(bucket: str) -> tuple[str, ...]:
    if "|" not in bucket:
        return ()
    cue = bucket.split("|", 1)[1].strip()
    return tuple(token for token in cue.split(" ") if token)


def _support_score(value: object) -> float:
    return 1.0 - exp(-max(0.0, _as_float(value)) / 3.0)


def _energy_attention(value: object) -> float:
    if not isinstance(value, dict):
        return 0.0
    return max(0.0, min(1.0, (_as_float(value.get("A")) + _as_float(value.get("R"))) / 2.0))


def _bounded(value: object) -> float:
    return max(0.0, min(1.0, _as_float(value)))


def _list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
