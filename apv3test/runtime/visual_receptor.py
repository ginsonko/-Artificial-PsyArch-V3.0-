from __future__ import annotations

import hashlib
import json
import math
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from PIL import Image, PngImagePlugin

from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


TRAINING_SDPL_ONLY = "training_sdpl_only"
SENSORY_SKETCH = "sensory_sketch"
PROTOTYPE_IMAGINATION = "prototype_imagination"
PERCEIVED_SOURCE = "PERCEIVED_SENSORY_SKETCH"
IMAGINED_SOURCE = "IMAGINED_PROTOTYPE_SKETCH"
DECISION_TIERS = ("firm", "soft", "ambig", "no_call")


@dataclass(frozen=True)
class VisualFastTrace:
    tick: int
    compact_vector: tuple[float, ...]
    channel_lengths: dict[str, int]
    input_trace_hash: str
    elapsed_ms: float
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class VisualAuditTrace:
    tick: int
    feature_vector: tuple[float, ...]
    channel_slices: dict[str, tuple[int, int]]
    channel_lengths: dict[str, int]
    input_trace_hash: str
    source_image_hash: str
    width: int
    height: int
    focus_xy: tuple[float, float]
    segmentation_confidence: float
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RenderArtifact:
    path: Path
    metadata_path: Path
    metadata: dict[str, object]
    image_sha256: str


@dataclass(frozen=True)
class FoveatedLayer:
    level: int
    downsample: int
    pixels: np.ndarray
    edge_pixels: np.ndarray


@dataclass
class SensoryCanvas:
    canvas_pixels: np.ndarray
    canvas_clarity: np.ndarray
    canvas_confidence: np.ndarray
    canvas_freshness: np.ndarray
    last_fixation_xy: tuple[int, int]
    tick: int
    source_image_hash: str
    first_tick: int

    @classmethod
    def from_native_image(cls, image_like: str | Path | Image.Image | np.ndarray, *, tick: int = 0) -> "SensoryCanvas":
        rgb = _as_native_rgb_array(image_like)
        h, w = rgb.shape[:2]
        return cls(
            canvas_pixels=np.zeros_like(rgb, dtype=np.float32),
            canvas_clarity=np.zeros((h, w), dtype=np.float32),
            canvas_confidence=np.zeros((h, w), dtype=np.float32),
            canvas_freshness=np.zeros((h, w), dtype=np.float32),
            last_fixation_xy=(w // 2, h // 2),
            tick=int(tick),
            source_image_hash=_hash_float_array(rgb),
            first_tick=int(tick),
        )

    def update_from_native_image(
        self,
        image_like: str | Path | Image.Image | np.ndarray,
        *,
        focus_xy: tuple[int, int],
        tick: int,
        source_reliability: float = 1.0,
    ) -> None:
        rgb = _as_native_rgb_array(image_like)
        if rgb.shape != self.canvas_pixels.shape:
            raise ValueError("SensoryCanvas image shape mismatch")
        phi = clarity_field(rgb.shape[:2], focus_xy)
        patch_value = render_foveated_from_native(rgb, focus_xy=focus_xy)
        src_conf = phi * float(np.clip(source_reliability, 0.0, 1.0))
        old = self.canvas_confidence
        eps = _float_constant("vision_sensor.fusion_epsilon")
        self.canvas_pixels = ((old[..., None] * self.canvas_pixels) + (src_conf[..., None] * patch_value)) / (
            old[..., None] + src_conf[..., None] + eps
        )
        decay = math.exp(-1.0 / _float_constant("vision_sensor.sensory_memory_tau_ticks"))
        self.canvas_clarity = np.maximum(self.canvas_clarity * decay, phi)
        self.canvas_confidence = np.maximum(self.canvas_confidence * decay, src_conf)
        self.canvas_freshness = np.where(
            phi >= _float_constant("vision_sensor.epsilon_freshness"),
            0.0,
            self.canvas_freshness + 1.0,
        )
        self.last_fixation_xy = (int(focus_xy[0]), int(focus_xy[1]))
        self.tick = int(tick)

    def render_image(self, target_size: int | None = None) -> Image.Image:
        pixels = np.uint8(np.clip(self.canvas_pixels, 0.0, 1.0) * 255.0)
        image = Image.fromarray(pixels, mode="RGB")
        if target_size is None:
            return image
        return image.resize((int(target_size), int(target_size)), Image.Resampling.BILINEAR)

    def clarity_coverage(self) -> float:
        return float((self.canvas_clarity >= _float_constant("vision_sensor.clarity_coverage_threshold")).mean())

    def to_state_item(self) -> StateItem:
        metadata = {
            "fixation_xy": self.last_fixation_xy,
            "patch_native_resolution": True,
            "clarity_mean": float(self.canvas_clarity.mean()),
            "confidence_mean": float(self.canvas_confidence.mean()),
            "tick": int(self.tick),
            "ticks_since_first_view": int(self.tick - self.first_tick),
            "source_image_hash": self.source_image_hash,
            "receptor_version": str(load_constant("phase19.vector.min_runtime_receptor_version")),
        }
        canvas_hash = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode("utf-8")).hexdigest()
        return StateItem(
            sa_id=f"sensory_canvas::{canvas_hash[:24]}::{int(self.tick)}",
            family="sensory_canvas",
            label="sensory_canvas",
            real_energy=float(self.canvas_confidence.mean()),
            attention_energy=float(self.canvas_clarity.mean()),
            cognitive_pressure=1.0 - float(self.canvas_confidence.mean()),
            last_tick=int(self.tick),
            channel_signature=("vision", "perceived", "canvas"),
            source="canvas_update",
            metadata=metadata,
        )


@dataclass(frozen=True)
class RetrievalWeights:
    alpha_part: float
    alpha_shape: float
    alpha_cooccur: float
    alpha_conflict: float


@dataclass
class CooccurrenceMatrix:
    source: str = TRAINING_SDPL_ONLY
    matrix: dict[tuple[str, str], float] = field(default_factory=dict)
    last_updated_tick: int = 0

    def update(
        self,
        left: str,
        right: str,
        value: float,
        *,
        tick: int,
        source_tag: str,
    ) -> None:
        if source_tag != TRAINING_SDPL_ONLY or self.source != TRAINING_SDPL_ONLY:
            raise ValueError("learned_cooccurrence writes require training_sdpl_only")
        key = tuple(sorted((str(left), str(right))))
        self.matrix[key] = float(value)
        self.last_updated_tick = int(tick)


class AuditPathQueue:
    def __init__(self, max_concurrent: int | None = None, *, drop_oldest: bool | None = None) -> None:
        self.max_concurrent = int(max_concurrent or load_constant("vision_sensor.audit_path_max_concurrent"))
        self.drop_oldest = bool(
            load_constant("vision_sensor.audit_path_drop_oldest")
            if drop_oldest is None
            else drop_oldest
        )
        self._items: deque[VisualAuditTrace] = deque()
        self.dropped_count = 0

    def submit(self, trace: VisualAuditTrace) -> bool:
        if len(self._items) >= self.max_concurrent:
            if not self.drop_oldest:
                return False
            self._items.popleft()
            self.dropped_count += 1
        self._items.append(trace)
        return True

    def pop_next(self) -> VisualAuditTrace | None:
        if not self._items:
            return None
        return self._items.popleft()

    def __len__(self) -> int:
        return len(self._items)


def prepare_visual_fast_frame(image_like: str | Path | Image.Image | np.ndarray) -> np.ndarray:
    return _as_rgb_array(image_like, max_px=_int_constant("vision_sensor.fast_resize_px"))


def extract_visual_fast_path(image_like: str | Path | Image.Image | np.ndarray, *, tick: int = 0) -> VisualFastTrace:
    started = time.perf_counter()
    rgb = _as_rgb_array(image_like, max_px=_int_constant("vision_sensor.fast_resize_px"))
    edge = _sobel_magnitude(_luma(rgb))
    v0_rgb = _resize_float_rgb(rgb, _int_constant("vision_sensor.v0_global_grid_px")).reshape(-1)
    v1 = _rgb_hist_regions(rgb, _fast_regions(rgb.shape[0], rgb.shape[1]))
    v4 = _hog_hist(edge, _sobel_orientation(_luma(rgb)), [np.ones(rgb.shape[:2], dtype=bool)])
    v8 = _layout_summary(_quick_mask(rgb, edge), focus_xy=_default_focus())
    compact = np.concatenate([v0_rgb, v1, v4, v8]).astype(np.float32, copy=False)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return VisualFastTrace(
        tick=int(tick),
        compact_vector=_as_float_tuple(compact),
        channel_lengths={
            "V0_fast_rgb": int(v0_rgb.size),
            "V1_fast_rgb_hist": int(v1.size),
            "V4_fast_hog": int(v4.size),
            "V8_fast_layout": int(v8.size),
        },
        input_trace_hash=_hash_float_array(compact),
        elapsed_ms=float(elapsed_ms),
        metadata={
            "pathway": "receptor_fast_path",
            "renders": False,
            "feature_family": "V0_fast+V1_fast+V4_fast+V8_fast",
        },
    )


