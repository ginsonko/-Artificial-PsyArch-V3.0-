from __future__ import annotations

from pathlib import Path

from apv3test.runtime import (
    ActionCompetition,
    DialogueTurnInput,
    FastHabitSystem,
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


def _single_reply_paradigm(case_name: str, cue: tuple[str, ...], reply: tuple[str, ...]):
    return ParadigmDiscoveryEngine().discover(
        [
            ParadigmObservation(case_name, cue, reply),
            ParadigmObservation(case_name, cue, reply),
        ]
    )[0]


def test_reproduces_greeting_successor_through_minimal_runtime() -> None:
    paradigm = _single_reply_paradigm("phase4_1_greeting", ("你", "好"), ("我", "在", "。"))

    result = MinimalDialogueRuntime().run_turn(
        _blank_state(),
        paradigm=paradigm,
        turn=DialogueTurnInput(
            tick=100,
            focus_tokens=("我", "在", "。"),
            candidate_pool=("我", "在", "。"),
            current_context_tags=("dialogue", "greeting"),
            commit_after_draft=True,
        ),
        commit_episode_id="commit:phase4_1:greeting",
    )

    assert result.emitted_tokens == ("我", "在", "。")
    assert result.committed_text == "我在。"
    assert result.state["action_outcomes"]["text_commit"]["reward_support"] == 1.0


def test_reproduces_idiom_successor_without_literal_answer_table() -> None:
    paradigm = _single_reply_paradigm("phase4_1_idiom", ("三", "顾"), ("茅", "庐"))

    result = MinimalDialogueRuntime().run_turn(
        _blank_state(),
        paradigm=paradigm,
        turn=DialogueTurnInput(
            tick=110,
            focus_tokens=("茅", "庐"),
            candidate_pool=("茅", "庐"),
            current_context_tags=("idiom", "successor"),
            commit_after_draft=True,
        ),
    )

    assert result.emitted_tokens == ("茅", "庐")
    assert result.committed_text == "茅庐"
    assert all(trace.selected[0].source_system == "paradigm_slot_fill" for trace in result.action_traces)


def test_reproduces_simple_math_process_tokens_as_paradigm_not_solver() -> None:
    paradigm = _single_reply_paradigm(
        "phase4_1_math_process",
        ("2", "+", "3"),
        ("列式", ":", "2", "+", "3", "=", "5"),
    )

    result = MinimalDialogueRuntime().run_turn(
        _blank_state(),
        paradigm=paradigm,
        turn=DialogueTurnInput(
            tick=120,
            focus_tokens=("列式", ":", "2", "+", "3", "=", "5"),
            candidate_pool=("列式", ":", "2", "+", "3", "=", "5"),
            current_context_tags=("math", "process"),
            commit_after_draft=True,
        ),
    )

    assert result.emitted_tokens == ("列式", ":", "2", "+", "3", "=", "5")
    assert result.committed_text == "列式:2+3=5"
    assert len(result.action_traces) == 7


def test_reproduces_percept_color_object_slot_skill() -> None:
    paradigm = ParadigmDiscoveryEngine().discover(
        [
            ParadigmObservation(
                "phase4_1_percept_slots",
                ("describe",),
                ("field::color", "percept::red", "field::object", "percept::apple"),
            ),
            ParadigmObservation(
                "phase4_1_percept_slots",
                ("describe",),
                ("field::color", "percept::blue", "field::object", "percept::cup"),
            ),
            ParadigmObservation(
                "phase4_1_percept_slots",
                ("describe",),
                ("field::color", "percept::green", "field::object", "percept::leaf"),
            ),
            ParadigmObservation(
                "phase4_1_percept_slots",
                ("describe",),
                ("field::color", "percept::yellow", "field::object", "percept::banana"),
            ),
        ]
    )[0]

    result = MinimalDialogueRuntime().run_turn(
        _blank_state(),
        paradigm=paradigm,
        turn=DialogueTurnInput(
            tick=130,
            focus_tokens=("percept::yellow", "percept::apple"),
            candidate_pool=("percept::yellow", "percept::apple"),
            current_context_tags=("vision", "describe"),
            commit_after_draft=True,
        ),
    )

    assert result.emitted_tokens == ("field::color", "percept::yellow", "field::object", "percept::apple")
    assert result.committed_text == "field::colorpercept::yellowfield::objectpercept::apple"
    assert result.committed_text != "黄色苹果"


def test_interruption_recovery_pressure_enters_competition_without_forced_resume() -> None:
    state = LearningEpisodeWriter().apply(
        _blank_state(),
        LearningEpisode(
            "phase4_1:interruption_pressure",
            action_outcomes=(
                LearnedActionOutcome(
                    "thought::resume_unfinished_task",
                    reward_delta=6.0,
                    support_delta=4.0,
                    actuator_id="attention_focus",
                    outcome_kind="thought",
                    context_tags=("unfinished", "idle"),
                    last_tick=140,
                ),
            ),
        ),
    )
    candidates = FastHabitSystem().candidates(
        state,
        current_context_tags=("unfinished", "idle"),
        grasp=0.4,
        demand_slow=1.8,
        current_tick=145,
    )
    trace = ActionCompetition().from_habit_candidates(candidates, tick=145)

    assert trace.selected[0].action_id == "thought::resume_unfinished_task"
    assert trace.decisions[0].requires_slow_review is True
    assert trace.selected[0].source_system == "fast_habit"


def test_small_skill_batch_survives_sqlite_restore(tmp_path: Path) -> None:
    runtime = MinimalDialogueRuntime()
    state = _blank_state()
    for tick, case_name, cue, reply, tags in (
        (150, "phase4_1_restore_greeting", ("你", "好"), ("我", "在", "。"), ("dialogue",)),
        (160, "phase4_1_restore_idiom", ("三", "顾"), ("茅", "庐"), ("idiom",)),
    ):
        paradigm = _single_reply_paradigm(case_name, cue, reply)
        result = runtime.run_turn(
            state,
            paradigm=paradigm,
            turn=DialogueTurnInput(
                tick=tick,
                focus_tokens=reply,
                candidate_pool=reply,
                current_context_tags=tags,
                commit_after_draft=True,
            ),
            commit_episode_id=f"commit:{case_name}",
        )
        state = result.state
    restored = SQLiteRuntimeStore(tmp_path / "runtime.sqlite").load_state(
        SQLiteRuntimeStore(tmp_path / "runtime.sqlite").save_state(state)
    )

    assert restored == state
    assert [item["text"] for item in restored["draft_runtime"]["commits"]] == ["我在。", "茅庐"]
    assert restored["action_outcomes"]["text_commit"]["reward_support"] == 2.0
