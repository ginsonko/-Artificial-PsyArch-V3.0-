from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from apv3test.runtime.habit_system import HabitCandidate


@dataclass(frozen=True)
class ActionProposal:
    tick: int
    action_id: str
    actuator_id: str
    source_system: str
    outcome_kind: str
    drive: float
    lambda_fast: float = 0.0
    habit_strength: float = 0.0
    slow_review_pressure: float = 0.0
    evidence_tags: tuple[str, ...] = ()
    payload: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_habit_candidate(cls, candidate: HabitCandidate, *, tick: int) -> "ActionProposal":
        return cls(
            tick=int(tick),
            action_id=candidate.action_id,
            actuator_id=candidate.actuator_id,
            source_system="fast_habit",
            outcome_kind=candidate.outcome_kind,
            drive=candidate.drive,
            lambda_fast=candidate.lambda_fast,
            habit_strength=candidate.habit_strength,
            slow_review_pressure=candidate.slow_review_pressure,
            evidence_tags=candidate.evidence_tags,
            payload={
                "context_match": candidate.context_match,
                "support_strength": candidate.support_strength,
                "reward_strength": candidate.reward_strength,
                "punish_strength": candidate.punish_strength,
                "recency_gain": candidate.recency_gain,
            },
        )


@dataclass(frozen=True)
class ActuatorCompetitionDecision:
    actuator_id: str
    selected: ActionProposal
    rejected: tuple[ActionProposal, ...]
    requires_slow_review: bool


@dataclass(frozen=True)
class ActionCompetitionTrace:
    tick: int
    decisions: tuple[ActuatorCompetitionDecision, ...]

    @property
    def selected(self) -> tuple[ActionProposal, ...]:
        return tuple(decision.selected for decision in self.decisions)

    @property
    def rejected(self) -> tuple[ActionProposal, ...]:
        items: list[ActionProposal] = []
        for decision in self.decisions:
            items.extend(decision.rejected)
        return tuple(items)

    def as_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "selected": [_proposal_dict(item) for item in self.selected],
            "rejected": [_proposal_dict(item) for item in self.rejected],
            "decisions": [
                {
                    "actuator_id": decision.actuator_id,
                    "selected": decision.selected.action_id,
                    "rejected": [item.action_id for item in decision.rejected],
                    "requires_slow_review": decision.requires_slow_review,
                }
                for decision in self.decisions
            ],
        }


class ActionCompetition:
    """Conflict-domain competition for AP action/thought proposals.

    This is a pre-execution trace. It does not run actuators, does not write
    learning evidence, and does not choose surface text.
    """

    def from_habit_candidates(
        self,
        candidates: Sequence[HabitCandidate],
        *,
        tick: int,
    ) -> ActionCompetitionTrace:
        proposals = [ActionProposal.from_habit_candidate(candidate, tick=tick) for candidate in candidates]
        return self.compete(proposals, tick=tick)

    def compete(self, proposals: Sequence[ActionProposal], *, tick: int) -> ActionCompetitionTrace:
        groups: dict[str, list[ActionProposal]] = {}
        for proposal in proposals:
            groups.setdefault(proposal.actuator_id, []).append(proposal)
        decisions: list[ActuatorCompetitionDecision] = []
        for actuator_id, group in groups.items():
            ordered = sorted(group, key=_proposal_order)
            selected = ordered[0]
            rejected = tuple(ordered[1:])
            decisions.append(
                ActuatorCompetitionDecision(
                    actuator_id=actuator_id,
                    selected=selected,
                    rejected=rejected,
                    requires_slow_review=selected.slow_review_pressure > 0.0,
                )
            )
        return ActionCompetitionTrace(
            tick=int(tick),
            decisions=tuple(sorted(decisions, key=lambda item: _proposal_order(item.selected))),
        )


def _proposal_order(proposal: ActionProposal) -> tuple[float, str]:
    return (-float(proposal.drive), proposal.action_id)


def _proposal_dict(proposal: ActionProposal) -> dict[str, Any]:
    return {
        "tick": proposal.tick,
        "action_id": proposal.action_id,
        "actuator_id": proposal.actuator_id,
        "source_system": proposal.source_system,
        "outcome_kind": proposal.outcome_kind,
        "drive": proposal.drive,
        "lambda_fast": proposal.lambda_fast,
        "habit_strength": proposal.habit_strength,
        "slow_review_pressure": proposal.slow_review_pressure,
        "evidence_tags": list(proposal.evidence_tags),
        "payload": dict(proposal.payload),
    }
