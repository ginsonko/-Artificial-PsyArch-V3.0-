from __future__ import annotations

from dataclasses import dataclass
from math import exp, tanh
from typing import Any, Mapping, Sequence

from apv3test.config.energy_config import APV3EnergyConfig
from apv3test.config.habit_config import APV3HabitConfig
from apv3test.runtime.energy_observer import APV3EnergyObserver


@dataclass(frozen=True)
class HabitCandidate:
    action_id: str
    actuator_id: str
    outcome_kind: str
    context_match: float
    support_strength: float
    reward_strength: float
    punish_strength: float
    recency_gain: float
    habit_strength: float
    lambda_fast: float
    drive: float
    slow_review_pressure: float
    evidence_tags: tuple[str, ...]


class FastHabitSystem:
    """Read fast-system habit candidates from action outcome memory.

    The system only proposes AP-native action/thought candidates and their
    energy readout. It does not choose text, use surface cue dispatch, or bypass
    actuator competition.
    """

    def __init__(
        self,
        habit_config: APV3HabitConfig | None = None,
        energy_config: APV3EnergyConfig | None = None,
    ) -> None:
        self.config = habit_config or APV3HabitConfig()
        self.energy = APV3EnergyObserver(energy_config)

    def candidates(
        self,
        state: Mapping[str, Any],
        *,
        current_context_tags: Sequence[str] = (),
        grasp: float = 0.0,
        demand_slow: float = 0.0,
        current_tick: int | None = None,
    ) -> tuple[HabitCandidate, ...]:
        outcomes = state.get("action_outcomes", {})
        if not isinstance(outcomes, dict):
            return ()
        rows: list[HabitCandidate] = []
        for action_id, payload in outcomes.items():
            if not isinstance(payload, dict):
                continue
            rows.append(
                self._candidate_from_payload(
                    str(action_id),
                    payload,
                    current_context_tags=tuple(str(tag) for tag in current_context_tags),
                    grasp=float(grasp),
                    demand_slow=float(demand_slow),
                    current_tick=current_tick,
                )
            )
        return tuple(sorted(rows, key=lambda item: (-item.drive, item.action_id)))

    def select_compatible(self, candidates: Sequence[HabitCandidate]) -> tuple[HabitCandidate, ...]:
        """Keep the strongest habit per actuator conflict domain.

        Different actuator ids may co-exist in the same tick. The execution
        surface still decides whether and how to act on the selected candidates.
        """

        winners: dict[str, HabitCandidate] = {}
        for candidate in candidates:
            current = winners.get(candidate.actuator_id)
            if current is None or _candidate_order(candidate) < _candidate_order(current):
                winners[candidate.actuator_id] = candidate
        return tuple(sorted(winners.values(), key=_candidate_order))

    def _candidate_from_payload(
        self,
        action_id: str,
        payload: Mapping[str, Any],
        *,
        current_context_tags: tuple[str, ...],
        grasp: float,
        demand_slow: float,
        current_tick: int | None,
    ) -> HabitCandidate:
        cfg = self.config
        reward_strength = _bounded_evidence(payload.get("reward_support"), cfg.support_half_life)
        punish_strength = _bounded_evidence(payload.get("punish_support"), cfg.support_half_life)
        support_strength = _bounded_evidence(
            payload.get("support", _as_float(payload.get("reward_support")) + _as_float(payload.get("punish_support"))),
            cfg.support_half_life,
        )
        recency_gain = _recency_gain(payload.get("last_tick"), current_tick, cfg)
        context_tags = _string_tuple(payload.get("context_tags"))
        context_match = _context_match(context_tags, current_context_tags)
        context_multiplier = cfg.context_floor + (1.0 - cfg.context_floor) * context_match
        positive = (
            cfg.support_weight * support_strength
            + cfg.reward_weight * reward_strength
            + cfg.drive_bias_weight * tanh(_as_float(payload.get("drive_bias")))
        )
        negative = cfg.punish_weight * punish_strength
        habit_strength = tanh(context_multiplier * ((1.0 + cfg.recency_gain_weight * recency_gain) * positive - negative))
        lambda_fast = self.energy.lambda_fast(grasp=grasp, habit=habit_strength, demand_slow=demand_slow)
        slow_review_pressure = float(demand_slow) - (max(0.0, float(grasp)) + max(0.0, habit_strength)) / 2.0
        drive = cfg.habit_drive_weight * habit_strength + cfg.lambda_fast_drive_weight * lambda_fast
        return HabitCandidate(
            action_id=action_id,
            actuator_id=str(payload.get("actuator_id", "") or action_id),
            outcome_kind=str(payload.get("outcome_kind", "action") or "action"),
            context_match=round(context_match, 6),
            support_strength=round(support_strength, 6),
            reward_strength=round(reward_strength, 6),
            punish_strength=round(punish_strength, 6),
            recency_gain=round(recency_gain, 6),
            habit_strength=round(habit_strength, 6),
            lambda_fast=lambda_fast,
            drive=round(drive, 6),
            slow_review_pressure=round(slow_review_pressure, 6),
            evidence_tags=context_tags,
        )


def _bounded_evidence(value: object, half_life: float) -> float:
    scale = max(1e-6, float(half_life))
    return 1.0 - exp(-max(0.0, _as_float(value)) / scale)


def _recency_gain(last_tick: object, current_tick: int | None, config: APV3HabitConfig) -> float:
    if current_tick is None:
        return max(0.0, float(config.unknown_recency_gain))
    try:
        age = max(0, int(current_tick) - int(last_tick))
    except (TypeError, ValueError):
        return max(0.0, float(config.unknown_recency_gain))
    scale = max(1e-6, float(config.recency_half_life_ticks))
    return exp(-float(age) / scale)


def _context_match(outcome_tags: tuple[str, ...], current_tags: tuple[str, ...]) -> float:
    if not outcome_tags and not current_tags:
        return 1.0
    if not outcome_tags or not current_tags:
        return 0.0
    learned = set(outcome_tags)
    current = set(current_tags)
    return len(learned & current) / max(1, len(learned | current))


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value)


def _candidate_order(candidate: HabitCandidate) -> tuple[float, str]:
    return (-float(candidate.drive), candidate.action_id)


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
