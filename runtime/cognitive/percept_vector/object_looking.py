from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image

from apv3test.runtime.visual_receptor import (
    extract_visual_audit_path_v2,
    extract_visual_audit_path_v2_object_centric,
)
from runtime.cognitive.attention.visual_focus import (
    apply_visual_focus_action,
    propose_visual_focus_actions,
)
from runtime.cognitive.percept_vector.phase19_runtime import (
    RecognitionResult,
    VisualTeachingExample,
    _diagnostic_tier,
    _opaque_id,
    _score_concept_channelwise,
)
from runtime.cognitive.state_pool.state_pool import StateItem, StatePool, load_constant


@dataclass(frozen=True)
class VisualObjectCandidate:
    candidate_id: str
    bbox: tuple[int, int, int, int]
    focus_xy: tuple[int, int]
    saliency: float
    area_ratio: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObjectFile:
    candidate: VisualObjectCandidate
    recognition: RecognitionResult
    tick_seen: int
    merged_count: int = 1


@dataclass(frozen=True)
class ObjectLookingResult:
    image_path: str
    objects: tuple[ObjectFile, ...]
    candidate_count: int
    scan_trace: tuple[dict[str, Any], ...]
    metadata: dict[str, Any] = field(default_factory=dict)


def extract_candidate_targets(image_path: Path | str, *, max_targets: int | None = None) -> tuple[VisualObjectCandidate, ...]:
    """@op_count: O(width * height + components log components)."""
    rgb = _load_rgb(image_path)
    height, width = rgb.shape[:2]
    max_targets = int(max_targets or load_constant("phase21.object_looking.max_candidates_per_image"))
    mask, saliency = _candidate_saliency_mask(rgb)
    components = _connected_components(mask)
    candidates: list[VisualObjectCandidate] = []
    for component_index, points in enumerate(components):
        ys = points[:, 0]
        xs = points[:, 1]
        area = int(points.shape[0])
        area_ratio = area / max(float(width * height), 1.0)
        if area_ratio < float(load_constant("phase21.object_looking.min_area_ratio")):
            continue
        x1, x2 = int(xs.min()), int(xs.max()) + 1
        y1, y2 = int(ys.min()), int(ys.max()) + 1
        bbox = _pad_bbox(
            (x1, y1, x2, y2),
            width=width,
            height=height,
            pad_ratio=float(load_constant("phase21.object_looking.candidate_padding_ratio")),
        )
        focus_xy = (int(round(float(xs.mean()))), int(round(float(ys.mean()))))
        candidate_id = _candidate_id(image_path, bbox, component_index)
        candidates.append(
            VisualObjectCandidate(
                candidate_id=candidate_id,
                bbox=bbox,
                focus_xy=focus_xy,
                saliency=float(np.mean(saliency[ys, xs])),
                area_ratio=float(area_ratio),
                metadata={
                    "family": "visual_candidate",
                    "channel_signature": ("vision", "candidate", "class_agnostic"),
                    "bbox": bbox,
                    "focus_xy": focus_xy,
                    "area_ratio": float(area_ratio),
                    "label_accessed": False,
                    "filename_accessed": False,
                },
            )
        )
    ordered = sorted(candidates, key=lambda item: (item.saliency, item.area_ratio, item.candidate_id), reverse=True)
    return tuple(_nms(ordered, max_targets=max_targets))


