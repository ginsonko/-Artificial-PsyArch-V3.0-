from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig


@dataclass(frozen=True)
class FocusTick:
    tick: int
    sa_bundle: tuple[str, ...]
    quantity_closure: float = 0.0
    step_closure: float = 0.0
    pressure_release: float = 0.0
    rhythm_reset: float = 0.0


@dataclass(frozen=True)
class BoundaryFeelingSA:
    tick: int
    sa_label: str
    score: float
    source_scores: dict[str, float]
    boundary: bool
    position: str = "none"


@dataclass(frozen=True)
class BoundarySegment:
    start_tick: int
    end_tick: int
    bundles: tuple[tuple[str, ...], ...]
    boundary_feelings: tuple[BoundaryFeelingSA, ...]

    @property
    def flattened_sa(self) -> tuple[str, ...]:
        labels: list[str] = []
        for bundle in self.bundles:
            labels.extend(bundle)
        return tuple(labels)


class BoundaryFeelingSegmenter:
    """Emergent boundary feelings over cross-tick first-class SA bundles.

    The segmenter consumes generic SA labels and cognitive-feeling scalar traces.
    It does not inspect text content, use external turn flags, or route by
    domain. Boundaries are auditable SA-like events.
    """

    def __init__(self, config: APV3ParadigmDiscoveryConfig | None = None) -> None:
        self.config = config or APV3ParadigmDiscoveryConfig()

    def segment(self, ticks: Iterable[FocusTick]) -> tuple[BoundarySegment, ...]:
        ordered = tuple(sorted(ticks, key=lambda item: item.tick))
        if not ordered:
            return ()
        segments: list[BoundarySegment] = []
        current_bundles: list[tuple[str, ...]] = []
        current_feelings: list[BoundaryFeelingSA] = []
        current_start = ordered[0].tick
        previous: FocusTick | None = None
        for item in ordered:
            if not current_bundles:
                current_start = item.tick
            feeling = self.boundary_feeling(previous, item)
            if current_bundles and feeling.boundary and feeling.position == "before":
                segments.append(
                    BoundarySegment(
                        start_tick=current_start,
                        end_tick=previous.tick if previous else item.tick,
                        bundles=tuple(current_bundles),
                        boundary_feelings=tuple(current_feelings),
                    )
                )
                current_bundles = []
                current_feelings = []
                current_start = item.tick
            current_bundles.append(tuple(item.sa_bundle))
            current_feelings.append(feeling)
            if feeling.boundary and feeling.position == "after":
                segments.append(
                    BoundarySegment(
                        start_tick=current_start,
                        end_tick=item.tick,
                        bundles=tuple(current_bundles),
                        boundary_feelings=tuple(current_feelings),
                    )
                )
                current_bundles = []
                current_feelings = []
            previous = item
        if current_bundles:
            segments.append(
                BoundarySegment(
                    start_tick=current_start,
                    end_tick=ordered[-1].tick,
                    bundles=tuple(current_bundles),
                    boundary_feelings=tuple(current_feelings),
                )
            )
        return tuple(segments)

    def boundary_feeling(self, previous: FocusTick | None, current: FocusTick) -> BoundaryFeelingSA:
        source_scores = {
            "continuity_drop": self._continuity_drop(previous.sa_bundle if previous else (), current.sa_bundle)
            * self.config.boundary_continuity_weight,
            "quantity_closure": _clamp01(current.quantity_closure) * self.config.boundary_quantity_weight,
            "step_closure": _clamp01(current.step_closure) * self.config.boundary_step_closure_weight,
            "pressure_release": _clamp01(current.pressure_release) * self.config.boundary_pressure_release_weight,
            "rhythm_reset": _clamp01(current.rhythm_reset) * self.config.boundary_rhythm_weight,
        }
        if previous is None:
            source_scores["continuity_drop"] = 0.0
        score = max(source_scores.values()) if source_scores else 0.0
        source = _max_source(source_scores)
        is_boundary = score >= self.config.boundary_threshold and previous is not None
        return BoundaryFeelingSA(
            tick=current.tick,
            sa_label=f"feeling::boundary::{source}",
            score=round(score, 6),
            source_scores={key: round(value, 6) for key, value in source_scores.items()},
            boundary=is_boundary,
            position=_boundary_position(source) if is_boundary else "none",
        )

    def _continuity_drop(self, previous: Sequence[str], current: Sequence[str]) -> float:
        prev_set = set(previous)
        cur_set = set(current)
        if not prev_set and not cur_set:
            return 0.0
        union = prev_set | cur_set
        if not union:
            return 0.0
        overlap = len(prev_set & cur_set) / len(union)
        return _clamp01(1.0 - overlap)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _max_source(values: dict[str, float]) -> str:
    if not values:
        return "none"
    return sorted(values.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _boundary_position(source: str) -> str:
    if source in {"quantity_closure", "step_closure", "pressure_release"}:
        return "after"
    return "before"
