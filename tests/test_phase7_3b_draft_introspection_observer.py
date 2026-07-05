from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from math import log

from apv3test.config.introspection_config import APV3DraftIntrospectionConfig
from apv3test.runtime import IncrementalTickInput, IncrementalTickRuntime
from apv3test.runtime.draft_introspection import (
    IntrospectionPrototype,
    IntrospectionPrototypeStore,
    emit_draft_introspection_feelings,
    extract_facts,
    make_feeling_label,
)


@dataclass(frozen=True)
class _View:
    role: str
    is_filled: bool
    fit_margin: float = 0.7
    occupancy: float = 0.7
    commit_readiness: float = 0.5


def _undecidable_views() -> tuple[_View, ...]:
    return (
        _View("slot", False, fit_margin=0.12, occupancy=0.2, commit_readiness=0.2),
        _View("shared_fragment", True, fit_margin=0.8, occupancy=1.0, commit_readiness=0.4),
    )


def test_phase7_3b_introspection_feeling_emerges_without_teaching_and_uses_subpool() -> None:
    state = {"schema_id": "apv3_runtime_ontology_state/v1", "state_field_items": [{"sa_label": "keep_me"}], "tick": 3}

    result = emit_draft_introspection_feelings(state, _undecidable_views(), current_tick=3)

    feelings = result["introspection_feelings"]
    assert len(feelings) == 1
    assert feelings[0]["sa_type"] == "draft_introspection_feeling"
    assert feelings[0]["sa_label"].startswith("feeling::draft::proto_")
    assert feelings[0]["facts"]["has_shared_after_unresolved"] is True
    assert result["state_field_items"] == [{"sa_label": "keep_me"}]
    assert result["draft_commit_blocked"] is True
    assert result["tick"] == 4


def test_phase7_3b_same_structure_different_content_reuses_prototype_id() -> None:
    state = {"tick": 1}
    first = emit_draft_introspection_feelings(state, _undecidable_views(), current_tick=1)
    second_views = (
        _View("slot", False, fit_margin=0.12, occupancy=0.2, commit_readiness=0.2),
        _View("fixed_anchor", True, fit_margin=0.9, occupancy=1.0, commit_readiness=0.4),
    )
    second = emit_draft_introspection_feelings(first, second_views, current_tick=2)

    labels = [item["sa_label"] for item in second["introspection_feelings"]]
    assert labels[0] == labels[1]


def test_phase7_3b_far_phi_spawns_even_when_single_softmax_would_be_one() -> None:
    cfg = APV3DraftIntrospectionConfig(theta_spawn=1.0, tau_init=0.1)
    store = IntrospectionPrototypeStore(cfg)
    first, r1 = store.respond_or_spawn((0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), current_tick=1)
    second, r2 = store.respond_or_spawn((1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0), current_tick=2)

    assert r1 == 1.0
    assert r2 == 1.0
    assert first.prototype_id != second.prototype_id
    assert len(store.prototypes) == 2


def test_phase7_3b_prototype_id_stays_stable_as_mu_drifts() -> None:
    cfg = APV3DraftIntrospectionConfig(theta_spawn=2.0, tau_init=0.5, eta_mu=0.4)
    store = IntrospectionPrototypeStore(cfg)
    proto, _ = store.respond_or_spawn((0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4), current_tick=1)
    before_id = proto.prototype_id
    before_mu = proto.mu
    for tick in range(2, 20):
        proto, _ = store.respond_or_spawn((0.45, 0.42, 0.43, 0.41, 0.44, 0.4, 0.46), current_tick=tick)

    assert proto.prototype_id == before_id
    assert proto.mu != before_mu
    assert make_feeling_label(proto.prototype_id) == make_feeling_label(before_id)


def test_phase7_3b_decay_is_true_per_tick_half_life() -> None:
    cfg = APV3DraftIntrospectionConfig(half_life_decay=0.5 ** (1 / 8), eviction_floor=0.001)
    store = IntrospectionPrototypeStore(cfg)
    proto, _ = store.respond_or_spawn((0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5), current_tick=0)
    proto.activation_ema = 1.0
    half_life = int(round(log(0.5) / log(cfg.half_life_decay)))
    for tick in range(1, half_life + 1):
        store.decay_unactivated(current_tick=tick)

    assert 0.45 < proto.activation_ema < 0.55
    for tick in range(half_life + 1, 2 * half_life + 1):
        store.decay_unactivated(current_tick=tick)
    assert 0.20 < proto.activation_ema < 0.30


