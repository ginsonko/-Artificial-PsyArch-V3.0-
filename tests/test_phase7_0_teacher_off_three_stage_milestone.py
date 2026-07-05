from __future__ import annotations

from apv3test.runtime import IncrementalTickInput, IncrementalTickRuntime


NI = "\u4f60"
HAO = "\u597d"
WO = "\u6211"
ZAI = "\u5728"
SAN = "\u4e09"
GU = "\u987e"
MAO = "\u8305"
LU = "\u5e90"
CAO = "\u8349"
ZHI = "\u4e4b"
ZHONG = "\u4e2d"


def _base_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "ctx_dialogue": {"vector": [1.0, 0.0], "support": 4.0, "promoted": True},
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
    *,
    case_name: str,
    cue_tokens: tuple[str, ...],
    reply_tokens: tuple[str, ...],
    context_tokens: tuple[str, ...],
) -> IncrementalTickInput:
    return IncrementalTickInput(
        tick=tick,
        case_name=case_name,
        cue_tokens=cue_tokens,
        reply_tokens=reply_tokens,
        context_tokens=context_tokens,
        source_kind="natural",
        teacher_stage="",
        commit_observation=True,
        reward_delta=1.0,
    )


def _teacher_off_recall(
    tick: int,
    *,
    cue_tokens: tuple[str, ...],
    context_tokens: tuple[str, ...],
) -> IncrementalTickInput:
    recall = IncrementalTickInput(
        tick=tick,
        cue_tokens=cue_tokens,
        context_tokens=context_tokens,
        emit_reply=True,
        commit_after_draft=True,
        grasp=1.2,
        demand_slow=0.1,
    )
    assert recall.reply_tokens == ()
    assert recall.focus_tokens == ()
    assert recall.candidate_pool == ()
    return recall


def _run_training(teaching_steps: tuple[IncrementalTickInput, ...]) -> dict:
    runtime = IncrementalTickRuntime()
    state = _base_state()
    for step in teaching_steps:
        state = runtime.run_tick(state, step).state
    return state


def test_phase7_0_teacher_off_echo_recall_no_prefilled_pool() -> None:
    state = _run_training(
        tuple(
            _teach(
                tick,
                case_name="phase7_echo",
                cue_tokens=(NI, HAO),
                reply_tokens=(NI, HAO),
                context_tokens=("ctx_dialogue",),
            )
            for tick in range(1, 51)
        )
    )

    result = IncrementalTickRuntime().run_tick(
        state,
        _teacher_off_recall(100, cue_tokens=(NI, HAO), context_tokens=("ctx_dialogue",)),
    )

    assert result.recall_result is not None
    assert result.recall_result.focus is not None
    assert result.recall_result.focus.pid == "p:discovered:phase7_echo"
    assert result.recall_result.focus.cn is not None
    assert result.recall_result.focus.cn.successor_tokens == (NI, HAO)
    assert result.dialogue_result is not None
    assert result.dialogue_result.emitted_tokens == (NI, HAO)


def test_phase7_0_teacher_off_successor_recall_no_prefilled_pool() -> None:
    state = _run_training(
        tuple(
            _teach(
                tick,
                case_name="phase7_successor",
                cue_tokens=(NI, HAO),
                reply_tokens=(WO, ZAI),
                context_tokens=("ctx_dialogue",),
            )
            for tick in range(1, 51)
        )
    )

    result = IncrementalTickRuntime().run_tick(
        state,
        _teacher_off_recall(100, cue_tokens=(NI, HAO), context_tokens=("ctx_dialogue",)),
    )

    assert result.recall_result is not None
    assert result.recall_result.focus is not None
    assert result.recall_result.focus.pid == "p:discovered:phase7_successor"
    assert result.recall_result.focus.cn is not None
    assert result.recall_result.focus.cn.successor_tokens == (WO, ZAI)
    assert result.dialogue_result is not None
    assert result.dialogue_result.emitted_tokens == (WO, ZAI)


def test_phase7_0_teacher_off_multi_reply_exposes_shared_cn_boundary() -> None:
    state = _run_training(
        tuple(
            _teach(
                tick,
                case_name="phase7_multi_reply",
                cue_tokens=(SAN, GU),
                reply_tokens=(MAO, LU),
                context_tokens=("ctx_idiom",),
            )
            for tick in range(1, 31)
        )
        + tuple(
            _teach(
                tick,
                case_name="phase7_multi_reply",
                cue_tokens=(SAN, GU),
                reply_tokens=(CAO, LU, ZHI, ZHONG),
                context_tokens=("ctx_idiom",),
            )
            for tick in range(31, 61)
        )
    )

    result = IncrementalTickRuntime().run_tick(
        state,
        _teacher_off_recall(100, cue_tokens=(SAN, GU), context_tokens=("ctx_idiom",)),
    )

    assert result.recall_result is not None
    assert result.recall_result.focus is not None
    assert result.recall_result.focus.pid == "p:discovered:phase7_multi_reply"
    assert result.recall_result.focus.cn is not None
    assert result.recall_result.focus.cn.successor_tokens == (LU,)
    assert result.dialogue_result is not None
    assert result.dialogue_result.emitted_tokens not in {
        (MAO, LU),
        (CAO, LU, ZHI, ZHONG),
    }
    assert set(result.dialogue_result.emitted_tokens) == {LU}
