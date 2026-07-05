from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from apv3test.config.habit_config import APV3HabitConfig
from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig
from apv3test.runtime.paradigm_discovery import ParadigmDiscoveryEngine, ParadigmObservation
from apv3test.runtime.paradigm_stats import RoleTransitionStats, promoted_context_similarity
from apv3test.runtime.paradigm_store import (
    append_observation,
    bucket_key,
    bucket_observations,
    ensure_incremental_state,
    mark_dirty,
    update_paradigm_stats,
    upsert_paradigm_pool_entry,
)
from apv3test.runtime.paradigm_types import IncrementalParadigmObservation, IncrementalParadigmUpdate


class IncrementalParadigmLearner:
    """Online Phase5 paradigm learner over dirty observation buckets."""

    def __init__(
        self,
        config: APV3ParadigmDiscoveryConfig | None = None,
        habit_config: APV3HabitConfig | None = None,
    ) -> None:
        self.config = config or APV3ParadigmDiscoveryConfig()
        self.habit_config = habit_config or APV3HabitConfig()
        self.role_stats = RoleTransitionStats(self.config, self.habit_config)

    def ingest(
        self,
        state: Mapping[str, Any],
        observation: IncrementalParadigmObservation,
    ) -> IncrementalParadigmUpdate:
        next_state = ensure_incremental_state(deepcopy(dict(state)))
        bucket = bucket_key(observation.case_name, observation.cue_tokens)
        append_observation(next_state, observation, bucket)
        mark_dirty(next_state, bucket, self.config.incremental_dirty_bucket_limit)

        transition_bias = self.role_stats.bias_map(
            next_state,
            current_context_tokens=observation.context_tokens,
            current_tick=observation.tick_id,
        )
        discovered = self._discover_bucket(bucket_observations(next_state, bucket), transition_bias)
        exposed = False
        if discovered is not None:
            roles = tuple(column.role for column in discovered.columns)
            self.role_stats.learn(
                next_state,
                roles,
                context_tokens=observation.context_tokens,
                committed=observation.committed,
                reward_delta=observation.reward_delta,
                punish_delta=observation.punish_delta,
                tick_id=observation.tick_id,
                provenance=observation.observation_id,
            )
            exposed = update_paradigm_stats(
                next_state,
                discovered,
                observation,
                bucket=bucket,
                config=self.config,
                habit_config=self.habit_config,
            )
            upsert_paradigm_pool_entry(next_state, discovered, observation, bucket=bucket, exposed=exposed)

        return IncrementalParadigmUpdate(
            state=next_state,
            dirty_buckets=tuple(next_state.get("dirty_paradigm_buckets", ())),
            discovered=discovered,
            transition_bias=transition_bias,
            exposed=exposed,
        )

    def ingest_many(
        self,
        state: Mapping[str, Any],
        observations: Sequence[IncrementalParadigmObservation],
    ) -> IncrementalParadigmUpdate:
        result = IncrementalParadigmUpdate(dict(state), (), None, {}, False)
        current: Mapping[str, Any] = state
        for observation in observations:
            result = self.ingest(current, observation)
            current = result.state
        return result

    def _discover_bucket(
        self,
        observations: Sequence[ParadigmObservation],
        transition_bias: Mapping[tuple[str, str], float],
    ):
        if len(observations) < self.config.min_support:
            return None
        engine = ParadigmDiscoveryEngine(self.config, transition_bias=transition_bias)
        discovered = engine.discover(observations)
        return discovered[0] if discovered else None


__all__ = [
    "IncrementalParadigmLearner",
    "IncrementalParadigmObservation",
    "IncrementalParadigmUpdate",
    "RoleTransitionStats",
    "promoted_context_similarity",
]
