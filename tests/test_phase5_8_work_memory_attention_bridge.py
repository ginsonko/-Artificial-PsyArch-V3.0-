from __future__ import annotations

from apv3test.runtime import (
    APV3WorkMemoryAttentionBridge,
    APV3WorkMemoryRuntime,
    IncrementalTickInput,
    IncrementalTickRuntime,
    WorkMemoryTickInput,
)


def _base_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "ctx_work": {"vector": [1.0, 0.0], "support": 4.0, "promoted": True},
                "goal::solve": {"vector": [0.9, 0.1], "support": 4.0, "promoted": True},
                "item::math": {"vector": [0.85, 0.15], "support": 4.0, "promoted": True},
                "goal::cook": {"vector": [0.0, 1.0], "support": 4.0, "promoted": True},
            }
        },
        "transitions": [],
        "paradigms": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def _teach_resume_skill(state: dict) -> dict:
    runtime = IncrementalTickRuntime()
    for tick in (1, 2):
        state = runtime.run_tick(
            state,
            IncrementalTickInput(
                tick=tick,
                case_name="skill_resume_math",
                cue_tokens=("goal::solve", "item::math"),
                reply_tokens=("continue::math",),
                context_tokens=("ctx_work",),
                commit_observation=True,
                reward_delta=1.0,
            ),
        ).state
    return state


def test_phase5_8_work_memory_idle_recall_feeds_bn_cn_attention() -> None:
    state = _teach_resume_skill(_base_state())
    work_memory = APV3WorkMemoryRuntime()
    state = work_memory.run_tick(
        state,
        WorkMemoryTickInput(tick=10, focus_tokens=("goal::solve", "item::math"), pressure=0.95),
    ).state

    result = APV3WorkMemoryAttentionBridge(work_memory=work_memory).run_idle_recall(
        state,
        tick=12,
        context_tokens=("ctx_work",),
    )

    assert result.work_memory_result.recalled_item is not None
    assert result.recall_result is not None
    assert result.recall_result.recall_result is not None
    assert result.recall_result.recall_result.focus is not None
    assert result.recall_result.recall_result.focus.pid == "p:discovered:skill_resume_math"
    assert result.recall_result.dialogue_result is not None
    assert result.recall_result.dialogue_result.emitted_tokens == ("continue::math",)


def test_phase5_8_work_memory_item_is_state_field_pool_entry() -> None:
    result = APV3WorkMemoryRuntime().run_tick(
        _base_state(),
        WorkMemoryTickInput(tick=10, focus_tokens=("goal::solve", "item::math"), pressure=0.95),
    )
    items = result.state["state_field_items"]
    pool_entry = next(item for item in items if item["sa_type"] == "work_memory_unfinished")

    assert pool_entry["sa_bundle"] == ["goal::solve", "item::math"]
    assert pool_entry["energy"]["P"] == 0.95
    assert pool_entry["energy"]["A"] == 0.95


def test_phase5_8_capacity_retains_high_pressure_item_over_recent_noise() -> None:
    runtime = APV3WorkMemoryRuntime()
    runtime.config = runtime.config.__class__(max_items=1)
    state = runtime.run_tick(
        _base_state(),
        WorkMemoryTickInput(tick=1, focus_tokens=("goal::cook",), pressure=0.95),
    ).state
    state = runtime.run_tick(
        state,
        WorkMemoryTickInput(tick=2, focus_tokens=("noise::brief",), pressure=0.05),
    ).state

    assert len(state["working_memory_items"]) == 1
    assert state["working_memory_items"][0]["sa_bundle"] == ["goal::cook"]


def test_phase5_8_bridge_does_not_emit_without_recalled_work_memory() -> None:
    result = APV3WorkMemoryAttentionBridge().run_idle_recall(_base_state(), tick=10, context_tokens=("ctx_work",))

    assert result.work_memory_result.recalled_item is None
    assert result.recall_result is None
