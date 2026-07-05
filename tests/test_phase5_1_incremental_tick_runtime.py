from __future__ import annotations

from pathlib import Path

from apv3test.runtime import (
    IncrementalTickInput,
    IncrementalTickRuntime,
    SQLiteRuntimeStore,
)


def _base_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "ctx_greeting": {"vector": [1.0, 0.0], "support": 4.0, "promoted": True},
                "ctx_greeting_near": {"vector": [0.96, 0.04], "support": 4.0, "promoted": True},
            }
        },
        "transitions": [],
        "paradigms": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def _teach_tick(
    tick: int,
    *,
    source_kind: str = "natural",
    commit: bool = True,
    emit_reply: bool = False,
    context: tuple[str, ...] = ("ctx_greeting",),
) -> IncrementalTickInput:
    return IncrementalTickInput(
        tick=tick,
        case_name="phase5_1_hello",
        cue_tokens=("你", "好"),
        reply_tokens=("我", "在"),
        context_tokens=context,
        source_kind=source_kind,
        teacher_stage="successor_prediction",
        commit_observation=commit,
        reward_delta=1.0 if commit else 0.0,
        emit_reply=emit_reply,
        commit_after_draft=emit_reply,
        grasp=1.2,
        demand_slow=0.1,
    )


def test_uncommitted_tick_only_stages_observation_without_support() -> None:
    runtime = IncrementalTickRuntime()

    result = runtime.run_tick(_base_state(), _teach_tick(1, commit=False))

    assert result.staged_observation is True
    assert result.learning_update is None
    assert len(result.state["pending_paradigm_observations"]) == 1
    assert "paradigm_observations" not in result.state
    assert result.state["paradigms"] == []


def test_commit_ticks_incrementally_learn_then_emit_low_granularity_reply() -> None:
    runtime = IncrementalTickRuntime()
    first = runtime.run_tick(_base_state(), _teach_tick(1, emit_reply=True))
    second = runtime.run_tick(first.state, _teach_tick(2, emit_reply=True))

    assert first.learning_update is not None
    assert first.learning_update.discovered is None
    assert second.learning_update is not None
    assert second.learning_update.discovered is not None
    assert second.dialogue_result is not None
    assert second.dialogue_result.emitted_tokens == ("我", "在")
    assert second.dialogue_result.committed_text == "我在"
    assert second.state["action_outcomes"]["text_commit"]["reward_support"] == 1.0
    assert second.state["paradigms"][0]["entry_kind"] == "ParadigmSA"


def test_feedback_after_staged_observation_resolves_pending_and_raises_support() -> None:
    runtime = IncrementalTickRuntime()
    staged = runtime.run_tick(_base_state(), _teach_tick(5, commit=False))

    feedback = runtime.run_tick(staged.state, _teach_tick(6, commit=True))

    assert staged.state["pending_paradigm_observations"]
    assert feedback.state["pending_paradigm_observations"] == []
    assert len(feedback.state["paradigm_observations"]) == 1
    assert feedback.state["paradigms"] == []


def test_idle_tick_settles_dirty_bucket_without_changing_paradigm_sa() -> None:
    runtime = IncrementalTickRuntime()
    state = runtime.run_tick(_base_state(), _teach_tick(1)).state
    learned = runtime.run_tick(state, _teach_tick(2)).state
    before = list(learned["paradigms"])

    idle = runtime.run_tick(learned, IncrementalTickInput(tick=20, idle=True))

    assert idle.idle_settled_bucket == "phase5_1_hello|你 好"
    assert idle.state["dirty_paradigm_buckets"] == []
    assert idle.state["idle_paradigm_maintenance"][-1]["kind"] == "dirty_bucket_settled"
    assert idle.state["paradigms"] == before


def test_realtime_role_transition_bias_is_read_during_later_tick_decode() -> None:
    runtime = IncrementalTickRuntime()
    state = runtime.run_tick(_base_state(), _teach_tick(1)).state
    state = runtime.run_tick(state, _teach_tick(2)).state

    later = runtime.run_tick(state, _teach_tick(3, context=("ctx_greeting_near",)))

    assert later.learning_update is not None
    assert later.learning_update.transition_bias
    assert later.learning_update.transition_bias[("fixed_anchor", "fixed_anchor")] > 0.0


def test_natural_and_llm_standard_ticks_emit_equivalent_runtime_behavior() -> None:
    runtime = IncrementalTickRuntime()
    natural_state = _base_state()
    llm_state = _base_state()
    for tick in (1, 2):
        natural = runtime.run_tick(natural_state, _teach_tick(tick, source_kind="natural", emit_reply=tick == 2))
        llm = runtime.run_tick(
            llm_state,
            _teach_tick(tick, source_kind="llm_standard_teacher", emit_reply=tick == 2),
        )
        natural_state = natural.state
        llm_state = llm.state

    assert natural.dialogue_result is not None
    assert llm.dialogue_result is not None
    assert natural.dialogue_result.emitted_tokens == llm.dialogue_result.emitted_tokens
    assert natural.dialogue_result.committed_text == llm.dialogue_result.committed_text
    assert natural_state["paradigms"] == llm_state["paradigms"]
    assert "llm_policy" not in str(llm_state)


def test_phase5_1_tick_runtime_survives_sqlite_restore(tmp_path: Path) -> None:
    runtime = IncrementalTickRuntime()
    state = runtime.run_tick(_base_state(), _teach_tick(1)).state
    state = runtime.run_tick(state, _teach_tick(2, emit_reply=True)).state
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    restored = store.load_state(store.save_state(state))

    assert restored == state
    assert restored["paradigms"][0]["entry_kind"] == "ParadigmSA"
    assert restored["draft_runtime"]["commits"][-1]["text"] == "我在"
