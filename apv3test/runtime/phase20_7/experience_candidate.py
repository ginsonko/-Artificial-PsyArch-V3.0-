from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID = "apv3_phase20_8e_unified_support/v1"


@dataclass(frozen=True)
class UnifiedExperienceCandidate:
    candidate_id: str
    candidate_kind: str
    event_id: str
    tick: int | None
    source_packet_id: str
    source_kind: str
    text: str
    text_signature: str | None
    visual_signature: str | None
    occurrence_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    payload_refs: tuple[str, ...]
    alignment_event_id: str | None
    support: float
    support_terms: tuple[tuple[str, float], ...]
    cause_slots: tuple[dict[str, Any], ...]
    payload: dict[str, Any]
    support_formula: str = UNIFIED_EXPERIENCE_SUPPORT_FORMULA_ID

    def audit_slot(self) -> dict[str, Any]:
        return {
            "slot_kind": "unified_experience_candidate",
            "candidate_id": self.candidate_id,
            "candidate_kind": self.candidate_kind,
            "source_kind": self.source_kind,
            "support": round(float(self.support), 4),
            "support_formula": self.support_formula,
            "support_terms": {key: round(float(value), 4) for key, value in self.support_terms},
            "occurrence_count": len(self.occurrence_ids),
            "edge_count": len(self.edge_ids),
            "payload_ref_count": len(self.payload_refs),
            "alignment_event_id": self.alignment_event_id,
        }


def compute_unified_experience_support(
    *,
    structural_similarity: float = 0.0,
    visual_similarity: float = 0.0,
    exact_text: float = 0.0,
    exact_input: float = 0.0,
    open_reference: float = 0.0,
    occurrence_energy: float = 0.0,
    recency: float = 0.0,
    payload_presence: float = 0.0,
    modality_match: float = 0.0,
    reward: float = 0.0,
    punish: float = 0.0,
    l1_vector_similarity: float = 0.0,
) -> tuple[float, tuple[tuple[str, float], ...]]:
    primary = max(
        _unit(structural_similarity),
        _unit(visual_similarity),
        _unit(exact_text),
        _unit(exact_input),
        _unit(open_reference),
        _unit(occurrence_energy),
        _unit(payload_presence),
        _unit(modality_match),
    )
    allow_context_bias = primary > 0.0
    # L1 online embedding similarity (whitepaper §35.3 / §173.3) is a learned,
    # receptor-local contrast signal stored on the existing vector_l1 column. It
    # only amplifies recall when there is already some primary surface/structure
    # evidence (allow_context_bias), so a pure learned match with zero structural
    # overlap cannot by itself summon an unrelated memory. It never enters the
    # ``primary`` max, so when it is 0.0 every other term and the total support
    # are bit-identical to the pre-L1 formula.
    l1_term = _unit(l1_vector_similarity) * (0.28 if allow_context_bias else 0.0)
    terms = (
        ("structural_similarity", _unit(structural_similarity) * 0.30),
        ("visual_similarity", _unit(visual_similarity) * 0.62),
        ("exact_text", _unit(exact_text) * 0.18),
        ("exact_input", _unit(exact_input) * 0.24),
        ("open_reference", _unit(open_reference) * 0.08),
        ("occurrence_energy", _unit(occurrence_energy) * 0.62),
        ("recency", _unit(recency) * (0.18 if allow_context_bias else 0.0)),
        ("payload_presence", _unit(payload_presence) * 0.08),
        ("modality_match", _unit(modality_match) * 0.10),
        ("reward", max(0.0, float(reward)) * (0.12 if allow_context_bias else 0.0)),
        ("punish", -max(0.0, float(punish)) * (0.12 if allow_context_bias else 0.0)),
        ("l1_vector_similarity", l1_term),
    )
    support = max(0.0, min(1.0, sum(value for _name, value in terms)))
    return support, tuple((name, value) for name, value in terms if abs(value) > 0.0001)


