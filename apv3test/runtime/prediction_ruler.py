from __future__ import annotations

from dataclasses import dataclass

from apv3test.config.energy_config import APV3EnergyConfig


@dataclass
class PredictionRuler:
    """APV3.0 prediction ruler model.

    This is a small standalone model for Phase 1.6 tests. It captures the
    intended baseline semantics before we patch the main state pool.
    """

    config: APV3EnergyConfig
    baseline: float = 0.0

    def begin_tick(self) -> None:
        self.baseline = max(0.0, float(self.baseline) * max(0.0, min(1.0, self.config.real_decay)))

    def observe_external(self, real_samples: list[float]) -> None:
        positives = [max(0.0, float(value)) for value in real_samples if float(value) > 0.0]
        if not positives:
            return
        mean_real = sum(positives) / len(positives)
        self.baseline = max(0.0, float(self.baseline) + mean_real)

    def target_cap(self, *, support_level: float = 0.0, live_real_energy: float | None = None) -> float:
        support = max(0.0, min(1.0, float(support_level)))
        ruler = max(0.0, float(live_real_energy)) if live_real_energy is not None else max(0.0, float(self.baseline))
        ratio = self.config.base_ratio + (1.0 - self.config.base_ratio) * support
        return max(float(self.config.min_target_cap), ruler * ratio)

