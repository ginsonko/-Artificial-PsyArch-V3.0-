from __future__ import annotations

from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


def bind_name_to_cluster(cluster: StateItem, *, name_sa_id: str) -> StateItem | None:
    """@op_count: O(1)."""
    if cluster.family != "anonymous_cluster":
        return None
    confidence = cluster.real_energy * float(load_constant("hierarchy.name_binding_gain"))
    return StateItem(
        sa_id=f"VocabSA::hierarchy::{name_sa_id}->{cluster.sa_id}",
        family="hierarchy",
        label="named_hierarchy",
        real_energy=confidence,
        cognitive_pressure=confidence,
        channel_signature=("hierarchy",),
        source="name_binding",
        metadata={
            "name_sa_id": name_sa_id,
            "cluster_sa_id": cluster.sa_id,
            "member_sa_ids": tuple(cluster.metadata.get("member_sa_ids", ())),
            "relation": "is_a_cluster",
        },
    )


def part_of_relation(part_sa_id: str, whole_sa_id: str, *, confidence: float) -> StateItem:
    """@op_count: O(1)."""
    value = min(1.0, max(0.0, float(confidence)))
    return StateItem(
        sa_id=f"VocabSA::hierarchy::part_of::{part_sa_id}->{whole_sa_id}",
        family="hierarchy",
        label="part_of",
        real_energy=value,
        cognitive_pressure=value,
        channel_signature=("hierarchy", "part_of"),
        source="part_whole_relation",
        metadata={
            "part_sa_id": part_sa_id,
            "whole_sa_id": whole_sa_id,
            "relation": "part_of",
        },
    )
