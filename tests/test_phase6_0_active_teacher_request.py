from __future__ import annotations

from apv3test.runtime import (
    APV3ActiveTeacherRequestRuntime,
    APV3CurriculumRemediationLoop,
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


def _signal(tick: int, *, pressure: float = 0.0, failed: bool = True, expected_pid: str = "") -> TeacherRequestSignal:
    return TeacherRequestSignal(
        tick=tick,
        cue_tokens=("goal::ask",),
        context_tokens=("ctx_work",),
        cognitive_pressure=pressure,
        recall_failed=failed,
        expected_pid=expected_pid,
    )


def test_phase6_0_repeated_recall_failure_creates_teacher_request_sa() -> None:
    runtime = APV3ActiveTeacherRequestRuntime()
    first = runtime.observe(_base_state(), _signal(1, pressure=0.2))
    second = runtime.observe(first.state, _signal(2, pressure=0.2))

    assert first.request is None
    assert first.suppressed_reason == "below_request_threshold"
    assert second.request is not None
    assert second.request.reason == "repeated_recall_failure"
    assert second.request.failure_count == 2
    pool_entry = next(item for item in second.state["state_field_items"] if item["sa_type"] == "teacher_request")
    assert pool_entry["cue_tokens"] == ["goal::ask"]
    assert pool_entry["energy"]["P"] > 0.0


def test_phase6_0_high_cognitive_pressure_can_request_teacher_without_waiting_for_repeats() -> None:
    result = APV3ActiveTeacherRequestRuntime().observe(_base_state(), _signal(5, pressure=0.9))

    assert result.request is not None
    assert result.request.reason == "high_cognitive_pressure"
    assert result.state["teacher_requests"][0]["reason"] == "high_cognitive_pressure"


def test_phase6_0_teacher_response_still_uses_ap_native_remediation_and_then_request_declines() -> None:
    runtime = APV3ActiveTeacherRequestRuntime()
    requested = runtime.observe(_base_state(), _signal(1, pressure=0.9))
    assert requested.request is not None

    episode = CurriculumEpisode(
        episode_id="phase6_0:teacher_response",
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
    learned = APV3CurriculumRemediationLoop().run(requested.state, episode, start_tick=10, remediation_start_tick=20)
    after = runtime.observe(
        learned.final.state,
        _signal(40, pressure=0.9, expected_pid="p:discovered:skill_teacher_answer"),
    )

    assert learned.final.validation_results[0].success is True
    assert after.request is None
    assert after.suppressed_reason == "mastered_expected_pid"
    assert "llm_policy" not in str(learned.final.state)


def test_phase6_0_request_cooldown_prevents_spam_without_hiding_failures() -> None:
    runtime = APV3ActiveTeacherRequestRuntime()
    first = runtime.observe(_base_state(), _signal(1, pressure=0.9))
    second = runtime.observe(first.state, _signal(2, pressure=0.9))

    assert first.request is not None
    assert second.request is None
    assert second.suppressed_reason == "request_cooldown"
    assert second.state["active_learning_failures"]["cue=goal::ask|ctx=ctx_work"]["failure_count"] == 2


def test_phase6_0_low_pressure_single_failure_does_not_request_teacher() -> None:
    result = APV3ActiveTeacherRequestRuntime().observe(_base_state(), _signal(1, pressure=0.1))

    assert result.request is None
    assert result.suppressed_reason == "below_request_threshold"
    assert result.state["teacher_requests"] == []
