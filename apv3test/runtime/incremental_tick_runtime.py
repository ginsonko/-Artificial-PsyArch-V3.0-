from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from apv3test.runtime.dialogue_runtime import DialogueTurnInput, DialogueTurnResult, MinimalDialogueRuntime
from apv3test.runtime.cooccurrence_store import CooccurrenceAssociationStore
from apv3test.runtime.draft_introspection import emit_draft_introspection_feelings
from apv3test.runtime.incremental_paradigm import (
    IncrementalParadigmLearner,
    IncrementalParadigmObservation,
    IncrementalParadigmUpdate,
)
from apv3test.runtime.paradigm_recall import ParadigmRecallAttention, ParadigmRecallResult
from apv3test.runtime.paradigm_recall import _paradigm_from_state
from apv3test.runtime.reply_pressure import reply_pressure_requires_response, update_reply_pressure_state


@dataclass(frozen=True)
class IncrementalTickInput:
    tick: int
    case_name: str = ""
    cue_tokens: tuple[str, ...] = ()
    reply_tokens: tuple[str, ...] = ()
    focus_tokens: tuple[str, ...] = ()
    candidate_pool: tuple[str, ...] = ()
    context_tokens: tuple[str, ...] = ()
    source_kind: str = "natural"
    teacher_stage: str = ""
    commit_observation: bool = False
    reward_delta: float = 0.0
    punish_delta: float = 0.0
    emit_reply: bool = False
    commit_after_draft: bool = False
    idle: bool = False
    grasp: float = 0.0
    demand_slow: float = 0.0
    incoming_external_query: tuple[str, ...] = ()


@dataclass(frozen=True)
class IncrementalTickResult:
    state: dict[str, Any]
    learning_update: IncrementalParadigmUpdate | None
    dialogue_result: DialogueTurnResult | None
    recall_result: ParadigmRecallResult | None
    staged_observation: bool
    idle_settled_bucket: str


