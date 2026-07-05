from __future__ import annotations

from pathlib import Path

from apv3test.runtime import (
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


def _learned_state(*outcomes: LearnedActionOutcome) -> dict:
    return LearningEpisodeWriter().apply(
        _blank_state(),
        LearningEpisode("habit:phase3:episode", action_outcomes=outcomes),
    )


def test_rewarded_supported_action_becomes_fast_habit_candidate() -> None:
    state = _learned_state(
        LearnedActionOutcome(
            "action::draft_commit",
            drive_bias_delta=0.8,
            reward_delta=8.0,
            support_delta=4.0,
            actuator_id="draft_editor",
            context_tags=("dialogue", "low_pressure"),
            last_tick=96,
        )
    )

    candidate = FastHabitSystem().candidates(
        state,
        current_context_tags=("dialogue", "low_pressure"),
        grasp=2.4,
        demand_slow=0.1,
        current_tick=100,
    )[0]

    assert candidate.action_id == "action::draft_commit"
    assert candidate.habit_strength > 0.8
    assert candidate.lambda_fast > 0.9
    assert candidate.drive > 1.4
    assert candidate.slow_review_pressure < 0.0


def test_punishment_suppresses_habit_in_similar_context() -> None:
    rewarded = _learned_state(
        LearnedActionOutcome(
            "action::reread",
            reward_delta=6.0,
            support_delta=4.0,
            actuator_id="draft_editor",
            context_tags=("ambiguous_draft",),
            last_tick=10,
        )
    )
    punished = _learned_state(
        LearnedActionOutcome(
            "action::reread",
            reward_delta=6.0,
            punish_delta=9.0,
            support_delta=4.0,
            actuator_id="draft_editor",
            context_tags=("ambiguous_draft",),
            last_tick=10,
        )
    )
    system = FastHabitSystem()

    rewarded_candidate = system.candidates(
        rewarded, current_context_tags=("ambiguous_draft",), grasp=1.2, demand_slow=0.4, current_tick=12
    )[0]
    punished_candidate = system.candidates(
        punished, current_context_tags=("ambiguous_draft",), grasp=1.2, demand_slow=0.4, current_tick=12
    )[0]

    assert punished_candidate.habit_strength < rewarded_candidate.habit_strength
    assert punished_candidate.drive < rewarded_candidate.drive


def test_context_mismatch_reduces_habit_without_erasing_evidence() -> None:
    state = _learned_state(
        LearnedActionOutcome(
            "action::focus_math",
            reward_delta=8.0,
            support_delta=5.0,
            actuator_id="attention_focus",
            outcome_kind="thought",
            context_tags=("math", "calculate"),
            last_tick=50,
        )
    )
    system = FastHabitSystem()

    matched = system.candidates(
        state, current_context_tags=("math", "calculate"), grasp=1.0, demand_slow=0.2, current_tick=51
    )[0]
    mismatched = system.candidates(
        state, current_context_tags=("chat", "comfort"), grasp=1.0, demand_slow=0.2, current_tick=51
    )[0]

    assert mismatched.context_match < matched.context_match
    assert mismatched.habit_strength < matched.habit_strength
    assert state["action_outcomes"]["action::focus_math"]["reward_support"] == 8.0


def test_same_actuator_keeps_one_winner_but_different_actuators_can_coactivate() -> None:
    state = _learned_state(
        LearnedActionOutcome(
            "action::type_token",
            reward_delta=9.0,
            support_delta=5.0,
            actuator_id="draft_editor",
            context_tags=("dialogue",),
        ),
        LearnedActionOutcome(
            "action::reread",
            reward_delta=4.0,
            support_delta=3.0,
            actuator_id="draft_editor",
            context_tags=("dialogue",),
        ),
        LearnedActionOutcome(
            "thought::focus_reply_band",
            reward_delta=8.0,
            support_delta=5.0,
            actuator_id="attention_focus",
            outcome_kind="thought",
            context_tags=("dialogue",),
        ),
    )
    candidates = FastHabitSystem().candidates(
        state, current_context_tags=("dialogue",), grasp=2.0, demand_slow=0.1
    )

    selected = FastHabitSystem().select_compatible(candidates)

    assert {item.actuator_id for item in selected} == {"draft_editor", "attention_focus"}
    assert sum(1 for item in selected if item.actuator_id == "draft_editor") == 1
    assert any(item.action_id == "thought::focus_reply_band" for item in selected)


def test_habit_action_outcomes_survive_sqlite_roundtrip(tmp_path: Path) -> None:
    state = _learned_state(
        LearnedActionOutcome(
            "action::commit_after_reread",
            drive_bias_delta=0.3,
            reward_delta=7.0,
            support_delta=4.0,
            actuator_id="draft_editor",
            context_tags=("reread_clean",),
            last_tick=20,
        )
    )
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")
    restored = store.load_state(store.save_state(state))

    candidate = FastHabitSystem().candidates(
        restored, current_context_tags=("reread_clean",), grasp=1.6, demand_slow=0.2, current_tick=22
    )[0]

    assert restored == state
    assert candidate.action_id == "action::commit_after_reread"
    assert candidate.lambda_fast > 0.85
