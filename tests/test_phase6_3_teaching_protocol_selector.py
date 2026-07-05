from __future__ import annotations

from apv3test.config import APV3ActiveLearningConfig
from apv3test.runtime import (
    APV3ActiveTeacherRequestRuntime,
    APV3CurriculumRunner,
    APV3TeachingProtocolSelector,
    TeacherEpisodeProposal,
    TeacherRequestSignal,
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


def test_phase6_3_request_without_teacher_tokens_waits_and_does_not_invent_answer() -> None:
    state, request = _request()
    proposal = APV3TeachingProtocolSelector().propose(state, request, reply_tokens=())

    assert isinstance(proposal, TeacherEpisodeProposal)
    assert proposal.status == "awaiting_teacher_evidence"
    assert proposal.episode.teaching_steps == ()
    assert proposal.episode.validation_cases == ()
    assert proposal.protocol_trace["cue_tokens"] == ["goal::ask"]
    assert proposal.protocol_trace["failure_diagnosis"] == "remediation_needed"
    assert "teacher::answer" not in str(proposal)
    assert "llm_policy" not in str(proposal)
    assert "answer_table" not in str(proposal)


def test_phase6_3_teacher_proposal_runs_as_ap_native_curriculum_episode() -> None:
    state, request = _request()
    proposal = APV3TeachingProtocolSelector().propose(
        state,
        request,
        reply_tokens=("teacher::answer",),
        source_kind="llm_standard_teacher",
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
    )
    result = APV3CurriculumRunner().run(state, proposal.episode, start_tick=10)

    assert proposal.status == "ready"
    assert len(proposal.episode.teaching_steps) == 2
    assert proposal.episode.teaching_steps[0].stage == "teacher_response"
    assert proposal.protocol_trace["request_reason"] == "remediation_needed"
    assert proposal.protocol_trace["cognitive_pressure"] == 0.9
    assert result.validation_results[0].success is True
    assert result.validation_results[0].emitted_tokens == ("teacher::answer",)
    assert result.validation_results[0].focus_pid == "p:discovered:skill_teacher_answer"
    assert "llm_policy" not in str(result.state)
    assert "answer_table" not in str(result.state)


def test_phase6_3_natural_and_llm_teacher_proposals_are_student_evidence_equivalent() -> None:
    def run(source_kind: str):
        state, request = _request()
        proposal = APV3TeachingProtocolSelector().propose(
            state,
            request,
            reply_tokens=("teacher::answer",),
            source_kind=source_kind,
            case_name="skill_teacher_answer",
            expected_pid="p:discovered:skill_teacher_answer",
        )
        return APV3CurriculumRunner().run(state, proposal.episode, start_tick=10)

    natural = run("natural_teacher")
    llm = run("llm_standard_teacher")

    assert natural.validation_results[0].success is True
    assert llm.validation_results[0].success is True
    assert natural.validation_results[0].emitted_tokens == llm.validation_results[0].emitted_tokens
    assert natural.validation_results[0].focus_pid == llm.validation_results[0].focus_pid
    assert "llm_policy" not in str(llm.state)


def test_phase6_3_exposed_skill_uses_weaker_teacher_evidence() -> None:
    state, request = _request()
    selector = APV3TeachingProtocolSelector()
    first = selector.propose(
        state,
        request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
    )
    learned = APV3CurriculumRunner().run(state, first.episode, start_tick=10)
    second = selector.propose(
        learned.state,
        request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
    )

    assert first.protocol_trace["evidence_repeats"] == 2
    assert second.protocol_trace["evidence_repeats"] == 1
    assert len(second.episode.teaching_steps) == 1
