from __future__ import annotations

from apv3test.config import APV3ActiveLearningConfig
from apv3test.runtime import (
    APV3ActiveTeacherRequestRuntime,
    APV3CurriculumRemediationLoop,
    APV3CurriculumRemediationPlanner,
    CurriculumEpisode,
    CurriculumValidationCase,
    TeacherRequestSignal,
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


def _signal(
    tick: int,
    *,
    pressure: float = 0.2,
    failed: bool = True,
    expected_pid: str = "",
) -> TeacherRequestSignal:
    return TeacherRequestSignal(
        tick=tick,
        cue_tokens=("goal::ask",),
        context_tokens=("ctx_work",),
        cognitive_pressure=pressure,
        recall_failed=failed,
        expected_pid=expected_pid,
    )


def _teacher_episode() -> CurriculumEpisode:
    return CurriculumEpisode(
        episode_id="phase6_2:teacher_response",
        source_kind="llm_standard_teacher",
        teaching_steps=(),
        validation_cases=(
            CurriculumValidationCase(
                "needs:teacher_response",
                ("goal::ask",),
                ("ctx_work",),
                ("teacher::answer",),
                expected_pid="p:discovered:skill_teacher_answer",
            ),
        ),
    )


def test_phase6_2_repeated_failures_raise_request_trace_until_pressure_cap() -> None:
    runtime = APV3ActiveTeacherRequestRuntime(APV3ActiveLearningConfig(request_cooldown_ticks=0))
    state = _base_state()

    first = runtime.observe(state, _signal(1))
    second = runtime.observe(first.state, _signal(20))
    third = runtime.observe(second.state, _signal(40))

    key = "cue=goal::ask|ctx=ctx_work"
    assert first.request is None
    assert second.request is not None
    assert third.request is not None
    assert third.state["active_learning_failures"][key]["failure_count"] == 3
    request_entries = [item for item in third.state["state_field_items"] if item["sa_type"] == "teacher_request"]
    assert request_entries[-1]["energy"]["P"] == 1.0
    assert request_entries[-1]["energy"]["A"] == 1.0


def test_phase6_2_successful_observations_reduce_failure_trace_without_hard_suppress() -> None:
    runtime = APV3ActiveTeacherRequestRuntime(APV3ActiveLearningConfig(request_cooldown_ticks=0))
    state = _base_state()
    failed_once = runtime.observe(state, _signal(1))
    failed_twice = runtime.observe(failed_once.state, _signal(20))

    recovered_once = runtime.observe(failed_twice.state, _signal(40, pressure=0.0, failed=False))
    recovered_twice = runtime.observe(recovered_once.state, _signal(60, pressure=0.0, failed=False))

    key = "cue=goal::ask|ctx=ctx_work"
    assert failed_twice.request is not None
    assert recovered_once.request is None
    assert recovered_once.suppressed_reason == "below_request_threshold"
    assert recovered_once.state["active_learning_failures"][key]["failure_count"] == 1
    assert recovered_twice.request is None
    assert recovered_twice.state["active_learning_failures"][key]["failure_count"] == 0


def test_phase6_2_mastered_teacher_response_declines_later_teacher_request() -> None:
    runtime = APV3ActiveTeacherRequestRuntime(APV3ActiveLearningConfig(request_cooldown_ticks=0))
    requested = runtime.observe(_base_state(), _signal(1, pressure=0.9))
    learned = APV3CurriculumRemediationLoop().run(
        requested.state,
        _teacher_episode(),
        start_tick=10,
        remediation_start_tick=20,
    )

    after_mastery = runtime.observe(
        learned.final.state,
        _signal(
            80,
            pressure=0.0,
            failed=False,
            expected_pid="p:discovered:skill_teacher_answer",
        ),
    )

    assert requested.request is not None
    assert learned.final.validation_results[0].success is True
    assert after_mastery.request is None
    assert after_mastery.suppressed_reason == "mastered_expected_pid"
    assert "llm_policy" not in str(learned.final.state)
    assert "answer_table" not in str(learned.final.state)


def test_phase6_2_remediation_intensity_is_strong_cold_start_then_weaker_after_exposure() -> None:
    loop = APV3CurriculumRemediationLoop()
    episode = _teacher_episode()
    trend = loop.run(_base_state(), episode, start_tick=10, remediation_start_tick=20)

    cold_start_suggestion = trend.suggestions[0]
    later_suggestion = APV3CurriculumRemediationPlanner().plan(
        episode.validation_cases,
        trend.initial.validation_results,
        source_kind=episode.source_kind,
        state=trend.final.state,
    )[0]

    assert cold_start_suggestion.evidence_repeats == 2
    assert cold_start_suggestion.remediation_intensity == 1.0
    assert later_suggestion.evidence_repeats == 1
    assert later_suggestion.remediation_intensity == 0.5
    assert later_suggestion.teaching_steps[0].stage == "remediate"
