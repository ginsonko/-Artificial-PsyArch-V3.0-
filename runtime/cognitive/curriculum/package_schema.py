from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class CurriculumGovernance:
    trust_tier: str
    license_id: str
    author_id: str
    source_policy: str
    review_status: str


@dataclass(frozen=True)
class CurriculumEntry:
    entry_id: str
    content_kind: str
    public_payload: Mapping[str, object]
    governance_tags: tuple[str, ...]
    held_out: bool = False


@dataclass(frozen=True)
class CurriculumPackage:
    schema_id: str
    package_id: str
    phase_id: str
    title: str
    governance: CurriculumGovernance
    entries: tuple[CurriculumEntry, ...]


@dataclass(frozen=True)
class CurriculumValidationTrace:
    package_id: str
    phase_id: str
    accepted: bool
    reasons: tuple[str, ...]
    entry_count: int


def load_curriculum_package(raw: Mapping[str, object]) -> CurriculumPackage:
    """@op_count: O(entries)."""
    governance = _governance(_mapping(raw.get("governance")))
    entries = tuple(_entry(item) for item in _sequence(raw.get("entries")))
    return CurriculumPackage(
        schema_id=str(raw.get("schema_id", "")),
        package_id=str(raw.get("package_id", "")),
        phase_id=str(raw.get("phase_id", "")),
        title=str(raw.get("title", "")),
        governance=governance,
        entries=entries,
    )


def validate_curriculum_package(package: CurriculumPackage) -> CurriculumValidationTrace:
    """@op_count: O(entries)."""
    reasons: list[str] = []
    if package.schema_id not in (
        "apv3_curriculum_package/v1",
        "apv3_styled_curriculum_pack/v1",
        "apv3_real_visual_curriculum_pack/v1",
        "apv3_clean_card_curriculum_pack/v1",
    ):
        reasons.append("unsupported_schema")
    if not package.package_id:
        reasons.append("missing_package_id")
    if not (
        package.phase_id.startswith("13.")
        or package.phase_id.startswith("16.")
        or package.phase_id.startswith("17.")
        or package.phase_id.startswith("18.")
    ):
        reasons.append("phase_must_be_13_x_or_16_x_or_17_x")
    if package.governance.source_policy == "runtime_llm":
        reasons.append("runtime_llm_source_forbidden")
    if not package.governance.license_id or not package.governance.author_id:
        reasons.append("missing_license_or_author")
    for entry in package.entries:
        if not entry.entry_id:
            reasons.append("missing_entry_id")
        if not entry.governance_tags:
            reasons.append(f"{entry.entry_id}:missing_governance_tags")
        if _payload_has_private_fields(entry.public_payload):
            reasons.append(f"{entry.entry_id}:private_field_in_public_payload")
    return CurriculumValidationTrace(
        package_id=package.package_id,
        phase_id=package.phase_id,
        accepted=not reasons,
        reasons=tuple(reasons),
        entry_count=len(package.entries),
    )


def package_capability_tags(package: CurriculumPackage) -> tuple[str, ...]:
    """@op_count: O(entries)."""
    tags = {entry.content_kind for entry in package.entries}
    tags.update(tag for entry in package.entries for tag in entry.governance_tags)
    return tuple(sorted(tags))


def _governance(raw: Mapping[str, object]) -> CurriculumGovernance:
    """@op_count: O(1)."""
    return CurriculumGovernance(
        trust_tier=str(raw.get("trust_tier", "")),
        license_id=str(raw.get("license_id", "")),
        author_id=str(raw.get("author_id", "")),
        source_policy=str(raw.get("source_policy", "")),
        review_status=str(raw.get("review_status", "")),
    )


def _entry(raw: object) -> CurriculumEntry:
    """@op_count: O(tags)."""
    if not isinstance(raw, Mapping):
        raise ValueError("curriculum entry must be a mapping")
    return CurriculumEntry(
        entry_id=str(raw.get("entry_id", "")),
        content_kind=str(raw.get("content_kind", "")),
        public_payload=_mapping(raw.get("public_payload")),
        governance_tags=tuple(str(item) for item in _sequence(raw.get("governance_tags"))),
        held_out=bool(raw.get("held_out", False)),
    )


def _payload_has_private_fields(payload: Mapping[str, object]) -> bool:
    """@op_count: O(payload_keys)."""
    private = {"answer", "event_id", "private_handle", "target_class", "style_tag", "context_tag"}
    return bool(private & set(payload))


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[object]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    return ()
