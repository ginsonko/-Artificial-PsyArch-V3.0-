from __future__ import annotations

import json
import math
import shutil
import statistics
import struct
import subprocess
import sys
import time
import wave
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apv3test.runtime.phase20_7 import (
    MediaInput,
    TeacherFeedback,
    list_active_unclosed_items,
    list_unified_memory_entries,
    run_phase20_7_turn,
)


RUN_ID = "20260626"
DEMO_ROOT = ROOT / "data" / "phase20_7_release_demo"
ASSET_ROOT = DEMO_ROOT / "assets"
REPORT_ROOT = ROOT / "reports"
DB_PATH = DEMO_ROOT / "phase20_7_release_demo.sqlite"
MANIFEST_PATH = REPORT_ROOT / f"Phase20_7_release_demo_manifest_{RUN_ID}.json"
PERFORMANCE_PATH = REPORT_ROOT / f"Phase20_7_performance_report_{RUN_ID}.json"
HTML_PATH = REPORT_ROOT / f"APV3_Phase20_7_ReleaseDemo_{RUN_ID}.html"
ZIP_PATH = REPORT_ROOT / f"APV3_Phase20_7_ReleaseDemo_Package_{RUN_ID}.zip"


def main() -> int:
    _reset_demo_dir()
    assets = _make_assets()
    flows, perf_samples = _run_flows(assets)
    performance = _summarize_performance(perf_samples)
    manifest = {
        "schema_id": "apv3_phase20_7_release_demo_manifest/v1",
        "run_id": RUN_ID,
        "objective": "APV3 Phase20.7 local open dialogue foundation release demo",
        "db_path": str(DB_PATH),
        "assets": {key: str(value) for key, value in assets.items()},
        "reports": {
            "html": str(HTML_PATH),
            "performance": str(PERFORMANCE_PATH),
            "zip": str(ZIP_PATH),
        },
        "flows": flows,
        "redlines": {
            "student_side_llm": False,
            "whole_image_label": False,
            "ocr": False,
            "cloud_tts": False,
            "frontend_fake_tick": False,
        },
    }
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    PERFORMANCE_PATH.write_text(json.dumps(performance, ensure_ascii=False, indent=2), encoding="utf-8")
    HTML_PATH.write_text(_render_html(manifest, performance), encoding="utf-8")
    _make_zip()
    print(json.dumps({"manifest": str(MANIFEST_PATH), "html": str(HTML_PATH), "zip": str(ZIP_PATH)}, ensure_ascii=False))
    return 0


def _reset_demo_dir() -> None:
    if DEMO_ROOT.exists():
        shutil.rmtree(DEMO_ROOT)
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)


def _make_assets() -> dict[str, Path]:
    assets = {
        "single_apple": ASSET_ROOT / "single_apple.png",
        "single_banana": ASSET_ROOT / "single_banana.png",
        "single_orange": ASSET_ROOT / "single_orange.png",
        "apple_variant_shifted": ASSET_ROOT / "apple_variant_shifted.png",
        "audio_tone": ASSET_ROOT / "audio_tone.wav",
    }
    _draw_apple(assets["single_apple"], offset=(0, 0))
    _draw_banana(assets["single_banana"])
    _draw_orange(assets["single_orange"])
    _draw_apple(assets["apple_variant_shifted"], offset=(8, -5))
    _make_wav(assets["audio_tone"])
    return assets


def _draw_apple(path: Path, *, offset: tuple[int, int]) -> None:
    image = Image.new("RGB", (96, 96), (18, 20, 22))
    draw = ImageDraw.Draw(image)
    dx, dy = offset
    draw.ellipse((22 + dx, 28 + dy, 76 + dx, 82 + dy), fill=(220, 32, 42), outline=(255, 170, 170), width=2)
    draw.rectangle((48 + dx, 16 + dy, 53 + dx, 32 + dy), fill=(95, 55, 25))
    draw.ellipse((54 + dx, 16 + dy, 73 + dx, 30 + dy), fill=(72, 170, 88))
    image.save(path)


def _draw_banana(path: Path) -> None:
    image = Image.new("RGB", (96, 96), (18, 20, 22))
    draw = ImageDraw.Draw(image)
    draw.arc((12, 18, 90, 96), start=198, end=340, fill=(246, 210, 54), width=15)
    draw.arc((22, 25, 82, 82), start=200, end=338, fill=(126, 88, 28), width=3)
    image.save(path)


