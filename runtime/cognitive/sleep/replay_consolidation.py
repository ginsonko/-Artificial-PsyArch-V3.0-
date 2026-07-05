from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.long_term.layers import LongTermDualLayer, RehydrationResult
from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass(frozen=True)
class SleepReplayTrace:
    replayed_sa_ids: tuple[str, ...]
    rehydration: RehydrationResult


def replay_for_consolidation(
    long_term: LongTermDualLayer,
    *,
    tick: int,
) -> SleepReplayTrace:
    """@op_count: O(cold_index log cold_index)."""
    selected = _select_replay_items(tuple(long_term.cold_index.values()))
    for item in selected:
        count = int(item.metadata.get("sleep_replay_count", 0)) + 1
        boosted = min(
            float(load_constant("sleep_replay.long_term_r_cap")),
            float(item.metadata.get("long_term_R", item.real_energy))
            + float(load_constant("sleep_replay.consolidation_gain")),
        )
        item.metadata["sleep_replay_count"] = count
        item.metadata["long_term_R"] = boosted
        item.real_energy = max(item.real_energy, boosted)
    rehydration = long_term.rehydrate_by_cues((item.sa_id for item in selected), tick=tick)
    return SleepReplayTrace(
        replayed_sa_ids=tuple(item.sa_id for item in selected),
        rehydration=rehydration,
    )


def _select_replay_items(items: tuple[StateItem, ...]) -> tuple[StateItem, ...]:
    limit = int(load_constant("sleep_replay.top_k"))
    ordered = sorted(
        items,
        key=lambda item: (
            float(item.metadata.get("long_term_R", item.real_energy)),
            item.cognitive_pressure,
            item.sa_id,
        ),
        reverse=True,
    )
    return tuple(ordered[:limit])
