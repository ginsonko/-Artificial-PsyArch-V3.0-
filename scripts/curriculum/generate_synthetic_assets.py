#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import wave
import zlib
from pathlib import Path


ROOT = Path("config/curriculum/assets")
PACKAGE_ROOT = Path("config/curriculum/packages/neutral")
SCRIPT_URL = "script://scripts/curriculum/generate_synthetic_assets.py"
LICENSE_ID = "LicenseRef-APV3-Synthetic-Generated"
ATTRIBUTION = "APV3 synthetic curriculum generator"
PNG_SIZE = 96
SAMPLE_RATE = 16000


PACKS = [
    {
        "package_id": "neutral_colors_v1",
        "title": "Neutral colors v1",
        "concept_kind": "color",
        "content_kind": "vocabulary_visual",
        "entries": [
            ("color_red", "红", "color", {"color": (218, 62, 55)}),
            ("color_yellow", "黄", "color", {"color": (236, 192, 48)}),
            ("color_blue", "蓝", "color", {"color": (54, 110, 190)}),
            ("color_green", "绿", "color", {"color": (70, 155, 90)}),
            ("color_white", "白", "color", {"color": (245, 245, 238)}),
        ],
    },
    {
        "package_id": "neutral_shapes_v1",
        "title": "Neutral shapes v1",
        "concept_kind": "shape",
        "content_kind": "vocabulary_visual",
        "entries": [
            ("shape_circle", "圆", "shape", {"shape": "circle", "color": (61, 137, 132)}),
            ("shape_square", "方", "shape", {"shape": "square", "color": (55, 105, 165)}),
            ("shape_triangle", "三角", "shape", {"shape": "triangle", "color": (224, 144, 58)}),
            ("shape_diamond", "菱形", "shape", {"shape": "diamond", "color": (145, 92, 168)}),
            ("shape_bar", "长条", "shape", {"shape": "bar", "color": (88, 120, 72)}),
        ],
    },
    {
        "package_id": "neutral_numbers_v1",
        "title": "Neutral numbers v1",
        "concept_kind": "number",
        "content_kind": "vocabulary_visual",
        "entries": [
            ("number_0", "0", "number", {"digit": 0, "color": (48, 91, 143)}),
            ("number_1", "1", "number", {"digit": 1, "color": (48, 91, 143)}),
            ("number_2", "2", "number", {"digit": 2, "color": (48, 91, 143)}),
            ("number_3", "3", "number", {"digit": 3, "color": (48, 91, 143)}),
            ("number_4", "4", "number", {"digit": 4, "color": (48, 91, 143)}),
        ],
    },
    {
        "package_id": "neutral_directions_v1",
        "title": "Neutral directions v1",
        "concept_kind": "direction",
        "content_kind": "vocabulary_visual",
        "entries": [
            ("direction_up", "上", "direction", {"direction": "up", "color": (31, 124, 114)}),
            ("direction_down", "下", "direction", {"direction": "down", "color": (31, 124, 114)}),
            ("direction_left", "左", "direction", {"direction": "left", "color": (31, 124, 114)}),
            ("direction_right", "右", "direction", {"direction": "right", "color": (31, 124, 114)}),
            ("direction_inside", "里", "direction", {"direction": "inside", "color": (31, 124, 114)}),
        ],
    },
    {
        "package_id": "neutral_daily_nouns_v1",
        "title": "Neutral daily nouns v1",
        "concept_kind": "daily_noun",
        "content_kind": "vocabulary_visual",
        "entries": [
            ("noun_apple", "苹果", "object", {"object": "apple", "color": (218, 62, 55)}),
            ("noun_cup", "杯子", "object", {"object": "cup", "color": (73, 139, 178)}),
            ("noun_book", "书", "object", {"object": "book", "color": (80, 140, 92)}),
            ("noun_table", "桌子", "object", {"object": "table", "color": (154, 106, 65)}),
            ("noun_chair", "椅子", "object", {"object": "chair", "color": (134, 97, 72)}),
        ],
    },
    {
        "package_id": "neutral_basic_actions_v1",
        "title": "Neutral basic actions v1",
        "concept_kind": "action",
        "content_kind": "vocabulary_visual",
        "entries": [
            ("action_walk", "走", "action", {"action": "walk", "color": (36, 119, 128)}),
            ("action_run", "跑", "action", {"action": "run", "color": (36, 119, 128)}),
            ("action_jump", "跳", "action", {"action": "jump", "color": (36, 119, 128)}),
            ("action_sit", "坐", "action", {"action": "sit", "color": (36, 119, 128)}),
            ("action_pick", "拿", "action", {"action": "pick", "color": (36, 119, 128)}),
        ],
    },
    {
        "package_id": "neutral_feedback_symbols_v1",
        "title": "Neutral feedback symbols v1",
        "concept_kind": "feedback",
        "content_kind": "vocabulary_visual",
        "entries": [
            ("feedback_correct", "对", "feedback", {"symbol": "check", "color": (31, 141, 91)}),
            ("feedback_wrong", "不对", "feedback", {"symbol": "cross", "color": (180, 71, 64)}),
            ("feedback_again", "再来", "feedback", {"symbol": "repeat", "color": (78, 102, 174)}),
            ("feedback_slow", "慢点", "feedback", {"symbol": "slow", "color": (176, 125, 42)}),
            ("feedback_thanks", "谢谢", "feedback", {"symbol": "heart", "color": (188, 81, 117)}),
        ],
    },
    {
        "package_id": "neutral_audio_patterns_v1",
        "title": "Neutral audio patterns v1",
        "concept_kind": "audio_pattern",
        "content_kind": "audio_pattern",
        "entries": [
            ("audio_soft_call", "轻声呼唤", "audio", {"freq": 440.0, "pattern": "soft_call"}),
            ("audio_confirm_tone", "确认音", "audio", {"freq": 554.37, "pattern": "confirm"}),
            ("audio_correction_tone", "纠正音", "audio", {"freq": 329.63, "pattern": "correction"}),
            ("audio_uncertain_tone", "不确定音", "audio", {"freq": 392.0, "pattern": "uncertain"}),
            ("audio_attention_tone", "注意音", "audio", {"freq": 659.25, "pattern": "attention"}),
        ],
    },
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-root", default=str(ROOT))
    parser.add_argument("--package-root", default=str(PACKAGE_ROOT))
    args = parser.parse_args()
    asset_root = Path(args.asset_root)
    package_root = Path(args.package_root)
    (asset_root / "visual" / "synthetic").mkdir(parents=True, exist_ok=True)
    (asset_root / "audio" / "synthetic").mkdir(parents=True, exist_ok=True)
    package_root.mkdir(parents=True, exist_ok=True)

    assets: list[dict[str, object]] = []
    packages: list[dict[str, object]] = []
    for pack in PACKS:
        package, new_assets = build_package(pack, asset_root)
        packages.append(package)
        assets.extend(new_assets)

    manifest = {
        "schema_id": "apv3_asset_manifest/v1",
        "manifest_id": "phase14_synthetic_first_curriculum_assets",
        "asset_origin_policy": "synthetic_first_no_external_download",
        "assets": assets,
    }
    write_json_yaml(asset_root / "manifest.yaml", manifest)
    for package in packages:
        write_json_yaml(package_root / f"{package['package_id']}.yaml", package)


def build_package(pack: dict[str, object], asset_root: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    package_entries = []
    assets = []
    entries = list(pack["entries"])
    for index, entry in enumerate(entries):
        concept_id, label, render_kind, spec = entry
        contrast_entry = entries[(index + 1) % len(entries)]
        contrast_spec = contrast_entry[3]
        train_refs = []
        held_refs = []
        contrast_refs = []
        if pack["content_kind"] == "audio_pattern":
            for variant in range(3):
                asset_id, record = write_audio_asset(asset_root, pack, concept_id, spec, "train", variant)
                train_refs.append(asset_id)
                assets.append(record)
            asset_id, record = write_audio_asset(asset_root, pack, concept_id, spec, "held_out", 0)
            held_refs.append(asset_id)
            assets.append(record)
            asset_id, record = write_audio_asset(asset_root, pack, concept_id, contrast_spec, "contrast", 0)
            contrast_refs.append(asset_id)
            assets.append(record)
        else:
            for variant in range(3):
                asset_id, record = write_visual_asset(asset_root, pack, concept_id, render_kind, spec, "train", variant)
                train_refs.append(asset_id)
                assets.append(record)
            asset_id, record = write_visual_asset(asset_root, pack, concept_id, render_kind, spec, "held_out", 0)
            held_refs.append(asset_id)
            assets.append(record)
            asset_id, record = write_visual_asset(asset_root, pack, concept_id, render_kind, contrast_spec, "contrast", 0)
            contrast_refs.append(asset_id)
            assets.append(record)
        package_entries.append(
            {
                "entry_id": concept_id,
                "content_kind": pack["content_kind"],
                "public_payload": {
                    "concept_kind": pack["concept_kind"],
                    "neutral_label": label,
                    "teaching_intent": "neutral_foundation",
                },
                "train_asset_refs": train_refs,
                "held_out_asset_refs": held_refs,
                "contrast_asset_refs": contrast_refs,
                "governance_tags": ["phase14", "synthetic", str(pack["concept_kind"])],
            }
        )
    package = {
        "schema_id": "apv3_neutral_curriculum_pack/v1",
        "package_id": pack["package_id"],
        "phase_id": "14.2",
        "title": pack["title"],
        "governance": {
            "trust_tier": "official",
            "license_id": LICENSE_ID,
            "author_id": "apv3_synthetic_generator",
            "source_policy": "generated_static_seed",
            "review_status": "phase14_alpha_reviewed",
        },
        "entries": package_entries,
    }
    return package, assets


def write_visual_asset(
    asset_root: Path,
    pack: dict[str, object],
    concept_id: str,
    render_kind: str,
    spec: dict[str, object],
    use_kind: str,
    variant: int,
) -> tuple[str, dict[str, object]]:
    asset_id = f"asset::{concept_id}::{use_kind}::{variant}"
    filename = f"{concept_id}_{use_kind}_{variant}.png"
    rel_path = Path("visual") / "synthetic" / filename
    path = asset_root / rel_path
    pixels = render_visual(render_kind, spec, variant=variant, use_kind=use_kind)
    write_png(path, pixels)
    data = path.read_bytes()
    record = asset_record(asset_id, rel_path, "image/png", use_kind, data, [str(pack["concept_kind"]), concept_id])
    return asset_id, record


def write_audio_asset(
    asset_root: Path,
    pack: dict[str, object],
    concept_id: str,
    spec: dict[str, object],
    use_kind: str,
    variant: int,
) -> tuple[str, dict[str, object]]:
    asset_id = f"asset::{concept_id}::{use_kind}::{variant}"
    filename = f"{concept_id}_{use_kind}_{variant}.wav"
    rel_path = Path("audio") / "synthetic" / filename
    path = asset_root / rel_path
    base = float(spec["freq"])
    freq = base + (variant - 1) * 12.0 if use_kind == "train" else base + 6.0
    if use_kind == "contrast":
        freq = base + 160.0
    write_wav(path, freq=freq)
    data = path.read_bytes()
    record = asset_record(asset_id, rel_path, "audio/wav", use_kind, data, [str(pack["concept_kind"]), concept_id])
    return asset_id, record


def asset_record(
    asset_id: str,
    rel_path: Path,
    media_type: str,
    use_kind: str,
    data: bytes,
    tags: list[str],
) -> dict[str, object]:
    intended_use = "curriculum_train" if use_kind == "train" else use_kind
    return {
        "asset_id": asset_id,
        "path": rel_path.as_posix(),
        "media_type": media_type,
        "sha256": hashlib.sha256(data).hexdigest(),
        "asset_origin": "generated_local",
        "source_url": f"{SCRIPT_URL}#{asset_id}",
        "license_id": LICENSE_ID,
        "attribution": ATTRIBUTION,
        "intended_use": intended_use,
        "held_out_group": "fold_0" if intended_use == "held_out" else "",
        "content_safety_review": "pass",
        "semantic_tags": tags,
    }


def render_visual(render_kind: str, spec: dict[str, object], *, variant: int, use_kind: str) -> list[list[tuple[int, int, int]]]:
    bg = (248, 250, 247) if use_kind != "contrast" else (244, 247, 250)
    pixels = [[bg for _ in range(PNG_SIZE)] for _ in range(PNG_SIZE)]
    color = tuple(spec.get("color", (48, 105, 150)))
    inset = 16 + variant * 3
    if use_kind == "held_out":
        inset = 13
    if render_kind == "color":
        draw_rect(pixels, inset, inset, PNG_SIZE - inset, PNG_SIZE - inset, color)
        draw_rect(pixels, inset + 8, inset + 8, PNG_SIZE - inset - 8, PNG_SIZE - inset - 8, blend(color, (255, 255, 255), 0.20))
    elif render_kind == "shape":
        draw_shape(pixels, str(spec["shape"]), color, inset)
    elif render_kind == "number":
        draw_digit(pixels, int(spec["digit"]), color)
    elif render_kind == "direction":
        draw_direction(pixels, str(spec["direction"]), color)
    elif render_kind == "object":
        draw_object(pixels, str(spec["object"]), color)
    elif render_kind == "action":
        draw_action(pixels, str(spec["action"]), color)
    elif render_kind == "feedback":
        draw_feedback(pixels, str(spec["symbol"]), color)
    draw_variant_mark(pixels, variant, use_kind)
    draw_rect_outline(pixels, 4, 4, 92, 92, (210, 222, 218))
    return pixels


def draw_shape(pixels, shape: str, color, inset: int) -> None:
    if shape == "circle":
        draw_circle(pixels, 48, 48, 30, color)
    elif shape == "square":
        draw_rect(pixels, inset, inset, PNG_SIZE - inset, PNG_SIZE - inset, color)
    elif shape == "triangle":
        draw_triangle(pixels, (48, inset), (PNG_SIZE - inset, PNG_SIZE - inset), (inset, PNG_SIZE - inset), color)
    elif shape == "diamond":
        draw_polygon(pixels, [(48, inset), (PNG_SIZE - inset, 48), (48, PNG_SIZE - inset), (inset, 48)], color)
    else:
        draw_rect(pixels, 18, 38, 78, 58, color)


def draw_digit(pixels, digit: int, color) -> None:
    segments = {
        0: "abcfed",
        1: "bc",
        2: "abged",
        3: "abgcd",
        4: "fgbc",
    }[digit]
    boxes = {
        "a": (28, 18, 68, 26),
        "b": (64, 22, 72, 46),
        "c": (64, 50, 72, 74),
        "d": (28, 70, 68, 78),
        "e": (24, 50, 32, 74),
        "f": (24, 22, 32, 46),
        "g": (28, 44, 68, 52),
    }
    for segment in segments:
        draw_rect(pixels, *boxes[segment], color)


def draw_direction(pixels, direction: str, color) -> None:
    if direction == "up":
        draw_triangle(pixels, (48, 18), (72, 50), (56, 50), color)
        draw_rect(pixels, 40, 48, 56, 78, color)
    elif direction == "down":
        draw_triangle(pixels, (48, 78), (72, 46), (56, 46), color)
        draw_rect(pixels, 40, 18, 56, 48, color)
    elif direction == "left":
        draw_triangle(pixels, (18, 48), (50, 24), (50, 40), color)
        draw_rect(pixels, 48, 40, 78, 56, color)
    elif direction == "right":
        draw_triangle(pixels, (78, 48), (46, 24), (46, 40), color)
        draw_rect(pixels, 18, 40, 48, 56, color)
    else:
        draw_circle(pixels, 48, 48, 32, blend(color, (255, 255, 255), 0.55))
        draw_circle(pixels, 48, 48, 15, color)


def draw_object(pixels, obj: str, color) -> None:
    if obj == "apple":
        draw_circle(pixels, 48, 52, 24, color)
        draw_rect(pixels, 47, 20, 51, 34, (83, 103, 61))
        draw_ellipse_leaf(pixels, 55, 27, (72, 142, 85))
    elif obj == "cup":
        draw_rect(pixels, 30, 30, 62, 74, color)
        draw_rect_outline(pixels, 60, 40, 76, 60, color)
    elif obj == "book":
        draw_rect(pixels, 25, 24, 46, 76, color)
        draw_rect(pixels, 50, 24, 71, 76, blend(color, (255, 255, 255), 0.25))
        draw_rect(pixels, 47, 24, 49, 76, (230, 236, 232))
    elif obj == "table":
        draw_rect(pixels, 20, 34, 76, 44, color)
        draw_rect(pixels, 28, 44, 36, 76, color)
        draw_rect(pixels, 60, 44, 68, 76, color)
    else:
        draw_rect(pixels, 32, 28, 62, 54, color)
        draw_rect(pixels, 38, 54, 46, 78, color)
        draw_rect(pixels, 54, 54, 62, 78, color)


def draw_action(pixels, action: str, color) -> None:
    draw_circle(pixels, 48, 22, 8, color)
    if action == "sit":
        draw_line(pixels, 48, 30, 48, 52, color, 5)
        draw_line(pixels, 48, 52, 68, 52, color, 5)
        draw_line(pixels, 68, 52, 68, 74, color, 5)
    elif action == "jump":
        draw_line(pixels, 48, 30, 48, 50, color, 5)
        draw_line(pixels, 48, 50, 30, 70, color, 5)
        draw_line(pixels, 48, 50, 68, 70, color, 5)
        draw_line(pixels, 28, 38, 68, 38, color, 4)
    elif action == "run":
        draw_line(pixels, 48, 30, 56, 52, color, 5)
        draw_line(pixels, 56, 52, 76, 62, color, 5)
        draw_line(pixels, 56, 52, 38, 74, color, 5)
        draw_line(pixels, 54, 38, 76, 30, color, 4)
    elif action == "pick":
        draw_line(pixels, 48, 30, 48, 56, color, 5)
        draw_line(pixels, 48, 44, 70, 62, color, 4)
        draw_circle(pixels, 74, 66, 7, (180, 115, 60))
    else:
        draw_line(pixels, 48, 30, 48, 56, color, 5)
        draw_line(pixels, 48, 56, 34, 76, color, 5)
        draw_line(pixels, 48, 56, 62, 76, color, 5)
        draw_line(pixels, 48, 40, 34, 52, color, 4)
        draw_line(pixels, 48, 40, 64, 50, color, 4)


def draw_feedback(pixels, symbol: str, color) -> None:
    if symbol == "check":
        draw_line(pixels, 24, 52, 42, 70, color, 8)
        draw_line(pixels, 42, 70, 76, 26, color, 8)
    elif symbol == "cross":
        draw_line(pixels, 28, 28, 70, 70, color, 8)
        draw_line(pixels, 70, 28, 28, 70, color, 8)
    elif symbol == "repeat":
        draw_circle_outline(pixels, 48, 48, 28, color)
        draw_triangle(pixels, (68, 26), (78, 42), (60, 40), color)
    elif symbol == "slow":
        draw_circle_outline(pixels, 48, 48, 30, color)
        draw_line(pixels, 48, 48, 48, 28, color, 5)
        draw_line(pixels, 48, 48, 62, 58, color, 5)
    else:
        draw_circle(pixels, 38, 40, 14, color)
        draw_circle(pixels, 58, 40, 14, color)
        draw_triangle(pixels, (25, 45), (71, 45), (48, 78), color)


def draw_variant_mark(pixels, variant: int, use_kind: str) -> None:
    offset = variant * 7
    if use_kind == "held_out":
        offset = 28
    elif use_kind == "contrast":
        offset = 42
    color = (218, 226, 222)
    draw_rect(pixels, 10 + offset, 84, 16 + offset, 88, color)


def write_wav(path: Path, *, freq: float) -> None:
    duration = 0.35
    total = int(SAMPLE_RATE * duration)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for index in range(total):
            t = index / SAMPLE_RATE
            envelope = min(1.0, index / 800.0, (total - index) / 800.0)
            sample = int(12000 * envelope * math.sin(2.0 * math.pi * freq * t))
            frames.extend(struct.pack("<h", sample))
        stream.writeframes(bytes(frames))


def write_png(path: Path, pixels: list[list[tuple[int, int, int]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    height = len(pixels)
    width = len(pixels[0])
    raw = b"".join(b"\x00" + bytes(channel for pixel in row for channel in pixel) for row in pixels)
    data = b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            png_chunk(b"IDAT", zlib.compress(raw)),
            png_chunk(b"IEND", b""),
        ]
    )
    path.write_bytes(data)


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def draw_rect(pixels, x1, y1, x2, y2, color) -> None:
    for y in range(max(0, y1), min(PNG_SIZE, y2)):
        for x in range(max(0, x1), min(PNG_SIZE, x2)):
            pixels[y][x] = color


def draw_rect_outline(pixels, x1, y1, x2, y2, color) -> None:
    draw_rect(pixels, x1, y1, x2, y1 + 2, color)
    draw_rect(pixels, x1, y2 - 2, x2, y2, color)
    draw_rect(pixels, x1, y1, x1 + 2, y2, color)
    draw_rect(pixels, x2 - 2, y1, x2, y2, color)


def draw_circle(pixels, cx, cy, radius, color) -> None:
    r2 = radius * radius
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            if 0 <= x < PNG_SIZE and 0 <= y < PNG_SIZE and (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                pixels[y][x] = color


def draw_circle_outline(pixels, cx, cy, radius, color) -> None:
    for r in range(radius - 2, radius + 2):
        draw_circle_edge(pixels, cx, cy, r, color)


def draw_circle_edge(pixels, cx, cy, radius, color) -> None:
    r2 = radius * radius
    inner = (radius - 1) * (radius - 1)
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            d = (x - cx) ** 2 + (y - cy) ** 2
            if 0 <= x < PNG_SIZE and 0 <= y < PNG_SIZE and inner <= d <= r2:
                pixels[y][x] = color


def draw_triangle(pixels, p1, p2, p3, color) -> None:
    draw_polygon(pixels, [p1, p2, p3], color)


def draw_polygon(pixels, points, color) -> None:
    min_x = max(0, min(p[0] for p in points))
    max_x = min(PNG_SIZE - 1, max(p[0] for p in points))
    min_y = max(0, min(p[1] for p in points))
    max_y = min(PNG_SIZE - 1, max(p[1] for p in points))
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            if point_in_poly(x, y, points):
                pixels[y][x] = color


def point_in_poly(x, y, points) -> bool:
    inside = False
    j = len(points) - 1
    for i in range(len(points)):
        xi, yi = points[i]
        xj, yj = points[j]
        if ((yi > y) != (yj > y)) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def draw_line(pixels, x1, y1, x2, y2, color, width) -> None:
    steps = max(abs(x2 - x1), abs(y2 - y1), 1)
    for step in range(steps + 1):
        t = step / steps
        x = int(x1 + (x2 - x1) * t)
        y = int(y1 + (y2 - y1) * t)
        draw_circle(pixels, x, y, max(1, width // 2), color)


def draw_ellipse_leaf(pixels, cx, cy, color) -> None:
    for y in range(cy - 8, cy + 8):
        for x in range(cx - 14, cx + 14):
            if 0 <= x < PNG_SIZE and 0 <= y < PNG_SIZE and ((x - cx) / 14) ** 2 + ((y - cy) / 8) ** 2 <= 1:
                pixels[y][x] = color


def blend(a, b, ratio):
    return tuple(int(a[i] * (1.0 - ratio) + b[i] * ratio) for i in range(3))


def write_json_yaml(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
