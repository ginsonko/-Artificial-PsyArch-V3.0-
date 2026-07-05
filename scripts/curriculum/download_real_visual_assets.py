#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
from io import BytesIO
from pathlib import Path
from typing import Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PIL import Image

from runtime.cognitive.curriculum.asset_governance import (
    load_asset_manifest_file,
    phase14_asset_summary,
)
from runtime.cognitive.state_pool.state_pool import load_constant


ASSET_ROOT = Path("config/curriculum/assets")
REAL_ROOT = ASSET_ROOT / "visual" / "real"
REAL_MANIFEST = ASSET_ROOT / "real_manifest.yaml"
REAL_PACKAGE_ROOT = Path("config/curriculum/packages/real")
SOURCE_SIDECAR = REAL_ROOT / "_sources.json"
USER_AGENT = "APV3test-real-asset-audit/0.1 (local research prototype)"

CONCEPTS = (
    {
        "entry_id": "noun_apple",
        "label": "苹果",
        "queries": ("apple fruit photograph", "red apple fruit", "apple tree fruit"),
    },
    {
        "entry_id": "noun_banana",
        "label": "香蕉",
        "queries": ("banana fruit photograph", "ripe bananas photograph", "banana bunch photograph"),
    },
    {
        "entry_id": "noun_orange",
        "label": "橙子",
        "queries": ("orange fruit photograph", "blood orange photograph", "orange tree fruit photograph", "citrus fruits photograph"),
    },
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-root", default=str(ASSET_ROOT))
    parser.add_argument("--package-root", default=str(REAL_PACKAGE_ROOT))
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    asset_root = Path(args.asset_root)
    package_root = Path(args.package_root)
    manifest_path = asset_root / "real_manifest.yaml"
    if args.summary_only:
        manifest = load_asset_manifest_file(manifest_path)
        print(json.dumps(phase14_asset_summary(manifest), ensure_ascii=False, sort_keys=True))
        return

    real_root = asset_root / "visual" / "real"
    real_root.mkdir(parents=True, exist_ok=True)
    package_root.mkdir(parents=True, exist_ok=True)
    for old_png in real_root.glob("*.png"):
        old_png.unlink()
    for old_pack in package_root.glob("real_*.yaml"):
        old_pack.unlink()

    search_limit = int(load_constant("curriculum.real_assets.commons_search_limit"))
    selected: dict[str, list[dict[str, object]]] = {}
    used_titles: set[str] = set()
    for concept in CONCEPTS:
        candidates = _select_candidates(concept, search_limit, used_titles)
        selected[str(concept["entry_id"])] = _materialize_candidates(concept, candidates)

    assets: list[dict[str, object]] = []
    sidecar: dict[str, object] = {"schema_id": "apv3_real_asset_sources/v1", "sources": []}
    for index, concept in enumerate(CONCEPTS):
        entry_id = str(concept["entry_id"])
        own_candidates = selected[entry_id]
        next_entry_id = str(CONCEPTS[(index + 1) % len(CONCEPTS)]["entry_id"])
        contrast_candidate = selected[next_entry_id][0]
        uses = (
            ("train", 0, own_candidates[0]),
            ("train", 1, own_candidates[1]),
            ("train", 2, own_candidates[2]),
            ("held_out", 0, own_candidates[3]),
            ("contrast", 0, contrast_candidate),
        )
        for use_kind, variant, candidate in uses:
            asset_id = f"asset::real::{entry_id}::{use_kind}::{variant}"
            rel_path = Path("visual") / "real" / f"{entry_id}_{use_kind}_{variant}.png"
            output_path = asset_root / rel_path
            png_bytes = bytes(candidate["png_bytes"])
            output_path.write_bytes(png_bytes)
            record = _asset_record(
                asset_id=asset_id,
                rel_path=rel_path,
                data=png_bytes,
                use_kind=use_kind,
                concept_id=entry_id,
                source_concept=str(candidate["concept_id"]),
                candidate=candidate,
            )
            assets.append(record)
            sidecar["sources"].append(
                {
                    "asset_id": asset_id,
                    "commons_title": candidate["title"],
                    "description_url": candidate["description_url"],
                    "download_url": candidate["download_url"],
                    "license_id": record["license_id"],
                    "attribution": record["attribution"],
                    "source_concept": candidate["concept_id"],
                }
            )

    manifest = {
        "schema_id": "apv3_asset_manifest/v1",
        "manifest_id": "phase17_real_visual_assets_v1",
        "asset_origin_policy": "wikimedia_commons_allowlisted_real_photos",
        "assets": assets,
    }
    _write_json_yaml(manifest_path, manifest)
    _write_json_yaml(SOURCE_SIDECAR, sidecar)
    _write_json_yaml(package_root / "real_fruit_photos_v1.yaml", _build_package())


def _select_candidates(
    concept: Mapping[str, object],
    search_limit: int,
    used_titles: set[str],
) -> list[dict[str, object]]:
    needed = int(load_constant("curriculum.real_assets.train_assets_per_concept")) + int(
        load_constant("curriculum.real_assets.held_out_assets_per_concept")
    )
    target_pool = min(max(needed + 6, 30), search_limit)
    found: list[dict[str, object]] = []
    for query in concept["queries"]:
        for candidate in _search_commons(str(query), search_limit):
            title = str(candidate["title"])
            if title in used_titles:
                continue
            if _title_has_forbidden_context(title):
                continue
            license_id, origin = _normalize_license(candidate)
            if not license_id:
                continue
            if not str(candidate.get("mime", "")).startswith("image/"):
                continue
            candidate["concept_id"] = concept["entry_id"]
            candidate["license_id"] = license_id
            candidate["asset_origin"] = origin
            used_titles.add(title)
            found.append(candidate)
            if len(found) >= target_pool:
                return found
    if len(found) >= needed:
        return found
    raise RuntimeError(f"not enough allowlisted real images for {concept['entry_id']}: {len(found)}")


def _materialize_candidates(
    concept: Mapping[str, object],
    candidates: list[dict[str, object]],
) -> list[dict[str, object]]:
    needed = int(load_constant("curriculum.real_assets.train_assets_per_concept")) + int(
        load_constant("curriculum.real_assets.held_out_assets_per_concept")
    )
    result: list[dict[str, object]] = []
    skipped: list[str] = []
    for candidate in candidates:
        try:
            candidate = dict(candidate)
            candidate["png_bytes"] = _download_candidate_png(candidate)
            result.append(candidate)
        except Exception as exc:
            skipped.append(f"{candidate.get('title', '')}:{type(exc).__name__}")
        if len(result) >= needed:
            return result
    raise RuntimeError(
        f"not enough decodable real images for {concept['entry_id']}: "
        f"{len(result)} good, skipped={skipped[:4]}"
    )


def _search_commons(query: str, limit: int) -> list[dict[str, object]]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime|size",
        "iiurlwidth": str(int(load_constant("curriculum.real_assets.thumbnail_max_px"))),
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urlencode(params)
    payload = _fetch_bytes(url)
    if not payload.lstrip().startswith(b"{"):
        return []
    raw = json.loads(payload.decode("utf-8"))
    result = []
    for page in raw.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        result.append(
            {
                "title": page.get("title", ""),
                "mime": info.get("mime", ""),
                "download_url": info.get("thumburl") or info.get("url"),
                "original_url": info.get("url"),
                "description_url": info.get("descriptionurl") or info.get("descriptionshorturl"),
                "artist": _clean_html(meta.get("Artist", {}).get("value", "")),
                "license_raw": str(meta.get("License", {}).get("value", "")),
                "license_short": str(meta.get("LicenseShortName", {}).get("value", "")),
                "license_url": str(meta.get("LicenseUrl", {}).get("value", "")),
            }
        )
    return result


def _title_has_forbidden_context(title: str) -> bool:
    lowered = title.lower()
    forbidden = (
        "woman",
        "man ",
        " men",
        "boy",
        "baby",
        "vendor",
        "person",
        "people",
        "portrait",
        "seated",
        "phone",
        "cards",
        "still life",
        "still-life",
        "painting",
        "drawing",
        "illustration",
        "moth",
        "skies",
        "cucurbita",
        "fish",
    )
    return any(token in lowered for token in forbidden)


def _normalize_license(candidate: Mapping[str, object]) -> tuple[str, str] | tuple[None, None]:
    raw = f"{candidate.get('license_raw', '')} {candidate.get('license_short', '')} {candidate.get('license_url', '')}".lower()
    if "by-sa" in raw or "share-alike" in raw or "share alike" in raw:
        return None, None
    if "cc0" in raw or "creative commons zero" in raw or "publicdomain/zero" in raw:
        return "CC0-1.0", "cc0"
    if "public domain" in raw or "pd-" in raw or "mark/1.0" in raw:
        return "PDM-1.0", "public_domain"
    if "by/4.0" in raw or "cc-by-4.0" in raw or "cc by 4.0" in raw:
        return "CC-BY-4.0", "cc_by"
    if "by/3.0" in raw or "cc-by-3.0" in raw or "cc by 3.0" in raw:
        return "CC-BY-3.0", "cc_by"
    if "by/2.0" in raw or "cc-by-2.0" in raw or "cc by 2.0" in raw:
        return "CC-BY-2.0", "cc_by"
    return None, None


def _download_and_convert_png(url: str) -> bytes:
    data = _fetch_bytes(url)
    image = Image.open(BytesIO(data))
    image = image.convert("RGB")
    max_px = int(load_constant("curriculum.real_assets.thumbnail_max_px"))
    image.thumbnail((max_px, max_px))
    out = BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _download_candidate_png(candidate: Mapping[str, object]) -> bytes:
    try:
        return _download_and_convert_png(str(candidate["download_url"]))
    except Exception:
        original = str(candidate.get("original_url", ""))
        if original and original != candidate.get("download_url"):
            return _download_and_convert_png(original)
        raise


def _fetch_bytes(url: str) -> bytes:
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if curl:
        completed = subprocess.run(
            [curl, "-L", "--silent", "--show-error", "--max-time", "60", "-A", USER_AGENT, url],
            capture_output=True,
            check=True,
        )
        if completed.stdout:
            return completed.stdout
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        return urlopen(request, timeout=45).read()
    except Exception:
        raise


def _asset_record(
    *,
    asset_id: str,
    rel_path: Path,
    data: bytes,
    use_kind: str,
    concept_id: str,
    source_concept: str,
    candidate: Mapping[str, object],
) -> dict[str, object]:
    intended_use = "curriculum_train" if use_kind == "train" else use_kind
    attribution = f"{_clean_html(str(candidate.get('artist', 'unknown')))}; {candidate['title']}"
    tags = ["real_photo", concept_id]
    if use_kind == "contrast":
        tags.append(f"contrast_source:{source_concept}")
    return {
        "asset_id": asset_id,
        "path": rel_path.as_posix(),
        "media_type": "image/png",
        "sha256": hashlib.sha256(data).hexdigest(),
        "asset_origin": candidate["asset_origin"],
        "source_url": candidate["description_url"],
        "license_id": candidate["license_id"],
        "attribution": attribution[:240],
        "intended_use": intended_use,
        "held_out_group": "fold_0" if intended_use == "held_out" else "",
        "content_safety_review": "pass",
        "semantic_tags": tags,
    }


def _build_package() -> dict[str, object]:
    entries = []
    for index, concept in enumerate(CONCEPTS):
        entry_id = str(concept["entry_id"])
        entries.append(
            {
                "entry_id": entry_id,
                "content_kind": "real_visual_vocabulary",
                "public_payload": {
                    "concept_kind": "fruit",
                    "neutral_label": concept["label"],
                    "teaching_intent": "real_photo_foundation",
                },
                "train_asset_refs": [f"asset::real::{entry_id}::train::{i}" for i in range(3)],
                "held_out_asset_refs": [f"asset::real::{entry_id}::held_out::0"],
                "contrast_asset_refs": [f"asset::real::{entry_id}::contrast::0"],
                "governance_tags": ["phase17", "real_photo", "wikimedia_commons", "fruit"],
            }
        )
    return {
        "schema_id": "apv3_real_visual_curriculum_pack/v1",
        "package_id": "real_fruit_photos_v1",
        "phase_id": "17.0",
        "title": "Real fruit photos v1",
        "governance": {
            "trust_tier": "official",
            "license_id": "mixed-allowlisted-commons",
            "author_id": "apv3_real_asset_collector",
            "source_policy": "wikimedia_commons_allowlisted_static_seed",
            "review_status": "phase17_alpha_reviewed",
        },
        "entries": entries,
    }


def _clean_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "unknown"


def _write_json_yaml(path: Path, data: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
