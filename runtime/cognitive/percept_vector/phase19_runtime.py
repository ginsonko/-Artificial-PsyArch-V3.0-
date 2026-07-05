from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import wave
from typing import Any, Iterable, Sequence

import numpy as np

from apv3test.runtime.visual_receptor import (
    SensoryCanvas,
    canvas_similarity,
    clarity_field,
    extract_visual_audit_path_v2,
)
from runtime.cognitive.percept_vector.vector_substrate import (
    ConceptPrototype,
    Layer1PerceptVectorStore,
    Layer2PartPrototypeStore,
    Layer3ConceptPrototypeStore,
    PartAssociation,
    PartPrototype,
    PerceptVector,
    TemporalEventBinding,
    assert_opaque_identifier,
    new_opaque_uuid,
)
from runtime.cognitive.state_pool.state_pool import load_constant


PERCEIVED = "PERCEIVED"
EXTERNAL_VISUAL = "EXTERNAL_VISUAL"
EXTERNAL_AUDIO = "EXTERNAL_AUDIO"
SELF_DRAFT_GRID = "SELF_DRAFT_GRID"
RECEPTOR_VERSION_VISUAL = "phase19_0a_foveated"
RECEPTOR_VERSION_AUDIO = "phase19_1a_auditory_foveated"


@dataclass(frozen=True)
class VisualTeachingExample:
    path: Path
    visible_teacher_label: str
    split: str
    tick: int
    substrate: str = EXTERNAL_VISUAL


