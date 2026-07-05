from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping, Sequence

from apv3test.runtime.action_competition import ActionProposal
from apv3test.runtime.draft_grid import DraftGrid
from apv3test.runtime.phase20_6_memory import FastChainHint, SlowMemoryHint


@dataclass(frozen=True)
class Phase20RuntimeOutput:
    reply_text: str
    reply_tokens: tuple[str, ...]
    runtime_events: tuple[dict[str, Any], ...]
    commit_tick_index: int
    source_candidate_id: str
    source_boundary: str
    unresolved_carry: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class _TokenCandidate:
    candidate_id: str
    source_kind: str
    text: str
    tokens: tuple[str, ...]
    source_refs: tuple[str, ...]
    support: float
    priority: float


@dataclass(frozen=True)
class _StateSnapshot:
    sa_id: str
    family: str
    label: str
    real_energy: float
    virtual_energy: float
    attention_energy: float
    cognitive_pressure: float
    channel_signature: tuple[str, ...]
    source: str = "phase20_6_runtime"

    def to_dict(self) -> dict[str, Any]:
        return {
            "sa_id": self.sa_id,
            "family": self.family,
            "label": self.label,
            "real_energy": round(float(self.real_energy), 6),
            "virtual_energy": round(float(self.virtual_energy), 6),
            "attention_energy": round(float(self.attention_energy), 6),
            "cognitive_pressure": round(float(self.cognitive_pressure), 6),
            "channel_signature": list(self.channel_signature),
            "source": self.source,
        }


