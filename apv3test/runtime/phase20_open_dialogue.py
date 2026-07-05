from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import mimetypes
import colorsys
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

from PIL import Image, ImageFilter

from apv3test.chat import APV3MinimalistChatSession, ChatTurn
from apv3test.runtime.action_competition import ActionProposal
from apv3test.runtime.cooccurrence_store import CooccurrenceAssociationStore
from apv3test.runtime.draft_action import DraftActionRunner, DraftTextAction
from apv3test.runtime.expression_phrase_memory import ExpressionPhraseMemory
from apv3test.runtime.phase20_6_memory import (
    consolidate_phase20_6_memory,
    fast_hints_from_state,
    slow_hints_from_state,
)
from apv3test.runtime.phase20_6_runtime import run_phase20_6_runtime
from apv3test.runtime.style_redlines import check_style_compliance, assert_style_compliant, style_safe_tokens
from runtime.cognitive.correction.natural_correction import (
    CorrectionCreditResult,
    apply_natural_correction_credit,
    reward_packet_action,
)
from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.percept_vector.object_looking import (
    ObjectFile,
    extract_candidate_targets,
)
from runtime.cognitive.percept_vector.phase19_runtime import VisualTeachingExample
from runtime.cognitive.sdpl.packet import make_packet
from runtime.cognitive.sdpl.q_table_backoff import QTableWithBackoff
from runtime.cognitive.state_pool.state_pool import StateItem


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE20_2_COOCCURRENCE_REWARD_WEIGHT = 1.0
PHASE20_2_PREVIOUS_REPLY_PUNISH_DELTA = 0.12
PHASE20_2_MIN_RECALL_SUPPORT = 0.5
PHASE20_2_MAX_TEACHING_REPLY_CHARS = 24
PHASE20_2_TEACHING_SCHEMA_ID = "apv3_phase20_2_cooccurrence_teaching_event/v1"
PHASE20_2_STYLE_IMPORT_LIMIT = 1200


@dataclass(frozen=True)
class UserTurnInput:
    text: str = ""
    image_path: Path | None = None
    audio_path: Path | None = None
    feedback_kind: str = "none"
    feedback_target_object_index: int | None = None
    feedback_explicit_label: str | None = None


@dataclass(frozen=True)
class StyledResponse:
    entry_id: str
    paradigm_id: str
    response_tokens: tuple[str, ...]
    response_text: str
    source_path: str
    affect_bucket: str = "neutral"


@dataclass(frozen=True)
class Phase20ObjectView:
    candidate_id: str
    top_visible_label: str
    top_concept_uuid: str
    raw_confidence: float
    decision_tier: str
    nearest_negative_margin: float
    tick_seen: int
    focus_xy: tuple[int, int] | None = None
    bbox: tuple[int, int, int, int] | None = None
    area_ratio: float = 0.0
    image_size: tuple[int, int] | None = None
    dominant_color_hex: str = "#8aa7a0"
    shape_bucket: str = "unknown"
    visual_signature_ids: tuple[str, ...] = ()
    visual_receptor_sketch: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FeedbackTrace:
    feedback_kind: str
    target_object_index: int | None
    correction_total_outcome: float
    eligibility: float
    action: str
    target_label: str
    explicit_label: str | None = None


@dataclass(frozen=True)
class TeachingTrace:
    teaching_id: str
    target_context_signature: str
    response_text: str
    response_tokens: tuple[str, ...]
    reward_delta: float
    previous_reply_punish_delta: float
    previous_reply_hash: str
    rewarded_teaching: bool
    punished_previous: bool
    visual_sa_ids: tuple[str, ...] = ()
    source: str = "teacher_event_cooccurrence"
    ordinary_user_text_persisted: bool = False
    teaching_text_persisted: bool = True


@dataclass(frozen=True)
class Phase20TeachingResult:
    tick: int
    teaching_trace: TeachingTrace
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaughtResponseCandidate:
    memory_id: str
    source_sa_id: str
    response_text: str
    response_tokens: tuple[str, ...]
    support: float
    source: str = "ap_native_cooccurrence"
    strong_visual_support: float = 0.0
    context_support: float = 0.0


@dataclass(frozen=True)
class StateItemSnapshot:
    sa_id: str
    family: str
    label: str
    real_energy: float
    virtual_energy: float
    attention_energy: float
    cognitive_pressure: float
    channel_signature: tuple[str, ...] = ()
    source: str = ""

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


@dataclass(frozen=True)
class RuntimeTickEvent:
    tick_index: int
    runtime_tick: int
    stage: str
    title: str
    summary: str
    detail: str
    actions_proposed: tuple[ActionProposal, ...]
    action_chosen: ActionProposal
    state_pool_top12: tuple[StateItemSnapshot, ...]
    draft_changes: dict[str, Any] = field(default_factory=dict)
    focus_xy: tuple[int, int] | None = None
    inner_picture_state: dict[str, Any] | None = None
    energy_RAPF: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    cognitive_pressure: float = 0.0
    unresolved_pressure: float = 0.0
    is_projection: bool = False
    source: str = "phase20_turn_loop"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "apv3_phase20_5a_runtime_tick_event/v1",
            "tick_index": int(self.tick_index),
            "runtime_tick": int(self.runtime_tick),
            "source": self.source,
            "stage": self.stage,
            "title": self.title,
            "summary": self.summary,
            "detail": self.detail,
            "actions_proposed": [_proposal_to_dict(item) for item in self.actions_proposed],
            "action_chosen": _proposal_to_dict(self.action_chosen),
            "state_pool_top12": [item.to_dict() for item in self.state_pool_top12],
            "draft_changes": dict(self.draft_changes),
            "focus_xy": list(self.focus_xy) if self.focus_xy is not None else None,
            "inner_picture_state": self.inner_picture_state,
            "energy_RAPF": [round(float(item), 6) for item in self.energy_RAPF],
            "cognitive_pressure": round(float(self.cognitive_pressure), 6),
            "unresolved_pressure": round(float(self.unresolved_pressure), 6),
            "is_projection": bool(self.is_projection),
        }


@dataclass(frozen=True)
class Phase20TurnResult:
    tick: int
    reply_text: str
    reply_tokens: tuple[str, ...]
    object_files: tuple[Phase20ObjectView, ...] = ()
    feedback_trace: FeedbackTrace | None = None
    teaching_trace: TeachingTrace | None = None
    styled_response: StyledResponse | None = None
    user_text_hash: str = ""
    image_sha16: str | None = None
    runtime_turn: ChatTurn | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentToolResult:
    reply: str
    object_files: tuple[Phase20ObjectView, ...]
    decision_tier: str
    raw_confidence: float
    epistemic_source: str
    trace: dict[str, Any]


class StyledCorpusIndex:
    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else PROJECT_ROOT / "config" / "curriculum" / "packages" / "styled"
        self._entries = self._load_entries()

    @property
    def entries(self) -> tuple[dict[str, Any], ...]:
        return self._entries

    def select(
        self,
        *,
        situation: str,
        seed_text: str,
        affect_bucket: str = "",
    ) -> StyledResponse:
        paradigm = _situation_to_paradigm(situation)
        candidates = tuple(entry for entry in self._entries if entry["paradigm_id"] == paradigm)
        if affect_bucket:
            affect_matched = tuple(entry for entry in candidates if entry.get("affect_bucket") == affect_bucket)
            if affect_matched:
                candidates = affect_matched
        if not candidates:
            candidates = tuple(entry for entry in self._entries if entry["paradigm_id"] == "PAR-A.01")
        index = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest(), 16) % max(len(candidates), 1)
        item = candidates[index]
        tokens = style_safe_tokens(tuple(str(token) for token in item["response_tokens"]))
        return StyledResponse(
            entry_id=str(item["entry_id"]),
            paradigm_id=str(item["paradigm_id"]),
            response_tokens=tokens,
            response_text=_display_text_from_corpus_item(str(item.get("response_text", "")), tokens),
            source_path=str(item["source_path"]),
            affect_bucket=str(item.get("affect_bucket", "neutral")),
        )

    def _load_entries(self) -> tuple[dict[str, Any], ...]:
        entries: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*.yaml")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            for raw in payload.get("entries", []):
                if not isinstance(raw, Mapping):
                    continue
                public = raw.get("public_payload", {})
                if not isinstance(public, Mapping):
                    continue
                response_tokens = tuple(str(token) for token in public.get("response_tokens", ()))
                response_text = _display_text_from_corpus_item(str(public.get("response_text", "")), response_tokens)
                if response_text.strip() == "嗯在" or "".join(response_tokens).strip() == "嗯在":
                    continue
                entries.append(
                    {
                        "entry_id": str(raw.get("entry_id", "")),
                        "paradigm_id": str(public.get("paradigm_id", "")),
                        "response_tokens": response_tokens,
                        "response_text": response_text,
                        "affect_bucket": str(public.get("affect_bucket", "neutral")),
                        "source_path": path.as_posix(),
                    }
                )
        if not entries:
            raise FileNotFoundError("styled corpus entries not found")
        return tuple(entries)


