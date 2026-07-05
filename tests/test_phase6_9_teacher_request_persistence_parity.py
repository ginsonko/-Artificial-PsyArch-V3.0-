from __future__ import annotations

from pathlib import Path

from apv3test.config import APV3ActiveLearningConfig
from apv3test.runtime import (
    APV3ActiveLearningBridge,
    APV3WorkMemoryRuntime,
    IncrementalTickInput,
    IncrementalTickRuntime,
    SQLiteRuntimeStore,
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


def _recall(state: dict, cue_tokens: tuple[str, ...], *, tick: int):
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


def _bridge() -> APV3ActiveLearningBridge:
    return APV3ActiveLearningBridge(config=APV3ActiveLearningConfig(request_cooldown_ticks=0))


def test_phase6_9_direct_teacher_request_survives_sqlite_warm_load(tmp_path: Path) -> None:
    bridge = _bridge()
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

    learned = bridge.run_teacher_response_iterations(
        request_result.state,
        request=request_result.teacher_request_result.request,
        reply_tokens=("teacher::answer",),
        case_name="skill_teacher_answer",
        expected_pid="p:discovered:skill_teacher_answer",
        start_tick=10,
    )
    memory_recall = _recall(learned.state, ("goal::ask",), tick=50)
    store = SQLiteRuntimeStore(tmp_path / "phase6_9_direct.sqlite")

    state_id = store.save_state(learned.state)
    restored = store.load_state(state_id)
    projection = store.load_ontology_projection(state_id)
    warm_recall = _recall(restored, ("goal::ask",), tick=50)
    after_success = bridge.observe_recall_failure(
        warm_recall.state,
        tick=51,
        cue_tokens=("goal::ask",),
        context_tokens=("ctx_work",),
        cognitive_pressure=0.9,
        recall_result=warm_recall,
    )

    assert learned.stopped_reason == "validation_success"
    assert restored == learned.state
    assert restored["teacher_requests"][0]["cue_tokens"] == ["goal::ask"]
    assert restored["paradigms"][0]["pid"] == "p:discovered:skill_teacher_answer"
    assert restored["paradigm_stats"]
    assert restored["paradigm_observations"]
    assert memory_recall.dialogue_result is not None
    assert warm_recall.dialogue_result is not None
    assert warm_recall.dialogue_result.emitted_tokens == memory_recall.dialogue_result.emitted_tokens
    assert warm_recall.dialogue_result.emitted_tokens == ("teacher::answer",)
    assert after_success.teacher_request_result is None
    assert projection["paradigm_sa"][0]["pid"] == "p:discovered:skill_teacher_answer"
    assert projection["paradigm_observations"][0]["schema_id"] == "apv3_paradigm_observation/v1"
    assert "skill_teacher_answer|goal::ask" in projection["paradigm_stats"]
    assert "llm_policy" not in str(restored)
    assert "answer_table" not in str(restored)


def test_phase6_9_work_memory_teacher_request_survives_sqlite_warm_load(tmp_path: Path) -> None:
    state = APV3WorkMemoryRuntime().run_tick(
        _base_state(),
        WorkMemoryTickInput(tick=5, focus_tokens=("goal::resume",), pressure=0.92),
    ).state
    bridge = _bridge()
    failed_idle = bridge.run_work_memory_idle(state, tick=12, context_tokens=("ctx_work",))
    assert failed_idle.teacher_request_result is not None
    assert failed_idle.teacher_request_result.request is not None

    learned = bridge.run_teacher_response_iterations(
        failed_idle.state,
        request=failed_idle.teacher_request_result.request,
        reply_tokens=("continue::resume",),
        case_name="skill_resume_answer",
        expected_pid="p:discovered:skill_resume_answer",
        start_tick=20,
    )
    memory_resume = bridge.run_work_memory_idle(learned.state, tick=32, context_tokens=("ctx_work",))
    store = SQLiteRuntimeStore(tmp_path / "phase6_9_work_memory.sqlite")

    state_id = store.save_state(learned.state)
    restored = store.load_state(state_id)
    projection = store.load_ontology_projection(state_id)
    warm_resume = bridge.run_work_memory_idle(restored, tick=32, context_tokens=("ctx_work",))

    assert learned.stopped_reason == "validation_success"
    assert restored == learned.state
    assert restored["working_memory_items"][0]["sa_bundle"] == ["goal::resume"]
    assert restored["teacher_requests"][0]["cue_tokens"] == ["goal::resume"]
    assert any(item["sa_type"] == "work_memory_unfinished" for item in restored["state_field_items"])
    assert any(item["sa_type"] == "teacher_request" for item in restored["state_field_items"])
    assert memory_resume.work_memory_bridge_result is not None
    assert memory_resume.work_memory_bridge_result.recall_result is not None
    assert warm_resume.work_memory_bridge_result is not None
    assert warm_resume.work_memory_bridge_result.recall_result is not None
    assert warm_resume.work_memory_bridge_result.recall_result.dialogue_result is not None
    assert warm_resume.work_memory_bridge_result.recall_result.dialogue_result.emitted_tokens == ("continue::resume",)
    assert memory_resume.work_memory_bridge_result.recall_result.dialogue_result is not None
    assert (
        warm_resume.work_memory_bridge_result.recall_result.dialogue_result.emitted_tokens
        == memory_resume.work_memory_bridge_result.recall_result.dialogue_result.emitted_tokens
    )
    assert warm_resume.teacher_request_result is None
    assert projection["paradigm_sa"][0]["pid"] == "p:discovered:skill_resume_answer"
    assert "skill_resume_answer|goal::resume" in projection["paradigm_stats"]