def run_phase20_6_runtime(
    *,
    base_tick: int,
    max_ticks: int,
    idle_ticks: int,
    user_text_hash: str,
    user_text_length: int,
    has_image: bool,
    visual_items: Sequence[Any],
    object_views: Sequence[Any],
    runtime_turn: Any,
    styled: Any,
    taught: Any,
    context_signature: str,
    fast_hints: Sequence[FastChainHint] = (),
    slow_hints: Sequence[SlowMemoryHint] = (),
    unresolved_carry: Sequence[Mapping[str, Any]] = (),
    affect_evidence: Mapping[str, Any] | None = None,
    sensor_actuator_context: Mapping[str, Any] | None = None,
    process_timing_ms: Mapping[str, float] | None = None,
) -> Phase20RuntimeOutput:
    """Run the Phase 20.6 true-runtime boundary.

    The Stage-0 implementation already moved visible output behind DraftGrid.
    This version tightens the boundary further: each tick rebuilds token/action
    candidates from the current draft prefix, then action competition chooses a
    single actuator action. There is no turn-start reply schedule that the UI
    later pretends to replay.
    """

    budget = max(4, int(max_ticks))
    idle_count = max(0, int(idle_ticks))
    token_candidates = _build_token_candidates(taught=taught, styled=styled, runtime_turn=runtime_turn)
    closure_allowance = max(2, min(12, max((len(item.text) for item in token_candidates), default=2))) if has_image else 0
    active_source = token_candidates[0]
    grid = DraftGrid()
    events: list[dict[str, Any]] = []
    committed_text = ""
    commit_tick_index = 0
    sensor_context = dict(sensor_actuator_context or {})

    stop_emitted = False
    tts_emitted = False
    for offset in range(budget + idle_count + closure_allowance + 3):
        tick_index = offset + 1
        runtime_tick = int(base_tick) + offset
        visible_before = grid.visible_text()
        next_token_candidates = _next_token_candidates(token_candidates, visible_before)
        if not committed_text and offset >= budget:
            if not visible_before:
                break
            if next_token_candidates and offset >= budget + closure_allowance:
                break
        committed_since = tick_index - commit_tick_index if commit_tick_index else 0
        state_items = _state_items_for_tick(
            tick_index=tick_index,
            user_text_hash=user_text_hash,
            user_text_length=user_text_length,
            visual_items=visual_items,
            source=active_source,
            slow_hints=slow_hints,
            unresolved_carry=unresolved_carry,
            affect_evidence=affect_evidence or {},
            context_signature=context_signature,
            grid=grid,
            committed_text=committed_text,
            sensor_context=sensor_context,
        )
        candidates = _action_candidates(
            tick_index=tick_index,
            has_image=has_image,
            token_candidates=next_token_candidates,
            grid=grid,
            committed=bool(committed_text),
            visual_focus_due=bool(has_image and not visible_before and offset == 0),
            visual_observe_required=bool(has_image and not visible_before and not committed_text and tick_index <= 3),
            fast_hints=fast_hints,
            stop_due=bool(committed_text and committed_since > max(0, idle_count)),
            teacher_focus_active=bool(sensor_context.get("teacher_focus_boxes")),
            tts_due=bool(committed_text and sensor_context.get("reply_tts_requested") and not tts_emitted),
        )
        chosen = _choose_action(candidates)

        typed_char = ""
        draft_action_kind = "idle_observe"
        if chosen.outcome_kind == "write_cell":
            typed_char = str(chosen.payload.get("next_token", ""))[:1]
            active_source = _candidate_by_id(
                token_candidates,
                str(chosen.payload.get("source_candidate_id", "")),
                default=active_source,
            )
            grid.write_at(0, min(len(visible_before), grid.cols - 1), typed_char, tick=runtime_tick)
            draft_action_kind = "type_text"
        elif chosen.outcome_kind == "commit_reply":
            committed_text = grid.visible_text()
            commit_tick_index = tick_index
            draft_action_kind = "commit"
        elif chosen.outcome_kind == "move_focus":
            draft_action_kind = "move_focus"
        elif chosen.outcome_kind == "look_again_draft":
            draft_action_kind = "look_again_draft"
        elif chosen.outcome_kind == "stop_generating":
            draft_action_kind = "stop_generating"
            stop_emitted = True
        elif chosen.outcome_kind == "reply_tts_audio":
            draft_action_kind = "reply_tts_audio"
            tts_emitted = True

        visible_text = grid.visible_text()
        pressure = _runtime_pressure(
            draft_action_kind=draft_action_kind,
            next_token_count=len(next_token_candidates),
            draft_length=len(visible_text),
            committed=bool(committed_text),
        )
        real, attention, fatigue = _energy_triplet(state_items, tick_index)
        focus_xy = _focus_for_tick(
            tick_index=tick_index,
            object_views=object_views,
            has_image=has_image,
            sensor_context=sensor_context,
        )
        event = {
            "schema_id": "apv3_phase20_5a_runtime_tick_event/v1",
            "phase20_6_schema_id": "apv3_phase20_6_runtime_tick_event/v1",
            "tick_index": tick_index,
            "runtime_tick": runtime_tick,
            "source": "phase20_6_true_runtime_boundary",
            "stage": "idle_tick_loop" if draft_action_kind == "idle_observe" else "ap_tick_loop",
            "title": f"tick {tick_index}",
            "summary": _summary_for_action(draft_action_kind, typed_char),
            "detail": (
                "Each tick rebuilds RecallCandidate and ActionCandidate rows from the current "
                "state pool, current draft prefix, and source-tagged evidence."
            ),
            "recall_candidates": [_recall_candidate_to_dict(item, visible_before) for item in next_token_candidates],
            "actions_proposed": [_proposal_to_dict(item) for item in candidates],
            "action_chosen": _proposal_to_dict(chosen),
            "action_competition": _action_competition_payload(chosen=chosen, candidates=candidates),
            "state_pool_top12": [item.to_dict() if hasattr(item, "to_dict") else dict(item) for item in state_items[:12]],
            "draft_changes": {
                "schema_id": "apv3_phase20_6_draftgrid_snapshot/v1",
                "draft_action_kind": draft_action_kind,
                "typed_token": typed_char,
                "draft_buffer": visible_text,
                "committed_text": committed_text,
                "source_candidate_id": active_source.candidate_id,
                "source_kind": active_source.source_kind,
                "source_refs": list(active_source.source_refs),
                "candidate_source_count": len(token_candidates),
                "next_token_candidate_count": len(next_token_candidates),
                "input_text_hash": user_text_hash,
                "input_text_length": int(user_text_length),
                "has_image": bool(has_image),
                "object_count": len(object_views),
                "teaching_candidate_applied": active_source.source_kind == "slow_cooccurrence_teacher_phrase",
                "teaching_id": active_source.candidate_id if active_source.source_kind == "slow_cooccurrence_teacher_phrase" else "",
                "candidate_phrase_ids": [item.candidate_id for item in token_candidates],
                "state_pool_count": len(state_items),
                "unresolved_carry_count": len(unresolved_carry),
                "affect_evidence": dict(affect_evidence or {}),
                "sensor_actuator_context": _sensor_context_event_payload(sensor_context),
                "audit_metrics": _audit_metrics_for_tick(
                    tick_index=tick_index,
                    state_items=state_items,
                    object_views=object_views,
                    draft_buffer=visible_text,
                    committed_text=committed_text,
                    process_timing_ms=process_timing_ms or {},
                    pressure=pressure,
                    fatigue=fatigue,
                ),
            },
            "draft_grid_snapshot": {
                "schema_id": "apv3_phase20_6_draftgrid_snapshot/v1",
                "visible_text": visible_text,
                "visible_text_hash": _sha16(visible_text),
                "committed_text_hash": _sha16(committed_text) if committed_text else "",
                "cursor": [0, min(len(visible_text), grid.cols - 1)],
                "changed_by_action": chosen.outcome_kind,
            },
            "focus_xy": list(focus_xy) if focus_xy is not None else None,
            "inner_picture_state": _inner_picture_state_for_tick(
                tick_index=tick_index,
                has_image=has_image,
                focus_xy=focus_xy,
                state_items=state_items,
                object_views=object_views,
            ),
            "inner_audio_state": _inner_audio_state_for_tick(
                tick_index=tick_index,
                sensor_context=sensor_context,
                state_items=state_items,
            ),
            "reply_tts_request": _reply_tts_request_payload(
                requested=bool(sensor_context.get("reply_tts_requested")),
                emitted=tts_emitted,
                chosen=chosen,
                committed_text=committed_text,
            ),
            "thought_cloud_items": _thought_cloud_items(state_items),
            "energy_RAPF": [round(real, 6), round(attention, 6), round(pressure, 6), round(fatigue, 6)],
            "cognitive_pressure": round(pressure, 6),
            "unresolved_pressure": round(pressure, 6),
            "is_projection": False,
        }
        event["phase20_6_tick_memory_records"] = _tick_memory_records_for_event(
            event,
            context_signature=context_signature,
        )
        events.append(event)
        if stop_emitted:
            break

    unresolved_after: tuple[dict[str, Any], ...] = ()
    if not committed_text:
        committed_text = grid.visible_text()
        unresolved_after = (
            {
                "schema_id": "apv3_phase20_6_unresolved_carry/v1",
                "context_signature": str(context_signature),
                "draft_text": committed_text,
                "draft_text_hash": _sha16(committed_text),
                "source_candidate_id": active_source.candidate_id,
                "source_kind": active_source.source_kind,
                "pressure": 1.0,
                "closed": False,
            },
        ) if committed_text else ()
        events.append(
            {
                "schema_id": "apv3_phase20_5a_runtime_tick_event/v1",
                "phase20_6_schema_id": "apv3_phase20_6_runtime_tick_event/v1",
                "tick_index": len(events) + 1,
                "runtime_tick": int(base_tick) + len(events),
                "source": "phase20_6_system_boundary",
                "stage": "system_stop",
                "title": "system boundary",
                "summary": "System tick ceiling reached; this is not AP active stop.",
                "detail": "The system boundary preserves the unfinished draft instead of pretending an AP stop action occurred.",
                "actions_proposed": [],
                "action_chosen": _proposal_to_dict(_system_boundary_action(int(base_tick) + len(events))),
                "action_competition": {
                    "schema_id": "apv3_phase20_6_action_competition/v1",
                    "selected_action_id": "phase20_6::system_boundary",
                    "rejected_action_ids": [],
                    "system_boundary": True,
                },
                "state_pool_top12": [],
                "draft_changes": {
                    "schema_id": "apv3_phase20_6_draftgrid_snapshot/v1",
                    "draft_action_kind": "system_stop",
                    "draft_buffer": committed_text,
                    "committed_text": committed_text,
                    "source_candidate_id": active_source.candidate_id,
                    "system_stop_not_ap_stop": True,
                    "audit_metrics": {},
                },
                "draft_grid_snapshot": {
                    "schema_id": "apv3_phase20_6_draftgrid_snapshot/v1",
                    "visible_text": committed_text,
                    "visible_text_hash": _sha16(committed_text),
                    "committed_text_hash": _sha16(committed_text) if committed_text else "",
                    "cursor": [0, min(len(committed_text), grid.cols - 1)],
                    "changed_by_action": "system_stop",
                },
                "focus_xy": None,
                "inner_picture_state": None,
                "thought_cloud_items": [],
                "energy_RAPF": [0.0, 0.0, 1.0, 0.0],
                "cognitive_pressure": 1.0,
                "unresolved_pressure": 1.0,
                "is_projection": False,
            }
        )

    return Phase20RuntimeOutput(
        reply_text=committed_text,
        reply_tokens=(committed_text,) if committed_text else (),
        runtime_events=tuple(events),
        commit_tick_index=_commit_tick(events),
        source_candidate_id=active_source.candidate_id,
        source_boundary="recall_candidate_to_action_competition_to_draftgrid_commit",
        unresolved_carry=unresolved_after,
    )


