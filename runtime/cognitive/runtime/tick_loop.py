from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from runtime.cognitive.marker.spawn_perceived import spawn_perceived
from runtime.cognitive.state_pool.state_pool import StatePool, load_constant
from runtime.sensor_adapters.text.char_stream import TextCharEvent, TextCharStream


@dataclass(frozen=True)
class TickTrace:
    tick: int
    input_events: tuple[TextCharEvent, ...]
    state_pool_top: tuple[dict[str, object], ...]
    draft_action: str
    draft_buffer: str
    committed_text: str
    idle: bool


@dataclass(frozen=True)
class TickLoopResult:
    state_pool: StatePool
    traces: tuple[TickTrace, ...]


class ContinuousTickRuntime:
    """Phase 8.2 logical tick loop over sparse sensor events."""

    def __init__(
        self,
        *,
        state_pool: StatePool | None = None,
        text_stream: TextCharStream | None = None,
    ) -> None:
        self.state_pool = state_pool or StatePool()
        self.text_stream = text_stream or TextCharStream()

    def run_text_message(
        self,
        text: str,
        *,
        start_tick: int = 0,
        utterance_id: str = "utterance",
        origin: str = "user_text",
        idle_ticks_after: int = 0,
    ) -> TickLoopResult:
        """@op_count: O(chars + ticks * active_sa)."""
        events = self.text_stream.events_from_text(
            text,
            start_tick=start_tick,
            utterance_id=utterance_id,
            origin=origin,
        )
        if events:
            final_tick = events[-1].tick + idle_ticks_after
        else:
            final_tick = start_tick + idle_ticks_after
        return self.run_events(events, start_tick=start_tick, final_tick=final_tick)

    def run_events(
        self,
        events: Iterable[TextCharEvent],
        *,
        start_tick: int = 0,
        final_tick: int | None = None,
    ) -> TickLoopResult:
        """@op_count: O(events + ticks * active_sa)."""
        events_by_tick: dict[int, list[TextCharEvent]] = {}
        max_tick = start_tick
        for event in events:
            events_by_tick.setdefault(event.tick, []).append(event)
            if event.tick > max_tick:
                max_tick = event.tick
        if final_tick is None:
            final_tick = max_tick

        traces: list[TickTrace] = []
        tick = start_tick
        while tick <= final_tick:
            tick_events = tuple(events_by_tick.get(tick, ()))
            traces.append(self._run_tick(tick, tick_events))
            tick += 1
        return TickLoopResult(state_pool=self.state_pool, traces=tuple(traces))

    def _run_tick(self, tick: int, events: tuple[TextCharEvent, ...]) -> TickTrace:
        self.state_pool.tick_decay(tick=tick)
        for event in events:
            self.state_pool.observe_external(event, tick=tick)
            self.state_pool.observe_external(spawn_perceived(event, tick=tick), tick=tick)
        return TickTrace(
            tick=tick,
            input_events=events,
            state_pool_top=self.state_pool.snapshot_top(),
            draft_action="noop",
            draft_buffer="",
            committed_text="",
            idle=not events,
        )


def phase8_2_trace_summary(result: TickLoopResult) -> dict[str, object]:
    """@op_count: O(ticks)."""
    return {
        "ticks": tuple(trace.tick for trace in result.traces),
        "input_event_counts": tuple(len(trace.input_events) for trace in result.traces),
        "idle_ticks": tuple(trace.tick for trace in result.traces if trace.idle),
        "top_k_limit": int(load_constant("context_signature.top_k")),
    }
