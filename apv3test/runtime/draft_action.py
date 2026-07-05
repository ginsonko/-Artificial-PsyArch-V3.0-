from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from apv3test.runtime.learning_writer import LearnedActionOutcome, LearningEpisode


@dataclass(frozen=True)
class DraftTextAction:
    tick: int
    kind: str
    text: str = ""
    count: int = 1
    old_text: str = ""
    new_text: str = ""
    actuator_id: str = "draft_editor"


class DraftActionRunner:
    """Minimal low-granularity draft editor.

    The runner models mechanical text actions only. It does not decide what to
    say and it does not write long-term learning evidence until a commit exists.
    """

    def ensure_state(self, state: Mapping[str, Any]) -> dict[str, Any]:
        next_state = deepcopy(dict(state))
        runtime = next_state.setdefault("draft_runtime", {})
        runtime.setdefault("buffer", "")
        runtime.setdefault("cursor", len(str(runtime.get("buffer", ""))))
        runtime.setdefault("readbacks", [])
        runtime.setdefault("commits", [])
        runtime.setdefault("action_log", [])
        return next_state

    def apply(self, state: Mapping[str, Any], action: DraftTextAction) -> dict[str, Any]:
        next_state = self.ensure_state(state)
        runtime = next_state["draft_runtime"]
        self._assert_single_action_per_tick(runtime, action)
        kind = action.kind
        if kind == "type_text":
            self._type_text(runtime, action.text)
        elif kind == "reread":
            self._reread(runtime, action.tick)
        elif kind == "delete_chars":
            self._delete_chars(runtime, action.count)
        elif kind == "replace_tail":
            self._replace_tail(runtime, action.old_text, action.new_text)
        elif kind == "commit":
            self._commit(runtime, action.tick)
        else:
            raise ValueError(f"unsupported draft action: {kind}")
        runtime["action_log"].append(
            {
                "tick": int(action.tick),
                "actuator_id": action.actuator_id,
                "kind": kind,
            }
        )
        return next_state

    def learning_episode_from_latest_commit(
        self,
        state: Mapping[str, Any],
        *,
        episode_id: str,
        reward_delta: float = 1.0,
        drive_bias_delta: float = 0.1,
    ) -> LearningEpisode | None:
        runtime = state.get("draft_runtime", {})
        commits = runtime.get("commits", []) if isinstance(runtime, dict) else []
        if not isinstance(commits, list) or not commits:
            return None
        latest = commits[-1]
        if not isinstance(latest, dict) or not str(latest.get("text", "")):
            return None
        return LearningEpisode(
            episode_id=episode_id,
            action_outcomes=(
                LearnedActionOutcome(
                    "text_commit",
                    drive_bias_delta=drive_bias_delta,
                    reward_delta=reward_delta,
                    punish_delta=0.0,
                ),
            ),
        )

    def _assert_single_action_per_tick(self, runtime: dict[str, Any], action: DraftTextAction) -> None:
        for item in runtime.get("action_log", []):
            if not isinstance(item, dict):
                continue
            if int(item.get("tick", -1)) == int(action.tick) and str(item.get("actuator_id", "")) == action.actuator_id:
                raise ValueError("same actuator already acted in this tick")

    def _type_text(self, runtime: dict[str, Any], text: str) -> None:
        buffer = str(runtime.get("buffer", ""))
        cursor = _bounded_cursor(runtime.get("cursor"), buffer)
        runtime["buffer"] = buffer[:cursor] + text + buffer[cursor:]
        runtime["cursor"] = cursor + len(text)

    def _reread(self, runtime: dict[str, Any], tick: int) -> None:
        runtime.setdefault("readbacks", []).append({"tick": int(tick), "text": str(runtime.get("buffer", ""))})

    def _delete_chars(self, runtime: dict[str, Any], count: int) -> None:
        buffer = str(runtime.get("buffer", ""))
        cursor = _bounded_cursor(runtime.get("cursor"), buffer)
        n = max(0, int(count))
        start = max(0, cursor - n)
        runtime["buffer"] = buffer[:start] + buffer[cursor:]
        runtime["cursor"] = start

    def _replace_tail(self, runtime: dict[str, Any], old_text: str, new_text: str) -> None:
        buffer = str(runtime.get("buffer", ""))
        if old_text and not buffer.endswith(old_text):
            raise ValueError("draft tail does not match old_text")
        if old_text:
            buffer = buffer[: -len(old_text)]
        runtime["buffer"] = buffer + new_text
        runtime["cursor"] = len(runtime["buffer"])

    def _commit(self, runtime: dict[str, Any], tick: int) -> None:
        text = str(runtime.get("buffer", ""))
        if text:
            runtime.setdefault("commits", []).append({"tick": int(tick), "text": text})
        runtime["buffer"] = ""
        runtime["cursor"] = 0


def _bounded_cursor(value: object, buffer: str) -> int:
    try:
        cursor = int(value)
    except (TypeError, ValueError):
        cursor = len(buffer)
    return max(0, min(len(buffer), cursor))

