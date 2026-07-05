from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Iterable, Mapping

from apv3test.config.energy_config import APV3EnergyConfig


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = exp(-value)
        return 1.0 / (1.0 + z)
    z = exp(value)
    return z / (1.0 + z)


@dataclass(frozen=True)
class APV3EnergyItem:
    sa_label: str
    real_energy: float = 0.0
    virtual_energy: float = 0.0
    attention_gain: float = 0.0
    fatigue: float = 0.0
    innate_weight: float = 1.0
    epistemic_debt: float = 0.0
    expected_information_gain: float = 0.0

    @property
    def cognitive_pressure(self) -> float:
        return float(self.real_energy) - float(self.virtual_energy)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "APV3EnergyItem":
        return cls(
            sa_label=str(payload.get("sa_label", "") or ""),
            real_energy=_as_float(payload.get("real_energy")),
            virtual_energy=_as_float(payload.get("virtual_energy")),
            attention_gain=_as_float(payload.get("attention_gain")),
            fatigue=_as_float(payload.get("fatigue")),
            innate_weight=_as_float(payload.get("innate_weight"), 1.0),
            epistemic_debt=_as_float(payload.get("epistemic_debt")),
            expected_information_gain=_as_float(payload.get("expected_information_gain")),
        )


@dataclass(frozen=True)
class APV3EnergyObservation:
    item_count: int
    pressure_loss: float
    epistemic_debt: float
    expected_information_gain: float
    state_debt: float
    action_free_energy: float
    top_pressures: list[dict]


class APV3EnergyObserver:
    """Read-only APV3.0 energy observer.

    The design text uses L-prime in two nearby senses: a state monitor that
    should make unresolved debt costly, and an action objective that should
    reward expected information gain. Keeping both quantities explicit prevents
    an EV sign mistake from turning silence into the mathematical optimum.
    """

    def __init__(self, config: APV3EnergyConfig | None = None) -> None:
        self.config = config or APV3EnergyConfig()

    def pressure_loss(self, pressure: float) -> float:
        p = float(pressure)
        if p >= 0.0:
            return 0.5 * p * p
        return 0.5 * self.config.overprediction_kappa * p * p

    def observe(self, items: Iterable[APV3EnergyItem | Mapping[str, object]]) -> APV3EnergyObservation:
        parsed: list[APV3EnergyItem] = [
            item if isinstance(item, APV3EnergyItem) else APV3EnergyItem.from_mapping(item)
            for item in items
        ]
        pressure_terms: list[tuple[str, float, float]] = []
        pressure_loss = 0.0
        epistemic_debt = 0.0
        expected_information_gain = 0.0
        for item in parsed:
            p = item.cognitive_pressure
            loss = max(0.0, item.innate_weight) * self.pressure_loss(p)
            pressure_loss += loss
            epistemic_debt += max(0.0, float(item.epistemic_debt))
            expected_information_gain += max(0.0, float(item.expected_information_gain))
            pressure_terms.append((item.sa_label, p, loss))

        beta = max(0.0, float(self.config.epistemic_beta))
        state_debt = pressure_loss + beta * epistemic_debt
        action_free_energy = pressure_loss - beta * expected_information_gain
        top = sorted(pressure_terms, key=lambda row: abs(row[1]), reverse=True)[:8]
        return APV3EnergyObservation(
            item_count=len(parsed),
            pressure_loss=round(pressure_loss, 6),
            epistemic_debt=round(epistemic_debt, 6),
            expected_information_gain=round(expected_information_gain, 6),
            state_debt=round(state_debt, 6),
            action_free_energy=round(action_free_energy, 6),
            top_pressures=[
                {"sa_label": label, "pressure": round(pressure, 6), "loss": round(loss, 6)}
                for label, pressure, loss in top
            ],
        )

    def lambda_fast(self, *, grasp: float, habit: float, demand_slow: float) -> float:
        cfg = self.config
        logit = (
            cfg.lambda_fast_grasp_weight * float(grasp)
            + cfg.lambda_fast_habit_weight * float(habit)
            - cfg.lambda_fast_slow_demand_weight * float(demand_slow)
            - cfg.lambda_fast_bias
        )
        return round(_sigmoid(logit), 6)

    def tau_focus(self, *, candidate_entropy: float, surprise_pressure: float, dissonance: float = 0.0) -> float:
        cfg = self.config
        exponent = (
            cfg.tau_candidate_entropy_weight * max(0.0, float(candidate_entropy))
            - cfg.tau_surprise_weight * max(0.0, float(surprise_pressure))
            + cfg.tau_dissonance_weight * max(0.0, float(dissonance))
        )
        return round(max(1e-6, cfg.tau_focus_base * exp(exponent)), 6)