@dataclass(frozen=True)
class VectorPopulationResult:
    percept_vectors: tuple[PerceptVector, ...]
    part_prototypes: tuple[PartPrototype, ...]
    concepts: tuple[ConceptPrototype, ...]
    stored_full_vectors: tuple[Path, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CueEvidence:
    cue_id: str
    support: float
    diagnosticity: float
    quality: float
    active: bool = True


@dataclass(frozen=True)
class ConfidenceDecision:
    raw_confidence: float
    decision_tier: str
    decomposition: dict[str, float | str | list[str]]


@dataclass(frozen=True)
class VisualProbeResult:
    query_label_visible_to_audit: str
    top_concept_uuid: str
    top_visible_label: str
    raw_confidence: float
    decision_tier: str
    nearest_negative_margin: float
    used_filename_label: bool


@dataclass(frozen=True)
class ChannelDiagnosticRow:
    channel: str
    similarity: float
    nearest_negative_similarity: float
    evidence: float
    contribution: float
    validity_ratio: float = 1.0
    enabled: bool = True


@dataclass(frozen=True)
class ConceptRecognitionScore:
    visible_teacher_label: str
    concept_uuid: str
    raw_confidence: float
    diagnostic_score: float
    channel_rows: tuple[ChannelDiagnosticRow, ...]
    most_diagnostic_channels: tuple[str, ...]


@dataclass(frozen=True)
class RecognitionResult:
    query_path: str
    top_visible_label: str
    top_concept_uuid: str
    raw_confidence: float
    decision_tier: str
    nearest_negative_margin: float
    all_concept_scores: tuple[ConceptRecognitionScore, ...]
    stage_trace: tuple[str, ...]
    fixation_log: tuple[dict[str, float | int | str], ...]
    used_filename_label: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AudioAuditTrace:
    tick: int
    feature_vector: tuple[float, ...]
    channel_lengths: dict[str, int]
    input_trace_hash: str
    source_audio_hash: str
    receptor_version: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FeedbackAdjustment:
    target_source: str
    target_substrate: str
    before: float
    after: float
    untouched_sources: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceAwareWeights:
    weights: dict[tuple[str, str], float]

    def apply_feedback(
        self,
        *,
        contributions: dict[tuple[str, str], float],
        correction_strength: float,
    ) -> FeedbackAdjustment:
        """@op_count: O(source_paths)."""
        if not contributions:
            raise ValueError("source-aware feedback needs contribution evidence")
        target = max(contributions.items(), key=lambda item: float(item[1]))[0]
        before = float(self.weights.get(target, 0.0))
        rate = float(load_constant("phase19.feedback.source_feedback_rate"))
        after = max(0.0, before - float(correction_strength) * rate)
        self.weights[target] = after
        untouched = {
            f"{source}:{substrate}": value
            for (source, substrate), value in self.weights.items()
            if (source, substrate) != target
        }
        return FeedbackAdjustment(
            target_source=target[0],
            target_substrate=target[1],
            before=before,
            after=after,
            untouched_sources=untouched,
            metadata={"mode": "auto_contribution"},
        )


def populate_visual_vectors(
    examples: Sequence[VisualTeachingExample],
    *,
    root: Path | str,
) -> VectorPopulationResult:
    """@op_count: O(examples * feature_dim)."""
    root = Path(root)
    layer1 = Layer1PerceptVectorStore(root / "layer1")
    layer2 = Layer2PartPrototypeStore(root / "layer2")
    layer3 = Layer3ConceptPrototypeStore(root / "layer3")
    full_root = root / "full_vectors"
    full_root.mkdir(parents=True, exist_ok=True)

    percepts: list[PerceptVector] = []
    full_paths: list[Path] = []
    grouped_parts: dict[str, list[PartAssociation]] = {}
    label_to_source: dict[str, str] = {}

    for index, example in enumerate(examples):
        trace = extract_visual_audit_path_v2(example.path, tick=example.tick)
        feature = np.asarray(trace.feature_vector, dtype=np.float32)
        signature = vector_signature(feature)
        vector_uuid = _opaque_id("pv", trace.input_trace_hash, str(index))
        full_path = full_root / f"{vector_uuid}.npy"
        np.save(full_path, feature)
        percept = PerceptVector(
            vector_uuid=vector_uuid,
            signature=signature,
            full_vec_path=str(full_path.as_posix()),
            epistemic_source=PERCEIVED,
            substrate=example.substrate,
            receptor_version=str(trace.metadata["receptor_version"]),
            tick_acquired=example.tick,
            importance=float(trace.segmentation_confidence),
            metadata={
                "split": example.split,
                "teacher_label_source": "visible_curriculum_signal",
                "visible_teacher_label": example.visible_teacher_label,
                "source_image_hash": trace.source_image_hash,
                "used_filename_label": False,
            },
        )
        layer1.put(percept)
        percepts.append(percept)
        full_paths.append(full_path)

        for channel in tuple(str(item) for item in load_constant("phase19.vector.layer2_part_channels")):
            start, end = trace.channel_slices[channel]
            part_signature = vector_signature(feature[start:end], width=int(load_constant("phase19.vector.part_signature_dim")))
            part_uuid = _opaque_id("part", channel, percept.vector_uuid)
            part = PartPrototype(
                part_uuid=part_uuid,
                channel=channel,
                patch_signature=part_signature,
                exemplar_id=percept.vector_uuid,
                activation_count=int(load_constant("phase19.vector.initial_observation_count")),
                metadata={"medoid_policy": "first_true_exemplar", "source_channel": channel},
            )
            layer2.put(part)
            grouped_parts.setdefault(example.visible_teacher_label, []).append(PartAssociation(part_uuid, 1.0))
        label_to_source[example.visible_teacher_label] = PERCEIVED

    concepts: list[ConceptPrototype] = []
    for label, parts in grouped_parts.items():
        concept = ConceptPrototype(
            concept_uuid=_opaque_id("c", label, "visible_teacher_signal"),
            lifecycle_status="promoted",
            part_weights=tuple(parts),
            vocab_associations=(
                f"teacher_visible::{_hash_text(label)[: int(load_constant('phase19.vector.visible_vocab_hash_chars'))]}",
            ),
            epistemic_source=label_to_source[label],
            lifetime_observations=sum(1 for item in examples if item.visible_teacher_label == label),
            metadata={
                "teacher_label_source": "visible_curriculum_signal",
                "visible_teacher_label": label,
                "used_filename_label": False,
            },
        )
        layer3.put_concept(concept)
        concepts.append(concept)

    return VectorPopulationResult(
        percept_vectors=tuple(percepts),
        part_prototypes=tuple(layer2.get(part_id) for part_id in layer2.list_ids() if layer2.get(part_id) is not None),
        concepts=tuple(concepts),
        stored_full_vectors=tuple(full_paths),
        metadata={
            "layer1_count": len(percepts),
            "layer2_count": len(layer2.list_ids()),
            "layer3_count": len(concepts),
            "receptor_version": RECEPTOR_VERSION_VISUAL,
            "boundary": "Phase 19.0b1 writes real vectors but does not prove final recognition quality.",
        },
    )


def vector_signature(feature: Iterable[float], *, width: int | None = None) -> tuple[int, ...]:
    """@op_count: O(feature_dim + signature_dim)."""
    values = np.asarray(tuple(feature), dtype=np.float32).reshape(-1)
    if values.size == 0:
        values = np.zeros(1, dtype=np.float32)
    target = int(width or load_constant("phase19.vector.layer1_signature_dim"))
    positions = np.linspace(0, values.size - 1, target)
    sampled = np.interp(positions, np.arange(values.size), np.nan_to_num(values))
    low = float(sampled.min())
    high = float(sampled.max())
    if abs(high - low) < float(load_constant("phase19.vector.signature_epsilon")):
        normalized = np.zeros_like(sampled)
    else:
        normalized = (sampled - low) / (high - low)
    max_value = int(load_constant("phase19.vector.signature_max_value"))
    return tuple(int(round(float(item) * max_value)) for item in np.clip(normalized, 0.0, 1.0))


def decide_humanlike_confidence(
    cues: Sequence[CueEvidence],
    *,
    top_score: float,
    nearest_negative_score: float,
    source_reliability: float,
    object_novelty: float,
    context_novelty: float,
) -> ConfidenceDecision:
    """@op_count: O(cues log cues)."""
    active = [cue for cue in cues if cue.active and cue.support >= float(load_constant("phase19.confidence.cue_support_floor"))]
    selected = sorted(active, key=lambda cue: cue.support * cue.diagnosticity, reverse=True)[
        : int(load_constant("phase19.confidence.top_m_cues"))
    ]
    pi = thresholded_noisy_or(selected)
    gamma = active_cue_diagnosticity(selected)
    q = float(np.clip(source_reliability, 0.0, 1.0))
    mu = shifted_margin(top_score, nearest_negative_score)
    raw = float(np.clip(pi * gamma * q * mu, 0.0, 1.0))
    tier = tier_map(raw, object_novelty=object_novelty)
    if context_novelty >= float(load_constant("phase19.confidence.context_novelty_reinspect_floor")) and tier == "firm":
        tier = "soft"
    return ConfidenceDecision(
        raw_confidence=raw,
        decision_tier=tier,
        decomposition={
            "Pi": pi,
            "Gamma": gamma,
            "Q": q,
            "mu": mu,
            "nu_object": float(object_novelty),
            "nu_context": float(context_novelty),
            "active_cues": [cue.cue_id for cue in selected],
        },
    )


def thresholded_noisy_or(cues: Sequence[CueEvidence]) -> float:
    """@op_count: O(cues)."""
    if not cues:
        return 0.0
    support_floor = float(load_constant("phase19.confidence.cue_support_floor"))
    product = 1.0
    for cue in cues:
        effective = max(0.0, float(cue.support) - support_floor) / max(
            1.0 - support_floor,
            float(load_constant("phase19.confidence.denominator_epsilon")),
        )
        product *= 1.0 - np.clip(effective * float(cue.quality), 0.0, 1.0)
    return float(1.0 - product)


def active_cue_diagnosticity(cues: Sequence[CueEvidence]) -> float:
    """@op_count: O(cues)."""
    if not cues:
        return 0.0
    values = [float(cue.diagnosticity) for cue in cues]
    return float(np.clip(sum(values) / len(values), 0.0, 1.0))


def shifted_margin(top_score: float, nearest_negative_score: float) -> float:
    """@op_count: O(1)."""
    margin = float(top_score) - float(nearest_negative_score)
    midpoint = float(load_constant("phase19.confidence.margin_midpoint"))
    slope = float(load_constant("phase19.confidence.margin_slope"))
    return float(1.0 / (1.0 + math.exp(-slope * (margin - midpoint))))


def tier_map(raw_confidence: float, *, object_novelty: float) -> str:
    """@op_count: O(1)."""
    raw = float(raw_confidence)
    novelty_penalty = max(0.0, float(object_novelty) - float(load_constant("phase19.confidence.object_novelty_free_margin")))
    raw = max(0.0, raw - novelty_penalty * float(load_constant("phase19.confidence.object_novelty_penalty")))
    if raw >= float(load_constant("phase19.confidence.firm_threshold")):
        return "firm"
    if raw >= float(load_constant("phase19.confidence.soft_threshold")):
        return "soft"
    if raw >= float(load_constant("phase19.confidence.ambig_threshold")):
        return "ambig"
    return "no_call"


def visual_loo_probe(examples: Sequence[VisualTeachingExample]) -> tuple[VisualProbeResult, ...]:
    """@op_count: O(examples^2 * feature_dim)."""
    traces = [(example, extract_visual_audit_path_v2(example.path, tick=example.tick)) for example in examples]
    results: list[VisualProbeResult] = []
    for held_example, held_trace in traces:
        held_feature = np.asarray(held_trace.feature_vector, dtype=np.float32)
        scores: list[tuple[str, float]] = []
        for train_example, train_trace in traces:
            if train_example.path == held_example.path:
                continue
            train_feature = np.asarray(train_trace.feature_vector, dtype=np.float32)
            score = cosine_similarity(held_feature, train_feature)
            scores.append((train_example.visible_teacher_label, score))
        best_by_label: dict[str, float] = {}
        for label, score in scores:
            best_by_label[label] = max(best_by_label.get(label, -1.0), score)
        ranked = sorted(best_by_label.items(), key=lambda item: item[1], reverse=True)
        top_label, top_score = ranked[0]
        nearest_negative = next((score for label, score in ranked if label != top_label), 0.0)
        cues = [
            CueEvidence(
                "nearest_positive",
                max(top_score, 0.0),
                float(load_constant("phase19.confidence.probe_positive_diagnosticity")),
                1.0,
            ),
            CueEvidence(
                "nearest_negative_gap",
                max(top_score - nearest_negative, 0.0),
                float(load_constant("phase19.confidence.probe_gap_diagnosticity")),
                float(load_constant("phase19.confidence.probe_gap_quality")),
            ),
        ]
        decision = decide_humanlike_confidence(
            cues,
            top_score=top_score,
            nearest_negative_score=nearest_negative,
            source_reliability=float(load_constant("phase19.confidence.probe_source_reliability")),
            object_novelty=max(0.0, 1.0 - max(top_score, 0.0)),
            context_novelty=float(load_constant("phase19.confidence.probe_context_novelty")),
        )
        results.append(
            VisualProbeResult(
                query_label_visible_to_audit=held_example.visible_teacher_label,
                top_concept_uuid=_opaque_id("c", top_label, "probe"),
                top_visible_label=top_label,
                raw_confidence=decision.raw_confidence,
                decision_tier=decision.decision_tier,
                nearest_negative_margin=top_score - nearest_negative,
                used_filename_label=False,
            )
        )
    return tuple(results)


def visual_recognize_v1_7(
    query_image_path: Path | str,
    *,
    teaching_examples: Sequence[VisualTeachingExample],
    tick: int = 0,
) -> RecognitionResult:
    """@op_count: O(examples * channels * feature_dim_per_channel)."""
    query_trace = extract_visual_audit_path_v2(Path(query_image_path), tick=tick)
    concept_traces = _concept_training_traces(teaching_examples)
    fixation_log = _diagnostic_fixation_log(query_trace)
    if not concept_traces:
        tentative = _opaque_id("c", query_trace.input_trace_hash, "tentative")
        return RecognitionResult(
            query_path=str(Path(query_image_path).as_posix()),
            top_visible_label="tentative_concept",
            top_concept_uuid=tentative,
            raw_confidence=0.0,
            decision_tier="ambig",
            nearest_negative_margin=0.0,
            all_concept_scores=(),
            stage_trace=("C_RECALL_PARTS", "SPAWN_TENTATIVE", "CONF_DECISION"),
            fixation_log=fixation_log,
            used_filename_label=False,
            metadata={"candidate_source": "empty_recall"},
        )

    channel_validity = _channel_validity_map(concept_traces)
    concept_scores = tuple(
        _score_concept_channelwise(query_trace, label, traces, concept_traces, channel_validity)
        for label, traces in sorted(concept_traces.items())
    )
    ranked = tuple(sorted(concept_scores, key=lambda item: item.raw_confidence, reverse=True))
    top = ranked[0]
    second_score = ranked[1].raw_confidence if len(ranked) > int(load_constant("phase19.vector.initial_observation_count")) else 0.0
    margin = top.raw_confidence - second_score
    tier = _diagnostic_tier(top.raw_confidence, margin)
    return RecognitionResult(
        query_path=str(Path(query_image_path).as_posix()),
        top_visible_label=top.visible_teacher_label,
        top_concept_uuid=top.concept_uuid,
        raw_confidence=top.raw_confidence,
        decision_tier=tier,
        nearest_negative_margin=margin,
        all_concept_scores=ranked,
        stage_trace=("C_RECALL_PARTS", "B_RECALL_EPISODICS", "CHANNEL_NOISY_OR", "CONF_DECISION"),
        fixation_log=fixation_log,
        used_filename_label=False,
        metadata={
            "recognizer_version": "phase19_7_diagnostic_first",
            "receptor_version": str(query_trace.metadata["receptor_version"]),
            "segmentation_confidence": float(query_trace.segmentation_confidence),
            "subject_weight": _subject_weight(query_trace.segmentation_confidence),
            "channel_validity": channel_validity,
        },
    )


def _concept_training_traces(
    examples: Sequence[VisualTeachingExample],
) -> dict[str, tuple[Any, ...]]:
    """@op_count: O(examples * feature_dim)."""
    grouped: dict[str, list[Any]] = {}
    for index, example in enumerate(examples, start=int(load_constant("phase19.vector.initial_observation_count"))):
        trace = extract_visual_audit_path_v2(example.path, tick=example.tick + index)
        grouped.setdefault(example.visible_teacher_label, []).append(trace)
    return {label: tuple(traces) for label, traces in grouped.items()}


def _score_concept_channelwise(
    query_trace: Any,
    label: str,
    traces: Sequence[Any],
    all_concept_traces: dict[str, tuple[Any, ...]],
    channel_validity: dict[str, float] | None = None,
) -> ConceptRecognitionScore:
    """@op_count: O(channels * feature_dim_per_channel)."""
    channel_weights = dict(load_constant("phase19.recognition.channel_weights"))
    rows: list[ChannelDiagnosticRow] = []
    for channel, weight in channel_weights.items():
        validity = float((channel_validity or {}).get(channel, 1.0))
        enabled = validity >= float(load_constant("phase19_7.channel_validity_min_ratio"))
        query_channel = _channel_array(query_trace, channel)
        similarities = [_channel_similarity(channel, query_channel, _channel_array(trace, channel)) for trace in traces]
        similarity = max(similarities) if similarities else 0.0
        nearest_negative = _nearest_negative_channel_similarity(query_trace, label, channel, all_concept_traces)
        evidence = _channel_evidence(similarity, nearest_negative)
        weighted = (
            evidence
            * float(weight)
            * _subject_weight(query_trace.segmentation_confidence)
            if enabled
            else 0.0
        )
        rows.append(
            ChannelDiagnosticRow(
                channel=channel,
                similarity=similarity,
                nearest_negative_similarity=nearest_negative,
                evidence=evidence,
                contribution=weighted,
                validity_ratio=validity,
                enabled=enabled,
            )
        )
    selected = sorted(rows, key=lambda row: row.contribution, reverse=True)[
        : int(load_constant("phase19.recognition.diagnostic_top_m"))
    ]
    product = 1.0
    for row in selected:
        product *= 1.0 - float(np.clip(
            row.contribution,
            0.0,
            float(load_constant("phase19_7.max_channel_contribution")),
        ))
    diagnostic_score = float(1.0 - product)
    quality = float(load_constant("phase19.recognition.default_source_quality"))
    raw = float(np.clip(diagnostic_score * quality, 0.0, 1.0))
    return ConceptRecognitionScore(
        visible_teacher_label=label,
        concept_uuid=_opaque_id("c", label, "phase19_7"),
        raw_confidence=raw,
        diagnostic_score=diagnostic_score,
        channel_rows=tuple(rows),
        most_diagnostic_channels=tuple(row.channel for row in selected[: int(load_constant("phase19.confidence.top_m_cues"))]),
    )


def _channel_validity_map(concept_traces: dict[str, tuple[Any, ...]]) -> dict[str, float]:
    """@op_count: O(channels * examples^2)."""
    channel_weights = dict(load_constant("phase19.recognition.channel_weights"))
    labels = sorted(concept_traces)
    ratios: dict[str, float] = {}
    for channel in channel_weights:
        within_distances: list[float] = []
        between_distances: list[float] = []
        for label in labels:
            traces = concept_traces[label]
            for left_index in range(len(traces)):
                for right_index in range(left_index + 1, len(traces)):
                    within_distances.append(
                        1.0 - _channel_similarity(
                            channel,
                            _channel_array(traces[left_index], channel),
                            _channel_array(traces[right_index], channel),
                        )
                    )
        for left_label_index, left_label in enumerate(labels):
            for right_label in labels[left_label_index + 1:]:
                for left_trace in concept_traces[left_label]:
                    for right_trace in concept_traces[right_label]:
                        between_distances.append(
                            1.0 - _channel_similarity(
                                channel,
                                _channel_array(left_trace, channel),
                                _channel_array(right_trace, channel),
                            )
                        )
        if len(within_distances) < int(load_constant("phase19_7.channel_validity_min_pairs")):
            ratios[channel] = 1.0
            continue
        within = float(np.mean(within_distances))
        between = float(np.mean(between_distances)) if between_distances else 0.0
        ratios[channel] = float(
            between
            / max(
                within,
                float(load_constant("phase19.confidence.denominator_epsilon")),
            )
        )
    return ratios


def _nearest_negative_channel_similarity(
    query_trace: Any,
    label: str,
    channel: str,
    all_concept_traces: dict[str, tuple[Any, ...]],
) -> float:
    """@op_count: O(other_concepts * examples * feature_dim_per_channel)."""
    negative_traces = [
        trace
        for other_label, traces in all_concept_traces.items()
        if other_label != label
        for trace in traces
    ]
    if not negative_traces:
        return 0.0
    values = [
        _channel_similarity(channel, _channel_array(query_trace, channel), _channel_array(trace, channel))
        for trace in negative_traces
    ]
    return max(values) if values else 0.0


def _channel_evidence(similarity: float, nearest_negative: float) -> float:
    """@op_count: O(1)."""
    floor = float(load_constant("phase19.recognition.channel_similarity_floor"))
    span = float(load_constant("phase19.recognition.channel_similarity_span"))
    gain = float(load_constant("phase19.recognition.channel_margin_gain"))
    base = max(0.0, (float(similarity) - floor) / max(span, float(load_constant("phase19.confidence.denominator_epsilon"))))
    margin = max(0.0, float(similarity) - float(nearest_negative))
    margin_gate = float(np.clip(gain * margin, 0.0, 1.0))
    return float(np.clip(base * margin_gate, 0.0, 1.0))


def _diagnostic_tier(raw: float, margin: float) -> str:
    """@op_count: O(1)."""
    tier = tier_map(raw, object_novelty=0.0)
    if tier == "firm" and margin < float(load_constant("phase19.recognition.diagnostic_margin_firm_floor")):
        return "soft"
    if tier == "soft" and margin < float(load_constant("phase19.recognition.diagnostic_margin_soft_floor")):
        return "ambig"
    return tier


def _channel_array(trace: Any, channel: str) -> np.ndarray:
    """@op_count: O(channel_dim)."""
    start, end = trace.channel_slices[channel]
    return np.asarray(trace.feature_vector[start:end], dtype=np.float32)


def _channel_similarity(channel: str, left: np.ndarray, right: np.ndarray) -> float:
    """@op_count: O(channel_dim)."""
    length = min(int(left.size), int(right.size))
    if length <= 0:
        return 0.0
    a = np.nan_to_num(left[:length])
    b = np.nan_to_num(right[:length])
    if channel == "V7":
        denominator = a + b + float(load_constant("phase19.confidence.denominator_epsilon"))
        distance = float(load_constant("phase19.recognition.chi_square_half_factor")) * float(np.sum(((a - b) * (a - b)) / denominator))
        return float(np.clip(1.0 - distance, 0.0, 1.0))
    if channel == "V10":
        return _active_row_similarity(
            a,
            b,
            row_width=int(load_constant("vision_sensor.part_profile_features")),
            coverage_index=int(load_constant("vision_sensor.part_profile_features")) - 1,
        )
    if channel == "V11":
        return _active_row_similarity(
            a,
            b,
            row_width=int(load_constant("vision_sensor.part_relation_features")),
            coverage_index=int(load_constant("phase19.vector.initial_observation_count")),
        )
    if channel == "V12":
        return _active_row_similarity(
            a,
            b,
            row_width=int(load_constant("vision_sensor.color_cluster_features")),
            coverage_index=0,
        )
    if channel in {"V1", "V2", "V3", "V7", "V12"}:
        denominator = a + b + float(load_constant("phase19.confidence.denominator_epsilon"))
        distance = (
            float(load_constant("phase19.recognition.chi_square_half_factor"))
            * float(np.sum(((a - b) * (a - b)) / denominator))
            / max(float(length), 1.0)
        )
        return float(np.clip(1.0 - distance, 0.0, 1.0))
    distance = float(np.mean(np.abs(a - b)))
    return float(np.clip(1.0 - distance, 0.0, 1.0))


def _active_row_similarity(left: np.ndarray, right: np.ndarray, *, row_width: int, coverage_index: int) -> float:
    """@op_count: O(rows * row_width)."""
    usable = min(left.size, right.size)
    usable -= usable % max(row_width, 1)
    if usable <= 0:
        return 0.0
    a = left[:usable].reshape(-1, row_width)
    b = right[:usable].reshape(-1, row_width)
    active = (a[:, coverage_index] > 0.0) | (b[:, coverage_index] > 0.0)
    if not active.any():
        return 0.0
    distance = float(np.mean(np.abs(a[active] - b[active])))
    return float(np.clip(1.0 - distance, 0.0, 1.0))


def _subject_weight(segmentation_confidence: float) -> float:
    """@op_count: O(1)."""
    if segmentation_confidence >= float(load_constant("phase19.recognition.segmentation_confidence_floor")):
        return float(load_constant("phase19.recognition.subject_weight_high_conf"))
    return float(load_constant("phase19.recognition.subject_weight_low_conf"))


def _diagnostic_fixation_log(trace: Any) -> tuple[dict[str, float | int | str], ...]:
    """@op_count: O(fixations)."""
    count_subject = int(load_constant("phase19_7.fixations_in_subject"))
    count_background = int(load_constant("phase19_7.fixations_in_background"))
    width = max(int(trace.width), 1)
    height = max(int(trace.height), 1)
    points: list[dict[str, float | int | str]] = []
    for index in range(count_subject):
        phase = (index + 1) / max(count_subject + 1, 1)
        points.append(
            {
                "fixation_index": index,
                "region": "subject",
                "chosen_x": int(width * phase),
                "chosen_y": int(height * (1.0 - phase if index % 2 else phase)),
                "saliency": 1.0 - phase * float(load_constant("phase19_7.fixation_saliency_decay")),
                "uncertainty": phase,
            }
        )
    for index in range(count_background):
        points.append(
            {
                "fixation_index": count_subject + index,
                "region": "background",
                "chosen_x": int(width * float(load_constant("phase19_7.background_fixation_ratio"))),
                "chosen_y": int(height * float(load_constant("phase19_7.background_fixation_ratio"))),
                "saliency": float(load_constant("phase19_7.background_saliency")),
                "uncertainty": float(load_constant("phase19_7.background_uncertainty")),
            }
        )
    return tuple(points)


def extract_audio_audit_path(
    audio_path: Path | str,
    *,
    tick: int = 0,
) -> AudioAuditTrace:
    """@op_count: O(samples + feature_dim)."""
    samples, rate = _read_wav_mono(Path(audio_path))
    if samples.size == 0:
        samples = np.zeros(int(load_constant("phase19.audio.min_samples")), dtype=np.float32)
    mag = np.abs(np.fft.rfft(samples, n=int(load_constant("phase19.audio.fft_size"))))
    mag = mag / max(float(mag.max()), float(load_constant("phase19.confidence.denominator_epsilon")))
    envelope = np.abs(samples)
    onset = np.abs(np.diff(envelope, prepend=envelope[:1]))
    pitch_like = _autocorr_profile(samples)

    a0 = _resample_vector(np.concatenate([samples, mag, envelope, onset]), int(load_constant("phase19.audio.a0_dim")))
    channels = {
        "A0": a0,
        "A1": _resample_vector(mag, int(load_constant("phase19.audio.a1_dim"))),
        "A2": _resample_vector(
            np.cumsum(mag) / max(float(mag.sum()), float(load_constant("phase19.confidence.denominator_epsilon"))),
            int(load_constant("phase19.audio.a2_dim")),
        ),
        "A3": _resample_vector(envelope, int(load_constant("phase19.audio.a3_dim"))),
        "A4": _resample_vector(onset, int(load_constant("phase19.audio.a4_dim"))),
        "A5": _resample_vector(np.gradient(envelope), int(load_constant("phase19.audio.a5_dim"))),
        "A6": _resample_vector(pitch_like, int(load_constant("phase19.audio.a6_dim"))),
        "A7": _resample_vector(np.sort(mag), int(load_constant("phase19.audio.a7_dim"))),
        "A8": _resample_vector(np.diff(mag, prepend=mag[:1]), int(load_constant("phase19.audio.a8_dim"))),
    }
    feature = np.concatenate([
        channels[f"A{index}"] for index in range(int(load_constant("phase19.audio.channel_count")))
    ]).astype(np.float32, copy=False)
    expected = int(load_constant("phase19.vector.audio_receptor_feature_dim"))
    if feature.size != expected:
        raise ValueError(f"audio feature dimension mismatch: {feature.size} != {expected}")
    return AudioAuditTrace(
        tick=int(tick),
        feature_vector=tuple(float(item) for item in feature),
        channel_lengths={key: int(value.size) for key, value in channels.items()},
        input_trace_hash=_hash_array(feature),
        source_audio_hash=_hash_array(samples),
        receptor_version=RECEPTOR_VERSION_AUDIO,
        metadata={
            "pathway": "auditory_reconstruction_audit_path",
            "sample_rate": int(rate),
            "evaluator_label_accessed": False,
            "inner_voice_sketch_only": True,
        },
    )


def audio_loo_probe(audio_paths: Sequence[Path]) -> tuple[float, ...]:
    """@op_count: O(items^2 * feature_dim)."""
    traces = [extract_audio_audit_path(path, tick=index) for index, path in enumerate(audio_paths)]
    similarities: list[float] = []
    for index, trace in enumerate(traces):
        other_scores = [
            cosine_similarity(trace.feature_vector, other.feature_vector)
            for other_index, other in enumerate(traces)
            if other_index != index
        ]
        similarities.append(max(other_scores) if other_scores else 0.0)
    return tuple(similarities)


def temporal_event_bind(
    percept_uuids: Sequence[str],
    *,
    tick_start: int,
    tick_end: int,
    source_markers: Sequence[str],
) -> TemporalEventBinding:
    """@op_count: O(percepts + markers)."""
    event = TemporalEventBinding(
        event_uuid=new_opaque_uuid("event"),
        percept_uuids=tuple(percept_uuids),
        tick_window=(int(tick_start), int(tick_end)),
        source_markers=tuple(source_markers),
        lifetime_cooccurrence_count=int(load_constant("phase19.binding.initial_event_count")),
        metadata={"promotion_threshold": int(load_constant("phase19.binding.promote_cooccurrence_threshold"))},
    )
    return event


def promote_event_to_concept_if_ready(
    event: TemporalEventBinding,
    parts: Sequence[PartAssociation],
) -> ConceptPrototype | None:
    """@op_count: O(parts)."""
    if event.lifetime_cooccurrence_count < int(load_constant("phase19.binding.promote_cooccurrence_threshold")):
        return None
    return ConceptPrototype(
        concept_uuid=new_opaque_uuid("c"),
        lifecycle_status="promoted",
        part_weights=tuple(parts),
        vocab_associations=(),
        epistemic_source="+".join(event.source_markers),
        lifetime_observations=event.lifetime_cooccurrence_count,
        metadata={"promoted_from_event_uuid": event.event_uuid},
    )


def choose_next_fixation(
    canvas: SensoryCanvas,
    *,
    motion_map: np.ndarray | None = None,
) -> tuple[int, int]:
    """@op_count: O(width * height)."""
    clarity_need = 1.0 - canvas.canvas_clarity
    confidence_need = 1.0 - canvas.canvas_confidence
    score = clarity_need * float(load_constant("phase19.active_perception.clarity_weight"))
    score += confidence_need * float(load_constant("phase19.active_perception.uncertainty_weight"))
    if motion_map is not None:
        score += np.asarray(motion_map, dtype=np.float32) * float(load_constant("phase19.active_perception.motion_weight"))
    y, x = np.unravel_index(int(np.argmax(score)), score.shape)
    return (int(x), int(y))


def active_visual_scan(image_like: Path | str | np.ndarray, *, ticks: int) -> tuple[SensoryCanvas, tuple[tuple[int, int], ...]]:
    """@op_count: O(ticks * width * height)."""
    canvas = SensoryCanvas.from_native_image(image_like, tick=0)
    fixations: list[tuple[int, int]] = []
    for tick in range(1, int(ticks) + 1):
        focus = choose_next_fixation(canvas)
        canvas.update_from_native_image(image_like, focus_xy=focus, tick=tick)
        fixations.append(focus)
    return canvas, tuple(fixations)


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    """@op_count: O(dim)."""
    a = np.asarray(tuple(left), dtype=np.float32).reshape(-1)
    b = np.asarray(tuple(right), dtype=np.float32).reshape(-1)
    length = min(a.size, b.size)
    if length == 0:
        return 0.0
    a = a[:length]
    b = b[:length]
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= float(load_constant("phase19.confidence.denominator_epsilon")):
        return 0.0
    return float(np.dot(a, b) / denom)


def _read_wav_mono(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as handle:
        rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
        channels = handle.getnchannels()
        width = handle.getsampwidth()
    if width == 1:
        data = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
        data = (data - float(load_constant("phase19.audio.uint8_center"))) / float(load_constant("phase19.audio.uint8_scale"))
    else:
        data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / float(load_constant("phase19.audio.int16_scale"))
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return data.astype(np.float32, copy=False), int(rate)


def _autocorr_profile(samples: np.ndarray) -> np.ndarray:
    if samples.size == 0:
        return np.zeros(1, dtype=np.float32)
    bounded = samples[: int(load_constant("phase19.audio.autocorr_sample_cap"))]
    corr = np.correlate(bounded, bounded, mode="full")[bounded.size - 1 :]
    return corr / max(float(np.max(np.abs(corr))), float(load_constant("phase19.confidence.denominator_epsilon")))


def _resample_vector(values: Iterable[float], width: int) -> np.ndarray:
    arr = np.asarray(tuple(values), dtype=np.float32).reshape(-1)
    if arr.size == 0:
        arr = np.zeros(1, dtype=np.float32)
    positions = np.linspace(0, arr.size - 1, int(width))
    sampled = np.interp(positions, np.arange(arr.size), np.nan_to_num(arr))
    return sampled.astype(np.float32, copy=False)


def _opaque_id(prefix: str, *parts: str) -> str:
    value = f"{prefix}_{_hash_text('|'.join(str(part) for part in parts))[: int(load_constant('phase19.vector.opaque_id_hash_chars'))]}"
    assert_opaque_identifier(value)
    return value


def _hash_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def _hash_array(values: Iterable[float]) -> str:
    arr = np.asarray(tuple(values), dtype=np.float32)
    return hashlib.sha256(arr.tobytes()).hexdigest()
