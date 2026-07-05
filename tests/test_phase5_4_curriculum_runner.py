from __future__ import annotations

from pathlib import Path

from apv3test.runtime import (
    APV3CurriculumRunner,
    CURRICULUM_TRACE_LABELS,
    CurriculumEpisode,
    CurriculumTeachingStep,
    CurriculumValidationCase,
    SQLiteRuntimeStore,
)


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


def _teaching_steps() -> tuple[CurriculumTeachingStep, ...]:
    return (
        CurriculumTeachingStep("skill_echo", ("echo",), ("echo",), ("ctx_dialogue",), "echo_imitation"),
        CurriculumTeachingStep("skill_greeting", ("你", "好"), ("我", "在"), ("ctx_dialogue",), "successor_prediction"),
        CurriculumTeachingStep("skill_greeting", ("你", "好"), ("我", "在"), ("ctx_dialogue",), "successor_prediction"),
        CurriculumTeachingStep("skill_idiom", ("三", "顾"), ("茅", "庐"), ("ctx_idiom",), "successor_prediction"),
        CurriculumTeachingStep("skill_idiom", ("三", "顾"), ("茅", "庐"), ("ctx_idiom",), "successor_prediction"),
        CurriculumTeachingStep(
            "skill_color_object",
            ("describe",),
            ("field::color", "percept::red", "field::object", "percept::apple"),
            ("ctx_visual",),
            "multi_reply_aggregation",
        ),
        CurriculumTeachingStep(
            "skill_color_object",
            ("describe",),
            ("field::color", "percept::blue", "field::object", "percept::cup"),
            ("ctx_visual",),
            "multi_reply_aggregation",
        ),
        CurriculumTeachingStep(
            "skill_color_object",
            ("describe",),
            ("field::color", "percept::green", "field::object", "percept::leaf"),
            ("ctx_visual",),
            "multi_reply_aggregation",
        ),
        CurriculumTeachingStep(
            "skill_color_object",
            ("describe",),
            ("field::color", "percept::yellow", "field::object", "percept::banana"),
            ("ctx_visual",),
            "focus_slot_filling",
        ),
        CurriculumTeachingStep(
            "skill_math_process",
            ("calc",),
            ("math::lhs", "1", "math::op", "+", "2", "math::eq", "3"),
            ("ctx_math",),
            "process_paradigm_binding",
        ),
        CurriculumTeachingStep(
            "skill_math_process",
            ("calc",),
            ("math::lhs", "2", "math::op", "+", "3", "math::eq", "5"),
            ("ctx_math",),
            "process_paradigm_binding",
        ),
        CurriculumTeachingStep(
            "skill_math_process",
            ("calc",),
            ("math::lhs", "4", "math::op", "+", "1", "math::eq", "5"),
            ("ctx_math",),
            "process_paradigm_binding",
        ),
    )


def _validation_cases(include_failures: bool = False) -> tuple[CurriculumValidationCase, ...]:
    cases = [
        CurriculumValidationCase(
            "success:greeting",
            ("你", "好"),
            ("ctx_dialogue",),
            ("我", "在"),
            expected_pid="p:discovered:skill_greeting",
        ),
        CurriculumValidationCase(
            "success:idiom",
            ("三", "顾"),
            ("ctx_idiom",),
            ("茅", "庐"),
            expected_pid="p:discovered:skill_idiom",
        ),
        CurriculumValidationCase(
            "success:color_object",
            ("describe",),
            ("ctx_visual",),
            ("field::color", "percept::yellow", "field::object", "percept::apple"),
            expected_pid="p:discovered:skill_color_object",
            focus_tokens=("percept::yellow", "percept::apple"),
            allow_current_focus=True,
        ),
        CurriculumValidationCase(
            "success:math_process",
            ("calc",),
            ("ctx_math",),
            ("math::lhs", "7", "math::op", "+", "2", "math::eq", "9"),
            expected_pid="p:discovered:skill_math_process",
            focus_tokens=("7", "2", "9"),
            allow_current_focus=True,
        ),
    ]
    if include_failures:
        cases.extend(
            [
                CurriculumValidationCase(
                    "failure:untrained_cue",
                    ("unknown",),
                    ("ctx_dialogue",),
                    ("我", "在"),
                    expected_pid="p:discovered:skill_greeting",
                ),
                CurriculumValidationCase(
                    "failure:slot_focus_expected",
                    ("describe",),
                    ("ctx_visual",),
                    ("field::color", "percept::yellow", "field::object", "percept::pear"),
                    expected_pid="p:discovered:skill_color_object",
                    focus_tokens=("percept::yellow", "percept::apple"),
                    allow_current_focus=True,
                ),
            ]
        )
    return tuple(cases)


