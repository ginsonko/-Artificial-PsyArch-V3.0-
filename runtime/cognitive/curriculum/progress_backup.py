from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from runtime.cognitive.state_pool.state_pool import load_constant


@dataclass(frozen=True)
class CurriculumProgressBackup:
    schema_version: int
    accepted_packages: tuple[str, ...]
    rejected_packages: tuple[str, ...]
    capability_tags: tuple[str, ...]


def build_progress_backup(state: Mapping[str, object]) -> CurriculumProgressBackup:
    """@op_count: O(installed_packages)."""
    installs = [item for item in state.get("curriculum_installs", []) if isinstance(item, Mapping)]
    accepted = tuple(str(item.get("package_id", "")) for item in installs if item.get("accepted"))
    rejected = tuple(str(item.get("package_id", "")) for item in installs if not item.get("accepted"))
    tags = tuple(str(item) for item in state.get("curriculum_capability_tags", ()) if str(item))
    return CurriculumProgressBackup(
        schema_version=int(load_constant("curriculum.substrate.progress_backup_schema_version")),
        accepted_packages=accepted,
        rejected_packages=rejected,
        capability_tags=tuple(sorted(set(tags))),
    )

