from __future__ import annotations

from runtime.cognitive.correction.natural_correction import (
    apply_natural_correction_credit,
    reward_packet_action,
)
from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.sdpl.packet import FeelingValue, make_packet
from runtime.cognitive.sdpl.q_table_backoff import QTableWithBackoff
from runtime.cognitive.state_pool.state_pool import StateItem


def _item(sa_id: str) -> StateItem:
    return StateItem(sa_id=sa_id, family="percept", label=sa_id, real_energy=0.8)


def _marker(kind: str, target: str, tick: int = 1) -> MarkerEvent:
    return MarkerEvent(tick=tick, kind=kind, target_sa_id=target, real_energy=1.0)


def test_natural_correction_penalizes_packet_action_without_erasing_real_packet() -> None:
    content = (_item("sa::cup"),)
    perceived = make_packet(
        content_sas=content,
        source_markers=(_marker("PERCEIVED", "sa::cup"),),
        feeling_sas=(FeelingValue("reality_sense", 0.9),),
    )
    imagined = make_packet(
        content_sas=content,
        source_markers=(_marker("IMAGINED", "sa::cup"),),
        feeling_sas=(FeelingValue("imagination_sense", 0.9),),
    )
    q_table = QTableWithBackoff()

    for _ in range(6):
        reward_packet_action(q_table, perceived, "reach")
        apply_natural_correction_credit(
            q_table,
            imagined,
            "reach",
            _marker("CORRECTION", "sa::cup", tick=3),
            action_tick=2,
        )

    assert q_table.query(perceived, "reach") > 0.0
    assert q_table.query(imagined, "reach") < 0.0


def test_two_stage_credit_assignment_decays_with_delay() -> None:
    packet = make_packet(content_sas=(_item("sa::late"),))
    q_table = QTableWithBackoff()

    near = apply_natural_correction_credit(
        q_table,
        packet,
        "commit",
        _marker("CORRECTION", "sa::late", tick=2),
        action_tick=1,
    )
    far = apply_natural_correction_credit(
        q_table,
        packet,
        "commit",
        _marker("CORRECTION", "sa::late", tick=60),
        action_tick=1,
    )

    assert near.eligibility > far.eligibility
    assert near.total_outcome < far.total_outcome
