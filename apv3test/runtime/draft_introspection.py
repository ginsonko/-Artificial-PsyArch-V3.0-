from __future__ import annotations

from dataclasses import dataclass
from math import exp, sqrt
from typing import Any, Iterable, Mapping, Protocol, Sequence

from apv3test.config.introspection_config import APV3DraftIntrospectionConfig


class DraftSAEnergyView(Protocol):
    """Modality-neutral numeric view over a draft SA."""

    @property
    def fit_margin(self) -> float: ...

    @property
    def occupancy(self) -> float: ...

    @property
    def commit_readiness(self) -> float: ...

    @property
    def role(self) -> str: ...

    @property
    def is_filled(self) -> bool: ...


@dataclass(frozen=True)
class DraftStructuralFacts:
    has_shared_after_unresolved: bool
    mean_slot_occupancy: float
    min_fit_margin: float
    paradigm_competition: float
    commit_readiness: float
    recent_punishment_resemblance: float
    unresolved_slot_count_norm: float
    commit_blocked: bool

    def to_phi(self) -> tuple[float, ...]:
        return (
            1.0 if self.has_shared_after_unresolved else 0.0,
            _clamp01(self.mean_slot_occupancy),
            _clamp01(self.min_fit_margin),
            _clamp01(self.paradigm_competition),
            _clamp01(self.commit_readiness),
            _clamp01(self.recent_punishment_resemblance),
            _clamp01(self.unresolved_slot_count_norm),
        )


@dataclass
class IntrospectionPrototype:
    prototype_id: int
    mu: tuple[float, ...]
    tau: tuple[float, ...]
    activation_ema: float
    last_activated_tick: int
    phi_pooling_schema_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "prototype_id": int(self.prototype_id),
            "mu": list(self.mu),
            "tau": list(self.tau),
            "activation_ema": float(self.activation_ema),
            "last_activated_tick": int(self.last_activated_tick),
            "phi_pooling_schema_version": self.phi_pooling_schema_version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], config: APV3DraftIntrospectionConfig) -> "IntrospectionPrototype":
        mu = _float_tuple(payload.get("mu"), width=config.feature_width)
        tau = _float_tuple(payload.get("tau"), width=config.feature_width, default=config.tau_init)
        version = str(payload.get("phi_pooling_schema_version", config.phi_pooling_schema_version))
        if version != config.phi_pooling_schema_version:
            mu = tuple(0.0 if index == 5 else value for index, value in enumerate(mu))
            tau = tuple(config.tau_init if index == 5 else value for index, value in enumerate(tau))
            version = config.phi_pooling_schema_version
        return cls(
            prototype_id=int(payload.get("prototype_id", 0)),
            mu=mu,
            tau=tau,
            activation_ema=max(0.0, float(payload.get("activation_ema", 0.0))),
            last_activated_tick=int(payload.get("last_activated_tick", 0)),
            phi_pooling_schema_version=version,
        )


@dataclass(frozen=True)
class DraftIntrospectionFeeling:
    sa_label: str
    sa_type: str
    real_energy: float
    cognitive_pressure: float
    tick: int
    facts: DraftStructuralFacts

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "apv3_draft_introspection_feeling/v1",
            "sa_label": self.sa_label,
            "sa_type": self.sa_type,
            "real_energy": round(float(self.real_energy), 6),
            "cognitive_pressure": round(float(self.cognitive_pressure), 6),
            "tick": int(self.tick),
            "facts": {
                "has_shared_after_unresolved": self.facts.has_shared_after_unresolved,
                "mean_slot_occupancy": round(self.facts.mean_slot_occupancy, 6),
                "min_fit_margin": round(self.facts.min_fit_margin, 6),
                "paradigm_competition": round(self.facts.paradigm_competition, 6),
                "commit_readiness": round(self.facts.commit_readiness, 6),
                "recent_punishment_resemblance": round(self.facts.recent_punishment_resemblance, 6),
                "unresolved_slot_count_norm": round(self.facts.unresolved_slot_count_norm, 6),
                "commit_blocked": self.facts.commit_blocked,
            },
        }


