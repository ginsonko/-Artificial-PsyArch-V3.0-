from __future__ import annotations

from dataclasses import dataclass, field

from runtime.cognitive.state_pool.state_pool import StatePool, load_constant


@dataclass(frozen=True)
class ControlledDirectEffectTrace:
    framework: str
    source_sa_id: str
    target_sa_id: str
    means_by_level: dict[float, float] = field(default_factory=dict)
    causal_strength_absolute: float = 0.0
    causal_strength_relative: float = 0.0
    monotonic: bool = False
    passes_threshold: bool = False


@dataclass
class CounterfactualModel:
    direct_effects: dict[tuple[str, str], float] = field(default_factory=dict)

    def set_direct_effect(self, source_sa_id: str, target_sa_id: str, effect_strength: float) -> None:
        """@op_count: O(1)."""
        self.direct_effects[(source_sa_id, target_sa_id)] = max(0.0, float(effect_strength))

    def estimate_controlled_direct_effect(
        self,
        state_pool: StatePool,
        *,
        source_sa_id: str,
        target_sa_id: str,
    ) -> ControlledDirectEffectTrace:
        """@op_count: O(level_count * bootstrap_count * horizon)."""
        source = state_pool.get(source_sa_id)
        target = state_pool.get(target_sa_id)
        source_r = 0.0 if source is None else max(0.0, source.real_energy)
        target_r = 0.0 if target is None else max(0.0, target.real_energy)
        effect = self.direct_effects.get((source_sa_id, target_sa_id), 0.0)
        levels = tuple(float(level) for level in load_constant("counterfactual.intervention_levels"))
        means = {
            level: _simulate_mean(target_r, source_r, effect, level)
            for level in levels
        }
        full = means.get(max(levels), 0.0)
        zero = means.get(min(levels), 0.0)
        absolute = full - zero
        relative = absolute / max(zero, float(load_constant("counterfactual.relative_baseline_epsilon")))
        monotonic = _monotonic_non_decreasing(levels, means)
        passes = monotonic and relative >= float(load_constant("counterfactual.causal_strength_min_relative"))
        return ControlledDirectEffectTrace(
            framework="controlled_direct_effect",
            source_sa_id=source_sa_id,
            target_sa_id=target_sa_id,
            means_by_level=means,
            causal_strength_absolute=absolute,
            causal_strength_relative=relative,
            monotonic=monotonic,
            passes_threshold=passes,
        )


def _simulate_mean(target_r: float, source_r: float, effect: float, level: float) -> float:
    n_boot = int(load_constant("counterfactual.n_bootstraps"))
    horizon = int(load_constant("counterfactual.max_horizon_ticks"))
    total = 0.0
    for _ in range(n_boot):
        running = target_r
        for _ in range(horizon):
            running = running + source_r * effect * level / max(float(horizon), 1.0)
        total = total + running
    return total / max(float(n_boot), 1.0)


def _monotonic_non_decreasing(levels: tuple[float, ...], means: dict[float, float]) -> bool:
    ordered = sorted(levels)
    tolerance = float(load_constant("counterfactual.monotonicity_tolerance"))
    return all(
        means[right] + tolerance >= means[left]
        for left, right in zip(ordered, ordered[1:])
    )