class Phase20MultimodalSession:
    def __init__(
        self,
        *,
        state_db_path: str | Path | None = None,
        teaching_examples: Sequence[VisualTeachingExample] | None = None,
        styled_corpus: StyledCorpusIndex | None = None,
    ) -> None:
        self.chat = APV3MinimalistChatSession(state_db_path=state_db_path)
        self.teaching_examples = tuple(teaching_examples or load_clean_card_teaching_examples())
        self.styled_corpus = styled_corpus or StyledCorpusIndex()
        self.q_table = QTableWithBackoff()
        self.last_turn: Phase20TurnResult | None = None
        self._ensure_styled_corpus_in_ap_memory()

    def turn(self, payload: Mapping[str, object] | UserTurnInput) -> Phase20TurnResult:
        user_input = parse_user_input(payload)
        live_payload = payload if isinstance(payload, Mapping) else {}
        turn_started = time.perf_counter()
        input_hash = _sha16(user_input.text) if user_input.text else ""
        timings: dict[str, float] = {}

        step_started = time.perf_counter()
        feedback_trace = self._process_feedback(user_input)
        timings["feedback_ms"] = _elapsed_ms(step_started)

        step_started = time.perf_counter()
        object_views = self._extract_visual_candidates(user_input.image_path) if user_input.image_path is not None else ()
        timings["visual_candidate_ms"] = _elapsed_ms(step_started)
        visual_items = _visual_state_items(object_views)

        step_started = time.perf_counter()
        runtime_turn = self.chat.say(user_input.text)
        timings["legacy_text_runtime_ms"] = _elapsed_ms(step_started)

        situation = _situation_from(user_input, object_views, feedback_trace)
        affect_evidence = _text_affect_evidence(user_input.text)
        step_started = time.perf_counter()
        styled = self.styled_corpus.select(
            situation=situation,
            seed_text=f"{runtime_turn.user_text_hash}:{situation}:{len(object_views)}:{affect_evidence.get('bucket', '')}",
            affect_bucket=str(affect_evidence.get("bucket", "")),
        )
        timings["style_ms"] = _elapsed_ms(step_started)

        context_signature, context_payload = _context_signature(
            user_text_hash=runtime_turn.user_text_hash,
            has_image=user_input.image_path is not None,
            situation=situation,
            object_views=object_views,
            styled=styled,
            affect_evidence=affect_evidence,
        )
        visual_sa_ids = _visual_sa_ids(object_views)
        step_started = time.perf_counter()
        taught = self._select_taught_response(context_signature, visual_sa_ids)
        timings["recall_ms"] = _elapsed_ms(step_started)
        source_candidate_ids = tuple(
            item for item in (
                taught.memory_id if taught is not None else "",
                f"style::{styled.entry_id}" if styled is not None else "",
                f"minimalist_runtime::{runtime_turn.tick}",
            )
            if item
        )
        fast_hints = fast_hints_from_state(self.chat.state, context_signature=context_signature)
        slow_hints = slow_hints_from_state(self.chat.state, source_candidate_ids=source_candidate_ids)
        unresolved_carry = tuple(
            item for item in self.chat.state.get("phase20_6_unresolved_carry", ())
            if isinstance(item, Mapping)
        ) if isinstance(self.chat.state.get("phase20_6_unresolved_carry", ()), list) else ()
        timings["turn_elapsed_ms"] = _elapsed_ms(turn_started)
        sensor_context = _sensor_actuator_context(live_payload, user_input=user_input)

        runtime_output = run_phase20_6_runtime(
            base_tick=runtime_turn.tick,
            max_ticks=_bounded_int(live_payload.get("max_ticks"), default=8, minimum=4, maximum=32),
            idle_ticks=_bounded_int(live_payload.get("idle_ticks"), default=2, minimum=0, maximum=8),
            user_text_hash=input_hash,
            user_text_length=len(user_input.text),
            has_image=user_input.image_path is not None,
            visual_items=visual_items,
            object_views=object_views,
            runtime_turn=runtime_turn,
            styled=styled,
            taught=taught,
            context_signature=context_signature,
            fast_hints=fast_hints,
            slow_hints=slow_hints,
            unresolved_carry=unresolved_carry,
            affect_evidence=affect_evidence,
            sensor_actuator_context=sensor_context,
            process_timing_ms=timings,
        )
        reply_text = runtime_output.reply_text
        reply_tokens = runtime_output.reply_tokens
        assert_style_compliant(reply_tokens, max_tokens=self.chat.profile.style_max_tokens)
        image_sha16 = _image_sha16(user_input.image_path) if user_input.image_path is not None else None
        result = Phase20TurnResult(
            tick=runtime_turn.tick,
            reply_text=reply_text,
            reply_tokens=reply_tokens,
            object_files=object_views,
            feedback_trace=feedback_trace,
            styled_response=styled,
            user_text_hash=runtime_turn.user_text_hash,
            image_sha16=image_sha16,
            runtime_turn=runtime_turn,
            metadata={
                "schema_id": "apv3_phase20_6_turn/v1",
                "source_boundary": "text_user_only_visual_candidates_separate",
                "raw_image_persisted": False,
                "zvec_commit": "not_in_phase20_6_stage0",
                "context_signature": context_signature,
                "context_signature_components": context_payload,
                "teaching_candidate_applied": taught is not None,
                "teaching_id": taught.memory_id if taught is not None else "",
                "teaching_source": taught.source if taught is not None else "",
                "visual_sa_ids": visual_sa_ids,
                "runtime_tick_events": runtime_output.runtime_events,
                "runtime_tick_event_source": "phase20_6_true_runtime_boundary",
                "runtime_tick_projection": False,
                "phase20_6_stage": "stage0_runtime_boundary",
                "phase20_6_source_candidate_id": runtime_output.source_candidate_id,
                "phase20_6_source_boundary": runtime_output.source_boundary,
                "phase20_6_commit_tick_index": runtime_output.commit_tick_index,
                "legacy_text_runtime_reply_not_committed": True,
                "phase20_6_fast_hint_count": len(fast_hints),
                "phase20_6_slow_hint_count": len(slow_hints),
                "phase20_6_unresolved_carry_in_count": len(unresolved_carry),
                "phase20_6_unresolved_carry_out": list(runtime_output.unresolved_carry),
                "phase20_6_affect_evidence": dict(affect_evidence),
                "phase20_6_sensor_actuator_context": dict(sensor_context),
            },
        )
        self._persist_phase20_trace(result, user_input)
        self.last_turn = result
        return result

    def teach_latest(self, payload: Mapping[str, object] | str) -> Phase20TeachingResult:
        text = str(payload if isinstance(payload, str) else payload.get("teaching_reply_text", "")).strip()
        tokens = _teaching_tokens_from_text(text)
        compliance = check_style_compliance(tokens, max_tokens=self.chat.profile.style_max_tokens)
        if not compliance.ok:
            raise ValueError(f"teaching_reply_style_rejected:{compliance.reason}")
        state = dict(self.chat.state)
        last_context = _latest_phase20_context(state)
        if not last_context:
            raise ValueError("phase20_teaching_needs_previous_turn")
        if isinstance(payload, Mapping):
            target_context = str(payload.get("target_context_signature", "") or "")
            target_tick_raw = payload.get("target_tick")
            if target_context and target_context != str(last_context.get("context_signature", "")):
                raise ValueError("phase20_teaching_target_context_changed")
            if target_tick_raw not in (None, "") and int(target_tick_raw) != int(last_context.get("tick", 0) or 0):
                raise ValueError("phase20_teaching_target_tick_changed")
        context_signature = str(last_context.get("context_signature", ""))
        previous_reply_hash = str(last_context.get("reply_text_hash", ""))
        visual_sa_ids = tuple(str(item) for item in last_context.get("visual_sa_ids", ()) if str(item))
        tick = int(last_context.get("tick", self.chat.tick))
        candidate, trace = _observe_teacher_cooccurrence(
            state,
            context_signature=context_signature,
            response_text=text,
            response_tokens=tokens,
            visual_sa_ids=visual_sa_ids,
            previous_reply_hash=previous_reply_hash,
            tick=max(self.chat.tick, tick),
        )
        state["phase20_last_teaching_trace"] = teaching_trace_to_dict(trace)
        self.chat.state = state
        self.chat.store.save_state(state)
        return Phase20TeachingResult(
            tick=tick,
            teaching_trace=trace,
            metadata={
                "schema_id": "apv3_phase20_1_teaching_result/v1",
                "candidate_support": candidate.support,
                "source_boundary": "teacher_event_not_user_query",
            },
        )

    def agent_tool(self, *, text: str = "", image_path: str | Path | None = None) -> AgentToolResult:
        result = self.turn({"text": text, "image_path": str(image_path) if image_path is not None else None})
        top = result.object_files[0] if result.object_files else None
        return AgentToolResult(
            reply=result.reply_text,
            object_files=result.object_files,
            decision_tier=top.decision_tier if top is not None else "no_visual_input",
            raw_confidence=top.raw_confidence if top is not None else 0.0,
            epistemic_source="PERCEIVED" if top is not None else "TEXT_ONLY",
            trace={
                "tick": result.tick,
                "image_sha16": result.image_sha16,
                "styled_entry_id": result.styled_response.entry_id if result.styled_response else "",
                "label_returned_by_zvec": False,
            },
        )

    def _ensure_styled_corpus_in_ap_memory(self) -> None:
        state = dict(self.chat.state)
        existing = state.get("phase20_style_corpus_import")
        if isinstance(existing, Mapping) and int(existing.get("imported_count", 0) or 0) >= PHASE20_2_STYLE_IMPORT_LIMIT:
            return
        memory = ExpressionPhraseMemory.from_state(state.get("expression_phrase_memory"))
        assoc = CooccurrenceAssociationStore.from_state(state.get("cooccurrence_associations"))
        imported = 0
        for item in self.styled_corpus.entries:
            if imported >= PHASE20_2_STYLE_IMPORT_LIMIT:
                break
            entry_id = str(item.get("entry_id", ""))
            paradigm_id = str(item.get("paradigm_id", ""))
            tokens = style_safe_tokens(tuple(str(token) for token in item.get("response_tokens", ()) if str(token)))
            if not entry_id or not paradigm_id or not tokens:
                continue
            phrase_id = f"style::{entry_id}"
            memory.observe(
                phrase_id,
                tokens,
                weight=1.0,
                current_tick=max(1, self.chat.tick),
                phrase_kind="styled_curriculum_example",
            )
            assoc.observe(
                f"style_paradigm::{paradigm_id}",
                phrase_id,
                weight=1.0,
                current_tick=max(1, self.chat.tick),
                paradigm_id=phrase_id,
            )
            imported += 1
        state["expression_phrase_memory"] = memory.export_state()
        state["cooccurrence_associations"] = assoc.export_state()
        state["phase20_style_corpus_import"] = {
            "schema_id": "apv3_phase20_2_style_corpus_import/v1",
            "source": "curriculum_styled_yaml",
            "imported_count": imported,
            "available_count": len(self.styled_corpus.entries),
            "import_limit": PHASE20_2_STYLE_IMPORT_LIMIT,
            "ap_native_memory": True,
        }
        self.chat.state = state
        self.chat.store.save_state(state)

    def _extract_visual_candidates(self, image_path: Path) -> tuple[Phase20ObjectView, ...]:
        candidates = extract_candidate_targets(image_path)
        views: list[Phase20ObjectView] = []
        image_size, signatures = _visual_candidate_signatures(image_path, candidates)
        for tick_seen, candidate in enumerate(candidates):
            signature = signatures.get(candidate.candidate_id, {})
            views.append(
                Phase20ObjectView(
                    candidate_id=candidate.candidate_id,
                    top_visible_label="visual_candidate",
                    top_concept_uuid=f"visual_candidate::{candidate.candidate_id}",
                    raw_confidence=float(candidate.saliency),
                    decision_tier="candidate_only",
                    nearest_negative_margin=0.0,
                    tick_seen=tick_seen,
                    focus_xy=candidate.focus_xy,
                    bbox=candidate.bbox,
                    area_ratio=float(candidate.area_ratio),
                    image_size=image_size,
                    dominant_color_hex=str(signature.get("dominant_color_hex", "#8aa7a0")),
                    shape_bucket=str(signature.get("shape_bucket", "unknown")),
                    visual_signature_ids=tuple(str(item) for item in signature.get("signature_ids", ()) if str(item)),
                    visual_receptor_sketch=dict(signature.get("visual_receptor_sketch", {}))
                    if isinstance(signature.get("visual_receptor_sketch", {}), Mapping)
                    else {},
                )
            )
        return tuple(views)

    def _process_image(self, image_path: Path) -> ObjectLookingResult:
        raise RuntimeError("phase20_legacy_whole_image_recognition_quarantined")

    def _process_feedback(self, user_input: UserTurnInput) -> FeedbackTrace | None:
        if user_input.feedback_kind == "none" or self.last_turn is None or not self.last_turn.object_files:
            return None
        target_index = int(user_input.feedback_target_object_index or 0)
        target_index = max(0, min(target_index, len(self.last_turn.object_files) - 1))
        target = self.last_turn.object_files[target_index]
        item = StateItem(
            sa_id=f"phase20_object::{target.candidate_id}",
            family="visual_object",
            label=target.top_concept_uuid,
            real_energy=max(target.raw_confidence, 0.0),
            metadata={"substrate": "EXTERNAL_VISUAL", "cognitive_content": target.top_concept_uuid},
        )
        marker = MarkerEvent(
            tick=self.chat.tick + 1,
            kind="CORRECTION" if user_input.feedback_kind != "positive" else "PERCEIVED",
            target_sa_id=item.sa_id,
            real_energy=1.0,
            metadata={"substrate": "EXTERNAL_VISUAL"},
        )
        packet = make_packet(content_sas=(item,), source_markers=(marker,), slot_context=("phase20_feedback",))
        action = f"recognize::{target.top_concept_uuid}"
        if user_input.feedback_kind == "positive":
            reward_packet_action(self.q_table, packet, action, amount=1.0)
            credit = CorrectionCreditResult(action=action, immediate_outcome=1.0, delayed_outcome=0.0, total_outcome=1.0, eligibility=1.0)
        else:
            credit = apply_natural_correction_credit(
                self.q_table,
                packet,
                action,
                marker,
                action_tick=self.last_turn.tick,
            )
        return FeedbackTrace(
            feedback_kind=user_input.feedback_kind,
            target_object_index=target_index,
            correction_total_outcome=float(credit.total_outcome),
            eligibility=float(credit.eligibility),
            action=action,
            target_label=target.top_visible_label,
            explicit_label=user_input.feedback_explicit_label,
        )

    def _select_taught_response(
        self,
        context_signature: str,
        visual_sa_ids: Sequence[str],
    ) -> TaughtResponseCandidate | None:
        assoc = CooccurrenceAssociationStore.from_state(self.chat.state.get("cooccurrence_associations"))
        memory = ExpressionPhraseMemory.from_state(self.chat.state.get("expression_phrase_memory"))
        weighted_labels = _weighted_recall_labels(context_signature, visual_sa_ids)
        has_visual = any(_is_visual_recall_label(label) for label, _weight in weighted_labels)
        current_tick = max(1, self.chat.tick + 1)
        scored: dict[str, dict[str, object]] = {}
        for label, label_weight in weighted_labels:
            for phrase_id in assoc.nearest_by_label((label,), top_k=8, current_tick=current_tick):
                raw_support = assoc.similarity(label, phrase_id, current_tick)
                support = raw_support * label_weight
                if support <= 0.0:
                    continue
                row = scored.setdefault(
                    phrase_id,
                    {
                        "support": 0.0,
                        "source_sa_id": label,
                        "max_label_weight": 0.0,
                        "strong_visual_support": 0.0,
                        "context_support": 0.0,
                    },
                )
                row["support"] = float(row["support"]) + support
                if label_weight >= float(row["max_label_weight"]):
                    row["source_sa_id"] = label
                    row["max_label_weight"] = label_weight
                if _is_strong_visual_recall_label(label):
                    row["strong_visual_support"] = float(row["strong_visual_support"]) + support
                if label == context_signature:
                    row["context_support"] = float(row["context_support"]) + support
        candidates: list[TaughtResponseCandidate] = []
        for phrase_id, row in scored.items():
            support = float(row["support"])
            strong_visual_support = float(row["strong_visual_support"])
            context_support = float(row["context_support"])
            if has_visual and strong_visual_support < PHASE20_2_MIN_RECALL_SUPPORT:
                continue
            if support < PHASE20_2_MIN_RECALL_SUPPORT:
                continue
            records = memory.recall((phrase_id,), top_k=1, current_tick=current_tick)
            if not records:
                continue
            record = records[0]
            # 只用结构命名空间判据过滤教师短语候选: teacher_phrase:: 前缀由
            # _phrase_id_for_teacher_text 唯一产出, 与 style:: / user_utterance::
            # 互斥; 不再用 phrase_kind 标签路由 (phase7_9 红线: 勿按 kind 脚本路由)。
            if not record.phrase_id.startswith("teacher_phrase::"):
                continue
            candidates.append(
                TaughtResponseCandidate(
                    memory_id=record.phrase_id,
                    source_sa_id=str(row["source_sa_id"]),
                    response_text="".join(record.tokens),
                    response_tokens=record.tokens,
                    support=support,
                    strong_visual_support=strong_visual_support,
                    context_support=context_support,
                )
            )
        candidates.sort(key=lambda item: (-item.support, item.memory_id))
        if len(candidates) > 1 and candidates[0].support - candidates[1].support < 0.18:
            return None
        return candidates[0] if candidates else None

    def _persist_phase20_trace(self, result: Phase20TurnResult, user_input: UserTurnInput) -> None:
        state = dict(self.chat.state)
        trace = [dict(item) for item in state.get("phase20_turn_trace", []) if isinstance(item, Mapping)]
        reply_text_hash = _sha16(result.reply_text)
        context_signature = str(result.metadata.get("context_signature", ""))
        context_components = result.metadata.get("context_signature_components", {})
        trace.append(
            {
                "schema_id": "apv3_phase20_1_turn_trace/v1",
                "tick": result.tick,
                "user_text_hash": result.user_text_hash,
                "user_text_length": len(user_input.text),
                "image_sha16": result.image_sha16,
                "raw_image_persisted": False,
                "object_files": [object_view_to_dict(item) for item in result.object_files],
                "feedback_trace": feedback_trace_to_dict(result.feedback_trace),
                "teaching_trace": teaching_trace_to_dict(result.teaching_trace),
                "styled_entry_id": result.styled_response.entry_id if result.styled_response else "",
                "styled_paradigm_id": result.styled_response.paradigm_id if result.styled_response else "",
                "reply_text": result.reply_text,
                "reply_text_hash": reply_text_hash,
                "context_signature": context_signature,
                "context_signature_components": context_components,
                "visual_sa_ids": list(result.metadata.get("visual_sa_ids", ())),
                "teaching_candidate_applied": bool(result.metadata.get("teaching_candidate_applied", False)),
                "teaching_id": str(result.metadata.get("teaching_id", "")),
                "source_boundary": "user_text_not_augmented_by_visual_label",
                "runtime_tick_events": list(result.metadata.get("runtime_tick_events", ())),
            }
        )
        state["phase20_6_unresolved_carry"] = list(result.metadata.get("phase20_6_unresolved_carry_out", ()))
        state["phase20_turn_trace"] = trace
        state["phase20_last_context"] = {
            "schema_id": "apv3_phase20_1_last_context/v1",
            "tick": int(result.tick),
            "context_signature": context_signature,
            "context_signature_components": context_components,
            "reply_text_hash": reply_text_hash,
            "styled_entry_id": result.styled_response.entry_id if result.styled_response else "",
            "styled_paradigm_id": result.styled_response.paradigm_id if result.styled_response else "",
            "object_count": len(result.object_files),
            "visual_sa_ids": list(result.metadata.get("visual_sa_ids", ())),
            "source_boundary": "teacher_can_target_this_context_without_user_text",
        }
        if user_input.text:
            _observe_user_utterance_memory(
                state,
                text=user_input.text,
                context_signature=context_signature,
                visual_sa_ids=tuple(str(item) for item in result.metadata.get("visual_sa_ids", ()) if str(item)),
                tick=int(result.tick),
            )
        state = consolidate_phase20_6_memory(
            state,
            context_signature=context_signature,
            runtime_events=tuple(result.metadata.get("runtime_tick_events", ())),
            tick=int(result.tick),
        )
        self.chat.state = state
        self.chat.store.save_state(state)


