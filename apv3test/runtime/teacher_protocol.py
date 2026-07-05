from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from apv3test.runtime.draft_action import DraftActionRunner, DraftTextAction
from apv3test.runtime.learning_writer import LearningEpisode, LearningEpisodeWriter
from apv3test.runtime.parity_probe import ParityProbeCase, ProbeResult, run_parity_probe


@dataclass(frozen=True)
class TeacherProtocolEpisode:
    episode_id: str
    learning_episode: LearningEpisode
    draft_actions: tuple[DraftTextAction, ...]
    probe_cases: tuple[ParityProbeCase, ...]
    commit_episode_id: str


@dataclass(frozen=True)
class TeacherProtocolResult:
    state: dict[str, Any]
    probe_results: list[ProbeResult]


class TeacherProtocolRunner:
    """Small structured teaching episode runner.

    It connects existing APV3.0test components in sequence. It does not infer
    what should be taught, choose text, or bypass the draft action boundary.
    """

    def __init__(
        self,
        learning_writer: LearningEpisodeWriter | None = None,
        draft_runner: DraftActionRunner | None = None,
    ) -> None:
        self.learning_writer = learning_writer or LearningEpisodeWriter()
        self.draft_runner = draft_runner or DraftActionRunner()

    def run(self, state: Mapping[str, Any], episode: TeacherProtocolEpisode) -> TeacherProtocolResult:
        next_state = self.learning_writer.apply(state, episode.learning_episode)
        for action in episode.draft_actions:
            next_state = self.draft_runner.apply(next_state, action)
        commit_episode = self.draft_runner.learning_episode_from_latest_commit(
            next_state,
            episode_id=episode.commit_episode_id,
        )
        if commit_episode is not None:
            next_state = self.learning_writer.apply(next_state, commit_episode)
        return TeacherProtocolResult(
            state=next_state,
            probe_results=run_parity_probe(next_state, episode.probe_cases),
        )

