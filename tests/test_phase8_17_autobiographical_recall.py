from __future__ import annotations

from runtime.cognitive.long_term.autobiographical import (
    AutobiographicalMemory,
    EntityAnchor,
)


def test_autobiographical_recall_requires_entity_anchor_and_emits_remembered_marker() -> None:
    memory = AutobiographicalMemory()
    memory.add_episode(
        episode_id="ep::first_teaching",
        cue_sa_ids=("vision::shape::apple",),
        entity_anchors=(EntityAnchor("entity::user", "teacher"),),
        support=0.9,
        created_tick=3,
    )

    recalls = memory.recall(
        cue_sa_ids=("vision::shape::apple",),
        entity_id="entity::user",
        tick=12,
    )

    assert recalls
    assert recalls[0].episode.episode_id == "ep::first_teaching"
    assert recalls[0].marker.kind == "REMEMBERED"
    assert "entity::user" in recalls[0].item.metadata["entity_anchors"]


def test_autobiographical_recall_does_not_cross_entity_anchor() -> None:
    memory = AutobiographicalMemory()
    memory.add_episode(
        episode_id="ep::private",
        cue_sa_ids=("text::cue::hello",),
        entity_anchors=(EntityAnchor("entity::user_a", "speaker"),),
        support=0.8,
        created_tick=4,
    )

    recalls = memory.recall(
        cue_sa_ids=("text::cue::hello",),
        entity_id="entity::user_b",
        tick=20,
    )

    assert recalls == ()
