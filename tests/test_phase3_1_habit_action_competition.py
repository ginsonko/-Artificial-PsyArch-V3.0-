from __future__ import annotations

from pathlib import Path

from apv3test.runtime import (
    ActionCompetition,
    FastHabitSystem,
    LearnedActionOutcome,
    LearningEpisode,
    LearningEpisodeWriter,
    SQLiteRuntimeStore,
)


def _blank_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {"tokens": {}},
        "transitions": [],
        "paradigms": [],
        "bn_candidates": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def _state_with_outcomes(*outcomes: LearnedActionOutcome) -> dict:
    return LearningEpisodeWriter().apply(
        _blank_state(),
        LearningEpisode("phase3_1:competition", action_outcomes=outcomes),
    )


def test_habit_candidates_enter_action_competition_trace() -> None:
    state = _state_with_outcomes(
        LearnedActionOutcome(
            "action::type_reply_token",
            reward_delta=8.0,
            support_delta=4.0,
            actuator_id="draft_editor",
            context_tags=("dialogue",),
        )
    )
    candidates = FastHabitSystem().candidates(
        state, current_context_tags=("dialogue",), grasp=2.0, demand_slow=0.1
    )

    trace = ActionCompetition().from_habit_candidates(candidates, tick=7)

    assert trace.selected[0].action_id == "action::type_reply_token"
    assert trace.selected[0].source_system == "fast_habit"
    assert trace.selected[0].lambda_fast > 0.8
    assert trace.as_dict()["decisions"][0]["selected"] == "action::type_reply_token"


def test_same_actuator_conflict_rejects_lower_drive_candidate() -> None:
    state = _state_with_outcomes(
        LearnedActionOutcome(
            "action::type_token",
            reward_delta=9.0,
            support_delta=4.0,
            actuator_id="draft_editor",
            context_tags=("dialogue",),
        ),
        LearnedActionOutcome(
            "action::reread",
            reward_delta=3.0,
            support_delta=2.0,
            actuator_id="draft_editor",
            context_tags=("dialogue",),
        ),
    )
    candidates = FastHabitSystem().candidates(
        state, current_context_tags=("dialogue",), grasp=2.0, demand_slow=0.1
    )

    trace = ActionCompetition().from_habit_candidates(candidates, tick=8)

    assert len(trace.selected) == 1
    assert trace.selected[0].actuator_id == "draft_editor"
    assert trace.selected[0].action_id == "action::type_token"
    assert trace.rejected[0].action_id == "action::reread"


def test_different_actuators_can_coexist_in_one_tick_trace() -> None:
    state = _state_with_outcomes(
        LearnedActionOutcome(
            "action::type_token",
            reward_delta=8.0,
            support_delta=4.0,
            actuator_id="draft_editor",
            context_tags=("dialogue",),
        ),
        LearnedActionOutcome(
            "thought::focus_reply_band",
            reward_delta=8.0,
            support_delta=4.0,
            actuator_id="attention_focus",
            outcome_kind="thought",
            context_tags=("dialogue",),
        ),
    )
    candidates = FastHabitSystem().candidates(
        state, current_context_tags=("dialogue",), grasp=2.0, demand_slow=0.1
    )

    trace = ActionCompetition().from_habit_candidates(candidates, tick=9)

    assert {item.actuator_id for item in trace.selected} == {"draft_editor", "attention_focus"}
    assert {item.outcome_kind for item in trace.selected} == {"action", "thought"}


def test_high_slow_pressure_marks_selected_candidate_for_review() -> None:
    state = _state_with_outcomes(
        LearnedActionOutcome(
            "action::commit",
            reward_delta=5.0,
            support_delta=3.0,
            actuator_id="draft_editor",
            context_tags=("ambiguous",),
        )
    )
    candidates = FastHabitSystem().candidates(
        state, current_context_tags=("ambiguous",), grasp=0.2, demand_slow=2.0
    )

    trace = ActionCompetition().from_habit_candidates(candidates, tick=10)

    assert trace.decisions[0].requires_slow_review is True
    assert trace.selected[0].slow_review_pressure > 0.0


def test_competition_trace_is_reproducible_after_sqlite_restore(tmp_path: Path) -> None:
    state = _state_with_outcomes(
        LearnedActionOutcome(
            "action::type_token",
            reward_delta=8.0,
            support_delta=4.0,
            actuator_id="draft_editor",
            context_tags=("dialogue",),
            last_tick=11,
        ),
        LearnedActionOutcome(
            "thought::focus_reply_band",
            reward_delta=7.0,
            support_delta=4.0,
            actuator_id="attention_focus",
            outcome_kind="thought",
            context_tags=("dialogue",),
            last_tick=11,
        ),
    )
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")
    restored = store.load_state(store.save_state(state))
    system = FastHabitSystem()
    competition = ActionCompetition()

    memory_trace = competition.from_habit_candidates(
        system.candidates(state, current_context_tags=("dialogue",), grasp=2.0, demand_slow=0.1, current_tick=12),
        tick=12,
    ).as_dict()
    restored_trace = competition.from_habit_candidates(
        system.candidates(restored, current_context_tags=("dialogue",), grasp=2.0, demand_slow=0.1, current_tick=12),
        tick=12,
    ).as_dict()

    assert restored == state
    assert restored_trace == memory_trace
