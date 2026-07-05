#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from runtime.cognitive.state_pool.state_pool import load_constant


ASSET_ROOT = Path("config/curriculum/assets")
PACKAGE_ROOT = Path("config/curriculum/packages/clean")
SCRIPT_URL = "script://scripts/curriculum/generate_clean_concept_cards.py"
LICENSE_ID = "LicenseRef-APV3-Synthetic-Generated"
ATTRIBUTION = "APV3 clean concept card generator"

CONCEPTS = (
    {
        "entry_id": "noun_apple",
        "label": "苹果",
        "shape": "apple",
        "contrast_shape": "banana",
        "contrast_source": "noun_banana",
    },
    {
        "entry_id": "noun_banana",
        "label": "香蕉",
        "shape": "banana",
        "contrast_shape": "orange",
        "contrast_source": "noun_orange",
    },
    {
        "entry_id": "noun_orange",
        "label": "橙子",
        "shape": "orange",
        "contrast_shape": "apple",
        "contrast_source": "noun_apple",
    },
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-root", default=str(ASSET_ROOT))
    parser.add_argument("--package-root", default=str(PACKAGE_ROOT))
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    asset_root = Path(args.asset_root)
    package_root = Path(args.package_root)
    manifest_path = asset_root / "clean_card_manifest.yaml"
    package_path = package_root / "clean_fruit_cards_v1.yaml"
    if args.summary_only:
        print(json.dumps(_summary_from_manifest(manifest_path), ensure_ascii=False, sort_keys=True))
        return

    (asset_root / "visual" / "clean_cards").mkdir(parents=True, exist_ok=True)
    package_root.mkdir(parents=True, exist_ok=True)

    assets: list[dict[str, object]] = []
    entries: list[dict[str, object]] = []
    for concept_index, concept in enumerate(CONCEPTS):
        entry, records = build_entry(asset_root, concept_index, concept)
        entries.append(entry)
        assets.extend(records)

    manifest = {
        "schema_id": "apv3_asset_manifest/v1",
        "manifest_id": "phase18_clean_concept_cards_v1",
        "asset_origin_policy": "clean_generated_cards_no_text_before_real_photo_generalization",
        "assets": assets,
    }
    package = {
        "schema_id": "apv3_clean_card_curriculum_pack/v1",
        "package_id": "clean_fruit_cards_v1",
        "phase_id": "18.0",
        "title": "Clean fruit concept cards v1",
        "governance": {
            "trust_tier": "official",
            "license_id": LICENSE_ID,
            "author_id": "apv3_clean_card_generator",
            "source_policy": "generated_static_seed_no_text_in_pixels",
            "review_status": "phase18_alpha_reviewed",
        },
        "entries": entries,
    }
    write_json_yaml(manifest_path, manifest)
    write_json_yaml(package_path, package)
    print(json.dumps(_summary_from_manifest(manifest_path), ensure_ascii=False, sort_keys=True))


def build_entry(asset_root: Path, concept_index: int, concept: dict[str, object]) -> tuple[dict[str, object], list[dict[str, object]]]:
    train_refs: list[str] = []
    held_refs: list[str] = []
    contrast_refs: list[str] = []
    records: list[dict[str, object]] = []

    train_count = int(load_constant("curriculum.clean_cards.train_assets_per_concept"))
    for variant in range(train_count):
        asset_id, record = write_card_asset(
            asset_root,
            entry_id=str(concept["entry_id"]),
            shape=str(concept["shape"]),
            use_kind="train",
            variant=variant,
            concept_index=concept_index,
            tags=("clean_card", str(concept["entry_id"])),
        )
        train_refs.append(asset_id)
        records.append(record)

    held_count = int(load_constant("curriculum.clean_cards.held_out_assets_per_concept"))
    for variant in range(held_count):
        asset_id, record = write_card_asset(
            asset_root,
            entry_id=str(concept["entry_id"]),
            shape=str(concept["shape"]),
            use_kind="held_out",
            variant=variant,
            concept_index=concept_index,
            tags=("clean_card", str(concept["entry_id"])),
        )
        held_refs.append(asset_id)
        records.append(record)

    contrast_count = int(load_constant("curriculum.clean_cards.contrast_assets_per_concept"))
    for variant in range(contrast_count):
        asset_id, record = write_card_asset(
            asset_root,
            entry_id=str(concept["entry_id"]),
            shape=str(concept["contrast_shape"]),
            use_kind="contrast",
            variant=variant,
            concept_index=concept_index,
            tags=("clean_card", str(concept["entry_id"]), f"contrast_source:{concept['contrast_source']}"),
        )
        contrast_refs.append(asset_id)
        records.append(record)

    entry = {
        "entry_id": str(concept["entry_id"]),
        "content_kind": "clean_visual_vocabulary",
        "public_payload": {
            "concept_kind": "fruit",
            "neutral_label": str(concept["label"]),
            "teaching_intent": "clean_card_first_concept",
        },
        "train_asset_refs": train_refs,
        "held_out_asset_refs": held_refs,
        "contrast_asset_refs": contrast_refs,
        "governance_tags": ["phase18", "clean_card", "fruit", "no_text_in_pixels"],
    }
    return entry, records


def write_card_asset(
    asset_root: Path,
    *,
    entry_id: str,
    shape: str,
    use_kind: str,
    variant: int,
    concept_index: int,
    tags: tuple[str, ...],
) -> tuple[str, dict[str, object]]:
    asset_id = f"asset::clean_card::{entry_id}::{use_kind}::{variant}"
    filename = f"{entry_id}_{use_kind}_{variant}.png"
    rel_path = Path("visual") / "clean_cards" / filename
    path = asset_root / rel_path
    image = render_card(shape=shape, use_kind=use_kind, variant=variant, concept_index=concept_index)
    image.save(path, "PNG")
    data = path.read_bytes()
    intended_use = "curriculum_train" if use_kind == "train" else use_kind
    record = {
        "asset_id": asset_id,
        "path": rel_path.as_posix(),
        "media_type": "image/png",
        "sha256": hashlib.sha256(data).hexdigest(),
        "asset_origin": "generated_local",
        "source_url": f"{SCRIPT_URL}#{asset_id}",
        "license_id": LICENSE_ID,
        "attribution": ATTRIBUTION,
        "intended_use": intended_use,
        "held_out_group": "fold_0" if intended_use == "held_out" else "",
        "content_safety_review": "pass",
        "semantic_tags": list(tags),
    }
    return asset_id, record


def render_card(*, shape: str, use_kind: str, variant: int, concept_index: int) -> Image.Image:
    """@op_count: O(width * height)."""
    size = int(load_constant("curriculum.clean_cards.card_canvas_px"))
    scale = int(load_constant("curriculum.clean_cards.render_scale"))
    canvas = size * scale
    rng = random.Random(f"{shape}:{use_kind}:{variant}:{concept_index}")
    bg = _background(canvas, rng)
    image = Image.new("RGB", (canvas, canvas), bg)
    draw = ImageDraw.Draw(image, "RGBA")

    card_margin = int(canvas * 0.08)
    draw.rounded_rectangle(
        (card_margin, card_margin, canvas - card_margin, canvas - card_margin),
        radius=int(canvas * 0.055),
        fill=(252, 252, 248, 255),
        outline=(214, 222, 218, 255),
        width=max(2, scale * 2),
    )
    _subtle_noise(image, rng)

    shift_x = int((rng.random() - 0.5) * canvas * 0.10)
    shift_y = int((rng.random() - 0.5) * canvas * 0.08)
    base_radius = canvas * (0.245 + rng.random() * 0.025)
    if use_kind == "held_out":
        base_radius = canvas * 0.275
        shift_x += int(canvas * 0.025)
    elif use_kind == "contrast":
        base_radius = canvas * 0.255
        shift_y -= int(canvas * 0.025)

    center = (canvas // 2 + shift_x, canvas // 2 + shift_y)
    shadow = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow, "RGBA")
    _draw_fruit(shadow_draw, shape, center=(center[0] + scale * 4, center[1] + scale * 6), radius=base_radius, alpha=55)
    image = Image.alpha_composite(image.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(scale * 3)))
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_fruit(draw, shape, center=center, radius=base_radius, alpha=255)

    image = image.resize((size, size), Image.Resampling.LANCZOS)
    return image.convert("RGB")


