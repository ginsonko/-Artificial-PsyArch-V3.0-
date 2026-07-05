from __future__ import annotations

from runtime.cognitive.attention.safety_gate import convex_attention_score
from runtime.cognitive.cognitive_feelings.factory import build_cognitive_feelings
from runtime.cognitive.correction.natural_correction import apply_natural_correction_credit
from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.sdpl.packet import FeelingValue, make_packet
from runtime.cognitive.sdpl.q_table_backoff import QTableWithBackoff
from runtime.cognitive.state_pool.state_pool import StateItem


def _item(sa_id: str) -> StateItem:
    return StateItem(
        sa_id=sa_id,
        family="percept",
        label=sa_id,
        real_energy=0.8,
        attention_energy=0.4,
        cognitive_pressure=0.4,
    )


def _marker(kind: str, target: str, tick: int = 1) -> MarkerEvent:
    return MarkerEvent(tick=tick, kind=kind, target_sa_id=target, real_energy=0.9)


def _packet(kind: str, feeling_key: str) -> object:
    content = (_item("sa::shared_content"),)
    return make_packet(
        content_sas=content,
        source_markers=(_marker(kind, "sa::shared_content"),),
        feeling_sas=(FeelingValue(feeling_key, 0.9),),
    )


def test_gate_imagination_adds_learning_evidence_without_needing_external_replay() -> None:
    perceived = _packet("PERCEIVED", "reality_sense")
    imagined = _packet("IMAGINED", "imagination_sense")
    external_only = QTableWithBackoff()
    mixed = QTableWithBackoff()

    for _ in range(3):
        external_only.update(perceived, "inspect", outcome=1.0)
        mixed.update(perceived, "inspect", outcome=1.0)
        mixed.update(imagined, "inspect", outcome=1.0)

    assert mixed.action_global_q["inspect"].sample_count > external_only.action_global_q["inspect"].sample_count
    assert mixed.query(perceived, "inspect") > 0.0


def test_gate_humanlike_imagined_mistake_learns_without_erasing_real_packet() -> None:
    perceived = _packet("PERCEIVED", "reality_sense")
    imagined = _packet("IMAGINED", "imagination_sense")
    q_table = QTableWithBackoff()

    for _ in range(6):
        q_table.update(perceived, "act", outcome=1.0)
        apply_natural_correction_credit(
            q_table,
            imagined,
            "act",
            _marker("CORRECTION", "sa::shared_content", tick=3),
            action_tick=2,
        )

    assert q_table.query(perceived, "act") > 0.0
    assert q_table.query(imagined, "act") < 0.0


def test_gate_external_surprise_pull_focus_back_from_imagination() -> None:
    item = _item("sa::surprise")
    item.gain_ledger.inject("imagination", 1.0)
    item.gain_ledger.inject("external", 4.0)
    item.cognitive_pressure = 0.9

    trace = convex_attention_score(item)

    assert trace.safety_gate_triggered is True
    assert trace.score == trace.external_score


def test_gate_source_feelings_distinguish_reality_and_imagination() -> None:
    real = _item("sa::real")
    real.gain_ledger.inject("external", 1.0)
    imagined = _item("sa::imagined")
    imagined.gain_ledger.inject("imagination", 1.0)

    real_feelings = build_cognitive_feelings(real, (_marker("PERCEIVED", real.sa_id),))
    imagined_feelings = build_cognitive_feelings(imagined, (_marker("IMAGINED", imagined.sa_id),))

    assert real_feelings.epistemic.values["reality_sense"] > real_feelings.epistemic.values["imagination_sense"]
    assert imagined_feelings.epistemic.values["imagination_sense"] > imagined_feelings.epistemic.values["reality_sense"]
