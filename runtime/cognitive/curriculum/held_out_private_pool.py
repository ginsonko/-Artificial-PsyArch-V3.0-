from __future__ import annotations

import random
import secrets
from dataclasses import dataclass, field
from typing import Mapping

from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


@dataclass(frozen=True)
class EvaluatorMetadata:
    target_class: str
    evaluator_payload: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PrivateHandle:
    handle_id: str
    metadata: EvaluatorMetadata


@dataclass(frozen=True)
class PublicHeldOutEvent:
    content_sas: tuple[StateItem, ...]
    source_markers: tuple[MarkerEvent, ...] = ()

    def to_ap_items(self) -> tuple[StateItem, ...]:
        """@op_count: O(content)."""
        return tuple(_clone_item(item) for item in self.content_sas)

    def to_public_trace(self) -> dict[str, object]:
        """@op_count: O(content + markers)."""
        return {
            "schema_id": "apv3_public_held_out_event/v1",
            "content_sas": [
                {
                    "sa_id": item.sa_id,
                    "family": item.family,
                    "channel_signature": list(item.channel_signature),
                    "source": item.source,
                }
                for item in self.content_sas
            ],
            "source_markers": [
                {
                    "kind": marker.kind,
                    "target_sa_id": marker.target_sa_id,
                }
                for marker in self.source_markers
            ],
        }


@dataclass(frozen=True)
class EvaluationPair:
    private_handle: PrivateHandle
    public_event: PublicHeldOutEvent


class HeldOutEventPool:
    """Held-out pool whose evaluator metadata never enters AP state."""

    def __init__(self) -> None:
        self._pairs: list[EvaluationPair] = []

    def reserve(
        self,
        public_event: PublicHeldOutEvent,
        evaluator_metadata: EvaluatorMetadata,
    ) -> PrivateHandle:
        """@op_count: O(event)."""
        _validate_public_event(public_event)
        handle = PrivateHandle(
            handle_id=secrets.token_hex(int(load_constant("curriculum.privacy.opaque_handle_bytes"))),
            metadata=evaluator_metadata,
        )
        self._pairs.append(EvaluationPair(private_handle=handle, public_event=public_event))
        return handle

    def sample_evaluation_batch(self, n: int) -> tuple[EvaluationPair, ...]:
        """@op_count: O(pool)."""
        if not self._pairs:
            return ()
        count = min(max(int(n), 0), len(self._pairs))
        return tuple(random.sample(self._pairs, count))

    def export_public_state(self) -> dict[str, object]:
        """@op_count: O(pool * event)."""
        return {
            "schema_id": "apv3_held_out_public_state/v1",
            "events": [pair.public_event.to_public_trace() for pair in self._pairs],
        }

    def __len__(self) -> int:
        return len(self._pairs)


def _validate_public_event(event: PublicHeldOutEvent) -> None:
    """@op_count: O(content + markers)."""
    for marker in event.source_markers:
        if marker.kind != "PERCEIVED":
            raise ValueError("held-out event source marker must be PERCEIVED")
    for item in event.content_sas:
        forbidden = {"vocab_label", "proposition", "answer", "event_id", "private_handle"}
        if forbidden & set(item.metadata):
            raise ValueError("held-out public event must not contain labels, propositions, answers, or ids")


def _clone_item(item: StateItem) -> StateItem:
    """@op_count: O(metadata)."""
    return StateItem(
        sa_id=item.sa_id,
        family=item.family,
        label=item.label,
        real_energy=item.real_energy,
        virtual_energy=item.virtual_energy,
        attention_energy=item.attention_energy,
        fatigue=item.fatigue,
        cognitive_pressure=item.cognitive_pressure,
        last_tick=item.last_tick,
        channel_signature=item.channel_signature,
        source=item.source,
        metadata=dict(item.metadata),
    )

