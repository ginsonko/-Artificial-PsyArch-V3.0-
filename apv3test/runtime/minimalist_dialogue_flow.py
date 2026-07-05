from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from apv3test.runtime.cooccurrence_learning import observe_existing_phrase_cooccurrence
from apv3test.runtime.cooccurrence_store import CooccurrenceAssociationStore
from apv3test.runtime.draft_introspection import emit_draft_introspection_feelings
from apv3test.runtime.expression_phrase_memory import ExpressionPhraseMemory
from apv3test.runtime.style_redlines import style_safe_tokens


class MinimalistDialogueView(Protocol):
    @property
    def fit_margin(self) -> float: ...

    @property
    def occupancy(self) -> float: ...

    @property
    def commit_readiness(self) -> float: ...

    @property
    def role(self) -> str: ...

    @property
    def is_filled(self) -> bool: ...


@dataclass(frozen=True)
class MinimalistDialogueTurnInput:
    tick: int
    incoming_external_query: tuple[str, ...] = ()
    incoming_query_hash: str | None = None
    incoming_query_count: int = 0
    incoming_query_total_length: int = 0
    context_tokens: tuple[str, ...] = ()
    views: tuple[MinimalistDialogueView, ...] = ()
    observed_expression_tokens: tuple[str, ...] = ()
    observed_expression_origin: str = "perception_other"
    observed_attention_weight: float = 0.8
    reward_delta: float = 0.0
    punish_delta: float = 0.0
    top_k: int = 8


@dataclass(frozen=True)
class MinimalistDialogueTurnResult:
    state: dict[str, Any]
    feeling_label: str
    learned_phrase_id: str
    candidate_phrase_ids: tuple[str, ...]
    committed_tokens: tuple[str, ...]
    committed_text: str
    committed_phrase_id: str
    feedback_target_phrase_id: str


class MinimalistDialogueFlowRuntime:
    """Multi-turn AP-native minimalist expression flow."""

    def __init__(self, seed_corpus_path: str | Path | None = None) -> None:
        self.seed_corpus_path = Path(seed_corpus_path) if seed_corpus_path is not None else _default_seed_path()

    def run_turn(
        self,
        state: Mapping[str, Any],
        turn: MinimalistDialogueTurnInput,
    ) -> MinimalistDialogueTurnResult:
        next_state = dict(state)
        phrase_memory = _phrase_memory_from_state(next_state, self.seed_corpus_path)
        cooccurrence = CooccurrenceAssociationStore.from_state(next_state.get("cooccurrence_associations"))
        trace = _trace_from_state(next_state)

        previous_pid = str(next_state.get("last_committed_phrase_id", ""))
        if previous_pid and turn.punish_delta > 0.0:
            phrase_memory.adjust_support(previous_pid, delta=-abs(float(turn.punish_delta)), current_tick=turn.tick)
        if previous_pid and turn.reward_delta > 0.0:
            phrase_memory.adjust_support(previous_pid, delta=abs(float(turn.reward_delta)), current_tick=turn.tick)

        observed_state = emit_draft_introspection_feelings(
            next_state,
            turn.views,
            current_tick=turn.tick,
            paradigm_competition=_context_competition(turn.context_tokens),
        )
        label = _latest_label(observed_state, turn.tick)

        learned_pid = ""
        if turn.observed_expression_tokens:
            learned_pid = observe_existing_phrase_cooccurrence(
                cooccurrence,
                phrase_memory,
                (label,),
                turn.observed_expression_tokens,
                origin=turn.observed_expression_origin,
                attention_weight=turn.observed_attention_weight,
                current_tick=turn.tick,
            )

        candidate_pids = cooccurrence.nearest_paradigms_by_label((label,), top_k=turn.top_k, current_tick=turn.tick)
        recalled = phrase_memory.recall(candidate_pids, top_k=1, current_tick=turn.tick)
        if recalled:
            committed_pid = recalled[0].phrase_id
            committed_tokens = style_safe_tokens(recalled[0].tokens)
        else:
            committed_pid = ""
            committed_tokens = style_safe_tokens(())
        committed_text = "".join(committed_tokens)
        query_count = int(turn.incoming_query_count or len(turn.incoming_external_query))
        query_total_length = int(
            turn.incoming_query_total_length
            or sum(len(item) for item in turn.incoming_external_query)
        )

        trace.append(
            {
                "schema_id": "apv3_minimalist_dialogue_turn/v1",
                "tick": int(turn.tick),
                "incoming_query_hash": turn.incoming_query_hash,
                "incoming_query_count": query_count,
                "incoming_query_total_length": query_total_length,
                "context_tokens": list(turn.context_tokens),
                "feeling_label": label,
                "learned_phrase_id": learned_pid,
                "candidate_phrase_ids": list(candidate_pids),
                "committed_phrase_id": committed_pid,
                "committed_tokens": list(committed_tokens),
                "committed_text": committed_text,
                "feedback_target_phrase_id": previous_pid,
                "reward_delta": float(turn.reward_delta),
                "punish_delta": float(turn.punish_delta),
            }
        )

        observed_state["cooccurrence_associations"] = cooccurrence.export_state()
        observed_state["expression_phrase_memory"] = phrase_memory.export_state()
        observed_state["minimalist_dialogue_trace"] = trace
        observed_state["last_committed_phrase_id"] = committed_pid
        observed_state["last_committed_text"] = committed_text
        return MinimalistDialogueTurnResult(
            state=observed_state,
            feeling_label=label,
            learned_phrase_id=learned_pid,
            candidate_phrase_ids=candidate_pids,
            committed_tokens=committed_tokens,
            committed_text=committed_text,
            committed_phrase_id=committed_pid,
            feedback_target_phrase_id=previous_pid,
        )


def _default_seed_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "introspection_phrase_seed_corpus.json"


def _phrase_memory_from_state(state: Mapping[str, Any], seed_path: Path) -> ExpressionPhraseMemory:
    payload = state.get("expression_phrase_memory")
    if isinstance(payload, Mapping):
        return ExpressionPhraseMemory.from_state(payload)
    return ExpressionPhraseMemory.from_seed_corpus(seed_path)


def _trace_from_state(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = state.get("minimalist_dialogue_trace", [])
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, Mapping)]


def _latest_label(state: Mapping[str, Any], tick: int) -> str:
    rows = state.get("introspection_feelings", [])
    if not isinstance(rows, list):
        return ""
    for item in reversed(rows):
        if isinstance(item, Mapping) and int(item.get("tick", -1)) == int(tick):
            return str(item.get("sa_label", ""))
    return ""


def _context_competition(context_tokens: Sequence[str]) -> float:
    return 1.0 if len(tuple(context_tokens)) > 1 else 0.0
