from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Iterable

from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass(frozen=True)
class EndogenousStepTrace:
    tick: int
    injected_by_sa: dict[str, dict[str, float]]


def step_endogenous_drive(
    items: Iterable[StateItem],
    *,
    tick: int,
    idle_score: float,
) -> EndogenousStepTrace:
    """@op_count: O(active_sa)."""
    injected: dict[str, dict[str, float]] = {}
    idle_boost = 1.0 + _sigmoid_soft(float(idle_score)) * float(load_constant("endogenous.idle_boost_max"))
    for item in items:
        unfinished = _positive_metadata(item, "unfinished_pressure", item.cognitive_pressure)
        expectation = _positive_metadata(item, "expectation_pressure", item.virtual_energy)
        residual = _positive_metadata(item, "residual_mass", item.attention_energy)
        d_unfinished = float(load_constant("endogenous.delta_unfinished")) * unfinished
        d_expectation = float(load_constant("endogenous.delta_expectation")) * expectation
        d_residual = float(load_constant("endogenous.delta_residual")) * residual * idle_boost
        item.gain_ledger.inject("unfinished_pressure", d_unfinished)
        item.gain_ledger.inject("expectation_pressure", d_expectation)
        item.gain_ledger.inject("residual_mass", d_residual)
        item.attention_energy = item.attention_energy + d_unfinished + d_expectation + d_residual
        item.last_tick = int(tick)
        injected[item.sa_id] = {
            "unfinished_pressure": d_unfinished,
            "expectation_pressure": d_expectation,
            "residual_mass": d_residual,
        }
    return EndogenousStepTrace(tick=int(tick), injected_by_sa=injected)


def update_prediction_pi(
    item: StateItem,
    *,
    observed_next_r: float = 0.0,
    currently_occurring: bool,
) -> float:
    """@op_count: O(1)."""
    current = float(item.metadata.get("Pi", 0.0))
    if currently_occurring:
        residual = float(observed_next_r) - current
        eta = min(
            float(load_constant("energy.eta_pi_max")),
            float(load_constant("energy.eta_pi_kappa")) * abs(residual),
        )
        updated = current + eta * residual
    else:
        updated = current * float(load_constant("energy.Pi_decay_when_absent"))
    item.metadata["Pi"] = updated
    return updated


def habituate_item(item: StateItem) -> float:
    """@op_count: O(1)."""
    growth = item.real_energy * (1.0 - float(load_constant("energy.F_decay")))
    item.fatigue = min(1.0, item.fatigue + max(0.0, growth))
    return item.fatigue


def compute_sleep_dilation_factor(items: Iterable[StateItem]) -> float:
    """@op_count: O(active_sa)."""
    item_tuple = tuple(items)
    if not item_tuple:
        return 1.0
    mean_fatigue = sum(item.fatigue for item in item_tuple) / len(item_tuple)
    signal = _sigmoid_sleep(mean_fatigue)
    return 1.0 + signal * float(load_constant("sleep.tick_dilation_max"))


def _positive_metadata(item: StateItem, key: str, fallback: float) -> float:
    return max(0.0, float(item.metadata.get(key, fallback)))


def _sigmoid_soft(value: float) -> float:
    k = float(load_constant("endogenous.idle_score_softness_k"))
    midpoint = float(load_constant("endogenous.idle_score_midpoint"))
    return 1.0 / (1.0 + exp(-((float(value) - midpoint) / max(k, 1.0))))


def _sigmoid_sleep(value: float) -> float:
    slope = float(load_constant("sleep.fatigue_sigmoid_slope"))
    midpoint = float(load_constant("sleep.fatigue_midpoint"))
    return 1.0 / (1.0 + exp(-((float(value) - midpoint) * slope)))
