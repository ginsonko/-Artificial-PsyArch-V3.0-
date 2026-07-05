from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig


ROLES = ("fixed_anchor", "slot", "shared_fragment")


@dataclass(frozen=True)
class RoleDecodeResult:
    roles: tuple[str, ...]
    score: float


class RoleViterbiDecoder:
    """Joint role decoder for aligned APV3 paradigm columns."""

    def __init__(
        self,
        config: APV3ParadigmDiscoveryConfig | None = None,
        transition_bias: Mapping[tuple[str, str], float] | None = None,
    ) -> None:
        self.config = config or APV3ParadigmDiscoveryConfig()
        self.transition_bias = dict(transition_bias or {})

    def decode(self, columns: Sequence[Any]) -> RoleDecodeResult:
        if not columns:
            return RoleDecodeResult((), 0.0)
        dp: list[dict[str, tuple[float, tuple[str, ...]]]] = []
        first = {
            role: (self._emission(columns[0], role), (role,))
            for role in ROLES
        }
        dp.append(first)
        for column in columns[1:]:
            layer: dict[str, tuple[float, tuple[str, ...]]] = {}
            for role in ROLES:
                best_score = -1e12
                best_path: tuple[str, ...] = ()
                for prev_role, (prev_score, prev_path) in dp[-1].items():
                    emit = self._emission(column, role)
                    candidate = prev_score + self._transition(prev_role, role) + emit
                    if candidate > best_score:
                        best_score = candidate
                        best_path = (*prev_path, role)
                layer[role] = (best_score, best_path)
            dp.append(layer)
        score, path = max(dp[-1].values(), key=lambda item: item[0])
        return RoleDecodeResult(path, round(score, 6))

    def apply(self, columns: Sequence[Any]) -> tuple[Any, ...]:
        decoded = self.decode(columns)
        updated: list[Any] = []
        for column, role in zip(columns, decoded.roles):
            anchor = column.anchor_label if role in {"fixed_anchor", "shared_fragment"} else None
            if role in {"fixed_anchor", "shared_fragment"} and anchor is None and len(column.distinct_tokens) == 1:
                anchor = column.distinct_tokens[0]
            updated.append(replace(column, role=role, anchor_label=anchor))
        return tuple(updated)

    def _emission(self, column: Any, role: str) -> float:
        full_single = len(column.distinct_tokens) == 1 and column.occupancy >= self.config.fixed_occupancy_min
        partial_single = (
            len(column.distinct_tokens) == 1
            and column.occupancy >= self.config.shared_occupancy_min
            and column.relation_pair_count > 0
        )
        diverse = len(column.distinct_tokens) > 1 or column.occupancy < self.config.fixed_occupancy_min
        coherence = max(0.0, column.relation_coherence)
        if role == "fixed_anchor":
            if full_single:
                return self.config.role_viterbi_fixed_match_reward * column.occupancy
            return -0.25
        if role == "shared_fragment":
            if full_single or partial_single:
                return self.config.role_viterbi_shared_match_reward * column.occupancy * coherence
            return -0.35
        if role == "slot":
            if full_single:
                return -0.45
            diversity = 1.0 if diverse else 0.0
            return (
                self.config.role_viterbi_slot_coherence_reward * coherence
                + self.config.role_viterbi_slot_diversity_reward * diversity
            )
        return -1.0

    def _transition(self, prev_role: str, role: str) -> float:
        learned_bias = float(self.transition_bias.get((prev_role, role), 0.0))
        if prev_role == role:
            return self.config.role_viterbi_same_role_reward + learned_bias
        if prev_role == "fixed_anchor" and role == "slot":
            return self.config.role_viterbi_fixed_to_slot_reward + learned_bias
        if prev_role == "slot" and role == "shared_fragment":
            return self.config.role_viterbi_slot_to_shared_reward + learned_bias
        if prev_role == "shared_fragment" and role == "slot":
            return self.config.role_viterbi_shared_to_slot_penalty + learned_bias
        return learned_bias
