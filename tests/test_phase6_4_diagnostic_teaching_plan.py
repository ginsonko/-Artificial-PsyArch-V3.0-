from __future__ import annotations

from apv3test.config import APV3ActiveLearningConfig
from apv3test.runtime import (
    APV3ActiveTeacherRequestRuntime,
    APV3CurriculumRunner,
    APV3TeachingProtocolSelector,
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
                "ctx_conflict": {"vector": [0.0, 1.0], "support": 4.0, "promoted": True},
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


def test_phase6_4_failure_diagnoses_shape_distinct_teacher_side_outlines() -> None:
    state, request = _request()
    selector = APV3TeachingProtocolSelector()

    bn = selector.propose(
        state,
        request,
        context=TeachingPlanContext(failure_kind="bn_not_recalled"),
    )
    cn = selector.propose(
        state,
        request,
        context=TeachingPlanContext(failure_kind="cn_successor_weak"),
    )
    conflict = selector.propose(
        state,
        request,
        context=TeachingPlanContext(
            failure_kind="attention_wrong",
            competing_pids=("p:discovered:skill_a", "p:discovered:skill_b"),
            current_focus_pid="p:discovered:skill_a",
        ),
    )

    assert "address:bn_not_recalled" in bn.protocol_trace["plan_outline"]
    assert "address:cn_successor_weak" in cn.protocol_trace["plan_outline"]
    assert "address:attention_wrong" in conflict.protocol_trace["plan_outline"]
    assert "include:competing_pids" in conflict.protocol_trace["plan_outline"]
    assert bn.episode.teaching_steps == cn.episode.teaching_steps == conflict.episode.teaching_steps == ()
    assert bn.status == cn.status == conflict.status == "awaiting_teacher_evidence"


def test_phase6_4_work_memory_failure_carries_unfinished_bundle_without_generating_answer() -> None:
    state, request = _request()
    proposal = APV3TeachingProtocolSelector().propose(
        state,
        request,
        context=TeachingPlanContext(
            failure_kind="work_memory_resume_failed",
            failure_detail="idle recall restored an unfinished bundle but Bn/Cn emitted nothing",
            work_memory_bundle=("goal::ask", "subgoal::resume"),
            pressure_sources=("work_memory_unfinished", "teacher_request"),
        ),
    )

    assert proposal.status == "awaiting_teacher_evidence"
    assert proposal.protocol_trace["work_memory_bundle"] == ["goal::ask", "subgoal::resume"]
    assert "address:work_memory_resume_failed" in proposal.protocol_trace["plan_outline"]
    assert "include:work_memory_bundle" in proposal.protocol_trace["plan_outline"]
    assert "include:pressure_sources" in proposal.protocol_trace["plan_outline"]
    assert proposal.episode.teaching_steps == ()
    assert proposal.episode.validation_cases == ()


def test_phase6_4_conflict_plan_runs_as_plain_ap_native_episode() -> None:
    state, request = _request()
    proposal = APV3TeachingProtocolSelector().propose(
        state,
        request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
        context=TeachingPlanContext(
            failure_kind="attention_wrong",
            competing_pids=("p:discovered:skill_wrong", "p:discovered:skill_teacher_answer"),
            current_focus_pid="p:discovered:skill_wrong",
        ),
    )
    result = APV3CurriculumRunner().run(state, proposal.episode, start_tick=10)

    assert "include:competing_pids" in proposal.protocol_trace["plan_outline"]
    assert proposal.episode.teaching_steps[0].stage == "teacher_response"
    assert result.validation_results[0].success is True
    assert result.validation_results[0].emitted_tokens == ("teacher::answer",)
    assert "include:competing_pids" not in str(result.state)
    assert "p:discovered:skill_wrong" not in str(result.state)
    assert "llm_policy" not in str(result.state)
    assert "answer_table" not in str(result.state)


def test_phase6_4_different_plan_contexts_keep_same_student_evidence_shape() -> None:
    state, request = _request()
    selector = APV3TeachingProtocolSelector()

    work_memory = selector.propose(
        state,
        request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
        context=TeachingPlanContext(
            failure_kind="work_memory_resume_failed",
            work_memory_bundle=("goal::ask",),
        ),
    )
    conflict = selector.propose(
        state,
        request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
        context=TeachingPlanContext(
            failure_kind="attention_wrong",
            competing_pids=("p:discovered:skill_a", "p:discovered:skill_b"),
        ),
    )

    assert work_memory.protocol_trace["plan_outline"] != conflict.protocol_trace["plan_outline"]
    assert work_memory.episode.teaching_steps == conflict.episode.teaching_steps
    assert work_memory.episode.validation_cases == conflict.episode.validation_cases
