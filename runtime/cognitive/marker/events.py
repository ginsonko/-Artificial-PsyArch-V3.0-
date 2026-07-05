from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MarkerEvent:
    tick: int
    kind: str
    target_sa_id: str
    real_energy: float
    origin: str = "source_marker"
    family: str = "marker"
    channel_signature: tuple[str, ...] = ("marker",)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def sa_id(self) -> str:
        return f"marker::{self.kind}::{self.target_sa_id}"

    @property
    def label(self) -> str:
        return self.kind


def event_value(event: object, name: str) -> object:
    """@op_count: O(1)."""
    if hasattr(event, name):
        return getattr(event, name)
    if isinstance(event, dict):
        return event[name]
    raise AttributeError(name)