def _build_token_candidates(*, taught: Any, styled: Any, runtime_turn: Any) -> tuple[_TokenCandidate, ...]:
    rows: list[_TokenCandidate] = []
    if taught is not None:
        taught_tokens = tuple(str(item) for item in getattr(taught, "response_tokens", ()) if str(item))
        if taught_tokens:
            rows.append(
                _TokenCandidate(
                    candidate_id=str(getattr(taught, "memory_id", "")),
                    source_kind="slow_cooccurrence_teacher_phrase",
                    text="".join(taught_tokens),
                    tokens=taught_tokens,
                    source_refs=(str(getattr(taught, "source_sa_id", "")), str(getattr(taught, "source", ""))),
                    support=float(getattr(taught, "support", 0.0)),
                    priority=1.0,
                )
            )
    styled_tokens = tuple(str(item) for item in getattr(styled, "response_tokens", ()) if str(item))
    styled_text = str(getattr(styled, "response_text", "") or "").strip()
    if styled_tokens or styled_text:
        rows.append(
            _TokenCandidate(
                candidate_id=f"style::{getattr(styled, 'entry_id', '')}",
                source_kind="styled_expression_pattern",
                text=styled_text or "".join(styled_tokens),
                tokens=(styled_text,) if styled_text else styled_tokens,
                source_refs=(str(getattr(styled, "paradigm_id", "")), str(getattr(styled, "source_path", ""))),
                support=0.5,
                priority=0.55,
            )
        )
    runtime_tokens = tuple(str(item) for item in getattr(runtime_turn, "reply_tokens", ()) if str(item))
    if runtime_tokens:
        rows.append(
            _TokenCandidate(
                candidate_id=f"minimalist_runtime::{getattr(runtime_turn, 'tick', 0)}",
                source_kind="legacy_runtime_candidate_evidence",
                text="".join(runtime_tokens),
                tokens=runtime_tokens,
                source_refs=(str(getattr(runtime_turn, "feeling_label", "")),),
                support=0.25,
                priority=0.25,
            )
        )
    if not rows:
        rows.append(
            _TokenCandidate(
                candidate_id="innate::minimal_ack",
                source_kind="innate_minimal_ack",
                text="嗯。",
                tokens=("嗯", "。"),
                source_refs=("innate_drive",),
                support=0.1,
                priority=0.1,
            )
        )
    return tuple(sorted(rows, key=lambda item: (-item.priority, -item.support, item.candidate_id)))


def _next_token_candidates(candidates: Sequence[_TokenCandidate], prefix: str) -> tuple[_TokenCandidate, ...]:
    rows: list[_TokenCandidate] = []
    for candidate in candidates:
        text = candidate.text
        if text and text != prefix and text.startswith(prefix):
            rows.append(candidate)
    return tuple(sorted(rows, key=lambda item: (-item.priority, -item.support, item.candidate_id)))


def _candidate_by_id(
    candidates: Sequence[_TokenCandidate],
    candidate_id: str,
    *,
    default: _TokenCandidate,
) -> _TokenCandidate:
    for candidate in candidates:
        if candidate.candidate_id == candidate_id:
            return candidate
    return default


def _recall_candidate_to_dict(candidate: _TokenCandidate, prefix: str) -> dict[str, Any]:
    next_token = candidate.text[len(prefix): len(prefix) + 1] if candidate.text.startswith(prefix) else ""
    return {
        "schema_id": "apv3_phase20_6_recall_candidate/v1",
        "candidate_id": candidate.candidate_id,
        "source_kind": candidate.source_kind,
        "source_refs": list(candidate.source_refs),
        "support": round(float(candidate.support), 6),
        "priority": round(float(candidate.priority), 6),
        "prefix_length": len(prefix),
        "next_token": next_token,
        "source_phrase_hash": _sha16(candidate.text),
        "source_phrase_length": len(candidate.text),
    }


