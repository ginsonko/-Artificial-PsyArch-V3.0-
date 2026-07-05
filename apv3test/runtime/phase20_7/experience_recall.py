from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Any, Callable

from .experience_candidate import compute_unified_experience_support


# A learned L1 text-vector similarity callable (whitepaper §35.3 / §173.3).
# It takes (query_text, memory_text) and returns a cosine similarity in [0, 1].
# When None (the default), no learned signal is added and the recall path is
# bit-identical to its pre-L1 behavior.
L1VectorSimilarityFn = Callable[[str, str], float]


@dataclass(frozen=True)
class ExperienceRecallQuery:
    query_text: str
    text_signature: str | None = None
    visual_signature: str | None = None
    input_signature: str | None = None
    open_reference: bool = False
    exact_input_allowed: bool = True


@dataclass(frozen=True)
class ExperienceRecallCandidate:
    alignment_event_id: str
    payload: dict[str, Any]
    input_event_id: str
    output_text: str
    output_chars: tuple[str, ...]
    source_text: str
    reward: float
    punish: float
    text_score: float
    text_coverage_units: tuple[str, ...]
    visual_score: float
    exact_text_match: float
    exact_input_match: bool
    visual_reference_family: bool
    support: float
    support_terms: tuple[tuple[str, float], ...]
    l1_vector_score: float = 0.0


def query_experience_alignment_candidates(
    conn: sqlite3.Connection,
    query: ExperienceRecallQuery,
    *,
    from_json: Callable[[str], Any],
    is_tombstoned: Callable[..., bool],
    input_payload_for_alignment: Callable[[sqlite3.Connection, dict[str, Any]], dict[str, Any]],
    semantic_text_overlap_with_units: Callable[[str, str], tuple[float, tuple[str, ...]]],
    visual_similarity: Callable[[str | None, str | None], float],
    observation_is_visual_reference_family: Callable[[dict[str, Any]], bool] | None = None,
    l1_vector_similarity: L1VectorSimilarityFn | None = None,
    limit: int = 400,
) -> tuple[ExperienceRecallCandidate, ...]:
    rows = conn.execute(
        """
        SELECT event_id, payload_json, reward, punish
        FROM phase20_7_experience_events
        WHERE event_kind='experience_alignment'
        ORDER BY created_at_ms DESC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    candidates: list[ExperienceRecallCandidate] = []
    for event_id, payload_json, reward, punish in rows:
        event_id = str(event_id)
        if is_tombstoned(conn, object_kind="event", object_ref=event_id):
            continue
        payload = from_json(str(payload_json))
        if not isinstance(payload, dict):
            continue
        # §2363/E4/C21: counter_evidence alignment 是纠错证据(惩罚主导的教师反馈),
        # 不是可复述答案 — 永不作为回复候选进入召回竞争. 它仍留在经验流里,
        # 供反例计数(_alignment_counter_count)与 §2363 反例通道消费.
        if str(payload.get("alignment_role") or "") == "counter_evidence":
            continue
        output_chars = tuple(str(ch) for ch in payload.get("output_chars", ()))
        output_text = "".join(output_chars).strip()
        input_event_id = str(payload.get("input_event_id") or "")
        input_payload = input_payload_for_alignment(conn, payload)
        source_text = str(input_payload.get("text", "") or "")
        text_score, coverage_units = semantic_text_overlap_with_units(query.query_text, output_text)
        if source_text:
            source_score, source_units = semantic_text_overlap_with_units(query.query_text, source_text)
            if source_score > text_score:
                text_score = source_score
                coverage_units = source_units
        candidate_visual = str(payload.get("visual_signature", "") or "") or None
        v_score = visual_similarity(query.visual_signature, candidate_visual)
        exact_text = 1.0 if query.text_signature and payload.get("text_signature") == query.text_signature else 0.0
        exact_input = bool(query.input_signature and payload.get("input_signature") == query.input_signature)
        visual_reference = bool(payload.get("visual_reference_family")) and bool(query.open_reference)
        if observation_is_visual_reference_family is not None:
            visual_reference = visual_reference and observation_is_visual_reference_family(payload)
        reward_value = float(reward or 0.0)
        punish_value = float(punish or 0.0)
        l1_score = 0.0
        if l1_vector_similarity is not None:
            try:
                l1_score = float(l1_vector_similarity(query.query_text, output_text) or 0.0)
            except Exception:
                l1_score = 0.0
        support, support_terms = compute_unified_experience_support(
            structural_similarity=float(text_score),
            visual_similarity=float(v_score),
            exact_text=float(exact_text),
            exact_input=1.0 if exact_input and query.exact_input_allowed else 0.0,
            open_reference=1.0 if visual_reference else 0.0,
            reward=reward_value,
            punish=punish_value,
            l1_vector_similarity=l1_score,
        )
        candidates.append(
            ExperienceRecallCandidate(
                alignment_event_id=event_id,
                payload=payload,
                input_event_id=input_event_id,
                output_text=output_text,
                output_chars=output_chars,
                source_text=source_text,
                reward=reward_value,
                punish=punish_value,
                text_score=float(text_score),
                text_coverage_units=tuple(str(unit) for unit in coverage_units),
                visual_score=float(v_score),
                exact_text_match=float(exact_text),
                exact_input_match=exact_input,
                visual_reference_family=visual_reference,
                support=support,
                support_terms=support_terms,
                l1_vector_score=float(l1_score),
            )
        )
    return tuple(candidates)
