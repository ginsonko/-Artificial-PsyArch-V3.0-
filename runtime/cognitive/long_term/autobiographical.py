from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from runtime.cognitive.long_term.rehydration import spawn_remembered
from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StateItem


@dataclass(frozen=True)
class EntityAnchor:
    entity_id: str
    relation: str


@dataclass(frozen=True)
class AutobiographicalEpisode:
    episode_id: str
    cue_sa_ids: tuple[str, ...]
    entity_anchors: tuple[EntityAnchor, ...]
    support: float
    created_tick: int


@dataclass(frozen=True)
class AutobiographicalRecall:
    episode: AutobiographicalEpisode
    item: StateItem
    marker: MarkerEvent


class AutobiographicalMemory:
    def __init__(self, episodes: Iterable[AutobiographicalEpisode] = ()) -> None:
        self.episodes = list(episodes)

    def add_episode(
        self,
        *,
        episode_id: str,
        cue_sa_ids: Iterable[str],
        entity_anchors: Iterable[EntityAnchor],
        support: float,
        created_tick: int,
    ) -> AutobiographicalEpisode:
        """@op_count: O(cue_count + entity_count)."""
        episode = AutobiographicalEpisode(
            episode_id=episode_id,
            cue_sa_ids=tuple(cue_sa_ids),
            entity_anchors=tuple(entity_anchors),
            support=float(support),
            created_tick=int(created_tick),
        )
        self.episodes.append(episode)
        return episode

    def recall(
        self,
        *,
        cue_sa_ids: Iterable[str],
        entity_id: str,
        tick: int,
    ) -> tuple[AutobiographicalRecall, ...]:
        """@op_count: O(episodes * cues * anchors)."""
        cue_set = set(cue_sa_ids)
        recalls: list[AutobiographicalRecall] = []
        for episode in self.episodes:
            if not cue_set.intersection(episode.cue_sa_ids):
                continue
            if entity_id not in {anchor.entity_id for anchor in episode.entity_anchors}:
                continue
            item = _episode_item(episode)
            marker = spawn_remembered(item, tick=tick, cue_alignment=1.0)
            recalls.append(AutobiographicalRecall(episode=episode, item=item, marker=marker))
        return tuple(sorted(recalls, key=lambda recall: (recall.episode.support, recall.episode.created_tick), reverse=True))


def _episode_item(episode: AutobiographicalEpisode) -> StateItem:
    return StateItem(
        sa_id=f"episode::{episode.episode_id}",
        family="episode",
        label=episode.episode_id,
        real_energy=episode.support,
        cognitive_pressure=0.0,
        source="autobiographical_memory",
        metadata={
            "long_term_layer": True,
            "long_term_R": episode.support,
            "entity_anchors": tuple(anchor.entity_id for anchor in episode.entity_anchors),
            "cue_sa_ids": episode.cue_sa_ids,
        },
    )
