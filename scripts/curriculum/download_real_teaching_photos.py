#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
from io import BytesIO
from pathlib import Path
import sys
from typing import Iterable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.cognitive.curriculum.asset_governance import ALLOWED_LICENSES
from runtime.cognitive.state_pool.state_pool import load_constant


USER_AGENT = "APV3test-real-teaching-library/0.1 (local research prototype)"
OUTPUT_ROOT = Path("config/curriculum/assets/visual/real_teaching_candidates")
ALLOWED_REAL_LICENSES = tuple(sorted(ALLOWED_LICENSES - {"LicenseRef-APV3-Synthetic-Generated"}))
DEFAULT_CONCEPTS: dict[str, tuple[str, ...]] = {
    "apple": ("apple fruit photo", "red apple fruit"),
    "banana": ("banana fruit photo", "ripe banana"),
    "orange": ("orange fruit photo", "citrus orange fruit"),
    "strawberry": ("strawberry fruit photo",),
    "grape": ("grape fruit photo",),
    "book": ("book object photo",),
    "cup": ("cup object photo",),
    "chair": ("chair object photo",),
    "table": ("table furniture photo",),
    "key": ("key object photo",),
    "phone": ("mobile phone object photo",),
    "computer": ("computer object photo",),
    "cat": ("cat animal photo",),
    "dog": ("dog animal photo",),
    "bird": ("bird animal photo",),
    "fish": ("fish animal photo",),
    "bread": ("bread food photo",),
    "rice": ("rice food photo",),
    "egg": ("egg food photo",),
    "cake": ("cake food photo",),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concepts", nargs="*", default=("apple", "banana", "orange"))
    parser.add_argument("--per-concept", type=int, default=int(load_constant("curriculum.real_assets.teaching_candidate_target_per_concept")))
    parser.add_argument("--output-dir", default=str(OUTPUT_ROOT))
    parser.add_argument("--sources", nargs="*", default=("commons", "openverse"))
    parser.add_argument("--fixture-source", default="")
    parser.add_argument("--max-file-size-mb", type=int, default=int(load_constant("curriculum.real_assets.teaching_max_file_size_mb")))
    parser.add_argument("--min-resolution", type=int, default=int(load_constant("curriculum.real_assets.teaching_min_resolution_px")))
    args = parser.parse_args()

    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    if args.fixture_source:
        records = build_fixture_candidates(Path(args.fixture_source), out_root, args.concepts, args.per_concept)
    else:
        records = download_candidates(
            concepts=args.concepts,
            per_concept=args.per_concept,
            out_root=out_root,
            sources=tuple(args.sources),
            max_file_size_mb=args.max_file_size_mb,
            min_resolution=args.min_resolution,
        )
    write_index(out_root, records)
    print(json.dumps({"candidate_count": len(records), "output_dir": out_root.as_posix()}, ensure_ascii=False))


def download_candidates(
    *,
    concepts: Iterable[str],
    per_concept: int,
    out_root: Path,
    sources: tuple[str, ...],
    max_file_size_mb: int,
    min_resolution: int,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for concept in concepts:
        queries = DEFAULT_CONCEPTS.get(concept, (f"{concept} photo",))
        concept_records: list[dict[str, object]] = []
        seen_urls: set[str] = set()
        for query in queries:
            for source in sources:
                for candidate in search_source(source, query, limit=max(per_concept, 10)):
                    if len(concept_records) >= per_concept:
                        break
                    if str(candidate["source_url"]) in seen_urls:
                        continue
                    seen_urls.add(str(candidate["source_url"]))
                    if not license_allowed(str(candidate["license_id"])):
                        continue
                    try:
                        record = materialize_candidate(
                            concept=concept,
                            candidate=candidate,
                            out_root=out_root,
                            max_file_size_mb=max_file_size_mb,
                            min_resolution=min_resolution,
                        )
                    except Exception:
                        record = None
                    if record is not None:
                        concept_records.append(record)
                        records.append(record)
                if len(concept_records) >= per_concept:
                    break
            if len(concept_records) >= per_concept:
                break
        if not concept_records:
            raise RuntimeError(f"no allowlisted candidates downloaded for {concept}")
        if len(concept_records) < per_concept:
            print(json.dumps({"warning": "concept_below_target", "concept": concept, "count": len(concept_records), "target": per_concept}, ensure_ascii=False))
    return records


def search_source(source: str, query: str, *, limit: int) -> list[dict[str, object]]:
    if source == "commons":
        return search_wikimedia_commons(query, limit=limit)
    if source == "openverse":
        return search_openverse(query, limit=limit)
    raise ValueError(f"unsupported source {source}; use commons/openverse")


def search_wikimedia_commons(query: str, *, limit: int) -> list[dict[str, object]]:
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
    raw = fetch_json("https://commons.wikimedia.org/w/api.php?" + urlencode(params))
    items: list[dict[str, object]] = []
    for page in raw.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        license_id = normalize_license(
            " ".join(
                str(meta.get(key, {}).get("value", ""))
                for key in ("License", "LicenseShortName", "LicenseUrl")
            )
        )
        if not license_id:
            continue
        items.append(
            {
                "source": "wikimedia_commons",
                "source_url": info.get("descriptionurl") or info.get("descriptionshorturl") or info.get("url"),
                "download_url": info.get("thumburl") or info.get("url"),
                "license_id": license_id,
                "author": strip_html(str(meta.get("Artist", {}).get("value", ""))),
                "title": page.get("title", ""),
            }
        )
    return items


def search_openverse(query: str, *, limit: int) -> list[dict[str, object]]:
    params = {
        "q": query,
        "page_size": str(min(limit, 20)),
        "license": "cc0,pdm,by",
    }
    raw = fetch_json("https://api.openverse.org/v1/images/?" + urlencode(params))
    items: list[dict[str, object]] = []
    for item in raw.get("results", []):
        license_id = normalize_license(f"{item.get('license', '')} {item.get('license_version', '')}")
        if not license_id:
            continue
        items.append(
            {
                "source": "openverse",
                "source_url": item.get("foreign_landing_url") or item.get("url"),
                "download_url": item.get("thumbnail") or item.get("url"),
                "license_id": license_id,
                "author": item.get("creator") or "",
                "title": item.get("title") or "",
            }
        )
    return items


def materialize_candidate(
    *,
    concept: str,
    candidate: Mapping[str, object],
    out_root: Path,
    max_file_size_mb: int,
    min_resolution: int,
) -> dict[str, object] | None:
    payload = fetch_bytes(str(candidate["download_url"]), max_bytes=max_file_size_mb * 1024 * 1024)
    image = Image.open(BytesIO(payload)).convert("RGB")
    if image.width < min_resolution or image.height < min_resolution:
        return None
    image.thumbnail((int(load_constant("curriculum.real_assets.thumbnail_max_px")), int(load_constant("curriculum.real_assets.thumbnail_max_px"))), Image.Resampling.LANCZOS)
    png_io = BytesIO()
    image.save(png_io, format="PNG")
    data = png_io.getvalue()
    sha = hashlib.sha256(data).hexdigest()
    candidate_id = f"cand_{sha[:16]}"
    concept_dir = out_root / concept
    concept_dir.mkdir(parents=True, exist_ok=True)
    image_path = concept_dir / f"{candidate_id}.png"
    sidecar_path = concept_dir / f"{candidate_id}.json"
    image_path.write_bytes(data)
    record = {
        "schema_id": "apv3_real_teaching_candidate/v1",
        "candidate_id": candidate_id,
        "concept": concept,
        "path": image_path.as_posix(),
        "sha256": sha,
        "source": candidate["source"],
        "source_url": candidate["source_url"],
        "download_url": candidate["download_url"],
        "license_id": candidate["license_id"],
        "author": candidate.get("author", ""),
        "title": candidate.get("title", ""),
        "curation_status": "keep",
        "content_safety_review": "pending_human",
    }
    sidecar_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def build_fixture_candidates(
    fixture_source: Path,
    out_root: Path,
    concepts: Iterable[str],
    per_concept: int,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    source_images = sorted(path for path in fixture_source.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    for concept in concepts:
        concept_images = [path for path in source_images if concept.lower() in path.stem.lower()]
        for path in concept_images[:per_concept]:
            data = path.read_bytes()
            image = Image.open(BytesIO(data)).convert("RGB")
            image.thumbnail((int(load_constant("curriculum.real_assets.thumbnail_max_px")), int(load_constant("curriculum.real_assets.thumbnail_max_px"))), Image.Resampling.LANCZOS)
            png_io = BytesIO()
            image.save(png_io, format="PNG")
            sha = hashlib.sha256(png_io.getvalue()).hexdigest()
            candidate = {
                "source": "fixture_local",
                "source_url": "fixture://" + path.name,
                "download_url": "fixture://" + path.name,
                "license_id": "CC0-1.0",
                "author": "fixture",
                "title": path.name,
            }
            record = materialize_bytes(concept, candidate, png_io.getvalue(), out_root, sha)
            records.append(record)
    return records


def materialize_bytes(concept: str, candidate: Mapping[str, object], data: bytes, out_root: Path, sha: str) -> dict[str, object]:
    candidate_id = f"cand_{sha[:16]}"
    concept_dir = out_root / concept
    concept_dir.mkdir(parents=True, exist_ok=True)
    image_path = concept_dir / f"{candidate_id}.png"
    sidecar_path = concept_dir / f"{candidate_id}.json"
    image_path.write_bytes(data)
    record = {
        "schema_id": "apv3_real_teaching_candidate/v1",
        "candidate_id": candidate_id,
        "concept": concept,
        "path": image_path.as_posix(),
        "sha256": sha,
        "source": candidate["source"],
        "source_url": candidate["source_url"],
        "download_url": candidate["download_url"],
        "license_id": candidate["license_id"],
        "author": candidate.get("author", ""),
        "title": candidate.get("title", ""),
        "curation_status": "keep",
        "content_safety_review": "pending_human",
    }
    sidecar_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def write_index(out_root: Path, records: list[dict[str, object]]) -> None:
    (out_root / "index.json").write_text(
        json.dumps(
            {
                "schema_id": "apv3_real_teaching_candidates_index/v1",
                "generated_at_unix": int(time.time()),
                "allowed_license_ids": list(ALLOWED_REAL_LICENSES),
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def license_allowed(license_id: str) -> bool:
    return license_id in ALLOWED_REAL_LICENSES


def normalize_license(raw: str) -> str | None:
    text = raw.lower().replace("_", "-")
    if "by-sa" in text or "nc" in text or "nd" in text or "sampling" in text:
        return None
    if "public domain" in text or "pdm" in text or "mark" in text:
        return "PDM-1.0"
    if "cc0" in text or "zero" in text:
        return "CC0-1.0"
    if "cc-by-4" in text or ("by" in text and "4.0" in text):
        return "CC-BY-4.0"
    if "cc-by-3" in text or ("by" in text and "3.0" in text):
        return "CC-BY-3.0"
    if "cc-by-2" in text or ("by" in text and "2.0" in text):
        return "CC-BY-2.0"
    if text.strip() in {"by", "cc by"}:
        return "CC-BY-4.0"
    return None


def fetch_json(url: str) -> dict[str, object]:
    text = fetch_bytes(url).decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text, strict=False)


def fetch_bytes(url: str, *, max_bytes: int | None = None) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(int(load_constant("curriculum.real_assets.teaching_retry_count"))):
        try:
            with urlopen(request, timeout=20) as response:
                data = response.read(max_bytes + 1) if max_bytes else response.read()
            if max_bytes and len(data) > max_bytes:
                raise ValueError("download_exceeds_max_bytes")
            return data
        except Exception:
            if attempt + 1 >= int(load_constant("curriculum.real_assets.teaching_retry_count")):
                raise
            time.sleep(0.5 + attempt)
    raise RuntimeError("unreachable")


def strip_html(value: str) -> str:
    out = []
    keep = True
    for char in value:
        if char == "<":
            keep = False
        elif char == ">":
            keep = True
        elif keep:
            out.append(char)
    return "".join(out).strip()


if __name__ == "__main__":
    main()
