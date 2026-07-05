from __future__ import annotations

from apv3test.runtime import IncrementalTickInput, IncrementalTickRuntime


def _base_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "ctx_a": {"vector": [1.0, 0.0], "support": 4.0, "promoted": True},
                "ctx_b": {"vector": [0.0, 1.0], "support": 4.0, "promoted": True},
            }
        },
        "transitions": [],
        "paradigms": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def _teach(
    tick: int,
    case_name: str,
    reply_tokens: tuple[str, ...],
    context_tokens: tuple[str, ...],
    *,
    reward_delta: float = 1.0,
    punish_delta: float = 0.0,
) -> IncrementalTickInput:
    return IncrementalTickInput(
        tick=tick,
        case_name=case_name,
        cue_tokens=("answer",),
        reply_tokens=reply_tokens,
        context_tokens=context_tokens,
        commit_observation=True,
        reward_delta=reward_delta,
        punish_delta=punish_delta,
    )


def _recall(tick: int, context_tokens: tuple[str, ...]) -> IncrementalTickInput:
    return IncrementalTickInput(
        tick=tick,
        cue_tokens=("answer",),
        context_tokens=context_tokens,
        emit_reply=True,
        commit_after_draft=True,
        grasp=1.3,
        demand_slow=0.1,
    )


def test_phase5_6_same_cue_different_context_selects_different_skill_without_keyword_route() -> None:
    runtime = IncrementalTickRuntime()
    state = _base_state()
    for tick in (1, 2):
        state = runtime.run_tick(state, _teach(tick, "skill_a", ("reply_a",), ("ctx_a",))).state
    for tick in (3, 4):
        state = runtime.run_tick(state, _teach(tick, "skill_b", ("reply_b",), ("ctx_b",))).state

    result_a = runtime.run_tick(state, _recall(20, ("ctx_a",)))
    result_b = runtime.run_tick(state, _recall(40, ("ctx_b",)))

    assert result_a.recall_result is not None
    assert result_b.recall_result is not None
    assert result_a.recall_result.focus is not None
    assert result_b.recall_result.focus is not None
    assert result_a.recall_result.focus.pid == "p:discovered:skill_a"
    assert result_b.recall_result.focus.pid == "p:discovered:skill_b"
    assert result_a.dialogue_result is not None
    assert result_b.dialogue_result is not None
    assert result_a.dialogue_result.emitted_tokens == ("reply_a",)
    assert result_b.dialogue_result.emitted_tokens == ("reply_b",)


def test_phase5_6_punished_wrong_paradigm_leaves_attention_competition() -> None:
    runtime = IncrementalTickRuntime()
    state = _base_state()
    for tick in (1, 2):
        state = runtime.run_tick(state, _teach(tick, "skill_wrong", ("wrong_reply",), ("ctx_a",))).state
    state = runtime.run_tick(
        state,
        _teach(3, "skill_wrong", ("wrong_reply",), ("ctx_a",), reward_delta=0.0, punish_delta=12.0),
    ).state
    for tick in (4, 5):
        state = runtime.run_tick(state, _teach(tick, "skill_right", ("right_reply",), ("ctx_a",))).state

    wrong = next(item for item in state["paradigms"] if item["pid"] == "p:discovered:skill_wrong")
    result = runtime.run_tick(state, _recall(20, ("ctx_a",)))

    assert wrong["exposed"] is False
    assert result.recall_result is not None
    assert result.recall_result.focus is not None
    assert result.recall_result.focus.pid == "p:discovered:skill_right"
    assert result.dialogue_result is not None
    assert result.dialogue_result.emitted_tokens == ("right_reply",)
    assert all(item.pid != "p:discovered:skill_wrong" for item in result.recall_result.bn_candidates)


def test_phase5_6_llm_and_natural_conflict_training_have_same_student_behavior() -> None:
    def run(source_kind: str):
        runtime = IncrementalTickRuntime()
        state = _base_state()
        for tick in (1, 2):
            tick_input = _teach(tick, "skill_a", ("reply_a",), ("ctx_a",))
            tick_input = IncrementalTickInput(**{**tick_input.__dict__, "source_kind": source_kind})
            state = runtime.run_tick(state, tick_input).state
        return runtime.run_tick(state, _recall(20, ("ctx_a",)))

    natural = run("natural")
    llm = run("llm_standard_teacher")

    assert natural.dialogue_result is not None
    assert llm.dialogue_result is not None
    assert natural.dialogue_result.emitted_tokens == llm.dialogue_result.emitted_tokens == ("reply_a",)
    assert "llm_policy" not in str(llm.state)
