from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from apv3test.runtime.paradigm_discovery import DiscoveredParadigm


@dataclass(frozen=True)
class IncrementalParadigmObservation:
    observation_id: str
    case_name: str
    cue_tokens: tuple[str, ...]
    reply_tokens: tuple[str, ...]
    tick_id: int
    context_tokens: tuple[str, ...] = ()
    modality: str = "text"
    committed: bool = True
    reward_delta: float = 0.0
    punish_delta: float = 0.0
    source_kind: str = "natural"
    teacher_stage: str = ""


@dataclass(frozen=True)
class IncrementalParadigmUpdate:
    state: dict[str, Any]
    dirty_buckets: tuple[str, ...]
    discovered: DiscoveredParadigm | None
    transition_bias: Mapping[tuple[str, str], float]
    exposed: bool
