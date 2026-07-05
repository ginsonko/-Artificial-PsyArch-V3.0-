from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from apv3test.runtime.incremental_tick_runtime import (
    IncrementalTickInput,
    IncrementalTickRuntime,
    IncrementalTickResult,
)


CURRICULUM_TRACE_LABELS = (
    "echo_imitation",
    "successor_prediction",
    "multi_reply_aggregation",
    "process_paradigm_binding",
    "focus_slot_filling",
    "recall_only_validation",
)


@dataclass(frozen=True)
class CurriculumTeachingStep:
    case_name: str
    cue_tokens: tuple[str, ...]
    reply_tokens: tuple[str, ...]
    context_tokens: tuple[str, ...]
    stage: str
    reward_delta: float = 1.0


@dataclass(frozen=True)
class CurriculumValidationCase:
    case_id: str
    cue_tokens: tuple[str, ...]
    context_tokens: tuple[str, ...]
    expected_tokens: tuple[str, ...]
    expected_pid: str = ""
    focus_tokens: tuple[str, ...] = ()
    allow_current_focus: bool = False


@dataclass(frozen=True)
class CurriculumEpisode:
    episode_id: str
    source_kind: str
    teaching_steps: tuple[CurriculumTeachingStep, ...]
    validation_cases: tuple[CurriculumValidationCase, ...]


@dataclass(frozen=True)
class CurriculumDiagnosis:
    failure_kind: str
    detail: str


@dataclass(frozen=True)
class CurriculumValidationResult:
    case_id: str
    success: bool
    expected_tokens: tuple[str, ...]
    emitted_tokens: tuple[str, ...]
    committed_text: str
    focus_pid: str
    diagnosis: CurriculumDiagnosis


@dataclass(frozen=True)
class CurriculumRunResult:
    state: dict[str, Any]
    stage_counts: Mapping[str, int]
    validation_results: tuple[CurriculumValidationResult, ...]


class APV3CurriculumRunner:
    """Run APV3 standard teaching episodes through the tick runtime."""

    def __init__(self, runtime: IncrementalTickRuntime | None = None) -> None:
        self.runtime = runtime or IncrementalTickRuntime()

    def run(
        self,
        state: Mapping[str, Any],
        episode: CurriculumEpisode,
        *,
        start_tick: int = 1,
    ) -> CurriculumRunResult:
        next_state = dict(state)
        tick = int(start_tick)
        stage_counts: dict[str, int] = {}
        for step in episode.teaching_steps:
            stage = step.stage or "unlabeled_teacher_trace"
            result = self.runtime.run_tick(
                next_state,
                IncrementalTickInput(
                    tick=tick,
                    case_name=step.case_name,
                    cue_tokens=step.cue_tokens,
                    reply_tokens=step.reply_tokens,
                    context_tokens=step.context_tokens,
                    source_kind=episode.source_kind,
                    teacher_stage=stage,
                    commit_observation=True,
                    reward_delta=step.reward_delta,
                ),
            )
            next_state = result.state
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            tick += 1

        validation_results: list[CurriculumValidationResult] = []
        for validation in episode.validation_cases:
            stage_counts["recall_only_validation"] = stage_counts.get("recall_only_validation", 0) + 1
            focus_tokens = validation.focus_tokens if validation.allow_current_focus else ()
            tick_result = self.runtime.run_tick(
                next_state,
                IncrementalTickInput(
                    tick=tick,
                    cue_tokens=validation.cue_tokens,
                    context_tokens=validation.context_tokens,
                    focus_tokens=focus_tokens,
                    candidate_pool=(),
                    emit_reply=True,
                    commit_after_draft=True,
                    grasp=1.3,
                    demand_slow=0.1,
                ),
            )
            validation_results.append(self._validation_result(validation, tick_result))
            next_state = tick_result.state
            tick = _next_tick_after_validation(tick, tick_result)
        return CurriculumRunResult(
            state=next_state,
            stage_counts=stage_counts,
            validation_results=tuple(validation_results),
        )

    def _validation_result(
        self,
        validation: CurriculumValidationCase,
        result: IncrementalTickResult,
    ) -> CurriculumValidationResult:
        focus = result.recall_result.focus if result.recall_result is not None else None
        focus_pid = focus.pid if focus is not None else ""
        emitted = result.dialogue_result.emitted_tokens if result.dialogue_result is not None else ()
        committed = result.dialogue_result.committed_text if result.dialogue_result is not None else ""
        success = (
            emitted == validation.expected_tokens
            and (not validation.expected_pid or validation.expected_pid == focus_pid)
        )
        diagnosis = _diagnose(validation, result, emitted=emitted, focus_pid=focus_pid)
        return CurriculumValidationResult(
            case_id=validation.case_id,
            success=success,
            expected_tokens=validation.expected_tokens,
            emitted_tokens=emitted,
            committed_text=committed,
            focus_pid=focus_pid,
            diagnosis=diagnosis,
        )


def _diagnose(
    validation: CurriculumValidationCase,
    result: IncrementalTickResult,
    *,
    emitted: tuple[str, ...],
    focus_pid: str,
) -> CurriculumDiagnosis:
    if result.recall_result is None or result.recall_result.focus is None:
        return CurriculumDiagnosis("bn_not_recalled", "no ParadigmSA entered attention focus")
    if validation.expected_pid and focus_pid != validation.expected_pid:
        return CurriculumDiagnosis("attention_wrong", f"focused {focus_pid} instead of {validation.expected_pid}")
    if result.recall_result.focus.cn is None:
        return CurriculumDiagnosis("cn_successor_weak", "focused paradigm has no usable successor")
    if result.dialogue_result is None:
        return CurriculumDiagnosis("commit_action_outcome_missing", "no draft action reached commit path")
    if emitted != validation.expected_tokens:
        expected_set = set(validation.expected_tokens)
        focus_set = set(validation.focus_tokens)
        if focus_set and expected_set & focus_set:
            return CurriculumDiagnosis("slot_focus_overridden", "emitted tokens differ from current focus-slot expectation")
        return CurriculumDiagnosis("cn_successor_weak", "successor tokens differ from expected validation target")
    return CurriculumDiagnosis("success", "validation passed")

def _next_tick_after_validation(current_tick: int, result: IncrementalTickResult) -> int:
    used_ticks = [int(current_tick)]
    if result.dialogue_result is not None:
        used_ticks.extend(int(trace.tick) for trace in result.dialogue_result.action_traces)
        commits = result.dialogue_result.state.get("draft_runtime", {}).get("commits", [])
        if isinstance(commits, list):
            for item in commits:
                if isinstance(item, dict):
                    try:
                        used_ticks.append(int(item.get("tick", current_tick)))
                    except (TypeError, ValueError):
                        pass
    return max(used_ticks) + 1
