from __future__ import annotations

from pathlib import Path

from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig
from apv3test.runtime import (
    LearningEpisode,
    LearningEpisodeWriter,
    PerceptObservation,
    PerceptPrototypeStore,
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


def test_same_percept_reuses_stable_token_across_surface_changes() -> None:
    store = PerceptPrototypeStore()

    first = store.observe(
        PerceptObservation(
            "vision_obj::frame1::slot3",
            {"hue": 0.9, "shape": 0.4, "size": 0.5},
            cognitive_pressure=0.9,
            continuity_anchor="object-track-1",
            modality="vision",
            tick=1,
        )
    )
    second = store.observe(
        PerceptObservation(
            "vision_obj::frame2::slot8",
            {"hue": 0.91, "shape": 0.41, "size": 0.5},
            cognitive_pressure=0.2,
            continuity_anchor="object-track-1",
            modality="vision",
            tick=2,
        )
    )

    assert first.token == second.token
    assert second.matched_existing
    assert len(store.prototypes) == 1


def test_distinct_percepts_do_not_overmerge() -> None:
    store = PerceptPrototypeStore()

    first = store.observe(
        PerceptObservation("vision::a", {"hue": 1.0, "shape": 0.0}, 0.9, modality="vision", tick=1)
    )
    second = store.observe(
        PerceptObservation("vision::b", {"hue": 0.0, "shape": 1.0}, 0.9, modality="vision", tick=2)
    )

    assert first.token != second.token
    assert len(store.prototypes) == 2


def test_prototype_limit_is_bounded_by_support_and_recency() -> None:
    config = APV3ParadigmDiscoveryConfig(percept_max_prototypes=2)
    store = PerceptPrototypeStore(config)

    kept = store.observe(PerceptObservation("stable::a", {"x": 1.0, "y": 0.0}, 0.9, tick=1))
    store.observe(PerceptObservation("stable::a2", {"x": 0.99, "y": 0.01}, 0.9, tick=2))
    store.observe(PerceptObservation("new::b", {"x": 0.0, "y": 1.0}, 0.9, tick=3))
    store.observe(PerceptObservation("new::c", {"x": -1.0, "y": 0.0}, 0.9, tick=4))

    tokens = {proto.token for proto in store.prototypes}
    assert len(store.prototypes) == 2
    assert kept.token in tokens


def test_percept_prototypes_persist_through_learning_writer_and_sqlite(tmp_path: Path) -> None:
    store = PerceptPrototypeStore()
    store.observe(PerceptObservation("vision::yellowish", {"hue": 0.9, "shape": 0.4}, 0.9, modality="vision", tick=1))
    episode = LearningEpisode("percept:episode", percept_prototypes=store.to_learned_prototypes())
    state = LearningEpisodeWriter().apply(_blank_state(), episode)

    runtime = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")
    state_id = runtime.save_state(state)
    restored = runtime.load_state(state_id)
    projection = runtime.load_ontology_projection(state_id)

    assert restored["percept_prototypes"][0]["features"]["token"].startswith("percept::prototype::")
    assert projection["percept_prototypes"][0]["features"]["modality_mix"] == ["vision"]


def test_percept_prototype_is_prerequisite_not_cross_modal_claim() -> None:
    store = PerceptPrototypeStore()
    vision = store.observe(
        PerceptObservation("vision::yellow", {"tone": 0.8, "shape": 0.2}, 0.9, modality="vision", tick=1)
    )
    audio = store.observe(
        PerceptObservation("audio::yellow_word", {"tone": 0.79, "shape": 0.21}, 0.9, modality="audio", tick=2)
    )

    assert vision.token == audio.token
    assert set(store.prototypes[0].modality_mix) == {"vision", "audio"}
    assert "cross_modal_generalization_proven" not in store.to_learned_prototypes()[0].features
