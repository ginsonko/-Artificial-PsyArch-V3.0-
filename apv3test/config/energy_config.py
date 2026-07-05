from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class APV3EnergyConfig:
    """Named APV3.0 energy parameters.

    These are observation parameters first. They must not affect runtime
    behavior until the observe-only gates pass.
    """

    overprediction_kappa: float = 1.35
    epistemic_beta: float = 0.35
    real_decay: float = 0.92
    base_ratio: float = 0.60
    min_target_cap: float = 0.0
    lambda_fast_bias: float = 0.0
    lambda_fast_grasp_weight: float = 1.0
    lambda_fast_habit_weight: float = 1.0
    lambda_fast_slow_demand_weight: float = 1.0
    tau_focus_base: float = 1.0
    tau_candidate_entropy_weight: float = 0.35
    tau_surprise_weight: float = 0.55
    tau_dissonance_weight: float = 0.25

