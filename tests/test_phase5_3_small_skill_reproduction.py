from __future__ import annotations

from pathlib import Path

from apv3test.runtime import IncrementalTickInput, IncrementalTickRuntime, SQLiteRuntimeStore


def _base_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "ctx_dialogue": {"vector": [1.0, 0.0, 0.0], "support": 4.0, "promoted": True},
                "ctx_idiom": {"vector": [0.0, 1.0, 0.0], "support": 4.0, "promoted": True},
                "ctx_visual": {"vector": [0.0, 0.0, 1.0], "support": 4.0, "promoted": True},
                "ctx_math": {"vector": [0.6, 0.6, 0.0], "support": 4.0, "promoted": True},
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
    source_kind: str,
    stage: str,
) -> IncrementalTickInput:
    return IncrementalTickInput(
        tick=tick,
        case_name=case_name,
        cue_tokens=cue,
        reply_tokens=reply,
        context_tokens=context,
        source_kind=source_kind,
        teacher_stage=stage,
        commit_observation=True,
        reward_delta=1.0,
    )


def _recall(
    tick: int,
    cue: tuple[str, ...],
    context: tuple[str, ...],
    *,
    focus: tuple[str, ...] = (),
    pool: tuple[str, ...] = (),
) -> IncrementalTickInput:
    return IncrementalTickInput(
        tick=tick,
        cue_tokens=cue,
        focus_tokens=focus,
        candidate_pool=pool,
        context_tokens=context,
        emit_reply=True,
        commit_after_draft=True,
        grasp=1.3,
        demand_slow=0.1,
    )


def _run_examples(state: dict, source_kind: str, start_tick: int = 1) -> dict:
    runtime = IncrementalTickRuntime()
    tick = start_tick
    examples = [
        ("skill_greeting", ("你", "好"), ("我", "在"), ("ctx_dialogue",), "successor_prediction"),
        ("skill_greeting", ("你", "好"), ("我", "在"), ("ctx_dialogue",), "successor_prediction"),
        ("skill_idiom", ("三", "顾"), ("茅", "庐"), ("ctx_idiom",), "successor_prediction"),
        ("skill_idiom", ("三", "顾"), ("茅", "庐"), ("ctx_idiom",), "successor_prediction"),
        (
            "skill_color_object",
            ("describe",),
            ("field::color", "percept::red", "field::object", "percept::apple"),
            ("ctx_visual",),
            "multi_reply_aggregation",
        ),
        (
            "skill_color_object",
            ("describe",),
            ("field::color", "percept::blue", "field::object", "percept::cup"),
            ("ctx_visual",),
            "multi_reply_aggregation",
        ),
        (
            "skill_color_object",
            ("describe",),
            ("field::color", "percept::green", "field::object", "percept::leaf"),
            ("ctx_visual",),
            "multi_reply_aggregation",
        ),
        (
            "skill_color_object",
            ("describe",),
            ("field::color", "percept::yellow", "field::object", "percept::banana"),
            ("ctx_visual",),
            "multi_reply_aggregation",
        ),
        (
            "skill_math_process",
            ("calc",),
            ("math::lhs", "1", "math::op", "+", "2", "math::eq", "3"),
            ("ctx_math",),
            "process_paradigm_binding",
        ),
        (
            "skill_math_process",
            ("calc",),
            ("math::lhs", "2", "math::op", "+", "3", "math::eq", "5"),
            ("ctx_math",),
            "process_paradigm_binding",
        ),
        (
            "skill_math_process",
            ("calc",),
            ("math::lhs", "4", "math::op", "+", "1", "math::eq", "5"),
            ("ctx_math",),
            "process_paradigm_binding",
        ),
    ]
    for case_name, cue, reply, context, stage in examples:
        state = runtime.run_tick(
            state,
            _teach(tick, case_name, cue, reply, context, source_kind=source_kind, stage=stage),
        ).state
        tick += 1
    return state


