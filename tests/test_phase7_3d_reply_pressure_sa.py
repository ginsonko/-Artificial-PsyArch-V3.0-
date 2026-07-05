from __future__ import annotations

import ast
import inspect

from apv3test.config.introspection_config import APV3ReplyPressureConfig
from apv3test.runtime import (
    IncrementalTickInput,
    IncrementalTickRuntime,
    derive_reply_pressure_sa,
    reply_pressure_requires_response,
    update_reply_pressure_state,
)
from apv3test.runtime import reply_pressure as reply_pressure_module


SAN = "\u4e09"
GU = "\u987e"
MAO = "\u8305"
LU = "\u5e90"
CAO = "\u8349"
ZHI = "\u4e4b"
ZHONG = "\u4e2d"


def _base_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "ctx_idiom": {"vector": [0.0, 1.0], "support": 4.0, "promoted": True},
                "ctx_expression": {"vector": [1.0, 0.0], "support": 4.0, "promoted": True},
            }
        },
        "transitions": [],
        "paradigms": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def _teach(
    tick: int,
    *,
    case_name: str,
    cue_tokens: tuple[str, ...],
    reply_tokens: tuple[str, ...],
    context_tokens: tuple[str, ...],
) -> IncrementalTickInput:
    return IncrementalTickInput(
        tick=tick,
        case_name=case_name,
        cue_tokens=cue_tokens,
        reply_tokens=reply_tokens,
        context_tokens=context_tokens,
        commit_observation=True,
        reward_delta=1.0,
    )


def _teach_multi_reply(state: dict, runtime: IncrementalTickRuntime) -> dict:
    for step in tuple(
        _teach(
            tick,
            case_name="phase7_3d_multi_reply",
            cue_tokens=(SAN, GU),
            reply_tokens=(MAO, LU),
            context_tokens=("ctx_idiom",),
        )
        for tick in range(1, 31)
    ) + tuple(
        _teach(
            tick,
            case_name="phase7_3d_multi_reply",
            cue_tokens=(SAN, GU),
            reply_tokens=(CAO, LU, ZHI, ZHONG),
            context_tokens=("ctx_idiom",),
        )
        for tick in range(31, 61)
    ):
        state = runtime.run_tick(state, step).state
    return state


def test_phase7_3d_external_query_ingest_creates_reply_pressure_without_scalar_switch() -> None:
    runtime = IncrementalTickRuntime()
    result = runtime.run_tick(
        _base_state(),
        IncrementalTickInput(tick=1, incoming_external_query=("你", "说", "呢")),
    )

    inputs = result.state["introspection_pressure_inputs"]
    assert any(item["sa_type"] == "external_query" and item["sa_kind"] == "external_demand" for item in inputs)
    pressure = result.state["introspection_pressure"][0]
    assert pressure["sa_type"] == "reply_pressure"
    assert pressure["real_energy"] >= APV3ReplyPressureConfig().reply_pressure_threshold
    assert "provenance" not in pressure
    assert "contributions" not in pressure
    assert result.state["reply_pressure_traces"][-1]["contributions"]


def test_phase7_3d_reply_pressure_uses_sa_kind_not_sa_type_open_policy() -> None:
    state = {
        "state_field_items": [
            {"sa_label": "x", "sa_type": "arbitrary_name", "sa_kind": "external_demand", "real_energy": 1.0},
            {"sa_label": "ignored", "sa_type": "external_query", "real_energy": 1.0},
        ]
    }

    pressure, trace = derive_reply_pressure_sa(state, current_tick=1)

    assert pressure.real_energy >= APV3ReplyPressureConfig().reply_pressure_threshold
    assert len(trace.contributions) == 1
    assert trace.contributions[0]["sa_label"] == "x"


def test_phase7_3d_external_query_pressure_decays_per_tick() -> None:
    cfg = APV3ReplyPressureConfig(pressure_half_life_decay=0.5, pressure_eviction_floor=0.001)
    state = update_reply_pressure_state(
        {},
        current_tick=1,
        incoming_external_query=("question",),
        config=cfg,
    )
    first = next(item for item in state["introspection_pressure_inputs"] if item["sa_type"] == "external_query")
    for tick in range(2, 5):
        state = update_reply_pressure_state(state, current_tick=tick, config=cfg)
    latest = next(item for item in state["introspection_pressure_inputs"] if item["sa_type"] == "external_query")

    assert abs(latest["real_energy"] - first["real_energy"] * (0.5 ** 3)) < 1e-6


def test_phase7_3d_silence_resets_on_commit_and_decays_after_saturation() -> None:
    cfg = APV3ReplyPressureConfig(silence_normalizer_ticks=2, silence_half_life_decay=0.5)
    state = {"last_commit_tick": 0}
    state = update_reply_pressure_state(state, current_tick=2, config=cfg)
    silence_before = next(item for item in state["introspection_pressure_inputs"] if item["sa_type"] == "silence")
    assert silence_before["real_energy"] > 0.9

    state = update_reply_pressure_state(state, current_tick=8, config=cfg)
    silence_long = next((item for item in state["introspection_pressure_inputs"] if item["sa_type"] == "silence"), None)
    assert silence_long is None or silence_long["real_energy"] < 0.03

    state = update_reply_pressure_state(state, current_tick=9, commit_happened=True, config=cfg)
    assert not any(item["sa_type"] == "silence" for item in state["introspection_pressure_inputs"])
    assert any(item["sa_type"] == "recent_commit" and item["sa_kind"] == "recent_action" for item in state["introspection_pressure_inputs"])
    assert state["introspection_pressure"][0]["real_energy"] < cfg.reply_pressure_neutral


def test_phase7_3d_reply_pressure_runtime_has_no_provenance_field_access() -> None:
    tree = ast.parse(inspect.getsource(reply_pressure_module))
    forbidden = {"provenance", "sources", "dominant_source"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden
