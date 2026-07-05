from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from apv3test.runtime.visual_receptor import extract_visual_audit_path_v2_object_centric
from runtime.cognitive.percept_vector import object_looking
from runtime.cognitive.percept_vector.object_looking import (
    build_object_centric_training_traces,
    count_objects,
    enumerate_objects_in_image,
    extract_candidate_targets,
)
from runtime.cognitive.percept_vector.phase19_runtime import visual_recognize_v1_7
from runtime.cognitive.state_pool.state_pool import load_constant
from scripts.reports.render_phase21_object_looking_showcase import (
    REPORT,
    _generate_probe_assets,
    _generate_training_assets,
    main as render_showcase,
)


def test_phase21_candidates_are_class_agnostic_and_not_filename_oracles() -> None:
    training = _generate_training_assets()
    candidates = extract_candidate_targets(training[0].path)
    assert candidates
    forbidden = {"apple", "banana", "orange", training[0].path.name}
    metadata_text = repr(candidates[0].metadata)
    assert not any(token in metadata_text for token in forbidden)
    assert candidates[0].metadata["label_accessed"] is False
    assert candidates[0].metadata["filename_accessed"] is False


def test_phase21_object_centric_channels_change_between_candidate_regions() -> None:
    _generate_training_assets()
    probe = _generate_probe_assets()[0]
    candidates = extract_candidate_targets(probe)
    assert len(candidates) >= 2
    left = extract_visual_audit_path_v2_object_centric(probe, candidate_bbox=candidates[0].bbox)
    right = extract_visual_audit_path_v2_object_centric(probe, candidate_bbox=candidates[1].bbox)
    diffs = []
    for channel in ("V7", "V10", "V11", "V12"):
        start, end = left.channel_slices[channel]
        a = np.asarray(left.feature_vector[start:end], dtype=np.float32)
        b = np.asarray(right.feature_vector[start:end], dtype=np.float32)
        diffs.append(float(np.mean(np.abs(a - b))))
    assert max(diffs) > float(load_constant("phase21.object_looking.object_channel_difference_floor"))


def test_phase21_v1b_v10_v11_v12_are_truly_local_to_candidate_bbox(tmp_path: Path) -> None:
    image_path = tmp_path / "phase21_v1b_locality_probe.png"
    _write_three_region_locality_probe(image_path)
    boxes = (
        (0, 0, 128, 128),
        (128, 128, 256, 256),
        (80, 80, 176, 176),
    )
    traces = tuple(
        extract_visual_audit_path_v2_object_centric(image_path, candidate_bbox=bbox)
        for bbox in boxes
    )
    assert len({trace.metadata["local_source_image_hash"] for trace in traces}) == len(traces)
    assert len({trace.source_image_hash for trace in traces}) == 1

    floor = float(load_constant("phase21.object_looking.object_channel_difference_floor"))
    for channel in ("V10", "V11", "V12"):
        assert _min_pairwise_channel_mean_abs(traces, channel) > floor, channel
    assert _min_pairwise_channel_l1(traces, "V7") > floor


def test_phase21_enumerates_multiple_objects_and_counts_object_files() -> None:
    training = _generate_training_assets()
    traces = build_object_centric_training_traces(training)
    probe = _generate_probe_assets()[0]
    result = enumerate_objects_in_image(probe, teaching_examples=training, concept_traces=traces)
    assert result.metadata["object_centric"] is True
    assert result.candidate_count >= 2
    assert count_objects(result) >= 2
    labels = {item.recognition.top_visible_label for item in result.objects}
    assert len(labels & {"apple", "banana", "orange"}) >= 2
    assert all(item.recognition.used_filename_label is False for item in result.objects)


def test_phase21_object_focus_improves_margin_over_whole_image_on_generated_probe() -> None:
    training = _generate_training_assets()
    traces = build_object_centric_training_traces(training)
    probe = _generate_probe_assets()[2]
    full = visual_recognize_v1_7(probe, teaching_examples=training)
    result = enumerate_objects_in_image(probe, teaching_examples=training, concept_traces=traces)
    best_object_margin = max(item.recognition.nearest_negative_margin for item in result.objects)
    assert best_object_margin > full.nearest_negative_margin + float(
        load_constant("phase21.object_looking.margin_improvement_floor")
    )


def test_phase21_runtime_redlines_prevent_prose_fixation_and_hidden_routes() -> None:
    source = inspect.getsource(object_looking.enumerate_objects_in_image)
    assert "propose_visual_focus_actions" in source
    assert "_diagnostic_fixation_log" not in source
    assert "extract_visual_audit_path_v2_object_centric" in inspect.getsource(object_looking.recognize_at_focus)
    assert "apple" not in inspect.getsource(object_looking.extract_candidate_targets)
    assert "banana" not in inspect.getsource(object_looking.extract_candidate_targets)
    assert "orange" not in inspect.getsource(object_looking.extract_candidate_targets)


def test_phase21_showcase_and_report_are_public_readable() -> None:
    render_showcase()
    text = REPORT.read_text(encoding="utf-8")
    assert "APV3 Phase 21：对象中心扫视识别" in text
    assert "逐图输出" in text
    assert "它仍不宣称真实世界照片识别完成" in text


def test_phase21_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "21.0"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 21.0 deliverables present" in completed.stdout


def test_phase21_v1b_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "21.v1b"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 21.v1b deliverables present" in completed.stdout


def _write_three_region_locality_probe(path: Path) -> None:
    image = Image.new("RGB", (256, 256), (245, 245, 245))
    draw = ImageDraw.Draw(image)
    for y in range(16, 112, 8):
        for x in range(16, 112, 8):
            color = (220, 20, 40) if ((x + y) // 8) % 2 == 0 else (255, 160, 170)
            draw.rectangle((x, y, x + 7, y + 7), fill=color)
    for index, x in enumerate(range(144, 240, 6)):
        color = (20, 170, 70) if index % 2 == 0 else (160, 240, 170)
        draw.rectangle((x, 144, x + 5, 240), fill=color)
    for radius, color in (
        (46, (40, 90, 230)),
        (30, (130, 180, 255)),
        (14, (30, 40, 120)),
    ):
        draw.ellipse((128 - radius, 128 - radius, 128 + radius, 128 + radius), fill=color)
    image.save(path)


def _min_pairwise_channel_mean_abs(traces: tuple[object, ...], channel: str) -> float:
    values = []
    for left_index, left in enumerate(traces):
        for right in traces[left_index + 1:]:
            start, end = left.channel_slices[channel]
            a = np.asarray(left.feature_vector[start:end], dtype=np.float32)
            b = np.asarray(right.feature_vector[start:end], dtype=np.float32)
            values.append(float(np.mean(np.abs(a - b))))
    return min(values)


def _min_pairwise_channel_l1(traces: tuple[object, ...], channel: str) -> float:
    values = []
    for left_index, left in enumerate(traces):
        for right in traces[left_index + 1:]:
            start, end = left.channel_slices[channel]
            a = np.asarray(left.feature_vector[start:end], dtype=np.float32)
            b = np.asarray(right.feature_vector[start:end], dtype=np.float32)
            values.append(float(np.sum(np.abs(a - b))))
    return min(values)
