from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from apv3test.runtime.incremental_tick_runtime import IncrementalTickInput, IncrementalTickResult, IncrementalTickRuntime
from apv3test.runtime.work_memory import APV3WorkMemoryRuntime, WorkMemoryTickInput, WorkMemoryTickResult


@dataclass(frozen=True)
class WorkMemoryAttentionBridgeResult:
    state: dict[str, Any]
    work_memory_result: WorkMemoryTickResult
    recall_result: IncrementalTickResult | None


class APV3WorkMemoryAttentionBridge:
    """Let idle working-memory recall supply focus/cue to Bn/Cn attention."""

    def __init__(
        self,
        *,
        work_memory: APV3WorkMemoryRuntime | None = None,
        tick_runtime: IncrementalTickRuntime | None = None,
    ) -> None:
        self.work_memory = work_memory or APV3WorkMemoryRuntime()
        self.tick_runtime = tick_runtime or IncrementalTickRuntime()

    def run_idle_recall(
        self,
        state: Mapping[str, Any],
        *,
        tick: int,
        context_tokens: tuple[str, ...] = (),
        commit_after_draft: bool = True,
        grasp: float = 1.2,
        demand_slow: float = 0.1,
    ) -> WorkMemoryAttentionBridgeResult:
        wm = self.work_memory.run_tick(state, WorkMemoryTickInput(tick=tick, idle=True))
        if wm.recalled_item is None:
            return WorkMemoryAttentionBridgeResult(wm.state, wm, None)
        recall = self.tick_runtime.run_tick(
            wm.state,
            IncrementalTickInput(
                tick=tick + 1,
                cue_tokens=wm.recalled_item.sa_bundle,
                focus_tokens=wm.recalled_item.sa_bundle,
                context_tokens=context_tokens,
                emit_reply=True,
                commit_after_draft=commit_after_draft,
                grasp=grasp,
                demand_slow=demand_slow,
            ),
        )
        return WorkMemoryAttentionBridgeResult(recall.state, wm, recall)
