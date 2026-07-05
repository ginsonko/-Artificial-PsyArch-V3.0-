from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from runtime.cognitive.state_pool.state_pool import load_constant


ALLOWED_LICENSES = {
    "LicenseRef-APV3-Synthetic-Generated",
    "CC0-1.0",
    "CC-BY-2.0",
    "CC-BY-3.0",
    "CC-BY-4.0",
    "PDM-1.0",
}
ALLOWED_ASSET_ORIGINS = {
    "generated_local",
    "public_domain",
    "cc0",
    "cc_by",
}
ALLOWED_INTENDED_USES = {
    "curriculum_train",
    "held_out",
    "contrast",
    "anti_example",
}
PRIVATE_PAYLOAD_FIELDS = {
    "answer",
    "target_class",
    "event_id",
    "private_handle",
    "context_tag",
    "style_tag",
}


@dataclass(frozen=True)
class CurriculumAssetRecord:
    asset_id: str
    path: str
    media_type: str
    sha256: str
    asset_origin: str
    source_url: str
    license_id: str
    attribution: str
    intended_use: str
    held_out_group: str
    content_safety_review: str
    semantic_tags: tuple[str, ...]


@dataclass(frozen=True)
class CurriculumAssetManifest:
    schema_id: str
    manifest_id: str
    assets: tuple[CurriculumAssetRecord, ...]


@dataclass(frozen=True)
class AssetManifestTrace:
    manifest_id: str
    accepted: bool
    reasons: tuple[str, ...]
    asset_count: int
    visual_count: int
    audio_count: int
    train_count: int
    held_out_count: int
    contrast_count: int


@dataclass(frozen=True)
class NeutralPackTrace:
    accepted: bool
    reasons: tuple[str, ...]
    package_count: int
    entry_count: int
    train_ref_count: int
    held_out_ref_count: int
    contrast_ref_count: int


def load_asset_manifest_file(path: str | Path) -> CurriculumAssetManifest:
    """@op_count: O(file_size + assets)."""
    raw = _load_mapping_file(path)
    assets = tuple(_asset_record(item) for item in _sequence(raw.get("assets")))
    return CurriculumAssetManifest(
        schema_id=str(raw.get("schema_id", "")),
        manifest_id=str(raw.get("manifest_id", "")),
        assets=assets,
    )


def validate_asset_manifest(manifest: CurriculumAssetManifest, root_dir: str | Path) -> AssetManifestTrace:
    """@op_count: O(assets * file_size)."""
    reasons: list[str] = []
    if manifest.schema_id != "apv3_asset_manifest/v1":
        reasons.append("unsupported_asset_manifest_schema")
    if not manifest.manifest_id:
        reasons.append("missing_manifest_id")
    if len(manifest.assets) < _manifest_asset_floor(manifest):
        reasons.append("asset_count_below_phase14_floor")

    seen: set[str] = set()
    root = Path(root_dir)
    visual_count = audio_count = train_count = held_out_count = contrast_count = 0
    for record in manifest.assets:
        if not record.asset_id:
            reasons.append("missing_asset_id")
            continue
        if record.asset_id in seen:
            reasons.append(f"{record.asset_id}:duplicate_asset_id")
        seen.add(record.asset_id)

        if record.license_id not in ALLOWED_LICENSES:
            reasons.append(f"{record.asset_id}:unsupported_license")
        if record.asset_origin not in ALLOWED_ASSET_ORIGINS:
            reasons.append(f"{record.asset_id}:unsupported_asset_origin")
        if record.intended_use not in ALLOWED_INTENDED_USES:
            reasons.append(f"{record.asset_id}:unsupported_intended_use")
        if record.content_safety_review != "pass":
            reasons.append(f"{record.asset_id}:content_safety_not_pass")
        if not record.source_url:
            reasons.append(f"{record.asset_id}:missing_source_url")
        if record.asset_origin == "generated_local" and not record.source_url.startswith("script://"):
            reasons.append(f"{record.asset_id}:generated_asset_source_not_script")
        if len(record.sha256) != int(load_constant("curriculum.asset.hash_hex_length")):
            reasons.append(f"{record.asset_id}:invalid_sha256_length")

        asset_path = Path(record.path)
        if asset_path.is_absolute() or ".." in asset_path.parts:
            reasons.append(f"{record.asset_id}:asset_path_not_manifest_relative")
            continue
        full_path = root / asset_path
        if not full_path.exists():
            reasons.append(f"{record.asset_id}:asset_file_missing")
            continue
        data = full_path.read_bytes()
        expected_hash = _sha256(data)
        if expected_hash != record.sha256:
            reasons.append(f"{record.asset_id}:sha256_mismatch")
        if record.media_type == "image/png":
            visual_count += 1
            if len(data) < int(load_constant("curriculum.asset.min_visual_asset_bytes")):
                reasons.append(f"{record.asset_id}:visual_asset_too_small")
        elif record.media_type == "audio/wav":
            audio_count += 1
            if len(data) < int(load_constant("curriculum.asset.min_audio_asset_bytes")):
                reasons.append(f"{record.asset_id}:audio_asset_too_small")
        else:
            reasons.append(f"{record.asset_id}:unsupported_media_type")

        if record.intended_use == "curriculum_train":
            train_count += 1
        elif record.intended_use == "held_out":
            held_out_count += 1
            if not record.held_out_group:
                reasons.append(f"{record.asset_id}:held_out_missing_group")
        elif record.intended_use in {"contrast", "anti_example"}:
            contrast_count += 1

    return AssetManifestTrace(
        manifest_id=manifest.manifest_id,
        accepted=not reasons,
        reasons=tuple(reasons),
        asset_count=len(manifest.assets),
        visual_count=visual_count,
        audio_count=audio_count,
        train_count=train_count,
        held_out_count=held_out_count,
        contrast_count=contrast_count,
    )


