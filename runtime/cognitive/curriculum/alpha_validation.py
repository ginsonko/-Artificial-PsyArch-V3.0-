from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from runtime.cognitive.state_pool.state_pool import load_constant
from runtime.demo_substrate.profile import DemoProfile
from runtime.demo_substrate.scenario_readiness import DemoReadinessTrace, evaluate_demo_readiness


@dataclass(frozen=True)
class Phase13AlphaTrace:
    supported_curriculum_phases: tuple[str, ...]
    demo_readiness: DemoReadinessTrace
    accepted: bool


def evaluate_phase13_alpha(
    profile: DemoProfile,
    *,
    curriculum_phases: Sequence[str],
    capability_tags: Sequence[str],
) -> Phase13AlphaTrace:
    """@op_count: O(phases + scenarios)."""
    phases = tuple(sorted({str(item) for item in curriculum_phases if str(item).startswith("13.")}))
    readiness = evaluate_demo_readiness(profile, tuple(str(item) for item in capability_tags))
    return Phase13AlphaTrace(
        supported_curriculum_phases=phases,
        demo_readiness=readiness,
        accepted=(
            len(phases) >= int(load_constant("curriculum.alpha.min_supported_curriculum_phases"))
            and readiness.supported_count >= int(load_constant("curriculum.alpha.min_ready_scenarios"))
        ),
    )

