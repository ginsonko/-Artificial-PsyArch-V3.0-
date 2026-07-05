from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from runtime.cognitive.state_pool.state_pool import load_constant


@dataclass(frozen=True)
class ExpressionCandidate:
    candidate_id: str
    tokens: tuple[str, ...]
    audit_style_tag: str = "quiet_girl"


@dataclass(frozen=True)
class ExpressionCorpusTrace:
    candidate_count: int
    long_reply_ratio: float
    accepted: bool
    rejected_ids: tuple[str, ...]


def validate_quiet_expression_corpus(candidates: Sequence[ExpressionCandidate]) -> ExpressionCorpusTrace:
    """@op_count: O(candidates)."""
    max_tokens = int(load_constant("curriculum.expression.max_tokens_per_candidate"))
    min_count = int(load_constant("curriculum.expression.candidate_count_min"))
    rejected = tuple(candidate.candidate_id for candidate in candidates if len(candidate.tokens) > max_tokens)
    long_count = sum(1 for candidate in candidates if len(candidate.tokens) > max_tokens)
    ratio = 0.0 if not candidates else float(long_count) / float(len(candidates))
    ratio_max = float(load_constant("curriculum.expression.long_reply_ratio_max"))
    return ExpressionCorpusTrace(
        candidate_count=len(candidates),
        long_reply_ratio=ratio,
        accepted=len(candidates) >= min_count and ratio <= ratio_max and not rejected,
        rejected_ids=rejected,
    )


def expression_texts(candidates: Sequence[ExpressionCandidate]) -> tuple[str, ...]:
    """@op_count: O(candidates * tokens)."""
    return tuple("".join(candidate.tokens) for candidate in candidates)