def _episode(source_kind: str, include_failures: bool = False) -> CurriculumEpisode:
    return CurriculumEpisode(
        episode_id=f"phase5_4:{source_kind}",
        source_kind=source_kind,
        teaching_steps=_teaching_steps(),
        validation_cases=_validation_cases(include_failures=include_failures),
    )


def test_curriculum_runner_records_six_stage_teaching_and_success_examples() -> None:
    result = APV3CurriculumRunner().run(_base_state(), _episode("natural"))

    assert set(CURRICULUM_TRACE_LABELS) <= set(result.stage_counts)
    assert result.stage_counts["echo_imitation"] == 1
    assert result.stage_counts["successor_prediction"] == 4
    assert result.stage_counts["multi_reply_aggregation"] == 3
    assert result.stage_counts["process_paradigm_binding"] == 3
    assert result.stage_counts["focus_slot_filling"] == 1
    assert result.stage_counts["recall_only_validation"] == 4
    assert all(item.success for item in result.validation_results)
    assert result.validation_results[0].emitted_tokens == ("我", "在")
    assert result.validation_results[2].emitted_tokens[-1] == "percept::apple"


def test_curriculum_runner_reports_failure_examples_without_patch_rules() -> None:
    result = APV3CurriculumRunner().run(_base_state(), _episode("natural", include_failures=True))
    failures = {item.case_id: item for item in result.validation_results if not item.success}

    assert failures["failure:untrained_cue"].diagnosis.failure_kind == "bn_not_recalled"
    assert failures["failure:slot_focus_expected"].diagnosis.failure_kind == "slot_focus_overridden"
    assert failures["failure:slot_focus_expected"].emitted_tokens[-1] == "percept::apple"


def test_curriculum_natural_and_llm_standard_teaching_are_equivalent() -> None:
    runner = APV3CurriculumRunner()
    natural = runner.run(_base_state(), _episode("natural"))
    llm = runner.run(_base_state(), _episode("llm_standard_teacher"))

    assert [item.emitted_tokens for item in natural.validation_results] == [
        item.emitted_tokens for item in llm.validation_results
    ]
    assert [item.focus_pid for item in natural.validation_results] == [item.focus_pid for item in llm.validation_results]
    assert "llm_policy" not in str(llm.state)


def test_curriculum_state_survives_sqlite_restore_and_validates_again(tmp_path: Path) -> None:
    runner = APV3CurriculumRunner()
    result = runner.run(_base_state(), _episode("natural"))
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")
    restored = store.load_state(store.save_state(result.state))
    validation_only = CurriculumEpisode(
        episode_id="phase5_4:restore:validation",
        source_kind="natural",
        teaching_steps=(),
        validation_cases=_validation_cases(),
    )

    restored_result = runner.run(restored, validation_only, start_tick=1000)

    assert all(item.success for item in restored_result.validation_results)
    assert restored_result.validation_results[3].emitted_tokens == (
        "math::lhs",
        "7",
        "math::op",
        "+",
        "2",
        "math::eq",
        "9",
    )


def test_curriculum_stage_labels_are_teacher_trace_not_runtime_schema() -> None:
    episode = CurriculumEpisode(
        episode_id="trace_only",
        source_kind="natural",
        teaching_steps=(CurriculumTeachingStep("trace_case", ("x",), ("y",), (), "teacher_custom_trace"),),
        validation_cases=(),
    )

    result = APV3CurriculumRunner().run(_base_state(), episode)

    assert result.stage_counts["teacher_custom_trace"] == 1
    assert result.validation_results == ()
