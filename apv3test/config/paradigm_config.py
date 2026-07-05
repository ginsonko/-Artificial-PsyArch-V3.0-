from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class APV3ParadigmDiscoveryConfig:
    """Named parameters for minimal paradigm discovery.

    This is the Phase2 preflight gate, not the full v2.1 alignment engine. The
    values are explicit so later AdaptiveTuner ownership has clear names.
    """

    min_support: int = 2
    support_half_life: float = 3.0
    anchor_quality_default: float = 0.8
    slot_quality_default: float = 0.7
    candidate_feature_floor: float = 0.05
    alignment_match_reward: float = 1.0
    alignment_mismatch_penalty: float = -0.8
    alignment_gap_penalty: float = -0.55
    alignment_max_len: int = 64
    alignment_max_window: int = 24
    fixed_occupancy_min: float = 0.999
    shared_occupancy_min: float = 0.5
    boundary_threshold: float = 0.62
    boundary_continuity_weight: float = 0.45
    boundary_quantity_weight: float = 0.85
    boundary_step_closure_weight: float = 1.0
    boundary_pressure_release_weight: float = 1.0
    boundary_rhythm_weight: float = 0.75
    coherence_neighbor_window: int = 1
    coherence_min_for_slot_quality: float = 0.34
    confidence_evidence_gamma: float = 1.0
    confidence_anchor_gamma: float = 1.0
    confidence_slot_gamma: float = 1.0
    role_viterbi_fixed_match_reward: float = 1.25
    role_viterbi_shared_match_reward: float = 1.2
    role_viterbi_slot_coherence_reward: float = 0.8
    role_viterbi_slot_diversity_reward: float = 0.35
    role_viterbi_same_role_reward: float = 0.08
    role_viterbi_fixed_to_slot_reward: float = 0.12
    role_viterbi_slot_to_shared_reward: float = 0.2
    role_viterbi_shared_to_slot_penalty: float = -0.35
    percept_match_threshold: float = 0.78
    percept_spawn_pressure_threshold: float = 0.35
    percept_merge_rate: float = 0.35
    percept_max_prototypes: int = 128
    slot_fill_focus_weight: float = 1.0
    slot_fill_relation_weight: float = 0.8
    slot_fill_successor_weight: float = 0.7
    slot_fill_min_score: float = 0.05
    incremental_dirty_bucket_limit: int = 32
    role_transition_weak_prior_scale: float = 1.0
    role_transition_support_weight: float = 0.18
    role_transition_reward_weight: float = 0.32
    role_transition_punish_weight: float = 0.42
    role_transition_context_similarity_min: float = 0.72
    paradigm_exposure_reward_weight: float = 0.2
    paradigm_exposure_punish_block_threshold: float = 0.58
    bn_recall_cue_weight: float = 0.42
    bn_recall_context_weight: float = 0.18
    bn_recall_conf_weight: float = 0.18
    bn_recall_support_weight: float = 0.12
    cn_successor_observation_weight: float = 0.62
    cn_successor_transition_weight: float = 0.38
    attention_bn_weight: float = 0.45
    attention_cn_weight: float = 0.35
    attention_energy_weight: float = 0.2
    additional_evidence_band_repeats: int = 1
