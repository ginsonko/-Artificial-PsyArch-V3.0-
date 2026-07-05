from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from apv3test.runtime.action_competition import ActionCompetition, ActionCompetitionTrace, ActionProposal
from apv3test.runtime.draft_action import DraftActionRunner, DraftTextAction
from apv3test.runtime.habit_system import FastHabitSystem
from apv3test.runtime.learning_writer import LearningEpisodeWriter
from apv3test.runtime.paradigm_discovery import DiscoveredParadigm
from apv3test.runtime.paradigm_fill import DraftCandidate, ParadigmSlotFiller


@dataclass(frozen=True)
class DialogueTurnInput:
    tick: int
    focus_tokens: tuple[str, ...]
    candidate_pool: tuple[str, ...]
    current_context_tags: tuple[str, ...] = ()
    successor_virtuals: Mapping[str, float] | None = None
    commit_after_draft: bool = False
    grasp: float = 0.0
    demand_slow: float = 0.0


@dataclass(frozen=True)
class DialogueTurnResult:
    state: dict[str, Any]
    draft_candidates: tuple[DraftCandidate, ...]
    action_traces: tuple[ActionCompetitionTrace, ...]
    emitted_tokens: tuple[str, ...]
    committed_text: str


class MinimalDialogueRuntime:
    """Small APV3.0test dialogue tick-chain skeleton.

    This class is glue over existing AP-native modules. It does not discover a
    new policy, infer target replies, or run a teacher-side model.
    """

    def __init__(
        self,
        *,
        slot_filler: ParadigmSlotFiller | None = None,
        habit_system: FastHabitSystem | None = None,
        competition: ActionCompetition | None = None,
        draft_runner: DraftActionRunner | None = None,
        learning_writer: LearningEpisodeWriter | None = None,
    ) -> None:
        self.slot_filler = slot_filler or ParadigmSlotFiller()
        self.habit_system = habit_system or FastHabitSystem()
        self.competition = competition or ActionCompetition()
        self.draft_runner = draft_runner or DraftActionRunner()
        self.learning_writer = learning_writer or LearningEpisodeWriter()

    def run_turn(
        self,
        state: Mapping[str, Any],
        *,
        paradigm: DiscoveredParadigm,
        turn: DialogueTurnInput,
        commit_episode_id: str | None = None,
    ) -> DialogueTurnResult:
        next_state = self.draft_runner.ensure_state(state)
        drafts = self.slot_filler.fill(
            paradigm,
            focus_tokens=turn.focus_tokens,
            candidate_pool=turn.candidate_pool,
            successor_virtuals=turn.successor_virtuals,
        )
        traces: list[ActionCompetitionTrace] = []
        emitted_tokens: list[str] = []
        for offset, draft in enumerate(drafts):
            tick = turn.tick + offset
            habit_candidates = self.habit_system.candidates(
                next_state,
                current_context_tags=turn.current_context_tags,
                grasp=turn.grasp,
                demand_slow=turn.demand_slow,
                current_tick=tick,
            )
            proposals = [
                ActionProposal.from_habit_candidate(candidate, tick=tick)
                for candidate in habit_candidates
            ]
            proposals.append(
                ActionProposal(
                    tick=tick,
                    action_id=f"draft_token::{draft.label}",
                    actuator_id="draft_editor",
                    source_system="paradigm_slot_fill",
                    outcome_kind="action",
                    drive=draft.strength,
                    lambda_fast=0.0,
                    habit_strength=0.0,
                    slow_review_pressure=0.0,
                    evidence_tags=turn.current_context_tags,
                    payload=draft.anchor_meta,
                )
            )
            trace = self.competition.compete(proposals, tick=tick)
            traces.append(trace)
            if not self._selected_draft_token(draft, trace.selected):
                break
            emitted_tokens.append(draft.label)
            next_state = self.draft_runner.apply(
                next_state,
                DraftTextAction(tick=tick, kind="type_text", text=draft.label),
            )
        committed_text = ""
        emitted = tuple(emitted_tokens)
        if turn.commit_after_draft and emitted and len(emitted) == len(drafts) and not _has_undecidable_fragment(drafts):
            commit_tick = turn.tick + len(traces)
            next_state = self.draft_runner.apply(next_state, DraftTextAction(tick=commit_tick, kind="commit"))
            runtime = next_state.get("draft_runtime", {})
            commits = runtime.get("commits", []) if isinstance(runtime, dict) else []
            if commits and isinstance(commits[-1], dict):
                committed_text = str(commits[-1].get("text", ""))
            if commit_episode_id:
                episode = self.draft_runner.learning_episode_from_latest_commit(
                    next_state,
                    episode_id=commit_episode_id,
                )
                if episode is not None:
                    next_state = self.learning_writer.apply(next_state, episode)
        return DialogueTurnResult(
            state=next_state,
            draft_candidates=drafts,
            action_traces=tuple(traces),
            emitted_tokens=emitted,
            committed_text=committed_text,
        )

    def _selected_draft_token(
        self,
        draft: DraftCandidate,
        selected: Sequence[ActionProposal],
    ) -> bool:
        expected_id = f"draft_token::{draft.label}"
        return any(
            item.actuator_id == "draft_editor"
            and item.action_id == expected_id
            and item.source_system == "paradigm_slot_fill"
            for item in selected
        )


def _has_undecidable_fragment(drafts: Sequence[DraftCandidate]) -> bool:
    return any(bool(item.anchor_meta.get("undecidable_fragment", False)) for item in drafts)
