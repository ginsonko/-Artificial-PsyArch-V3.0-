from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


FAST_STORE_SCHEMA = "apv3_phase20_6_fast_action_chain_store/v1"
SLOW_STORE_SCHEMA = "apv3_phase20_6_slow_memory_store/v1"


@dataclass(frozen=True)
class FastChainHint:
    chain_id: str
    context_signature: str
    next_outcome_kind: str
    support: float
    update_count: int


@dataclass(frozen=True)
class SlowMemoryHint:
    memory_id: str
    source_candidate_id: str
    source_kind: str
    support: float
    last_tick: int


def fast_hints_from_state(state: Mapping[str, Any], *, context_signature: str) -> tuple[FastChainHint, ...]:
    store = state.get("phase20_6_fast_action_chains")
    if not isinstance(store, Mapping):
        return ()
    rows = store.get("chains", [])
    hints = []
    for row in rows if isinstance(rows, list) else ():
        if not isinstance(row, Mapping):
            continue
        if str(row.get("context_signature", "")) != str(context_signature):
            continue
        hints.append(
            FastChainHint(
                chain_id=str(row.get("chain_id", "")),
                context_signature=str(row.get("context_signature", "")),
                next_outcome_kind=str(row.get("next_outcome_kind", "")),
                support=float(row.get("support", 0.0) or 0.0),
                update_count=int(row.get("update_count", 0) or 0),
            )
        )
    return tuple(sorted(hints, key=lambda item: (-item.support, item.chain_id))[:8])


def slow_hints_from_state(state: Mapping[str, Any], *, source_candidate_ids: Sequence[str]) -> tuple[SlowMemoryHint, ...]:
    wanted = {str(item) for item in source_candidate_ids if str(item)}
    if not wanted:
        return ()
    store = state.get("phase20_6_slow_memory")
    if not isinstance(store, Mapping):
        return ()
    rows = store.get("memories", [])
    hints = []
    for row in rows if isinstance(rows, list) else ():
        if not isinstance(row, Mapping):
            continue
        source_candidate_id = str(row.get("source_candidate_id", ""))
        if source_candidate_id not in wanted:
            continue
        hints.append(
            SlowMemoryHint(
                memory_id=str(row.get("memory_id", "")),
                source_candidate_id=source_candidate_id,
                source_kind=str(row.get("source_kind", "")),
                support=float(row.get("support", 0.0) or 0.0),
                last_tick=int(row.get("last_tick", 0) or 0),
            )
        )
    return tuple(sorted(hints, key=lambda item: (-item.support, item.memory_id))[:8])


def consolidate_phase20_6_memory(
    state: Mapping[str, Any],
    *,
    context_signature: str,
    runtime_events: Sequence[Mapping[str, Any]],
    tick: int,
) -> dict[str, Any]:
    """Persist action-chain and source-candidate evidence without answer tables."""

    new_state = dict(state)
    action_kinds = [
        str(event.get("action_chosen", {}).get("outcome_kind", ""))
        for event in runtime_events
        if isinstance(event, Mapping) and event.get("source") == "phase20_6_true_runtime_boundary"
    ]
    write_source_ids = []
    write_source_kinds = []
    tick_memory_records: list[dict[str, Any]] = []
    for event in runtime_events:
        if not isinstance(event, Mapping):
            continue
        records = event.get("phase20_6_tick_memory_records", [])
        if isinstance(records, list):
            tick_memory_records.extend(dict(row) for row in records if isinstance(row, Mapping))
        draft = event.get("draft_changes", {})
        if not isinstance(draft, Mapping) or draft.get("draft_action_kind") != "type_text":
            continue
        source_id = str(draft.get("source_candidate_id", ""))
        source_kind = str(draft.get("source_kind", ""))
        if source_id:
            write_source_ids.append(source_id)
            write_source_kinds.append(source_kind)

    new_state["phase20_6_fast_action_chains"] = _updated_fast_store(
        new_state.get("phase20_6_fast_action_chains"),
        context_signature=context_signature,
        action_kinds=tuple(action_kinds),
        tick=int(tick),
    )
    new_state["phase20_6_slow_memory"] = _updated_slow_store(
        new_state.get("phase20_6_slow_memory"),
        source_candidate_ids=tuple(write_source_ids),
        source_kinds=tuple(write_source_kinds),
        tick=int(tick),
    )
    new_state["phase20_6_tick_memories"] = _updated_tick_memory_store(
        new_state.get("phase20_6_tick_memories"),
        tick_memory_records=tuple(tick_memory_records),
        tick=int(tick),
    )
    return new_state


