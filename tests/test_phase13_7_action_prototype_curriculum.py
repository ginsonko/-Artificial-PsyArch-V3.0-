from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.curriculum.action_social import ActionPrototype, select_action_prototype
from runtime.cognitive.sdpl.packet import make_packet
from runtime.cognitive.sdpl.q_table_backoff import QTableWithBackoff
from runtime.cognitive.state_pool.state_pool import StateItem


def test_phase13_7_action_prototype_selection_uses_sdpl_q_not_keyword_route() -> None:
    item = StateItem(sa_id="sa::feedback", family="control", label="feedback", real_energy=0.8)
    packet = make_packet(content_sas=(item,))
    q_table = QTableWithBackoff()
    q_table.update(packet, "action::accept_feedback", outcome=1.0)
    q_table.update(packet, "action::ignore_feedback", outcome=-1.0)
    trace = select_action_prototype(
        packet,
        q_table,
        (
            ActionPrototype("action::accept_feedback", "reward"),
            ActionPrototype("action::ignore_feedback", "none"),
        ),
    )

    assert trace.action_id == "action::accept_feedback"
    assert trace.score > 0.0


def test_phase13_7_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "13.7"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr

