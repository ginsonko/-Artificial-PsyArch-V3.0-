from __future__ import annotations

from apv3test.runtime import (
    APV3ActiveLearningBridge,
    APV3CurriculumRemediationLoop,
    APV3WorkMemoryRuntime,
    CurriculumEpisode,
    CurriculumValidationCase,
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
            }
        },
        "transitions": [],
        "paradigms": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def _store_work_memory(state: dict) -> dict:
    return APV3WorkMemoryRuntime().run_tick(
        state,
        WorkMemoryTickInput(tick=10, focus_tokens=("goal::ask",), pressure=0.9),
    ).state


def _teacher_episode() -> CurriculumEpisode:
    return CurriculumEpisode(
        episode_id="phase6_1:teacher_response",
        source_kind="llm_standard_teacher",
        teaching_steps=(),
        validation_cases=(
            CurriculumValidationCase(
                "needs:ask",
                ("goal::ask",),
                ("ctx_work",),
                ("teacher::answer",),
                expected_pid="p:discovered:skill_teacher_answer",
            ),
        ),
    )


def test_phase6_1_work_memory_bridge_failure_creates_teacher_request() -> None:
    state = _store_work_memory(_base_state())
    result = APV3ActiveLearningBridge().run_work_memory_idle(state, tick=20, context_tokens=("ctx_work",))

    assert result.work_memory_bridge_result is not None
    assert result.work_memory_bridge_result.work_memory_result.recalled_item is not None
    assert result.work_memory_bridge_result.recall_result is not None
    assert result.work_memory_bridge_result.recall_result.dialogue_result is None
    assert result.teacher_request_result is not None
    assert result.teacher_request_result.request is not None
    assert result.teacher_request_result.request.reason == "remediation_needed"
    assert result.teacher_request_result.request.cue_tokens == ("goal::ask",)


def test_phase6_1_teacher_response_allows_original_work_memory_task_to_resume_without_new_request() -> None:
    state = _store_work_memory(_base_state())
    failed = APV3ActiveLearningBridge().run_work_memory_idle(state, tick=20, context_tokens=("ctx_work",))
    learned = APV3CurriculumRemediationLoop().run(
        failed.state,
        _teacher_episode(),
        start_tick=21,
        remediation_start_tick=25,
    )
    resumed = APV3ActiveLearningBridge().run_work_memory_idle(
        learned.final.state,
        tick=35,
        context_tokens=("ctx_work",),
    )

    assert learned.final.validation_results[0].success is True
    assert resumed.work_memory_bridge_result is not None
    assert resumed.work_memory_bridge_result.recall_result is not None
    assert resumed.work_memory_bridge_result.recall_result.dialogue_result is not None
    assert resumed.work_memory_bridge_result.recall_result.dialogue_result.emitted_tokens == ("teacher::answer",)
    assert resumed.teacher_request_result is None
    assert "llm_policy" not in str(resumed.state)


def test_phase6_1_direct_bn_cn_failure_creates_teacher_request() -> None:
    tick_runtime = IncrementalTickRuntime()
    state = _base_state()
    recall = tick_runtime.run_tick(
        state,
        IncrementalTickInput(
            tick=5,
            cue_tokens=("goal::ask",),
            context_tokens=("ctx_work",),
            emit_reply=True,
            commit_after_draft=True,
        ),
    )
    result = APV3ActiveLearningBridge().observe_recall_failure(
        recall.state,
        tick=6,
        cue_tokens=("goal::ask",),
        context_tokens=("ctx_work",),
        cognitive_pressure=0.8,
        recall_result=recall,
    )

    assert recall.dialogue_result is None
    assert result.teacher_request_result is not None
    assert result.teacher_request_result.request is not None
    assert result.teacher_request_result.request.reason == "remediation_needed"


def test_phase6_1_successful_recall_does_not_create_teacher_request() -> None:
    state = APV3CurriculumRemediationLoop().run(_base_state(), _teacher_episode(), start_tick=1).final.state
    recall = IncrementalTickRuntime().run_tick(
        state,
        IncrementalTickInput(
            tick=20,
            cue_tokens=("goal::ask",),
            context_tokens=("ctx_work",),
            emit_reply=True,
            commit_after_draft=True,
        ),
    )
    result = APV3ActiveLearningBridge().observe_recall_failure(
        recall.state,
        tick=21,
        cue_tokens=("goal::ask",),
        context_tokens=("ctx_work",),
        cognitive_pressure=0.8,
        recall_result=recall,
    )

    assert recall.dialogue_result is not None
    assert recall.dialogue_result.emitted_tokens == ("teacher::answer",)
    assert result.teacher_request_result is None
