from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from apv3test.config.active_learning_config import APV3ActiveLearningConfig
from apv3test.runtime.active_teacher_request import (
    APV3ActiveTeacherRequestRuntime,
    TeacherRequestResult,
    TeacherRequestSA,
    TeacherRequestSignal,
)
from apv3test.runtime.incremental_tick_runtime import IncrementalTickResult
from apv3test.runtime.teaching_iteration_loop import (
    APV3TeachingIterationLoop,
    TeachingIterationInput,
    TeachingIterationResult,
)
from apv3test.runtime.teaching_protocol_selector import TeachingPlanContext
from apv3test.runtime.work_memory_attention import APV3WorkMemoryAttentionBridge, WorkMemoryAttentionBridgeResult


@dataclass(frozen=True)
class ActiveLearningBridgeResult:
    state: dict[str, Any]
    work_memory_bridge_result: WorkMemoryAttentionBridgeResult | None
    teacher_request_result: TeacherRequestResult | None


@dataclass(frozen=True)
class ActiveLearningTeachingResult:
    state: dict[str, Any]
    iterations: tuple[TeachingIterationResult, ...]
    stopped_reason: str


class APV3ActiveLearningBridge:
    """Connect AP-native failure signals to teacher_request SA creation."""

    def __init__(
        self,
        *,
        work_memory_bridge: APV3WorkMemoryAttentionBridge | None = None,
        teacher_request_runtime: APV3ActiveTeacherRequestRuntime | None = None,
        teaching_iteration_loop: APV3TeachingIterationLoop | None = None,
        config: APV3ActiveLearningConfig | None = None,
    ) -> None:
        self.work_memory_bridge = work_memory_bridge or APV3WorkMemoryAttentionBridge()
        self.teacher_request_runtime = teacher_request_runtime or APV3ActiveTeacherRequestRuntime()
        self.teaching_iteration_loop = teaching_iteration_loop or APV3TeachingIterationLoop()
        self.config = config or APV3ActiveLearningConfig()

    def run_work_memory_idle(
        self,
        state: Mapping[str, Any],
        *,
        tick: int,
        context_tokens: tuple[str, ...] = (),
    ) -> ActiveLearningBridgeResult:
        bridge = self.work_memory_bridge.run_idle_recall(state, tick=tick, context_tokens=context_tokens)
        if bridge.work_memory_result.recalled_item is None or _incremental_succeeded(bridge.recall_result):
            return ActiveLearningBridgeResult(bridge.state, bridge, None)
        item = bridge.work_memory_result.recalled_item
        teacher = self.teacher_request_runtime.observe(
            bridge.state,
            TeacherRequestSignal(
                tick=tick + 2,
                cue_tokens=item.sa_bundle,
                context_tokens=context_tokens,
                cognitive_pressure=item.pressure,
                recall_failed=True,
                remediation_need=1.0,
            ),
        )
        return ActiveLearningBridgeResult(teacher.state, bridge, teacher)

    def observe_recall_failure(
        self,
        state: Mapping[str, Any],
        *,
        tick: int,
        cue_tokens: tuple[str, ...],
        context_tokens: tuple[str, ...] = (),
        cognitive_pressure: float = 0.0,
        recall_result: IncrementalTickResult | None = None,
    ) -> ActiveLearningBridgeResult:
        if _incremental_succeeded(recall_result):
            return ActiveLearningBridgeResult(dict(state), None, None)
        teacher = self.teacher_request_runtime.observe(
            state,
            TeacherRequestSignal(
                tick=tick,
                cue_tokens=cue_tokens,
                context_tokens=context_tokens,
                cognitive_pressure=cognitive_pressure,
                recall_failed=True,
                remediation_need=1.0,
            ),
        )
        return ActiveLearningBridgeResult(teacher.state, None, teacher)

    def run_teacher_response_iterations(
        self,
        state: Mapping[str, Any],
        *,
        request: TeacherRequestSA,
        reply_tokens: tuple[str, ...],
        case_name: str,
        expected_pid: str,
        source_kind: str = "llm_standard_teacher",
        context: TeachingPlanContext | None = None,
        start_tick: int = 1,
    ) -> ActiveLearningTeachingResult:
        current_state = dict(state)
        current_context = context or TeachingPlanContext(failure_kind=request.reason)
        previous_failure_kind = ""
        iterations: list[TeachingIterationResult] = []
        max_depth = max(1, int(self.config.max_teaching_iteration_depth))

        for index in range(max_depth):
            result = self.teaching_iteration_loop.run_once(
                current_state,
                TeachingIterationInput(
                    request=request,
                    reply_tokens=reply_tokens,
                    source_kind=source_kind,
                    case_name=case_name,
                    expected_pid=expected_pid,
                    context=current_context,
                    previous_failure_kind=previous_failure_kind,
                ),
                start_tick=int(start_tick) + index * 100,
            )
            iterations.append(result)
            current_state = result.state
            if result.run_result is None:
                return ActiveLearningTeachingResult(current_state, tuple(iterations), "awaiting_teacher_evidence")
            if result.next_proposal is None:
                return ActiveLearningTeachingResult(current_state, tuple(iterations), "validation_success")
            current_context = result.next_context
            previous_failure_kind = result.next_context.failure_kind

        return ActiveLearningTeachingResult(current_state, tuple(iterations), "max_iteration_depth")


def _incremental_succeeded(result: IncrementalTickResult | None) -> bool:
    return result is not None and result.dialogue_result is not None and bool(result.dialogue_result.emitted_tokens)
