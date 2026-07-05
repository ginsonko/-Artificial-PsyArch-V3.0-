from __future__ import annotations

from runtime.cognitive.composed_vocab.contrast_generalization import contrast_pairwise_margin
from runtime.cognitive.composed_vocab.delta_p_cold_fork import (
    VocabCandidate,
    evaluate_delta_p_incremental,
)
from runtime.cognitive.composed_vocab.held_out_pool import HeldOutPool
from runtime.cognitive.composed_vocab.sparse_pairwise import SparsePairwiseGraph
from runtime.cognitive.sdpl.packet import make_packet
from runtime.cognitive.state_pool.state_pool import StateItem


def _item(sa_id: str) -> StateItem:
    return StateItem(
        sa_id=sa_id,
        family="percept",
        label=sa_id,
        real_energy=0.8,
        cognitive_pressure=0.4,
        channel_signature=("vision",),
    )


def _observe(graph: SparsePairwiseGraph, *ids: str) -> None:
    graph.observe_packet(make_packet(content_sas=tuple(_item(sa_id) for sa_id in ids)))


def test_contrast_curriculum_separates_target_pair_from_distractors_without_labels() -> None:
    graph = SparsePairwiseGraph()
    target_color = "vision::color::c_target"
    target_shape = "vision::shape::s_target"
    other_color = "vision::color::c_other"
    other_shape = "vision::shape::s_other"

    for _ in range(12):
        _observe(graph, target_color, target_shape, "vision::x_bucket::left")
    for _ in range(4):
        _observe(graph, target_color, other_shape, "vision::x_bucket::right")
        _observe(graph, other_color, target_shape, "vision::x_bucket::left")

    trace = contrast_pairwise_margin(
        graph,
        target_pair=(target_color, target_shape),
        distractor_pairs=((target_color, other_shape), (other_color, target_shape)),
    )

    assert trace.separates_target is True
    assert trace.target_count > trace.strongest_distractor_count


def test_delta_p_gate_promotes_joint_visual_candidate_and_rejects_single_slot_ablation() -> None:
    target_color = "vision::color::c_target"
    target_shape = "vision::shape::s_target"
    held_out = HeldOutPool()
    current = (_item(target_color), _item(target_shape))

    for index in range(50):
        held_out.add_items(f"held::{index}", (_item(target_color), _item(target_shape)))

    joint = evaluate_delta_p_incremental(
        VocabCandidate(
            candidate_id="vocab::joint",
            component_ids=(target_color, target_shape),
            predicted_pressure_reduction=0.2,
        ),
        current,
        held_out,
    )
    ablated = evaluate_delta_p_incremental(
        VocabCandidate(
            candidate_id="vocab::ablated",
            component_ids=(target_shape,),
            predicted_pressure_reduction=0.2,
        ),
        current,
        held_out,
    )

    assert joint.passes is True
    assert ablated.passes is False
    assert ablated.reason == "insufficient_components"