def _action_candidates(
    *,
    tick_index: int,
    has_image: bool,
    token_candidates: Sequence[_TokenCandidate],
    grid: DraftGrid,
    committed: bool,
    visual_focus_due: bool,
    visual_observe_required: bool,
    fast_hints: Sequence[FastChainHint],
    stop_due: bool,
    teacher_focus_active: bool = False,
    tts_due: bool = False,
) -> tuple[ActionProposal, ...]:
    rows: list[ActionProposal] = []
    visible_text = grid.visible_text()
    if has_image and not committed:
        rows.append(
            _proposal(
                tick_index,
                "move_focus",
                "visual_sampler",
                drive=_clip01((0.94 if visual_focus_due or visual_observe_required else 0.34) + (0.18 if teacher_focus_active else 0.0) + _fast_boost(fast_hints, "move_focus")),
                evidence_tags=(
                    "visual_candidate_sa",
                    "saliency_only_no_label",
                    "teacher_guided_focus" if teacher_focus_active else "auto_focus",
                    "observe_before_write" if visual_observe_required else "observation_optional",
                ),
                payload={
                    "source_candidate_ids": [item.candidate_id for item in token_candidates],
                    "teacher_guided_focus": bool(teacher_focus_active),
                    "semantic_label_authority": False,
                    "visual_observe_required": bool(visual_observe_required),
                },
            )
        )
    if not committed and not visual_observe_required:
        for index, candidate in enumerate(token_candidates[:4]):
            next_token = candidate.text[len(visible_text): len(visible_text) + 1]
            if not next_token:
                continue
            rows.append(
                _proposal(
                    tick_index,
                    "write_cell",
                    "draft_grid",
                    drive=_clip01(0.46 + 0.28 * candidate.priority + 0.18 * candidate.support - 0.02 * index + _fast_boost(fast_hints, "write_cell")),
                    evidence_tags=("recall_candidate", candidate.source_kind, "draftgrid_write"),
                    payload={
                        "source_candidate_id": candidate.candidate_id,
                        "semantic_authority": candidate.source_kind,
                        "next_token": next_token,
                        "prefix_length": len(visible_text),
                        "visible_text_before_hash": _sha16(visible_text),
                    },
                )
            )
    if not committed and visible_text and not token_candidates:
        rows.append(
            _proposal(
                tick_index,
                "commit_reply",
                "draft_grid",
                drive=_clip01(0.9 + _fast_boost(fast_hints, "commit_reply")),
                evidence_tags=("draftgrid_visible_text", "commit_readiness"),
                payload={"draft_text_hash": _sha16(visible_text)},
            )
        )
    if committed and tts_due:
        rows.append(
            _proposal(
                tick_index,
                "reply_tts_audio",
                "local_tts_actuator",
                drive=0.985,
                evidence_tags=("reply_tts", "local_browser_or_offline_actuator", "not_inner_voice"),
                payload={"local_only": True, "semantic_authority": False, "inner_voice": False},
            )
        )
    if committed and stop_due:
        rows.append(
            _proposal(
                tick_index,
                "stop_generating",
                "runtime",
                drive=0.96,
                evidence_tags=("active_stop", "after_commit", "low_unresolved_pressure"),
                payload={"stop_kind": "active_runtime_stop", "commit_already_done": True},
            )
        )
    elif committed:
        rows.append(
            _proposal(
                tick_index,
                "idle_observe",
                "runtime",
                drive=0.25,
                evidence_tags=("after_commit", "quiet_tick"),
                payload={},
            )
        )
    if not rows:
        rows.append(
            _proposal(
                tick_index,
                "look_again_draft",
                "draft_grid",
                drive=0.2,
                evidence_tags=("draft_review",),
                payload={"visible_text_before_hash": _sha16(visible_text)},
            )
        )
    return tuple(sorted(rows, key=lambda item: (-float(item.drive), item.action_id)))


def _proposal(
    tick: int,
    kind: str,
    actuator_id: str,
    *,
    drive: float,
    evidence_tags: Sequence[str],
    payload: Mapping[str, Any],
) -> ActionProposal:
    return ActionProposal(
        tick=int(tick),
        action_id=f"phase20_6::{kind}",
        actuator_id=actuator_id,
        source_system="phase20_runtime_loop",
        outcome_kind=kind,
        drive=max(0.0, min(1.0, float(drive))),
        evidence_tags=tuple(str(item) for item in evidence_tags),
        payload=dict(payload),
    )


def _system_boundary_action(tick: int) -> ActionProposal:
    return ActionProposal(
        tick=int(tick),
        action_id="phase20_6::system_boundary",
        actuator_id="system",
        source_system="phase20_runtime_boundary",
        outcome_kind="system_stop",
        drive=0.0,
        evidence_tags=("system_boundary_not_ap_action",),
        payload={"system_stop_not_ap_stop": True},
    )


def _choose_action(candidates: Sequence[ActionProposal]) -> ActionProposal:
    return tuple(sorted(candidates, key=lambda item: (-float(item.drive), item.action_id)))[0]


def _fast_boost(hints: Sequence[FastChainHint], outcome_kind: str) -> float:
    for hint in hints:
        if hint.next_outcome_kind == outcome_kind:
            return min(0.08, 0.01 * max(1, hint.update_count))
    return 0.0


def _action_competition_payload(*, chosen: ActionProposal, candidates: Sequence[ActionProposal]) -> dict[str, Any]:
    rejected = [item for item in candidates if item.action_id != chosen.action_id]
    return {
        "schema_id": "apv3_phase20_6_action_competition/v1",
        "selected_action_id": chosen.action_id,
        "selected_outcome_kind": chosen.outcome_kind,
        "rejected_action_ids": [item.action_id for item in rejected],
        "candidate_count": len(candidates),
        "source_candidate_ids": [
            str(item.payload.get("source_candidate_id"))
            for item in candidates
            if item.payload.get("source_candidate_id")
        ],
        "system_boundary": False,
    }


