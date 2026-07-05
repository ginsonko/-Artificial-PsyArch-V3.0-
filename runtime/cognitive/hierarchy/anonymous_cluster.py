from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass(frozen=True)
class VocabProfile:
    sa_id: str
    slot_preferences: tuple[str, ...]
    channel_signature: tuple[str, ...]


def spawn_anonymous_super_cluster(profiles: Iterable[VocabProfile]) -> StateItem | None:
    """@op_count: O(profile_count^2)."""
    profile_tuple = tuple(profiles)
    min_members = int(load_constant("hierarchy.agglomerative_min_cluster_size"))
    if len(profile_tuple) < min_members:
        return None
    seed = _best_seed(profile_tuple)
    members = tuple(
        profile for profile in profile_tuple
        if _profile_similarity(seed, profile) >= float(load_constant("hierarchy.common_pref_similarity_min"))
    )
    if len(members) < min_members:
        return None
    shared_slots = _shared_slots(members)
    shared_channel = _shared_channel(members)
    return StateItem(
        sa_id="VocabSA::anonymous_cluster::" + "::".join(sorted(profile.sa_id for profile in members)),
        family="anonymous_cluster",
        label="anonymous_super_cluster",
        real_energy=float(len(members)) / max(float(len(profile_tuple)), 1.0),
        cognitive_pressure=float(len(shared_slots)) / max(float(len(seed.slot_preferences)), 1.0),
        channel_signature=("anonymous_cluster",) + shared_channel,
        source="agglomerative_slot_channel",
        metadata={
            "member_sa_ids": tuple(profile.sa_id for profile in members),
            "shared_slots": shared_slots,
            "shared_channel_signature": shared_channel,
        },
    )


def _best_seed(profiles: tuple[VocabProfile, ...]) -> VocabProfile:
    return max(
        profiles,
        key=lambda profile: (
            sum(_profile_similarity(profile, other) for other in profiles),
            profile.sa_id,
        ),
    )


def _profile_similarity(left: VocabProfile, right: VocabProfile) -> float:
    slot_score = _jaccard(left.slot_preferences, right.slot_preferences)
    channel_score = _jaccard(left.channel_signature, right.channel_signature)
    return (
        slot_score * float(load_constant("hierarchy.slot_similarity_weight"))
        + channel_score * float(load_constant("hierarchy.channel_similarity_weight"))
    )


def _jaccard(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    if not union:
        return 0.0
    return float(len(left_set & right_set)) / float(len(union))


def _shared_slots(members: tuple[VocabProfile, ...]) -> tuple[str, ...]:
    shared = set(members[0].slot_preferences)
    for member in members[1:]:
        shared &= set(member.slot_preferences)
    return tuple(sorted(shared))


def _shared_channel(members: tuple[VocabProfile, ...]) -> tuple[str, ...]:
    shared = set(members[0].channel_signature)
    for member in members[1:]:
        shared &= set(member.channel_signature)
    return tuple(sorted(shared))