def enumerate_objects_in_image(
    image_path: Path | str,
    *,
    teaching_examples: Sequence[VisualTeachingExample],
    concept_traces: dict[str, tuple[Any, ...]] | None = None,
    tick_budget: int | None = None,
) -> ObjectLookingResult:
    """@op_count: O(candidates * examples * channels * feature_dim_per_channel)."""
    path = Path(image_path)
    candidates = extract_candidate_targets(path)
    pool = StatePool()
    inject_candidates_to_state_pool(pool, candidates, tick=0)
    concept_traces = concept_traces or build_object_centric_training_traces(teaching_examples)
    tick_budget = int(tick_budget or load_constant("phase21.object_looking.tick_budget"))
    objects: list[ObjectFile] = []
    scan_trace: list[dict[str, Any]] = []
    visited: list[VisualObjectCandidate] = []
    current_focus_id: str | None = None
    for tick in range(tick_budget):
        proposals = propose_visual_focus_actions(pool.items.values(), current_focus_id=current_focus_id)
        saccade = next((proposal for proposal in proposals if proposal.action_kind == "saccade_to_visual"), None)
        if saccade is None:
            break
        item = pool.get(saccade.target_sa_id)
        if item is None:
            break
        candidate = _candidate_from_state_item(item, candidates)
        if candidate is None:
            break
        apply_visual_focus_action(item, saccade, tick=tick)
        if any(_bbox_iou(candidate.bbox, prior.bbox) >= float(load_constant("phase21.object_looking.ior_iou_threshold")) for prior in visited):
            item.fatigue = item.fatigue + float(load_constant("phase21.object_looking.visited_fatigue_gain"))
            scan_trace.append({"tick": tick, "action": "skip_ior", "candidate_id": candidate.candidate_id})
            continue
        recognition = recognize_at_focus(path, candidate=candidate, concept_traces=concept_traces, tick=tick)
        objects.append(ObjectFile(candidate=candidate, recognition=recognition, tick_seen=tick))
        visited.append(candidate)
        item.fatigue = item.fatigue + float(load_constant("phase21.object_looking.visited_fatigue_gain"))
        current_focus_id = item.sa_id
        scan_trace.append(
            {
                "tick": tick,
                "action": "saccade_to_visual",
                "candidate_id": candidate.candidate_id,
                "bbox": candidate.bbox,
                "focus_xy": candidate.focus_xy,
                "top_visible_label": recognition.top_visible_label,
                "decision_tier": recognition.decision_tier,
                "margin": recognition.nearest_negative_margin,
            }
        )
        if len(objects) >= int(load_constant("phase21.object_looking.max_objects_per_image")):
            break
    return ObjectLookingResult(
        image_path=str(path.as_posix()),
        objects=tuple(objects),
        candidate_count=len(candidates),
        scan_trace=tuple(scan_trace),
        metadata={
            "phase": "21.0",
            "object_centric": True,
            "candidate_source": "class_agnostic_saliency",
            "used_filename_label": False,
        },
    )


def inject_candidates_to_state_pool(pool: StatePool, candidates: Sequence[VisualObjectCandidate], *, tick: int) -> None:
    """@op_count: O(candidates)."""
    for candidate in candidates:
        item = StateItem(
            sa_id=f"visual_candidate::{candidate.candidate_id}",
            family="visual_candidate",
            label="visual_candidate",
            real_energy=candidate.saliency,
            attention_energy=candidate.saliency * float(load_constant("phase21.object_looking.saliency_attention_gain")),
            cognitive_pressure=1.0 - min(1.0, candidate.saliency),
            last_tick=int(tick),
            channel_signature=("vision", "candidate", "class_agnostic"),
            source="class_agnostic_candidate_detector",
            metadata=dict(candidate.metadata),
        )
        pool.items[item.sa_id] = item


def recognize_at_focus(
    image_path: Path | str,
    *,
    candidate: VisualObjectCandidate,
    concept_traces: dict[str, tuple[Any, ...]],
    tick: int = 0,
) -> RecognitionResult:
    """@op_count: O(concepts * examples * channels * feature_dim_per_channel)."""
    query_trace = extract_visual_audit_path_v2_object_centric(
        Path(image_path),
        candidate_bbox=candidate.bbox,
        focus_xy=candidate.focus_xy,
        tick=tick,
    )
    return _recognize_trace(
        Path(image_path),
        query_trace=query_trace,
        concept_traces=concept_traces,
        fixation_log=(
            {
                "fixation_index": 0,
                "region": "object_candidate",
                "chosen_x": int(candidate.focus_xy[0]),
                "chosen_y": int(candidate.focus_xy[1]),
                "saliency": float(candidate.saliency),
                "uncertainty": 1.0 - min(1.0, float(candidate.saliency)),
            },
        ),
        metadata={
            "recognizer_version": "phase21_object_centric",
            "candidate_id": candidate.candidate_id,
            "candidate_bbox": candidate.bbox,
            "object_centric": True,
        },
    )


