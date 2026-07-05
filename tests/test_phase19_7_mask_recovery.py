from __future__ import annotations

import inspect
from pathlib import Path

from apv3test.runtime import visual_receptor
from apv3test.runtime.visual_receptor import (
    _as_native_rgb_array,
    _luma,
    _shape_geometry,
    _sobel_magnitude,
    solve_subject_mask,
)
import runtime.cognitive.percept_vector.phase19_runtime as phase19_runtime
from runtime.cognitive.percept_vector.phase19_runtime import (
    VisualTeachingExample,
    visual_recognize_v1_7,
)


def _mask_shape(path: Path) -> tuple[float, float, float]:
    rgb = _as_native_rgb_array(path)
    mask, confidence = solve_subject_mask(rgb, _sobel_magnitude(_luma(rgb)))
    shape = _shape_geometry(mask)
    return float(shape[0]), float(shape[2]), float(confidence)


def _clean_path(name: str) -> Path:
    return Path("config/curriculum/assets/visual/clean_cards") / name


def _clean_training_examples() -> tuple[VisualTeachingExample, ...]:
    root = Path("config/curriculum/assets/visual/clean_cards")
    examples: list[VisualTeachingExample] = []
    tick = 1
    for label in ("apple", "banana", "orange"):
        for index in range(3):
            examples.append(VisualTeachingExample(root / f"noun_{label}_train_{index}.png", label, "clean_train", tick))
            tick += 1
    return tuple(examples)


def test_phase19_7_subject_mask_keeps_banana_shape_diagnostic() -> None:
    apple_aspect, apple_circularity, apple_conf = _mask_shape(_clean_path("noun_apple_train_0.png"))
    banana_aspect, banana_circularity, banana_conf = _mask_shape(_clean_path("noun_banana_train_0.png"))
    orange_aspect, orange_circularity, orange_conf = _mask_shape(_clean_path("noun_orange_train_0.png"))

    assert banana_aspect < apple_aspect
    assert banana_aspect < orange_aspect
    assert banana_circularity < apple_circularity
    assert banana_circularity < orange_circularity
    assert min(apple_conf, banana_conf, orange_conf) >= 0.40


def test_phase19_7_quick_mask_no_longer_uses_mean_threshold_formula() -> None:
    source = inspect.getsource(visual_receptor._quick_mask)

    assert "score.mean" not in source
    assert "np.percentile" in source


def test_phase19_7_diagnostic_recognizer_does_not_call_full_vector_cosine() -> None:
    source = inspect.getsource(phase19_runtime.visual_recognize_v1_7)

    assert "cosine_similarity" not in source
    assert "C_RECALL_PARTS" in source
    assert "CHANNEL_NOISY_OR" in source


def test_phase19_7_wrong_real_photo_calls_are_not_firm() -> None:
    query_root = Path("真实图片测试资产")
    truth_paths = (
        ("apple", query_root / "真实苹果1.jpeg"),
        ("apple", query_root / "真实苹果2.jpg"),
        ("apple", query_root / "真实苹果3.jpeg"),
        ("banana", query_root / "真实香蕉1.webp"),
        ("banana", query_root / "真实香蕉2.webp"),
        ("banana", query_root / "真实香蕉3.webp"),
        ("banana", query_root / "真实香蕉4.webp"),
        ("orange", query_root / "真实橙子1.webp"),
        ("orange", query_root / "真实橙子2.webp"),
        ("orange", query_root / "真实橙子3.jpeg"),
        ("orange", query_root / "绿色橙子1.webp"),
        ("apple", query_root / "黄绿色苹果1.jpg"),
    )

    for tick, (truth, path) in enumerate(truth_paths, start=100):
        result = visual_recognize_v1_7(path, teaching_examples=_clean_training_examples(), tick=tick)
        if result.top_visible_label != truth:
            assert result.decision_tier != "firm"
        assert result.used_filename_label is False
