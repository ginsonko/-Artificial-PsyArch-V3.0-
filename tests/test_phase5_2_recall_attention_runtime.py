from __future__ import annotations

from pathlib import Path

from apv3test.runtime import (
    IncrementalTickInput,
    IncrementalTickRuntime,
    ParadigmRecallAttention,
    SQLiteRuntimeStore,
)


def _base_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "ctx_dialogue": {"vector": [1.0, 0.0], "support": 4.0, "promoted": True},
                "ctx_dialogue_near": {"vector": [0.98, 0.02], "support": 4.0, "promoted": True},
                "ctx_idiom": {"vector": [0.0, 1.0], "support": 4.0, "promoted": True},
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
    cue: tuple[str, ...],
    reply: tuple[str, ...],
    context: tuple[str, ...],
    *,
    source_kind: str = "natural",
) -> IncrementalTickInput:
    return IncrementalTickInput(
        tick=tick,
        case_name=case_name,
        cue_tokens=cue,
        reply_tokens=reply,
        context_tokens=context,
        source_kind=source_kind,
        teacher_stage="successor_prediction",
        commit_observation=True,
        reward_delta=1.0,
    )


def _recall(
    tick: int,
    cue: tuple[str, ...],
    context: tuple[str, ...],
) -> IncrementalTickInput:
    return IncrementalTickInput(
        tick=tick,
        cue_tokens=cue,
        context_tokens=context,
        emit_reply=True,
        commit_after_draft=True,
        grasp=1.2,
        demand_slow=0.1,
    )


def test_bn_cn_attention_recall_emits_reply_without_teacher_reply_tokens() -> None:
    runtime = IncrementalTickRuntime()
    state = _base_state()
    state = runtime.run_tick(state, _teach(1, "hello_skill", ("你", "好"), ("我", "在"), ("ctx_dialogue",))).state
    state = runtime.run_tick(state, _teach(2, "hello_skill", ("你", "好"), ("我", "在"), ("ctx_dialogue",))).state

    result = runtime.run_tick(state, _recall(10, ("你", "好"), ("ctx_dialogue_near",)))

    assert result.recall_result is not None
    assert result.recall_result.focus is not None
    assert result.recall_result.focus.pid == "p:discovered:hello_skill"
    assert result.recall_result.focus.cn is not None
    assert result.recall_result.focus.cn.successor_tokens == ("我", "在")
    assert result.dialogue_result is not None
    assert result.dialogue_result.emitted_tokens == ("我", "在")
    assert result.dialogue_result.committed_text == "我在"


def test_attention_focus_selects_matching_paradigm_among_competing_skills() -> None:
    runtime = IncrementalTickRuntime()
    state = _base_state()
    for tick, case_name, cue, reply, context in (
        (1, "hello_skill", ("你", "好"), ("我", "在"), ("ctx_dialogue",)),
        (2, "hello_skill", ("你", "好"), ("我", "在"), ("ctx_dialogue",)),
        (3, "idiom_skill", ("三", "顾"), ("茅", "庐"), ("ctx_idiom",)),
        (4, "idiom_skill", ("三", "顾"), ("茅", "庐"), ("ctx_idiom",)),
    ):
        state = runtime.run_tick(state, _teach(tick, case_name, cue, reply, context)).state

    recall = ParadigmRecallAttention().recall(
        state,
        cue_tokens=("三", "顾"),
        context_tokens=("ctx_idiom",),
    )

    assert recall.focus is not None
    assert recall.focus.pid == "p:discovered:idiom_skill"
    assert recall.focus.cn is not None
    assert recall.focus.cn.successor_tokens == ("茅", "庐")
    assert recall.bn_candidates[0].pid == "p:discovered:idiom_skill"


def test_cn_can_read_explicit_successor_edge_as_supporting_evidence() -> None:
    runtime = IncrementalTickRuntime()
    state = _base_state()
    state = runtime.run_tick(state, _teach(1, "hello_skill", ("你", "好"), ("我", "在"), ("ctx_dialogue",))).state
    state = runtime.run_tick(state, _teach(2, "hello_skill", ("你", "好"), ("我", "在"), ("ctx_dialogue",))).state
    state["transitions"].append({"source": "你好", "target": "我在", "support": 8.0})

    recall = ParadigmRecallAttention().recall(
        state,
        cue_tokens=("你", "好"),
        context_tokens=("ctx_dialogue",),
    )

    assert recall.focus is not None
    assert recall.focus.cn is not None
    assert recall.focus.cn.transition_score > recall.focus.cn.observation_score
    assert recall.focus.cn.source == "explicit_transition"


