from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from PIL import Image, ImageDraw

from apv3test.runtime.phase20_7 import MediaInput, TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.vision import (
    SensoryCanvas,
    _next_idle_focus_from_canvas,
)


def _make_two_region_image(path: Path) -> Path:
    """A 72x72 image with a salient region (bright red, edges) and a plainer region (dim)."""
    image = Image.new("RGB", (72, 72), (8, 8, 8))
    draw = ImageDraw.Draw(image)
    draw.rectangle((4, 4, 24, 24), fill=(240, 30, 30))
    draw.rectangle((48, 48, 68, 68), fill=(45, 45, 45))
    image.save(path)
    return path


def _canvas_with_confidence_map(
    width: int = 72,
    height: int = 72,
    *,
    confidence_map: np.ndarray,
    clarity_map: np.ndarray | None = None,
    pixels_map: np.ndarray | None = None,
    last_fixation_xy: tuple[int, int] = (36, 36),
    tick: int = 5,
) -> SensoryCanvas:
    """构造一个带指定 confidence 分布的 canvas, 用于单元测试焦点选择."""
    if clarity_map is None:
        clarity_map = np.ones((height, width), dtype=np.float32) * 0.6
    if pixels_map is None:
        pixels_map = np.zeros((height, width, 3), dtype=np.float32)
        pixels_map[:height // 2, :width // 2] = (0.95, 0.1, 0.1)  # salient red
    return SensoryCanvas(
        canvas_pixels=pixels_map,
        canvas_clarity=clarity_map.astype(np.float32),
        canvas_confidence=confidence_map.astype(np.float32),
        canvas_freshness=np.ones((height, width), dtype=np.float32),
        last_fixation_xy=last_fixation_xy,
        tick=tick,
        source_image_hash="test",
        first_tick=0,
    )


def test_phase20_7v_focus_trace_emits_confidence_gap_signal() -> None:
    """红线锁定: 视焦点 trace 现在包含 confidence_gap (认知驱动信号, §16.3/§16.7).

    修复前 saliency 只有 edge/saturation/clarity_gap/distance/jitter;
    修复后注入 confidence_gap = 1 - canvas_confidence (低把握吸引焦点).
    单元测试直接验证 _next_idle_focus_from_canvas 的 focus_trace 输出含 confidence_gap.
    """
    confidence = np.ones((72, 72), dtype=np.float32) * 0.9
    confidence[50:65, 50:65] = 0.15  # 低把握区域 (右下)
    canvas = _canvas_with_confidence_map(confidence_map=confidence)
    focus_xy, trace = _next_idle_focus_from_canvas(canvas, tick=5, allow_unknown=False)
    assert "confidence_gap" in trace
    assert 0.0 <= float(trace["confidence_gap"]) <= 1.0
    # 信号被镜像到 selected_action 的场景由 vision tick 处理, 这里只验 focus_trace 本身


def test_phase20_7v_low_confidence_region_attracts_focus() -> None:
    """拟人行为锁定: 把握度低的区域会吸引重复关注 ("还没看清那里, 再看一眼").

    构造一张画布, 左上是高把握高显著性区, 右下是低把握区.
    如果焦点纯环境显著性, 会只盯左上. 如果含认知驱动, 应偏向右下低把握区.
    """
    confidence = np.ones((72, 72), dtype=np.float32) * 0.92
    confidence[48:68, 48:68] = 0.12  # 右下低把握
    pixels = np.zeros((72, 72, 3), dtype=np.float32)
    pixels[4:24, 4:24] = (0.95, 0.1, 0.1)  # 左上亮红 (高 edge/saturation)
    canvas = _canvas_with_confidence_map(
        confidence_map=confidence,
        pixels_map=pixels,
        last_fixation_xy=(14, 14),  # 当前焦点在左上
    )
    focus_xy, trace = _next_idle_focus_from_canvas(canvas, tick=5, allow_unknown=False)
    # 认知驱动应使焦点偏向右下低把握区 (confidence_gap 高)
    # 对抗性自检: 这不是硬断言"必须在右下", 而是确认 confidence_gap 在焦点处显著>0
    assert float(trace["confidence_gap"]) > 0.1, "焦点处 confidence_gap 应显著, 证明认知驱动力在起作用"


def test_phase20_7v_high_confidence_does_not_pretend_unknown() -> None:
    """安全边界: 高把握画布不会假装未知, confidence_gap 应低, 不夸大不确定性."""
    confidence = np.ones((72, 72), dtype=np.float32) * 0.95
    canvas = _canvas_with_confidence_map(confidence_map=confidence)
    _, trace = _next_idle_focus_from_canvas(canvas, tick=5, allow_unknown=False)
    assert float(trace["confidence_gap"]) <= 0.2, "高把握区 confidence_gap 应低 (不假装未知)"


def test_phase20_7v_cognitive_drive_does_not_break_visual_teaching(tmp_path: Path) -> None:
    """回归保护: 认知驱动注入后, 苹果/香蕉教学仍然互相不覆盖."""
    db_path = tmp_path / "focus_teach.sqlite"
    apple_like = _make_two_region_image(tmp_path / "apple_t.png")
    banana_like = Image.new("RGB", (72, 72), (8, 8, 8))
    ImageDraw.Draw(banana_like).rectangle((4, 4, 68, 68), fill=(240, 220, 40))
    banana_like.save(tmp_path / "banana_t.png")

    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0),
        session_id="focus-teach-a",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        teacher_feedback=TeacherFeedback(feedback_text="是香蕉", reward_mag=1.0),
        session_id="focus-teach-b",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    apple_recall = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(apple_like)),),
        session_id="focus-recall-a",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    banana_recall = run_phase20_7_turn(
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(banana_like)),),
        session_id="focus-recall-b",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    assert apple_recall.reply_text == "是苹果"
    assert banana_recall.reply_text == "是香蕉"


def test_phase20_7v_stage5_focus_still_multi_point_and_clarity_accumulates(tmp_path: Path) -> None:
    """回归保护: 认知驱动注入后, stage5 首图采样焦点仍多点 + 清晰度积累."""
    db_path = tmp_path / "stage5_focus.sqlite"
    image_path = _make_two_region_image(tmp_path / "two_region.png")
    result = run_phase20_7_turn(
        media_inputs=(MediaInput(media_type="image", path=str(image_path)),),
        session_id="stage5-cog",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage5",
    )
    visual_events = [e for e in result.tick_trace if e.visual_inner_picture]
    assert len(visual_events) >= 2
    focus_points = [
        tuple(e.selected_action["focus_xy"])
        for e in visual_events
        if isinstance(e.selected_action, dict)
    ]
    assert len(set(focus_points)) >= 2
    clarity = [float(e.visual_inner_picture["clarity_coverage"]) for e in visual_events]
    assert clarity[-1] >= clarity[0]