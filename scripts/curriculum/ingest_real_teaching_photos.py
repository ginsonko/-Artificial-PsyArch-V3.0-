#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.cognitive.curriculum.asset_governance import ALLOWED_LICENSES
from runtime.cognitive.percept_vector.phase19_runtime import VisualTeachingExample, populate_visual_vectors
from runtime.cognitive.state_pool.state_pool import load_constant


DEFAULT_CANDIDATE_ROOT = Path("config/curriculum/assets/visual/real_teaching_candidates")
DEFAULT_CURATED_ROOT = Path("config/curriculum/assets/visual/real_teaching")
DEFAULT_CURATION_JSON = DEFAULT_CANDIDATE_ROOT / "curation.json"
DEFAULT_VECTOR_ROOT = Path("data/phase19_8_real_teaching_vectors")
DEFAULT_MANIFEST = Path("config/curriculum/assets/visual/real_teaching_manifest.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", default=str(DEFAULT_CANDIDATE_ROOT))
    parser.add_argument("--curation-json", default=str(DEFAULT_CURATION_JSON))
    parser.add_argument("--curated-dir", default=str(DEFAULT_CURATED_ROOT))
    parser.add_argument("--vector-root", default=str(DEFAULT_VECTOR_ROOT))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    args = parser.parse_args()

    result = ingest_curated_photos(
        candidate_root=Path(args.candidate_root),
        curation_json=Path(args.curation_json),
        curated_dir=Path(args.curated_dir),
        vector_root=Path(args.vector_root),
        manifest_path=Path(args.manifest),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def ingest_curated_photos(
    *,
    candidate_root: Path,
    curation_json: Path,
    curated_dir: Path,
    vector_root: Path,
    manifest_path: Path,
) -> dict[str, object]:
    records = load_kept_records(candidate_root, curation_json)
    if not records:
        raise RuntimeError("no kept records in curation json")
    curated_dir.mkdir(parents=True, exist_ok=True)
    manifest_records: list[dict[str, object]] = []
    skipped_concepts: list[dict[str, object]] = []
    train_examples: list[VisualTeachingExample] = []
    tick = 19800
    for concept, own_records in sorted(group_by_concept(records).items()):
        sorted_records = sorted(own_records, key=lambda item: str(item["sha256"]))
        min_keep = int(load_constant("curriculum.real_assets.teaching_curated_min_per_concept"))
        if len(sorted_records) < min_keep:
            skipped_concepts.append({"concept": concept, "kept_count": len(sorted_records), "reason": "below_min_keep"})
            continue
        train_count = max(1, int(len(sorted_records) * int(load_constant("curriculum.real_assets.teaching_train_ratio_percent")) / 100))
        for index, record in enumerate(sorted_records):
            split = "train" if index < train_count else "held_out"
            src = Path(str(record["path"]))
            dst_dir = curated_dir / concept / split
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst = dst_dir / f"{record['candidate_id']}.png"
            shutil.copyfile(src, dst)
            copied_hash = sha256_file(dst)
            if copied_hash != record["sha256"]:
                raise RuntimeError(f"{record['candidate_id']}: sha mismatch after copy")
            manifest_records.append(
                {
                    "schema_id": "apv3_real_teaching_asset/v1",
                    "candidate_id": record["candidate_id"],
                    "concept": concept,
                    "split": split,
                    "path": dst.as_posix(),
                    "sha256": copied_hash,
                    "license_id": record["license_id"],
                    "source_url": record["source_url"],
                    "author": record.get("author", ""),
                    "source": record.get("source", ""),
                    "teacher_label_source": "human_curated_visible_label",
                    "used_filename_label": False,
                }
            )
            if split == "train":
                train_examples.append(VisualTeachingExample(dst, concept, "real_teaching_train", tick))
                tick += 1
    vector_result = populate_visual_vectors(tuple(train_examples), root=vector_root)
    manifest = {
        "schema_id": "apv3_real_teaching_manifest/v1",
        "curation_schema_id": "apv3_real_teaching_curation/v1",
        "records": manifest_records,
        "vector_root": vector_root.as_posix(),
        "layer1_count": vector_result.metadata["layer1_count"],
        "layer2_count": vector_result.metadata["layer2_count"],
        "layer3_count": vector_result.metadata["layer3_count"],
        "skipped_concepts": skipped_concepts,
        "boundary": "Held-out files are copied for audit but are not used to populate training vectors.",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "curated_count": len(manifest_records),
        "train_count": sum(1 for item in manifest_records if item["split"] == "train"),
        "held_out_count": sum(1 for item in manifest_records if item["split"] == "held_out"),
        "layer1_count": vector_result.metadata["layer1_count"],
        "skipped_concepts": skipped_concepts,
        "manifest": manifest_path.as_posix(),
    }


def load_kept_records(candidate_root: Path, curation_json: Path) -> list[dict[str, object]]:
    curation = json.loads(curation_json.read_text(encoding="utf-8"))
    if curation.get("schema_id") != "apv3_real_teaching_curation/v1":
        raise ValueError("unsupported curation schema")
    status_by_id = {str(item["candidate_id"]): str(item["status"]) for item in curation.get("records", [])}
    seen_ids: set[str] = set()
    kept: list[dict[str, object]] = []
    for sidecar in sorted(candidate_root.glob("*/*.json")):
        record = json.loads(sidecar.read_text(encoding="utf-8"))
        if record.get("schema_id") != "apv3_real_teaching_candidate/v1":
            continue
        candidate_id = str(record["candidate_id"])
        if candidate_id in seen_ids:
            continue
        seen_ids.add(candidate_id)
        if status_by_id.get(candidate_id, "drop") != "keep":
            continue
        if record.get("license_id") not in ALLOWED_LICENSES or record.get("license_id") == "LicenseRef-APV3-Synthetic-Generated":
            raise ValueError(f"{record.get('candidate_id')}: unsupported real teaching license")
        kept.append(record)
    return kept


def group_by_concept(records: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for record in records:
        grouped.setdefault(str(record["concept"]), []).append(record)
    return grouped


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    main()
