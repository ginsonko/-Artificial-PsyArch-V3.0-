from __future__ import annotations

from pathlib import Path

import numpy as np

from apv3test.runtime.visual_receptor import extract_visual_audit_path_v2
from runtime.cognitive.percept_vector.phase19_runtime import _channel_similarity
from runtime.cognitive.state_pool.state_pool import load_constant


def test_phase19_7h_visual_trace_has_local_diagnostic_channels() -> None:
    trace = extract_visual_audit_path_v2(Path("config/curriculum/assets/visual/clean_cards/noun_apple_train_0.png"))

    assert len(trace.feature_vector) == int(load_constant("phase19.vector.visual_receptor_feature_dim")) == 28686
    assert trace.channel_lengths["V6"] == 40
    assert trace.channel_lengths["V7"] == 320
    assert trace.channel_lengths["V10"] == 384
    assert trace.channel_lengths["V11"] == 64
    assert trace.channel_lengths["V12"] == 48


def test_phase19_7h_global_statistics_are_audit_only_in_recognition_weights() -> None:
    weights = dict(load_constant("phase19.recognition.channel_weights"))

    for channel in ("V1", "V2", "V3", "V4", "V8", "V9"):
        assert weights[channel] == 0.0
    for channel in ("V7", "V10", "V11", "V12"):
        assert weights[channel] > 0.0


def test_phase19_7h_sparse_part_similarity_does_not_reward_shared_absence() -> None:
    left = np.zeros(int(load_constant("vision_sensor.part_top_k")) * int(load_constant("vision_sensor.part_profile_features")), dtype=np.float32)
    right = left.copy()
    width = int(load_constant("vision_sensor.part_profile_features"))
    left[0:width] = np.asarray([0.1, 0.8, 0.9, 0.6, 0.2, 0.5], dtype=np.float32)
    right[width:width * 2] = np.asarray([0.9, 0.8, 0.9, 0.6, 0.2, 0.5], dtype=np.float32)

    assert _channel_similarity("V10", left, right) < 0.95
