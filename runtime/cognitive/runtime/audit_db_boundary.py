from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderOnlyReference:
    payload_id: str
    owner: str = "ui_render"
    can_read_payload: bool = False


def make_render_only_reference(payload_id: str, *, owner: str = "ui_render") -> RenderOnlyReference:
    """@op_count: O(1)."""
    return RenderOnlyReference(payload_id=str(payload_id), owner=str(owner))


def cognitive_payload_access_allowed(reference: RenderOnlyReference) -> bool:
    """@op_count: O(1)."""
    return bool(reference.can_read_payload)