def count_objects(result: ObjectLookingResult) -> int:
    """@op_count: O(1)."""
    return len(result.objects)


def _recognize_trace(
    query_path: Path,
    *,
    query_trace: Any,
    concept_traces: dict[str, tuple[Any, ...]],
    fixation_log: tuple[dict[str, float | int | str], ...],
    metadata: dict[str, Any],
) -> RecognitionResult:
    if not concept_traces:
        tentative = _opaque_id("c", query_trace.input_trace_hash, "tentative")
        return RecognitionResult(
            query_path=str(query_path.as_posix()),
            top_visible_label="tentative_concept",
            top_concept_uuid=tentative,
            raw_confidence=0.0,
            decision_tier="ambig",
            nearest_negative_margin=0.0,
            all_concept_scores=(),
            stage_trace=("C_RECALL_PARTS", "SPAWN_TENTATIVE", "CONF_DECISION"),
            fixation_log=fixation_log,
            used_filename_label=False,
            metadata={**metadata, "candidate_source": "empty_recall"},
        )
    channel_validity = _channel_validity_map_for_object_traces(concept_traces)
    concept_scores = tuple(
        _score_concept_channelwise(query_trace, label, traces, concept_traces, channel_validity)
        for label, traces in sorted(concept_traces.items())
    )
    ranked = tuple(sorted(concept_scores, key=lambda item: item.raw_confidence, reverse=True))
    top = ranked[0]
    second_score = ranked[1].raw_confidence if len(ranked) > 1 else 0.0
    margin = top.raw_confidence - second_score
    return RecognitionResult(
        query_path=str(query_path.as_posix()),
        top_visible_label=top.visible_teacher_label,
        top_concept_uuid=top.concept_uuid,
        raw_confidence=top.raw_confidence,
        decision_tier=_diagnostic_tier(top.raw_confidence, margin),
        nearest_negative_margin=margin,
        all_concept_scores=ranked,
        stage_trace=("VISUAL_CANDIDATE", "SACCADE_TO_VISUAL", "OBJECT_CENTRIC_CHANNELS", "CONF_DECISION"),
        fixation_log=fixation_log,
        used_filename_label=False,
        metadata={
            **metadata,
            "channel_validity": channel_validity,
            "receptor_version": str(query_trace.metadata["receptor_version"]),
            "segmentation_confidence": float(query_trace.segmentation_confidence),
        },
    )


def build_object_centric_training_traces(
    examples: Sequence[VisualTeachingExample],
) -> dict[str, tuple[Any, ...]]:
    """@op_count: O(examples * feature_dim)."""
    grouped: dict[str, list[Any]] = {}
    for index, example in enumerate(examples, start=1):
        candidates = extract_candidate_targets(example.path, max_targets=1)
        if candidates:
            candidate = candidates[0]
            trace = extract_visual_audit_path_v2_object_centric(
                example.path,
                candidate_bbox=candidate.bbox,
                focus_xy=candidate.focus_xy,
                tick=example.tick + index,
            )
        else:
            trace = extract_visual_audit_path_v2(example.path, tick=example.tick + index)
        grouped.setdefault(example.visible_teacher_label, []).append(trace)
    return {label: tuple(traces) for label, traces in grouped.items()}


def _channel_validity_map_for_object_traces(concept_traces: dict[str, tuple[Any, ...]]) -> dict[str, float]:
    from runtime.cognitive.percept_vector.phase19_runtime import _channel_validity_map

    return _channel_validity_map(concept_traces)