def extract_visual_audit_path(
    image_like: str | Path | Image.Image | np.ndarray,
    *,
    tick: int = 0,
    focus_xy: tuple[float, float] | None = None,
) -> VisualAuditTrace:
    rgb = _as_rgb_array(image_like)
    focus = focus_xy or _default_focus()
    luma = _luma(rgb)
    edge = _sobel_magnitude(luma)
    orientation = _sobel_orientation(luma)
    mask, segmentation_confidence = _best_mask(rgb, edge)

    channels: list[tuple[str, np.ndarray]] = []
    channels.append(("V0", _v0_vector(rgb, edge, focus)))
    regions12 = _regions_s0_s1_s2(rgb.shape[0], rgb.shape[1])
    regions37 = _regions_s0_s1_s2_s3(rgb.shape[0], rgb.shape[1])
    channels.append(("V1", _rgb_hist_regions(rgb, regions12)))
    channels.append(("V2", _hsv_hist_regions(rgb, regions12)))
    channels.append(("V3", _lbp_regions(luma, regions37)))
    channels.append(("V4", _hog_hist(edge, orientation, regions37)))
    channels.append(("V5", _radial_profile(edge, _int_constant("vision_sensor.v5_radial_bins"))))
    channels.append(("V6", _shape_geometry(mask)))
    channels.append(("V7", _part_prototype_coverage(rgb, mask)))
    channels.append(("V8", _layout_summary(mask, focus_xy=focus)))
    channels.append(("V9", _foreground_background_kl(rgb, luma, mask)))
    channels.append(("V10", _per_part_color_texture(rgb, mask)))
    channels.append(("V11", _part_relational_graph(rgb, mask)))
    channels.append(("V12", _color_cluster_spatial_map(rgb, mask)))

    feature_parts: list[np.ndarray] = []
    slices: dict[str, tuple[int, int]] = {}
    lengths: dict[str, int] = {}
    cursor = 0
    for name, vector in channels:
        clean = np.nan_to_num(vector.astype(np.float32, copy=False), copy=False)
        start = cursor
        cursor += int(clean.size)
        slices[name] = (start, cursor)
        lengths[name] = int(clean.size)
        feature_parts.append(clean.reshape(-1))

    feature = np.concatenate(feature_parts).astype(np.float32, copy=False)
    expected = _int_constant("vision_sensor.feature_vector_dim")
    if int(feature.size) != expected:
        raise ValueError(f"visual feature dimension mismatch: {feature.size} != {expected}")
    image_hash = _hash_float_array(rgb.astype(np.float32))
    trace_hash = _hash_float_array(feature)
    return VisualAuditTrace(
        tick=int(tick),
        feature_vector=_as_float_tuple(feature),
        channel_slices=slices,
        channel_lengths=lengths,
        input_trace_hash=trace_hash,
        source_image_hash=image_hash,
        width=int(rgb.shape[1]),
        height=int(rgb.shape[0]),
        focus_xy=(float(focus[0]), float(focus[1])),
        segmentation_confidence=float(segmentation_confidence),
        metadata={
            "pathway": "reconstruction_audit_path",
            "feature_vector_dim": int(feature.size),
            "evaluator_label_accessed": False,
            "fast_path_paired": False,
        },
    )


def extract_visual_audit_path_v2(
    image_like: str | Path | Image.Image | np.ndarray,
    *,
    tick: int = 0,
    focus_xy: tuple[int, int] | None = None,
) -> VisualAuditTrace:
    rgb = _as_native_rgb_array(image_like)
    focus = focus_xy or _native_default_focus(rgb)
    luma = _luma(rgb)
    edge = _sobel_magnitude(luma)
    orientation = _sobel_orientation(luma)
    mask, segmentation_confidence = _best_mask(rgb, edge)

    channels: list[tuple[str, np.ndarray]] = []
    channels.append(("V0", _v0_foveated_vector(rgb, edge, focus)))
    regions12 = _regions_s0_s1_s2(rgb.shape[0], rgb.shape[1])
    regions37 = _regions_s0_s1_s2_s3(rgb.shape[0], rgb.shape[1])
    channels.append(("V1", _rgb_hist_regions(rgb, regions12)))
    channels.append(("V2", _hsv_hist_regions(rgb, regions12)))
    channels.append(("V3", _lbp_regions(luma, regions37)))
    channels.append(("V4", _hog_hist(edge, orientation, regions37)))
    channels.append(("V5", _radial_profile(edge, _int_constant("vision_sensor.v5_radial_bins"))))
    channels.append(("V6", _shape_geometry(mask)))
    channels.append(("V7", _part_prototype_coverage(rgb, mask)))
    channels.append(("V8", _layout_summary(mask, focus_xy=(focus[0] / max(rgb.shape[1] - 1, 1), focus[1] / max(rgb.shape[0] - 1, 1)))))
    channels.append(("V9", _foreground_background_kl(rgb, luma, mask)))
    channels.append(("V10", _per_part_color_texture(rgb, mask)))
    channels.append(("V11", _part_relational_graph(rgb, mask)))
    channels.append(("V12", _color_cluster_spatial_map(rgb, mask)))

    feature_parts: list[np.ndarray] = []
    slices: dict[str, tuple[int, int]] = {}
    lengths: dict[str, int] = {}
    cursor = 0
    for name, vector in channels:
        clean = np.nan_to_num(vector.astype(np.float32, copy=False), copy=False)
        start = cursor
        cursor += int(clean.size)
        slices[name] = (start, cursor)
        lengths[name] = int(clean.size)
        feature_parts.append(clean.reshape(-1))
    feature = np.concatenate(feature_parts).astype(np.float32, copy=False)
    expected = _int_constant("phase19.vector.visual_receptor_feature_dim")
    if int(feature.size) != expected:
        raise ValueError(f"visual v2 feature dimension mismatch: {feature.size} != {expected}")
    return VisualAuditTrace(
        tick=int(tick),
        feature_vector=_as_float_tuple(feature),
        channel_slices=slices,
        channel_lengths=lengths,
        input_trace_hash=_hash_float_array(feature),
        source_image_hash=_hash_float_array(rgb),
        width=int(rgb.shape[1]),
        height=int(rgb.shape[0]),
        focus_xy=(float(focus[0]), float(focus[1])),
        segmentation_confidence=float(segmentation_confidence),
        metadata={
            "pathway": "reconstruction_audit_path_v2",
            "feature_vector_dim": int(feature.size),
            "evaluator_label_accessed": False,
            "receptor_version": str(load_constant("phase19.vector.min_runtime_receptor_version")),
            "patch_native_resolution": True,
            "canvas_state_dim": int(load_constant("phase19.vector.canvas_state_dim")),
        },
    )


def extract_visual_audit_path_v2_object_centric(
    image_like: str | Path | Image.Image | np.ndarray,
    *,
    candidate_bbox: tuple[int, int, int, int],
    tick: int = 0,
    focus_xy: tuple[int, int] | None = None,
) -> VisualAuditTrace:
    """@op_count: O(candidate_width * candidate_height * feature_dim)."""
    rgb = _as_native_rgb_array(image_like)
    height, width = rgb.shape[:2]
    x1, y1, x2, y2 = _clip_bbox(candidate_bbox, width=width, height=height)
    local_rgb = rgb[y1:y2, x1:x2]
    if local_rgb.size == 0:
        local_rgb = rgb
        x1, y1, x2, y2 = 0, 0, width, height
    local_focus = focus_xy
    if local_focus is None:
        local_focus = _native_default_focus(local_rgb)
    else:
        local_focus = (
            int(np.clip(int(local_focus[0]) - x1, 0, max(local_rgb.shape[1] - 1, 0))),
            int(np.clip(int(local_focus[1]) - y1, 0, max(local_rgb.shape[0] - 1, 0))),
        )
    trace = extract_visual_audit_path_v2(local_rgb, tick=tick, focus_xy=local_focus)
    metadata = dict(trace.metadata)
    metadata.update(
        {
            "object_centric": True,
            "parent_width": int(width),
            "parent_height": int(height),
            "candidate_bbox": (int(x1), int(y1), int(x2), int(y2)),
            "parent_focus_xy": (int(x1 + local_focus[0]), int(y1 + local_focus[1])),
            "local_source_image_hash": trace.source_image_hash,
            "evaluator_label_accessed": False,
        }
    )
    return VisualAuditTrace(
        tick=trace.tick,
        feature_vector=trace.feature_vector,
        channel_slices=trace.channel_slices,
        channel_lengths=trace.channel_lengths,
        input_trace_hash=trace.input_trace_hash,
        source_image_hash=_hash_float_array(rgb),
        width=trace.width,
        height=trace.height,
        focus_xy=trace.focus_xy,
        segmentation_confidence=trace.segmentation_confidence,
        metadata=metadata,
    )


def render_sensory_sketch(
    trace: VisualAuditTrace,
    *,
    out_dir: str | Path = "data/inner_picture/phase19_0",
    stem: str | None = None,
) -> RenderArtifact:
    image = _render_sketch_image(trace)
    metadata = _render_metadata(
        trace,
        render_mode=SENSORY_SKETCH,
        epistemic_source=PERCEIVED_SOURCE,
        prototype_trace_hash=None,
        source_confidence=max(float(trace.segmentation_confidence), _float_constant("vision_sensor.source_confidence_floor")),
    )
    return _write_render_artifact(image, metadata, out_dir=out_dir, stem=stem or f"sensory_{trace.input_trace_hash[:16]}")


