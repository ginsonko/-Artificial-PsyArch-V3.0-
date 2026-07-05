from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class APV3WorkMemoryConfig:
    """Named parameters for pressure-driven working memory probes."""

    open_pressure_min: float = 0.05
    closure_threshold: float = 0.82
    interruption_surprise_min: float = 0.5
    idle_recall_pressure_min: float = 0.08
    pressure_decay_per_tick: float = 0.92
    recency_half_life_ticks: float = 12.0
    semantic_overlap_min: float = 0.72
    max_items: int = 16