def _candidate_saliency_mask(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    border = np.concatenate([rgb[0, :, :], rgb[-1, :, :], rgb[:, 0, :], rgb[:, -1, :]], axis=0)
    border_mean = border.mean(axis=0)
    color_dist = np.linalg.norm(rgb - border_mean, axis=2)
    color_dist = color_dist / max(float(color_dist.max()), float(load_constant("phase19.confidence.denominator_epsilon")))
    luma = rgb.mean(axis=2)
    edge = _edge_magnitude(luma)
    saliency = (
        color_dist * float(load_constant("phase21.object_looking.color_saliency_weight"))
        + edge * float(load_constant("phase21.object_looking.edge_saliency_weight"))
    )
    saliency = saliency / max(float(saliency.max()), float(load_constant("phase19.confidence.denominator_epsilon")))
    threshold = max(
        float(np.percentile(saliency, int(load_constant("phase21.object_looking.saliency_percentile")))),
        float(load_constant("phase21.object_looking.saliency_floor")),
    )
    mask = saliency >= threshold
    return _clean_binary(mask), saliency


def _connected_components(mask: np.ndarray) -> list[np.ndarray]:
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    components: list[np.ndarray] = []
    for y in range(height):
        for x in range(width):
            if seen[y, x] or not mask[y, x]:
                continue
            stack = [(y, x)]
            seen[y, x] = True
            points: list[tuple[int, int]] = []
            while stack:
                cy, cx = stack.pop()
                points.append((cy, cx))
                for ny in range(max(0, cy - 1), min(height, cy + 2)):
                    for nx in range(max(0, cx - 1), min(width, cx + 2)):
                        if not seen[ny, nx] and mask[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
            components.append(np.asarray(points, dtype=np.int32))
    return components


def _nms(candidates: Sequence[VisualObjectCandidate], *, max_targets: int) -> list[VisualObjectCandidate]:
    kept: list[VisualObjectCandidate] = []
    for candidate in candidates:
        if any(_bbox_iou(candidate.bbox, prior.bbox) >= float(load_constant("phase21.object_looking.nms_iou_threshold")) for prior in kept):
            continue
        kept.append(candidate)
        if len(kept) >= max_targets:
            break
    return kept


def _candidate_from_state_item(item: StateItem, candidates: Sequence[VisualObjectCandidate]) -> VisualObjectCandidate | None:
    candidate_id = item.sa_id.removeprefix("visual_candidate::")
    return next((candidate for candidate in candidates if candidate.candidate_id == candidate_id), None)


def _bbox_iou(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> float:
    lx1, ly1, lx2, ly2 = left
    rx1, ry1, rx2, ry2 = right
    ix1, iy1 = max(lx1, rx1), max(ly1, ry1)
    ix2, iy2 = min(lx2, rx2), min(ly2, ry2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    left_area = max(0, lx2 - lx1) * max(0, ly2 - ly1)
    right_area = max(0, rx2 - rx1) * max(0, ry2 - ry1)
    return inter / max(float(left_area + right_area - inter), 1.0)


def _pad_bbox(
    bbox: tuple[int, int, int, int],
    *,
    width: int,
    height: int,
    pad_ratio: float,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    pad_x = int(round((x2 - x1) * pad_ratio))
    pad_y = int(round((y2 - y1) * pad_ratio))
    return (
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(width, x2 + pad_x),
        min(height, y2 + pad_y),
    )


def _clean_binary(mask: np.ndarray) -> np.ndarray:
    padded = np.pad(mask.astype(np.uint8), 1, mode="constant")
    total = sum(
        padded[1 + dy:1 + dy + mask.shape[0], 1 + dx:1 + dx + mask.shape[1]]
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
    )
    return total >= int(load_constant("phase21.object_looking.binary_neighbor_min"))


def _edge_magnitude(luma: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(luma.astype(np.float32))
    edge = np.sqrt(gx * gx + gy * gy)
    return edge / max(float(edge.max()), float(load_constant("phase19.confidence.denominator_epsilon")))


def _load_rgb(path: Path | str) -> np.ndarray:
    image = Image.open(Path(path)).convert("RGB")
    return np.asarray(image, dtype=np.float32) / float(load_constant("phase21.object_looking.rgb_scale"))


def _candidate_id(image_path: Path | str, bbox: tuple[int, int, int, int], index: int) -> str:
    payload = f"{Path(image_path).as_posix()}::{bbox}::{int(index)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[
        : int(load_constant("phase21.object_looking.candidate_id_hex_length"))
    ]
