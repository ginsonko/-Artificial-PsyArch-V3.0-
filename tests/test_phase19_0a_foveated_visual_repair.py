from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from apv3test.runtime.visual_receptor import (
    SensoryCanvas,
    build_foveated_pyramid,
    canvas_similarity,
    clarity_field,
    extract_visual_audit_path_v2,
    foveal_radius_px,
    render_prediction_overlay_stub,
    render_remembered_overlay_stub,
    render_sensory_canvas_sketch,
    sample_audit_images,
)
from runtime.cognitive.state_pool.state_pool import load_constant


SHOWCASE = Path("reports/APV3_Phase19_0a_FoveatedVisualRepair_Showcase_20260619.html")


def _gradient_image(size: int = 64) -> np.ndarray:
    yy, xx = np.indices((size, size))
    rgb = np.stack([
        xx / float(size - 1),
        yy / float(size - 1),
        ((xx + yy) % size) / float(size - 1),
    ], axis=-1)
    return rgb.astype(np.float32)


def test_phase19_0a_focus_core_is_native_crop_not_resized() -> None:
    image = _gradient_image()
    focus = (32, 32)

    layers = build_foveated_pyramid(image, focus_xy=focus)

    assert len(layers) == int(load_constant("vision_sensor.foveal_layer_count")) == 6
    assert layers[0].downsample == 1
    assert layers[0].pixels.shape == (32, 32, 3)
    np.testing.assert_allclose(layers[0].pixels, image[16:48, 16:48], atol=1e-6)


def test_phase19_0a_foveal_radius_scales_with_viewport() -> None:
    assert foveal_radius_px(64, 64) == int(load_constant("vision_sensor.foveal_radius_min_px"))
    assert foveal_radius_px(1024, 1024) > int(load_constant("vision_sensor.foveal_radius_min_px"))


def test_phase19_0a_v2_feature_vector_is_dimensionally_closed_and_versioned() -> None:
    path = sample_audit_images(1)[0]
    trace = extract_visual_audit_path_v2(path, tick=190)

    assert len(trace.feature_vector) == int(load_constant("phase19.vector.visual_receptor_feature_dim")) == 28686
    assert trace.channel_lengths["V0"] == int(load_constant("vision_sensor.v0_foveated_dim"))
    assert trace.channel_lengths["V6"] == 40
    assert trace.channel_lengths["V7"] == 320
    assert trace.channel_lengths["V10"] == 384
    assert trace.channel_lengths["V11"] == 64
    assert trace.channel_lengths["V12"] == 48
    assert trace.metadata["receptor_version"] == "phase19_0a_foveated"
    assert trace.metadata["patch_native_resolution"] is True
    assert trace.metadata["evaluator_label_accessed"] is False


def test_phase19_0a_clarity_field_has_single_floor_and_focus_peak() -> None:
    phi = clarity_field((128, 128), (64, 64))

    assert 0.99 <= float(phi[64, 64]) <= 1.0
    assert abs(float(phi[0, 0]) - float(load_constant("vision_sensor.clarity_floor"))) < 0.02
    assert float(phi[64, 64]) > float(phi[64, 90]) > float(phi[0, 0])


def test_phase19_0a_canvas_accumulates_coverage_and_similarity_over_fixations() -> None:
    image = _gradient_image(128)
    canvas = SensoryCanvas.from_native_image(image, tick=0)
    start_similarity = canvas_similarity(image, canvas)
    start_coverage = canvas.clarity_coverage()
    fixations = ((32, 32), (96, 32), (32, 96), (96, 96), (64, 64))

    for tick, focus in enumerate(fixations, start=1):
        canvas.update_from_native_image(image, focus_xy=focus, tick=tick)

    normalized_gain = (canvas_similarity(image, canvas) - start_similarity) / max(1.0 - start_similarity, 1e-6)
    coverage_gain = canvas.clarity_coverage() - start_coverage

    assert normalized_gain >= float(load_constant("vision_sensor.mult_tick_normalized_gain_min"))
    assert coverage_gain >= float(load_constant("vision_sensor.mult_tick_coverage_gain_min"))
    assert canvas.to_state_item().metadata["patch_native_resolution"] is True


def test_phase19_0a_overlay_families_are_source_separated(tmp_path: Path) -> None:
    image = _gradient_image(96)
    canvas = SensoryCanvas.from_native_image(image, tick=0)
    canvas.update_from_native_image(image, focus_xy=(48, 48), tick=1)

    sensory = render_sensory_canvas_sketch(canvas, out_dir=tmp_path, stem="sensory")
    remembered = render_remembered_overlay_stub(out_dir=tmp_path, stem="remembered")
    predicted = render_prediction_overlay_stub(out_dir=tmp_path, stem="predicted")

    assert sensory.metadata["epistemic_source"] == "PERCEIVED_SENSORY_SKETCH"
    assert remembered.metadata["epistemic_source"] == "REMEMBERED_SKETCH"
    assert predicted.metadata["epistemic_source"] == "INFERRED_SKETCH"
    assert sensory.metadata["render_mode"] == "sensory_sketch"
    assert remembered.metadata["schema_only"] is True
    assert predicted.metadata["schema_only"] is True


def test_phase19_0a_no_layer_recall_inside_r_sketch_source() -> None:
    source = Path("apv3test/runtime/visual_receptor.py").read_text(encoding="utf-8")
    start = source.index("def render_sensory_canvas_sketch")
    end = source.index("def render_remembered_overlay_stub")
    body = source[start:end]

    assert "layer1_b_recall" not in body
    assert "layer3_lookup" not in body


def test_phase19_0a_showcase_and_report_boundaries() -> None:
    report = Path("docs/FinalReport_Phase19_0a_FoveatedVisualRepair_20260619.md").read_text(encoding="utf-8")
    page = SHOWCASE.read_text(encoding="utf-8")

    assert "foveated visual repair" in report
    assert "does not prove object recognition" in report
    assert "原图" in page
    assert "单 tick" in page
    assert "5 tick" in page
    assert "不证明真实照片识别" in page


def test_phase19_0a_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "19.0a"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 19.0a deliverables present" in completed.stdout