def _state_items_for_tick(
    *,
    tick_index: int,
    user_text_hash: str,
    user_text_length: int,
    visual_items: Sequence[Any],
    source: _TokenCandidate,
    slow_hints: Sequence[SlowMemoryHint],
    unresolved_carry: Sequence[Mapping[str, Any]],
    affect_evidence: Mapping[str, Any],
    context_signature: str,
    grid: DraftGrid,
    committed_text: str,
    sensor_context: Mapping[str, Any] | None = None,
) -> tuple[_StateSnapshot, ...]:
    phase = min(1.0, max(0.0, (int(tick_index) - 1) * 0.12))
    rows: list[_StateSnapshot] = [
        _snapshot("phase20_input", user_text_hash or "empty", 0.42, 0.36, 0.2, ("text", "external_user")),
        _snapshot("context", context_signature, 0.55, 0.5, 0.25, ("context", "phase20")),
        _snapshot("source_candidate", source.candidate_id, min(1.0, source.support), 0.58, 0.2, ("memory", source.source_kind)),
        _snapshot("draft_grid", grid.visible_text() or committed_text or "empty", min(0.9, 0.25 + phase), min(0.9, 0.32 + phase), 0.2, ("draft", "text")),
    ]
    sensor_context = dict(sensor_context or {})
    for index, box in enumerate(tuple(sensor_context.get("teacher_focus_boxes", ()))[:3]):
        if not isinstance(box, Mapping):
            continue
        label = f"teacher_focus_box_{index + 1}:{_box_signature(box)}"
        rows.append(
            _snapshot(
                "teacher_guided_focus",
                label,
                0.36,
                0.78,
                0.12,
                ("vision", "teacher_saliency", "no_label"),
            )
        )
    if sensor_context.get("canvas_image_path"):
        rows.append(
            _snapshot(
                "canvas_visual_sensor",
                str(sensor_context.get("canvas_image_hash", "")) or "canvas_input",
                0.48,
                0.52,
                0.18,
                ("vision", "canvas", "user_sensor_input"),
            )
        )
    if sensor_context.get("audio_path"):
        rows.append(
            _snapshot(
                "audio_audit_sensor",
                str(sensor_context.get("audio_hash", "")) or "audio_input",
                0.34,
                0.42,
                0.2,
                ("audio", "recording", "audit_only"),
            )
        )
    if sensor_context.get("reply_tts_requested"):
        rows.append(
            _snapshot(
                "reply_tts_actuator_intent",
                "local_reply_tts",
                0.16,
                0.35,
                0.08,
                ("actuator", "tts", "local_only"),
            )
        )
    for hint in tuple(slow_hints)[:4]:
        rows.append(
            _snapshot(
                "slow_memory_hint",
                hint.memory_id,
                min(1.0, hint.support * 0.1),
                min(1.0, 0.35 + hint.support * 0.05),
                0.16,
                ("memory", "slow", hint.source_kind),
            )
        )
    for carry in tuple(unresolved_carry)[:3]:
        if not isinstance(carry, Mapping):
            continue
        rows.append(
            _snapshot(
                "unresolved_carry",
                str(carry.get("context_signature", "")) or str(carry.get("draft_text_hash", "")),
                _clip01(float(carry.get("pressure", 0.5) or 0.5)),
                0.72,
                _clip01(float(carry.get("pressure", 0.5) or 0.5)),
                ("memory", "unresolved", "cross_turn"),
            )
        )
    if affect_evidence:
        rows.append(
            _snapshot(
                "affect_evidence",
                str(affect_evidence.get("bucket", "neutral")),
                _clip01(float(affect_evidence.get("confidence", 0.0) or 0.0)),
                _clip01(float(affect_evidence.get("attention", 0.35) or 0.35)),
                _clip01(float(affect_evidence.get("pressure", 0.18) or 0.18)),
                ("affect", "text_receptor", str(affect_evidence.get("bucket", "neutral"))),
            )
        )
    for index, item in enumerate(tuple(visual_items)[:6]):
        label = str(getattr(item, "label", "") or getattr(item, "top_concept_uuid", "") or "visual_candidate")
        real = float(getattr(item, "real_energy", getattr(item, "raw_confidence", 0.0)))
        att = float(getattr(item, "attention_energy", getattr(item, "raw_confidence", 0.0)))
        boost = max(0.0, 1.0 - abs(index - ((tick_index - 1) % max(1, len(visual_items)))) * 0.2)
        rows.append(
            _snapshot(
                "visual_candidate",
                label,
                real * (0.6 + 0.3 * boost),
                att * (0.55 + 0.35 * boost),
                max(0.05, 1.0 - min(1.0, real)),
                ("vision", "candidate", "class_agnostic"),
            )
        )
    return tuple(rows[:12])


def _snapshot(
    family: str,
    label: str,
    real_energy: float,
    attention_energy: float,
    cognitive_pressure: float,
    channel_signature: Sequence[str],
) -> _StateSnapshot:
    channels = tuple(str(item) for item in channel_signature)
    return _StateSnapshot(
        sa_id=f"phase20_6::{family}::{_sha16(label)[:12]}",
        family=str(family),
        label=str(label or "none"),
        real_energy=_clip01(real_energy),
        virtual_energy=_clip01(0.42 if "memory" in channels else 0.08 if "vision" in channels else 0.32),
        attention_energy=_clip01(attention_energy),
        cognitive_pressure=_clip01(cognitive_pressure),
        channel_signature=channels,
    )


def _runtime_pressure(*, draft_action_kind: str, next_token_count: int, draft_length: int, committed: bool) -> float:
    if committed or draft_action_kind == "commit":
        return 0.08
    if next_token_count <= 0 and draft_length > 0:
        return 0.14
    return _clip01(0.22 + 0.05 * max(1, int(next_token_count)))


def _energy_triplet(state_items: Sequence[_StateSnapshot], tick_index: int) -> tuple[float, float, float]:
    if not state_items:
        return 0.0, 0.0, 0.0
    real = sum(float(item.real_energy) for item in state_items) / len(state_items)
    attention = sum(float(item.attention_energy) for item in state_items) / len(state_items)
    fatigue = _clip01(float(max(0, tick_index - 1)) * 0.03)
    return real, attention, fatigue


def _focus_for_tick(
    *,
    tick_index: int,
    object_views: Sequence[Any],
    has_image: bool,
    sensor_context: Mapping[str, Any] | None = None,
) -> tuple[int, int] | None:
    if not has_image:
        return None
    boxes = tuple((sensor_context or {}).get("teacher_focus_boxes", ()))
    if boxes:
        box = boxes[(int(tick_index) - 1) % len(boxes)]
        if isinstance(box, Mapping):
            cx = float(box.get("x", 0.0) or 0.0) + float(box.get("w", 0.0) or 0.0) / 2.0
            cy = float(box.get("y", 0.0) or 0.0) + float(box.get("h", 0.0) or 0.0) / 2.0
            return max(0, min(100, int(round(cx)))), max(0, min(100, int(round(cy))))
    if object_views:
        item = object_views[(int(tick_index) - 1) % len(object_views)]
        sketch = getattr(item, "visual_receptor_sketch", {}) or {}
        if isinstance(sketch, Mapping):
            path = sketch.get("focus_path_pct")
            if isinstance(path, Sequence) and path:
                raw = path[(int(tick_index) - 1) % len(path)]
                if isinstance(raw, Sequence) and len(raw) >= 2:
                    return (
                        max(0, min(100, int(round(float(raw[0]))))),
                        max(0, min(100, int(round(float(raw[1]))))),
                    )
        focus = getattr(item, "focus_xy", None)
        if isinstance(focus, tuple) and len(focus) == 2:
            size = getattr(item, "image_size", None)
            if isinstance(size, tuple) and len(size) == 2 and int(size[0]) > 1 and int(size[1]) > 1:
                fx = int(focus[0]) / max(1, int(size[0]) - 1) * 100.0
                fy = int(focus[1]) / max(1, int(size[1]) - 1) * 100.0
            else:
                fx = float(focus[0])
                fy = float(focus[1])
            offsets = ((0, 0), (4, -3), (-4, 4), (3, 5), (-5, -2), (4, 3))
            dx, dy = offsets[(int(tick_index) - 1) % len(offsets)]
            return max(0, min(100, int(round(fx + dx)))), max(0, min(100, int(round(fy + dy))))
    path = ((28, 35), (54, 42), (72, 58), (42, 68), (61, 31), (36, 52))
    return path[(int(tick_index) - 1) % len(path)]