def render_prototype_imagination(
    trace: VisualAuditTrace,
    *,
    out_dir: str | Path = "data/inner_picture/phase19_0",
    stem: str | None = None,
) -> RenderArtifact:
    image = _render_proto_image(trace)
    prototype_hash = _hash_float_array(np.asarray(trace.feature_vector, dtype=np.float32)[
        trace.channel_slices["V1"][0]: trace.channel_slices["V8"][1]
    ])
    metadata = _render_metadata(
        trace,
        render_mode=PROTOTYPE_IMAGINATION,
        epistemic_source=IMAGINED_SOURCE,
        prototype_trace_hash=prototype_hash,
        source_confidence=_float_constant("vision_sensor.prototype_source_confidence"),
    )
    return _write_render_artifact(image, metadata, out_dir=out_dir, stem=stem or f"proto_{prototype_hash[:16]}")


def make_inner_picture_state(
    trace: VisualAuditTrace,
    artifact: RenderArtifact,
    *,
    tick: int,
) -> StateItem:
    metadata = dict(artifact.metadata)
    mode = str(metadata["render_mode"])
    source_key = "sensory" if mode == SENSORY_SKETCH else "imagined"
    hash_key = str(metadata["input_trace_hash"] if source_key == "sensory" else metadata["prototype_trace_hash"])
    sa_id = f"inner_picture::{source_key}::{hash_key[:24]}::{int(tick)}"
    return StateItem(
        sa_id=sa_id,
        family="inner_picture",
        label="inner_picture_sketch",
        real_energy=float(metadata["source_confidence"]),
        cognitive_pressure=1.0 - float(metadata["source_confidence"]),
        last_tick=int(tick),
        channel_signature=("vision", source_key, "sketch"),
        source="reconstruction_R",
        metadata={
            **metadata,
            "rendered_png_bytes_sha256": artifact.image_sha256,
            "rendered_png_path": artifact.path.as_posix(),
            "feature_vector_sha256": trace.input_trace_hash,
        },
    )


def assert_retrieval_alpha_weights(weights: RetrievalWeights | None = None) -> RetrievalWeights:
    loaded = weights or RetrievalWeights(
        alpha_part=_float_constant("vision_sensor.alpha_part"),
        alpha_shape=_float_constant("vision_sensor.alpha_shape"),
        alpha_cooccur=_float_constant("vision_sensor.alpha_cooccur"),
        alpha_conflict=_float_constant("vision_sensor.alpha_conflict"),
    )
    if loaded.alpha_part + loaded.alpha_shape + loaded.alpha_cooccur > 1.0:
        raise ValueError("retrieval alpha_part + alpha_shape + alpha_cooccur must be <= 1")
    if not (0.0 <= loaded.alpha_conflict <= 0.5):
        raise ValueError("retrieval alpha_conflict must be in [0, 0.5]")
    return loaded


def normalized_recall_score(raw_recall: float) -> float:
    kappa = _float_constant("vision_sensor.kappa_recall")
    midpoint = _float_constant("vision_sensor.recall_midpoint")
    value = 1.0 / (1.0 + math.exp(-kappa * (float(raw_recall) - midpoint)))
    return float(max(0.0, min(1.0, value)))


def sample_audit_images(limit: int | None = None) -> tuple[Path, ...]:
    roots = (
        Path("真实图片测试资产"),
        Path("config/curriculum/assets/visual/clean_cards"),
        Path("config/curriculum/assets/visual/real"),
    )
    paths: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            paths.extend(sorted(root.glob(pattern)))
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = path.resolve().as_posix().lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    if limit is not None:
        return tuple(unique[: int(limit)])
    return tuple(unique)


def foveal_radius_px(width: int, height: int) -> int:
    ratio = _float_constant("vision_sensor.foveal_radius_ratio_k")
    min_px = _int_constant("vision_sensor.foveal_radius_min_px")
    max_px = _int_constant("vision_sensor.foveal_radius_max_px")
    return int(np.clip(round(ratio * min(int(width), int(height))), min_px, max_px))


def build_foveated_pyramid(
    image_like: str | Path | Image.Image | np.ndarray,
    *,
    focus_xy: tuple[int, int] | None = None,
) -> tuple[FoveatedLayer, ...]:
    rgb = _as_native_rgb_array(image_like)
    focus = focus_xy or _native_default_focus(rgb)
    layer_count = _int_constant("vision_sensor.foveal_layer_count")
    layers: list[FoveatedLayer] = []
    for level in range(layer_count):
        downsample = int(2 ** level)
        if level == 0:
            tile = _native_focus_core(rgb, focus)
        else:
            tile = rgb.copy()
            for _ in range(level):
                tile = _box_average_half(tile)
            tile = _resize_box_average(tile, _int_constant("vision_sensor.v0_layer_tile_px"))
        edge_tile = _resize_box_average(_sobel_magnitude(_luma(tile))[..., None], _int_constant("vision_sensor.v0_layer_tile_px"))[..., 0]
        if tile.shape[:2] != (_int_constant("vision_sensor.v0_layer_tile_px"), _int_constant("vision_sensor.v0_layer_tile_px")):
            tile = _resize_box_average(tile, _int_constant("vision_sensor.v0_layer_tile_px"))
        layers.append(FoveatedLayer(level=level, downsample=downsample, pixels=tile, edge_pixels=edge_tile))
    return tuple(layers)


def clarity_field(shape: tuple[int, int], focus_xy: tuple[int, int]) -> np.ndarray:
    height, width = int(shape[0]), int(shape[1])
    yy, xx = np.indices((height, width))
    sigma = _float_constant("vision_sensor.clarity_focus_sigma_px")
    floor = _float_constant("vision_sensor.clarity_floor")
    dist2 = (xx - int(focus_xy[0])) ** 2 + (yy - int(focus_xy[1])) ** 2
    raw = np.exp(-dist2 / max(2.0 * sigma * sigma, 1e-6))
    return np.clip(floor + (1.0 - floor) * raw, 0.0, 1.0).astype(np.float32)


