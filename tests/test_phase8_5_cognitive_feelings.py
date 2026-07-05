from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.cognitive_feelings.factory import build_cognitive_feelings
from runtime.cognitive.cognitive_feelings.epistemic_source_feelings import (
    marker_energy_signal,
)
from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StateItem


def _item(sa_id: str) -> StateItem:
    item = StateItem(
        sa_id=sa_id,
        family="percept",
        label=sa_id,
        real_energy=0.8,
        virtual_energy=0.6,
        attention_energy=0.7,
        cognitive_pressure=0.2,
        fatigue=0.1,
    )
    return item


def _marker(kind: str, target: str, energy: float = 0.8) -> MarkerEvent:
    return MarkerEvent(tick=1, kind=kind, target_sa_id=target, real_energy=energy)


def test_epistemic_feelings_separate_real_and_imagined_source_continuously() -> None:
    real_item = _item("sa::seen")
    real_item.gain_ledger.inject("external", 1.0)
    imagined_item = _item("sa::imagined")
    imagined_item.gain_ledger.inject("imagination", 1.0)

    real = build_cognitive_feelings(real_item, (_marker("PERCEIVED", real_item.sa_id),))
    imagined = build_cognitive_feelings(
        imagined_item,
        (_marker("IMAGINED", imagined_item.sa_id),),
    )

    assert real.epistemic.values["reality_sense"] > real.epistemic.values["imagination_sense"]
    assert imagined.epistemic.values["imagination_sense"] > imagined.epistemic.values["reality_sense"]
    assert 0.0 < marker_energy_signal((_marker("PERCEIVED", real_item.sa_id),), "PERCEIVED") < 1.0


def test_hearsay_guess_and_incongruity_are_trace_values_not_routes() -> None:
    item = _item("sa::claim")
    item.gain_ledger.inject("external", 0.5)
    item.metadata["low_grasp_score"] = 0.8
    item.metadata["candidate_entropy"] = 0.7
    item.metadata["prediction_mismatch"] = 0.9

    snapshot = build_cognitive_feelings(
        item,
        (
            _marker("HEARSAY", item.sa_id),
            _marker("CORRECTION", item.sa_id, energy=0.7),
        ),
    )

    assert snapshot.epistemic.values["hearsay_sense"] > 0.0
    assert snapshot.epistemic.values["guess_sense"] > 0.0
    assert snapshot.epistemic.values["incongruity"] > 0.0
    assert set(snapshot.core) == {"fluency", "boredom", "fulfillment", "satisfaction"}


def test_cognitive_feelings_export_as_packet_values() -> None:
    item = _item("sa::packet")
    item.gain_ledger.inject("feedback", 1.0)
    packet_values = build_cognitive_feelings(
        item,
        (_marker("PERCEIVED", item.sa_id),),
    ).to_packet_feelings()

    keys = {value.key for value in packet_values}
    assert {"fluency", "satisfaction", "reality_sense", "imagination_sense"} <= keys


def test_phase8_5_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "8.5"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 8.5 deliverables present" in completed.stdout