def _box_signature(box: Mapping[str, Any]) -> str:
    return ",".join(
        f"{key}={round(float(box.get(key, 0.0) or 0.0), 3)}"
        for key in ("x", "y", "w", "h")
    )


def _inner_picture_state_for_tick(
    *,
    tick_index: int,
    has_image: bool,
    focus_xy: tuple[int, int] | None,
    state_items: Sequence[_StateSnapshot],
    object_views: Sequence[Any],
) -> dict[str, Any]:
    visual_states = [item for item in state_items if "vision" in item.channel_signature or item.family.startswith("visual")]
    layers = []
    samples = []
    state_energy_by_label = {
        str(item.label): _clip01((float(item.real_energy) + float(item.attention_energy)) / 2.0)
        for item in visual_states
    }
    image_size = None
    for index, obj in enumerate(tuple(object_views)[:6]):
        bbox = getattr(obj, "bbox", None)
        size = getattr(obj, "image_size", None)
        if isinstance(size, tuple) and len(size) == 2:
            image_size = size
        if not isinstance(bbox, tuple) or len(bbox) != 4 or not image_size:
            continue
        width, height = max(1, int(image_size[0])), max(1, int(image_size[1]))
        x1, y1, x2, y2 = (int(v) for v in bbox)
        cx = ((x1 + x2) / 2.0) / width * 100.0
        cy = ((y1 + y2) / 2.0) / height * 100.0
        bw = max(8.0, (x2 - x1) / width * 100.0)
        bh = max(8.0, (y2 - y1) / height * 100.0)
        candidate_label = f"visual_candidate::{getattr(obj, 'candidate_id', '')}"
        energy = max(
            state_energy_by_label.get(candidate_label, 0.0),
            _clip01(float(getattr(obj, "raw_confidence", 0.0) or 0.0)),
        )
        clarity = _clip01(0.18 + 0.13 * int(tick_index))
        obj_sketch = getattr(obj, "visual_receptor_sketch", {}) or {}
        if isinstance(obj_sketch, Mapping):
            samples.extend(
                _sketch_samples_for_tick(
                    obj_sketch,
                    focus_xy=focus_xy,
                    tick_index=tick_index,
                    energy=energy,
                    candidate_label=candidate_label,
                )
            )
        layers.append(
            {
                "sa_id": candidate_label,
                "label": _short_visual_label(getattr(obj, "shape_bucket", "visual")),
                "opacity": round(0.12 + 0.76 * energy * clarity, 4),
                "scale": round(0.7 + 0.45 * energy, 4),
                "depth": index,
                "x": round(cx, 3),
                "y": round(cy, 3),
                "width_pct": round(bw, 3),
                "height_pct": round(bh, 3),
                "color": str(getattr(obj, "dominant_color_hex", "#8aa7a0") or "#8aa7a0"),
                "shape_bucket": str(getattr(obj, "shape_bucket", "unknown")),
                "energy": round(energy, 6),
                "clarity": round(clarity, 6),
                "source": "object_view_state_pool_visual_sa",
            }
        )
    for index, item in enumerate(sorted(visual_states, key=lambda row: row.attention_energy, reverse=True)[:6]):
        if any(layer.get("sa_id") == item.label for layer in layers):
            continue
        energy = _clip01((float(item.real_energy) + float(item.attention_energy)) / 2.0)
        layers.append(
            {
                "sa_id": item.sa_id,
                "label": _short_visual_label(item.label),
                "opacity": round(0.18 + 0.72 * energy, 4),
                "scale": round(0.62 + 0.58 * energy, 4),
                "depth": len(layers),
                "x": 18 + ((index * 23 + tick_index * 11) % 64),
                "y": 22 + ((index * 17 + tick_index * 7) % 54),
                "width_pct": round(14.0 + 16.0 * energy, 3),
                "height_pct": round(14.0 + 16.0 * energy, 3),
                "color": "#6ea8a0",
                "shape_bucket": "state",
                "energy": round(energy, 6),
                "clarity": round(_clip01(0.18 + 0.13 * int(tick_index)), 6),
                "source": "state_pool_visual_sa",
            }
        )
        if len(layers) >= 6:
            break
    return {
        "schema_id": "apv3_phase20_6_inner_picture_state/v1",
        "enabled": bool(has_image and (samples or layers)),
        "source": "state_pool_visual_receptor_sketch_samples",
        "focus_xy": list(focus_xy) if focus_xy is not None else None,
        "object_count": len(object_views),
        "tick_index": int(tick_index),
        "layers": layers,
        "samples": samples[:1600],
        "sample_count": len(samples),
        "reconstruction_boundary": "native receptor samples filtered by state energy and foveated clarity, not a raw image preview",
    }