def _draw_orange(path: Path) -> None:
    image = Image.new("RGB", (96, 96), (18, 20, 22))
    draw = ImageDraw.Draw(image)
    draw.ellipse((20, 22, 78, 82), fill=(236, 132, 38), outline=(255, 210, 120), width=2)
    draw.ellipse((40, 18, 55, 28), fill=(73, 150, 70))
    for x in range(32, 70, 9):
        draw.line((x, 38, x - 12, 72), fill=(200, 92, 30), width=1)
    image.save(path)


def _make_wav(path: Path) -> None:
    rate = 8000
    frames = []
    for index in range(rate // 5):
        value = int(11000 * math.sin(2 * math.pi * 440 * index / rate))
        frames.append(struct.pack("<h", value))
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(b"".join(frames))


def _run_flows(assets: dict[str, Path]) -> tuple[dict[str, object], dict[str, list[float]]]:
    perf: dict[str, list[float]] = {"text_ms": [], "visual_ms": [], "stage6_ms": []}
    if DB_PATH.exists():
        DB_PATH.unlink()

    def timed(name: str, **kwargs):
        start = time.perf_counter()
        result = run_phase20_7_turn(db_path=DB_PATH, **kwargs)
        perf[name].append((time.perf_counter() - start) * 1000.0)
        return result

    learn = timed(
        "text_ms",
        user_text="你好啊",
        teacher_feedback=TeacherFeedback(feedback_text="你也好", reward_mag=1.0),
        session_id="release-learn",
        runtime_stage="stage6",
        post_commit_idle_ticks=0,
    )
    recall = timed("text_ms", user_text="你好啊", session_id="release-recall", runtime_stage="stage6", post_commit_idle_ticks=0)
    near = timed("text_ms", user_text="你好呀", session_id="release-near", runtime_stage="stage6", post_commit_idle_ticks=0)
    unknown = timed("text_ms", user_text="猫是什么", session_id="release-unknown", runtime_stage="stage6", post_commit_idle_ticks=0)
    repeat_unknown = timed("text_ms", user_text="猫是什么", session_id="release-repeat", runtime_stage="stage6", post_commit_idle_ticks=0)
    idle = timed("text_ms", user_text="", session_id="release-idle", runtime_stage="stage6", post_commit_idle_ticks=0)
    cat_learn = timed(
        "text_ms",
        user_text="猫是什么",
        teacher_feedback=TeacherFeedback(feedback_text="猫是一种动物", reward_mag=1.0),
        session_id="release-cat-learn",
        runtime_stage="stage6",
        post_commit_idle_ticks=0,
    )
    cat_recall = timed("text_ms", user_text="猫是什么", session_id="release-cat-recall", runtime_stage="stage6", post_commit_idle_ticks=0)
    visual = timed(
        "visual_ms",
        user_text="这是什么",
        media_inputs=(MediaInput(media_type="image", path=str(assets["single_apple"])),),
        session_id="release-visual",
        runtime_stage="stage6",
        post_commit_idle_ticks=0,
    )
    audio = timed(
        "stage6_ms",
        media_inputs=(MediaInput(media_type="audio", path=str(assets["audio_tone"])),),
        session_id="release-audio",
        runtime_stage="stage6",
        post_commit_idle_ticks=0,
    )

    visual_ticks = [event.to_dict() for event in visual.tick_trace if event.visual_inner_picture]
    tts_ticks = [event.to_dict() for event in recall.tick_trace if event.selected_action.get("action_type") == "reply_tts_audio"]
    flows = {
        "text_learning": {
            "learn_reply": learn.reply_text,
            "recall_reply": recall.reply_text,
            "near_reply": near.reply_text,
            "near_has_structural_b": any(event.b_candidates and event.b_candidates[0].get("kind") == "structural_b" for event in near.tick_trace),
        },
        "unclosed_idle": {
            "first_unknown_reply": unknown.reply_text,
            "repeat_unknown_reply": repeat_unknown.reply_text,
            "idle_action": idle.tick_trace[0].selected_action if idle.tick_trace else {},
            "cat_learn_reply": cat_learn.reply_text,
            "cat_recall_reply": cat_recall.reply_text,
            "active_unclosed_after_learning": list(list_active_unclosed_items(DB_PATH)),
        },
        "visual_patch_reconstruction": {
            "visual_tick_count": len(visual_ticks),
            "focus_points": [tick["selected_action"].get("focus_xy") for tick in visual_ticks],
            "clarity": [tick["visual_inner_picture"].get("clarity_coverage") for tick in visual_ticks],
            "inner_picture_last": visual_ticks[-1]["visual_inner_picture"].get("path") if visual_ticks else None,
        },
        "audio_tts": {
            "audio_tick_action": audio.tick_trace[0].selected_action if audio.tick_trace else {},
            "tts_action": tts_ticks[0]["selected_action"] if tts_ticks else {},
        },
        "memory": {
            "items": list(list_unified_memory_entries(DB_PATH, limit=12)),
        },
    }
    return flows, perf


def _summarize_performance(samples: dict[str, list[float]]) -> dict[str, object]:
    rows = {}
    for name, values in samples.items():
        if not values:
            continue
        ordered = sorted(values)
        rows[name] = {
            "count": len(values),
            "min_ms": round(min(values), 3),
            "median_ms": round(statistics.median(values), 3),
            "p95_ms": round(ordered[min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1)], 3),
            "max_ms": round(max(values), 3),
        }
    return {
        "schema_id": "apv3_phase20_7_performance_report/v1",
        "thresholds": {
            "text_turn_p95_ms": 1500,
            "visual_turn_p95_ms": 3000,
            "stage6_turn_p95_ms": 3000,
        },
        "samples": rows,
        "notes": [
            "Performance is local prototype timing, not a final optimized benchmark.",
            "TTS voice enumeration may be slower on first local run.",
        ],
    }


