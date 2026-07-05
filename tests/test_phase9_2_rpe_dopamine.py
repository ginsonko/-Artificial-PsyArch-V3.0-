from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.reward.rpe import apply_rpe_learning
from runtime.cognitive.sdpl.packet import make_packet
from runtime.cognitive.sdpl.q_table_backoff import QTableWithBackoff
from runtime.cognitive.state_pool.state_pool import StateItem


def _item(sa_id: str) -> StateItem:
    return StateItem(sa_id=sa_id, family="drive", label=sa_id, real_energy=0.8)


def _packet() -> object:
    return make_packet(
        content_sas=(_item("EntitySA::drive::curiosity"),),
        source_markers=(MarkerEvent(tick=1, kind="PERCEIVED", target_sa_id="scene", real_energy=0.9),),
    )


def test_positive_rpe_creates_dopamine_burst_and_raises_q() -> None:
    q_table = QTableWithBackoff()
    packet = _packet()
    target = _item("EntitySA::drive::curiosity")

    trace = apply_rpe_learning(
        q_table,
        packet,
        "drive_action::inspect",
        actual_reward=1.0,
        target_item=target,
    )

    assert trace.predicted_reward == 0.0
    assert trace.rpe > 0.0
    assert trace.dopamine_delta > 0.0
    assert q_table.query(packet, "drive_action::inspect") > 0.0
    assert target.gain_ledger.gain_by_source["rpe_signal"] > 0.0


def test_negative_rpe_dips_without_erasing_positive_packet_history() -> None:
    q_table = QTableWithBackoff()
    packet = _packet()
    for _ in range(6):
        apply_rpe_learning(q_table, packet, "drive_action::inspect", actual_reward=1.0)
    before = q_table.query(packet, "drive_action::inspect")

    trace = apply_rpe_learning(q_table, packet, "drive_action::inspect", actual_reward=0.0)
    after = q_table.query(packet, "drive_action::inspect")

    assert before > 0.0
    assert trace.rpe < 0.0
    assert trace.dopamine_delta < 0.0
    assert after < before
    assert after > 0.0


def test_surprising_outcome_has_higher_learning_eligibility_than_predicted_outcome() -> None:
    q_table = QTableWithBackoff()
    packet = _packet()

    surprise = apply_rpe_learning(q_table, packet, "drive_action::try", actual_reward=1.0)
    predicted = apply_rpe_learning(q_table, packet, "drive_action::try", actual_reward=1.0)

    assert surprise.learning_eligibility > predicted.learning_eligibility


def test_phase9_2_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "9.2"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 9.2 deliverables present" in completed.stdout