def test_phase7_3b_warmload_preserves_next_id_after_all_prototypes_evicted() -> None:
    cfg = APV3DraftIntrospectionConfig(eviction_floor=0.5, half_life_decay=0.1)
    store = IntrospectionPrototypeStore(cfg)
    proto, _ = store.respond_or_spawn((0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2), current_tick=0)
    assert proto.prototype_id == 0
    exported = store.export_state()
    store.decay_unactivated(current_tick=1)
    empty_export = store.export_state()
    assert empty_export["prototypes"] == []
    assert empty_export["next_id"] == exported["next_id"]

    restored = IntrospectionPrototypeStore.from_state(empty_export, cfg)
    new_proto, _ = restored.respond_or_spawn((0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9), current_tick=2)
    assert new_proto.prototype_id == 1


def test_phase7_3b_tau_updates_from_old_mu_before_mu_moves() -> None:
    cfg = APV3DraftIntrospectionConfig(theta_spawn=10.0, tau_init=0.5, tau_floor=0.0, eta_mu=1.0)
    store = IntrospectionPrototypeStore(cfg)
    proto = IntrospectionPrototype(
        prototype_id=0,
        mu=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        tau=(0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5),
        activation_ema=1.0,
        last_activated_tick=0,
        phi_pooling_schema_version=cfg.phi_pooling_schema_version,
    )
    store = IntrospectionPrototypeStore(cfg, (proto,), next_id=1)
    updated, _ = store.respond_or_spawn((1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0), current_tick=1)

    assert updated.mu == (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
    assert all(value > 0.99 for value in updated.tau)


def test_phase7_3b_phi_pooling_schema_mismatch_invalidates_phi6_only() -> None:
    cfg_v1 = APV3DraftIntrospectionConfig(phi_pooling_schema_version="phi6.draft_to_vec.v1")
    store = IntrospectionPrototypeStore(cfg_v1)
    proto, _ = store.respond_or_spawn((0.1, 0.2, 0.3, 0.4, 0.5, 0.9, 0.7), current_tick=1)
    exported = store.export_state()
    exported["prototypes"][0]["phi_pooling_schema_version"] = "phi6.old"
    cfg_v2 = APV3DraftIntrospectionConfig(phi_pooling_schema_version="phi6.draft_to_vec.v2")
    restored = IntrospectionPrototypeStore.from_state(exported, cfg_v2)

    restored_proto = restored.prototypes[0]
    assert restored_proto.prototype_id == proto.prototype_id
    assert restored_proto.mu[:5] == proto.mu[:5]
    assert restored_proto.mu[5] == 0.0
    assert restored_proto.mu[6] == proto.mu[6]


def test_phase7_3b_extract_facts_uses_is_filled_not_content() -> None:
    facts = extract_facts(_undecidable_views())

    assert facts.has_shared_after_unresolved is True
    assert facts.unresolved_slot_count_norm == 1.0
    assert facts.to_phi()[0] == 1.0


def test_phase7_3b_extract_facts_ast_only_reads_energy_view_contract() -> None:
    tree = ast.parse(inspect.getsource(extract_facts))
    allowed = {"role", "is_filled", "occupancy", "fit_margin", "commit_readiness"}
    forbidden = {
        "filler",
        "value",
        "cue",
        "label",
        "sa_label",
        "anchor_meta",
        "meta",
        "attrs",
        "__dict__",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden
            if isinstance(node.value, ast.Name) and node.value.id in {"view"}:
                assert node.attr in allowed
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "getattr"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"startswith", "endswith", "__contains__"}


def test_phase7_3b_observer_does_not_break_phase7_1_recall_state_field_items() -> None:
    runtime = IncrementalTickRuntime()
    state = {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {"tokens": {"ctx_dialogue": {"vector": [1.0, 0.0], "support": 4.0, "promoted": True}}},
        "transitions": [],
        "paradigms": [],
        "action_outcomes": {},
        "percept_prototypes": [],
        "state_field_items": [{"sa_label": "existing", "sa_type": "sentinel"}],
    }
    for tick in range(1, 8):
        state = runtime.run_tick(
            state,
            IncrementalTickInput(
                tick=tick,
                case_name="phase7_3b_regression",
                cue_tokens=("你", "好"),
                reply_tokens=("我", "在"),
                context_tokens=("ctx_dialogue",),
                commit_observation=True,
                reward_delta=1.0,
            ),
        ).state
    observed = emit_draft_introspection_feelings(state, _undecidable_views(), current_tick=20)

    assert {"sa_label": "existing", "sa_type": "sentinel"} in observed["state_field_items"]
    assert "introspection_feelings" in observed
