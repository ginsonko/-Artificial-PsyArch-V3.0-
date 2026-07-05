from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class APV3ActiveLearningConfig:
    """Named parameters for active teacher-request probes."""

    pressure_request_threshold: float = 0.75
    repeated_failure_threshold: int = 2
    remediation_need_threshold: float = 1.0
    request_cooldown_ticks: int = 8
    max_teacher_requests: int = 32
    max_teaching_iteration_depth: int = 3