def _manifest_asset_floor(manifest: CurriculumAssetManifest) -> int:
    """@op_count: O(1)."""
    if manifest.manifest_id.startswith("phase17_real_visual_assets"):
        return int(load_constant("curriculum.real_assets.min_real_visual_assets"))
    if manifest.manifest_id.startswith("phase18_clean_concept_cards"):
        return int(load_constant("curriculum.clean_cards.min_clean_card_assets"))
    return int(load_constant("curriculum.asset.min_manifest_assets"))


def load_neutral_curriculum_pack_file(path: str | Path) -> Mapping[str, object]:
    """@op_count: O(file_size)."""
    return _load_mapping_file(path)


def validate_neutral_curriculum_packs(
    manifest: CurriculumAssetManifest,
    packages: Sequence[Mapping[str, object]],
) -> NeutralPackTrace:
    """@op_count: O(packages * entries * asset_refs)."""
    reasons: list[str] = []
    if len(packages) < int(load_constant("curriculum.asset.min_packages")):
        reasons.append("package_count_below_phase14_floor")
    asset_by_id = {record.asset_id: record for record in manifest.assets}
    entry_count = train_ref_count = held_out_ref_count = contrast_ref_count = 0

    for package in packages:
        package_id = str(package.get("package_id", ""))
        if package.get("schema_id") != "apv3_neutral_curriculum_pack/v1":
            reasons.append(f"{package_id}:unsupported_neutral_pack_schema")
        governance = _mapping(package.get("governance"))
        if str(governance.get("license_id", "")) not in ALLOWED_LICENSES:
            reasons.append(f"{package_id}:unsupported_pack_license")
        entries = tuple(_mapping(item) for item in _sequence(package.get("entries")))
        if len(entries) < int(load_constant("curriculum.asset.min_entries_per_package")):
            reasons.append(f"{package_id}:entry_count_below_floor")
        for entry in entries:
            entry_count += 1
            entry_id = str(entry.get("entry_id", ""))
            public_payload = _mapping(entry.get("public_payload"))
            if PRIVATE_PAYLOAD_FIELDS & set(public_payload):
                reasons.append(f"{entry_id}:private_field_in_public_payload")
            media_type = "audio/wav" if str(entry.get("content_kind", "")) == "audio_pattern" else "image/png"
            train_refs = _string_tuple(entry.get("train_asset_refs"))
            held_out_refs = _string_tuple(entry.get("held_out_asset_refs"))
            contrast_refs = _string_tuple(entry.get("contrast_asset_refs"))
            train_ref_count += len(train_refs)
            held_out_ref_count += len(held_out_refs)
            contrast_ref_count += len(contrast_refs)
            if len(train_refs) < int(load_constant("curriculum.asset.min_train_assets_per_entry")):
                reasons.append(f"{entry_id}:not_enough_train_assets")
            if len(held_out_refs) < int(load_constant("curriculum.asset.min_held_out_assets_per_entry")):
                reasons.append(f"{entry_id}:not_enough_held_out_assets")
            if len(contrast_refs) < int(load_constant("curriculum.asset.min_contrast_assets_per_entry")):
                reasons.append(f"{entry_id}:not_enough_contrast_assets")
            if set(train_refs) & set(held_out_refs):
                reasons.append(f"{entry_id}:held_out_asset_leaked_into_train_refs")
            _check_refs(entry_id, train_refs, "curriculum_train", media_type, asset_by_id, reasons)
            _check_refs(entry_id, held_out_refs, "held_out", media_type, asset_by_id, reasons)
            _check_refs(entry_id, contrast_refs, "contrast", media_type, asset_by_id, reasons)

    return NeutralPackTrace(
        accepted=not reasons,
        reasons=tuple(reasons),
        package_count=len(packages),
        entry_count=entry_count,
        train_ref_count=train_ref_count,
        held_out_ref_count=held_out_ref_count,
        contrast_ref_count=contrast_ref_count,
    )


