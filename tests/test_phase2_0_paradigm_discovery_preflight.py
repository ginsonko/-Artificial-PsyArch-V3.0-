from __future__ import annotations

from pathlib import Path

from apv3test.runtime import (
    LearningEpisodeWriter,
    ParadigmDiscoveryEngine,
    ParadigmObservation,
    ParityProbeCase,
    SQLiteRuntimeStore,
    assert_probe_parity,
    run_parity_probe,
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


def test_discovers_fixed_successor_from_repeated_observations() -> None:
    engine = ParadigmDiscoveryEngine()
    discovered = engine.discover(
        [
            ParadigmObservation("greeting_discovered", ("你", "好"), ("我", "在", "。")),
            ParadigmObservation("greeting_discovered", ("你", "好"), ("我", "在", "。")),
        ]
    )

    state = LearningEpisodeWriter().apply(_blank_state(), engine.to_learning_episode("discover:greeting", discovered))
    result = run_parity_probe(
        state,
        [
            ParityProbeCase(
                "greeting_discovered",
                "你好",
                "type_char",
                ("你好", "我在。"),
                "memory:discovered:greeting_discovered",
                "我在。",
                "p:discovered:greeting_discovered",
            )
        ],
    )[0]

    assert discovered[0].fixed_prefix == ("我", "在", "。")
    assert discovered[0].slot_spans == ()
    assert result.bn_top[0]["candidate_id"] == "memory:discovered:greeting_discovered"
    assert result.cn_successors[0]["target"] == "我在。"
    assert result.paradigms[0]["pid"] == "p:discovered:greeting_discovered"


def test_discovers_shared_fragment_and_slot_from_multiple_replies() -> None:
    engine = ParadigmDiscoveryEngine()
    discovered = engine.discover(
        [
            ParadigmObservation("idiom_multi_reply", ("三", "顾"), ("茅", "庐")),
            ParadigmObservation("idiom_multi_reply", ("三", "顾"), ("臣", "于", "草", "庐")),
        ]
    )

    item = discovered[0]

    assert item.fixed_prefix == ()
    assert item.shared_suffix == ("庐",)
    assert item.slot_spans == (("茅",), ("臣", "于", "草"))
    episode = engine.to_learning_episode("discover:idiom", discovered)
    assert "slot" in episode.paradigms[0].slot_types
    assert "shared_fragment" in episode.paradigms[0].slot_types


def test_discovered_paradigm_survives_sqlite_restore_and_recall(tmp_path: Path) -> None:
    engine = ParadigmDiscoveryEngine()
    discovered = engine.discover(
        [
            ParadigmObservation("yellow_object", ("黄", "色", "物", "体"), ("黄", "色", "苹", "果")),
            ParadigmObservation("yellow_object", ("黄", "色", "物", "体"), ("黄", "色", "香", "蕉")),
        ]
    )
    state = LearningEpisodeWriter().apply(_blank_state(), engine.to_learning_episode("discover:yellow_object", discovered))
    cases = [
        ParityProbeCase(
            "yellow_object",
            "黄色物体",
            "compose_slots",
            ("黄色物体", "黄色苹果"),
            "memory:discovered:yellow_object",
            "黄色苹果",
            "p:discovered:yellow_object",
        )
    ]
    memory_results = run_parity_probe(state, cases)
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(state)
    restored = store.load_state(state_id)
    restored_results = run_parity_probe(restored, cases)

    assert_probe_parity(memory_results, restored_results)
    projection = store.load_ontology_projection(state_id)
    paradigm_ids = {row["pid"] for row in projection["paradigm_sa"]}
    assert "p:discovered:yellow_object" in paradigm_ids
