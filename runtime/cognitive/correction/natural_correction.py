from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.sdpl.packet import LearningPacket
from runtime.cognitive.sdpl.q_table_backoff import QTableWithBackoff
from runtime.cognitive.state_pool.state_pool import load_constant


@dataclass(frozen=True)
class CorrectionCreditResult:
    action: str
    immediate_outcome: float
    delayed_outcome: float
    total_outcome: float
    eligibility: float


def apply_natural_correction_credit(
    q_table: QTableWithBackoff,
    packet: LearningPacket,
    action: str,
    correction_marker: MarkerEvent,
    *,
    action_tick: int,
) -> CorrectionCreditResult:
    """@op_count: O(backoff_layers)."""
    delay = max(0, int(correction_marker.tick) - int(action_tick))
    eligibility = _temporal_eligibility(delay)
    immediate = -float(correction_marker.real_energy)
    delayed = immediate * eligibility
    total = immediate + delayed
    q_table.update(packet, action, outcome=total, eligibility=eligibility)
    return CorrectionCreditResult(
        action=action,
        immediate_outcome=immediate,
        delayed_outcome=delayed,
        total_outcome=total,
        eligibility=eligibility,
    )


def reward_packet_action(
    q_table: QTableWithBackoff,
    packet: LearningPacket,
    action: str,
    *,
    amount: float = 1.0,
) -> None:
    """@op_count: O(backoff_layers)."""
    q_table.update(packet, action, outcome=float(amount), eligibility=1.0)


def _temporal_eligibility(delay_ticks: int) -> float:
    timeout = float(load_constant("credit_assignment.phase_2_timeout_ticks"))
    return max(0.0, 1.0 - (float(delay_ticks) / max(timeout, 1.0)))