class IntrospectionPrototypeStore:
    """Observer-only prototype store for draft-introspection feelings."""

    def __init__(
        self,
        config: APV3DraftIntrospectionConfig | None = None,
        prototypes: Iterable[IntrospectionPrototype] = (),
        *,
        next_id: int | None = None,
    ) -> None:
        self.config = config or APV3DraftIntrospectionConfig()
        self._prototypes = list(prototypes)
        self._next_id = int(next_id) if next_id is not None else self._infer_next_id()

    @property
    def prototypes(self) -> tuple[IntrospectionPrototype, ...]:
        return tuple(self._prototypes)

    @property
    def next_id(self) -> int:
        return self._next_id

    def respond_or_spawn(self, phi: Sequence[float], *, current_tick: int) -> tuple[IntrospectionPrototype, float]:
        vector = _normalized_phi(phi, self.config.feature_width)
        if not self._prototypes:
            return self._spawn(vector, current_tick), 1.0
        best_distance = min(_whitened_distance(vector, proto) for proto in self._prototypes)
        if best_distance > self.config.theta_spawn:
            return self._spawn(vector, current_tick), 1.0
        responsibilities = self._responsibilities(vector)
        for proto, weight in responsibilities:
            self._update_prototype(proto, vector, weight, current_tick)
        best_proto, best_weight = max(responsibilities, key=lambda item: item[1])
        return best_proto, best_weight

    def decay_unactivated(self, *, current_tick: int, association_store: Any | None = None) -> tuple[str, ...]:
        evicted_labels: list[str] = []
        live: list[IntrospectionPrototype] = []
        for proto in self._prototypes:
            if proto.last_activated_tick != int(current_tick):
                proto.activation_ema *= self.config.half_life_decay
            if proto.activation_ema > self.config.eviction_floor:
                live.append(proto)
            else:
                evicted_labels.append(make_feeling_label(proto.prototype_id))
        if len(live) > self.config.max_prototypes:
            live.sort(key=lambda item: item.activation_ema, reverse=True)
            for proto in live[self.config.max_prototypes :]:
                evicted_labels.append(make_feeling_label(proto.prototype_id))
            live = live[: self.config.max_prototypes]
        self._prototypes = live
        if association_store is not None:
            for label in evicted_labels:
                try:
                    association_store.retire_label(label, current_tick)
                except AttributeError:
                    pass
        return tuple(evicted_labels)

    def export_state(self) -> dict[str, Any]:
        return {
            "schema_id": "apv3_introspection_prototype_store/v1",
            "next_id": int(self._next_id),
            "phi_pooling_schema_version": self.config.phi_pooling_schema_version,
            "prototypes": [proto.to_dict() for proto in self._prototypes],
        }

    @classmethod
    def from_state(
        cls,
        payload: Mapping[str, Any] | None,
        config: APV3DraftIntrospectionConfig | None = None,
    ) -> "IntrospectionPrototypeStore":
        cfg = config or APV3DraftIntrospectionConfig()
        if not isinstance(payload, Mapping):
            return cls(cfg)
        raw_items = payload.get("prototypes", [])
        prototypes = [
            IntrospectionPrototype.from_dict(item, cfg)
            for item in raw_items
            if isinstance(item, Mapping)
        ] if isinstance(raw_items, list) else []
        next_id = payload.get("next_id")
        if next_id is None:
            next_id = max((proto.prototype_id for proto in prototypes), default=-1) + 1
        return cls(cfg, prototypes, next_id=int(next_id))

    def _spawn(self, phi: tuple[float, ...], current_tick: int) -> IntrospectionPrototype:
        proto = IntrospectionPrototype(
            prototype_id=self._next_id,
            mu=phi,
            tau=tuple(self.config.tau_init for _ in range(self.config.feature_width)),
            activation_ema=1.0,
            last_activated_tick=int(current_tick),
            phi_pooling_schema_version=self.config.phi_pooling_schema_version,
        )
        self._next_id += 1
        self._prototypes.append(proto)
        return proto

    def _update_prototype(self, proto: IntrospectionPrototype, phi: tuple[float, ...], weight: float, current_tick: int) -> None:
        eta = max(0.0, min(1.0, self.config.eta_mu * float(weight)))
        old_mu = proto.mu
        residual_sq = tuple((phi[index] - old_mu[index]) ** 2 for index in range(self.config.feature_width))
        proto.tau = tuple(
            max(
                self.config.tau_floor,
                sqrt((1.0 - eta) * proto.tau[index] * proto.tau[index] + eta * residual_sq[index]),
            )
            for index in range(self.config.feature_width)
        )
        proto.mu = tuple((1.0 - eta) * old_mu[index] + eta * phi[index] for index in range(self.config.feature_width))
        proto.activation_ema = proto.activation_ema * self.config.half_life_decay + float(weight)
        proto.last_activated_tick = int(current_tick)

    def _responsibilities(self, phi: tuple[float, ...]) -> tuple[tuple[IntrospectionPrototype, float], ...]:
        logits = tuple(-0.5 * _whitened_distance(phi, proto) ** 2 for proto in self._prototypes)
        max_logit = max(logits)
        raw = tuple(exp(value - max_logit) for value in logits)
        total = sum(raw)
        if total <= 0.0:
            share = 1.0 / max(1, len(self._prototypes))
            return tuple((proto, share) for proto in self._prototypes)
        return tuple((proto, raw[index] / total) for index, proto in enumerate(self._prototypes))

    def _infer_next_id(self) -> int:
        return max((proto.prototype_id for proto in self._prototypes), default=-1) + 1


