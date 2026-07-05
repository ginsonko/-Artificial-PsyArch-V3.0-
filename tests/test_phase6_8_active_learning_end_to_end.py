from __future__ import annotations

from apv3test.config import APV3ActiveLearningConfig
from apv3test.runtime import (
    APV3ActiveLearningBridge,
    APV3WorkMemoryRuntime,
    ActiveLearningTeachingResult,
    IncrementalTickInput,
    IncrementalTickRuntime,
    WorkMemoryTickInput,
)


def _base_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "ctx_work": {"vector": [1.0, 0.0], "support": 4.0, "promoted": True},
                "goal::ask": {"vector": [0.9, 0.1], "support": 4.0, "promoted": True},
                "goal::resume": {"vector": [0.8, 0.2], "support": 4.0, "promoted": True},
            }
        },
        "transitions": [],
        "paradigms": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def _recall(state: dict, cue_tokens: tuple[str, ...], *, tick: int = 1):
    return IncrementalTickRuntime().run_tick(
        state,
        IncrementalTickInput(
            tick=tick,
            cue_tokens=cue_tokens,
            context_tokens=("ctx_work",),
            emit_reply=True,
            commit_after_draft=True,
            grasp=1.3,
            demand_slow=0.1,
        ),
    )


def test_phase6_8_direct_failure_ask_teacher_learn_recall_then_stop_asking() -> None:
    bridge = APV3ActiveLearningBridge(config=APV3ActiveLearningConfig(request_cooldown_ticks=0))

    failed = _recall(_base_state(), ("goal::ask",), tick=1)
    request_result = bridge.observe_recall_failure(
        failed.state,
        tick=2,
        cue_tokens=("goal::ask",),
        context_tokens=("ctx_work",),
        cognitive_pressure=0.9,
        recall_result=failed,
    )

    assert failed.dialogue_result is None
    assert request_result.teacher_request_result is not None
    assert request_result.teacher_request_result.request is not None
    assert request_result.teacher_request_result.request.reason == "remediation_needed"

    learned = bridge.run_teacher_response_iterations(
        request_result.state,
        request=request_result.teacher_request_result.request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
        start_tick=10,
    )
    recalled = _recall(learned.state, ("goal::ask",), tick=50)
    after_success = bridge.observe_recall_failure(
        recalled.state,
        tick=51,
        cue_tokens=("goal::ask",),
        context_tokens=("ctx_work",),
        cognitive_pressure=0.9,
        recall_result=recalled,
    )

    assert isinstance(learned, ActiveLearningTeachingResult)
    assert learned.stopped_reason == "validation_success"
    assert recalled.dialogue_result is not None
    assert recalled.dialogue_result.emitted_tokens == ("teacher::answer",)
    assert after_success.teacher_request_result is None
    assert "llm_policy" not in str(after_success.state)
    assert "answer_table" not in str(after_success.state)


def test_phase6_8_work_memory_failure_ask_teacher_then_idle_resume_succeeds() -> None:
    state = APV3WorkMemoryRuntime().run_tick(
        _base_state(),
        WorkMemoryTickInput(tick=5, focus_tokens=("goal::resume",), pressure=0.92),
    ).state
    bridge = APV3ActiveLearningBridge(config=APV3ActiveLearningConfig(request_cooldown_ticks=0))

    failed_idle = bridge.run_work_memory_idle(state, tick=12, context_tokens=("ctx_work",))

    assert failed_idle.work_memory_bridge_result is not None
    assert failed_idle.work_memory_bridge_result.work_memory_result.recalled_item is not None
    assert failed_idle.work_memory_bridge_result.recall_result is not None
    assert failed_idle.work_memory_bridge_result.recall_result.dialogue_result is None
    assert failed_idle.teacher_request_result is not None
    assert failed_idle.teacher_request_result.request is not None
    assert failed_idle.teacher_request_result.request.cue_tokens == ("goal::resume",)

    learned = bridge.run_teacher_response_iterations(
        failed_idle.state,
        request=failed_idle.teacher_request_result.request,
        reply_tokens=("continue::resume",),
        case_name="skill_resume_answer",
        expected_pid="p:discovered:skill_resume_answer",
        start_tick=20,
    )
    resumed = bridge.run_work_memory_idle(learned.state, tick=32, context_tokens=("ctx_work",))

    assert learned.stopped_reason == "validation_success"
    assert resumed.work_memory_bridge_result is not None
    assert resumed.work_memory_bridge_result.recall_result is not None
    assert resumed.work_memory_bridge_result.recall_result.dialogue_result is not None
    assert resumed.work_memory_bridge_result.recall_result.dialogue_result.emitted_tokens == ("continue::resume",)
    assert resumed.teacher_request_result is None


def test_phase6_8_no_external_teacher_evidence_waits_without_learning() -> None:
    bridge = APV3ActiveLearningBridge(config=APV3ActiveLearningConfig(request_cooldown_ticks=0))
    failed = _recall(_base_state(), ("goal::ask",), tick=1)
    request_result = bridge.observe_recall_failure(
        failed.state,
        tick=2,
        cue_tokens=("goal::ask",),
        context_tokens=("ctx_work",),
        cognitive_pressure=0.9,
        recall_result=failed,
    )
    assert request_result.teacher_request_result is not None
    assert request_result.teacher_request_result.request is not None

    waiting = bridge.run_teacher_response_iterations(
        request_result.state,
        request=request_result.teacher_request_result.request,
        reply_tokens=(),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
        start_tick=10,
    )

    assert waiting.stopped_reason == "awaiting_teacher_evidence"
    assert waiting.state == request_result.state
    assert waiting.iterations[0].run_result is None
    assert waiting.state.get("paradigms", []) == []


def test_phase6_8_persistent_teaching_failure_stops_at_depth_boundary() -> None:
    bridge = APV3ActiveLearningBridge(
        config=APV3ActiveLearningConfig(request_cooldown_ticks=0, max_teaching_iteration_depth=2)
    )
    failed = _recall(_base_state(), ("goal::ask",), tick=1)
    request_result = bridge.observe_recall_failure(
        failed.state,
        tick=2,
        cue_tokens=("goal::ask",),
        context_tokens=("ctx_work",),
        cognitive_pressure=0.9,
        recall_result=failed,
    )
    assert request_result.teacher_request_result is not None
    assert request_result.teacher_request_result.request is not None

    bounded = bridge.run_teacher_response_iterations(
        request_result.state,
        request=request_result.teacher_request_result.request,
        reply_tokens=("teacher::answer",),
        case_name="skill_wrong_pid",
        expected_pid="p:discovered:skill_teacher_answer",
        start_tick=10,
    )

    assert bounded.stopped_reason == "max_iteration_depth"
    assert len(bounded.iterations) == 2
    assert all(item.run_result is not None for item in bounded.iterations)
    assert all(
        item.run_result.validation_results[0].success is False
        for item in bounded.iterations
        if item.run_result is not None
    )