def _updated_fast_store(
    payload: Any,
    *,
    context_signature: str,
    action_kinds: Sequence[str],
    tick: int,
) -> dict[str, Any]:
    rows = []
    if isinstance(payload, Mapping) and isinstance(payload.get("chains"), list):
        rows = [dict(row) for row in payload["chains"] if isinstance(row, Mapping)]
    compact_actions = tuple(kind for kind in action_kinds if kind and kind != "idle_observe")
    for index, outcome_kind in enumerate(compact_actions[:16]):
        chain_id = f"fast_chain::{context_signature}::{index}::{outcome_kind}"
        existing = next((row for row in rows if row.get("chain_id") == chain_id), None)
        if existing is None:
            rows.append(
                {
                    "chain_id": chain_id,
                    "context_signature": str(context_signature),
                    "step_index": index,
                    "next_outcome_kind": str(outcome_kind),
                    "support": 1.0,
                    "update_count": 1,
                    "last_tick": int(tick),
                    "stores_surface_phrase": False,
                }
            )
        else:
            existing["support"] = float(existing.get("support", 0.0) or 0.0) + 1.0
            existing["update_count"] = int(existing.get("update_count", 0) or 0) + 1
            existing["last_tick"] = int(tick)
    return {
        "schema_id": FAST_STORE_SCHEMA,
        "chains": sorted(rows, key=lambda row: (-float(row.get("support", 0.0) or 0.0), str(row.get("chain_id", ""))))[:512],
    }


def _updated_slow_store(
    payload: Any,
    *,
    source_candidate_ids: Sequence[str],
    source_kinds: Sequence[str],
    tick: int,
) -> dict[str, Any]:
    rows = []
    if isinstance(payload, Mapping) and isinstance(payload.get("memories"), list):
        rows = [dict(row) for row in payload["memories"] if isinstance(row, Mapping)]
    for index, source_id in enumerate(source_candidate_ids):
        source_kind = source_kinds[index] if index < len(source_kinds) else ""
        memory_id = f"slow_source::{source_id}"
        existing = next((row for row in rows if row.get("memory_id") == memory_id), None)
        if existing is None:
            rows.append(
                {
                    "memory_id": memory_id,
                    "source_candidate_id": str(source_id),
                    "source_kind": str(source_kind),
                    "support": 1.0,
                    "update_count": 1,
                    "last_tick": int(tick),
                    "stores_surface_phrase": False,
                    "semantic_authority": "source_tagged_candidate",
                }
            )
        else:
            existing["support"] = float(existing.get("support", 0.0) or 0.0) + 1.0
            existing["update_count"] = int(existing.get("update_count", 0) or 0) + 1
            existing["last_tick"] = int(tick)
    return {
        "schema_id": SLOW_STORE_SCHEMA,
        "memories": sorted(rows, key=lambda row: (-float(row.get("support", 0.0) or 0.0), str(row.get("memory_id", ""))))[:1024],
    }


def _updated_tick_memory_store(
    payload: Any,
    *,
    tick_memory_records: Sequence[Mapping[str, Any]],
    tick: int,
) -> dict[str, Any]:
    rows = []
    if isinstance(payload, Mapping) and isinstance(payload.get("memories"), list):
        rows = [dict(row) for row in payload["memories"] if isinstance(row, Mapping)]
    by_id = {str(row.get("memory_id", "")): row for row in rows if row.get("memory_id")}
    for raw in tick_memory_records:
        memory_id = str(raw.get("memory_id", ""))
        if not memory_id:
            continue
        row = dict(raw)
        row["last_tick"] = int(tick)
        row.setdefault("update_count", 1)
        row.setdefault("support", 1.0)
        by_id[memory_id] = row
    merged = sorted(
        by_id.values(),
        key=lambda row: (
            -int(row.get("last_tick", 0) or 0),
            str(row.get("memory_tier", "")),
            str(row.get("memory_id", "")),
        ),
    )
    return {
        "schema_id": "apv3_phase20_6_tick_memory_store/v1",
        "memories": merged[:2048],
    }
