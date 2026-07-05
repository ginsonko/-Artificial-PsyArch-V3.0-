from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from apv3test.runtime.active_teacher_request import TeacherRequestSA
from apv3test.runtime.curriculum import APV3CurriculumRunner, CurriculumRunResult, CurriculumValidationResult
from apv3test.runtime.teaching_protocol_selector import (
    APV3TeachingProtocolSelector,
    RepeatedEvidenceCourseProposal,
    TeachingPlanContext,
)


@dataclass(frozen=True)
class TeachingIterationInput:
    request: TeacherRequestSA
    reply_tokens: tuple[str, ...] = ()
    source_kind: str = "llm_standard_teacher"
    case_name: str = ""
    expected_pid: str = ""
    context: TeachingPlanContext = TeachingPlanContext()
    previous_failure_kind: str = ""


@dataclass(frozen=True)
class TeachingIterationResult:
    state: dict[str, Any]
    proposal: RepeatedEvidenceCourseProposal
    run_result: CurriculumRunResult | None
    next_context: TeachingPlanContext
    next_proposal: RepeatedEvidenceCourseProposal | None


class APV3TeachingIterationLoop:
    """Teacher-side proposal -> validate -> diagnose -> next proposal loop."""

    def __init__(
        self,
        *,
        selector: APV3TeachingProtocolSelector | None = None,
        runner: APV3CurriculumRunner | None = None,
    ) -> None:
        self.selector = selector or APV3TeachingProtocolSelector()
        self.runner = runner or APV3CurriculumRunner()

    def run_once(
        self,
        state: Mapping[str, Any],
        iteration: TeachingIterationInput,
        *,
        start_tick: int = 1,
    ) -> TeachingIterationResult:
        proposal = self.selector.propose_repeated_evidence_course(
            state,
            iteration.request,
            reply_tokens=iteration.reply_tokens,
            source_kind=iteration.source_kind,
            case_name=iteration.case_name,
            expected_pid=iteration.expected_pid,
            context=iteration.context,
            previous_failure_kind=iteration.previous_failure_kind,
        )
        if proposal.status != "ready":
            return TeachingIterationResult(dict(state), proposal, None, iteration.context, None)

        run_result = self.runner.run(state, proposal.episode, start_tick=start_tick)
        failed = _first_failure(run_result)
        if failed is None:
            return TeachingIterationResult(run_result.state, proposal, run_result, TeachingPlanContext(), None)

        next_context = _context_from_failure(failed, iteration.context)
        next_proposal = self.selector.propose_repeated_evidence_course(
            run_result.state,
            iteration.request,
            reply_tokens=iteration.reply_tokens,
            source_kind=iteration.source_kind,
            case_name=iteration.case_name,
            expected_pid=iteration.expected_pid,
            context=next_context,
            previous_failure_kind=failed.diagnosis.failure_kind,
        )
        return TeachingIterationResult(run_result.state, proposal, run_result, next_context, next_proposal)


def _first_failure(run_result: CurriculumRunResult) -> CurriculumValidationResult | None:
    for result in run_result.validation_results:
        if not result.success:
            return result
    return None


def _context_from_failure(
    result: CurriculumValidationResult,
    previous: TeachingPlanContext,
) -> TeachingPlanContext:
    return TeachingPlanContext(
        failure_kind=result.diagnosis.failure_kind,
        failure_detail=result.diagnosis.detail,
        work_memory_bundle=previous.work_memory_bundle,
        competing_pids=_unique_nonempty((previous.current_focus_pid, result.focus_pid)),
        pressure_sources=previous.pressure_sources,
        current_focus_pid=result.focus_pid,
    )


def _unique_nonempty(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for item in values if item))
