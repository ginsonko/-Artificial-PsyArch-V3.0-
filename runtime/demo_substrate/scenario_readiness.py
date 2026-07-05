from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.state_pool.state_pool import load_constant
from runtime.demo_substrate.profile import DemoProfile


@dataclass(frozen=True)
class ScenarioReadiness:
    scenario_id: str
    score: float
    ready: bool
    missing_tags: tuple[str, ...]


@dataclass(frozen=True)
class DemoReadinessTrace:
    scenario_results: tuple[ScenarioReadiness, ...]
    supported_count: int
    ready_for_public_trial: bool


def evaluate_demo_readiness(profile: DemoProfile, available_capability_tags: tuple[str, ...]) -> DemoReadinessTrace:
    available = set(available_capability_tags)
    threshold = float(load_constant("demo_substrate.readiness_min_score"))
    results: list[ScenarioReadiness] = []
    for scenario in profile.scenarios:
        required = set(scenario.capability_tags)
        score = 1.0 if not required else float(len(required & available)) / float(len(required))
        missing = tuple(sorted(required - available))
        results.append(
            ScenarioReadiness(
                scenario_id=scenario.scenario_id,
                score=score,
                ready=score >= threshold,
                missing_tags=missing,
            )
        )
    supported = sum(1 for result in results if result.ready)
    return DemoReadinessTrace(
        scenario_results=tuple(results),
        supported_count=supported,
        ready_for_public_trial=supported >= int(load_constant("demo_substrate.scenario_min_supported")),
    )
