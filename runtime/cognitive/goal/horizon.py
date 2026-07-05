from __future__ import annotations

from dataclasses import dataclass

from runtime.cognitive.state_pool.state_pool import StateItem, StatePool, load_constant


@dataclass(frozen=True)
class GoalProgressTrace:
    goal_sa_id: str
    progress: float
    completed: bool
    horizon_ticks: int


def create_goal_sa(
    state_pool: StatePool,
    *,
    goal_id: str,
    target_sa_id: str,
    tick: int,
    horizon_ticks: int | None = None,
) -> StateItem:
    """@op_count: O(1)."""
    horizon = int(horizon_ticks if horizon_ticks is not None else load_constant("goal.long_horizon_ticks"))
    item = StateItem(
        sa_id=f"EntitySA::goal::{goal_id}",
        family="goal",
        label="long_horizon_goal",
        real_energy=1.0,
        virtual_energy=0.0,
        attention_energy=float(load_constant("goal.attention_gain_scale")),
        cognitive_pressure=1.0,
        last_tick=int(tick),
        channel_signature=("goal",),
        source="goal_horizon",
        metadata={
            "goal_id": goal_id,
            "target_sa_id": target_sa_id,
            "created_tick": int(tick),
            "horizon_ticks": horizon,
            "progress": 0.0,
            "completed": False,
        },
    )
    item.gain_ledger.inject("unfinished_pressure", item.attention_energy)
    state_pool.items[item.sa_id] = item
    return item


def update_goal_progress(goal: StateItem, *, evidence_strength: float, tick: int) -> GoalProgressTrace:
    """@op_count: O(1)."""
    gain = float(load_constant("goal.progress_gain"))
    previous = float(goal.metadata.get("progress", 0.0))
    progress = min(1.0, max(0.0, previous + max(0.0, float(evidence_strength)) * gain))
    completed = progress >= float(load_constant("goal.completion_threshold"))
    goal.metadata["progress"] = progress
    goal.metadata["completed"] = completed
    goal.virtual_energy = progress
    goal.cognitive_pressure = max(0.0, goal.real_energy - progress)
    goal.last_tick = int(tick)
    if completed:
        goal.real_energy = progress
        goal.cognitive_pressure = 0.0
    return GoalProgressTrace(
        goal_sa_id=goal.sa_id,
        progress=progress,
        completed=completed,
        horizon_ticks=int(goal.metadata.get("horizon_ticks", load_constant("goal.long_horizon_ticks"))),
    )
