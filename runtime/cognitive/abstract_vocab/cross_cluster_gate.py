from __future__ import annotations

from typing import Iterable

from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


def spawn_abstract_vocab_from_clusters(clusters: Iterable[StateItem], *, abstract_label: str) -> StateItem | None:
    """@op_count: O(cluster_count * relation_count)."""
    cluster_tuple = tuple(clusters)
    if len(cluster_tuple) < int(load_constant("abstract_vocab.min_source_clusters")):
        return None
    relation_sets = tuple(_relation_set(cluster) for cluster in cluster_tuple)
    shared_relations = _shared_relations(relation_sets)
    if len(shared_relations) < int(load_constant("abstract_vocab.min_shared_relations")):
        return None
    diversity = len({cluster.sa_id for cluster in cluster_tuple})
    if diversity < int(load_constant("abstract_vocab.cluster_diversity_min")):
        return None
    overlap = _overlap_score(relation_sets, shared_relations)
    if overlap < float(load_constant("abstract_vocab.relation_similarity_min")):
        return None
    return StateItem(
        sa_id=f"VocabSA::abstract::{abstract_label}",
        family="abstract_vocab",
        label="cross_cluster_abstract",
        real_energy=overlap,
        cognitive_pressure=overlap,
        channel_signature=("abstract_vocab",),
        source="cross_cluster_gate",
        metadata={
            "abstract_label": abstract_label,
            "source_cluster_sa_ids": tuple(cluster.sa_id for cluster in cluster_tuple),
            "shared_relations": shared_relations,
            "relation_overlap": overlap,
        },
    )


def _relation_set(cluster: StateItem) -> set[str]:
    relations = set(str(value) for value in cluster.metadata.get("shared_slots", ()))
    relations.update(str(value) for value in cluster.metadata.get("shared_channel_signature", ()))
    relation = cluster.metadata.get("relation")
    if relation:
        relations.add(str(relation))
    return relations


def _shared_relations(relation_sets: tuple[set[str], ...]) -> tuple[str, ...]:
    shared = set(relation_sets[0]) if relation_sets else set()
    for relation_set in relation_sets[1:]:
        shared &= relation_set
    return tuple(sorted(shared))


def _overlap_score(relation_sets: tuple[set[str], ...], shared_relations: tuple[str, ...]) -> float:
    denominator = max(float(max((len(item) for item in relation_sets), default=0)), 1.0)
    return min(1.0, float(len(shared_relations)) / denominator)
