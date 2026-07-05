from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.composed_vocab.delta_p_cold_fork import (
    VocabCandidate,
    evaluate_delta_p_incremental,
)
from runtime.cognitive.composed_vocab.held_out_pool import HeldOutPool
from runtime.cognitive.composed_vocab.sparse_pairwise import SparsePairwiseGraph
from runtime.cognitive.endogenous.imagined_marker_spawn import spawn_imagined
from runtime.cognitive.long_term.rehydration import spawn_remembered
from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.sdpl.packet import FeelingValue, make_packet
from runtime.cognitive.sdpl.q_table_backoff import QTableWithBackoff
from runtime.cognitive.state_pool.state_pool import StateItem


def _item(sa_id: str, *, pressure: float = 0.4, real: float = 0.8) -> StateItem:
    return StateItem(
        sa_id=sa_id,
        family="percept",
        label=sa_id,
        real_energy=real,
        cognitive_pressure=pressure,
    )


def _marker(kind: str, target: str, energy: float = 0.8) -> MarkerEvent:
    return MarkerEvent(tick=1, kind=kind, target_sa_id=target, real_energy=energy)


def test_packet_key_keeps_same_content_separate_by_epistemic_source() -> None:
    content = (_item("sa::apple"),)
    perceived = make_packet(
        content_sas=content,
        source_markers=(_marker("PERCEIVED", "sa::apple"),),
        feeling_sas=(FeelingValue("reality_sense", 0.9),),
    )
    imagined = make_packet(
        content_sas=content,
        source_markers=(_marker("IMAGINED", "sa::apple"),),
        feeling_sas=(FeelingValue("imagination_sense", 0.9),),
    )

    assert perceived.content_key() == imagined.content_key()
    assert perceived.source_key() != imagined.source_key()
    assert perceived.packet_key() != imagined.packet_key()


def test_q_backoff_penalizes_imagined_packet_without_erasing_perceived_packet() -> None:
    content = (_item("sa::door"),)
    perceived = make_packet(
        content_sas=content,
        source_markers=(_marker("PERCEIVED", "sa::door"),),
        feeling_sas=(FeelingValue("reality_sense", 0.9),),
    )
    imagined = make_packet(
        content_sas=content,
        source_markers=(_marker("IMAGINED", "sa::door"),),
        feeling_sas=(FeelingValue("imagination_sense", 0.9),),
    )
    q_table = QTableWithBackoff()

    for _ in range(6):
        q_table.update(perceived, "touch", outcome=1.0)
        q_table.update(imagined, "touch", outcome=-1.0)

    assert q_table.query(perceived, "touch") > 0.0
    assert q_table.query(imagined, "touch") < 0.0


def test_sparse_pairwise_graph_records_cooccurrence_under_packet_key() -> None:
    packet = make_packet(
        content_sas=(_item("sa::yellow"), _item("sa::apple"), _item("sa::table")),
        source_markers=(_marker("PERCEIVED", "scene"),),
    )
    graph = SparsePairwiseGraph()

    graph.observe_packet(packet)
    graph.observe_packet(packet)

    assert graph.pair_count("sa::apple", "sa::yellow") == 2.0
    assert graph.top_partners("sa::apple")[0][1] == 2.0


def test_held_out_delta_p_requires_pool_then_promotes_only_value_adding_candidate() -> None:
    current = (_item("sa::yellow"), _item("sa::apple"))
    held_out = HeldOutPool()
    candidate = VocabCandidate(
        candidate_id="vocab::yellow_apple",
        component_ids=("sa::yellow", "sa::apple"),
        predicted_pressure_reduction=0.2,
    )

    too_early = evaluate_delta_p_incremental(candidate, current, held_out)
    assert too_early.passes is False
    assert too_early.reason == "insufficient_held_out"

    for index in range(50):
        held_out.add_items(f"s::{index}", (_item("sa::yellow"), _item("sa::apple")))

    accepted = evaluate_delta_p_incremental(candidate, current, held_out)
    rejected = evaluate_delta_p_incremental(
        VocabCandidate(
            candidate_id="vocab::noise",
            component_ids=("sa::unrelated",),
            predicted_pressure_reduction=0.2,
        ),
        current,
        held_out,
    )

    assert accepted.passes is True
    assert accepted.mean_delta_p > 0.0
    assert rejected.passes is False
    assert rejected.mean_delta_p == 0.0


def test_imagined_and_remembered_marker_spawn_from_energy_provenance() -> None:
    item = _item("sa::inner_scene")
    item.gain_ledger.inject("imagination", 0.8)
    item.gain_ledger.inject("external", 0.2)
    imagined = spawn_imagined(item, tick=4)
    item.metadata["long_term_R"] = 0.8
    remembered = spawn_remembered(item, tick=5, cue_alignment=0.5)

    assert imagined is not None
    assert imagined.kind == "IMAGINED"
    assert remembered.kind == "REMEMBERED"
    assert remembered.target_sa_id == item.sa_id


def test_phase8_4_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "8.4"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 8.4 deliverables present" in completed.stdout
