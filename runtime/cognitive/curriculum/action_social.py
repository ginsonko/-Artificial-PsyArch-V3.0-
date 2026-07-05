from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from runtime.cognitive.sdpl.packet import LearningPacket
from runtime.cognitive.sdpl.q_table_backoff import QTableWithBackoff


@dataclass(frozen=True)
class ActionPrototype:
    action_id: str
    capability_tag: str


@dataclass(frozen=True)
class ActionSelectionTrace:
    action_id: str
    score: float
    candidate_count: int


@dataclass(frozen=True)
class SocialPatternTrace:
    pattern_id: str
    source_count: int
    accepted: bool


def select_action_prototype(
    packet: LearningPacket,
    q_table: QTableWithBackoff,
    candidates: Sequence[ActionPrototype],
) -> ActionSelectionTrace:
    """@op_count: O(candidates)."""
    scored = tuple((q_table.query(packet, candidate.action_id), candidate.action_id) for candidate in candidates)
    if not scored:
        return ActionSelectionTrace(action_id="", score=0.0, candidate_count=0)
    score, action_id = max(scored, key=lambda item: (item[0], item[1]))
    return ActionSelectionTrace(action_id=action_id, score=score, candidate_count=len(candidates))


def validate_social_pattern(pattern_id: str, source_examples: Sequence[str]) -> SocialPatternTrace:
    """@op_count: O(source_examples)."""
    unique = {str(item) for item in source_examples if str(item)}
    return SocialPatternTrace(pattern_id=pattern_id, source_count=len(unique), accepted=len(unique) >= 2)