def _render_html(manifest: dict[str, object], performance: dict[str, object]) -> str:
    flows = manifest["flows"]
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>APV3 Phase20.7 Release Demo</title>
  <style>
    body {{ font-family: 'Microsoft YaHei', system-ui, sans-serif; margin: 28px; background: #f7f7f8; color: #20242a; }}
    h1 {{ font-size: 22px; }}
    h2 {{ font-size: 16px; margin-top: 24px; }}
    pre {{ background: #fff; border: 1px solid #dfe3e8; border-radius: 8px; padding: 12px; white-space: pre-wrap; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
    img {{ max-width: 160px; image-rendering: pixelated; border: 1px solid #ccd4dd; background: #fff; }}
  </style>
</head>
<body>
  <h1>APV3 Phase20.7 发布 demo</h1>
  <p>目标: 会学的 3-5 岁小孩级本地 AP 对话底座。不是全知 LLM。</p>
  <h2>文本学习与结构类比</h2>
  <pre>{json.dumps(flows["text_learning"], ensure_ascii=False, indent=2)}</pre>
  <h2>未闭合感与闲时思考</h2>
  <pre>{json.dumps(flows["unclosed_idle"], ensure_ascii=False, indent=2)}</pre>
  <h2>视觉 patch 与内心画面</h2>
  <pre>{json.dumps(flows["visual_patch_reconstruction"], ensure_ascii=False, indent=2)}</pre>
  <h2>音频 audit 与 xiaoyi TTS</h2>
  <pre>{json.dumps(flows["audio_tts"], ensure_ascii=False, indent=2)}</pre>
  <h2>性能摘要</h2>
  <pre>{json.dumps(performance, ensure_ascii=False, indent=2)}</pre>
</body>
</html>
"""


def _make_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    include_paths = [
        MANIFEST_PATH,
        PERFORMANCE_PATH,
        HTML_PATH,
        ROOT / "docs" / "UserGuide_Phase20_7_ReleaseDemo_20260626.md",
        ROOT / "docs" / "FinalReport_Phase20_7_Stage8_ReleaseDemo_20260626.md",
        ROOT / "reports" / "Phase20_7_redline_report_20260626.txt",
        ROOT / "apv3test" / "web" / "static" / "phase20_7_workbench.html",
        ROOT / "apv3test" / "web" / "static" / "phase20_7_workbench.css",
        ROOT / "apv3test" / "web" / "static" / "phase20_7_workbench.js",
    ]
    include_paths.extend(sorted(ASSET_ROOT.glob("*")))
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in include_paths:
            if path.exists():
                zf.write(path, path.relative_to(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