def parse_user_input(payload: Mapping[str, object] | UserTurnInput) -> UserTurnInput:
    if isinstance(payload, UserTurnInput):
        return payload
    image_value = payload.get("image_path")
    media_value = payload.get("media_path")
    media_type = str(payload.get("media_type", "") or "")
    if not media_type and media_value:
        media_type = mimetypes.guess_type(str(media_value))[0] or ""
    image_path = Path(str(image_value)) if image_value else None
    audio_path = None
    if media_value and media_type.startswith("audio/"):
        audio_path = Path(str(media_value))
    elif media_value and not image_path and not media_type.startswith("image/"):
        guessed = mimetypes.guess_type(str(media_value))[0] or ""
        if guessed.startswith("audio/"):
            audio_path = Path(str(media_value))
    if media_value and not image_path and media_type.startswith("image/"):
        image_path = Path(str(media_value))
    return UserTurnInput(
        text=str(payload.get("text", "")).strip(),
        image_path=image_path,
        audio_path=audio_path,
        feedback_kind=str(payload.get("feedback_kind", "none") or "none"),
        feedback_target_object_index=_optional_int(payload.get("feedback_target_object_index")),
        feedback_explicit_label=str(payload.get("feedback_explicit_label", "") or "") or None,
    )


def _sensor_actuator_context(payload: Mapping[str, object], *, user_input: UserTurnInput) -> dict[str, Any]:
    media_source = str(payload.get("media_source", "") or "")
    boxes = _teacher_focus_boxes(payload.get("teacher_focus_boxes"))
    canvas_path = user_input.image_path if media_source == "canvas" and user_input.image_path is not None else None
    audio_path = user_input.audio_path
    return {
        "schema_id": "apv3_phase20_6_sensor_actuator_context/v1",
        "teacher_focus_boxes": boxes,
        "teacher_focus_semantic_authority": False,
        "canvas_image_path": str(canvas_path) if canvas_path is not None else "",
        "canvas_image_hash": _path_sha16(canvas_path) if canvas_path is not None else "",
        "audio_path": str(audio_path) if audio_path is not None else "",
        "audio_hash": _path_sha16(audio_path) if audio_path is not None else "",
        "audio_mode": "audio_audit_only" if audio_path is not None else "no_audio_input",
        "reply_tts_requested": bool(payload.get("tts_enabled", False)),
        "reply_tts_local_only": True,
        "semantic_authority": False,
    }


