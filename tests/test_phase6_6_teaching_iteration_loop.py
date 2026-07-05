from __future__ import annotations

from apv3test.config import APV3ActiveLearningConfig
from apv3test.runtime import (
    APV3ActiveTeacherRequestRuntime,
    APV3TeachingIterationLoop,
    TeacherRequestSignal,
    TeachingIterationInput,
    TeachingPlanContext,
)


def _base_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "ctx_work": {"vector": [1.0, 0.0], "support": 4.0, "promoted": True},
                "goal::ask": {"vector": [0.9, 0.1], "support": 4.0, "promoted": True},
            }
        },
        "transitions": [],
        "paradigms": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def _request():
    result = APV3ActiveTeacherRequestRuntime(APV3ActiveLearningConfig(request_cooldown_ticks=0)).observe(
        _base_state(),
        TeacherRequestSignal(
            tick=1,
            cue_tokens=("goal::ask",),
            context_tokens=("ctx_work",),
            cognitive_pressure=0.9,
            recall_failed=True,
            remediation_need=1.0,
        ),
    )
    assert result.request is not None
    return result.state, result.request


def test_phase6_6_iteration_waits_when_teacher_has_no_evidence() -> None:
    state, request = _request()
    result = APV3TeachingIterationLoop().run_once(
        state,
        TeachingIterationInput(request=request, context=TeachingPlanContext(failure_kind="bn_not_recalled")),
    )

    assert result.proposal.status == "awaiting_teacher_evidence"
    assert result.run_result is None
    assert result.next_proposal is None
    assert result.state == state


def test_phase6_6_successful_iteration_stops_without_next_proposal() -> None:
    state, request = _request()
    result = APV3TeachingIterationLoop().run_once(
        state,
        TeachingIterationInput(
            request=request,
            reply_tokens=("teacher::answer",),
            case_name="skill_teacher_answer",
            expected_pid="p:discovered:skill_teacher_answer",
            context=TeachingPlanContext(failure_kind="cn_successor_weak"),
        ),
        start_tick=10,
    )

    assert result.run_result is not None
    assert result.run_result.validation_results[0].success is True
    assert result.next_context.failure_kind == ""
    assert result.next_proposal is None
    assert "llm_policy" not in str(result.state)
    assert "answer_table" not in str(result.state)


def test_phase6_6_failed_validation_generates_next_context_and_repeat_proposal() -> None:
    state, request = _request()
    result = APV3TeachingIterationLoop().run_once(
        state,
        TeachingIterationInput(
            request=request,
            reply_tokens=("teacher::answer",),
            case_name="skill_wrong",
            expected_pid="p:discovered:skill_teacher_answer",
            context=TeachingPlanContext(
                failure_kind="attention_wrong",
                current_focus_pid="p:discovered:older_focus",
            ),
        ),
        start_tick=10,
    )

    assert result.run_result is not None
    assert result.run_result.validation_results[0].success is False
    assert result.next_context.failure_kind == "attention_wrong"
    assert result.next_context.current_focus_pid == "p:discovered:skill_wrong"
    assert "p:discovered:older_focus" in result.next_context.competing_pids
    assert "p:discovered:skill_wrong" in result.next_context.competing_pids
    assert result.next_proposal is not None
    assert result.next_proposal.protocol_trace["previous_failure_kind"] == "attention_wrong"
    assert result.next_proposal.repeat_bands[3].teaching_step_count == 1
    assert result.next_proposal.protocol_trace["was_exposed_at_check_time"] is False


def test_phase6_6_next_iteration_uses_runner_returned_state_for_exposed_check() -> None:
    state, request = _request()
    first = APV3TeachingIterationLoop().run_once(
        state,
        TeachingIterationInput(
            request=request,
            reply_tokens=("teacher::answer",),
            case_name="skill_teacher_answer",
            expected_pid="p:discovered:skill_teacher_answer",
        ),
        start_tick=10,
    )
    second = APV3TeachingIterationLoop().run_once(
        first.state,
        TeachingIterationInput(
            request=request,
            reply_tokens=("teacher::answer",),
            case_name="skill_teacher_answer",
            expected_pid="p:discovered:skill_teacher_answer",
        ),
        start_tick=30,
    )

    assert first.proposal.protocol_trace["was_exposed_at_check_time"] is False
    assert second.proposal.protocol_trace["was_exposed_at_check_time"] is True
    assert first.proposal.repeat_bands[0].teaching_step_count == 2
    assert second.proposal.repeat_bands[0].teaching_step_count == 1