def test_cn_aggregates_shared_token_successor_instead_of_replaying_one_full_reply() -> None:
    runtime = IncrementalTickRuntime()
    state = _base_state()
    for tick, head in enumerate(("a", "b", "c", "d", "e"), start=1):
        state = runtime.run_tick(
            state,
            _teach(
                tick,
                "shared_tail_skill",
                ("stem",),
                (head, "shared_tail"),
                ("ctx_dialogue",),
            ),
        ).state

    result = runtime.run_tick(
        state,
        IncrementalTickInput(
            tick=20,
            cue_tokens=("stem",),
            focus_tokens=("z",),
            context_tokens=("ctx_dialogue",),
            emit_reply=True,
            commit_after_draft=True,
            grasp=1.2,
            demand_slow=0.1,
        ),
    )

    assert result.recall_result is not None
    assert result.recall_result.focus is not None
    assert result.recall_result.focus.cn is not None
    assert result.recall_result.focus.cn.successor_tokens == ("shared_tail",)
    assert result.dialogue_result is not None
    assert result.dialogue_result.emitted_tokens == ("z", "shared_tail")
    assert result.dialogue_result.emitted_tokens not in {
        ("a", "shared_tail"),
        ("b", "shared_tail"),
        ("c", "shared_tail"),
        ("d", "shared_tail"),
        ("e", "shared_tail"),
    }


def test_recall_without_exposed_paradigm_does_not_emit_or_commit() -> None:
    runtime = IncrementalTickRuntime()
    state = _base_state()

    result = runtime.run_tick(state, _recall(5, ("未", "学"), ("ctx_dialogue",)))

    assert result.recall_result is not None
    assert result.recall_result.focus is None
    assert result.dialogue_result is None
    assert "draft_runtime" not in result.state


def test_natural_and_llm_taught_skills_recall_with_equivalent_behavior() -> None:
    runtime = IncrementalTickRuntime()
    natural_state = _base_state()
    llm_state = _base_state()
    for tick in (1, 2):
        natural_state = runtime.run_tick(
            natural_state,
            _teach(tick, "hello_skill", ("你", "好"), ("我", "在"), ("ctx_dialogue",), source_kind="natural"),
        ).state
        llm_state = runtime.run_tick(
            llm_state,
            _teach(
                tick,
                "hello_skill",
                ("你", "好"),
                ("我", "在"),
                ("ctx_dialogue",),
                source_kind="llm_standard_teacher",
            ),
        ).state

    natural = runtime.run_tick(natural_state, _recall(10, ("你", "好"), ("ctx_dialogue",)))
    llm = runtime.run_tick(llm_state, _recall(10, ("你", "好"), ("ctx_dialogue",)))

    assert natural.dialogue_result is not None
    assert llm.dialogue_result is not None
    assert natural.dialogue_result.emitted_tokens == llm.dialogue_result.emitted_tokens
    assert natural.dialogue_result.committed_text == llm.dialogue_result.committed_text
    assert natural.recall_result is not None and llm.recall_result is not None
    assert natural.recall_result.focus is not None and llm.recall_result.focus is not None
    assert natural.recall_result.focus.pid == llm.recall_result.focus.pid
    assert "llm_policy" not in str(llm.state)


def test_phase5_2_recall_state_survives_sqlite_restore(tmp_path: Path) -> None:
    runtime = IncrementalTickRuntime()
    state = _base_state()
    state = runtime.run_tick(state, _teach(1, "hello_skill", ("你", "好"), ("我", "在"), ("ctx_dialogue",))).state
    state = runtime.run_tick(state, _teach(2, "hello_skill", ("你", "好"), ("我", "在"), ("ctx_dialogue",))).state
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")
    restored = store.load_state(store.save_state(state))

    result = runtime.run_tick(restored, _recall(20, ("你", "好"), ("ctx_dialogue",)))

    assert result.dialogue_result is not None
    assert result.dialogue_result.committed_text == "我在"
    assert result.recall_result is not None
    assert result.recall_result.focus is not None
    assert result.recall_result.focus.pid == "p:discovered:hello_skill"