def _teacher_focus_boxes(value: object) -> tuple[dict[str, float], ...]:
    if not isinstance(value, list):
        return ()
    boxes: list[dict[str, float]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        box = {
            key: max(0.0, min(100.0, float(item.get(key, 0.0) or 0.0)))
            for key in ("x", "y", "w", "h")
        }
        if box["w"] <= 0.0 or box["h"] <= 0.0:
            continue
        boxes.append(box)
    return tuple(boxes[:6])


def _path_sha16(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]


def load_clean_card_teaching_examples() -> tuple[VisualTeachingExample, ...]:
    package_path = PROJECT_ROOT / "config" / "curriculum" / "packages" / "clean" / "clean_fruit_cards_v1.yaml"
    manifest_path = PROJECT_ROOT / "config" / "curriculum" / "assets" / "clean_card_manifest.yaml"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = {str(item["asset_id"]): item for item in manifest.get("assets", [])}
    examples: list[VisualTeachingExample] = []
    tick = 0
    for entry in package.get("entries", []):
        public = entry.get("public_payload", {})
        label = str(public.get("neutral_label", entry.get("entry_id", "")))
        for asset_ref in entry.get("train_asset_refs", []):
            asset = assets[str(asset_ref)]
            path = PROJECT_ROOT / "config" / "curriculum" / "assets" / str(asset["path"])
            tick += 1
            examples.append(VisualTeachingExample(path=path, visible_teacher_label=label, split="train", tick=tick))
    return tuple(examples)


def assemble_reply_tokens(
    styled: StyledResponse,
    object_views: Sequence[Phase20ObjectView],
    runtime_tokens: Sequence[str],
) -> tuple[str, ...]:
    prefix = tuple(styled.response_tokens or runtime_tokens)
    if not object_views:
        return style_safe_tokens(prefix or tuple(runtime_tokens))
    confident = [item for item in object_views if item.decision_tier in {"firm", "soft"}]
    if not confident:
        return style_safe_tokens(prefix)
    labels = tuple(item.top_visible_label for item in confident[: max(1, 3 - len(prefix))])
    return style_safe_tokens(prefix + labels)


def assemble_reply_text(
    styled: StyledResponse,
    object_views: Sequence[Phase20ObjectView],
    reply_tokens: Sequence[str],
) -> str:
    base = str(styled.response_text or "").strip() or "".join(str(token) for token in reply_tokens)
    confident = [item for item in object_views if item.decision_tier in {"firm", "soft"}]
    labels = tuple(item.top_visible_label for item in confident)
    if not labels:
        return base
    if any(label and label in base for label in labels):
        return base
    suffix = "、".join(label for label in labels[:1] if label)
    if not suffix:
        return base
    return f"{base.rstrip('。')}: {suffix}。"


def _display_text_from_corpus_item(response_text: str, tokens: Sequence[str]) -> str:
    text = str(response_text or "").strip()
    return text if text else "".join(str(token) for token in tokens)


def object_view_to_dict(item: Phase20ObjectView) -> dict[str, object]:
    return {
        "candidate_id": item.candidate_id,
        "top_visible_label": item.top_visible_label,
        "top_concept_uuid": item.top_concept_uuid,
        "raw_confidence": item.raw_confidence,
        "decision_tier": item.decision_tier,
        "nearest_negative_margin": item.nearest_negative_margin,
        "tick_seen": item.tick_seen,
        "focus_xy": list(item.focus_xy) if item.focus_xy is not None else None,
        "bbox": list(item.bbox) if item.bbox is not None else None,
        "area_ratio": item.area_ratio,
        "image_size": list(item.image_size) if item.image_size is not None else None,
        "dominant_color_hex": item.dominant_color_hex,
        "shape_bucket": item.shape_bucket,
        "visual_signature_ids": list(item.visual_signature_ids),
        "visual_receptor_sketch": item.visual_receptor_sketch,
    }


def feedback_trace_to_dict(trace: FeedbackTrace | None) -> dict[str, object] | None:
    if trace is None:
        return None
    return {
        "feedback_kind": trace.feedback_kind,
        "target_object_index": trace.target_object_index,
        "correction_total_outcome": trace.correction_total_outcome,
        "eligibility": trace.eligibility,
        "action": trace.action,
        "target_label": trace.target_label,
        "explicit_label": trace.explicit_label,
    }


def teaching_trace_to_dict(trace: TeachingTrace | None) -> dict[str, object] | None:
    if trace is None:
        return None
    return {
        "schema_id": PHASE20_2_TEACHING_SCHEMA_ID,
        "teaching_id": trace.teaching_id,
        "target_context_signature": trace.target_context_signature,
        "response_text": trace.response_text,
        "response_tokens": list(trace.response_tokens),
        "reward_delta": trace.reward_delta,
        "previous_reply_punish_delta": trace.previous_reply_punish_delta,
        "previous_reply_hash": trace.previous_reply_hash,
        "rewarded_teaching": trace.rewarded_teaching,
        "punished_previous": trace.punished_previous,
        "visual_sa_ids": list(trace.visual_sa_ids),
        "source": trace.source,
        "ordinary_user_text_persisted": trace.ordinary_user_text_persisted,
        "teaching_text_persisted": trace.teaching_text_persisted,
    }


class _RuntimeEventBuilder:
    def __init__(self, *, base_tick: int) -> None:
        self.base_tick = int(base_tick)
        self.events: list[RuntimeTickEvent] = []

    def emit(
        self,
        stage: str,
        title: str,
        summary: str,
        detail: str,
        state_items: Sequence[StateItemSnapshot],
        *,
        focus_xy: tuple[int, int] | None = None,
        draft_changes: Mapping[str, Any] | None = None,
    ) -> None:
        tick_index = len(self.events) + 1
        chosen = _action_for_stage(stage, tick_index=tick_index)
        items = tuple(state_items)[:12]
        pressure = _mean(item.cognitive_pressure for item in items)
        attention = _mean(item.attention_energy for item in items)
        real = _mean(item.real_energy for item in items)
        fatigue = max(0.0, min(1.0, float(tick_index - 1) * 0.03))
        self.events.append(
            RuntimeTickEvent(
                tick_index=tick_index,
                runtime_tick=self.base_tick + tick_index - 1,
                stage=str(stage),
                title=str(title),
                summary=str(summary),
                detail=str(detail),
                actions_proposed=(chosen,),
                action_chosen=chosen,
                state_pool_top12=items,
                draft_changes=dict(draft_changes or {}),
                focus_xy=focus_xy,
                energy_RAPF=(real, attention, pressure, fatigue),
                cognitive_pressure=pressure,
                unresolved_pressure=max(0.0, min(1.0, pressure)),
                is_projection=False,
            )
        )


def _action_for_stage(stage: str, *, tick_index: int) -> ActionProposal:
    return ActionProposal(
        tick=int(tick_index),
        action_id=f"phase20_5a::{stage}",
        actuator_id="phase20_turn_loop",
        source_system="phase20_runtime_loop",
        outcome_kind="runtime_step",
        drive=1.0,
        evidence_tags=("runtime_tick_event", "not_projection"),
        payload={"stage": str(stage)},
    )


def _state_snapshot(
    family: str,
    label: str,
    real_energy: float,
    attention_energy: float,
    cognitive_pressure: float,
    channel_signature: Sequence[str],
) -> StateItemSnapshot:
    safe_label = str(label or "none")
    sa_id = f"phase20_5a::{family}::{_sha16(safe_label)[:12]}"
    return StateItemSnapshot(
        sa_id=sa_id,
        family=str(family),
        label=safe_label,
        real_energy=max(0.0, min(1.0, float(real_energy))),
        virtual_energy=max(0.0, min(1.0, _virtual_energy_for_family(str(family), tuple(str(item) for item in channel_signature)))),
        attention_energy=max(0.0, min(1.0, float(attention_energy))),
        cognitive_pressure=max(0.0, min(1.0, float(cognitive_pressure))),
        channel_signature=tuple(str(item) for item in channel_signature),
        source="phase20_runtime_loop",
    )


def _virtual_energy_for_family(family: str, channel_signature: Sequence[str]) -> float:
    channels = {str(item) for item in channel_signature}
    if "vision" in channels or family.startswith("visual"):
        return 0.08
    if "audio" in channels or family.startswith("audio"):
        return 0.08
    if "memory" in channels or family == "teacher_phrase":
        return 0.42
    if family in {"draft_box", "action_competition", "styled_expression", "context"}:
        return 0.56
    return 0.32


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


def _mean(values: Sequence[float] | Any) -> float:
    rows = [float(item) for item in values]
    if not rows:
        return 0.0
    return sum(rows) / len(rows)


def _bounded_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = int(default)
    return max(int(minimum), min(int(maximum), number))


def ap_perceive_and_reply(text: str = "", image_path: str | Path | None = None) -> AgentToolResult:
    session = Phase20MultimodalSession()
    return session.agent_tool(text=text, image_path=image_path)


def _object_views(objects: Sequence[ObjectFile]) -> tuple[Phase20ObjectView, ...]:
    return tuple(
        Phase20ObjectView(
            candidate_id=item.candidate.candidate_id,
            top_visible_label=item.recognition.top_visible_label,
            top_concept_uuid=item.recognition.top_concept_uuid,
            raw_confidence=float(item.recognition.raw_confidence),
            decision_tier=item.recognition.decision_tier,
            nearest_negative_margin=float(item.recognition.nearest_negative_margin),
            tick_seen=int(item.tick_seen),
        )
        for item in objects
    )


def _visual_state_items(object_views: Sequence[Phase20ObjectView]) -> tuple[Phase20ObjectView, ...]:
    return tuple(object_views)


def _situation_from(
    user_input: UserTurnInput,
    object_views: Sequence[Phase20ObjectView],
    feedback_trace: FeedbackTrace | None,
) -> str:
    if feedback_trace is not None:
        return "feedback_positive" if user_input.feedback_kind == "positive" else "feedback_negative"
    if not object_views:
        return "text_only"
    if any(item.decision_tier == "firm" for item in object_views):
        return "object_firm"
    if any(item.decision_tier == "soft" for item in object_views):
        return "object_soft"
    return "object_no_call"


def _situation_to_paradigm(situation: str) -> str:
    return {
        "feedback_positive": "PAR-D.02",
        "feedback_negative": "PAR-N.01",
        "object_firm": "PAR-A.02",
        "object_soft": "PAR-A.06",
        "object_no_call": "PAR-Q.06",
        "text_only": "PAR-Q.06",
    }.get(situation, "PAR-A.01")


def _context_signature(
    *,
    user_text_hash: str,
    has_image: bool,
    situation: str,
    object_views: Sequence[Phase20ObjectView],
    styled: StyledResponse,
    affect_evidence: Mapping[str, object] | None = None,
) -> tuple[str, dict[str, object]]:
    top = object_views[0] if object_views else None
    affect_evidence = affect_evidence or {}
    payload: dict[str, object] = {
        "schema_id": "apv3_phase20_1_context_signature/v1",
        "user_text_hash": str(user_text_hash or ""),
        "has_image": bool(has_image),
        "situation": str(situation),
        "object_count_bucket": min(len(object_views), 3),
        "top_concept_uuid": "" if top is None else top.top_concept_uuid,
        "top_decision_tier": "" if top is None else top.decision_tier,
        "styled_paradigm_id": styled.paradigm_id,
        "affect_bucket": str(affect_evidence.get("bucket", "")),
        "affect_confidence_bucket": _bucket_float(float(affect_evidence.get("confidence", 0.0) or 0.0)),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return f"phase20ctx::{_sha16(canonical)}", payload


def _text_affect_evidence(text: str) -> dict[str, object]:
    value = str(text or "").strip()
    lowered = value.lower()
    warm_cues = ("难过", "傷心", "伤心", "委屈", "害怕", "焦虑", "不舒服", "崩溃", "sad", "upset")
    sleepy_cues = ("困", "累", "疲惫", "sleepy", "tired")
    shy_cues = ("不好意思", "害羞", "尴尬")
    curious_cues = ("什么", "为什么", "怎么", "?", "？")
    if any(cue in lowered or cue in value for cue in warm_cues):
        bucket = "warm"
        confidence = 0.74
        pressure = 0.42
    elif any(cue in lowered or cue in value for cue in sleepy_cues):
        bucket = "sleepy"
        confidence = 0.64
        pressure = 0.32
    elif any(cue in lowered or cue in value for cue in shy_cues):
        bucket = "shy"
        confidence = 0.58
        pressure = 0.28
    elif any(cue in lowered or cue in value for cue in curious_cues):
        bucket = "curious"
        confidence = 0.46
        pressure = 0.22
    else:
        bucket = "calm"
        confidence = 0.22
        pressure = 0.12
    return {
        "schema_id": "apv3_phase20_6_text_affect_evidence/v1",
        "bucket": bucket,
        "confidence": confidence,
        "attention": min(0.85, 0.25 + confidence * 0.55),
        "pressure": pressure,
        "source": "text_affect_receptor_uncertain_sa",
        "direct_reply_authority": False,
    }


def _bucket_float(value: float) -> str:
    if value >= 0.66:
        return "high"
    if value >= 0.33:
        return "mid"
    return "low"


def _latest_phase20_context(state: Mapping[str, object]) -> Mapping[str, object]:
    direct = state.get("phase20_last_context")
    if isinstance(direct, Mapping) and direct.get("context_signature"):
        return direct
    rows = state.get("phase20_turn_trace", [])
    if isinstance(rows, list):
        for row in reversed(rows):
            if isinstance(row, Mapping) and row.get("context_signature"):
                return row
    return {}


def _teaching_tokens_from_text(text: str) -> tuple[str, ...]:
    value = str(text or "").strip()
    if not value:
        raise ValueError("empty_teaching_reply")
    if len(value) > PHASE20_2_MAX_TEACHING_REPLY_CHARS:
        raise ValueError("teaching_reply_too_long")
    return (value,)


def _phrase_id_for_teacher_text(response_text: str) -> str:
    return f"teacher_phrase::{_sha16(response_text)}"


def _observe_teacher_cooccurrence(
    state: dict[str, object],
    *,
    context_signature: str,
    response_text: str,
    response_tokens: Sequence[str],
    visual_sa_ids: Sequence[str],
    previous_reply_hash: str,
    tick: int,
) -> tuple[TaughtResponseCandidate, TeachingTrace]:
    phrase_id = _phrase_id_for_teacher_text(response_text)
    memory = ExpressionPhraseMemory.from_state(state.get("expression_phrase_memory"))
    assoc = CooccurrenceAssociationStore.from_state(state.get("cooccurrence_associations"))
    memory.observe(
        phrase_id,
        tuple(str(token) for token in response_tokens),
        weight=PHASE20_2_COOCCURRENCE_REWARD_WEIGHT,
        current_tick=int(tick),
        phrase_kind="teacher_event_cooccurrence",
        allow_new=True,
    )
    if not memory.tokens_for(phrase_id, current_tick=int(tick)):
        raise RuntimeError("phase20_teacher_phrase_memory_write_failed")
    weighted_source_sa_ids = _weighted_recall_labels(context_signature, visual_sa_ids)
    source_sa_ids = tuple(label for label, _weight in weighted_source_sa_ids)
    for source_sa_id, source_weight in weighted_source_sa_ids:
        assoc.observe(
            source_sa_id,
            phrase_id,
            weight=PHASE20_2_COOCCURRENCE_REWARD_WEIGHT * source_weight,
            current_tick=int(tick),
            paradigm_id=phrase_id,
        )

    penalties = [dict(item) for item in state.get("phase20_reply_penalties", []) if isinstance(item, Mapping)]
    penalty_id = f"phase20penalty::{_sha16(context_signature + '|' + previous_reply_hash)}"
    penalty_row = next((row for row in penalties if str(row.get("penalty_id", "")) == penalty_id), None)
    if penalty_row is None:
        penalty_row = {
            "schema_id": "apv3_phase20_1_previous_reply_penalty/v1",
            "penalty_id": penalty_id,
            "context_signature": context_signature,
            "reply_text_hash": previous_reply_hash,
            "punish_support": 0.0,
            "source": "teacher_event_cooccurrence_feedback",
        }
        penalties.append(penalty_row)
    penalty_row["punish_support"] = float(penalty_row.get("punish_support", 0.0)) + PHASE20_2_PREVIOUS_REPLY_PUNISH_DELTA
    penalty_row["last_update_tick"] = int(tick)

    events = [dict(item) for item in state.get("phase20_cooccurrence_teaching_events", []) if isinstance(item, Mapping)]
    teaching_id = f"phase20teach::{_sha16(context_signature + '|' + phrase_id + '|' + str(tick))}"
    events.append(
        {
            "schema_id": PHASE20_2_TEACHING_SCHEMA_ID,
            "teaching_id": teaching_id,
            "phrase_id": phrase_id,
            "context_signature": context_signature,
            "visual_sa_ids": list(source_sa_ids),
            "source": "teacher_event_cooccurrence",
            "tick": int(tick),
        }
    )
    state["expression_phrase_memory"] = memory.export_state()
    state["cooccurrence_associations"] = assoc.export_state()
    state["phase20_cooccurrence_teaching_events"] = events
    state["phase20_reply_penalties"] = penalties
    candidate = TaughtResponseCandidate(
        memory_id=phrase_id,
        source_sa_id=source_sa_ids[0] if source_sa_ids else context_signature,
        response_text=response_text,
        response_tokens=tuple(str(token) for token in response_tokens),
        support=PHASE20_2_COOCCURRENCE_REWARD_WEIGHT,
    )
    trace = TeachingTrace(
        teaching_id=teaching_id,
        target_context_signature=context_signature,
        response_text=response_text,
        response_tokens=tuple(str(token) for token in response_tokens),
        reward_delta=PHASE20_2_COOCCURRENCE_REWARD_WEIGHT,
        previous_reply_punish_delta=PHASE20_2_PREVIOUS_REPLY_PUNISH_DELTA,
        previous_reply_hash=previous_reply_hash,
        rewarded_teaching=True,
        punished_previous=bool(previous_reply_hash),
        visual_sa_ids=source_sa_ids,
    )
    return candidate, trace


def _observe_user_utterance_memory(
    state: dict[str, object],
    *,
    text: str,
    context_signature: str,
    visual_sa_ids: Sequence[str],
    tick: int,
) -> None:
    value = str(text or "").strip()
    if not value:
        return
    phrase_id = f"user_utterance::{_sha16(value)}"
    memory = ExpressionPhraseMemory.from_state(state.get("expression_phrase_memory"))
    assoc = CooccurrenceAssociationStore.from_state(state.get("cooccurrence_associations"))
    memory.observe(
        phrase_id,
        (value,),
        weight=0.55,
        current_tick=int(tick),
        phrase_kind="user_observed_utterance",
        allow_new=True,
    )
    source_sa_ids = tuple(dict.fromkeys((str(context_signature), *tuple(str(item) for item in visual_sa_ids if str(item)))))
    for source_sa_id in source_sa_ids:
        assoc.observe(
            source_sa_id,
            phrase_id,
            weight=0.55,
            current_tick=int(tick),
        )
    observations = [dict(item) for item in state.get("phase20_user_utterance_observations", []) if isinstance(item, Mapping)]
    observations.append(
        {
            "schema_id": "apv3_phase20_legacy_disabled_user_utterance_memory/v1",
            "phrase_id": phrase_id,
            "context_signature": str(context_signature),
            "visual_sa_ids": list(source_sa_ids),
            "text_hash": _sha16(value),
            "text_length": len(value),
            "tick": int(tick),
            "source": "current_session_user_observed_utterance",
        }
    )
    state["expression_phrase_memory"] = memory.export_state()
    state["cooccurrence_associations"] = assoc.export_state()
    state["phase20_user_utterance_observations"] = observations[-400:]


def _visual_sa_ids(object_views: Sequence[Phase20ObjectView]) -> tuple[str, ...]:
    ids: list[str] = []
    if object_views:
        ids.append(f"visual_scene::object_count::{min(len(object_views), 4)}")
    for item in object_views:
        ids.append(f"visual_object::{item.candidate_id}")
        if item.top_concept_uuid:
            ids.append(f"visual_concept::{item.top_concept_uuid}")
        ids.extend(item.visual_signature_ids)
        ids.extend(_visual_feature_sa_ids(item))
    return tuple(dict.fromkeys(ids))


def _visual_feature_sa_ids(item: Phase20ObjectView) -> tuple[str, ...]:
    focus = item.focus_xy or (0, 0)
    bbox = item.bbox or (0, 0, 0, 0)
    width = max(1, int(bbox[2]) - int(bbox[0]))
    height = max(1, int(bbox[3]) - int(bbox[1]))
    aspect = width / max(float(height), 1.0)
    return (
        f"visual_feature::area::{_bucket_float(float(item.area_ratio))}",
        f"visual_feature::saliency::{_bucket_float(float(item.raw_confidence))}",
        f"visual_feature::aspect::{_aspect_bucket(aspect)}",
        f"visual_feature::focus_grid::{_grid_bucket(focus[0])}:{_grid_bucket(focus[1])}",
    )


def _aspect_bucket(value: float) -> str:
    if value >= 1.75:
        return "wide"
    if value <= 0.7:
        return "tall"
    return "balanced"


def _grid_bucket(value: int) -> str:
    number = int(value)
    if number < 96:
        return "low"
    if number < 192:
        return "mid"
    return "high"


def _weighted_recall_labels(
    context_signature: str,
    visual_sa_ids: Sequence[str],
) -> tuple[tuple[str, float], ...]:
    rows: list[tuple[str, float]] = []
    has_visual = any(_is_visual_recall_label(str(item)) for item in visual_sa_ids)
    rows.append((str(context_signature), 0.05 if has_visual else 1.0))
    for raw in visual_sa_ids:
        label = str(raw)
        if not label:
            continue
        rows.append((label, _visual_sa_recall_weight(label)))
    merged: dict[str, float] = {}
    for label, weight in rows:
        merged[label] = max(float(weight), merged.get(label, 0.0))
    return tuple((label, weight) for label, weight in merged.items() if weight > 0.0)


def _visual_sa_recall_weight(label: str) -> float:
    value = str(label)
    if value.startswith("visual_object::"):
        return 0.42
    if value.startswith("visual_concept::visual_candidate::"):
        return 0.38
    if value.startswith("visual_signature::foveated_sketch::"):
        return 1.22
    if value.startswith("visual_signature::receptor_profile::"):
        return 0.92
    if value.startswith("visual_signature::compound::"):
        return 1.05
    if value.startswith("visual_signature::"):
        return 0.1
    if value.startswith("visual_feature::"):
        return 0.05
    if value.startswith("visual_scene::"):
        return 0.02
    return 0.2


def _is_visual_recall_label(label: str) -> bool:
    return str(label).startswith(("visual_object::", "visual_concept::", "visual_signature::", "visual_feature::", "visual_scene::"))


def _is_strong_visual_recall_label(label: str) -> bool:
    value = str(label)
    return value.startswith(("visual_signature::foveated_sketch::", "visual_signature::compound::", "visual_signature::receptor_profile::"))


def _visual_candidate_signatures(image_path: Path, candidates: Sequence[Any]) -> tuple[tuple[int, int] | None, dict[str, dict[str, object]]]:
    try:
        with Image.open(image_path) as raw:
            image = raw.convert("RGB")
    except Exception:
        return None, {}
    image_size = image.size
    edge_image = image.convert("L").filter(ImageFilter.FIND_EDGES)
    signatures: dict[str, dict[str, object]] = {}
    for candidate in candidates:
        bbox = tuple(int(v) for v in getattr(candidate, "bbox", (0, 0, image.width, image.height)))
        crop = image.crop(_clamped_bbox(bbox, image_size)).resize((24, 24))
        pixels = list(crop.getdata())
        objectish = [pixel for pixel in pixels if _pixel_objectish(pixel)]
        sample = objectish or pixels
        red = sum(pixel[0] for pixel in sample) / max(len(sample), 1)
        green = sum(pixel[1] for pixel in sample) / max(len(sample), 1)
        blue = sum(pixel[2] for pixel in sample) / max(len(sample), 1)
        hue, sat, val = colorsys.rgb_to_hsv(red / 255.0, green / 255.0, blue / 255.0)
        hue_bucket = _hue_bucket(hue)
        sat_bucket = _bucket_float(sat)
        val_bucket = _bucket_float(val)
        width = max(1, bbox[2] - bbox[0])
        height = max(1, bbox[3] - bbox[1])
        aspect_bucket = _aspect_bucket(width / max(float(height), 1.0))
        area_bucket = _bucket_float(float(getattr(candidate, "area_ratio", 0.0)))
        saliency_bucket = _bucket_float(float(getattr(candidate, "saliency", 0.0)))
        sketch = _build_visual_receptor_sketch(
            image,
            edge_image,
            bbox=bbox,
            focus_xy=tuple(int(v) for v in getattr(candidate, "focus_xy", ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2))),
            candidate_id=str(getattr(candidate, "candidate_id", "")),
        )
        sketch_hash = str(sketch.get("stable_signature", ""))
        edge_bucket = str(sketch.get("edge_bucket", "edge_low"))
        luma_bucket = str(sketch.get("luma_bucket", val_bucket))
        receptor_profile = "|".join((hue_bucket, sat_bucket, luma_bucket, aspect_bucket, edge_bucket))
        compound = "|".join((receptor_profile, area_bucket, saliency_bucket, sketch_hash[:12]))
        signature_ids = (
            f"visual_signature::compound::{_sha16(compound)}",
            f"visual_signature::foveated_sketch::{sketch_hash}",
            f"visual_signature::receptor_profile::{_sha16(receptor_profile)}",
            f"visual_signature::color::{hue_bucket}",
            f"visual_signature::saturation::{sat_bucket}",
            f"visual_signature::value::{val_bucket}",
            f"visual_signature::shape::{aspect_bucket}",
            f"visual_signature::edge::{edge_bucket}",
        )
        signatures[str(getattr(candidate, "candidate_id", ""))] = {
            "dominant_color_hex": f"#{int(red):02x}{int(green):02x}{int(blue):02x}",
            "shape_bucket": aspect_bucket,
            "signature_ids": signature_ids,
            "visual_receptor_sketch": sketch,
        }
    return image_size, signatures


def _build_visual_receptor_sketch(
    image: Image.Image,
    edge_image: Image.Image,
    *,
    bbox: tuple[int, int, int, int],
    focus_xy: tuple[int, int],
    candidate_id: str,
) -> dict[str, object]:
    width, height = image.size
    x1, y1, x2, y2 = _clamped_bbox(bbox, (width, height))
    if x2 <= x1 or y2 <= y1:
        x1, y1, x2, y2 = 0, 0, width, height
    fx = max(0, min(width - 1, int(focus_xy[0])))
    fy = max(0, min(height - 1, int(focus_xy[1])))
    samples: list[dict[str, object]] = []
    # Coarse object-wide receptor samples preserve shape/color/brightness/edge hints.
    grid_x = 28
    grid_y = 28
    for gy in range(grid_y):
        py = int(round(y1 + (gy + 0.5) * (y2 - y1) / grid_y))
        for gx in range(grid_x):
            px = int(round(x1 + (gx + 0.5) * (x2 - x1) / grid_x))
            samples.append(_visual_sample_payload(image, edge_image, px, py, width, height, "object_grid"))
    focus_path = _visual_focus_path((x1, y1, x2, y2), (fx, fy))
    # Dense foveal samples are taken from native pixels around multiple future
    # fixation points. Runtime only reveals the samples that have been looked at
    # by the current tick, so the inner picture becomes richer with saccades.
    radius = max(16, min(48, min(x2 - x1, y2 - y1) // 3 if min(x2 - x1, y2 - y1) > 0 else 24))
    foveal_side = 29
    for focus_index, (path_fx, path_fy) in enumerate(focus_path):
        for gy in range(foveal_side):
            py = int(round(path_fy - radius + gy * (2 * radius) / max(1, foveal_side - 1)))
            for gx in range(foveal_side):
                px = int(round(path_fx - radius + gx * (2 * radius) / max(1, foveal_side - 1)))
                if x1 <= px < x2 and y1 <= py < y2:
                    payload = _visual_sample_payload(image, edge_image, px, py, width, height, "foveal_native")
                    payload["focus_index"] = focus_index
                    payload["focus_x"] = round(path_fx / max(width - 1, 1) * 100.0, 4)
                    payload["focus_y"] = round(path_fy / max(height - 1, 1) * 100.0, 4)
                    samples.append(payload)
    stable_crop = image.crop((x1, y1, x2, y2)).resize((12, 12), Image.Resampling.BOX)
    stable_bytes = bytes(
        int(channel // 32) for pixel in stable_crop.getdata() for channel in pixel
    )
    stable_signature = hashlib.sha256(stable_bytes).hexdigest()[:16]
    mean_luma = sum(float(sample.get("luma", 0.0) or 0.0) for sample in samples) / max(len(samples), 1)
    mean_edge = sum(float(sample.get("edge", 0.0) or 0.0) for sample in samples) / max(len(samples), 1)
    return {
        "schema_id": "apv3_phase20_visual_receptor_sketch/v1",
        "source": "native_pixel_receptor_samples",
        "candidate_id": str(candidate_id),
        "image_size": [int(width), int(height)],
        "bbox": [int(x1), int(y1), int(x2), int(y2)],
        "focus_xy": [int(fx), int(fy)],
        "focus_path": [[int(px), int(py)] for px, py in focus_path],
        "focus_path_pct": [
            [
                round(px / max(width - 1, 1) * 100.0, 4),
                round(py / max(height - 1, 1) * 100.0, 4),
            ]
            for px, py in focus_path
        ],
        "stable_signature": stable_signature,
        "luma_bucket": _bucket_float(mean_luma),
        "edge_bucket": _bucket_float(mean_edge),
        "mean_luma": round(float(mean_luma), 4),
        "mean_edge": round(float(mean_edge), 4),
        "sample_count": len(samples),
        "samples": samples,
        "channels": ["native_rgb", "luma", "edge", "foveal_clarity"],
        "raw_image_path_persisted": False,
    }


def _visual_focus_path(
    bbox: tuple[int, int, int, int],
    center: tuple[int, int],
) -> tuple[tuple[int, int], ...]:
    x1, y1, x2, y2 = bbox
    cx, cy = center
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    offsets = (
        (0.0, 0.0),
        (-0.24, -0.18),
        (0.24, -0.16),
        (-0.2, 0.2),
        (0.22, 0.18),
        (0.0, -0.32),
        (0.0, 0.32),
        (-0.34, 0.0),
        (0.34, 0.0),
    )
    points: list[tuple[int, int]] = []
    for ox, oy in offsets:
        px = int(round(cx + ox * width))
        py = int(round(cy + oy * height))
        px = max(x1, min(x2 - 1, px))
        py = max(y1, min(y2 - 1, py))
        if (px, py) not in points:
            points.append((px, py))
    return tuple(points)


def _visual_sample_payload(
    image: Image.Image,
    edge_image: Image.Image,
    px: int,
    py: int,
    width: int,
    height: int,
    kind: str,
) -> dict[str, object]:
    x = max(0, min(width - 1, int(px)))
    y = max(0, min(height - 1, int(py)))
    red, green, blue = image.getpixel((x, y))
    edge = edge_image.getpixel((x, y)) / 255.0
    luma = (0.299 * red + 0.587 * green + 0.114 * blue) / 255.0
    return {
        "x": round(x / max(width - 1, 1) * 100.0, 4),
        "y": round(y / max(height - 1, 1) * 100.0, 4),
        "color": f"#{int(red):02x}{int(green):02x}{int(blue):02x}",
        "luma": round(float(luma), 4),
        "edge": round(float(edge), 4),
        "kind": kind,
    }


def _clamped_bbox(bbox: tuple[int, int, int, int], image_size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = image_size
    x1, y1, x2, y2 = bbox
    return (
        max(0, min(width - 1, int(x1))),
        max(0, min(height - 1, int(y1))),
        max(1, min(width, int(x2))),
        max(1, min(height, int(y2))),
    )


def _pixel_objectish(pixel: tuple[int, int, int]) -> bool:
    red, green, blue = pixel
    high = max(red, green, blue)
    low = min(red, green, blue)
    return (high - low) > 24 or high < 225


def _hue_bucket(hue: float) -> str:
    degree = (float(hue) % 1.0) * 360.0
    if degree < 25 or degree >= 340:
        return "red"
    if degree < 55:
        return "orange"
    if degree < 80:
        return "yellow"
    if degree < 160:
        return "green"
    if degree < 220:
        return "cyan"
    if degree < 285:
        return "blue"
    return "purple"


def _image_sha16(path: Path | None) -> str | None:
    if path is None:
        return None
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def _sha16(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


# Phase 20.5a2 repair: a workbench tick is a complete AP loop snapshot, not
# one named pipeline stage stretched into a fake tick.
def _legacy_workbench_turn_disabled(self: Phase20MultimodalSession, payload: Mapping[str, object] | UserTurnInput) -> Phase20TurnResult:
    turn_started = time.perf_counter()
    live_payload = payload if isinstance(payload, Mapping) else {}
    user_input = parse_user_input(payload)
    input_hash = _sha16(user_input.text) if user_input.text else ""
    timings: dict[str, float] = {}
    step_started = time.perf_counter()
    feedback_trace = self._process_feedback(user_input)
    timings["feedback_ms"] = _elapsed_ms(step_started)
    step_started = time.perf_counter()
    object_result = self._process_image(user_input.image_path) if user_input.image_path is not None else None
    timings["visual_ms"] = _elapsed_ms(step_started)
    object_views = _object_views(object_result.objects if object_result is not None else ())
    visual_items = tuple(
        _state_snapshot(
            "visual_object",
            item.top_visible_label or item.top_concept_uuid,
            max(item.raw_confidence, 0.0),
            max(item.raw_confidence, 0.0),
            1.0 - max(min(item.raw_confidence, 1.0), 0.0),
            ("vision", "object_file"),
        )
        for item in object_views[:6]
    )

    step_started = time.perf_counter()
    runtime_turn = self.chat.say(user_input.text)
    timings["text_runtime_ms"] = _elapsed_ms(step_started)
    situation = _situation_from(user_input, object_views, feedback_trace)
    step_started = time.perf_counter()
    styled = self.styled_corpus.select(
        situation=situation,
        seed_text=f"{runtime_turn.user_text_hash}:{situation}:{len(object_views)}",
    )
    timings["style_ms"] = _elapsed_ms(step_started)
    context_signature, context_payload = _context_signature(
        user_text_hash=runtime_turn.user_text_hash,
        has_image=user_input.image_path is not None,
        situation=situation,
        object_views=object_views,
        styled=styled,
    )
    visual_sa_ids = _visual_sa_ids(object_views)
    step_started = time.perf_counter()
    taught = self._select_taught_response(context_signature, visual_sa_ids)
    timings["recall_ms"] = _elapsed_ms(step_started)
    step_started = time.perf_counter()
    if taught is not None:
        reply_tokens = taught.response_tokens
        reply_text = "".join(taught.response_tokens)
    else:
        reply_tokens = assemble_reply_tokens(styled, object_views, runtime_turn.reply_tokens)
        reply_text = assemble_reply_text(styled, object_views, reply_tokens)
    assert_style_compliant(reply_tokens, max_tokens=self.chat.profile.style_max_tokens)
    timings["draft_assembly_ms"] = _elapsed_ms(step_started)
    image_sha16 = _image_sha16(user_input.image_path) if user_input.image_path is not None else None
    timings["turn_elapsed_ms"] = _elapsed_ms(turn_started)

    runtime_events = tuple(
        event.to_dict()
        for event in _legacy_workbench_ticks_disabled(
            base_tick=runtime_turn.tick,
            max_ticks=_bounded_int(live_payload.get("max_ticks"), default=8, minimum=4, maximum=24),
            idle_ticks=_bounded_int(live_payload.get("idle_ticks"), default=2, minimum=0, maximum=8),
            user_text_hash=input_hash,
            user_text_length=len(user_input.text),
            has_image=user_input.image_path is not None,
            visual_items=visual_items,
            object_views=object_views,
            runtime_turn=runtime_turn,
            taught=taught,
            styled=styled,
            reply_text=reply_text,
            reply_tokens=reply_tokens,
            context_signature=context_signature,
            process_timing_ms=timings,
        )
    )
    result = Phase20TurnResult(
        tick=runtime_turn.tick,
        reply_text=reply_text,
        reply_tokens=reply_tokens,
        object_files=object_views,
        feedback_trace=feedback_trace,
        styled_response=styled,
        user_text_hash=runtime_turn.user_text_hash,
        image_sha16=image_sha16,
        runtime_turn=runtime_turn,
        metadata={
            "schema_id": "apv3_phase20_1_turn/v1",
            "source_boundary": "text_user_only_visual_separate",
            "raw_image_persisted": False,
            "zvec_commit": "not_in_phase20_0",
            "context_signature": context_signature,
            "context_signature_components": context_payload,
            "teaching_candidate_applied": taught is not None,
            "teaching_id": taught.memory_id if taught is not None else "",
            "teaching_source": taught.source if taught is not None else "",
            "visual_sa_ids": visual_sa_ids,
            "runtime_tick_events": runtime_events,
            "runtime_tick_event_source": "phase20_5a2_per_tick_workbench_snapshot",
            "runtime_tick_projection": False,
        },
    )
    self._persist_phase20_trace(result, user_input)
    self.last_turn = result
    return result


def _legacy_workbench_ticks_disabled(
    *,
    base_tick: int,
    max_ticks: int,
    idle_ticks: int,
    user_text_hash: str,
    user_text_length: int,
    has_image: bool,
    visual_items: Sequence[StateItemSnapshot],
    object_views: Sequence[Phase20ObjectView],
    runtime_turn: ChatTurn,
    taught: TaughtResponseCandidate | None,
    styled: StyledResponse,
    reply_text: str,
    reply_tokens: Sequence[str],
    context_signature: str,
    process_timing_ms: Mapping[str, float] | None = None,
) -> tuple[RuntimeTickEvent, ...]:
    tokens = _reply_graphemes(reply_tokens, reply_text)
    draft_runner = DraftActionRunner()
    draft_state: dict[str, Any] = {}
    events: list[RuntimeTickEvent] = []
    cognitive_items = (
        _state_snapshot("phase20_input", user_text_hash or "empty", 0.4, 0.35, 0.2, ("text", "external_user")),
        _state_snapshot("dialogue_feeling", runtime_turn.feeling_label or "feeling", 0.6, 0.55, 0.35, ("text", "dialogue_runtime")),
        _state_snapshot("context", context_signature, 0.55, 0.5, 0.25, ("context", "phase20")),
        _state_snapshot("styled_expression", styled.paradigm_id, 0.5, 0.45, 0.2, ("style", "expression")),
    )
    if taught is not None:
        cognitive_items = (
            *cognitive_items,
            _state_snapshot("teacher_phrase", taught.memory_id, min(taught.support, 1.0), min(taught.support, 1.0), 0.1, ("memory", "cooccurrence")),
        )

    write_ticks = min(len(tokens), max(0, max_ticks - 1))
    tick_count = max(1, write_ticks + 1 + max(0, idle_ticks))
    tick_count = min(max_ticks + max(0, idle_ticks), tick_count)
    for offset in range(tick_count):
        tick_index = offset + 1
        runtime_tick = int(base_tick) + offset
        token = tokens[offset] if offset < write_ticks else ""
        if token:
            draft_state = draft_runner.apply(
                draft_state,
                DraftTextAction(tick=runtime_tick, kind="type_text", text=token),
            )
            draft_action_kind = "type_text"
        elif offset == write_ticks:
            draft_state = draft_runner.apply(
                draft_state,
                DraftTextAction(tick=runtime_tick, kind="commit"),
            )
            draft_action_kind = "commit"
        else:
            draft_action_kind = "idle_observe"
        draft_runtime = dict(draft_state.get("draft_runtime", {})) if isinstance(draft_state.get("draft_runtime"), Mapping) else {}
        draft_buffer = str(draft_runtime.get("buffer", ""))
        commits = draft_runtime.get("commits", [])
        committed_text = ""
        if isinstance(commits, list) and commits and isinstance(commits[-1], Mapping):
            committed_text = str(commits[-1].get("text", ""))
        stage = "ap_tick_loop" if draft_action_kind != "idle_observe" else "idle_tick_loop"
        title = f"tick {tick_index}"
        if draft_action_kind == "type_text":
            summary = f"读入证据并向草稿框写入 `{token}`。"
            detail = "同一 tick 内同时保留输入感受、视觉候选、共现召回、风格候选和草稿动作；不是阶段流水线。"
        elif draft_action_kind == "commit":
            summary = "草稿框内容达到提交点，执行 commit。"
            detail = "20.5a2 记录草稿 commit 快照；主动停与 stop/request_teacher 竞争仍留到 20.5b。"
        else:
            summary = "提交后空 tick，保持最近工作状态并等待下一轮。"
            detail = "空 tick 不伪造额外推理，只显示工作记忆残留。"
        state_items = _tick_state_items(
            cognitive_items=cognitive_items,
            visual_items=visual_items,
            tick_index=tick_index,
            draft_action_kind=draft_action_kind,
            draft_buffer=draft_buffer,
            committed_text=committed_text,
        )
        action = _action_for_stage(draft_action_kind, tick_index=tick_index)
        real = _mean(item.real_energy for item in state_items)
        attention = _mean(item.attention_energy for item in state_items)
        pressure = 0.1 if draft_action_kind in {"commit", "idle_observe"} else max(0.15, 0.6 - min(0.5, offset * 0.08))
        fatigue = max(0.0, min(1.0, float(offset) * 0.03))
        focus_xy = _focus_for_tick(tick_index=tick_index, object_count=len(object_views), has_image=has_image)
        inner_picture_state = _inner_picture_state_for_tick(
            tick_index=tick_index,
            has_image=has_image,
            focus_xy=focus_xy,
            state_items=state_items,
            object_views=object_views,
        )
        audit_metrics = _audit_metrics_for_tick(
            tick_index=tick_index,
            tick_count=tick_count,
            state_items=state_items,
            object_views=object_views,
            draft_buffer=draft_buffer,
            committed_text=committed_text,
            taught=taught,
            process_timing_ms=process_timing_ms or {},
            energy_RAPF=(real, attention, pressure, fatigue),
        )
        events.append(
            RuntimeTickEvent(
                tick_index=tick_index,
                runtime_tick=runtime_tick,
                stage=stage,
                title=title,
                summary=summary,
                detail=detail,
                actions_proposed=(action,),
                action_chosen=action,
                state_pool_top12=state_items,
                draft_changes={
                    "schema_id": "apv3_phase20_legacy_disabled_draft_snapshot/v1",
                    "draft_action_kind": draft_action_kind,
                    "typed_token": token,
                    "draft_buffer": draft_buffer,
                    "committed_text": committed_text,
                    "reply_target_hash": _sha16(reply_text),
                    "reply_token_count": len(tokens),
                    "context_signature": context_signature,
                    "teaching_candidate_applied": taught is not None,
                    "teaching_id": taught.memory_id if taught is not None else "",
                    "input_text_hash": user_text_hash,
                    "input_text_length": int(user_text_length),
                    "has_image": bool(has_image),
                    "object_count": len(object_views),
                    "object_labels": [item.top_visible_label for item in object_views[:6]],
                    "candidate_phrase_ids": [],
                    "state_pool_count": len(state_items),
                    "audit_metrics": audit_metrics,
                },
                focus_xy=focus_xy,
                inner_picture_state=inner_picture_state,
                energy_RAPF=(real, attention, pressure, fatigue),
                cognitive_pressure=pressure,
                unresolved_pressure=pressure,
                is_projection=False,
                source="phase20_5a2_workbench_tick_loop",
            )
        )
    return tuple(events)


def _elapsed_ms(start: float) -> float:
    return round(max(0.0, (time.perf_counter() - float(start)) * 1000.0), 3)


def _tick_state_items(
    *,
    cognitive_items: Sequence[StateItemSnapshot],
    visual_items: Sequence[StateItemSnapshot],
    tick_index: int,
    draft_action_kind: str,
    draft_buffer: str,
    committed_text: str,
) -> tuple[StateItemSnapshot, ...]:
    phase = max(0.0, min(1.0, float(tick_index - 1) * 0.12))
    visual_scaled: list[StateItemSnapshot] = []
    for index, item in enumerate(visual_items):
        boost = max(0.0, 1.0 - abs(index - ((tick_index - 1) % max(1, len(visual_items)))) * 0.22)
        visual_scaled.append(
            StateItemSnapshot(
                sa_id=item.sa_id,
                family=item.family,
                label=item.label,
                real_energy=max(0.0, min(1.0, item.real_energy * (0.62 + 0.32 * boost))),
                virtual_energy=item.virtual_energy,
                attention_energy=max(0.0, min(1.0, item.attention_energy * (0.55 + 0.38 * boost))),
                cognitive_pressure=item.cognitive_pressure,
                channel_signature=item.channel_signature,
                source=item.source,
            )
        )
    draft_label = draft_buffer or committed_text or draft_action_kind
    dynamic_items = (
        _state_snapshot("draft_box", draft_label, min(0.85, 0.28 + phase), min(0.9, 0.35 + phase), 0.2, ("draft", "text")),
        _state_snapshot("action_competition", draft_action_kind, 0.42, 0.58, 0.32, ("action", draft_action_kind)),
    )
    return tuple((*dynamic_items, *cognitive_items, *tuple(visual_scaled)))[:12]


def _focus_for_tick(*, tick_index: int, object_count: int, has_image: bool) -> tuple[int, int] | None:
    if not has_image:
        return None
    path = ((28, 35), (54, 42), (72, 58), (42, 68), (61, 31), (36, 52))
    index = (max(1, int(tick_index)) - 1) % len(path)
    if object_count <= 1:
        return path[index]
    return path[(index + min(object_count, len(path)) - 1) % len(path)]


def _inner_picture_state_for_tick(
    *,
    tick_index: int,
    has_image: bool,
    focus_xy: tuple[int, int] | None,
    state_items: Sequence[StateItemSnapshot],
    object_views: Sequence[Phase20ObjectView],
) -> dict[str, Any]:
    visual_states = [item for item in state_items if "vision" in item.channel_signature or item.family.startswith("visual")]
    layers: list[dict[str, Any]] = []
    for index, item in enumerate(sorted(visual_states, key=lambda row: row.attention_energy, reverse=True)[:6]):
        energy = max(0.0, min(1.0, (float(item.real_energy) + float(item.attention_energy)) / 2.0))
        layers.append(
            {
                "sa_id": item.sa_id,
                "label": item.label,
                "opacity": round(0.18 + 0.72 * energy, 4),
                "scale": round(0.62 + 0.58 * energy, 4),
                "depth": index,
                "x": 18 + ((index * 23 + tick_index * 11) % 64),
                "y": 22 + ((index * 17 + tick_index * 7) % 54),
                "energy": round(energy, 6),
            }
        )
    return {
        "schema_id": "apv3_phase20_5a3_inner_picture_state/v1",
        "enabled": bool(has_image and layers),
        "source": "state_pool_energy_reconstruction_not_original_asset",
        "focus_xy": list(focus_xy) if focus_xy is not None else None,
        "object_count": len(object_views),
        "tick_index": int(tick_index),
        "layers": layers,
    }


def _audit_metrics_for_tick(
    *,
    tick_index: int,
    tick_count: int,
    state_items: Sequence[StateItemSnapshot],
    object_views: Sequence[Phase20ObjectView],
    draft_buffer: str,
    committed_text: str,
    taught: TaughtResponseCandidate | None,
    process_timing_ms: Mapping[str, float],
    energy_RAPF: tuple[float, float, float, float],
) -> dict[str, Any]:
    real, attention, pressure, fatigue = energy_RAPF
    visual_count = sum(1 for item in state_items if "vision" in item.channel_signature or item.family.startswith("visual"))
    text_count = sum(1 for item in state_items if "text" in item.channel_signature or item.family in {"phase20_input", "dialogue_feeling", "draft_box"})
    memory_count = sum(1 for item in state_items if "memory" in item.channel_signature or item.family == "teacher_phrase")
    total_timing = sum(float(value) for value in process_timing_ms.values() if isinstance(value, (int, float)))
    return {
        "schema_id": "apv3_phase20_5a3_tick_audit_metrics/v1",
        "tick_index": int(tick_index),
        "tick_count": int(tick_count),
        "runtime_ms": round(float(process_timing_ms.get("turn_elapsed_ms", total_timing)), 3),
        "process_timing_ms": {str(key): round(float(value), 3) for key, value in process_timing_ms.items()},
        "state_pool_count": len(state_items),
        "visual_state_count": visual_count,
        "text_state_count": text_count,
        "memory_state_count": memory_count,
        "object_file_count": len(object_views),
        "draft_length": len(draft_buffer),
        "committed_length": len(committed_text),
        "recall_hit": 1 if taught is not None else 0,
        "mean_real_energy": round(float(real), 6),
        "mean_attention_energy": round(float(attention), 6),
        "mean_cognitive_pressure": round(float(pressure), 6),
        "mean_fatigue": round(float(fatigue), 6),
        "max_attention_energy": round(max((float(item.attention_energy) for item in state_items), default=0.0), 6),
        "max_real_energy": round(max((float(item.real_energy) for item in state_items), default=0.0), 6),
    }


def _reply_graphemes(reply_tokens: Sequence[str], reply_text: str) -> tuple[str, ...]:
    text = str(reply_text or "") or "".join(str(item) for item in reply_tokens if str(item))
    return tuple(text)