def _recall_suite(state: dict, start_tick: int = 100) -> dict[str, tuple[str, ...]]:
    runtime = IncrementalTickRuntime()
    cases = {
        "greeting": _recall(start_tick, ("你", "好"), ("ctx_dialogue",)),
        "idiom": _recall(start_tick + 10, ("三", "顾"), ("ctx_idiom",)),
        "color_object": _recall(
            start_tick + 20,
            ("describe",),
            ("ctx_visual",),
            focus=("percept::yellow", "percept::apple"),
            pool=("percept::yellow", "percept::apple"),
        ),
        "math_process": _recall(
            start_tick + 30,
            ("calc",),
            ("ctx_math",),
            focus=("7", "2", "9"),
            pool=("7", "2", "9"),
        ),
    }
    outputs: dict[str, tuple[str, ...]] = {}
    for name, tick_input in cases.items():
        result = runtime.run_tick(state, tick_input)
        assert result.recall_result is not None
        assert result.recall_result.focus is not None
        assert result.dialogue_result is not None
        outputs[name] = result.dialogue_result.emitted_tokens
    return outputs


def test_phase5_3_natural_teaching_reproduces_small_skill_batch_without_reply_tokens() -> None:
    state = _run_examples(_base_state(), "natural")

    outputs = _recall_suite(state)

    assert outputs["greeting"] == ("我", "在")
    assert outputs["idiom"] == ("茅", "庐")
    assert outputs["color_object"] == ("field::color", "percept::yellow", "field::object", "percept::apple")
    assert outputs["math_process"] == ("math::lhs", "7", "math::op", "+", "2", "math::eq", "9")


def test_phase5_3_llm_standard_teaching_is_equivalent_to_natural_teaching() -> None:
    natural_state = _run_examples(_base_state(), "natural")
    llm_state = _run_examples(_base_state(), "llm_standard_teacher")

    natural_outputs = _recall_suite(natural_state)
    llm_outputs = _recall_suite(llm_state)

    assert natural_outputs == llm_outputs
    assert "llm_policy" not in str(llm_state)
    assert [item["pid"] for item in natural_state["paradigms"]] == [item["pid"] for item in llm_state["paradigms"]]


def test_phase5_3_attention_selects_color_or_math_by_cue_and_context_not_skill_route() -> None:
    state = _run_examples(_base_state(), "natural")
    runtime = IncrementalTickRuntime()

    visual = runtime.run_tick(
        state,
        _recall(
            200,
            ("describe",),
            ("ctx_visual",),
            focus=("percept::yellow", "percept::apple"),
            pool=("percept::yellow", "percept::apple"),
        ),
    )
    math = runtime.run_tick(
        state,
        _recall(210, ("calc",), ("ctx_math",), focus=("7", "2", "9"), pool=("7", "2", "9")),
    )

    assert visual.recall_result is not None and visual.recall_result.focus is not None
    assert math.recall_result is not None and math.recall_result.focus is not None
    assert visual.recall_result.focus.pid == "p:discovered:skill_color_object"
    assert math.recall_result.focus.pid == "p:discovered:skill_math_process"


def test_phase5_3_sqlite_restore_preserves_small_skill_recall(tmp_path: Path) -> None:
    state = _run_examples(_base_state(), "natural")
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")
    restored = store.load_state(store.save_state(state))

    outputs = _recall_suite(restored)

    assert outputs["greeting"] == ("我", "在")
    assert outputs["color_object"][-1] == "percept::apple"
    assert outputs["math_process"] == ("math::lhs", "7", "math::op", "+", "2", "math::eq", "9")


def test_phase5_3_failure_probe_reports_no_output_for_untrained_cue_without_patch_rules() -> None:
    state = _run_examples(_base_state(), "natural")
    runtime = IncrementalTickRuntime()

    result = runtime.run_tick(state, _recall(300, ("unknown",), ("ctx_dialogue",)))

    assert result.recall_result is not None
    assert result.recall_result.focus is None
    assert result.dialogue_result is None
