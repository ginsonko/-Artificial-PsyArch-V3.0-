from __future__ import annotations

from apv3test.runtime import (
    APV3CurriculumRemediationLoop,
    APV3CurriculumRemediationPlanner,
    CurriculumEpisode,
    CurriculumTeachingStep,
    CurriculumValidationCase,
)


def _base_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "ctx_dialogue": {"vector": [1.0, 0.0], "support": 4.0, "promoted": True},
                "ctx_visual": {"vector": [0.0, 1.0], "support": 4.0, "promoted": True},
            }
        },
        "transitions": [],
        "paradigms": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def _missing_greeting_episode(source_kind: str) -> CurriculumEpisode:
    return CurriculumEpisode(
        episode_id=f"phase5_5_missing_greeting:{source_kind}",
        source_kind=source_kind,
        teaching_steps=(),
        validation_cases=(
            CurriculumValidationCase(
                "needs:greeting",
                ("你", "好"),
                ("ctx_dialogue",),
                ("我", "在"),
                expected_pid="p:discovered:skill_greeting",
            ),
        ),
    )


def test_phase5_5_remediation_loop_learns_missing_bn_without_answer_patch() -> None:
    result = APV3CurriculumRemediationLoop().run(_base_state(), _missing_greeting_episode("natural"))

    assert result.initial.validation_results[0].success is False
    assert result.initial.validation_results[0].diagnosis.failure_kind == "bn_not_recalled"
    assert len(result.suggestions) == 1
    assert result.suggestions[0].teaching_steps
    assert result.suggestions[0].teaching_steps[0].stage == "remediate"
    assert result.suggestions[0].failure_kind == "bn_not_recalled"
    assert result.suggestions[0].evidence_repeats == 2
    assert result.suggestions[0].remediation_intensity == 1.0
    assert result.final.validation_results[0].success is True
    assert result.final.validation_results[0].emitted_tokens == ("我", "在")
    assert "llm_policy" not in str(result.final.state)


def test_phase5_5_natural_and_llm_standard_remediation_are_evidence_equivalent() -> None:
    loop = APV3CurriculumRemediationLoop()
    natural = loop.run(_base_state(), _missing_greeting_episode("natural"))
    llm = loop.run(_base_state(), _missing_greeting_episode("llm_standard_teacher"))

    assert [item.emitted_tokens for item in natural.final.validation_results] == [
        item.emitted_tokens for item in llm.final.validation_results
    ]
    assert [item.focus_pid for item in natural.final.validation_results] == [
        item.focus_pid for item in llm.final.validation_results
    ]
    assert [step.reply_tokens for step in natural.remediation_episode.teaching_steps] == [
        step.reply_tokens for step in llm.remediation_episode.teaching_steps
    ]


def test_phase5_5_planner_does_not_solidify_current_focus_conflict() -> None:
    case = CurriculumValidationCase(
        "conflict:slot_focus",
        ("describe",),
        ("ctx_visual",),
        ("field::color", "percept::yellow", "field::object", "percept::pear"),
        expected_pid="p:discovered:skill_color_object",
        focus_tokens=("percept::yellow", "percept::apple"),
        allow_current_focus=True,
    )
    episode = CurriculumEpisode(
        episode_id="phase5_5_focus_conflict",
        source_kind="natural",
        teaching_steps=(
            CurriculumTeachingStep(
                "skill_color_object",
                ("describe",),
                ("field::color", "percept::yellow", "field::object", "percept::apple"),
                ("ctx_visual",),
                "teacher_trace",
            ),
        ),
        validation_cases=(case,),
    )
    result = APV3CurriculumRemediationLoop().run(_base_state(), episode)

    assert result.initial.validation_results[0].success is False
    assert result.suggestions[0].teaching_steps == ()
    assert "contradictory memory" in result.suggestions[0].rationale
    assert result.remediation_episode.teaching_steps == ()


def test_phase5_5_planner_outputs_ap_native_steps_not_runtime_rules() -> None:
    initial = APV3CurriculumRemediationLoop().run(_base_state(), _missing_greeting_episode("natural")).initial
    suggestion = APV3CurriculumRemediationPlanner().plan(
        _missing_greeting_episode("natural").validation_cases,
        initial.validation_results,
        source_kind="natural",
    )[0]

    assert all(isinstance(step, CurriculumTeachingStep) for step in suggestion.teaching_steps)
    assert "keyword" not in str(suggestion).lower()
    assert "answer_table" not in str(suggestion).lower()


def test_phase5_5_remediation_intensity_drops_for_already_exposed_paradigm() -> None:
    state = {
        "paradigms": [
            {
                "pid": "p:discovered:skill_greeting",
                "entry_kind": "ParadigmSA",
                "exposed": True,
            }
        ]
    }
    initial = APV3CurriculumRemediationLoop().run(_base_state(), _missing_greeting_episode("natural")).initial
    suggestion = APV3CurriculumRemediationPlanner().plan(
        _missing_greeting_episode("natural").validation_cases,
        initial.validation_results,
        source_kind="natural",
        state=state,
    )[0]

    assert suggestion.evidence_repeats == 1
    assert suggestion.remediation_intensity == 0.5
