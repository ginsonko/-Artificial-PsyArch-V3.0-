from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig
from apv3test.runtime.active_teacher_request import TeacherRequestSA
from apv3test.runtime.curriculum import CurriculumEpisode, CurriculumTeachingStep, CurriculumValidationCase


@dataclass(frozen=True)
class TeacherEpisodeProposal:
    """Teacher-side proposal derived from a teacher_request SA."""

    request_id: str
    status: str
    source_kind: str
    episode: CurriculumEpisode
    protocol_trace: Mapping[str, Any]


@dataclass(frozen=True)
class TeacherEvidenceRepeatBand:
    """Teacher-side label for repeated AP-native evidence, not a course stage."""

    band_name: str
    intent: str
    teaching_step_count: int = 0
    validation_case_count: int = 0
    trigger: str = "always"


@dataclass(frozen=True)
class RepeatedEvidenceCourseProposal:
    """Teacher-side repeat schedule expressed as same-shape AP-native evidence."""

    request_id: str
    status: str
    source_kind: str
    episode: CurriculumEpisode
    repeat_bands: tuple[TeacherEvidenceRepeatBand, ...]
    protocol_trace: Mapping[str, Any]


@dataclass(frozen=True)
class TeachingPlanContext:
    """Teacher-side diagnostic context for shaping a teaching outline."""

    failure_kind: str = ""
    failure_detail: str = ""
    work_memory_bundle: tuple[str, ...] = ()
    competing_pids: tuple[str, ...] = ()
    pressure_sources: tuple[str, ...] = ()
    current_focus_pid: str = ""


