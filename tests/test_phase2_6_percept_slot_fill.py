from __future__ import annotations

from pathlib import Path

from apv3test.runtime import (
    LearningEpisode,
    LearningEpisodeWriter,
    ParadigmDiscoveryEngine,
    ParadigmObservation,
    ParadigmSlotFiller,
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


def _color_object_paradigm():
    return ParadigmDiscoveryEngine().discover(
        [
            ParadigmObservation(
                "color_object_slots",
                ("describe",),
                ("field::color", "percept::red", "field::object", "percept::apple"),
            ),
            ParadigmObservation(
                "color_object_slots",
                ("describe",),
                ("field::color", "percept::blue", "field::object", "percept::cup"),
            ),
            ParadigmObservation(
                "color_object_slots",
                ("describe",),
                ("field::color", "percept::green", "field::object", "percept::leaf"),
            ),
            ParadigmObservation(
                "color_object_slots",
                ("describe",),
                ("field::color", "percept::yellow", "field::object", "percept::banana"),
            ),
        ]
    )[0]


def test_percept_tokens_fill_color_object_slots_without_target_phrase() -> None:
    paradigm = _color_object_paradigm()
    drafts = ParadigmSlotFiller().fill(
        paradigm,
        focus_tokens=("percept::yellow", "percept::apple"),
        candidate_pool=("percept::yellow", "percept::apple"),
    )

    slot_labels = tuple(draft.label for draft in drafts if draft.role == "slot")

    assert slot_labels == ("percept::yellow", "percept::apple")
    assert tuple(draft.role for draft in drafts) == ("fixed_anchor", "slot", "fixed_anchor", "slot")
    assert "".join(slot_labels) != "黄色苹果"
    assert drafts[-1].anchor_meta["previous_prefix"].endswith("field::object")


def test_successor_virtuals_can_supply_missing_slot_candidate_without_bypassing_competition() -> None:
    paradigm = _color_object_paradigm()
    drafts = ParadigmSlotFiller().fill(
        paradigm,
        focus_tokens=("percept::yellow",),
        candidate_pool=("percept::yellow",),
        successor_virtuals={"percept::apple": 0.9},
    )

    slot_drafts = tuple(draft for draft in drafts if draft.role == "slot")
    assert tuple(draft.label for draft in slot_drafts) == ("percept::yellow", "percept::apple")
    assert "successor_virtual" in str(slot_drafts[1].anchor_meta["source"])
    assert slot_drafts[1].strength > 0.0


def test_percept_slot_fill_uses_persisted_prototype_tokens_after_restore(tmp_path: Path) -> None:
    proto_store = PerceptPrototypeStore()
    yellow = proto_store.observe(
        PerceptObservation("vision::yellow", {"hue": 0.9, "shape": 0.1}, 0.9, modality="vision", tick=1)
    )
    apple = proto_store.observe(
        PerceptObservation("vision::apple", {"hue": 0.2, "shape": 0.95}, 0.9, modality="vision", tick=2)
    )
    state = LearningEpisodeWriter().apply(
        _blank_state(),
        LearningEpisode("percept:yellow_apple", percept_prototypes=proto_store.to_learned_prototypes()),
    )
    runtime = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")
    restored = runtime.load_state(runtime.save_state(state))
    restored_tokens = tuple(item["features"]["token"] for item in restored["percept_prototypes"])
    paradigm = _color_object_paradigm()

    drafts = ParadigmSlotFiller().fill(
        paradigm,
        focus_tokens=restored_tokens,
        candidate_pool=restored_tokens,
    )

    assert tuple(draft.label for draft in drafts if draft.role == "slot") == (yellow.token, apple.token)


def test_slot_fill_does_not_create_full_sentence_macro_or_reward_self_emission() -> None:
    paradigm = _color_object_paradigm()

    drafts = ParadigmSlotFiller().fill(
        paradigm,
        focus_tokens=("percept::yellow", "percept::apple"),
        candidate_pool=("percept::yellow", "percept::apple"),
    )

    assert len(drafts) == 4
    assert all(draft.anchor_meta["schema_id"] == "text_visible_draft_token/v1" for draft in drafts)
    assert not hasattr(ParadigmSlotFiller(), "commit")


def test_all_slot_cold_start_paradigm_is_not_exposed_without_relation_evidence() -> None:
    paradigm = ParadigmDiscoveryEngine().discover(
        [
            ParadigmObservation("bare_color_object", ("describe",), ("percept::red", "percept::apple")),
            ParadigmObservation("bare_color_object", ("describe",), ("percept::blue", "percept::cup")),
            ParadigmObservation("bare_color_object", ("describe",), ("percept::green", "percept::leaf")),
        ]
    )[0]

    drafts = ParadigmSlotFiller().fill(
        paradigm,
        focus_tokens=("percept::yellow", "percept::apple"),
        candidate_pool=("percept::yellow", "percept::apple"),
    )

    assert paradigm.conf == 0.0
    assert drafts == ()
