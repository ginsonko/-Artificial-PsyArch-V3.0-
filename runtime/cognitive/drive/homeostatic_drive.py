from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from runtime.cognitive.state_pool.state_pool import StateItem, StatePool, load_constant


@dataclass(frozen=True)
class DriveSatisfaction:
    drive_kind: str
    strength: float = 1.0


@dataclass(frozen=True)
class DriveTickInput:
    tick: int
    idle_ticks: int = 0
    body_deficit: float = 0.0
    novelty_gap: float = 0.0
    unexplored_mass: float = 0.0
    social_absence_ticks: int = 0
    unfinished_pressure: float = 0.0
    satisfaction_events: tuple[DriveSatisfaction, ...] = ()


@dataclass(frozen=True)
class DriveActionProposal:
    drive_kind: str
    drive_sa_id: str
    action_id: str
    pressure: float
    score: float


@dataclass(frozen=True)
class DriveHomeostasisTrace:
    tick: int
    pressure_by_drive: dict[str, float] = field(default_factory=dict)
    proposals: tuple[DriveActionProposal, ...] = ()


def step_drive_homeostasis(
    state_pool: StatePool,
    tick_input: DriveTickInput,
) -> DriveHomeostasisTrace:
    """@op_count: O(drive_kind_count * feature_count)."""
    feature_map = _input_features(tick_input)
    satisfaction = _satisfaction_map(tick_input.satisfaction_events)
    pressures: dict[str, float] = {}

    for kind in tuple(load_constant("drive.initial_kinds")):
        drive_kind = str(kind)
        item = _ensure_drive_item(state_pool, drive_kind)
        previous = max(0.0, float(item.cognitive_pressure)) * float(
            load_constant("drive.pressure_persistence")
        )
        raw_signal = _weighted_signal(drive_kind, feature_map)
        pressure = _clamp01(
            previous
            + raw_signal * float(load_constant("drive.signal_gain"))
            - satisfaction.get(drive_kind, 0.0)
            * float(load_constant("drive.satisfaction_relief_scale"))
        )
        gain = max(0.0, pressure * float(load_constant("drive.attention_gain_scale")))

        item.real_energy = pressure * float(load_constant("drive.real_energy_scale"))
        item.virtual_energy = item.virtual_energy * float(load_constant("drive.virtual_decay"))
        item.cognitive_pressure = pressure
        item.attention_energy = item.attention_energy + gain
        item.gain_ledger.inject("drive_pressure", gain)
        item.last_tick = int(tick_input.tick)
        item.metadata["drive_kind"] = drive_kind
        item.metadata["last_drive_signal"] = raw_signal
        item.metadata["last_satisfaction"] = satisfaction.get(drive_kind, 0.0)
        pressures[drive_kind] = pressure

    proposals = propose_drive_actions(state_pool.items.values())
    return DriveHomeostasisTrace(
        tick=int(tick_input.tick),
        pressure_by_drive=pressures,
        proposals=proposals,
    )


def propose_drive_actions(items: Iterable[StateItem]) -> tuple[DriveActionProposal, ...]:
    """@op_count: O(active_sa log active_sa)."""
    threshold = float(load_constant("drive.proposal_threshold"))
    proposals = []
    for item in items:
        if item.metadata.get("entity_kind") != "drive":
            continue
        pressure = float(item.cognitive_pressure)
        if pressure < threshold:
            continue
        proposals.append(
            DriveActionProposal(
                drive_kind=str(item.metadata.get("drive_kind", "")),
                drive_sa_id=item.sa_id,
                action_id="drive_action::satisfy_drive",
                pressure=pressure,
                score=pressure + item.attention_energy - item.fatigue,
            )
        )
    return tuple(
        sorted(
            proposals,
            key=lambda proposal: (proposal.score, proposal.drive_sa_id),
            reverse=True,
        )
    )


def drive_sa_id(drive_kind: str) -> str:
    """@op_count: O(1)."""
    return f"EntitySA::drive::{drive_kind}"


def _ensure_drive_item(state_pool: StatePool, drive_kind: str) -> StateItem:
    sa_id = drive_sa_id(drive_kind)
    item = state_pool.items.get(sa_id)
    if item is None:
        item = StateItem(
            sa_id=sa_id,
            family="entity",
            label=f"drive::{drive_kind}",
            channel_signature=("drive", drive_kind),
            source="drive_homeostasis",
            metadata={
                "entity_kind": "drive",
                "drive_kind": drive_kind,
                "ledger_source": "drive_pressure",
            },
        )
        state_pool.items[sa_id] = item
    return item


def _input_features(tick_input: DriveTickInput) -> Mapping[str, float]:
    return {
        "body_deficit": _clamp01(float(tick_input.body_deficit)),
        "novelty_gap": _clamp01(float(tick_input.novelty_gap)),
        "unexplored_mass": _clamp01(float(tick_input.unexplored_mass)),
        "unfinished_pressure": _clamp01(float(tick_input.unfinished_pressure)),
        "idle_norm": _normalized_ticks(
            int(tick_input.idle_ticks),
            "drive.idle_ticks_full",
        ),
        "social_absence_norm": _normalized_ticks(
            int(tick_input.social_absence_ticks),
            "drive.social_absence_ticks_full",
        ),
    }


def _weighted_signal(drive_kind: str, feature_map: Mapping[str, float]) -> float:
    weights = dict(load_constant(f"drive.input_weights.{drive_kind}"))
    total = sum(float(weight) * feature_map.get(str(feature), 0.0) for feature, weight in weights.items())
    return _clamp01(total)


def _satisfaction_map(events: Iterable[DriveSatisfaction]) -> dict[str, float]:
    result: dict[str, float] = {}
    for event in events:
        result[event.drive_kind] = result.get(event.drive_kind, 0.0) + _clamp01(event.strength)
    return result


def _normalized_ticks(ticks: int, constant_path: str) -> float:
    denom = max(1.0, float(load_constant(constant_path)))
    return _clamp01(float(max(0, ticks)) / denom)


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))