class APV3TeachingProtocolSelector:
    """Translate teacher_request SA into standard AP-native teaching episodes.

    This object lives on the teacher side. It may organize evidence that a
    human/LLM teacher provides, but it never invents reply tokens for the
    student runtime.
    """

    def __init__(self, config: APV3ParadigmDiscoveryConfig | None = None) -> None:
        self.config = config or APV3ParadigmDiscoveryConfig()

    def propose(
        self,
        state: Mapping[str, Any],
        request: TeacherRequestSA,
        *,
        reply_tokens: tuple[str, ...] = (),
        source_kind: str = "llm_standard_teacher",
        case_name: str = "",
        expected_pid: str = "",
        context: TeachingPlanContext | None = None,
    ) -> TeacherEpisodeProposal:
        target_case_name = case_name or _case_name_from_request(request)
        target_pid = expected_pid or f"p:discovered:{target_case_name}"
        plan_context = context or TeachingPlanContext()
        exposed_at_check = _expected_paradigm_is_exposed(state, target_pid)
        trace = _protocol_trace(
            request,
            target_case_name,
            target_pid,
            context=plan_context,
            has_teacher_evidence=bool(reply_tokens),
            was_exposed_at_check_time=exposed_at_check,
        )

        if not reply_tokens:
            return TeacherEpisodeProposal(
                request_id=request.request_id,
                status="awaiting_teacher_evidence",
                source_kind=source_kind,
                episode=CurriculumEpisode(
                    episode_id=f"teacher_protocol:{_safe_id(request.request_id)}:awaiting",
                    source_kind=source_kind,
                    teaching_steps=(),
                    validation_cases=(),
                ),
                protocol_trace=trace,
            )

        repeats = 1 if exposed_at_check else max(1, int(self.config.min_support))
        steps = tuple(
            CurriculumTeachingStep(
                case_name=target_case_name,
                cue_tokens=request.cue_tokens,
                reply_tokens=reply_tokens,
                context_tokens=request.context_tokens,
                stage="teacher_response",
                reward_delta=1.0,
            )
            for _ in range(repeats)
        )
        validation = CurriculumValidationCase(
            case_id=f"validate:{target_case_name}",
            cue_tokens=request.cue_tokens,
            context_tokens=request.context_tokens,
            expected_tokens=reply_tokens,
            expected_pid=target_pid,
        )
        return TeacherEpisodeProposal(
            request_id=request.request_id,
            status="ready",
            source_kind=source_kind,
            episode=CurriculumEpisode(
                episode_id=f"teacher_protocol:{_safe_id(request.request_id)}",
                source_kind=source_kind,
                teaching_steps=steps,
                validation_cases=(validation,),
            ),
            protocol_trace={**trace, "evidence_repeats": repeats},
        )

    def propose_repeated_evidence_course(
        self,
        state: Mapping[str, Any],
        request: TeacherRequestSA,
        *,
        reply_tokens: tuple[str, ...] = (),
        source_kind: str = "llm_standard_teacher",
        case_name: str = "",
        expected_pid: str = "",
        context: TeachingPlanContext | None = None,
        previous_failure_kind: str = "",
    ) -> RepeatedEvidenceCourseProposal:
        target_case_name = case_name or _case_name_from_request(request)
        target_pid = expected_pid or f"p:discovered:{target_case_name}"
        plan_context = context or TeachingPlanContext()
        exposed_at_check = _expected_paradigm_is_exposed(state, target_pid)
        trace = _protocol_trace(
            request,
            target_case_name,
            target_pid,
            context=plan_context,
            has_teacher_evidence=bool(reply_tokens),
            was_exposed_at_check_time=exposed_at_check,
        )

        if not reply_tokens:
            bands = (
                TeacherEvidenceRepeatBand(
                    "await_teacher_evidence",
                    "teacher supplies target successor tokens before student evidence is written",
                    trigger="missing_teacher_evidence",
                ),
            )
            return RepeatedEvidenceCourseProposal(
                request_id=request.request_id,
                status="awaiting_teacher_evidence",
                source_kind=source_kind,
                episode=CurriculumEpisode(
                    episode_id=f"teacher_course:{_safe_id(request.request_id)}:awaiting",
                    source_kind=source_kind,
                    teaching_steps=(),
                    validation_cases=(),
                ),
                repeat_bands=bands,
                protocol_trace={**trace, "evidence_repeat_bands": _repeat_band_trace(bands)},
            )

        support_repeats = 1 if exposed_at_check else max(1, int(self.config.min_support))
        additional_repeats = max(0, int(self.config.additional_evidence_band_repeats))
        remediation_repeats = 1 if previous_failure_kind else 0
        steps = (
            _teaching_steps(
                target_case_name,
                request,
                reply_tokens,
                support_repeats,
            )
            + _teaching_steps(
                target_case_name,
                request,
                reply_tokens,
                additional_repeats,
            )
            + _teaching_steps(
                target_case_name,
                request,
                reply_tokens,
                remediation_repeats,
            )
        )
        validation = CurriculumValidationCase(
            case_id=f"validate:{target_case_name}",
            cue_tokens=request.cue_tokens,
            context_tokens=request.context_tokens,
            expected_tokens=reply_tokens,
            expected_pid=target_pid,
        )
        bands = (
            TeacherEvidenceRepeatBand(
                "initial_support_repeats",
                "same-shape cue/reply/context evidence repeated for initial support",
                teaching_step_count=support_repeats,
            ),
            TeacherEvidenceRepeatBand(
                "additional_successor_repeats",
                "same-shape cue/reply/context evidence repeated for successor statistics",
                teaching_step_count=additional_repeats,
            ),
            TeacherEvidenceRepeatBand(
                "recall_only_validation",
                "validate with cue/context only and no candidate answer pool",
                validation_case_count=1,
            ),
            TeacherEvidenceRepeatBand(
                "failure_followup_repeats",
                "same-shape AP-native evidence repeated only when previous validation failed",
                teaching_step_count=remediation_repeats,
                trigger=previous_failure_kind or "if_validation_fails",
            ),
        )
        return RepeatedEvidenceCourseProposal(
            request_id=request.request_id,
            status="ready",
            source_kind=source_kind,
            episode=CurriculumEpisode(
                episode_id=f"teacher_course:{_safe_id(request.request_id)}",
                source_kind=source_kind,
                teaching_steps=steps,
                validation_cases=(validation,),
            ),
            repeat_bands=bands,
            protocol_trace={
                **trace,
                "evidence_repeat_bands": _repeat_band_trace(bands),
                "evidence_repeats": len(steps),
                "previous_failure_kind": previous_failure_kind,
                "student_evidence_shape": "same_cue_reply_context_repeated",
            },
        )


