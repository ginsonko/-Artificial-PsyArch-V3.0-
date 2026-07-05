from __future__ import annotations

from pathlib import Path

from apv3test.runtime import (
    IncrementalParadigmLearner,
    IncrementalParadigmObservation,
    ParadigmDiscoveryEngine,
    ParadigmObservation,
    RoleTransitionStats,
    SQLiteRuntimeStore,
    promoted_context_similarity,
)


def _base_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {"tokens": {}},
        "transitions": [],
        "paradigms": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def _obs(
    observation_id: str,
    case_name: str,
    cue: tuple[str, ...],
    reply: tuple[str, ...],
    tick: int,
    *,
    context: tuple[str, ...] = (),
    source_kind: str = "natural",
    reward: float = 0.0,
    punish: float = 0.0,
) -> IncrementalParadigmObservation:
    return IncrementalParadigmObservation(
        observation_id=observation_id,
        case_name=case_name,
        cue_tokens=cue,
        reply_tokens=reply,
        tick_id=tick,
        context_tokens=context,
        source_kind=source_kind,
        reward_delta=reward,
        punish_delta=punish,
        teacher_stage="successor_prediction",
    )


def test_incremental_ingest_updates_dirty_bucket_and_keeps_paradigm_as_pool_entry() -> None:
    learner = IncrementalParadigmLearner()

    first = learner.ingest(_base_state(), _obs("o1", "greeting", ("你", "好"), ("我", "在"), 1))
    assert first.discovered is None
    assert first.dirty_buckets == ("greeting|你 好",)
    assert first.state["paradigms"] == []

    second = learner.ingest(first.state, _obs("o2", "greeting", ("你", "好"), ("我", "在"), 2))

    assert second.discovered is not None
    assert second.discovered.pid == "p:discovered:greeting"
    assert second.state["paradigm_stats"]["greeting|你 好"]["support"] == 2.0
    assert second.state["paradigms"][0]["entry_kind"] == "ParadigmSA"
    assert second.state["paradigms"][0]["anchor_meta"]["stats_ref"] == "paradigm_stats:greeting|你 好"
    assert second.state["state_field_items"][0]["sa_type"] == "paradigm_sa"


def test_incremental_bucket_matches_batch_discovery_without_global_recompute() -> None:
    learner = IncrementalParadigmLearner()
    state = _base_state()
    observations = [
        _obs("g1", "greeting", ("你", "好"), ("我", "在"), 1),
        _obs("i1", "idiom", ("三", "顾"), ("茅", "庐"), 2),
        _obs("g2", "greeting", ("你", "好"), ("我", "在"), 3),
        _obs("i2", "idiom", ("三", "顾"), ("茅", "庐"), 4),
    ]
    for item in observations:
        state = learner.ingest(state, item).state

    batch = ParadigmDiscoveryEngine().discover(
        [
            ParadigmObservation("greeting", ("你", "好"), ("我", "在")),
            ParadigmObservation("greeting", ("你", "好"), ("我", "在")),
            ParadigmObservation("idiom", ("三", "顾"), ("茅", "庐")),
            ParadigmObservation("idiom", ("三", "顾"), ("茅", "庐")),
        ]
    )
    batch_pids = {item.pid for item in batch}
    incremental_pids = {item["pid"] for item in state["paradigms"]}

    assert incremental_pids == batch_pids
    assert state["dirty_paradigm_buckets"][0] == "idiom|三 顾"
    assert state["paradigm_stats"]["greeting|你 好"]["support"] == 2.0


