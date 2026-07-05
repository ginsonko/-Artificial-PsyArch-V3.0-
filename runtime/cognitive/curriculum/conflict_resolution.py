from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from runtime.cognitive.marker.events import MarkerEvent


class CorrectionStatus(str, Enum):
    SYSTEM_COMMIT_REJECTED = "system_commit_rejected"
    PENDING_PERCEIVED_REVALIDATION = "pending_perceived_revalidation"


@dataclass(frozen=True)
class ConflictResolution:
    status: str
    correction_marker_id: str
    target_sa_id: str


def spawn_pending_perceived_revalidation(*, target_sa_id: str, tick: int, energy: float) -> ConflictResolution:
    """@op_count: O(1)."""
    marker = MarkerEvent(
        tick=int(tick),
        kind="CORRECTION",
        target_sa_id=str(target_sa_id),
        real_energy=float(energy),
        metadata={
            "status": CorrectionStatus.PENDING_PERCEIVED_REVALIDATION.value,
            "target_sa_id": str(target_sa_id),
            "ledger_source": "external",
        },
    )
    return ConflictResolution(
        status=CorrectionStatus.PENDING_PERCEIVED_REVALIDATION.value,
        correction_marker_id=marker.sa_id,
        target_sa_id=str(target_sa_id),
    )