def _protocol_trace(
    request: TeacherRequestSA,
    case_name: str,
    expected_pid: str,
    *,
    context: TeachingPlanContext,
    has_teacher_evidence: bool,
    was_exposed_at_check_time: bool = False,
) -> dict[str, Any]:
    failure_kind = context.failure_kind or request.reason
    return {
        "schema_id": "apv3_teacher_episode_proposal_trace/v1",
        "request_id": request.request_id,
        "cue_tokens": list(request.cue_tokens),
        "context_tokens": list(request.context_tokens),
        "request_reason": request.reason,
        "failure_diagnosis": failure_kind,
        "failure_detail": context.failure_detail,
        "failure_count": int(request.failure_count),
        "cognitive_pressure": float(request.cognitive_pressure),
        "remediation_need": float(request.remediation_need),
        "work_memory_bundle": list(context.work_memory_bundle),
        "competing_pids": list(context.competing_pids),
        "pressure_sources": list(context.pressure_sources),
        "current_focus_pid": context.current_focus_pid,
        "plan_outline": _plan_outline(request, context, has_teacher_evidence=has_teacher_evidence),
        "case_name": case_name,
        "expected_pid": expected_pid,
        "was_exposed_at_check_time": bool(was_exposed_at_check_time),
        "state_handoff_contract": "caller_must_use_runner_returned_state_for_next_proposal",
    }


def _teaching_steps(
    case_name: str,
    request: TeacherRequestSA,
    reply_tokens: tuple[str, ...],
    repeats: int,
) -> tuple[CurriculumTeachingStep, ...]:
    return tuple(
        CurriculumTeachingStep(
            case_name=case_name,
            cue_tokens=request.cue_tokens,
            reply_tokens=reply_tokens,
            context_tokens=request.context_tokens,
            stage="teacher_response",
            reward_delta=1.0,
        )
        for _ in range(max(0, int(repeats)))
    )


def _repeat_band_trace(rounds: tuple[TeacherEvidenceRepeatBand, ...]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "band_name": item.band_name,
            "intent": item.intent,
            "teaching_step_count": int(item.teaching_step_count),
            "validation_case_count": int(item.validation_case_count),
            "trigger": item.trigger,
        }
        for item in rounds
    )


def _plan_outline(
    request: TeacherRequestSA,
    context: TeachingPlanContext,
    *,
    has_teacher_evidence: bool,
) -> tuple[str, ...]:
    outline: list[str] = []
    if not has_teacher_evidence:
        outline.append("await_teacher_evidence")
    failure_kind = context.failure_kind or request.reason
    if failure_kind:
        outline.append(f"address:{failure_kind}")
    if context.work_memory_bundle:
        outline.append("include:work_memory_bundle")
    if context.competing_pids:
        outline.append("include:competing_pids")
    if context.pressure_sources:
        outline.append("include:pressure_sources")
    if has_teacher_evidence:
        outline.append("provide:committed_successor_evidence")
    return tuple(outline)


def _case_name_from_request(request: TeacherRequestSA) -> str:
    cue = "_".join(request.cue_tokens) or "empty_cue"
    ctx = "_".join(request.context_tokens) or "empty_context"
    return _safe_id(f"teacher_response_{cue}_{ctx}")


def _safe_id(value: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in value)
    safe = "_".join(part for part in safe.split("_") if part)
    return safe[:96] or "teacher_response"


def _expected_paradigm_is_exposed(state: Mapping[str, Any], expected_pid: str) -> bool:
    paradigms = state.get("paradigms", [])
    if not isinstance(paradigms, list):
        return False
    for item in paradigms:
        if isinstance(item, dict) and str(item.get("pid", "")) == expected_pid:
            return bool(item.get("exposed", False))
    return False