def test_role_transition_bias_uses_promoted_vectors_for_similar_context() -> None:
    state = _base_state()
    state["online_embedding"]["tokens"] = {
        "ctx_math": {"vector": [1.0, 0.0], "support": 4.0, "promoted": True},
        "ctx_math_near": {"vector": [0.96, 0.04], "support": 4.0, "promoted": True},
        "ctx_unpromoted_near": {"vector": [0.97, 0.03], "support": 4.0, "promoted": False},
    }
    stats = RoleTransitionStats()
    stats.learn(
        state,
        ("fixed_anchor", "slot", "shared_fragment"),
        context_tokens=("ctx_math",),
        committed=True,
        reward_delta=2.0,
        punish_delta=0.0,
        tick_id=10,
        provenance="role:math",
    )

    near_bias = stats.bias_map(state, current_context_tokens=("ctx_math_near",), current_tick=11)
    blocked_bias = stats.bias_map(state, current_context_tokens=("ctx_unpromoted_near",), current_tick=11)

    assert near_bias[("fixed_anchor", "slot")] > 0.0
    assert blocked_bias == {}
    assert promoted_context_similarity(state, ("ctx_math",), ("ctx_unpromoted_near",)) == 0.0


def test_recent_punishment_blocks_exposure_then_decays_with_action_outcome_style_recency() -> None:
    learner = IncrementalParadigmLearner()
    state = _base_state()
    state = learner.ingest(state, _obs("p1", "repairable", ("问",), ("答",), 1)).state
    state = learner.ingest(state, _obs("p2", "repairable", ("问",), ("答",), 2)).state

    punished = learner.ingest(
        state,
        _obs("p3", "repairable", ("问",), ("答",), 3, punish=8.0),
    )
    assert punished.state["paradigm_stats"]["repairable|问"]["exposed"] is False
    assert punished.state["paradigms"][0]["exposed"] is False

    recovered = learner.ingest(
        punished.state,
        _obs("p4", "repairable", ("问",), ("答",), 300, reward=4.0),
    )
    assert recovered.state["paradigm_stats"]["repairable|问"]["punish_pressure"] < 0.01
    assert recovered.state["paradigms"][0]["exposed"] is True


def test_natural_and_llm_standard_teaching_write_equivalent_runtime_evidence() -> None:
    learner = IncrementalParadigmLearner()
    natural = learner.ingest_many(
        _base_state(),
        [
            _obs("n1", "hello_skill", ("你", "好"), ("我", "在"), 1, source_kind="natural"),
            _obs("n2", "hello_skill", ("你", "好"), ("我", "在"), 2, source_kind="natural"),
        ],
    ).state
    llm = learner.ingest_many(
        _base_state(),
        [
            _obs("l1", "hello_skill", ("你", "好"), ("我", "在"), 1, source_kind="llm_standard_teacher"),
            _obs("l2", "hello_skill", ("你", "好"), ("我", "在"), 2, source_kind="llm_standard_teacher"),
        ],
    ).state

    assert natural["paradigms"] == llm["paradigms"]
    assert natural["paradigm_stats"]["hello_skill|你 好"]["support"] == llm["paradigm_stats"]["hello_skill|你 好"]["support"]
    assert natural["paradigm_observations"][0]["schema_id"] == llm["paradigm_observations"][0]["schema_id"]
    assert "llm_policy" not in str(llm)


def test_incremental_phase5_state_survives_sqlite_restore_and_projection(tmp_path: Path) -> None:
    learner = IncrementalParadigmLearner()
    state = learner.ingest_many(
        _base_state(),
        [
            _obs("s1", "sqlite_skill", ("三", "顾"), ("茅", "庐"), 1),
            _obs("s2", "sqlite_skill", ("三", "顾"), ("茅", "庐"), 2),
        ],
    ).state
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(state)
    restored = store.load_state(state_id)
    projection = store.load_ontology_projection(state_id)

    assert restored["paradigm_stats"] == state["paradigm_stats"]
    assert projection["paradigm_observations"][0]["schema_id"] == "apv3_paradigm_observation/v1"
    assert "sqlite_skill|三 顾" in projection["paradigm_stats"]
    assert projection["paradigm_sa"][0]["entry_kind"] == "ParadigmSA"
