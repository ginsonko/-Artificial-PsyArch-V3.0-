from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class APV3HabitConfig:
    """Named tuner-owned parameters for fast-system habit readout.

    Habit is read from AP-native action outcome evidence. It is not a lookup
    table and it does not execute actions by itself.
    """

    support_half_life: float = 4.0
    recency_half_life_ticks: float = 32.0
    unknown_recency_gain: float = 0.5
    support_weight: float = 0.8
    reward_weight: float = 1.2
    punish_weight: float = 1.4
    drive_bias_weight: float = 0.8
    recency_gain_weight: float = 0.35
    context_floor: float = 0.2
    habit_drive_weight: float = 1.0
    lambda_fast_drive_weight: float = 0.75