def phase14_asset_summary(manifest: CurriculumAssetManifest) -> dict[str, int]:
    """@op_count: O(assets)."""
    visual = sum(1 for record in manifest.assets if record.media_type == "image/png")
    audio = sum(1 for record in manifest.assets if record.media_type == "audio/wav")
    train = sum(1 for record in manifest.assets if record.intended_use == "curriculum_train")
    held_out = sum(1 for record in manifest.assets if record.intended_use == "held_out")
    contrast = sum(1 for record in manifest.assets if record.intended_use in {"contrast", "anti_example"})
    return {
        "assets": len(manifest.assets),
        "visual": visual,
        "audio": audio,
        "train": train,
        "held_out": held_out,
        "contrast": contrast,
    }


def _check_refs(
    entry_id: str,
    refs: Sequence[str],
    expected_use: str,
    expected_media_type: str,
    asset_by_id: Mapping[str, CurriculumAssetRecord],
    reasons: list[str],
) -> None:
    for ref in refs:
        record = asset_by_id.get(ref)
        if record is None:
            reasons.append(f"{entry_id}:{ref}:asset_ref_missing")
            continue
        if record.media_type != expected_media_type:
            reasons.append(f"{entry_id}:{ref}:media_type_mismatch")
        if expected_use == "contrast":
            if record.intended_use not in {"contrast", "anti_example"}:
                reasons.append(f"{entry_id}:{ref}:asset_use_not_contrast")
        elif record.intended_use != expected_use:
            reasons.append(f"{entry_id}:{ref}:asset_use_mismatch")


def _asset_record(raw: object) -> CurriculumAssetRecord:
    if not isinstance(raw, Mapping):
        raise ValueError("asset record must be a mapping")
    record = CurriculumAssetRecord(
        asset_id=str(raw.get("asset_id", "")),
        path=str(raw.get("path", "")),
        media_type=str(raw.get("media_type", "")),
        sha256=str(raw.get("sha256", "")),
        asset_origin=str(raw.get("asset_origin", "")),
        source_url=str(raw.get("source_url", "")),
        license_id=str(raw.get("license_id", "")),
        attribution=str(raw.get("attribution", "")),
        intended_use=str(raw.get("intended_use", "")),
        held_out_group=str(raw.get("held_out_group", "")),
        content_safety_review=str(raw.get("content_safety_review", "")),
        semantic_tags=_string_tuple(raw.get("semantic_tags")),
    )
    return record


def _load_mapping_file(path: str | Path) -> Mapping[str, object]:
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml

        raw = yaml.safe_load(text)
    except Exception:
        raw = json.loads(text)
    if not isinstance(raw, Mapping):
        raise ValueError("file must contain a mapping")
    return raw


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[object]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    return ()


def _string_tuple(value: object) -> tuple[str, ...]:
    return tuple(str(item) for item in _sequence(value) if str(item))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
