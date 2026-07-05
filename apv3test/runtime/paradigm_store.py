from __future__ import annotations

from typing import Any, Mapping, Sequence

from apv3test.config.habit_config import APV3HabitConfig
from apv3test.config.paradigm_config import APV3ParadigmDiscoveryConfig
from apv3test.runtime.alignment import AlignmentColumn
from apv3test.runtime.paradigm_discovery import DiscoveredParadigm, ParadigmObservation
from apv3test.runtime.paradigm_stats import decayed_pressure
from apv3test.runtime.paradigm_types import IncrementalParadigmObservation


def ensure_incremental_state(state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("schema_id", "apv3_runtime_ontology_state/v1")
    state.setdefault("online_embedding", {}).setdefault("tokens", {})
    state.setdefault("paradigm_observations", [])
    state.setdefault("paradigm_stats", {})
    state.setdefault("role_transition_stats", [])
    state.setdefault("paradigms", [])
    state.setdefault("state_field_items", [])
    state.setdefault("dirty_paradigm_buckets", [])
    return state


def append_observation(state: dict[str, Any], observation: IncrementalParadigmObservation, bucket: str) -> None:
    rows = state["paradigm_observations"]
    if not isinstance(rows, list):
        state["paradigm_observations"] = []
        rows = state["paradigm_observations"]
    rows.append(
        {
            "schema_id": "apv3_paradigm_observation/v1",
            "observation_id": observation.observation_id,
            "bucket": bucket,
            "case_name": observation.case_name,
            "cue_tokens": list(observation.cue_tokens),
            "reply_tokens": list(observation.reply_tokens),
            "tick_id": int(observation.tick_id),
            "context_tokens": list(observation.context_tokens),
            "modality": observation.modality,
            "committed": bool(observation.committed),
            "reward_delta": float(observation.reward_delta),
            "punish_delta": float(observation.punish_delta),
            "source_kind": observation.source_kind,
            "teacher_stage": observation.teacher_stage,
        }
    )


def mark_dirty(state: dict[str, Any], bucket: str, limit: int) -> None:
    dirty = state["dirty_paradigm_buckets"]
    if not isinstance(dirty, list):
        state["dirty_paradigm_buckets"] = []
        dirty = state["dirty_paradigm_buckets"]
    if bucket in dirty:
        dirty.remove(bucket)
    dirty.insert(0, bucket)
    del dirty[max(1, int(limit)) :]


def bucket_observations(state: Mapping[str, Any], bucket: str) -> tuple[ParadigmObservation, ...]:
    rows = state.get("paradigm_observations", [])
    if not isinstance(rows, list):
        return ()
    result: list[ParadigmObservation] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("bucket") != bucket or not bool(row.get("committed", False)):
            continue
        result.append(
            ParadigmObservation(
                str(row.get("case_name", "")),
                string_tuple(row.get("cue_tokens")),
                string_tuple(row.get("reply_tokens")),
            )
        )
    return tuple(result)


def update_paradigm_stats(
    state: dict[str, Any],
    paradigm: DiscoveredParadigm,
    observation: IncrementalParadigmObservation,
    *,
    bucket: str,
    config: APV3ParadigmDiscoveryConfig,
    habit_config: APV3HabitConfig,
) -> bool:
    stats = state["paradigm_stats"]
    if not isinstance(stats, dict):
        state["paradigm_stats"] = {}
        stats = state["paradigm_stats"]
    payload = stats.get(bucket, {})
    if not isinstance(payload, dict):
        payload = {}
    payload["bucket"] = bucket
    payload["pid"] = paradigm.pid
    payload["case_name"] = paradigm.case_name
    payload["support"] = float(paradigm.support)
    payload["conf"] = float(paradigm.conf)
    payload["last_tick"] = int(observation.tick_id)
    payload["columns"] = [_column_payload(column) for column in paradigm.columns]
    payload["reward_support"] = _nonnegative(_as_float(payload.get("reward_support")) + observation.reward_delta)
    payload["punish_support"] = _nonnegative(_as_float(payload.get("punish_support")) + observation.punish_delta)
    if observation.reward_delta > 0:
        payload["reward_last_tick"] = int(observation.tick_id)
    if observation.punish_delta > 0:
        payload["punish_last_tick"] = int(observation.tick_id)
    payload["observation_ids"] = _merged_list(payload.get("observation_ids"), (observation.observation_id,))
    punish_pressure = decayed_pressure(
        payload.get("punish_support"),
        payload.get("punish_last_tick"),
        observation.tick_id,
        habit_config,
    )
    reward_pressure = decayed_pressure(
        payload.get("reward_support"),
        payload.get("reward_last_tick"),
        observation.tick_id,
        habit_config,
    )
    exposed = (punish_pressure - config.paradigm_exposure_reward_weight * reward_pressure) < (
        config.paradigm_exposure_punish_block_threshold
    )
    payload["punish_pressure"] = round(punish_pressure, 6)
    payload["reward_pressure"] = round(reward_pressure, 6)
    payload["exposed"] = bool(exposed)
    stats[bucket] = payload
    return bool(exposed)


def upsert_paradigm_pool_entry(
    state: dict[str, Any],
    paradigm: DiscoveredParadigm,
    observation: IncrementalParadigmObservation,
    *,
    bucket: str,
    exposed: bool,
) -> None:
    paradigms = state["paradigms"]
    if not isinstance(paradigms, list):
        state["paradigms"] = []
        paradigms = state["paradigms"]
    payload = {
        "pid": paradigm.pid,
        "entry_kind": "ParadigmSA",
        "pool_entry_schema": "apv3_pool_entry/paradigm_sa/v1",
        "support": float(paradigm.support),
        "conf": float(paradigm.conf),
        "exposed": bool(exposed),
        "slot_types": _unique_preserve_order(column.role for column in paradigm.columns),
        "probe_tags": [paradigm.case_name],
        "anchor_meta": {"bucket": bucket, "stats_ref": f"paradigm_stats:{bucket}"},
        "energy": {
            "R": round(float(paradigm.conf), 6),
            "V": round(float(paradigm.conf) * (1.0 if exposed else 0.25), 6),
            "P": round(max(0.0, 1.0 - float(paradigm.conf)), 6),
            "A": round(float(paradigm.conf) if exposed else 0.0, 6),
            "F": 0.0,
        },
    }
    existing = _find_by_id(paradigms, "pid", paradigm.pid)
    if existing is None:
        paradigms.append(payload)
    else:
        existing.update(payload)
    _upsert_state_field_item(state, payload)


def bucket_key(case_name: str, cue_tokens: Sequence[str]) -> str:
    return f"{case_name}|{' '.join(str(token) for token in cue_tokens)}"


def string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value)


