from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from apv3test.config.introspection_config import APV3CooccurrenceConfig
from apv3test.runtime.cooccurrence_store import CooccurrenceAssociationStore
from apv3test.runtime.expression_phrase_memory import ExpressionPhraseMemory


@dataclass(frozen=True)
class ExternalExpressionToken:
    token: str
    origin: str
    attention_weight: float = 1.0
    segment_id: str = ""
    paradigm_id: str = ""


def observe_feeling_expression_cooccurrence(
    store: CooccurrenceAssociationStore,
    feeling_labels: Sequence[str],
    external_tokens: Sequence[ExternalExpressionToken],
    *,
    current_tick: int,
    config: APV3CooccurrenceConfig | None = None,
) -> None:
    cfg = config or store.config
    for label in feeling_labels:
        for token in external_tokens:
            gamma = _origin_gamma(token.origin, cfg)
            if gamma <= 0.0:
                continue
            attention = max(0.0, min(1.0, float(token.attention_weight)))
            weight = min(cfg.cooccurrence_max_weight, cfg.cooccurrence_lr * gamma * attention)
            if weight <= 0.0:
                continue
            store.observe(
                str(label),
                str(token.token),
                weight=weight,
                current_tick=current_tick,
                paradigm_id=token.paradigm_id or None,
            )


def observe_existing_phrase_cooccurrence(
    store: CooccurrenceAssociationStore,
    phrase_memory: ExpressionPhraseMemory,
    feeling_labels: Sequence[str],
    expression_tokens: Sequence[str],
    *,
    origin: str,
    attention_weight: float,
    current_tick: int,
    config: APV3CooccurrenceConfig | None = None,
) -> str:
    """Teach only when an external expression matches a known phrase sequence."""

    phrase_id = phrase_memory.phrase_id_for_tokens(expression_tokens)
    if not phrase_id:
        return ""
    tokens = tuple(
        ExternalExpressionToken(
            str(token),
            origin,
            attention_weight=float(attention_weight),
            segment_id=phrase_id,
            paradigm_id=phrase_id,
        )
        for token in expression_tokens
    )
    observe_feeling_expression_cooccurrence(
        store,
        feeling_labels,
        tokens,
        current_tick=current_tick,
        config=config,
    )
    phrase_memory.observe(
        phrase_id,
        expression_tokens,
        weight=max(0.0, min(1.0, float(attention_weight))),
        current_tick=current_tick,
    )
    return phrase_id


def _origin_gamma(origin: str, config: APV3CooccurrenceConfig) -> float:
    if origin == "perception_other":
        return float(config.gamma_perception_other)
    if origin == "teacher_reply":
        return float(config.gamma_teacher_reply)
    if origin == "self_emission":
        return float(config.gamma_self_emission)
    return 0.0