def render_foveated_from_native(
    image_like: str | Path | Image.Image | np.ndarray,
    *,
    focus_xy: tuple[int, int] | None = None,
) -> np.ndarray:
    rgb = _as_native_rgb_array(image_like)
    focus = focus_xy or _native_default_focus(rgb)
    phi = clarity_field(rgb.shape[:2], focus)
    coarse_side = max(_int_constant("vision_sensor.v0_layer_tile_px"), min(rgb.shape[0], rgb.shape[1]) // 4)
    blurred = _resize_box_average(rgb, coarse_side)
    blurred = np.asarray(
        Image.fromarray(np.uint8(np.clip(blurred, 0.0, 1.0) * 255.0), mode="RGB").resize(
            (rgb.shape[1], rgb.shape[0]), Image.Resampling.NEAREST
        ),
        dtype=np.float32,
    ) / 255.0
    return (phi[..., None] * rgb + (1.0 - phi[..., None]) * blurred).astype(np.float32)


def render_sensory_canvas_sketch(
    canvas: SensoryCanvas,
    *,
    out_dir: str | Path = "data/inner_picture/phase19_0a",
    stem: str | None = None,
) -> RenderArtifact:
    image = canvas.render_image(_int_constant("vision_sensor.render_px"))
    metadata = {
        "render_mode": SENSORY_SKETCH,
        "epistemic_source": PERCEIVED_SOURCE,
        "receptor_version": str(load_constant("phase19.vector.min_runtime_receptor_version")),
        "source_image_hash": canvas.source_image_hash,
        "canvas_clarity_mean": float(canvas.canvas_clarity.mean()),
        "canvas_confidence_mean": float(canvas.canvas_confidence.mean()),
        "clarity_coverage": canvas.clarity_coverage(),
        "patch_native_resolution": True,
        "evaluator_label_accessed": False,
        "phase19_0a": True,
    }
    return _write_render_artifact(image, metadata, out_dir=out_dir, stem=stem or f"sensory_canvas_{canvas.source_image_hash[:16]}_{canvas.tick}")


def render_remembered_overlay_stub(
    *,
    out_dir: str | Path = "data/inner_picture/phase19_0a",
    stem: str = "remembered_overlay_schema",
) -> RenderArtifact:
    image = Image.new("RGB", (_int_constant("vision_sensor.render_px"), _int_constant("vision_sensor.render_px")), (238, 241, 239))
    metadata = {
        "render_mode": "remembered_overlay",
        "epistemic_source": "REMEMBERED_SKETCH",
        "schema_only": True,
        "phase19_0b1_required_for_real_recall": True,
        "evaluator_label_accessed": False,
    }
    return _write_render_artifact(image, metadata, out_dir=out_dir, stem=stem)


def render_prediction_overlay_stub(
    *,
    out_dir: str | Path = "data/inner_picture/phase19_0a",
    stem: str = "prediction_overlay_schema",
) -> RenderArtifact:
    image = Image.new("RGB", (_int_constant("vision_sensor.render_px"), _int_constant("vision_sensor.render_px")), (242, 238, 232))
    metadata = {
        "render_mode": "prediction_overlay",
        "epistemic_source": "INFERRED_SKETCH",
        "schema_only": True,
        "phase19_2_required_for_real_prediction": True,
        "evaluator_label_accessed": False,
    }
    return _write_render_artifact(image, metadata, out_dir=out_dir, stem=stem)


def canvas_similarity(native_rgb: np.ndarray, canvas: SensoryCanvas) -> float:
    if native_rgb.shape != canvas.canvas_pixels.shape:
        raise ValueError("canvas similarity shape mismatch")
    mse = float(np.mean((native_rgb - canvas.canvas_pixels) ** 2))
    return float(max(0.0, min(1.0, 1.0 - mse)))


def _render_metadata(
    trace: VisualAuditTrace,
    *,
    render_mode: str,
    epistemic_source: str,
    prototype_trace_hash: str | None,
    source_confidence: float,
) -> dict[str, object]:
    return {
        "render_mode": render_mode,
        "input_trace_hash": trace.input_trace_hash,
        "prototype_trace_hash": prototype_trace_hash,
        "evaluator_label_accessed": False,
        "epistemic_source": epistemic_source,
        "source_confidence": float(max(0.0, min(1.0, source_confidence))),
        "confidence_score": 0.0,
        "decision_tier": "no_call",
        "confidence_decomposition": {
            "Pi": 0.0,
            "Gamma": 0.0,
            "Q": float(trace.segmentation_confidence),
            "mu": 0.0,
            "nu_object": None,
            "nu_context": None,
            "active_cues": [],
            "channel_evidence": {f"V{i}": float(trace.channel_lengths.get(f"V{i}", 0)) for i in range(10)},
            "phase19_2_pending": True,
        },
        "feature_vector_dim": len(trace.feature_vector),
        "source_image_hash": trace.source_image_hash,
    }


def _write_render_artifact(
    image: Image.Image,
    metadata: Mapping[str, object],
    *,
    out_dir: str | Path,
    stem: str,
) -> RenderArtifact:
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{stem}.png"
    metadata_path = target_dir / f"{stem}.json"
    png_info = PngImagePlugin.PngInfo()
    png_info.add_text("apv3_phase19_metadata", json.dumps(metadata, ensure_ascii=False, sort_keys=True))
    image.save(path, format="PNG", pnginfo=png_info)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return RenderArtifact(
        path=path,
        metadata_path=metadata_path,
        metadata=dict(metadata),
        image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _render_sketch_image(trace: VisualAuditTrace) -> Image.Image:
    feature = np.asarray(trace.feature_vector, dtype=np.float32)
    v0_start, _ = trace.channel_slices["V0"]
    grid_px = _int_constant("vision_sensor.v0_global_grid_px")
    render_px = _int_constant("vision_sensor.render_px")
    global_rgb = feature[v0_start: v0_start + grid_px * grid_px * 3].reshape(grid_px, grid_px, 3)
    image = Image.fromarray(np.uint8(np.clip(global_rgb, 0.0, 1.0) * 255.0), mode="RGB")
    image = image.resize((render_px, render_px), Image.Resampling.BILINEAR)

    focus_px = _int_constant("vision_sensor.v0_focus_patch_px")
    patch_start = v0_start + grid_px * grid_px * 3 + grid_px * grid_px * 3 + grid_px * grid_px
    patch = feature[patch_start: patch_start + focus_px * focus_px * 3].reshape(focus_px, focus_px, 3)
    patch_img = Image.fromarray(np.uint8(np.clip(patch, 0.0, 1.0) * 255.0), mode="RGB")
    patch_img = patch_img.resize((render_px // 2, render_px // 2), Image.Resampling.BILINEAR)
    image.paste(patch_img, (render_px // 4, render_px // 4))
    return image


def _render_proto_image(trace: VisualAuditTrace) -> Image.Image:
    render_px = _int_constant("vision_sensor.render_px")
    feature = np.asarray(trace.feature_vector, dtype=np.float32)
    v0_start, _ = trace.channel_slices["V0"]
    grid_px = _int_constant("vision_sensor.v0_global_grid_px")
    focus_px = _int_constant("vision_sensor.v0_focus_patch_px")
    patch_start = v0_start + grid_px * grid_px * 3 + grid_px * grid_px * 3 + grid_px * grid_px
    patch = feature[patch_start: patch_start + focus_px * focus_px * 3].reshape(focus_px, focus_px, 3)
    hsv = _rgb_to_hsv(patch)
    objectish = (hsv[..., 1] > 0.12) & (hsv[..., 2] < 0.96)
    pixels = patch[objectish] if objectish.any() else patch.reshape(-1, 3)
    color = np.uint8(np.clip(pixels.mean(axis=0), 0.0, 1.0) * 255.0)
    canvas = np.ones((render_px, render_px, 3), dtype=np.uint8) * np.uint8(245)
    mask_start, _ = trace.channel_slices["V8"]
    layout = feature[mask_start: mask_start + 5]
    cx = int(float(layout[0]) * (render_px - 1))
    cy = int(float(layout[1]) * (render_px - 1))
    area = max(float(layout[3]), 0.05)
    radius = int(max(render_px * 0.12, math.sqrt(area) * render_px * 0.35))
    yy, xx = np.ogrid[:render_px, :render_px]
    blob = ((xx - cx) ** 2 + (yy - cy) ** 2) <= radius * radius
    canvas[blob] = color
    image = Image.fromarray(canvas, mode="RGB")
    return image


def _v0_vector(rgb: np.ndarray, edge: np.ndarray, focus_xy: tuple[float, float]) -> np.ndarray:
    grid = _int_constant("vision_sensor.v0_global_grid_px")
    focus_px = _int_constant("vision_sensor.v0_focus_patch_px")
    low_rgb = _resize_float_rgb(rgb, grid).reshape(-1)
    low_lab = _resize_float_array(_rgb_to_lab(rgb), grid).reshape(-1)
    low_edge = _resize_float_gray(edge, grid).reshape(-1)
    patch_rgb = _focus_patch(rgb, focus_xy, focus_px)
    patch_edge = _focus_patch(edge[..., None], focus_xy, focus_px)[..., 0]
    return np.concatenate([low_rgb, low_lab, low_edge, patch_rgb.reshape(-1), patch_edge.reshape(-1)])


def _v0_foveated_vector(rgb: np.ndarray, edge: np.ndarray, focus_xy: tuple[int, int]) -> np.ndarray:
    layers = build_foveated_pyramid(rgb, focus_xy=focus_xy)
    rgb_parts = [layer.pixels.reshape(-1) for layer in layers]
    edge_parts = [layer.edge_pixels.reshape(-1) for layer in layers]
    vector = np.concatenate(rgb_parts + edge_parts).astype(np.float32, copy=False)
    expected = _int_constant("vision_sensor.v0_foveated_dim")
    if int(vector.size) != expected:
        raise ValueError(f"V0 foveated dimension mismatch: {vector.size} != {expected}")
    return vector


def _rgb_hist_regions(rgb: np.ndarray, regions: Sequence[np.ndarray]) -> np.ndarray:
    vectors = []
    bins = _int_constant("vision_sensor.rgb_hist_bins")
    bin_index = np.minimum((rgb * bins).astype(int), bins - 1)
    for region in regions:
        if not region.any():
            vectors.append(np.zeros(bins * 3, dtype=np.float32))
            continue
        parts = [
            np.bincount(bin_index[..., channel][region].reshape(-1), minlength=bins).astype(np.float32)
            for channel in range(3)
        ]
        hist = np.concatenate(parts)
        vectors.append(hist / max(float(hist.sum()), 1.0))
    return np.concatenate(vectors)


def _hsv_hist_regions(rgb: np.ndarray, regions: Sequence[np.ndarray]) -> np.ndarray:
    hsv = _rgb_to_hsv(rgb)
    vectors = []
    h_bins = _int_constant("vision_sensor.hsv_h_bins")
    s_bins = _int_constant("vision_sensor.hsv_s_bins")
    v_bins = _int_constant("vision_sensor.hsv_v_bins")
    for region in regions:
        pixels = hsv[region]
        if pixels.size == 0:
            vectors.append(np.zeros(h_bins * s_bins * v_bins, dtype=np.float32))
            continue
        h = np.minimum((pixels[:, 0] * h_bins).astype(int), h_bins - 1)
        s = np.minimum((pixels[:, 1] * s_bins).astype(int), s_bins - 1)
        v = np.minimum((pixels[:, 2] * v_bins).astype(int), v_bins - 1)
        idx = h * s_bins * v_bins + s * v_bins + v
        hist = np.bincount(idx, minlength=h_bins * s_bins * v_bins).astype(np.float32)
        vectors.append(hist / max(float(hist.sum()), 1.0))
    return np.concatenate(vectors)


def _lbp_regions(luma: np.ndarray, regions: Sequence[np.ndarray]) -> np.ndarray:
    vectors = []
    bins = _int_constant("vision_sensor.lbp_bins")
    codes_by_radius = [_lbp_codes(luma, radius) for radius in (1, 2, 3)]
    for region in regions:
        per_region = []
        for codes in codes_by_radius:
            values = codes[region]
            hist = np.bincount((values % bins).reshape(-1), minlength=bins).astype(np.float32)
            per_region.append(hist / max(float(hist.sum()), 1.0))
        vectors.append(np.concatenate(per_region))
    return np.concatenate(vectors)


def _hog_hist(edge: np.ndarray, orientation: np.ndarray, regions: Sequence[np.ndarray]) -> np.ndarray:
    vectors = []
    bins = _int_constant("vision_sensor.hog_bins")
    bin_index = np.floor(((orientation + math.pi) / (2.0 * math.pi)) * bins).astype(int)
    bin_index = np.clip(bin_index, 0, bins - 1)
    for region in regions:
        weights = edge[region]
        indexes = bin_index[region]
        hist = np.bincount(indexes.reshape(-1), weights=weights.reshape(-1), minlength=bins).astype(np.float32)
        norm = float(np.linalg.norm(hist))
        vectors.append(hist / max(norm, 1e-6))
    return np.concatenate(vectors)


def _radial_profile(edge: np.ndarray, bins: int) -> np.ndarray:
    h, w = edge.shape
    yy, xx = np.indices((h, w))
    cx = (w - 1) / 2.0
    cy = (h - 1) / 2.0
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    dist = dist / max(float(dist.max()), 1e-6)
    idx = np.minimum((dist * bins).astype(int), bins - 1)
    sums = np.bincount(idx.reshape(-1), weights=edge.reshape(-1), minlength=bins).astype(np.float32)
    counts = np.bincount(idx.reshape(-1), minlength=bins).astype(np.float32)
    return sums / np.maximum(counts, 1.0)


def _shape_geometry(mask: np.ndarray) -> np.ndarray:
    ys, xs = np.where(mask)
    if xs.size == 0:
        return np.zeros(40, dtype=np.float32)
    h, w = mask.shape
    width = max(int(xs.max() - xs.min() + 1), 1)
    height = max(int(ys.max() - ys.min() + 1), 1)
    aspect = min(width / max(height, 1), height / max(width, 1))
    bbox_fill = float(mask.sum()) / float(max(width * height, 1))
    perimeter = _mask_perimeter(mask)
    circularity = 4.0 * math.pi * float(mask.sum()) / max(float(perimeter * perimeter), 1.0)
    centered = np.stack([xs - xs.mean(), ys - ys.mean()], axis=1)
    if centered.shape[0] > 1:
        cov = np.cov(centered, rowvar=False)
        eigvals, eigvecs = np.linalg.eigh(cov)
        vec = eigvecs[:, int(np.argmax(eigvals))]
        orientation = abs(math.atan2(float(vec[1]), float(vec[0]))) / math.pi
    else:
        orientation = 0.0
    crop = mask[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1]
    flipped = np.fliplr(crop)
    min_w = min(crop.shape[1], flipped.shape[1])
    symmetry = 1.0 - float(np.logical_xor(crop[:, :min_w], flipped[:, :min_w]).sum()) / max(float(crop[:, :min_w].sum() + flipped[:, :min_w].sum()), 1.0)
    legacy = np.asarray([
        max(0.0, min(1.0, aspect)),
        max(0.0, min(1.0, bbox_fill)),
        max(0.0, min(1.0, circularity)),
        max(0.0, min(1.0, orientation)),
        max(0.0, min(1.0, symmetry)),
    ], dtype=np.float32)
    boundary_y, boundary_x = np.where(_mask_boundary(mask))
    fourier = _contour_fourier_descriptor(boundary_x, boundary_y)
    pca_ratio = _pca_ratio_feature(xs, ys)
    curvature = _contour_curvature_feature(boundary_x, boundary_y)
    corners = _corner_density_feature(mask)
    return np.concatenate([
        legacy,
        fourier,
        np.asarray([pca_ratio, curvature, corners], dtype=np.float32),
    ]).astype(np.float32)


def _part_prototype_coverage(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    top_k = _int_constant("vision_sensor.part_top_k")
    cells = _int_constant("vision_sensor.part_spatial_cells")
    codes, xs, ys, _hsv, _luma, _edge = _part_code_data(rgb, mask)
    if codes.size == 0:
        return np.zeros(top_k + top_k * cells, dtype=np.float32)
    coverage = np.bincount(codes, minlength=top_k).astype(np.float32)[:top_k]
    total = max(float(coverage.sum()), 1.0)
    coverage = coverage / total
    h, w = mask.shape
    x_mid = (w - 1) / 2.0
    y_mid = (h - 1) / 2.0
    cell_index = (ys > y_mid).astype(int) * 2 + (xs > x_mid).astype(int)
    spatial = np.zeros((top_k, cells), dtype=np.float32)
    np.add.at(spatial, (codes, cell_index), 1.0 / total)
    return np.concatenate([coverage, spatial.reshape(-1)]).astype(np.float32)


def _per_part_color_texture(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    codes, _xs, _ys, hsv, luma, edge = _part_code_data(rgb, mask)
    top_k = _int_constant("vision_sensor.part_top_k")
    features_per_part = _int_constant("vision_sensor.part_profile_features")
    out = np.zeros((top_k, features_per_part), dtype=np.float32)
    if codes.size == 0:
        return out.reshape(-1)
    total = max(float(codes.size), 1.0)
    for code in range(top_k):
        selected = codes == code
        if not selected.any():
            continue
        out[code] = np.asarray([
            float(hsv[selected, 0].mean()),
            float(hsv[selected, 1].mean()),
            float(hsv[selected, 2].mean()),
            float(luma[selected].mean()),
            float(edge[selected].mean()),
            float(selected.sum()) / total,
        ], dtype=np.float32)
    return out.reshape(-1)


def _part_relational_graph(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    codes, xs, ys, _hsv, _luma, edge = _part_code_data(rgb, mask)
    slots = _int_constant("vision_sensor.part_relation_slots")
    features = _int_constant("vision_sensor.part_relation_features")
    out = np.zeros((slots, features), dtype=np.float32)
    if codes.size == 0:
        return out.reshape(-1)
    counts = np.bincount(codes, minlength=_int_constant("vision_sensor.part_top_k")).astype(np.float32)
    ordered = np.argsort(counts)[::-1][:slots]
    h, w = mask.shape
    total = max(float(codes.size), 1.0)
    center_x = float(xs.mean()) / max(float(w - 1), 1.0)
    center_y = float(ys.mean()) / max(float(h - 1), 1.0)
    for slot, code in enumerate(ordered):
        selected = codes == int(code)
        if not selected.any():
            continue
        px = xs[selected].astype(np.float32)
        py = ys[selected].astype(np.float32)
        cx = float(px.mean()) / max(float(w - 1), 1.0)
        cy = float(py.mean()) / max(float(h - 1), 1.0)
        dx = cx - center_x
        dy = cy - center_y
        dist = min(1.0, math.sqrt(dx * dx + dy * dy))
        angle = (math.atan2(dy, dx) + math.pi) / (2.0 * math.pi)
        spread_x = float(px.std()) / max(float(w - 1), 1.0)
        spread_y = float(py.std()) / max(float(h - 1), 1.0)
        out[slot] = np.asarray([
            float(code) / max(float(_int_constant("vision_sensor.part_top_k") - 1), 1.0),
            float(selected.sum()) / total,
            cx,
            cy,
            dist,
            angle,
            float(edge[selected].mean()),
            min(1.0, abs(spread_x - spread_y)),
        ], dtype=np.float32)
    return out.reshape(-1)


def _color_cluster_spatial_map(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    hsv = _rgb_to_hsv(rgb)
    bins = _int_constant("vision_sensor.color_cluster_bins")
    features = _int_constant("vision_sensor.color_cluster_features")
    out = np.zeros((bins, features), dtype=np.float32)
    ys, xs = np.where(mask)
    if xs.size == 0:
        return out.reshape(-1)
    hue = hsv[..., 0][mask]
    edge = _sobel_magnitude(_luma(rgb))[mask]
    codes = np.minimum((hue * bins).astype(int), bins - 1)
    h, w = mask.shape
    total = max(float(xs.size), 1.0)
    for code in range(bins):
        selected = codes == code
        if not selected.any():
            continue
        px = xs[selected].astype(np.float32)
        py = ys[selected].astype(np.float32)
        out[code] = np.asarray([
            float(selected.sum()) / total,
            float(px.mean()) / max(float(w - 1), 1.0),
            float(py.mean()) / max(float(h - 1), 1.0),
            float((py < (h - 1) / 2.0).sum()) / max(float(selected.sum()), 1.0),
            float((px < (w - 1) / 2.0).sum()) / max(float(selected.sum()), 1.0),
            float(edge[selected].mean()),
        ], dtype=np.float32)
    return out.reshape(-1)


def _part_code_data(
    rgb: np.ndarray,
    mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    hsv_full = _rgb_to_hsv(rgb)
    luma_full = _luma(rgb)
    edge_full = _sobel_magnitude(luma_full)
    ys, xs = np.where(mask)
    if xs.size == 0:
        empty_i = np.zeros(0, dtype=np.int64)
        empty_f = np.zeros((0, 3), dtype=np.float32)
        return empty_i, empty_i, empty_i, empty_f, np.zeros(0, dtype=np.float32), np.zeros(0, dtype=np.float32)
    hsv = hsv_full[ys, xs]
    luma = luma_full[ys, xs]
    edge = edge_full[ys, xs]
    hue_bins = _int_constant("vision_sensor.color_cluster_bins")
    hue_code = np.minimum((hsv[:, 0] * hue_bins).astype(np.int64), hue_bins - 1)
    sat_threshold = float(np.median(hsv[:, 1]))
    val_threshold = float(np.median(hsv[:, 2]))
    edge_threshold = float(np.percentile(edge, _int_constant("vision_sensor.mask_edge_percentile")))
    sat_code = (hsv[:, 1] > sat_threshold).astype(np.int64)
    val_code = (hsv[:, 2] > val_threshold).astype(np.int64)
    edge_code = (edge > edge_threshold).astype(np.int64)
    codes = hue_code * 8 + sat_code * 4 + val_code * 2 + edge_code
    codes = np.minimum(codes, _int_constant("vision_sensor.part_top_k") - 1)
    return codes.astype(np.int64), xs.astype(np.int64), ys.astype(np.int64), hsv.astype(np.float32), luma.astype(np.float32), edge.astype(np.float32)


def _mask_boundary(mask: np.ndarray) -> np.ndarray:
    padded = np.pad(mask.astype(np.uint8), 1, mode="constant")
    neighbor_count = sum(
        padded[1 + dy:1 + dy + mask.shape[0], 1 + dx:1 + dx + mask.shape[1]]
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
    )
    return mask & (neighbor_count < 9)


def _contour_fourier_descriptor(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    pairs = 16
    if xs.size < 2:
        return np.zeros(pairs * 2, dtype=np.float32)
    cx = float(xs.mean())
    cy = float(ys.mean())
    angles = np.arctan2(ys - cy, xs - cx)
    order = np.argsort(angles)
    points = (xs[order] - cx) + 1j * (ys[order] - cy)
    scale = max(float(np.abs(points).max()), float(load_constant("phase19.confidence.denominator_epsilon")))
    spectrum = np.fft.fft(points / scale)
    selected = spectrum[1:pairs + 1]
    if selected.size < pairs:
        selected = np.pad(selected, (0, pairs - selected.size), mode="constant")
    return np.concatenate([selected.real, selected.imag]).astype(np.float32)


def _pca_ratio_feature(xs: np.ndarray, ys: np.ndarray) -> float:
    if xs.size < 2:
        return 0.0
    centered = np.stack([xs - xs.mean(), ys - ys.mean()], axis=1)
    eigvals = np.linalg.eigvalsh(np.cov(centered, rowvar=False))
    ratio = math.sqrt(float(eigvals.max()) / max(float(eigvals.min()), float(load_constant("phase19.confidence.denominator_epsilon"))))
    return max(0.0, min(1.0, (ratio - 1.0) / 4.0))


def _contour_curvature_feature(xs: np.ndarray, ys: np.ndarray) -> float:
    if xs.size < 3:
        return 0.0
    cx = float(xs.mean())
    cy = float(ys.mean())
    order = np.argsort(np.arctan2(ys - cy, xs - cx))
    pts = np.stack([xs[order], ys[order]], axis=1).astype(np.float32)
    prev_pts = np.roll(pts, 1, axis=0)
    next_pts = np.roll(pts, -1, axis=0)
    v1 = pts - prev_pts
    v2 = next_pts - pts
    a1 = np.arctan2(v1[:, 1], v1[:, 0])
    a2 = np.arctan2(v2[:, 1], v2[:, 0])
    delta = np.abs((a2 - a1 + math.pi) % (2.0 * math.pi) - math.pi)
    return max(0.0, min(1.0, float(delta.mean() / math.pi)))


def _corner_density_feature(mask: np.ndarray) -> float:
    boundary = _mask_boundary(mask)
    if not boundary.any():
        return 0.0
    padded = np.pad(boundary.astype(np.uint8), 1, mode="constant")
    neighbor_count = sum(
        padded[1 + dy:1 + dy + mask.shape[0], 1 + dx:1 + dx + mask.shape[1]]
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
        if not (dy == 0 and dx == 0)
    )
    sparse_turns = boundary & (neighbor_count <= 2)
    return max(0.0, min(1.0, float(sparse_turns.sum()) / max(float(boundary.sum()), 1.0)))


def _layout_summary(mask: np.ndarray, *, focus_xy: tuple[float, float]) -> np.ndarray:
    h, w = mask.shape
    ys, xs = np.where(mask)
    if xs.size == 0:
        return np.asarray([0.5, 0.5, 0.0, 0.0, 0.0], dtype=np.float32)
    cx = float(xs.mean()) / max(float(w - 1), 1.0)
    cy = float(ys.mean()) / max(float(h - 1), 1.0)
    offset = math.sqrt((cx - 0.5) ** 2 + (cy - 0.5) ** 2)
    area = float(mask.mean())
    focus = 1.0 - min(1.0, math.sqrt((cx - focus_xy[0]) ** 2 + (cy - focus_xy[1]) ** 2))
    return np.asarray([cx, cy, offset, area, focus], dtype=np.float32)


def _foreground_background_kl(rgb: np.ndarray, luma: np.ndarray, mask: np.ndarray) -> np.ndarray:
    bg = ~mask
    rgb_obj = _flat_rgb_hist(rgb[mask])
    rgb_bg = _flat_rgb_hist(rgb[bg])
    hsv = _rgb_to_hsv(rgb)
    hsv_obj = _flat_scalar_hist(hsv[..., 0][mask], _int_constant("vision_sensor.rgb_hist_bins"))
    hsv_bg = _flat_scalar_hist(hsv[..., 0][bg], _int_constant("vision_sensor.rgb_hist_bins"))
    lum_obj = _flat_scalar_hist(luma[mask], _int_constant("vision_sensor.lbp_bins"))
    lum_bg = _flat_scalar_hist(luma[bg], _int_constant("vision_sensor.lbp_bins"))
    return np.asarray([
        _kl(rgb_obj, rgb_bg),
        _kl(hsv_obj, hsv_bg),
        _kl(lum_obj, lum_bg),
    ], dtype=np.float32)


def _best_mask(rgb: np.ndarray, edge: np.ndarray) -> tuple[np.ndarray, float]:
    return solve_subject_mask(rgb, edge)


def solve_subject_mask(rgb: np.ndarray, edge: np.ndarray) -> tuple[np.ndarray, float]:
    lab = _rgb_to_lab(rgb)
    hsv = _rgb_to_hsv(rgb)
    center = _center_prior(rgb.shape[0], rgb.shape[1])
    border = np.concatenate([lab[0, :, :], lab[-1, :, :], lab[:, 0, :], lab[:, -1, :]], axis=0)
    border_mean = border.mean(axis=0)
    color_dist = np.linalg.norm(lab - border_mean, axis=2)
    color_dist = color_dist / max(float(color_dist.max()), float(load_constant("phase19.confidence.denominator_epsilon")))
    saturation = hsv[..., 1]
    value = hsv[..., 2]
    non_white = (saturation >= _float_constant("vision_sensor.mask_saturation_floor")) & (
        value <= _float_constant("vision_sensor.mask_white_value_ceiling")
    )

    score = (
        color_dist * _float_constant("vision_sensor.mask_color_weight")
        + edge * _float_constant("vision_sensor.mask_edge_weight")
        + center * _float_constant("vision_sensor.mask_center_weight")
    )
    candidates = [
        color_dist >= float(np.percentile(color_dist, _int_constant("vision_sensor.mask_color_percentile"))),
        non_white,
        non_white & (saturation >= float(np.percentile(saturation[non_white], _int_constant("vision_sensor.mask_saturation_percentile"))) if non_white.any() else non_white),
        score >= float(np.percentile(score, _int_constant("vision_sensor.mask_edge_percentile"))),
        center >= 0.35,
    ]
    scored: list[tuple[float, np.ndarray]] = []
    for candidate in candidates:
        cleaned = _largest_component(_clean_mask(candidate))
        confidence = _subject_mask_confidence(cleaned, rgb, edge, center, color_dist)
        scored.append((confidence, cleaned))
    confidence, mask = max(scored, key=lambda item: item[0])
    if confidence < _float_constant("vision_sensor.mask_conf_min_use"):
        fallback = _largest_component(_clean_mask(non_white))
        fallback_conf = _subject_mask_confidence(fallback, rgb, edge, center, color_dist)
        if fallback_conf > confidence:
            confidence, mask = fallback_conf, fallback
    return mask.astype(bool), float(max(0.0, min(1.0, confidence)))


def _legacy_best_mask(rgb: np.ndarray, edge: np.ndarray) -> tuple[np.ndarray, float]:
    lab = _rgb_to_lab(rgb)
    border = np.concatenate([lab[0, :, :], lab[-1, :, :], lab[:, 0, :], lab[:, -1, :]], axis=0)
    border_mean = border.mean(axis=0)
    color_dist = np.linalg.norm(lab - border_mean, axis=2)
    color_dist = color_dist / max(float(color_dist.max()), 1e-6)
    center = _center_prior(rgb.shape[0], rgb.shape[1])
    score = color_dist + edge * 0.45 + center * 0.15
    threshold = float(score.mean() + score.std() * 0.15)
    saliency = score >= threshold
    color_cluster = color_dist >= float(color_dist.mean())
    edge_mask = edge >= float(edge.mean() + edge.std() * 0.5)
    center_mask = center >= 0.35
    candidates = (saliency, color_cluster, edge_mask, center_mask)
    scored = [(_mask_confidence(mask, edge), _clean_mask(mask)) for mask in candidates]
    confidence, mask = max(scored, key=lambda item: item[0])
    if mask.mean() <= 0.01:
        mask = center_mask
        confidence = min(confidence, 0.3)
    return mask.astype(bool), float(max(0.0, min(1.0, confidence)))


def _clean_mask(mask: np.ndarray) -> np.ndarray:
    padded = np.pad(mask.astype(np.uint8), 1, mode="constant")
    total = sum(
        padded[1 + dy:1 + dy + mask.shape[0], 1 + dx:1 + dx + mask.shape[1]]
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
    )
    return total >= 5


def _largest_component(mask: np.ndarray) -> np.ndarray:
    if not mask.any():
        return mask.astype(bool)
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    best: list[tuple[int, int]] = []
    ys, xs = np.where(mask)
    for start_y, start_x in zip(ys.tolist(), xs.tolist()):
        if seen[start_y, start_x]:
            continue
        stack = [(start_y, start_x)]
        seen[start_y, start_x] = True
        component: list[tuple[int, int]] = []
        while stack:
            y, x = stack.pop()
            component.append((y, x))
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny = y + dy
                nx = x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(component) > len(best):
            best = component
    out = np.zeros_like(mask, dtype=bool)
    for y, x in best:
        out[y, x] = True
    return out


def _mask_confidence(mask: np.ndarray, edge: np.ndarray) -> float:
    area = float(mask.mean())
    if area <= 0.0:
        return 0.0
    area_score = 1.0 - min(1.0, abs(area - 0.35) / 0.35)
    edge_score = float(edge[mask].mean()) if mask.any() else 0.0
    return max(0.0, min(1.0, 0.6 * area_score + 0.4 * edge_score))


def _subject_mask_confidence(
    mask: np.ndarray,
    rgb: np.ndarray,
    edge: np.ndarray,
    center: np.ndarray,
    color_dist: np.ndarray,
) -> float:
    area = float(mask.mean())
    if area <= 0.0:
        return 0.0
    min_cov = _float_constant("vision_sensor.mask_min_coverage")
    max_cov = _float_constant("vision_sensor.mask_max_coverage")
    if area < min_cov or area > max_cov:
        coverage_score = 0.0
    else:
        coverage_score = 1.0 - min(
            1.0,
            abs(area - _float_constant("vision_sensor.mask_conf_area_target"))
            / max(_float_constant("vision_sensor.mask_conf_area_span"), float(load_constant("phase19.confidence.denominator_epsilon"))),
        )
    edge_score = float(edge[mask].mean()) if mask.any() else 0.0
    center_score = float(center[mask].mean()) if mask.any() else 0.0
    contrast_score = float(color_dist[mask].mean()) if mask.any() else 0.0
    return max(
        0.0,
        min(
            1.0,
            coverage_score * _float_constant("vision_sensor.mask_conf_area_weight")
            + edge_score * _float_constant("vision_sensor.mask_conf_edge_weight")
            + center_score * _float_constant("vision_sensor.mask_conf_center_weight")
            + contrast_score * _float_constant("vision_sensor.mask_conf_contrast_weight"),
        ),
    )


def _regions_s0_s1_s2(height: int, width: int) -> list[np.ndarray]:
    return _regions_s0_s1(height, width) + _grid_regions(height, width, 3)


def _regions_s0_s1_s2_s3(height: int, width: int) -> list[np.ndarray]:
    return _regions_s0_s1_s2(height, width) + _grid_regions(height, width, 5)


def _fast_regions(height: int, width: int) -> list[np.ndarray]:
    return _regions_s0_s1(height, width)


def _regions_s0_s1(height: int, width: int) -> list[np.ndarray]:
    all_region = np.ones((height, width), dtype=bool)
    center = _center_prior(height, width) >= 0.5
    return [all_region, center, ~center]


def _grid_regions(height: int, width: int, grid: int) -> list[np.ndarray]:
    yy, xx = np.indices((height, width))
    rows = np.minimum((yy * grid // max(height, 1)).astype(int), grid - 1)
    cols = np.minimum((xx * grid // max(width, 1)).astype(int), grid - 1)
    return [(rows == row) & (cols == col) for row in range(grid) for col in range(grid)]


def _center_prior(height: int, width: int) -> np.ndarray:
    yy, xx = np.indices((height, width))
    cx = (width - 1) / 2.0
    cy = (height - 1) / 2.0
    dist = np.sqrt(((xx - cx) / max(cx, 1.0)) ** 2 + ((yy - cy) / max(cy, 1.0)) ** 2)
    return np.clip(1.0 - dist, 0.0, 1.0).astype(np.float32)


def _focus_patch(array: np.ndarray, focus_xy: tuple[float, float], size: int) -> np.ndarray:
    h, w = array.shape[:2]
    side = min(h, w, max(8, min(h, w) // 2))
    cx = int(np.clip(focus_xy[0], 0.0, 1.0) * max(w - 1, 1))
    cy = int(np.clip(focus_xy[1], 0.0, 1.0) * max(h - 1, 1))
    x0 = int(np.clip(cx - side // 2, 0, max(w - side, 0)))
    y0 = int(np.clip(cy - side // 2, 0, max(h - side, 0)))
    patch = array[y0:y0 + side, x0:x0 + side]
    if patch.ndim == 2:
        patch = patch[..., None]
    return _resize_float_array(patch, size)


def _native_focus_core(array: np.ndarray, focus_xy: tuple[int, int]) -> np.ndarray:
    h, w = array.shape[:2]
    radius = foveal_radius_px(w, h)
    side = radius * 2
    cx = int(np.clip(focus_xy[0], 0, max(w - 1, 0)))
    cy = int(np.clip(focus_xy[1], 0, max(h - 1, 0)))
    x0 = int(np.clip(cx - radius, 0, max(w - side, 0)))
    y0 = int(np.clip(cy - radius, 0, max(h - side, 0)))
    core = array[y0:y0 + side, x0:x0 + side]
    tile = _int_constant("vision_sensor.v0_layer_tile_px")
    if core.shape[0] == tile and core.shape[1] == tile:
        return core.copy()
    return _resize_box_average(core, tile)


def _quick_mask(rgb: np.ndarray, edge: np.ndarray) -> np.ndarray:
    luma = _luma(rgb)
    center = _center_prior(rgb.shape[0], rgb.shape[1])
    score = np.abs(luma - float(np.median(luma))) + edge * _float_constant("vision_sensor.mask_edge_weight") + center * _float_constant("vision_sensor.mask_center_weight")
    threshold = float(np.percentile(score, _int_constant("vision_sensor.mask_edge_percentile")))
    mask = score >= threshold
    if float(mask.mean()) <= _float_constant("vision_sensor.mask_min_coverage"):
        return center >= _float_constant("vision_sensor.mask_conf_area_target")
    return mask


def _as_rgb_array(image_like: str | Path | Image.Image | np.ndarray, *, max_px: int | None = None) -> np.ndarray:
    if isinstance(image_like, np.ndarray):
        array = image_like.astype(np.float32, copy=False)
        if array.max(initial=0.0) > 1.0:
            array = array / 255.0
        if array.ndim == 2:
            array = np.repeat(array[..., None], 3, axis=2)
        if array.shape[2] == 4:
            array = array[..., :3]
        return np.clip(array, 0.0, 1.0)
    if isinstance(image_like, Image.Image):
        image = image_like if image_like.mode == "RGB" else image_like.convert("RGB")
    else:
        image = Image.open(Path(image_like)).convert("RGB")
    bounded_px = int(max_px or _int_constant("vision_sensor.audit_resize_px"))
    if max_px is not None:
        image = image.resize((bounded_px, bounded_px), Image.Resampling.BILINEAR)
    else:
        image.thumbnail((bounded_px, bounded_px), Image.Resampling.BILINEAR)
    return np.asarray(image, dtype=np.float32) / 255.0


def _as_native_rgb_array(image_like: str | Path | Image.Image | np.ndarray) -> np.ndarray:
    if isinstance(image_like, np.ndarray):
        array = image_like.astype(np.float32, copy=False)
        if array.max(initial=0.0) > 1.0:
            array = array / 255.0
        if array.ndim == 2:
            array = np.repeat(array[..., None], 3, axis=2)
        if array.shape[2] == 4:
            array = array[..., :3]
        return np.clip(array, 0.0, 1.0)
    if isinstance(image_like, Image.Image):
        image = image_like if image_like.mode == "RGB" else image_like.convert("RGB")
    else:
        image = Image.open(Path(image_like)).convert("RGB")
    return np.asarray(image, dtype=np.float32) / 255.0


def _native_default_focus(rgb: np.ndarray) -> tuple[int, int]:
    return (int((rgb.shape[1] - 1) * 0.5), int((rgb.shape[0] - 1) * 0.5))


def _clip_bbox(bbox: tuple[int, int, int, int], *, width: int, height: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = (int(value) for value in bbox)
    x1 = int(np.clip(x1, 0, max(width - 1, 0)))
    y1 = int(np.clip(y1, 0, max(height - 1, 0)))
    x2 = int(np.clip(x2, x1 + 1, width))
    y2 = int(np.clip(y2, y1 + 1, height))
    return x1, y1, x2, y2


def _resize_float_rgb(rgb: np.ndarray, size: int) -> np.ndarray:
    return _resize_float_array(rgb, size)


def _resize_float_gray(gray: np.ndarray, size: int) -> np.ndarray:
    return _resize_float_array(gray[..., None], size)[..., 0]


def _resize_float_array(array: np.ndarray, size: int) -> np.ndarray:
    scaled = np.uint8(np.clip(array, 0.0, 1.0) * 255.0)
    if scaled.ndim == 2:
        mode = "L"
    elif scaled.shape[2] == 1:
        scaled = scaled[..., 0]
        mode = "L"
    else:
        mode = "RGB"
    image = Image.fromarray(scaled, mode=mode).resize((size, size), Image.Resampling.BILINEAR)
    out = np.asarray(image, dtype=np.float32) / 255.0
    if array.ndim == 3 and array.shape[2] == 1:
        out = out[..., None]
    return out


def _resize_box_average(array: np.ndarray, size: int) -> np.ndarray:
    scaled = np.uint8(np.clip(array, 0.0, 1.0) * 255.0)
    if scaled.ndim == 2:
        mode = "L"
    elif scaled.shape[2] == 1:
        scaled = scaled[..., 0]
        mode = "L"
    else:
        mode = "RGB"
    image = Image.fromarray(scaled, mode=mode).resize((int(size), int(size)), Image.Resampling.BOX)
    out = np.asarray(image, dtype=np.float32) / 255.0
    if array.ndim == 3 and array.shape[2] == 1:
        out = out[..., None]
    return out


def _box_average_half(array: np.ndarray) -> np.ndarray:
    h, w = array.shape[:2]
    h2 = max(h // 2, 1)
    w2 = max(w // 2, 1)
    trimmed = array[:h2 * 2, :w2 * 2]
    if trimmed.shape[0] < 2 or trimmed.shape[1] < 2:
        return array.copy()
    if array.ndim == 2:
        return trimmed.reshape(h2, 2, w2, 2).mean(axis=(1, 3)).astype(np.float32)
    return trimmed.reshape(h2, 2, w2, 2, array.shape[2]).mean(axis=(1, 3)).astype(np.float32)


def _luma(rgb: np.ndarray) -> np.ndarray:
    return (rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114).astype(np.float32)


def _sobel_magnitude(gray: np.ndarray) -> np.ndarray:
    padded = np.pad(gray, 1, mode="edge")
    gx = (
        -padded[:-2, :-2] - 2.0 * padded[1:-1, :-2] - padded[2:, :-2]
        + padded[:-2, 2:] + 2.0 * padded[1:-1, 2:] + padded[2:, 2:]
    )
    gy = (
        -padded[:-2, :-2] - 2.0 * padded[:-2, 1:-1] - padded[:-2, 2:]
        + padded[2:, :-2] + 2.0 * padded[2:, 1:-1] + padded[2:, 2:]
    )
    mag = np.sqrt(gx * gx + gy * gy)
    return (mag / max(float(mag.max()), 1e-6)).astype(np.float32)


def _sobel_orientation(gray: np.ndarray) -> np.ndarray:
    padded = np.pad(gray, 1, mode="edge")
    gx = (
        -padded[:-2, :-2] - 2.0 * padded[1:-1, :-2] - padded[2:, :-2]
        + padded[:-2, 2:] + 2.0 * padded[1:-1, 2:] + padded[2:, 2:]
    )
    gy = (
        -padded[:-2, :-2] - 2.0 * padded[:-2, 1:-1] - padded[:-2, 2:]
        + padded[2:, :-2] + 2.0 * padded[2:, 1:-1] + padded[2:, 2:]
    )
    return np.arctan2(gy, gx).astype(np.float32)


def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    matrix = np.asarray(
        [[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]],
        dtype=np.float32,
    )
    xyz = linear @ matrix.T
    white = np.asarray([0.95047, 1.0, 1.08883], dtype=np.float32)
    ratio = xyz / white
    delta = 6.0 / 29.0
    f = np.where(ratio > delta ** 3, np.cbrt(ratio), ratio / (3.0 * delta ** 2) + 4.0 / 29.0)
    lab = np.empty_like(f, dtype=np.float32)
    lab[..., 0] = (116.0 * f[..., 1] - 16.0) / 100.0
    lab[..., 1] = (500.0 * (f[..., 0] - f[..., 1]) + 128.0) / 255.0
    lab[..., 2] = (200.0 * (f[..., 1] - f[..., 2]) + 128.0) / 255.0
    return np.clip(lab, 0.0, 1.0)


def _rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    maxc = np.max(rgb, axis=-1)
    minc = np.min(rgb, axis=-1)
    delta = maxc - minc
    hue = np.zeros_like(maxc)
    mask = delta > 1e-6
    rmask = mask & (maxc == r)
    gmask = mask & (maxc == g)
    bmask = mask & (maxc == b)
    hue[rmask] = ((g[rmask] - b[rmask]) / delta[rmask]) % 6.0
    hue[gmask] = ((b[gmask] - r[gmask]) / delta[gmask]) + 2.0
    hue[bmask] = ((r[bmask] - g[bmask]) / delta[bmask]) + 4.0
    hue = hue / 6.0
    sat = np.divide(delta, maxc, out=np.zeros_like(delta), where=maxc > 1e-6)
    return np.stack([hue, sat, maxc], axis=-1).astype(np.float32)


def _lbp_codes(gray: np.ndarray, radius: int) -> np.ndarray:
    padded = np.pad(gray, radius, mode="edge")
    center = padded[radius:-radius, radius:-radius]
    offsets = (
        (-radius, -radius), (-radius, 0), (-radius, radius), (0, radius),
        (radius, radius), (radius, 0), (radius, -radius), (0, -radius),
    )
    code = np.zeros_like(center, dtype=np.uint8)
    for bit, (dy, dx) in enumerate(offsets):
        neigh = padded[radius + dy: radius + dy + gray.shape[0], radius + dx: radius + dx + gray.shape[1]]
        code |= ((neigh >= center).astype(np.uint8) << bit)
    return code


def _mask_perimeter(mask: np.ndarray) -> int:
    padded = np.pad(mask.astype(np.uint8), 1, mode="constant")
    center = padded[1:-1, 1:-1]
    neighbours = (
        padded[:-2, 1:-1] + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]
    )
    boundary = (center == 1) & (neighbours < 4)
    return int(boundary.sum())


def _flat_rgb_hist(pixels: np.ndarray) -> np.ndarray:
    if pixels.size == 0:
        return np.ones(_int_constant("vision_sensor.rgb_hist_bins") * 3, dtype=np.float32)
    bins = _int_constant("vision_sensor.rgb_hist_bins")
    hist = np.concatenate([
        np.histogram(pixels[:, channel], bins=bins, range=(0.0, 1.0), density=False)[0].astype(np.float32)
        for channel in range(3)
    ])
    return hist / max(float(hist.sum()), 1.0)


def _flat_scalar_hist(values: np.ndarray, bins: int) -> np.ndarray:
    if values.size == 0:
        return np.ones(bins, dtype=np.float32) / float(bins)
    hist = np.histogram(values.reshape(-1), bins=bins, range=(0.0, 1.0), density=False)[0].astype(np.float32)
    return hist / max(float(hist.sum()), 1.0)


def _kl(left: np.ndarray, right: np.ndarray) -> float:
    eps = 1e-6
    return float(np.sum((left + eps) * np.log((left + eps) / (right + eps))))


def _hash_float_array(array: np.ndarray) -> str:
    clean = np.nan_to_num(np.asarray(array, dtype=np.float32), copy=False)
    return hashlib.sha256(clean.tobytes()).hexdigest()


def _as_float_tuple(values: Iterable[float] | np.ndarray) -> tuple[float, ...]:
    arr = np.asarray(values, dtype=np.float32).reshape(-1)
    return tuple(float(v) for v in arr)


def _default_focus() -> tuple[float, float]:
    return (
        _float_constant("vision_sensor.default_focus_x"),
        _float_constant("vision_sensor.default_focus_y"),
    )


def _int_constant(path: str) -> int:
    return int(load_constant(path))


def _float_constant(path: str) -> float:
    return float(load_constant(path))