class IncrementalTickRuntime:
    """Connect incremental paradigm learning to the minimal tick runtime.

    The class is orchestration only. It stages uncommitted observations, lets
    commit/feedback create AP-native learning evidence, and reuses the existing
    low-granularity dialogue runtime when a paradigm is available.
    """

    def __init__(
        self,
        *,
        learner: IncrementalParadigmLearner | None = None,
        dialogue_runtime: MinimalDialogueRuntime | None = None,
        recall_attention: ParadigmRecallAttention | None = None,
    ) -> None:
        self.learner = learner or IncrementalParadigmLearner()
        self.dialogue_runtime = dialogue_runtime or MinimalDialogueRuntime()
        self.recall_attention = recall_attention or ParadigmRecallAttention()

    def run_tick(
        self,
        state: Mapping[str, Any],
        tick_input: IncrementalTickInput,
    ) -> IncrementalTickResult:
        next_state = _ensure_tick_state(deepcopy(dict(state)))
        next_state = update_reply_pressure_state(
            next_state,
            current_tick=tick_input.tick,
            incoming_external_query=tick_input.incoming_external_query,
            commit_happened=bool(tick_input.commit_observation),
        )
        if tick_input.idle:
            settled = _settle_one_dirty_bucket(next_state, tick_input.tick)
            return IncrementalTickResult(next_state, None, None, None, False, settled)

        if tick_input.emit_reply and not tick_input.reply_tokens and not tick_input.commit_observation:
            return self._run_recall_turn(next_state, tick_input)

        observation_id = _observation_id(tick_input)
        should_learn = (
            bool(tick_input.commit_observation)
            or float(tick_input.reward_delta) > 0.0
            or float(tick_input.punish_delta) > 0.0
        )
        if not should_learn:
            _stage_pending_observation(next_state, tick_input, observation_id)
            return IncrementalTickResult(next_state, None, None, None, True, "")

        observation = IncrementalParadigmObservation(
            observation_id=observation_id,
            case_name=tick_input.case_name,
            cue_tokens=tick_input.cue_tokens,
            reply_tokens=tick_input.reply_tokens,
            tick_id=tick_input.tick,
            context_tokens=tick_input.context_tokens,
            committed=True,
            reward_delta=tick_input.reward_delta,
            punish_delta=tick_input.punish_delta,
            source_kind=tick_input.source_kind,
            teacher_stage=tick_input.teacher_stage,
        )
        update = self.learner.ingest(next_state, observation)
        next_state = _resolve_pending_observation(update.state, tick_input, observation_id)

        dialogue_result: DialogueTurnResult | None = None
        if tick_input.emit_reply and update.discovered is not None and update.exposed:
            dialogue_result = self.dialogue_runtime.run_turn(
                next_state,
                paradigm=update.discovered,
                turn=DialogueTurnInput(
                    tick=tick_input.tick + 1,
                    focus_tokens=tick_input.reply_tokens,
                    candidate_pool=tick_input.reply_tokens,
                    current_context_tags=tick_input.context_tokens,
                    commit_after_draft=tick_input.commit_after_draft,
                    grasp=tick_input.grasp,
                    demand_slow=tick_input.demand_slow,
                ),
                commit_episode_id=f"commit:{observation_id}" if tick_input.commit_after_draft else None,
            )
            next_state = dialogue_result.state
        return IncrementalTickResult(next_state, update, dialogue_result, None, False, "")

    def _run_recall_turn(
        self,
        state: dict[str, Any],
        tick_input: IncrementalTickInput,
    ) -> IncrementalTickResult:
        recall = self.recall_attention.recall(
            state,
            cue_tokens=tick_input.cue_tokens,
            context_tokens=tick_input.context_tokens,
        )
        dialogue_result: DialogueTurnResult | None = None
        next_state = state
        if recall.focus is not None and recall.focus.cn is not None and recall.focus.bn.paradigm is not None:
            focus_tokens = tuple(tick_input.focus_tokens)
            candidate_pool = _unique_tokens((*tick_input.candidate_pool, *focus_tokens))
            dialogue_result = self.dialogue_runtime.run_turn(
                state,
                paradigm=recall.focus.bn.paradigm,
                turn=DialogueTurnInput(
                    tick=tick_input.tick + 1,
                    focus_tokens=focus_tokens,
                    candidate_pool=candidate_pool,
                    current_context_tags=tick_input.context_tokens,
                    commit_after_draft=tick_input.commit_after_draft,
                    grasp=tick_input.grasp,
                    demand_slow=tick_input.demand_slow,
                ),
                commit_episode_id=f"commit:recall:{tick_input.tick}:{recall.focus.pid}"
                if tick_input.commit_after_draft
                else None,
            )
            next_state = dialogue_result.state
            if reply_pressure_requires_response(next_state) and _has_undecidable_fragment(dialogue_result):
                uncertainty = self._run_learned_expression_reply(next_state, tick_input, dialogue_result)
                if uncertainty is not None:
                    dialogue_result = uncertainty
                    next_state = uncertainty.state
        return IncrementalTickResult(next_state, None, dialogue_result, recall, False, "")

    def _run_learned_expression_reply(
        self,
        state: dict[str, Any],
        tick_input: IncrementalTickInput,
        uncertain_result: DialogueTurnResult,
    ) -> DialogueTurnResult | None:
        views = _draft_views_from_uncertain_result(uncertain_result)
        if not views:
            return None
        observed_state = emit_draft_introspection_feelings(state, views, current_tick=tick_input.tick)
        feeling_labels = tuple(
            str(item.get("sa_label", ""))
            for item in observed_state.get("introspection_feelings", [])
            if isinstance(item, dict) and int(item.get("tick", -1)) == int(tick_input.tick)
        )
        if not feeling_labels:
            return None
        store = CooccurrenceAssociationStore.from_state(observed_state.get("cooccurrence_associations"))
        candidate_pids = store.nearest_paradigms_by_label(
            feeling_labels,
            top_k=3,
            current_tick=tick_input.tick,
        )
        for pid in candidate_pids:
            paradigm = _lookup_paradigm_by_pid(observed_state, pid)
            if paradigm is None:
                continue
            expression_state = _clear_uncommitted_draft_buffer(observed_state)
            return self.dialogue_runtime.run_turn(
                expression_state,
                paradigm=paradigm,
                turn=DialogueTurnInput(
                    tick=tick_input.tick + 1 + len(uncertain_result.action_traces),
                    focus_tokens=uncertain_result.emitted_tokens,
                    candidate_pool=uncertain_result.emitted_tokens,
                    current_context_tags=tick_input.context_tokens,
                    commit_after_draft=tick_input.commit_after_draft,
                    grasp=tick_input.grasp,
                    demand_slow=tick_input.demand_slow,
                ),
                commit_episode_id=f"commit:learned_expression:{tick_input.tick}:{pid}"
                if tick_input.commit_after_draft
                else None,
            )
        return DialogueTurnResult(
            state=observed_state,
            draft_candidates=uncertain_result.draft_candidates,
            action_traces=uncertain_result.action_traces,
            emitted_tokens=uncertain_result.emitted_tokens,
            committed_text=uncertain_result.committed_text,
        )