def _background(canvas: int, rng: random.Random) -> tuple[int, int, int]:
    palette = (
        (236, 240, 238),
        (239, 238, 231),
        (234, 240, 242),
        (241, 237, 239),
    )
    return palette[int(rng.random() * len(palette)) % len(palette)]


def _subtle_noise(image: Image.Image, rng: random.Random) -> None:
    pixels = image.load()
    width, height = image.size
    for y in range(height):
        for x in range(width):
            if rng.random() > 0.965:
                r, g, b = pixels[x, y]
                delta = rng.choice((-2, -1, 1, 2))
                pixels[x, y] = (max(0, min(255, r + delta)), max(0, min(255, g + delta)), max(0, min(255, b + delta)))


def _draw_fruit(draw: ImageDraw.ImageDraw, shape: str, *, center: tuple[int, int], radius: float, alpha: int) -> None:
    if shape == "apple":
        _draw_apple(draw, center=center, radius=radius, alpha=alpha)
    elif shape == "banana":
        _draw_banana(draw, center=center, radius=radius, alpha=alpha)
    elif shape == "orange":
        _draw_orange(draw, center=center, radius=radius, alpha=alpha)
    else:
        raise ValueError(f"unknown shape: {shape}")


def _draw_apple(draw: ImageDraw.ImageDraw, *, center: tuple[int, int], radius: float, alpha: int) -> None:
    cx, cy = center
    r = int(radius)
    red = (211, 55, 48, alpha)
    dark = (156, 42, 41, alpha)
    leaf = (67, 137, 80, alpha)
    draw.ellipse((cx - r, cy - r // 2, cx, cy + r), fill=red, outline=dark, width=max(2, r // 18))
    draw.ellipse((cx, cy - r // 2, cx + r, cy + r), fill=red, outline=dark, width=max(2, r // 18))
    draw.ellipse((cx - int(r * 0.78), cy - int(r * 0.55), cx + int(r * 0.78), cy + int(r * 0.92)), fill=red)
    draw.rectangle((cx - r // 14, cy - r, cx + r // 14, cy - r // 2), fill=(91, 78, 48, alpha))
    draw.ellipse((cx + r // 12, cy - r, cx + int(r * 0.75), cy - int(r * 0.58)), fill=leaf)
    draw.ellipse((cx - r // 3, cy - r // 3, cx - r // 10, cy - r // 8), fill=(240, 109, 95, max(80, alpha // 2)))


def _draw_banana(draw: ImageDraw.ImageDraw, *, center: tuple[int, int], radius: float, alpha: int) -> None:
    cx, cy = center
    r = int(radius)
    yellow = (237, 195, 55, alpha)
    edge = (169, 124, 34, alpha)
    outer = (cx - int(r * 1.35), cy - int(r * 0.75), cx + int(r * 1.15), cy + int(r * 1.05))
    inner = (cx - int(r * 0.92), cy - int(r * 1.02), cx + int(r * 1.22), cy + int(r * 0.60))
    draw.pieslice(outer, 22, 206, fill=yellow, outline=edge, width=max(2, r // 18))
    draw.pieslice(inner, 18, 206, fill=(252, 252, 248, alpha))
    draw.ellipse((cx - int(r * 1.27), cy + int(r * 0.25), cx - int(r * 1.05), cy + int(r * 0.48)), fill=edge)
    draw.ellipse((cx + int(r * 0.82), cy - int(r * 0.48), cx + int(r * 1.04), cy - int(r * 0.28)), fill=edge)


def _draw_orange(draw: ImageDraw.ImageDraw, *, center: tuple[int, int], radius: float, alpha: int) -> None:
    cx, cy = center
    r = int(radius)
    orange = (225, 117, 41, alpha)
    edge = (175, 83, 31, alpha)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=orange, outline=edge, width=max(2, r // 18))
    for offset in (-r // 2, 0, r // 2):
        draw.arc((cx - r + abs(offset) // 3, cy - r, cx + r - abs(offset) // 3, cy + r), 76, 284, fill=(242, 154, 76, alpha), width=max(2, r // 24))
    draw.arc((cx - r, cy - r // 2, cx + r, cy + r // 2), 0, 360, fill=(242, 154, 76, alpha), width=max(2, r // 24))
    draw.ellipse((cx - r // 3, cy - r // 3, cx - r // 8, cy - r // 8), fill=(247, 173, 93, max(80, alpha // 2)))


def _summary_from_manifest(path: Path) -> dict[str, int]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    assets = raw.get("assets", [])
    return {
        "assets": len(assets),
        "train": sum(1 for item in assets if item.get("intended_use") == "curriculum_train"),
        "held_out": sum(1 for item in assets if item.get("intended_use") == "held_out"),
        "contrast": sum(1 for item in assets if item.get("intended_use") == "contrast"),
        "visual": sum(1 for item in assets if item.get("media_type") == "image/png"),
    }


def write_json_yaml(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
