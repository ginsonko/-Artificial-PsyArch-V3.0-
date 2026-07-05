from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig
from apv3test.runtime.coherence import RelationCoherenceScorer
from apv3test.runtime.role_decode import RoleViterbiDecoder


@dataclass(frozen=True)
class AlignmentColumn:
    col_index: int
    values: tuple[str | None, ...]
    occupancy: float
    distinct_tokens: tuple[str, ...]
    role: str
    anchor_label: str | None
    relation_coherence: float = 0.0
    relation_pair_count: int = 0
    relation_signature_tokens: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnchorRelativeAlignment:
    columns: tuple[AlignmentColumn, ...]

    def role_sequence(self) -> tuple[str, ...]:
        return tuple(column.role for column in self.columns)


class AnchorRelativeAligner:
    """Bounded NW-style alignment for APV3 paradigm columns.

    This is a structural observation operator. It aligns SA/token sequences into
    columns; it does not choose actions, mutate embeddings, or create policy.
    """

    def __init__(
        self,
        config: APV3ParadigmDiscoveryConfig | None = None,
        transition_bias: Mapping[tuple[str, str], float] | None = None,
    ) -> None:
        self.config = config or APV3ParadigmDiscoveryConfig()
        self.coherence = RelationCoherenceScorer(self.config)
        self.role_decoder = RoleViterbiDecoder(self.config, transition_bias=transition_bias)

    def align(self, sequences: Sequence[Sequence[str]]) -> AnchorRelativeAlignment:
        normalized = tuple(tuple(seq)[: self.config.alignment_max_len] for seq in sequences)
        if not normalized:
            return AnchorRelativeAlignment(())
        profile: list[list[str | None]] = [[token] for token in normalized[0]]
        for seq_index, sequence in enumerate(normalized[1:], start=1):
            consensus = tuple(_consensus_token(column) for column in profile)
            pair_columns = self._align_pair(consensus, sequence)
            profile = self._merge_profile(profile, pair_columns, previous_count=seq_index)
        columns = self._classify_columns(profile, normalized)
        return AnchorRelativeAlignment(self.role_decoder.apply(columns))

    def _align_pair(
        self,
        left: tuple[str | None, ...],
        right: tuple[str, ...],
    ) -> list[tuple[str | None, str | None]]:
        n = len(left)
        m = len(right)
        neg_inf = -1e12
        score = [[neg_inf for _ in range(m + 1)] for _ in range(n + 1)]
        back: list[list[str | None]] = [[None for _ in range(m + 1)] for _ in range(n + 1)]
        score[0][0] = 0.0
        for i in range(n + 1):
            j_min = max(0, i - self.config.alignment_max_window)
            j_max = min(m, i + self.config.alignment_max_window)
            for j in range(j_min, j_max + 1):
                current = score[i][j]
                if current <= neg_inf / 2:
                    continue
                if i < n and j < m and abs((i + 1) - (j + 1)) <= self.config.alignment_max_window:
                    candidate = current + self._match_score(left[i], right[j])
                    if candidate > score[i + 1][j + 1]:
                        score[i + 1][j + 1] = candidate
                        back[i + 1][j + 1] = "diag"
                if i < n and abs((i + 1) - j) <= self.config.alignment_max_window:
                    candidate = current + self.config.alignment_gap_penalty
                    if candidate > score[i + 1][j]:
                        score[i + 1][j] = candidate
                        back[i + 1][j] = "left_gap"
                if j < m and abs(i - (j + 1)) <= self.config.alignment_max_window:
                    candidate = current + self.config.alignment_gap_penalty
                    if candidate > score[i][j + 1]:
                        score[i][j + 1] = candidate
                        back[i][j + 1] = "right_gap"
        return self._traceback(left, right, back)

    def _match_score(self, left: str | None, right: str) -> float:
        if left is None:
            return self.config.alignment_mismatch_penalty * 0.5
        if left == right:
            return self.config.alignment_match_reward
        return self.config.alignment_mismatch_penalty

    def _traceback(
        self,
        left: tuple[str | None, ...],
        right: tuple[str, ...],
        back: list[list[str | None]],
    ) -> list[tuple[str | None, str | None]]:
        i = len(left)
        j = len(right)
        result: list[tuple[str | None, str | None]] = []
        while i > 0 or j > 0:
            move = back[i][j]
            if move == "diag":
                result.append((left[i - 1], right[j - 1]))
                i -= 1
                j -= 1
            elif move == "left_gap":
                result.append((left[i - 1], None))
                i -= 1
            elif move == "right_gap":
                result.append((None, right[j - 1]))
                j -= 1
            else:
                if i > 0:
                    result.append((left[i - 1], None))
                    i -= 1
                elif j > 0:
                    result.append((None, right[j - 1]))
                    j -= 1
        result.reverse()
        return result

    def _merge_profile(
        self,
        profile: list[list[str | None]],
        pair_columns: list[tuple[str | None, str | None]],
        *,
        previous_count: int,
    ) -> list[list[str | None]]:
        merged: list[list[str | None]] = []
        profile_index = 0
        for left_token, right_token in pair_columns:
            if left_token is None:
                merged.append([None for _ in range(previous_count)] + [right_token])
            else:
                if profile_index < len(profile):
                    merged.append([*profile[profile_index], right_token])
                    profile_index += 1
                else:
                    merged.append([None for _ in range(previous_count)] + [right_token])
        while profile_index < len(profile):
            merged.append([*profile[profile_index], None])
            profile_index += 1
        return merged

    def _classify_columns(
        self,
        profile: list[list[str | None]],
        sequences: tuple[tuple[str, ...], ...],
    ) -> list[AlignmentColumn]:
        columns: list[AlignmentColumn] = []
        total = max(1, len(profile[0]) if profile else 1)
        for index, values in enumerate(profile):
            present = tuple(value for value in values if value is not None)
            distinct = tuple(sorted(set(present)))
            occupancy = len(present) / total
            coherence = self.coherence.score_column(sequences, values)
            columns.append(
                AlignmentColumn(
                    col_index=index,
                    values=tuple(values),
                    occupancy=round(occupancy, 6),
                    distinct_tokens=distinct,
                    role="slot",
                    anchor_label=None,
                    relation_coherence=coherence.score,
                    relation_pair_count=coherence.pair_count,
                    relation_signature_tokens=tuple(signature.token for signature in coherence.signatures),
                )
            )
        return columns


def _consensus_token(values: Sequence[str | None]) -> str | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    counts = {value: present.count(value) for value in set(present)}
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