def _ensure_tick_state(state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("schema_id", "apv3_runtime_ontology_state/v1")
    state.setdefault("pending_paradigm_observations", [])
    state.setdefault("idle_paradigm_maintenance", [])
    return state


def _stage_pending_observation(state: dict[str, Any], tick_input: IncrementalTickInput, observation_id: str) -> None:
    pending = state["pending_paradigm_observations"]
    if not isinstance(pending, list):
        state["pending_paradigm_observations"] = []
        pending = state["pending_paradigm_observations"]
    pending.append(
        {
            "schema_id": "apv3_pending_paradigm_observation/v1",
            "observation_id": observation_id,
            "case_name": tick_input.case_name,
            "cue_tokens": list(tick_input.cue_tokens),
            "reply_tokens": list(tick_input.reply_tokens),
            "tick": int(tick_input.tick),
            "context_tokens": list(tick_input.context_tokens),
            "source_kind": tick_input.source_kind,
            "teacher_stage": tick_input.teacher_stage,
        }
    )


def _resolve_pending_observation(
    state: dict[str, Any],
    tick_input: IncrementalTickInput,
    observation_id: str,
) -> dict[str, Any]:
    pending = state.get("pending_paradigm_observations", [])
    if not isinstance(pending, list):
        return state
    compatible_ids = {
        observation_id,
        _observation_id(
            IncrementalTickInput(
                tick=tick_input.tick - 1,
                case_name=tick_input.case_name,
                cue_tokens=tick_input.cue_tokens,
                reply_tokens=tick_input.reply_tokens,
                context_tokens=tick_input.context_tokens,
                source_kind=tick_input.source_kind,
                teacher_stage=tick_input.teacher_stage,
            )
        ),
    }
    state["pending_paradigm_observations"] = [
        item
        for item in pending
        if not isinstance(item, dict) or str(item.get("observation_id", "")) not in compatible_ids
    ]
    return state


def _settle_one_dirty_bucket(state: dict[str, Any], tick: int) -> str:
    dirty = state.get("dirty_paradigm_buckets", [])
    if not isinstance(dirty, list) or not dirty:
        return ""
    bucket = str(dirty.pop())
    maintenance = state["idle_paradigm_maintenance"]
    if not isinstance(maintenance, list):
        state["idle_paradigm_maintenance"] = []
        maintenance = state["idle_paradigm_maintenance"]
    maintenance.append({"tick": int(tick), "bucket": bucket, "kind": "dirty_bucket_settled"})
    return bucket


def _observation_id(tick_input: IncrementalTickInput) -> str:
    cue = " ".join(tick_input.cue_tokens)
    reply = " ".join(tick_input.reply_tokens)
    return f"tick:{int(tick_input.tick)}:{tick_input.case_name}:{cue}->{reply}:{tick_input.source_kind}"


def _unique_tokens(values: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)


def _has_undecidable_fragment(result: DialogueTurnResult) -> bool:
    return any(bool(item.anchor_meta.get("undecidable_fragment", False)) for item in result.draft_candidates)


@dataclass(frozen=True)
class _DraftView:
    role: str
    is_filled: bool
    fit_margin: float
    occupancy: float
    commit_readiness: float


def _draft_views_from_uncertain_result(result: DialogueTurnResult) -> tuple[_DraftView, ...]:
    views: list[_DraftView] = []
    for candidate in result.draft_candidates:
        unresolved = int(candidate.anchor_meta.get("unresolved_slots_before", 0))
        if bool(candidate.anchor_meta.get("undecidable_fragment", False)) and unresolved > 0:
            for _ in range(unresolved):
                views.append(_DraftView("slot", False, 0.0, 0.0, 0.0))
        views.append(
            _DraftView(
                role=candidate.role,
                is_filled=True,
                fit_margin=min(1.0, max(0.0, float(candidate.strength))),
                occupancy=1.0,
                commit_readiness=0.35 if bool(candidate.anchor_meta.get("undecidable_fragment", False)) else 0.8,
            )
        )
    return tuple(views)


def _lookup_paradigm_by_pid(state: dict[str, Any], pid: str):
    rows = state.get("paradigms", [])
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict) or str(row.get("pid", "")) != str(pid):
            continue
        anchor_meta = row.get("anchor_meta", {})
        bucket = str(anchor_meta.get("bucket", "")) if isinstance(anchor_meta, dict) else ""
        if not bucket:
            continue
        return _paradigm_from_state(state, row, bucket)
    return None


def _clear_uncommitted_draft_buffer(state: dict[str, Any]) -> dict[str, Any]:
    next_state = deepcopy(dict(state))
    runtime = next_state.get("draft_runtime", {})
    if isinstance(runtime, dict):
        runtime["buffer"] = ""
        runtime["cursor"] = 0
    return next_state
