from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class APV3PersistenceConfig:
    runtime_db_path: Path
    audit_db_path: Path
    budget_bytes: int = 10 * 1024 * 1024 * 1024
    forgetting_enabled: bool = True
    audit_budget_fraction: float = 0.25
    prune_batch: int = 256

