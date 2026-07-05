from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig
from apv3test.runtime.curriculum import (
    APV3CurriculumRunner,
    CurriculumEpisode,
    CurriculumRunResult,
    CurriculumTeachingStep,
    CurriculumValidationCase,
    CurriculumValidationResult,
)


@dataclass(frozen=True)
class CurriculumRemediationSuggestion:
    case_id: str
    failure_kind: str
    teaching_steps: tuple[CurriculumTeachingStep, ...]
    rationale: str
    evidence_repeats: int = 0
    remediation_intensity: float = 0.0


@dataclass(frozen=True)
class CurriculumRemediationLoopResult:
    initial: CurriculumRunResult
    suggestions: tuple[CurriculumRemediationSuggestion, ...]
    remediation_episode: CurriculumEpisode
    final: CurriculumRunResult


class APV3CurriculumRemediationPlanner:
    """Generate AP-native teaching evidence for failed validation cases."""

    def __init__(self, config: APV3ParadigmDiscoveryConfig | None = None) -> None:
        self.config = config or APV3ParadigmDiscoveryConfig()

    def plan(
        self,
        validation_cases: Sequence[CurriculumValidationCase],
        validation_results: Sequence[CurriculumValidationResult],
        *,
        source_kind: str,
        state: Mapping[str, Any] | None = None,
    ) -> tuple[CurriculumRemediationSuggestion, ...]:
        cases = {case.case_id: case for case in validation_cases}
        suggestions: list[CurriculumRemediationSuggestion] = []
        for result in validation_results:
            if result.success:
                continue
            case = cases.get(result.case_id)
            if case is None:
                continue
            suggestions.append(self._suggest(case, result, source_kind=source_kind, state=state or {}))
        return tuple(suggestions)

    def _suggest(
        self,
        case: CurriculumValidationCase,
        result: CurriculumValidationResult,
        *,
        source_kind: str,
        state: Mapping[str, Any],
    ) -> CurriculumRemediationSuggestion:
        if _focus_conflicts_with_expected(case):
            return CurriculumRemediationSuggestion(
                case_id=case.case_id,
                failure_kind=result.diagnosis.failure_kind,
                teaching_steps=(),
                rationale="current focus tokens conflict with expected target; do not solidify contradictory memory",
            )
        if not case.expected_tokens:
            return CurriculumRemediationSuggestion(
                case_id=case.case_id,
                failure_kind=result.diagnosis.failure_kind,
                teaching_steps=(),
                rationale="no teacher target tokens available for AP-native remediation",
            )
        case_name = _case_name_for_remediation(case)
        stage = "remediate"
        support_count = _remediation_repeats(state, case, self.config)
        steps = tuple(
            CurriculumTeachingStep(
                case_name=case_name,
                cue_tokens=case.cue_tokens,
                reply_tokens=case.expected_tokens,
                context_tokens=case.context_tokens,
                stage=stage,
                reward_delta=1.0,
            )
            for _ in range(support_count)
        )
        return CurriculumRemediationSuggestion(
            case_id=case.case_id,
            failure_kind=result.diagnosis.failure_kind,
            teaching_steps=steps,
            rationale=f"{source_kind} teacher supplies committed AP-native evidence with adaptive intensity",
            evidence_repeats=support_count,
            remediation_intensity=round(support_count / max(1, int(self.config.min_support)), 6),
        )


class APV3CurriculumRemediationLoop:
    """Run train -> validate -> diagnose -> remediate -> validate."""

    def __init__(
        self,
        *,
        runner: APV3CurriculumRunner | None = None,
        planner: APV3CurriculumRemediationPlanner | None = None,
    ) -> None:
        self.runner = runner or APV3CurriculumRunner()
        self.planner = planner or APV3CurriculumRemediationPlanner()

    def run(
        self,
        state: Mapping[str, Any],
        episode: CurriculumEpisode,
        *,
        start_tick: int = 1,
        remediation_start_tick: int = 1000,
    ) -> CurriculumRemediationLoopResult:
        initial = self.runner.run(state, episode, start_tick=start_tick)
        suggestions = self.planner.plan(
            episode.validation_cases,
            initial.validation_results,
            source_kind=episode.source_kind,
            state=initial.state,
        )
        remediation_steps = tuple(step for suggestion in suggestions for step in suggestion.teaching_steps)
        remediation_cases = tuple(
            case
            for case in episode.validation_cases
            if any(s.case_id == case.case_id and s.teaching_steps for s in suggestions)
        )
        remediation_episode = CurriculumEpisode(
            episode_id=f"{episode.episode_id}:remediation",
            source_kind=episode.source_kind,
            teaching_steps=remediation_steps,
            validation_cases=remediation_cases,
        )
        final = self.runner.run(
            initial.state,
            remediation_episode,
            start_tick=max(int(start_tick), int(remediation_start_tick)),
        )
        return CurriculumRemediationLoopResult(initial, suggestions, remediation_episode, final)


def _focus_conflicts_with_expected(case: CurriculumValidationCase) -> bool:
    if not case.allow_current_focus or not case.focus_tokens:
        return False
    expected = set(case.expected_tokens)
    return any(token not in expected for token in case.focus_tokens)


def _case_name_for_remediation(case: CurriculumValidationCase) -> str:
    prefix = "p:discovered:"
    if case.expected_pid.startswith(prefix):
        return case.expected_pid[len(prefix) :]
    return "remediate_" + "".join(ch if ch.isalnum() else "_" for ch in case.case_id)


def _remediation_repeats(
    state: Mapping[str, Any],
    case: CurriculumValidationCase,
    config: APV3ParadigmDiscoveryConfig,
) -> int:
    return 1 if _expected_paradigm_is_exposed(state, case.expected_pid) else max(1, int(config.min_support))


def _expected_paradigm_is_exposed(state: Mapping[str, Any], expected_pid: str) -> bool:
    paradigms = state.get("paradigms", [])
    if not isinstance(paradigms, list):
        return False
    for item in paradigms:
        if isinstance(item, dict) and str(item.get("pid", "")) == expected_pid:
            return bool(item.get("exposed", False))
    return False
