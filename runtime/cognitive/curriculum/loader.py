from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from runtime.cognitive.curriculum.package_schema import (
    CurriculumPackage,
    CurriculumValidationTrace,
    load_curriculum_package,
    package_capability_tags,
    validate_curriculum_package,
)


@dataclass(frozen=True)
class CurriculumInstallTrace:
    package_id: str
    phase_id: str
    accepted: bool
    reasons: tuple[str, ...]
    capability_tags: tuple[str, ...]


def load_curriculum_package_file(path: str | Path) -> CurriculumPackage:
    """@op_count: O(file_size + entries)."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError("curriculum package file must contain an object")
    return load_curriculum_package(raw)


def install_curriculum_package(state: Mapping[str, object], package: CurriculumPackage) -> dict[str, object]:
    """@op_count: O(entries + installed_packages)."""
    trace = _trace_from_validation(validate_curriculum_package(package), package)
    next_state = dict(state)
    rows = [dict(item) for item in next_state.get("curriculum_installs", []) if isinstance(item, Mapping)]
    rows.append(
        {
            "schema_id": "apv3_curriculum_install_trace/v1",
            "package_id": trace.package_id,
            "phase_id": trace.phase_id,
            "accepted": trace.accepted,
            "reasons": list(trace.reasons),
            "capability_tags": list(trace.capability_tags),
        }
    )
    next_state["curriculum_installs"] = rows
    if trace.accepted:
        active = set(next_state.get("curriculum_capability_tags", ()))
        active.update(trace.capability_tags)
        next_state["curriculum_capability_tags"] = sorted(active)
    return next_state


def _trace_from_validation(
    validation: CurriculumValidationTrace,
    package: CurriculumPackage,
) -> CurriculumInstallTrace:
    """@op_count: O(entries)."""
    return CurriculumInstallTrace(
        package_id=package.package_id,
        phase_id=package.phase_id,
        accepted=validation.accepted,
        reasons=validation.reasons,
        capability_tags=package_capability_tags(package) if validation.accepted else (),
    )

