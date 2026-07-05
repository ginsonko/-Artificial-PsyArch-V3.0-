from __future__ import annotations

from apv3test.runtime import (
    APV3CurriculumRemediationLoop,
    APV3WorkMemoryAttentionBridge,
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
                "ctx_math": {"vector": [1.0, 0.0, 0.0], "support": 4.0, "promoted": True},
                "ctx_dialogue": {"vector": [0.0, 1.0, 0.0], "support": 4.0, "promoted": True},
                "ctx_work": {"vector": [0.5, 0.5, 0.0], "support": 4.0, "promoted": True},
                "goal::resume": {"vector": [0.8, 0.2, 0.0], "support": 4.0, "promoted": True},
                "goal::urgent": {"vector": [0.9, 0.1, 0.0], "support": 4.0, "promoted": True},
                "goal::minor": {"vector": [0.1, 0.9, 0.0], "support": 4.0, "promoted": True},
            }
        },
        "transitions": [],
        "paradigms": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def _teach_skill(
    state: dict,
    *,
    case_name: str,
    cue_tokens: tuple[str, ...],
    reply_tokens: tuple[str, ...],
    context_tokens: tuple[str, ...],
    start_tick: int,
    reward_delta: float = 1.0,
    punish_delta: float = 0.0,
) -> dict:
    runtime = IncrementalTickRuntime()
    for offset in (0, 1):
        state = runtime.run_tick(
            state,
            IncrementalTickInput(
                tick=start_tick + offset,
                case_name=case_name,
                cue_tokens=cue_tokens,
                reply_tokens=reply_tokens,
                context_tokens=context_tokens,
                commit_observation=True,
                reward_delta=reward_delta,
                punish_delta=punish_delta,
            ),
        ).state
    return state


def _store_work_memory(state: dict, bundle: tuple[str, ...], *, tick: int, pressure: float) -> dict:
    return APV3WorkMemoryRuntime().run_tick(
        state,
        WorkMemoryTickInput(tick=tick, focus_tokens=bundle, pressure=pressure),
    ).state


def test_phase5_9_work_memory_recovery_respects_multiskill_context_competition() -> None:
    state = _base_state()
    state = _teach_skill(
        state,
        case_name="skill_resume_math",
        cue_tokens=("goal::resume",),
        reply_tokens=("continue::math",),
        context_tokens=("ctx_math",),
        start_tick=1,
    )
    state = _teach_skill(
        state,
        case_name="skill_resume_dialogue",
        cue_tokens=("goal::resume",),
        reply_tokens=("continue::dialogue",),
        context_tokens=("ctx_dialogue",),
        start_tick=10,
    )
    state = _store_work_memory(state, ("goal::resume",), tick=30, pressure=0.9)

    math = APV3WorkMemoryAttentionBridge().run_idle_recall(state, tick=40, context_tokens=("ctx_math",))
    dialogue = APV3WorkMemoryAttentionBridge().run_idle_recall(state, tick=50, context_tokens=("ctx_dialogue",))

    assert math.recall_result is not None
    assert dialogue.recall_result is not None
    assert math.recall_result.dialogue_result is not None
    assert dialogue.recall_result.dialogue_result is not None
    assert math.recall_result.recall_result.focus.pid == "p:discovered:skill_resume_math"
    assert dialogue.recall_result.recall_result.focus.pid == "p:discovered:skill_resume_dialogue"
    assert math.recall_result.dialogue_result.emitted_tokens == ("continue::math",)
    assert dialogue.recall_result.dialogue_result.emitted_tokens == ("continue::dialogue",)


def test_phase5_9_work_memory_failure_can_be_remediated_then_recalled() -> None:
    state = _store_work_memory(_base_state(), ("goal::resume",), tick=10, pressure=0.9)
    before = APV3WorkMemoryAttentionBridge().run_idle_recall(state, tick=20, context_tokens=("ctx_work",))

    assert before.work_memory_result.recalled_item is not None
    assert before.recall_result is not None
    assert before.recall_result.dialogue_result is None

    episode = CurriculumEpisode(
        episode_id="phase5_9:wm_remediate",
        source_kind="natural",
        teaching_steps=(),
        validation_cases=(
            CurriculumValidationCase(
                "needs:resume_work",
                ("goal::resume",),
                ("ctx_work",),
                ("continue::work",),
                expected_pid="p:discovered:skill_resume_work",
            ),
        ),
    )
    remediated = APV3CurriculumRemediationLoop().run(
        before.state,
        episode,
        start_tick=21,
        remediation_start_tick=25,
    )
    after = APV3WorkMemoryAttentionBridge().run_idle_recall(
        remediated.final.state,
        tick=40,
        context_tokens=("ctx_work",),
    )

    assert remediated.initial.validation_results[0].success is False
    assert remediated.final.validation_results[0].success is True
    assert after.recall_result is not None
    assert after.recall_result.dialogue_result is not None
    assert after.recall_result.dialogue_result.emitted_tokens == ("continue::work",)
    assert "answer_table" not in str(after.state).lower()


def test_phase5_9_reward_punish_refinement_applies_after_work_memory_recovery() -> None:
    state = _base_state()
    state = _teach_skill(
        state,
        case_name="skill_wrong_resume",
        cue_tokens=("goal::resume",),
        reply_tokens=("wrong::resume",),
        context_tokens=("ctx_work",),
        start_tick=1,
    )
    state = IncrementalTickRuntime().run_tick(
        state,
        IncrementalTickInput(
            tick=5,
            case_name="skill_wrong_resume",
            cue_tokens=("goal::resume",),
            reply_tokens=("wrong::resume",),
            context_tokens=("ctx_work",),
            commit_observation=True,
            punish_delta=12.0,
        ),
    ).state
    state = _teach_skill(
        state,
        case_name="skill_right_resume",
        cue_tokens=("goal::resume",),
        reply_tokens=("right::resume",),
        context_tokens=("ctx_work",),
        start_tick=10,
    )
    state = _store_work_memory(state, ("goal::resume",), tick=30, pressure=0.9)

    result = APV3WorkMemoryAttentionBridge().run_idle_recall(state, tick=40, context_tokens=("ctx_work",))
    wrong = next(item for item in result.state["paradigms"] if item["pid"] == "p:discovered:skill_wrong_resume")

    assert wrong["exposed"] is False
    assert result.recall_result is not None
    assert result.recall_result.recall_result.focus.pid == "p:discovered:skill_right_resume"
    assert result.recall_result.dialogue_result.emitted_tokens == ("right::resume",)


def test_phase5_9_multiple_unfinished_tasks_recall_high_pressure_one_first() -> None:
    state = _base_state()
    state = _teach_skill(
        state,
        case_name="skill_urgent",
        cue_tokens=("goal::urgent",),
        reply_tokens=("do::urgent",),
        context_tokens=("ctx_work",),
        start_tick=1,
    )
    state = _teach_skill(
        state,
        case_name="skill_minor",
        cue_tokens=("goal::minor",),
        reply_tokens=("do::minor",),
        context_tokens=("ctx_work",),
        start_tick=10,
    )
    state = _store_work_memory(state, ("goal::minor",), tick=30, pressure=0.25)
    state = _store_work_memory(state, ("goal::urgent",), tick=31, pressure=0.95)

    result = APV3WorkMemoryAttentionBridge().run_idle_recall(state, tick=40, context_tokens=("ctx_work",))

    assert result.work_memory_result.recalled_item is not None
    assert result.work_memory_result.recalled_item.sa_bundle == ("goal::urgent",)
    assert result.recall_result is not None
    assert result.recall_result.dialogue_result.emitted_tokens == ("do::urgent",)
