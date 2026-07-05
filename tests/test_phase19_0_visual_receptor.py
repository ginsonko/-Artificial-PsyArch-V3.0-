from __future__ import annotations

import math
import subprocess
import sys
from statistics import median
from pathlib import Path

import pytest
from PIL import Image

from apv3test.runtime.visual_receptor import (
    AuditPathQueue,
    CooccurrenceMatrix,
    RetrievalWeights,
    assert_retrieval_alpha_weights,
    extract_visual_audit_path,
    extract_visual_fast_path,
    make_inner_picture_state,
    normalized_recall_score,
    prepare_visual_fast_frame,
    render_prototype_imagination,
    render_sensory_sketch,
    sample_audit_images,
)
from runtime.cognitive.state_pool.state_pool import load_constant


SHOWCASE = Path("reports/APV3_Phase19_0_VisualReceptorSketch_Showcase_20260619.html")


def test_phase19_0_audit_feature_vector_is_dimensionally_closed_and_finite() -> None:
    path = sample_audit_images(1)[0]
    trace = extract_visual_audit_path(path, tick=19)

    assert len(trace.feature_vector) == int(load_constant("vision_sensor.feature_vector_dim")) == 8654
    assert trace.channel_lengths == {
        "V0": 4544,
        "V1": 288,
        "V2": 1536,
        "V3": 1110,
        "V4": 296,
        "V5": 16,
        "V6": 40,
        "V7": 320,
        "V8": 5,
        "V9": 3,
        "V10": 384,
        "V11": 64,
        "V12": 48,
    }
    assert all(math.isfinite(value) for value in trace.feature_vector)
    assert trace.metadata["evaluator_label_accessed"] is False
    assert trace.metadata["pathway"] == "reconstruction_audit_path"


def test_phase19_0_fast_path_uses_prepared_tick_frames_and_stays_under_5ms() -> None:
    paths = sample_audit_images(12)
    assert len(paths) >= 12
    frames = [prepare_visual_fast_frame(Image.open(path).convert("RGB")) for path in paths[:12]]

    extract_visual_fast_path(frames[0], tick=0)
    latencies = [
        median(extract_visual_fast_path(frame, tick=index).elapsed_ms for _ in range(3))
        for index, frame in enumerate(frames, start=1)
    ]
    p95 = sorted(latencies)[math.ceil(len(latencies) * 0.95) - 1]

    assert len(extract_visual_fast_path(frames[0]).compact_vector) == 277
    assert p95 < float(load_constant("vision_sensor.fast_path_p95_ms")), latencies


def test_phase19_0_render_modes_and_inner_picture_metadata_are_source_separated(tmp_path: Path) -> None:
    trace = extract_visual_audit_path(sample_audit_images(1)[0], tick=3)
    sensory = render_sensory_sketch(trace, out_dir=tmp_path)
    proto = render_prototype_imagination(trace, out_dir=tmp_path)
    sensory_state = make_inner_picture_state(trace, sensory, tick=3)
    proto_state = make_inner_picture_state(trace, proto, tick=3)

    assert sensory.path.read_bytes().startswith(b"\x89PNG")
    assert proto.path.read_bytes().startswith(b"\x89PNG")
    assert sensory.metadata["render_mode"] == "sensory_sketch"
    assert sensory.metadata["prototype_trace_hash"] is None
    assert sensory.metadata["epistemic_source"] == "PERCEIVED_SENSORY_SKETCH"
    assert proto.metadata["render_mode"] == "prototype_imagination"
    assert proto.metadata["prototype_trace_hash"]
    assert proto.metadata["epistemic_source"] == "IMAGINED_PROTOTYPE_SKETCH"
    assert sensory.metadata["evaluator_label_accessed"] is False
    assert proto.metadata["evaluator_label_accessed"] is False
    assert isinstance(sensory.metadata["confidence_score"], float)
    assert isinstance(sensory.metadata["decision_tier"], str)
    assert sensory.metadata["decision_tier"] == "no_call"
    assert sensory_state.sa_id != proto_state.sa_id
    assert sensory_state.channel_signature == ("vision", "sensory", "sketch")
    assert proto_state.channel_signature == ("vision", "imagined", "sketch")

    forbidden = ("真实", "苹果", "香蕉", "橙子", "orange", "banana", "apple")
    joined = " ".join([
        sensory_state.sa_id,
        proto_state.sa_id,
        sensory_state.metadata["rendered_png_path"],
        proto_state.metadata["rendered_png_path"],
    ]).lower()
    assert not any(token.lower() in joined for token in forbidden)


def test_phase19_0_cooccurrence_source_lock_and_retrieval_alpha_assertions() -> None:
    matrix = CooccurrenceMatrix()
    matrix.update("sa_a", "sa_b", 0.4, tick=1, source_tag="training_sdpl_only")

    assert matrix.matrix[("sa_a", "sa_b")] == 0.4
    with pytest.raises(ValueError):
        matrix.update("sa_a", "sa_c", 0.2, tick=2, source_tag="evaluator_sidecar")

    assert_retrieval_alpha_weights()
    with pytest.raises(ValueError):
        assert_retrieval_alpha_weights(RetrievalWeights(0.5, 0.4, 0.2, 0.1))
    with pytest.raises(ValueError):
        assert_retrieval_alpha_weights(RetrievalWeights(0.2, 0.2, 0.1, 0.7))
    assert 0.0 <= normalized_recall_score(-10.0) <= normalized_recall_score(10.0) <= 1.0


def test_phase19_0_audit_queue_degrades_without_blocking_fast_path() -> None:
    paths = sample_audit_images(3)
    traces = [extract_visual_audit_path(path, tick=index) for index, path in enumerate(paths, start=1)]
    queue = AuditPathQueue(max_concurrent=2, drop_oldest=True)

    assert queue.submit(traces[0]) is True
    assert queue.submit(traces[1]) is True
    assert queue.submit(traces[2]) is True
    assert len(queue) == 2
    assert queue.dropped_count == 1

    frame = prepare_visual_fast_frame(Image.open(paths[0]).convert("RGB"))
    fast = extract_visual_fast_path(frame, tick=99)
    assert fast.metadata["pathway"] == "receptor_fast_path"
    assert len(fast.compact_vector) == 277


def test_phase19_0_visual_receptor_keeps_external_ml_models_out() -> None:
    source = Path("apv3test/runtime/visual_receptor.py").read_text(encoding="utf-8")
    forbidden = ("import cv2", "import torch", "import tensorflow", "import sklearn", "import librosa")

    assert not any(token in source for token in forbidden)
    assert "training_sdpl_only" in source
    assert "evaluator_label_accessed" in source


def test_phase19_0_showcase_is_readable_and_does_not_overclaim() -> None:
    text = SHOWCASE.read_text(encoding="utf-8")

    assert "APV3 Phase 19.0：视觉感受器和内心草图" in text
    assert "8654" in text
    assert "sensory_sketch" in text
    assert "prototype_imagination" in text
    assert "不证明 AP 已经会识别真实照片" in text
    assert "fast path" in text
    assert "???" not in text


def test_phase19_0_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "19.0"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
