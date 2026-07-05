from __future__ import annotations

from dataclasses import dataclass, field


LEDGER_SOURCES = (
    "external",
    "feedback",
    "rpe_signal",
    "unfinished_pressure",
    "expectation_pressure",
    "residual_mass",
    "drive_pressure",
    "imagination",
    "replay",
    "user_directed",
)

ENDOGENOUS_SOURCES = (
    "unfinished_pressure",
    "expectation_pressure",
    "residual_mass",
    "drive_pressure",
    "imagination",
    "replay",
)


@dataclass
class AttentionGainLedger:
    gain_by_source: dict[str, float] = field(
        default_factory=lambda: {source: 0.0 for source in LEDGER_SOURCES}
    )

    def inject(self, source: str, amount: float) -> None:
        """@op_count: O(1)."""
        if source not in self.gain_by_source:
            raise ValueError(f"unknown attention gain source: {source}")
        self.gain_by_source[source] = self.gain_by_source[source] + float(amount)

    def step_decay(self, decay: float) -> None:
        """@op_count: O(source_count)."""
        for source in self.gain_by_source:
            self.gain_by_source[source] = self.gain_by_source[source] * float(decay)

    def total(self) -> float:
        """@op_count: O(source_count)."""
        return sum(self.gain_by_source.values())

    def endogenous_share(self) -> float:
        """@op_count: O(source_count)."""
        total = self.total()
        if total <= 0.0:
            return 0.0
        endo = sum(self.gain_by_source[source] for source in ENDOGENOUS_SOURCES)
        share = endo / total
        return max(0.0, min(1.0, share))

    def snapshot(self) -> dict[str, float]:
        """@op_count: O(source_count)."""
        return dict(self.gain_by_source)