def _sketch_samples_for_tick(
    sketch: Mapping[str, Any],
    *,
    focus_xy: tuple[int, int] | None,
    tick_index: int,
    energy: float,
    candidate_label: str,
) -> list[dict[str, Any]]:
    raw_samples = sketch.get("samples", ())
    if not isinstance(raw_samples, Sequence):
        return []
    raw_focus = focus_xy if focus_xy is not None else sketch.get("focus_xy", (50, 50))
    if not isinstance(raw_focus, Sequence) or len(raw_focus) < 2:
        raw_focus = (50, 50)
    fx = float(raw_focus[0])
    fy = float(raw_focus[1])
    tick_phase = max(0.0, min(1.0, (int(tick_index) - 1) / 6.0))
    visible_focus_count = max(1, min(9, int(tick_index)))
    rows: list[dict[str, Any]] = []
    max_stride = max(1, 4 - min(3, int(tick_index) // 2))
    for index, raw in enumerate(raw_samples):
        if not isinstance(raw, Mapping):
            continue
        kind = str(raw.get("kind", ""))
        focus_index = int(raw.get("focus_index", 0) or 0)
        if kind == "foveal_native" and focus_index >= visible_focus_count:
            continue
        x = float(raw.get("x", 50.0) or 50.0)
        y = float(raw.get("y", 50.0) or 50.0)
        focus_px = float(raw.get("focus_x", fx) or fx) if kind == "foveal_native" else fx
        focus_py = float(raw.get("focus_y", fy) or fy) if kind == "foveal_native" else fy
        dx_current = x - fx
        dy_current = y - fy
        current_dist = (dx_current * dx_current + dy_current * dy_current) ** 0.5
        dx_sample = x - focus_px
        dy_sample = y - focus_py
        sample_dist = (dx_sample * dx_sample + dy_sample * dy_sample) ** 0.5
        active_dist = min(current_dist, sample_dist)
        clarity = _clip01(0.05 + 0.95 * pow(2.718281828, -(active_dist * active_dist) / (2.0 * 16.0 * 16.0)))
        if kind == "foveal_native" and focus_index < visible_focus_count - 1:
            clarity = _clip01(max(clarity, 0.36 - 0.025 * (visible_focus_count - focus_index)))
        if kind != "foveal_native" and index % max_stride != 0 and clarity < 0.58:
            continue
        if kind == "foveal_native" and clarity < 0.18 and index % 3 != 0:
            continue
        edge = _clip01(float(raw.get("edge", 0.0) or 0.0))
        luma = _clip01(float(raw.get("luma", 0.0) or 0.0))
        opacity = _clip01((0.14 + 0.72 * clarity + 0.18 * edge) * (0.38 + 0.62 * energy) * (0.55 + 0.45 * tick_phase))
        radius = 0.9 + 2.6 * clarity + 1.2 * edge
        rows.append(
            {
                "schema_id": "apv3_phase20_6_inner_picture_sample/v1",
                "sa_id": candidate_label,
                "x": round(x, 4),
                "y": round(y, 4),
                "color": str(raw.get("color", "#6ea8a0") or "#6ea8a0"),
                "opacity": round(opacity, 4),
                "radius": round(radius, 3),
                "clarity": round(clarity, 4),
                "edge": round(edge, 4),
                "luma": round(luma, 4),
                "kind": kind or "sample",
                "focus_index": focus_index,
                "source": "visual_receptor_sketch_native_pixel",
            }
        )
    rows.sort(key=lambda item: (float(item["clarity"]), float(item["edge"])), reverse=True)
    return rows


def _tick_memory_records_for_event(event: Mapping[str, Any], *, context_signature: str) -> list[dict[str, Any]]:
    tick_index = int(event.get("tick_index", 0) or 0)
    runtime_tick = int(event.get("runtime_tick", 0) or 0)
    action = event.get("action_chosen", {})
    action_kind = str(action.get("outcome_kind", "")) if isinstance(action, Mapping) else ""
    draft = event.get("draft_changes", {})
    source_id = str(draft.get("source_candidate_id", "")) if isinstance(draft, Mapping) else ""
    source_kind = str(draft.get("source_kind", "")) if isinstance(draft, Mapping) else ""
    draft_hash = _sha16(str(draft.get("draft_buffer", ""))) if isinstance(draft, Mapping) else ""
    focus = event.get("focus_xy")
    inner = event.get("inner_picture_state", {})
    sample_count = int(inner.get("sample_count", 0) or 0) if isinstance(inner, Mapping) else 0
    state_count = len(event.get("state_pool_top12", ()) or ())
    records = [
        {
            "schema_id": "apv3_phase20_6_tick_fast_memory/v1",
            "memory_id": f"fast_tick::{context_signature}::{tick_index}::{_sha16(action_kind + '|' + draft_hash)}",
            "memory_tier": "fast",
            "context_signature": str(context_signature),
            "tick_index": tick_index,
            "runtime_tick": runtime_tick,
            "action_kind": action_kind,
            "draft_hash": draft_hash,
            "focus_xy": focus if isinstance(focus, list) else list(focus) if isinstance(focus, tuple) else None,
            "state_pool_count": state_count,
            "support": 1.0,
            "display_title": f"快记忆 tick {tick_index}: {action_kind or 'observe'}",
            "display_detail": f"草稿哈希 {draft_hash} · 状态项 {state_count}",
        },
        {
            "schema_id": "apv3_phase20_6_tick_slow_memory/v1",
            "memory_id": f"slow_tick::{context_signature}::{tick_index}::{_sha16(source_id + '|' + source_kind + '|' + str(sample_count))}",
            "memory_tier": "slow",
            "context_signature": str(context_signature),
            "tick_index": tick_index,
            "runtime_tick": runtime_tick,
            "source_candidate_id": source_id,
            "source_kind": source_kind,
            "visual_sample_count": sample_count,
            "support": 1.0,
            "display_title": f"慢记忆 tick {tick_index}: {source_kind or '状态来源'}",
            "display_detail": f"来源 {source_id or '无'} · 内心画面采样 {sample_count}",
        },
    ]
    return records


def _short_visual_label(label: object) -> str:
    text = str(label or "视觉对象")
    if text.startswith("visual_candidate::"):
        return "视觉候选"
    if text in {"wide", "tall", "balanced"}:
        return {"wide": "横向形体", "tall": "纵向形体", "balanced": "均衡形体"}[text]
    if len(text) > 18:
        return text[:8] + "..." + text[-6:]
    return text


def _inner_audio_state_for_tick(
    *,
    tick_index: int,
    sensor_context: Mapping[str, Any],
    state_items: Sequence[_StateSnapshot],
) -> dict[str, Any]:
    audio_states = [item for item in state_items if "audio" in item.channel_signature]
    has_audio = bool(sensor_context.get("audio_path"))
    focus_band = [0.0, 0.0]
    if has_audio:
        center = 0.18 + 0.12 * ((int(tick_index) - 1) % 5)
        focus_band = [round(center, 3), round(min(1.0, center + 0.18), 3)]
    return {
        "schema_id": "apv3_phase20_6_inner_audio_state/v1",
        "enabled": has_audio,
        "source": "audio_sensor_audit_only_not_recognition" if has_audio else "no_audio_input",
        "audio_hash": str(sensor_context.get("audio_hash", "")),
        "focus_band": focus_band,
        "state_count": len(audio_states),
        "tick_index": int(tick_index),
    }


def _reply_tts_request_payload(
    *,
    requested: bool,
    emitted: bool,
    chosen: ActionProposal,
    committed_text: str,
) -> dict[str, Any]:
    return {
        "schema_id": "apv3_phase20_6_reply_tts_request/v1",
        "requested": bool(requested),
        "emitted_this_turn": bool(emitted),
        "selected_this_tick": str(chosen.outcome_kind) == "reply_tts_audio",
        "local_only": True,
        "not_inner_voice": True,
        "semantic_authority": False,
        "text_hash": _sha16(committed_text) if committed_text else "",
        "text_length": len(committed_text),
    }


def _sensor_context_event_payload(sensor_context: Mapping[str, Any]) -> dict[str, Any]:
    boxes = [
        {key: round(float(box.get(key, 0.0) or 0.0), 4) for key in ("x", "y", "w", "h")}
        for box in sensor_context.get("teacher_focus_boxes", ())
        if isinstance(box, Mapping)
    ]
    return {
        "schema_id": "apv3_phase20_6_sensor_actuator_context/v1",
        "teacher_focus_boxes": boxes,
        "teacher_focus_semantic_authority": False,
        "canvas_image_hash": str(sensor_context.get("canvas_image_hash", "")),
        "audio_hash": str(sensor_context.get("audio_hash", "")),
        "audio_mode": str(sensor_context.get("audio_mode", "audio_audit_only")),
        "reply_tts_requested": bool(sensor_context.get("reply_tts_requested")),
        "reply_tts_local_only": True,
    }


def _thought_cloud_items(state_items: Sequence[_StateSnapshot]) -> list[dict[str, Any]]:
    rows = []
    for index, item in enumerate(sorted(state_items, key=lambda row: row.attention_energy, reverse=True)[:12]):
        real = _clip01(float(item.real_energy))
        virtual = _clip01(float(item.virtual_energy))
        total = max(0.000001, real + virtual)
        balance = (real - virtual) / total
        rows.append(
            {
                "schema_id": "apv3_phase20_6_thought_cloud_item/v1",
                "sa_id": item.sa_id,
                "display_label": item.label,
                "family": item.family,
                "radius": round(8.0 + 26.0 * _clip01(item.attention_energy), 3),
                "energy": round(_clip01(item.attention_energy), 6),
                "real_virtual_balance": round(balance, 6),
                "x_hint": round(0.5 + 0.42 * (((index * 37) % 100) / 100.0 - 0.5), 4),
                "y_hint": round(0.5 + 0.42 * (((index * 53) % 100) / 100.0 - 0.5), 4),
            }
        )
    return rows


def _audit_metrics_for_tick(
    *,
    tick_index: int,
    state_items: Sequence[_StateSnapshot],
    object_views: Sequence[Any],
    draft_buffer: str,
    committed_text: str,
    process_timing_ms: Mapping[str, float],
    pressure: float,
    fatigue: float,
) -> dict[str, Any]:
    total_timing = sum(float(value) for value in process_timing_ms.values() if isinstance(value, (int, float)))
    visual_count = sum(1 for item in state_items if "vision" in item.channel_signature or item.family.startswith("visual"))
    text_count = sum(1 for item in state_items if "text" in item.channel_signature or item.family in {"phase20_input", "draft_grid"})
    memory_count = sum(1 for item in state_items if "memory" in item.channel_signature or item.family == "source_candidate")
    return {
        "schema_id": "apv3_phase20_6_tick_audit_metrics/v1",
        "tick_index": int(tick_index),
        "runtime_ms": round(float(process_timing_ms.get("turn_elapsed_ms", total_timing)), 3),
        "process_timing_ms": {str(key): round(float(value), 3) for key, value in process_timing_ms.items()},
        "state_pool_count": len(state_items),
        "visual_state_count": visual_count,
        "text_state_count": text_count,
        "memory_state_count": memory_count,
        "object_file_count": len(object_views),
        "draft_length": len(draft_buffer),
        "committed_length": len(committed_text),
        "mean_cognitive_pressure": round(float(pressure), 6),
        "mean_fatigue": round(float(fatigue), 6),
        "max_attention_energy": round(max((float(item.attention_energy) for item in state_items), default=0.0), 6),
        "max_real_energy": round(max((float(item.real_energy) for item in state_items), default=0.0), 6),
    }


def _proposal_to_dict(proposal: ActionProposal) -> dict[str, Any]:
    return {
        "tick": int(proposal.tick),
        "action_id": str(proposal.action_id),
        "actuator_id": str(proposal.actuator_id),
        "source_system": str(proposal.source_system),
        "outcome_kind": str(proposal.outcome_kind),
        "drive": round(float(proposal.drive), 6),
        "lambda_fast": round(float(proposal.lambda_fast), 6),
        "habit_strength": round(float(proposal.habit_strength), 6),
        "slow_review_pressure": round(float(proposal.slow_review_pressure), 6),
        "evidence_tags": list(proposal.evidence_tags),
        "payload": dict(proposal.payload),
    }


def _summary_for_action(kind: str, token: str) -> str:
    if kind == "type_text":
        return f"action_competition selected write_cell `{token}`"
    if kind == "move_focus":
        return "action_competition selected move_focus"
    if kind == "commit":
        return "action_competition selected commit_reply"
    if kind == "system_stop":
        return "system boundary stop"
    if kind == "stop_generating":
        return "action_competition selected active stop"
    if kind == "look_again_draft":
        return "action_competition selected draft review"
    return "post-commit quiet tick"


def _commit_tick(events: Sequence[Mapping[str, Any]]) -> int:
    for event in events:
        draft = event.get("draft_changes", {})
        if isinstance(draft, Mapping) and draft.get("draft_action_kind") == "commit":
            return int(event.get("tick_index", 0) or 0)
    return 0


def _sha16(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
