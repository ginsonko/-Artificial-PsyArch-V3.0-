from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.reward.handler import apply_punishment, apply_reward
from runtime.cognitive.runtime.audit_db_boundary import (
    cognitive_payload_access_allowed,
    make_render_only_reference,
)
from runtime.cognitive.runtime.tick_loop import ContinuousTickRuntime
from runtime.cognitive.state_pool.state_pool import StatePool
from runtime.cognitive.state_pool.target_cap import compute_real_evidence_cap
from runtime.cognitive.state_pool.v_double_control import apply_v_double_control
from runtime.cognitive.text_understanding.proposition_emit import emit_proposition_and_hearsay
from runtime.sensor_adapters.text.char_stream import TextCharStream


def test_tick_loop_spawns_perceived_marker_and_records_external_ledger() -> None:
    result = ContinuousTickRuntime().run_text_message("你", start_tick=1, utterance_id="u-perceived")

    char_item = result.state_pool.get("text_char::你")
    marker_item = result.state_pool.get("marker::PERCEIVED::text_char::你")

    assert char_item is not None
    assert marker_item is not None
    assert char_item.gain_ledger.gain_by_source["external"] > 0.0
    assert marker_item.gain_ledger.gain_by_source["external"] > 0.0
    assert marker_item.metadata["target_sa_id"] == "text_char::你"


def test_hearsay_spawns_only_from_proposition_layer_not_text_char_layer() -> None:
    events = TextCharStream().events_from_text("你好", start_tick=3, utterance_id="u-hearsay")
    emitted = emit_proposition_and_hearsay(events, speaker_entity_id="speaker::user")

    assert emitted is not None
    proposition, marker = emitted
    assert proposition.sa_id == "proposition::u-hearsay"
    assert proposition.text == "你好"
    assert marker.kind == "HEARSAY"
    assert marker.target_sa_id == proposition.sa_id
    assert marker.metadata["source_entity_id"] == "speaker::user"


def test_punishment_spawns_correction_marker_through_feedback_handler() -> None:
    state_pool = StatePool()
    result = ContinuousTickRuntime(state_pool=state_pool).run_text_message("错", start_tick=5)
    target_id = "text_char::错"
    before = result.state_pool.get(target_id)

    assert before is not None
    feedback = apply_punishment(result.state_pool, target_sa_id=target_id, tick=6)
    correction = result.state_pool.get(f"marker::CORRECTION::{target_id}")

    assert feedback.marker is not None
    assert feedback.marker.kind == "CORRECTION"
    assert correction is not None
    assert correction.gain_ledger.gain_by_source["feedback"] > 0.0


def test_reward_updates_feedback_ledger_without_correction_marker() -> None:
    result = ContinuousTickRuntime().run_text_message("对", start_tick=7)
    target_id = "text_char::对"

    feedback = apply_reward(result.state_pool, target_sa_id=target_id, tick=8)
    item = result.state_pool.get(target_id)

    assert feedback.marker is None
    assert item is not None
    assert item.gain_ledger.gain_by_source["feedback"] > 0.0
    assert result.state_pool.get(f"marker::CORRECTION::{target_id}") is None


def test_target_cap_zero_floor_and_v_double_control_split_memory_support() -> None:
    result = ContinuousTickRuntime().run_text_message("忆", start_tick=9, idle_ticks_after=1)
    item = result.state_pool.get("text_char::忆")

    assert item is not None
    assert compute_real_evidence_cap(item, tick=9) > 0.0
    assert compute_real_evidence_cap(item, tick=10) == 0.0

    item.metadata["long_term_layer"] = True
    item.metadata["long_term_R"] = item.real_energy
    floor, cap = apply_v_double_control(item, tick=10, cue_alignment=1.0)

    assert cap == 0.0
    assert floor > 0.0
    assert item.virtual_energy >= floor


def test_render_boundary_never_allows_cognitive_payload_access() -> None:
    reference = make_render_only_reference("payload::recent-frame")

    assert reference.payload_id == "payload::recent-frame"
    assert cognitive_payload_access_allowed(reference) is False


def test_phase8_3_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "8.3"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 8.3 deliverables present" in completed.stdout