def unified_candidate_from_recall(candidate: Any) -> UnifiedExperienceCandidate:
    payload = dict(getattr(candidate, "payload", {}) or {})
    occurrence_ids = _tuple_str(payload.get("output_occurrence_ids", ()))
    payload_refs = _tuple_str(
        payload.get("payload_refs", ())
        or payload.get("borrowed_patch_payload_refs", ())
        or payload.get("reconstructed_from_payload_refs", ())
    )
    support_terms = _support_terms(candidate)
    return UnifiedExperienceCandidate(
        candidate_id=f"alignment::{getattr(candidate, 'alignment_event_id', '')}",
        candidate_kind="experience_alignment",
        event_id=str(getattr(candidate, "alignment_event_id", "")),
        tick=None,
        source_packet_id="",
        source_kind="alignment_memory",
        text=str(getattr(candidate, "output_text", "") or getattr(candidate, "source_text", "")),
        text_signature=str(payload.get("text_signature") or "") or None,
        visual_signature=str(payload.get("visual_signature") or "") or None,
        occurrence_ids=occurrence_ids,
        edge_ids=(),
        payload_refs=payload_refs,
        alignment_event_id=str(getattr(candidate, "alignment_event_id", "")) or None,
        support=float(getattr(candidate, "support", 0.0) or 0.0),
        support_terms=support_terms,
        cause_slots=(
            {
                "slot_kind": "experience_alignment_candidate",
                "source_kind": "alignment_memory",
                "input_event_id": str(getattr(candidate, "input_event_id", "") or ""),
            },
        ),
        payload=payload,
    )


def unified_candidate_from_flow(candidate: Any) -> UnifiedExperienceCandidate:
    return UnifiedExperienceCandidate(
        candidate_id=str(getattr(candidate, "candidate_id", "")),
        candidate_kind=str(getattr(candidate, "candidate_kind", "")),
        event_id=str(getattr(candidate, "event_id", "")),
        tick=int(getattr(candidate, "tick", 0) or 0),
        source_packet_id=str(getattr(candidate, "source_packet_id", "") or ""),
        source_kind=str(getattr(candidate, "source_kind", "")),
        text=str(getattr(candidate, "text", "") or ""),
        text_signature=getattr(candidate, "text_signature", None),
        visual_signature=getattr(candidate, "visual_signature", None),
        occurrence_ids=_tuple_str(getattr(candidate, "occurrence_ids", ())),
        edge_ids=_tuple_str(getattr(candidate, "edge_ids", ())),
        payload_refs=_tuple_str(getattr(candidate, "payload_refs", ())),
        alignment_event_id=getattr(candidate, "alignment_event_id", None),
        support=float(getattr(candidate, "support", 0.0) or 0.0),
        support_terms=_support_terms(candidate),
        cause_slots=tuple(dict(slot) for slot in getattr(candidate, "cause_slots", ()) if isinstance(slot, Mapping)),
        payload=dict(getattr(candidate, "payload", {}) or {}),
    )


def merge_unified_experience_candidates(*candidate_groups: Iterable[UnifiedExperienceCandidate]) -> tuple[UnifiedExperienceCandidate, ...]:
    merged: dict[str, UnifiedExperienceCandidate] = {}
    for group in candidate_groups:
        for candidate in group:
            previous = merged.get(candidate.candidate_id)
            if previous is None or candidate.support > previous.support:
                merged[candidate.candidate_id] = candidate
    return tuple(sorted(merged.values(), key=lambda item: item.support, reverse=True))


def _support_terms(candidate: Any) -> tuple[tuple[str, float], ...]:
    terms = getattr(candidate, "support_terms", ())
    out: list[tuple[str, float]] = []
    for item in terms or ():
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            continue
        try:
            out.append((str(item[0]), float(item[1])))
        except (TypeError, ValueError):
            continue
    return tuple(out)


def _tuple_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes, bytearray)):
        text = str(value)
        return (text,) if text else ()
    try:
        return tuple(str(item) for item in value if str(item))
    except TypeError:
        text = str(value)
        return (text,) if text else ()


def _unit(value: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
