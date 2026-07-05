from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from .models import Phase207TurnResult, RuntimeTickEventV2


CSTAR_MIN_ERROR_FORMULA_ID = "apv3_phase20_8h_cstar_min_error/v1"
PHASE20_9A_LEARNING_PROTOCOL_PROJECTION_ID = "apv3_phase20_9a_six_stage_learning_protocol_projection/v1"
PHASE20_9C_LEARNING_LOOP_METRICS_ID = "apv3_phase20_9c_learning_loop_metrics/v1"
LEARNING_PROTOCOL_PHASES = (
    "demonstrate",
    "strong_scaffold",
    "weak_scaffold",
    "feedback_only",
    "teacher_off",
    "cold_retest",
)


def complete_turn_cognitive_cycle(result: Phase207TurnResult) -> Phase207TurnResult:
    if result.stage_id == "20.7-stage0":
        return result
    return replace(
        result,
        tick_trace=tuple(complete_every_tick_cognitive_cycle(event) for event in result.tick_trace),
    )


def complete_every_tick_cognitive_cycle(event: RuntimeTickEventV2) -> RuntimeTickEventV2:
    # no_write_reason is a perception label, not a reason to skip cognition
    b_candidates = tuple(event.b_candidates)
    tick_evidence_b = _weak_b_candidate(event)
    default_forward = _default_c_forward(event, b_candidates, tick_evidence_b)
    c_forward = tuple(event.c_forward)
    if not c_forward:
        c_forward = (default_forward,)
    elif not any(row.get("kind") == "every_tick_forward_prediction" for row in c_forward):
        c_forward = c_forward + (default_forward,)
    default_backward = _default_c_backward(event, b_candidates, tick_evidence_b)
    c_backward = tuple(event.c_backward)
    if not c_backward:
        c_backward = (default_backward,)
    elif not _has_unified_statistics_cause(c_backward):
        c_backward = c_backward + (default_backward,)
    cstar = dict(event.cstar_packet)
    if not cstar:
        cstar = _default_cstar_packet(event, b_candidates, tick_evidence_b, c_forward, c_backward)
    else:
        cstar = {
            "kind": cstar.get("kind", "every_tick_min_error_cycle"),
            "completed_by": cstar.get("completed_by", "phase20_8b_every_tick_cycle"),
            **cstar,
        }
        cstar.setdefault("unified_candidate_statistics", tick_evidence_b["unified_candidate_statistics"])
    cstar = _integrate_cstar_packet(
        event,
        cstar,
        b_candidates=b_candidates,
        tick_evidence_b=tick_evidence_b,
        c_forward=c_forward,
        c_backward=c_backward,
    )
    feelings = {
        "every_tick_cycle_completed": True,
        "cstar_min_error_integrated": True,
        **dict(event.feelings),
    }
    learning_deltas = _with_learning_protocol_projection(
        event,
        b_candidates=b_candidates,
        c_forward=c_forward,
        c_backward=c_backward,
        cstar_packet=cstar,
    )
    learning_deltas = _with_learning_loop_metrics(
        event,
        learning_deltas=learning_deltas,
        b_candidates=b_candidates,
        c_forward=c_forward,
        c_backward=c_backward,
        cstar_packet=cstar,
    )
    return replace(
        event,
        b_candidates=b_candidates,
        c_forward=c_forward,
        c_backward=c_backward,
        cstar_packet=cstar,
        feelings=feelings,
        learning_deltas=learning_deltas,
    )