def extract_facts(
    views: Sequence[DraftSAEnergyView],
    *,
    paradigm_competition: float = 0.0,
    recent_punishment_resemblance: float = 0.0,
) -> DraftStructuralFacts:
    slot_views = [view for view in views if view.role == "slot"]
    unresolved_slots = sum(1 for view in slot_views if not view.is_filled)
    has_shared = False
    seen_unresolved_slot = False
    for view in views:
        if view.role == "slot" and not view.is_filled:
            seen_unresolved_slot = True
        if seen_unresolved_slot and view.role in {"fixed_anchor", "shared_fragment"}:
            has_shared = True
            break
    mean_occ = sum(_clamp01(view.occupancy) for view in slot_views) / max(1, len(slot_views))
    min_margin = min((_clamp01(view.fit_margin) for view in slot_views), default=1.0)
    readiness = sum(_clamp01(view.commit_readiness) for view in views) / max(1, len(views))
    unresolved_norm = unresolved_slots / max(1, len(slot_views))
    commit_blocked = has_shared or unresolved_slots > 0 or min_margin < 0.2 or readiness < 0.25
    return DraftStructuralFacts(
        has_shared_after_unresolved=has_shared,
        mean_slot_occupancy=mean_occ,
        min_fit_margin=min_margin,
        paradigm_competition=_clamp01(paradigm_competition),
        commit_readiness=readiness,
        recent_punishment_resemblance=_clamp01(recent_punishment_resemblance),
        unresolved_slot_count_norm=unresolved_norm,
        commit_blocked=commit_blocked,
    )


def emit_draft_introspection_feelings(
    state: Mapping[str, Any],
    views: Sequence[DraftSAEnergyView],
    *,
    store: IntrospectionPrototypeStore | None = None,
    current_tick: int | None = None,
    paradigm_competition: float = 0.0,
    recent_punishment_resemblance: float = 0.0,
) -> dict[str, Any]:
    next_state = dict(state)
    tick = int(current_tick if current_tick is not None else next_state.get("tick", 0))
    active_store = store or IntrospectionPrototypeStore.from_state(next_state.get("introspection_prototype_store"))
    feelings = list(next_state.get("introspection_feelings", [])) if isinstance(next_state.get("introspection_feelings", []), list) else []
    if views:
        facts = extract_facts(
            views,
            paradigm_competition=paradigm_competition,
            recent_punishment_resemblance=recent_punishment_resemblance,
        )
        proto, response = active_store.respond_or_spawn(facts.to_phi(), current_tick=tick)
        feeling = DraftIntrospectionFeeling(
            sa_label=make_feeling_label(proto.prototype_id),
            sa_type="draft_introspection_feeling",
            real_energy=response,
            cognitive_pressure=(1.0 / (1.0 + max(0.0, proto.activation_ema))) * active_store.config.beta_pressure,
            tick=tick,
            facts=facts,
        )
        feelings.append(feeling.to_dict())
        next_state["draft_commit_blocked"] = facts.commit_blocked
    active_store.decay_unactivated(current_tick=tick)
    next_state["introspection_prototype_store"] = active_store.export_state()
    next_state["introspection_feelings"] = feelings
    next_state["tick"] = tick + 1
    return next_state


def make_feeling_label(prototype_id: int) -> str:
    return f"feeling::draft::proto_{int(prototype_id)}"


def _whitened_distance(phi: Sequence[float], proto: IntrospectionPrototype) -> float:
    total = 0.0
    for index, value in enumerate(phi):
        scale = max(1e-9, proto.tau[index])
        total += ((float(value) - proto.mu[index]) / scale) ** 2
    return sqrt(total)


def _normalized_phi(phi: Sequence[float], width: int) -> tuple[float, ...]:
    values = [float(item) for item in phi]
    if len(values) != width:
        raise ValueError(f"expected phi width {width}, got {len(values)}")
    return tuple(_clamp01(value) for value in values)


def _float_tuple(value: Any, *, width: int, default: float = 0.0) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)):
        return tuple(float(default) for _ in range(width))
    values = [float(item) for item in value[:width]]
    while len(values) < width:
        values.append(float(default))
    return tuple(values)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
