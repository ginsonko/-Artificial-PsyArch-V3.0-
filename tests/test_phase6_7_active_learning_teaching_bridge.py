from __future__ import annotations

from apv3test.config import APV3ActiveLearningConfig
from apv3test.runtime import (
    APV3ActiveLearningBridge,
    APV3ActiveTeacherRequestRuntime,
    ActiveLearningTeachingResult,
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


def test_phase6_7_bridge_runs_teacher_response_until_success_and_updates_state() -> None:
    state, request = _request()
    result = APV3ActiveLearningBridge().run_teacher_response_iterations(
        state,
        request=request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
        start_tick=10,
    )

    assert isinstance(result, ActiveLearningTeachingResult)
    assert result.stopped_reason == "validation_success"
    assert len(result.iterations) == 1
    assert result.iterations[0].run_result is not None
    assert result.iterations[0].run_result.validation_results[0].success is True
    assert any(item["pid"] == "p:discovered:skill_teacher_answer" for item in result.state["paradigms"])
    assert "llm_policy" not in str(result.state)
    assert "answer_table" not in str(result.state)


def test_phase6_7_bridge_waits_without_teacher_tokens_and_writes_no_teaching_state() -> None:
    state, request = _request()
    result = APV3ActiveLearningBridge().run_teacher_response_iterations(
        state,
        request=request,
        reply_tokens=(),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
    )

    assert result.stopped_reason == "awaiting_teacher_evidence"
    assert len(result.iterations) == 1
    assert result.iterations[0].run_result is None
    assert result.state == state


def test_phase6_7_bridge_stops_at_configured_max_depth_for_persistent_failure() -> None:
    state, request = _request()
    bridge = APV3ActiveLearningBridge(config=APV3ActiveLearningConfig(max_teaching_iteration_depth=2))
    result = bridge.run_teacher_response_iterations(
        state,
        request=request,
        reply_tokens=("teacher::answer",),
        case_name="skill_wrong",
        expected_pid="p:discovered:skill_teacher_answer",
        start_tick=10,
    )

    assert result.stopped_reason == "max_iteration_depth"
    assert len(result.iterations) == 2
    assert all(item.run_result is not None for item in result.iterations)
    assert all(item.run_result.validation_results[0].success is False for item in result.iterations if item.run_result)
    assert result.iterations[0].next_proposal is not None
    assert result.iterations[1].next_proposal is not None
    assert result.iterations[1].proposal.protocol_trace["previous_failure_kind"] == "attention_wrong"


def test_phase6_7_success_after_prior_learning_suppresses_repeated_support() -> None:
    state, request = _request()
    bridge = APV3ActiveLearningBridge()
    first = bridge.run_teacher_response_iterations(
        state,
        request=request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
        start_tick=10,
    )
    second = bridge.run_teacher_response_iterations(
        first.state,
        request=request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
        start_tick=100,
    )

    assert first.iterations[0].proposal.protocol_trace["was_exposed_at_check_time"] is False
    assert second.iterations[0].proposal.protocol_trace["was_exposed_at_check_time"] is True
    assert first.iterations[0].proposal.repeat_bands[0].teaching_step_count == 2
    assert second.iterations[0].proposal.repeat_bands[0].teaching_step_count == 1
