from __future__ import annotations

from dataclasses import dataclass, replace
from math import sqrt
from typing import Iterable, Mapping

from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig
from apv3test.runtime.learning_writer import LearnedPerceptPrototype


@dataclass(frozen=True)
class PerceptObservation:
    source_sa: str
    features: Mapping[str, float]
    cognitive_pressure: float
    continuity_anchor: str | None = None
    modality: str | None = None
    tick: int = 0


@dataclass(frozen=True)
class PerceptPrototype:
    prototype_id: str
    token: str
    vector: tuple[float, ...]
    support: float
    continuity_anchor: str | None
    last_tick: int
    modality_mix: tuple[str, ...] = ()


@dataclass(frozen=True)
class PerceptPrototypeResult:
    observation: PerceptObservation
    token: str
    prototype_id: str
    matched_existing: bool
    similarity: float


class PerceptPrototypeStore:
    """Stable modality-agnostic prototype tokens for percept-like SA."""

    def __init__(
        self,
        config: APV3ParadigmDiscoveryConfig | None = None,
        prototypes: Iterable[PerceptPrototype] = (),
    ) -> None:
        self.config = config or APV3ParadigmDiscoveryConfig()
        self._prototypes: list[PerceptPrototype] = list(prototypes)
        self._next_id = self._infer_next_id()

    @property
    def prototypes(self) -> tuple[PerceptPrototype, ...]:
        return tuple(self._prototypes)

    def observe(self, observation: PerceptObservation) -> PerceptPrototypeResult:
        vector = _vector_from_features(observation.features)
        best_index, best_similarity = self._best_match(vector, observation.continuity_anchor)
        should_match = (
            best_index is not None
            and best_similarity >= self.config.percept_match_threshold
        )
        if should_match:
            proto = self._update(best_index, vector, observation)
            return PerceptPrototypeResult(observation, proto.token, proto.prototype_id, True, round(best_similarity, 6))
        if observation.cognitive_pressure < self.config.percept_spawn_pressure_threshold and best_index is not None:
            proto = self._update(best_index, vector, observation, weak=True)
            return PerceptPrototypeResult(observation, proto.token, proto.prototype_id, True, round(best_similarity, 6))
        proto = self._spawn(vector, observation)
        self._enforce_limit()
        return PerceptPrototypeResult(observation, proto.token, proto.prototype_id, False, round(best_similarity, 6))

    def to_learned_prototypes(self) -> tuple[LearnedPerceptPrototype, ...]:
        return tuple(
            LearnedPerceptPrototype(
                prototype_id=proto.prototype_id,
                support_delta=proto.support,
                features={
                    "token": proto.token,
                    "vector": list(proto.vector),
                    "continuity_anchor": proto.continuity_anchor,
                    "last_tick": proto.last_tick,
                    "modality_mix": list(proto.modality_mix),
                },
                probe_tags=("percept_prototype",),
            )
            for proto in self._prototypes
        )

    @classmethod
    def from_state(
        cls,
        payload: object,
        config: APV3ParadigmDiscoveryConfig | None = None,
    ) -> PerceptPrototypeStore:
        prototypes: list[PerceptPrototype] = []
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                features = item.get("features", {})
                vector = features.get("vector", []) if isinstance(features, dict) else []
                token = str(features.get("token", "")) if isinstance(features, dict) else ""
                prototype_id = str(item.get("prototype_id", ""))
                if not prototype_id:
                    continue
                prototypes.append(
                    PerceptPrototype(
                        prototype_id=prototype_id,
                        token=token or f"percept::prototype::{prototype_id}",
                        vector=tuple(float(value) for value in vector),
                        support=float(item.get("support", 0.0)),
                        continuity_anchor=str(features.get("continuity_anchor")) if isinstance(features, dict) and features.get("continuity_anchor") is not None else None,
                        last_tick=int(features.get("last_tick", 0)) if isinstance(features, dict) else 0,
                        modality_mix=tuple(str(value) for value in features.get("modality_mix", ())) if isinstance(features, dict) else (),
                    )
                )
        return cls(config=config, prototypes=prototypes)

    def _best_match(self, vector: tuple[float, ...], continuity_anchor: str | None) -> tuple[int | None, float]:
        best_index: int | None = None
        best_similarity = 0.0
        for index, proto in enumerate(self._prototypes):
            similarity = _cosine(vector, proto.vector)
            if continuity_anchor and proto.continuity_anchor == continuity_anchor:
                similarity = max(similarity, min(1.0, similarity + 0.08))
            if similarity > best_similarity:
                best_similarity = similarity
                best_index = index
        return best_index, best_similarity

    def _update(
        self,
        index: int,
        vector: tuple[float, ...],
        observation: PerceptObservation,
        *,
        weak: bool = False,
    ) -> PerceptPrototype:
        proto = self._prototypes[index]
        rate = self.config.percept_merge_rate * (0.35 if weak else 1.0)
        merged = _normalize(tuple((1.0 - rate) * a + rate * b for a, b in zip(proto.vector, vector)))
        support_delta = 0.25 if weak else 1.0
        modality_mix = _merged_tuple(proto.modality_mix, observation.modality)
        updated = replace(
            proto,
            vector=merged,
            support=proto.support + support_delta,
            continuity_anchor=proto.continuity_anchor or observation.continuity_anchor,
            last_tick=max(proto.last_tick, int(observation.tick)),
            modality_mix=modality_mix,
        )
        self._prototypes[index] = updated
        return updated

    def _spawn(self, vector: tuple[float, ...], observation: PerceptObservation) -> PerceptPrototype:
        prototype_id = f"proto:{self._next_id:04d}"
        self._next_id += 1
        proto = PerceptPrototype(
            prototype_id=prototype_id,
            token=f"percept::prototype::{prototype_id}",
            vector=vector,
            support=1.0,
            continuity_anchor=observation.continuity_anchor,
            last_tick=int(observation.tick),
            modality_mix=_merged_tuple((), observation.modality),
        )
        self._prototypes.append(proto)
        return proto

    def _enforce_limit(self) -> None:
        limit = max(1, int(self.config.percept_max_prototypes))
        if len(self._prototypes) <= limit:
            return
        self._prototypes.sort(key=lambda proto: (proto.support, proto.last_tick), reverse=True)
        del self._prototypes[limit:]

    def _infer_next_id(self) -> int:
        max_id = 0
        for proto in self._prototypes:
            suffix = proto.prototype_id.rsplit(":", 1)[-1]
            try:
                max_id = max(max_id, int(suffix))
            except ValueError:
                continue
        return max_id + 1


def _vector_from_features(features: Mapping[str, float]) -> tuple[float, ...]:
    ordered = [float(features[key]) for key in sorted(features)]
    return _normalize(tuple(ordered))


def _normalize(vector: tuple[float, ...]) -> tuple[float, ...]:
    norm = sqrt(sum(value * value for value in vector))
    if norm <= 1e-12:
        return tuple(0.0 for _ in vector)
    return tuple(round(value / norm, 6) for value in vector)


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right))))


def _merged_tuple(values: tuple[str, ...], new_value: str | None) -> tuple[str, ...]:
    result = list(values)
    if new_value and new_value not in result:
        result.append(new_value)
    return tuple(result)