def _upsert_state_field_item(state: dict[str, Any], paradigm_payload: Mapping[str, Any]) -> None:
    items = state["state_field_items"]
    if not isinstance(items, list):
        state["state_field_items"] = []
        items = state["state_field_items"]
    item_id = str(paradigm_payload.get("pid", ""))
    payload = {
        "item_id": item_id,
        "sa_type": "paradigm_sa",
        "ref": item_id,
        "energy": dict(paradigm_payload.get("energy", {})),
        "anchor_meta": dict(paradigm_payload.get("anchor_meta", {})),
    }
    existing = _find_by_id(items, "item_id", item_id)
    if existing is None:
        items.append(payload)
    else:
        existing.update(payload)


def _column_payload(column: AlignmentColumn) -> dict[str, Any]:
    return {
        "col_index": column.col_index,
        "values": list(column.values),
        "occupancy": column.occupancy,
        "distinct_tokens": list(column.distinct_tokens),
        "role": column.role,
        "anchor_label": column.anchor_label,
        "relation_coherence": column.relation_coherence,
        "relation_pair_count": column.relation_pair_count,
        "relation_signature_tokens": list(column.relation_signature_tokens),
    }


def _unique_preserve_order(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(str(value))
    return result


def _find_by_id(items: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    for item in items:
        if str(item.get(key, "")) == value:
            return item
    return None


def _merged_list(existing: object, additions: tuple[str, ...]) -> list[str]:
    merged = [str(item) for item in existing] if isinstance(existing, list) else []
    for item in additions:
        if item not in merged:
            merged.append(str(item))
    return merged


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _nonnegative(value: float) -> float:
    return max(0.0, float(value))
