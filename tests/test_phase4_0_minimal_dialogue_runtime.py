from __future__ import annotations

from pathlib import Path

from apv3test.runtime import (
    DialogueTurnInput,
    LearnedActionOutcome,
    LearningEpisode,
    LearningEpisodeWriter,
    MinimalDialogueRuntime,
    ParadigmDiscoveryEngine,
    ParadigmObservation,
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


def _color_object_paradigm():
    return ParadigmDiscoveryEngine().discover(
        [
            ParadigmObservation(
                "phase4_color_object",
                ("describe",),
                ("field::color", "percept::red", "field::object", "percept::apple"),
            ),
            ParadigmObservation(
                "phase4_color_object",
                ("describe",),
                ("field::color", "percept::blue", "field::object", "percept::cup"),
            ),
            ParadigmObservation(
                "phase4_color_object",
                ("describe",),
                ("field::color", "percept::green", "field::object", "percept::leaf"),
            ),
            ParadigmObservation(
                "phase4_color_object",
                ("describe",),
                ("field::color", "percept::yellow", "field::object", "percept::banana"),
            ),
        ]
    )[0]


def test_minimal_dialogue_runtime_writes_tokens_one_tick_at_a_time_and_commits() -> None:
    result = MinimalDialogueRuntime().run_turn(
        _blank_state(),
        paradigm=_color_object_paradigm(),
        turn=DialogueTurnInput(
            tick=20,
            focus_tokens=("percept::yellow", "percept::apple"),
            candidate_pool=("percept::yellow", "percept::apple"),
            current_context_tags=("vision", "describe"),
            commit_after_draft=True,
        ),
        commit_episode_id="commit:phase4:yellow_apple",
    )

    assert result.emitted_tokens == ("field::color", "percept::yellow", "field::object", "percept::apple")
    assert [trace.tick for trace in result.action_traces] == [20, 21, 22, 23]
    assert result.committed_text == "field::colorpercept::yellowfield::objectpercept::apple"
    assert result.state["draft_runtime"]["buffer"] == ""
    assert result.state["action_outcomes"]["text_commit"]["reward_support"] == 1.0


def test_fast_habit_can_compete_with_paradigm_token_without_bypassing_conflict_domain() -> None:
    state = LearningEpisodeWriter().apply(
        _blank_state(),
        LearningEpisode(
            "phase4:habit:strong_reread",
            action_outcomes=(
                LearnedActionOutcome(
                    "action::reread",
                    reward_delta=10.0,
                    support_delta=8.0,
                    drive_bias_delta=2.0,
                    actuator_id="draft_editor",
                    context_tags=("ambiguous",),
                ),
            ),
        ),
    )

    result = MinimalDialogueRuntime().run_turn(
        state,
        paradigm=_color_object_paradigm(),
        turn=DialogueTurnInput(
            tick=30,
            focus_tokens=("percept::yellow", "percept::apple"),
            candidate_pool=("percept::yellow", "percept::apple"),
            current_context_tags=("ambiguous",),
            grasp=2.0,
            demand_slow=0.1,
            commit_after_draft=True,
        ),
    )
    first_trace = result.action_traces[0]

    assert first_trace.selected[0].actuator_id == "draft_editor"
    assert first_trace.selected[0].action_id == "action::reread"
    assert result.emitted_tokens == ()
    assert result.state["draft_runtime"]["buffer"] == ""
    assert result.committed_text == ""


def test_attention_habit_can_coexist_while_draft_token_wins_editor() -> None:
    state = LearningEpisodeWriter().apply(
        _blank_state(),
        LearningEpisode(
            "phase4:habit:attention",
            action_outcomes=(
                LearnedActionOutcome(
                    "thought::focus_visual_band",
                    reward_delta=8.0,
                    support_delta=4.0,
                    actuator_id="attention_focus",
                    outcome_kind="thought",
                    context_tags=("vision", "describe"),
                ),
            ),
        ),
    )

    result = MinimalDialogueRuntime().run_turn(
        state,
        paradigm=_color_object_paradigm(),
        turn=DialogueTurnInput(
            tick=40,
            focus_tokens=("percept::yellow", "percept::apple"),
            candidate_pool=("percept::yellow", "percept::apple"),
            current_context_tags=("vision", "describe"),
            grasp=1.6,
            demand_slow=0.1,
            commit_after_draft=True,
        ),
    )
    first_trace = result.action_traces[0]

    assert {item.actuator_id for item in first_trace.selected} == {"draft_editor", "attention_focus"}
    assert result.emitted_tokens == ("field::color", "percept::yellow", "field::object", "percept::apple")
    assert result.committed_text == "field::colorpercept::yellowfield::objectpercept::apple"


def test_minimal_dialogue_runtime_survives_sqlite_restore(tmp_path: Path) -> None:
    runtime = MinimalDialogueRuntime()
    turn = DialogueTurnInput(
        tick=50,
        focus_tokens=("percept::yellow", "percept::apple"),
        candidate_pool=("percept::yellow", "percept::apple"),
        current_context_tags=("vision", "describe"),
        commit_after_draft=True,
    )
    result = runtime.run_turn(
        _blank_state(),
        paradigm=_color_object_paradigm(),
        turn=turn,
        commit_episode_id="commit:phase4:restore",
    )
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")
    restored = store.load_state(store.save_state(result.state))

    assert restored == result.state
    assert restored["draft_runtime"]["commits"][-1]["text"] == "field::colorpercept::yellowfield::objectpercept::apple"
    assert restored["action_outcomes"]["text_commit"]["reward_support"] == 1.0