def _with_learning_protocol_projection(
    event: RuntimeTickEventV2,
    *,
    b_candidates: tuple[dict[str, Any], ...],
    c_forward: tuple[dict[str, Any], ...],
    c_backward: tuple[dict[str, Any], ...],
    cstar_packet: dict[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    existing = tuple(event.learning_deltas)
    if any(
        isinstance(delta, Mapping)
        and delta.get("delta_kind") == "learning_protocol_projection"
        and delta.get("formula_id") == PHASE20_9A_LEARNING_PROTOCOL_PROJECTION_ID
        for delta in existing
    ):
        return existing
    return existing + (
        _learning_protocol_projection(
            event,
            b_candidates=b_candidates,
            c_forward=c_forward,
            c_backward=c_backward,
            cstar_packet=cstar_packet,
        ),
    )


def _learning_protocol_projection(
    event: RuntimeTickEventV2,
    *,
    b_candidates: tuple[dict[str, Any], ...],
    c_forward: tuple[dict[str, Any], ...],
    c_backward: tuple[dict[str, Any], ...],
    cstar_packet: dict[str, Any],
) -> dict[str, Any]:
    action = str(event.selected_action.get("action_type") or "unknown")
    teacher_signal = _teacher_signal(event)
    request_signal = _request_scaffold_signal(event)
    receptor_signal = 1.0 if event.receptor_outputs or event.external_inputs else 0.0
    b_support = _unit(_b_support(b_candidates, _weak_b_candidate(event)))
    structural_signal = 1.0 if any(candidate.get("kind") == "structural_b" for candidate in b_candidates) else 0.0
    exact_signal = 1.0 if any(candidate.get("kind") == "exact_b0" for candidate in b_candidates) else 0.0
    cstar_grasp = _unit(cstar_packet.get("grasp", 0.0))
    candidate_stats = cstar_packet.get("unified_candidate_statistics")
    candidate_count = 0
    if isinstance(candidate_stats, Mapping):
        try:
            candidate_count = int(candidate_stats.get("candidate_count", 0) or 0)
        except (TypeError, ValueError):
            candidate_count = 0
    teacher_absent = teacher_signal <= 0.0
    teacher_off_signal = 1.0 if teacher_absent and b_candidates and action not in {"request_teacher", "maintain_unclosed"} else 0.0
    weak_memory_signal = 1.0 if teacher_absent and (structural_signal > 0.0 or candidate_count > 0) else 0.0
    sensory_action = action in {
        "observe_text",
        "move_focus",
        "maintain_focus",
        "audio_audit_sensor",
        "idle_visual_focus",
        "idle_audio_focus",
        "visual_imagination_recall",
    }
    scores = {
        "demonstrate": _unit((0.50 if sensory_action else 0.0) + receptor_signal * 0.32 + (0.10 if c_forward else 0.0)),
        "strong_scaffold": _unit(teacher_signal * 0.70 + (0.18 if action == "integrate_feedback" else 0.0)),
        "weak_scaffold": _unit(request_signal * 0.56 + weak_memory_signal * 0.28 + structural_signal * 0.20),
        "feedback_only": _unit(teacher_signal * 0.38 + (0.22 if _feedback_only_hint(event) else 0.0)),
        "teacher_off": _unit(teacher_off_signal * (0.46 + b_support * 0.34 + cstar_grasp * 0.14 + exact_signal * 0.06)),
        "cold_retest": _unit(teacher_off_signal * _cold_retest_hint(event) * (0.44 + b_support * 0.34)),
    }
    selected_phase = max(LEARNING_PROTOCOL_PHASES, key=lambda phase: scores.get(phase, 0.0))
    selected_score = _unit(scores.get(selected_phase, 0.0))
    if selected_score <= 0.0:
        selected_phase = "demonstrate"
        selected_score = 0.0
    return {
        "delta_kind": "learning_protocol_projection",
        "formula_id": PHASE20_9A_LEARNING_PROTOCOL_PROJECTION_ID,
        "protocol_phases": LEARNING_PROTOCOL_PHASES,
        "current_protocol_stage": selected_phase,
        "stage_index": LEARNING_PROTOCOL_PHASES.index(selected_phase),
        "stage_support": round(selected_score, 4),
        "stage_scores": {phase: round(_unit(scores.get(phase, 0.0)), 4) for phase in LEARNING_PROTOCOL_PHASES},
        "evidence": {
            "selected_action": action,
            "teacher_signal": round(teacher_signal, 4),
            "request_scaffold_signal": round(request_signal, 4),
            "receptor_signal": round(receptor_signal, 4),
            "b_candidate_count": len(b_candidates),
            "b_support": round(b_support, 4),
            "structural_signal": round(structural_signal, 4),
            "exact_signal": round(exact_signal, 4),
            "candidate_count": candidate_count,
            "cstar_grasp": round(cstar_grasp, 4),
            "c_forward_count": len(c_forward),
            "c_backward_count": len(c_backward),
        },
        "projection_only": True,
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
    }


def _with_learning_loop_metrics(
    event: RuntimeTickEventV2,
    *,
    learning_deltas: tuple[Mapping[str, Any], ...],
    b_candidates: tuple[dict[str, Any], ...],
    c_forward: tuple[dict[str, Any], ...],
    c_backward: tuple[dict[str, Any], ...],
    cstar_packet: dict[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    if any(
        isinstance(delta, Mapping)
        and delta.get("delta_kind") == "learning_loop_metrics"
        and delta.get("formula_id") == PHASE20_9C_LEARNING_LOOP_METRICS_ID
        for delta in learning_deltas
    ):
        return learning_deltas
    projection = _learning_protocol_projection_from(learning_deltas)
    if not projection:
        return learning_deltas
    return learning_deltas + (
        _learning_loop_metrics(
            event,
            projection=projection,
            b_candidates=b_candidates,
            c_forward=c_forward,
            c_backward=c_backward,
            cstar_packet=cstar_packet,
        ),
    )


def _learning_protocol_projection_from(learning_deltas: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    for delta in learning_deltas:
        if not isinstance(delta, Mapping):
            continue
        if (
            delta.get("delta_kind") == "learning_protocol_projection"
            and delta.get("formula_id") == PHASE20_9A_LEARNING_PROTOCOL_PROJECTION_ID
        ):
            return dict(delta)
    return {}


def _learning_loop_metrics(
    event: RuntimeTickEventV2,
    *,
    projection: dict[str, Any],
    b_candidates: tuple[dict[str, Any], ...],
    c_forward: tuple[dict[str, Any], ...],
    c_backward: tuple[dict[str, Any], ...],
    cstar_packet: dict[str, Any],
) -> dict[str, Any]:
    evidence = projection.get("evidence") if isinstance(projection.get("evidence"), Mapping) else {}
    scores = projection.get("stage_scores") if isinstance(projection.get("stage_scores"), Mapping) else {}
    action = str(event.selected_action.get("action_type") or evidence.get("selected_action") or "unknown")
    teacher_signal = _unit(evidence.get("teacher_signal", _teacher_signal(event)))
    request_signal = _unit(evidence.get("request_scaffold_signal", _request_scaffold_signal(event)))
    b_support = _unit(evidence.get("b_support", _b_support(b_candidates, _weak_b_candidate(event))))
    exact_signal = _unit(evidence.get("exact_signal", 0.0))
    structural_signal = _unit(evidence.get("structural_signal", 0.0))
    cstar_grasp = _unit(evidence.get("cstar_grasp", cstar_packet.get("grasp", 0.0)))
    candidate_count = _safe_int(evidence.get("candidate_count", 0))
    conflict_entropy = _unit(cstar_packet.get("conflict_entropy", _competition_entropy(event)))
    e_total = _unit(cstar_packet.get("e_total", 1.0 - cstar_grasp))
    feedback_hint = _feedback_only_hint(event)
    cold_hint = _cold_retest_hint(event)
    teacher_absent = teacher_signal <= 0.0
    has_memory = bool(b_candidates) or candidate_count > 0 or structural_signal > 0.0 or exact_signal > 0.0

    feedback_only_readiness = _unit(
        teacher_signal * 0.26
        + feedback_hint * 0.34
        + cstar_grasp * 0.16
        + (1.0 - conflict_entropy) * 0.10
        + min(1.0, len(event.experience_event_ids_written) / 4.0) * 0.14
    )
    if teacher_signal <= 0.0:
        feedback_only_readiness *= 0.35

    teacher_off_readiness = 0.0
    if teacher_absent and has_memory and action not in {"request_teacher", "maintain_unclosed"}:
        teacher_off_readiness = _unit(
            b_support * 0.38
            + cstar_grasp * 0.24
            + exact_signal * 0.18
            + structural_signal * 0.08
            + (1.0 - request_signal) * 0.07
            + (1.0 - conflict_entropy) * 0.05
        )

    cold_retest_readiness = 0.0
    if teacher_absent and has_memory:
        cold_retest_readiness = _unit(teacher_off_readiness * 0.72 + cold_hint * 0.28)

    scaffold_regression_need = _unit(
        (1.0 - b_support) * 0.24
        + (1.0 - cstar_grasp) * 0.28
        + request_signal * 0.24
        + conflict_entropy * 0.12
        + (1.0 if action in {"request_teacher", "maintain_unclosed"} else 0.0) * 0.12
    )
    if teacher_signal > 0.0:
        scaffold_regression_need *= 0.45
    if teacher_off_readiness >= 0.62:
        scaffold_regression_need *= 0.55

    tendencies = {
        "feedback_only": round(feedback_only_readiness, 4),
        "teacher_off_probe": round(teacher_off_readiness, 4),
        "cold_retest_probe": round(cold_retest_readiness, 4),
        "return_to_scaffold": round(scaffold_regression_need, 4),
    }
    dominant_tendency = max(tendencies, key=lambda key: tendencies[key])
    return {
        "delta_kind": "learning_loop_metrics",
        "formula_id": PHASE20_9C_LEARNING_LOOP_METRICS_ID,
        "source_projection_formula_id": PHASE20_9A_LEARNING_PROTOCOL_PROJECTION_ID,
        "current_protocol_stage": projection.get("current_protocol_stage"),
        "stage_scores": {str(key): round(_unit(value), 4) for key, value in scores.items()},
        "feedback_only_readiness": round(feedback_only_readiness, 4),
        "teacher_off_readiness": round(teacher_off_readiness, 4),
        "cold_retest_readiness": round(cold_retest_readiness, 4),
        "scaffold_regression_need": round(scaffold_regression_need, 4),
        "dominant_learning_tendency": dominant_tendency,
        "tendencies": tendencies,
        "evidence": {
            "selected_action": action,
            "teacher_signal": round(teacher_signal, 4),
            "request_scaffold_signal": round(request_signal, 4),
            "b_support": round(b_support, 4),
            "exact_signal": round(exact_signal, 4),
            "structural_signal": round(structural_signal, 4),
            "candidate_count": candidate_count,
            "cstar_grasp": round(cstar_grasp, 4),
            "conflict_entropy": round(conflict_entropy, 4),
            "e_total": round(e_total, 4),
            "feedback_only_hint": round(feedback_hint, 4),
            "cold_retest_hint": round(cold_hint, 4),
            "c_forward_count": len(c_forward),
            "c_backward_count": len(c_backward),
            "has_memory_evidence": has_memory,
        },
        "projection_only": True,
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
    }


def _teacher_signal(event: RuntimeTickEventV2) -> float:
    action = str(event.selected_action.get("action_type") or "")
    score = 1.0 if action == "integrate_feedback" else 0.0
    for ref in event.source_refs:
        if str(ref.get("source_kind") or "") == "teacher_feedback_event":
            score = max(score, 1.0)
    for delta in event.learning_deltas:
        if isinstance(delta, Mapping) and delta.get("delta_kind") == "experience_alignment_written":
            score = max(score, 1.0)
    return _unit(score)


def _request_scaffold_signal(event: RuntimeTickEventV2) -> float:
    action = str(event.selected_action.get("action_type") or "")
    if action in {"request_teacher", "maintain_unclosed"}:
        return 1.0
    for row in event.action_competition:
        if row.get("action_type") in {"request_teacher", "maintain_unclosed"}:
            try:
                return max(0.0, min(1.0, float(row.get("drive", 0.0) or 0.0)))
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _feedback_only_hint(event: RuntimeTickEventV2) -> float:
    for delta in event.learning_deltas:
        if not isinstance(delta, Mapping):
            continue
        if delta.get("delta_kind") != "experience_alignment_written":
            continue
        if delta.get("backward_attribution") or delta.get("recovered_target"):
            return 1.0
    return 0.0


def _cold_retest_hint(event: RuntimeTickEventV2) -> float:
    if event.external_inputs:
        return 0.0
    if event.tick >= 48:
        return 0.35
    return 0.0


def _weak_b_candidate(event: RuntimeTickEventV2) -> dict[str, Any]:
    strongest_state = _strongest_state_item(event)
    selected = dict(event.selected_action)
    drive = _selected_drive(event)
    support = max(
        drive,
        float(strongest_state.get("A", 0.0) or strongest_state.get("attention", 0.0) or 0.0),
        _inner_modality_support(event),
        0.12,
    )
    return {
        "kind": "tick_evidence_b",
        "support": round(min(1.0, support), 4),
        "selected_action": selected.get("action_type"),
        "strongest_state_sa_id": strongest_state.get("sa_id"),
        "receptor_count": len(tuple(event.receptor_outputs)),
        "experience_event_count": len(tuple(event.experience_event_ids_written)),
        "unified_candidate_statistics": _unified_candidate_statistics(
            event,
            b_candidates=tuple(event.b_candidates),
            c_backward=tuple(event.c_backward),
        ),
        "writes_answer_directly": False,
    }


def _has_unified_statistics_cause(c_backward: Sequence[Mapping[str, Any]]) -> bool:
    for row in c_backward:
        cause_slots = row.get("cause_slots", ()) if isinstance(row, Mapping) else ()
        if not isinstance(cause_slots, Sequence) or isinstance(cause_slots, (str, bytes, bytearray)):
            continue
        for slot in cause_slots:
            if isinstance(slot, Mapping) and slot.get("slot_kind") == "unified_candidate_statistics":
                return True
    return False


def _default_c_forward(
    event: RuntimeTickEventV2,
    b_candidates: tuple[dict[str, Any], ...],
    tick_evidence_b: dict[str, Any],
) -> dict[str, Any]:
    action = str(event.selected_action.get("action_type", "unknown"))
    prediction = {
        "move_focus": "continued_sampling_may_raise_visual_clarity",
        "maintain_focus": "continued_sampling_may_stabilize_visual_clarity",
        "idle_visual_focus": "remembered_patch_sampling_may_enrich_inner_picture",
        "visual_imagination_recall": "remembered_visual_patch_may_drive_next_attention",
        "audio_audit_sensor": "audio_trace_may_enter_inner_rehearsal",
        "idle_audio_focus": "inner_audio_trace_decays_or_refocuses",
        "write_cell": "draft_grid_may_gain_next_visible_unit",
        "continue_writing": "successor_pressure_may_keep_draftgrid_writing",
        "read_draft": "self_draftgrid_readback_may_detect_conflict_or_readiness",
        "edit_cell": "local_revision_may_reduce_draft_conflict_when_alternative_exists",
        "commit_reply": "draft_commit_may_close_current_reply_pressure",
        "stop_generating": "pause_or_stop_may_reduce_overrun_when_continue_pressure_is_low",
        "reply_tts_audio": "tts_actuator_may_externalize_committed_reply",
        "integrate_feedback": "teacher_feedback_may_reweight_future_recall",
        "observe_text": "text_occurrences_may_recall_experience_flow",
        "idle_think": "short_structure_flow_may_continue_by_successor_bias",
        "idle_observe": "low_pressure_observation_may_wait_or_decay",
    }.get(action, "current_action_may_change_next_state_pool_energy")
    return {
        "kind": "every_tick_forward_prediction",
        "model": "phase20_8b_common_cycle/v1",
        "selected_action": action,
        "prediction": prediction,
        "support": round(_b_support(b_candidates, tick_evidence_b), 4),
        "subjective": True,
    }


def _default_c_backward(
    event: RuntimeTickEventV2,
    b_candidates: tuple[dict[str, Any], ...],
    tick_evidence_b: dict[str, Any],
) -> dict[str, Any]:
    support = _b_support(b_candidates, tick_evidence_b)
    return {
        "kind": "every_tick_backward_min_error",
        "model": "phase20_8b_common_cycle/v1",
        "selected_source_kind": _selected_source_kind(event),
        "cause_slots": _cause_slots(event)
        + [
            {
                "slot_kind": "unified_candidate_statistics",
                **dict(tick_evidence_b.get("unified_candidate_statistics", {})),
            }
        ],
        "neutralized_occurrences": _neutralized_occurrences(event, support=support),
        "cause_grasp": round(min(1.0, support), 4),
        "e_backward": round(max(0.0, 1.0 - min(1.0, support)), 4),
        "subjective": True,
        "may_be_wrong": True,
    }


def _default_cstar_packet(
    event: RuntimeTickEventV2,
    b_candidates: tuple[dict[str, Any], ...],
    tick_evidence_b: dict[str, Any],
    c_forward: tuple[dict[str, Any], ...],
    c_backward: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    forward_support = max((_support(row) for row in c_forward), default=0.0)
    backward_grasp = max((float(row.get("cause_grasp", row.get("support", 0.0)) or 0.0) for row in c_backward), default=0.0)
    grasp = min(1.0, max(forward_support, backward_grasp, _selected_drive(event)))
    return {
        "kind": "every_tick_min_error_cycle",
        "model": "phase20_8b_common_cycle/v1",
        "completed_by": "phase20_8b_every_tick_cycle",
        "b_candidate_count": len(b_candidates),
        "tick_evidence_b": tick_evidence_b,
        "unified_candidate_statistics": _unified_candidate_statistics(
            event,
            b_candidates=b_candidates,
            c_backward=c_backward,
        ),
        "prediction_count": len(c_forward),
        "attribution_count": len(c_backward),
        "grasp": round(grasp, 4),
        "e_forward": round(max(0.0, 1.0 - forward_support), 4),
        "e_backward": round(max(0.0, 1.0 - backward_grasp), 4),
        "conflict_entropy": round(_competition_entropy(event), 4),
        "writes_answer_directly": False,
    }


def _integrate_cstar_packet(
    event: RuntimeTickEventV2,
    cstar: dict[str, Any],
    *,
    b_candidates: tuple[dict[str, Any], ...],
    tick_evidence_b: dict[str, Any],
    c_forward: tuple[dict[str, Any], ...],
    c_backward: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    stats = _unified_candidate_statistics(event, b_candidates=b_candidates, c_backward=c_backward)
    if not stats["candidate_count"]:
        stats = dict(cstar.get("unified_candidate_statistics") or stats)
    b_support = _unit(_b_support(b_candidates, tick_evidence_b))
    forward_support = _unit(max((_support(row) for row in c_forward), default=0.0))
    backward_grasp = _unit(max((_backward_grasp(row) for row in c_backward), default=0.0))
    candidate_support = _unit(stats.get("max_support", 0.0))
    action_drive = _unit(_selected_drive(event))
    conflict_entropy = _unit(_competition_entropy(event))

    e_forward = 1.0 - forward_support
    e_backward = 1.0 - backward_grasp
    e_b = 1.0 - max(b_support, candidate_support)
    e_action = 1.0 - action_drive
    e_conflict = conflict_entropy
    e_total = (
        e_forward * 0.30
        + e_backward * 0.30
        + e_b * 0.18
        + e_conflict * 0.12
        + e_action * 0.10
    )
    e_total = _unit(e_total)
    grasp = 1.0 - e_total
    cstar_virtual_energy = max(b_support, forward_support, backward_grasp, candidate_support) * (1.0 - 0.35 * conflict_entropy)
    forward_backward_total = forward_support + backward_grasp
    if forward_backward_total <= 0:
        alpha_forward = 0.5
        alpha_backward = 0.5
    else:
        alpha_forward = forward_support / forward_backward_total
        alpha_backward = backward_grasp / forward_backward_total
    integration = {
        "formula_id": CSTAR_MIN_ERROR_FORMULA_ID,
        "b_support": round(b_support, 4),
        "forward_support": round(forward_support, 4),
        "backward_grasp": round(backward_grasp, 4),
        "unified_candidate_support": round(candidate_support, 4),
        "selected_action_drive": round(action_drive, 4),
        "conflict_entropy": round(conflict_entropy, 4),
        "e_forward": round(e_forward, 4),
        "e_backward": round(e_backward, 4),
        "e_b": round(e_b, 4),
        "e_action": round(e_action, 4),
        "e_conflict": round(e_conflict, 4),
        "e_total": round(e_total, 4),
        "grasp": round(grasp, 4),
        "cstar_virtual_energy": round(cstar_virtual_energy, 4),
        "alpha_forward": round(alpha_forward, 4),
        "alpha_backward": round(alpha_backward, 4),
        "writes_answer_directly": False,
    }
    return {
        **cstar,
        "cstar_formula_id": CSTAR_MIN_ERROR_FORMULA_ID,
        "cstar_model": "phase20_8h_unified_min_error_integration/v1",
        "completed_by": "phase20_8h_unified_cstar_min_error",
        "unified_candidate_statistics": stats,
        "cstar_min_error_integration": integration,
        "grasp": integration["grasp"],
        "e_forward": integration["e_forward"],
        "e_backward": integration["e_backward"],
        "e_total": integration["e_total"],
        "conflict_entropy": integration["conflict_entropy"],
        "cstar_virtual_energy": integration["cstar_virtual_energy"],
        "alpha_forward": integration["alpha_forward"],
        "alpha_backward": integration["alpha_backward"],
        "writes_answer_directly": False,
    }


def _b_support(b_candidates: tuple[dict[str, Any], ...], tick_evidence_b: dict[str, Any]) -> float:
    if b_candidates:
        return float(b_candidates[0].get("support", 0.12) or 0.12)
    return float(tick_evidence_b.get("support", 0.12) or 0.12)


def _unified_candidate_statistics(
    event: RuntimeTickEventV2,
    *,
    b_candidates: Sequence[dict[str, Any]] = (),
    c_backward: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    slots = _unified_candidate_slots(b_candidates=b_candidates, c_backward=c_backward or tuple(event.c_backward))
    unique: dict[str, dict[str, Any]] = {}
    for slot in slots:
        candidate_id = str(
            slot.get("candidate_id")
            or slot.get("alignment_event_id")
            or f"{slot.get('candidate_kind', 'candidate')}::{len(unique)}"
        )
        if candidate_id not in unique:
            unique[candidate_id] = slot
            continue
        if _slot_support(slot) > _slot_support(unique[candidate_id]):
            unique[candidate_id] = slot
    values = tuple(unique.values())
    candidate_kinds = sorted({str(slot.get("candidate_kind")) for slot in values if slot.get("candidate_kind")})
    support_formulas = sorted({str(slot.get("support_formula")) for slot in values if slot.get("support_formula")})
    return {
        "candidate_count": len(values),
        "max_support": round(max((_slot_support(slot) for slot in values), default=0.0), 4),
        "candidate_kinds": candidate_kinds,
        "support_formulas": support_formulas,
        "candidate_ids": tuple(unique.keys())[:8],
        "evidence_source": "existing_runtime_tick_audit_slots",
        "creates_candidate": False,
    }


def _unified_candidate_slots(
    *,
    b_candidates: Sequence[dict[str, Any]],
    c_backward: Sequence[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    slots: list[dict[str, Any]] = []
    for candidate in b_candidates:
        if isinstance(candidate, Mapping):
            slots.extend(_slots_from_sequence(candidate.get("candidate_audit_slots", ())))
    for row in c_backward:
        if isinstance(row, Mapping):
            slots.extend(_slots_from_sequence(row.get("cause_slots", ())))
    return tuple(slots)


def _slots_from_sequence(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(
        dict(slot)
        for slot in value
        if isinstance(slot, Mapping) and slot.get("slot_kind") == "unified_experience_candidate"
    )


def _slot_support(slot: Mapping[str, Any]) -> float:
    try:
        return max(0.0, min(1.0, float(slot.get("support", 0.0) or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _selected_drive(event: RuntimeTickEventV2) -> float:
    for row in event.action_competition:
        if row.get("selected"):
            try:
                return float(row.get("drive", 0.0) or 0.0)
            except (TypeError, ValueError):
                return 0.0
    try:
        return float(event.selected_action.get("drive", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _inner_modality_support(event: RuntimeTickEventV2) -> float:
    visual = event.visual_inner_picture or {}
    audio = event.audio_inner_sketch or {}
    values: list[float] = []
    for key in ("clarity_coverage", "imagined_visual_grasp", "borrowed_patch_payload_count"):
        if key in visual:
            try:
                value = float(visual[key] or 0.0)
            except (TypeError, ValueError):
                value = 0.0
            values.append(min(1.0, value if key != "borrowed_patch_payload_count" else value / 12.0))
    for key in ("inner_energy",):
        if key in audio:
            try:
                values.append(float(audio[key] or 0.0))
            except (TypeError, ValueError):
                pass
    return max(values, default=0.0)


def _strongest_state_item(event: RuntimeTickEventV2) -> dict[str, Any]:
    best: dict[str, Any] = {}
    best_score = -1.0
    for item in event.state_pool_top:
        score = 0.0
        for key in ("A", "attention", "R", "real", "V", "virtual", "P", "pressure"):
            try:
                score += abs(float(item.get(key, 0.0) or 0.0))
            except (TypeError, ValueError):
                pass
        if score > best_score:
            best_score = score
            best = dict(item)
    return best


def _selected_source_kind(event: RuntimeTickEventV2) -> str:
    if event.visual_inner_picture:
        return str(event.visual_inner_picture.get("source") or "visual_inner_picture")
    if event.audio_inner_sketch:
        return str(event.audio_inner_sketch.get("source") or "audio_inner_sketch")
    if event.receptor_outputs:
        return str(event.receptor_outputs[0].get("receptor") or "receptor_output")
    if event.unclosed_items:
        return "unclosed_item"
    if event.draft_grid.get("occupied_cells"):
        return "draft_grid"
    return str(event.selected_action.get("action_type") or "selected_action")


def _cause_slots(event: RuntimeTickEventV2) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for output in event.receptor_outputs[:3]:
        slots.append({"slot_kind": "receptor_output", "receptor": output.get("receptor"), "event_id": output.get("event_id")})
    if event.visual_inner_picture:
        slots.append(
            {
                "slot_kind": "visual_inner_picture",
                "source": event.visual_inner_picture.get("source"),
                "epistemic_source": event.visual_inner_picture.get("epistemic_source"),
                "raw_source_asset_used_for_render": event.visual_inner_picture.get("raw_source_asset_used_for_render"),
            }
        )
    if event.audio_inner_sketch:
        slots.append({"slot_kind": "audio_inner_sketch", "source": event.audio_inner_sketch.get("source")})
    if event.unclosed_items:
        slots.append({"slot_kind": "unclosed_item", "count": len(tuple(event.unclosed_items))})
    strongest = _strongest_state_item(event)
    if strongest:
        slots.append({"slot_kind": "strongest_state_pool_item", "sa_id": strongest.get("sa_id"), "family": strongest.get("family")})
    slots.append({"slot_kind": "selected_action", "action_type": event.selected_action.get("action_type")})
    return slots


def _neutralized_occurrences(event: RuntimeTickEventV2, *, support: float) -> list[dict[str, Any]]:
    refs = list(event.experience_event_ids_written[:3])
    if not refs:
        refs = [str(event.selected_action.get("action_type") or "action")]
    return [
        {
            "occurrence_id": ref,
            "neutralize_score": round(min(1.0, support), 4),
            "source_kind": _selected_source_kind(event),
        }
        for ref in refs
    ]


def _support(row: dict[str, Any]) -> float:
    for key in ("support", "cause_grasp", "drive"):
        if key in row:
            try:
                return float(row.get(key, 0.0) or 0.0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _backward_grasp(row: dict[str, Any]) -> float:
    for key in ("cause_grasp", "support", "grasp"):
        if key in row:
            try:
                return float(row.get(key, 0.0) or 0.0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _unit(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _competition_entropy(event: RuntimeTickEventV2) -> float:
    drives: list[float] = []
    for row in event.action_competition:
        try:
            value = max(0.0, float(row.get("drive", 0.0) or 0.0))
        except (TypeError, ValueError):
            value = 0.0
        if value > 0:
            drives.append(value)
    total = sum(drives)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for drive in drives:
        p = drive / total
        entropy -= p * __import__("math").log(p)
    max_entropy = __import__("math").log(max(len(drives), 1))
    return entropy / max_entropy if max_entropy > 0 else 0.0
