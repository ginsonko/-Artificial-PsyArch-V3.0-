from __future__ import annotations

from apv3test.config import APV3ActiveLearningConfig
from apv3test.runtime import (
    APV3ActiveTeacherRequestRuntime,
    APV3CurriculumRunner,
    APV3TeachingProtocolSelector,
    RepeatedEvidenceCourseProposal,
    TeacherRequestSignal,
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


def _ready_course(previous_failure_kind: str = "") -> RepeatedEvidenceCourseProposal:
    state, request = _request()
    return APV3TeachingProtocolSelector().propose_repeated_evidence_course(
        state,
        request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
        context=TeachingPlanContext(failure_kind="cn_successor_weak"),
        previous_failure_kind=previous_failure_kind,
    )


def test_phase6_5_repeated_evidence_without_teacher_tokens_waits_and_writes_no_student_evidence() -> None:
    state, request = _request()
    proposal = APV3TeachingProtocolSelector().propose_repeated_evidence_course(
        state,
        request,
        context=TeachingPlanContext(failure_kind="bn_not_recalled"),
    )

    assert proposal.status == "awaiting_teacher_evidence"
    assert proposal.episode.teaching_steps == ()
    assert proposal.episode.validation_cases == ()
    assert proposal.repeat_bands[0].band_name == "await_teacher_evidence"
    assert proposal.protocol_trace["evidence_repeat_bands"][0]["trigger"] == "missing_teacher_evidence"
    assert "teacher::answer" not in str(proposal)
    assert "answer_table" not in str(proposal)


def test_phase6_5_repeated_evidence_course_runs_support_repeats_and_validation() -> None:
    state, request = _request()
    proposal = APV3TeachingProtocolSelector().propose_repeated_evidence_course(
        state,
        request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
        context=TeachingPlanContext(failure_kind="cn_successor_weak"),
    )
    result = APV3CurriculumRunner().run(state, proposal.episode, start_tick=10)

    assert proposal.status == "ready"
    assert [item.band_name for item in proposal.repeat_bands] == [
        "initial_support_repeats",
        "additional_successor_repeats",
        "recall_only_validation",
        "failure_followup_repeats",
    ]
    assert proposal.repeat_bands[0].teaching_step_count == 2
    assert proposal.repeat_bands[1].teaching_step_count == 1
    assert proposal.repeat_bands[2].validation_case_count == 1
    assert proposal.repeat_bands[3].teaching_step_count == 0
    assert proposal.protocol_trace["student_evidence_shape"] == "same_cue_reply_context_repeated"
    assert len(proposal.episode.teaching_steps) == 3
    assert all(step.stage == "teacher_response" for step in proposal.episode.teaching_steps)
    assert len({(step.cue_tokens, step.reply_tokens, step.context_tokens) for step in proposal.episode.teaching_steps}) == 1
    assert result.validation_results[0].success is True
    assert result.validation_results[0].emitted_tokens == ("teacher::answer",)


def test_phase6_5_previous_failure_adds_ap_native_remediation_round() -> None:
    proposal = _ready_course(previous_failure_kind="cn_successor_weak")

    assert proposal.repeat_bands[3].band_name == "failure_followup_repeats"
    assert proposal.repeat_bands[3].trigger == "cn_successor_weak"
    assert proposal.repeat_bands[3].teaching_step_count == 1
    assert proposal.protocol_trace["previous_failure_kind"] == "cn_successor_weak"
    assert len(proposal.episode.teaching_steps) == 4
    assert all(step.stage == "teacher_response" for step in proposal.episode.teaching_steps)


def test_phase6_5_repeat_bands_do_not_leak_into_student_runtime_state() -> None:
    state, _request_sa = _request()
    proposal = _ready_course(previous_failure_kind="attention_wrong")
    result = APV3CurriculumRunner().run(state, proposal.episode, start_tick=10)
    student_state = str(result.state)

    assert result.validation_results[0].success is True
    assert "initial_support_repeats" not in student_state
    assert "additional_successor_repeats" not in student_state
    assert "recall_only_validation" not in student_state
    assert "failure_followup_repeats" not in student_state
    assert "llm_policy" not in student_state
    assert "answer_table" not in student_state


def test_phase6_5_exposed_skill_reduces_cue_support_round() -> None:
    state, request = _request()
    selector = APV3TeachingProtocolSelector()
    first = selector.propose_repeated_evidence_course(
        state,
        request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
    )
    learned = APV3CurriculumRunner().run(state, first.episode, start_tick=10)
    second = selector.propose_repeated_evidence_course(
        learned.state,
        request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
    )

    assert first.repeat_bands[0].teaching_step_count == 2
    assert second.repeat_bands[0].teaching_step_count == 1
    assert first.protocol_trace["was_exposed_at_check_time"] is False
    assert second.protocol_trace["was_exposed_at_check_time"] is True
    assert len(second.episode.teaching_steps) == 2
