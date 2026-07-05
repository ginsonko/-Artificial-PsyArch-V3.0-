from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

from apv3test.runtime.cooccurrence_store import CooccurrenceAssociationStore
from apv3test.runtime.expression_phrase_memory import ExpressionPhraseMemory


PACKAGE_SCHEMA_ID = "apv3_phase20_3_cooccurrence_memory_package/v1"
REGISTRY_KEY = "phase20_memory_package_registry"


@dataclass(frozen=True)
class MemoryPackageResult:
    state: dict[str, Any]
    payload: dict[str, Any]


def list_memory_view(
    state: Mapping[str, Any],
    *,
    query: str = "",
    package_id: str = "",
    kinds: Sequence[str] = (),
    limit: int = 200,
) -> dict[str, Any]:
    memories = _all_memories(state)
    q = str(query or "").strip()
    kind_set = {str(item) for item in kinds if str(item)}
    if q:
        memories = [item for item in memories if q in _search_blob(item)]
    if kind_set:
        memories = [item for item in memories if str(item.get("kind", "")) in kind_set]
    if package_id:
        registry = _registry(state)
        record = next((item for item in registry if str(item.get("package_id", "")) == package_id), {})
        ids = set(str(item) for item in record.get("added_memory_ids", []) + record.get("dedup_memory_ids", []))
        memories = [item for item in memories if str(item.get("memory_id", "")) in ids]
    return {
        "schema_id": "apv3_phase20_3_memory_view/v1",
        "packages": _registry(state),
        "memories": memories[: max(0, int(limit))],
        "total_memories": len(memories),
        "query": q,
        "package_id": str(package_id or ""),
        "kinds": sorted(kind_set),
    }


def export_memory_package(
    state: Mapping[str, Any],
    *,
    name: str,
    query: str = "",
    include_memory_ids: Sequence[str] = (),
    exclude_memory_ids: Sequence[str] = (),
    kinds: Sequence[str] = (),
) -> dict[str, Any]:
    include = {str(item) for item in include_memory_ids if str(item)}
    exclude = {str(item) for item in exclude_memory_ids if str(item)}
    kind_set = {str(item) for item in kinds if str(item)}
    memories = _all_memories(state)
    if include:
        memories = [item for item in memories if str(item.get("memory_id", "")) in include]
    if query:
        memories = [item for item in memories if str(query) in _search_blob(item)]
    if kind_set:
        memories = [item for item in memories if str(item.get("kind", "")) in kind_set]
    if exclude:
        memories = [item for item in memories if str(item.get("memory_id", "")) not in exclude]
    package_id = f"pkg::{_sha16(str(name) + '|' + json.dumps([item['memory_id'] for item in memories], sort_keys=True))}"
    return {
        "schema_id": PACKAGE_SCHEMA_ID,
        "package_id": package_id,
        "name": str(name or "未命名记忆包"),
        "license": "AGPL-3.0-or-later",
        "export_policy": {
            "raw_user_text_included": False,
            "raw_image_included": False,
            "source": "explicit_user_memory_export",
        },
        "memories": memories,
    }


def import_memory_package(state: Mapping[str, Any], package: Mapping[str, Any]) -> MemoryPackageResult:
    if str(package.get("schema_id", "")) != PACKAGE_SCHEMA_ID:
        raise ValueError("unsupported_memory_package_schema")
    next_state = dict(state)
    package_id = str(package.get("package_id", "")) or f"pkg::{_sha16(json.dumps(package, ensure_ascii=False, sort_keys=True))}"
    batch_id = f"batch::{_sha16(package_id + '|' + str(len(_registry(next_state))))}"
    existing_ids = {str(item.get("memory_id", "")) for item in _all_memories(next_state)}
    added: list[str] = []
    dedup: list[str] = []
    for item in package.get("memories", []):
        if not isinstance(item, Mapping):
            continue
        memory_id = str(item.get("memory_id", ""))
        if not memory_id:
            continue
        if memory_id in existing_ids:
            dedup.append(memory_id)
            continue
        _add_memory(next_state, item)
        existing_ids.add(memory_id)
        added.append(memory_id)
    registry = _registry(next_state)
    registry.append(
        {
            "schema_id": "apv3_phase20_3_imported_package_registry/v1",
            "package_id": package_id,
            "name": str(package.get("name", package_id)),
            "import_batch_id": batch_id,
            "status": "active",
            "added_memory_ids": added,
            "dedup_memory_ids": dedup,
            "memory_count": len(added) + len(dedup),
            "added_count": len(added),
            "dedup_count": len(dedup),
        }
    )
    next_state[REGISTRY_KEY] = registry
    return MemoryPackageResult(
        state=next_state,
        payload={
            "package_id": package_id,
            "import_batch_id": batch_id,
            "added_count": len(added),
            "dedup_count": len(dedup),
            "added_memory_ids": added,
            "dedup_memory_ids": dedup,
        },
    )


def uninstall_memory_package(state: Mapping[str, Any], package_id: str) -> MemoryPackageResult:
    next_state = dict(state)
    registry = _registry(next_state)
    record = next((item for item in registry if str(item.get("package_id", "")) == str(package_id)), None)
    if record is None:
        raise ValueError("memory_package_not_found")
    ids = [str(item) for item in record.get("added_memory_ids", []) if str(item)]
    delete_memories_in_place(next_state, ids)
    record["status"] = "uninstalled"
    record["uninstalled_memory_ids"] = ids
    next_state[REGISTRY_KEY] = registry
    return MemoryPackageResult(
        state=next_state,
        payload={"package_id": str(package_id), "removed_count": len(ids), "removed_memory_ids": ids},
    )


def delete_memories(state: Mapping[str, Any], memory_ids: Sequence[str]) -> MemoryPackageResult:
    next_state = dict(state)
    removed = delete_memories_in_place(next_state, memory_ids)
    return MemoryPackageResult(state=next_state, payload={"removed_count": len(removed), "removed_memory_ids": removed})


def delete_memories_in_place(state: dict[str, Any], memory_ids: Sequence[str]) -> list[str]:
    targets = {str(item) for item in memory_ids if str(item)}
    if not targets:
        return []
    removed: list[str] = []
    memory_payload = state.get("expression_phrase_memory")
    if isinstance(memory_payload, Mapping):
        records = []
        for record in memory_payload.get("records", []):
            if not isinstance(record, Mapping):
                continue
            memory_id = f"expr::{record.get('phrase_id', '')}"
            if memory_id in targets:
                removed.append(memory_id)
                continue
            records.append(dict(record))
        state["expression_phrase_memory"] = {**dict(memory_payload), "records": records}
    assoc_payload = state.get("cooccurrence_associations")
    if isinstance(assoc_payload, Mapping):
        pairs, pair_removed = _filter_pairs(assoc_payload.get("pairs"), targets, prefix="assoc")
        paradigm_pairs, paradigm_removed = _filter_pairs(assoc_payload.get("paradigm_pairs"), targets, prefix="assocp")
        removed.extend(pair_removed)
        removed.extend(paradigm_removed)
        state["cooccurrence_associations"] = {
            **dict(assoc_payload),
            "pairs": pairs,
            "paradigm_pairs": paradigm_pairs,
        }
    tick_payload = state.get("phase20_6_tick_memories")
    if isinstance(tick_payload, Mapping):
        rows = []
        for record in tick_payload.get("memories", []):
            if not isinstance(record, Mapping):
                continue
            memory_id = str(record.get("memory_id", ""))
            if memory_id in targets:
                removed.append(memory_id)
                continue
            rows.append(dict(record))
        state["phase20_6_tick_memories"] = {**dict(tick_payload), "memories": rows}
    return removed


def _all_memories(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    memories: list[dict[str, Any]] = []
    memory = ExpressionPhraseMemory.from_state(state.get("expression_phrase_memory"))
    phrase_text_by_id = {record.phrase_id: "".join(record.tokens) for record in memory.records}
    phrase_kind_by_id = {record.phrase_id: record.phrase_kind for record in memory.records}
    for record in memory.records:
        text = "".join(record.tokens)
        memories.append(
            {
                "memory_id": f"expr::{record.phrase_id}",
                "kind": "expression_phrase",
                "kind_label": _kind_label("expression_phrase"),
                "text": text,
                "display_title": _phrase_title(record.phrase_id, text, record.phrase_kind),
                "display_detail": f"{_phrase_kind_label(record.phrase_kind)} · support {record.support:.3f}",
                "tokens": list(record.tokens),
                "support": record.support,
                "phrase_kind": record.phrase_kind,
                "payload": record.to_dict(),
            }
        )
    assoc = CooccurrenceAssociationStore.from_state(state.get("cooccurrence_associations"))
    for pair in assoc.pairs:
        left = _readable_key(pair.key_a, phrase_text_by_id, phrase_kind_by_id)
        right = _readable_key(pair.key_b, phrase_text_by_id, phrase_kind_by_id)
        memories.append(
            {
                "memory_id": _pair_memory_id(pair.key_a, pair.key_b, prefix="assoc"),
                "kind": "cooccurrence_pair",
                "kind_label": _kind_label("cooccurrence_pair"),
                "text": f"{left['title']} ↔ {right['title']}",
                "display_title": f"{left['title']} ↔ {right['title']}",
                "display_detail": f"{left['detail']} / {right['detail']} · support {pair.cumulative_weight:.3f}",
                "endpoint_a": left,
                "endpoint_b": right,
                "support": pair.cumulative_weight,
                "payload": _pair_payload(pair),
            }
        )
    for pair in assoc.paradigm_pairs:
        left = _readable_key(pair.key_a, phrase_text_by_id, phrase_kind_by_id)
        right = _readable_key(pair.key_b, phrase_text_by_id, phrase_kind_by_id)
        memories.append(
            {
                "memory_id": _pair_memory_id(pair.key_a, pair.key_b, prefix="assocp"),
                "kind": "paradigm_pair",
                "kind_label": _kind_label("paradigm_pair"),
                "text": f"{left['title']} ↔ {right['title']}",
                "display_title": f"{left['title']} ↔ {right['title']}",
                "display_detail": f"{left['detail']} / {right['detail']} · support {pair.cumulative_weight:.3f}",
                "endpoint_a": left,
                "endpoint_b": right,
                "support": pair.cumulative_weight,
                "payload": _pair_payload(pair),
            }
        )
    tick_store = state.get("phase20_6_tick_memories")
    if isinstance(tick_store, Mapping):
        for row in tick_store.get("memories", []):
            if not isinstance(row, Mapping):
                continue
            tier = str(row.get("memory_tier", ""))
            memory_id = str(row.get("memory_id", ""))
            if not memory_id:
                continue
            kind = "fast_tick_memory" if tier == "fast" else "slow_tick_memory" if tier == "slow" else "tick_memory"
            memories.append(
                {
                    "memory_id": memory_id,
                    "kind": kind,
                    "kind_label": _kind_label(kind),
                    "text": str(row.get("display_title", memory_id)),
                    "display_title": str(row.get("display_title", memory_id)),
                    "display_detail": str(row.get("display_detail", "")),
                    "support": float(row.get("support", 0.0) or 0.0),
                    "payload": dict(row),
                }
            )
    memories.sort(key=_memory_sort_key)
    return memories


def _memory_sort_key(item: Mapping[str, Any]) -> tuple[int, str, str]:
    phrase_kind = str(item.get("phrase_kind", ""))
    kind = str(item.get("kind", ""))
    priority = {
        "teacher_event_cooccurrence": 0,
        "user_observed_utterance": 1,
        "cooccurrence_pair": 2,
        "paradigm_pair": 3,
        "styled_curriculum_example": 8,
    }.get(phrase_kind, {"cooccurrence_pair": 2, "paradigm_pair": 3, "fast_tick_memory": 4, "slow_tick_memory": 4}.get(kind, 5))
    return (priority, kind, str(item.get("memory_id", "")))


def _add_memory(state: dict[str, Any], item: Mapping[str, Any]) -> None:
    kind = str(item.get("kind", ""))
    payload = item.get("payload", {})
    if not isinstance(payload, Mapping):
        return
    if kind == "expression_phrase":
        memory = ExpressionPhraseMemory.from_state(state.get("expression_phrase_memory"))
        memory.observe(
            str(payload.get("phrase_id", "")),
            tuple(str(token) for token in payload.get("tokens", ()) if str(token)),
            weight=max(float(payload.get("support", 1.0)), 0.0),
            current_tick=int(payload.get("last_update_tick", 1) or 1),
            style_tier=int(payload.get("style_tier", 2) or 2),
            phrase_kind=str(payload.get("phrase_kind", "")),
            allow_new=True,
        )
        state["expression_phrase_memory"] = memory.export_state()
        return
    if kind in {"cooccurrence_pair", "paradigm_pair"}:
        assoc_payload = dict(state.get("cooccurrence_associations", {}) if isinstance(state.get("cooccurrence_associations"), Mapping) else {})
        key = "paradigm_pairs" if kind == "paradigm_pair" else "pairs"
        rows = [dict(row) for row in assoc_payload.get(key, []) if isinstance(row, Mapping)]
        rows.append(dict(payload))
        assoc_payload[key] = rows
        assoc_payload.setdefault("schema_id", "apv3_cooccurrence_association_store/v1")
        assoc_payload.setdefault("pairs", [])
        assoc_payload.setdefault("paradigm_pairs", [])
        state["cooccurrence_associations"] = assoc_payload
    if kind in {"fast_tick_memory", "slow_tick_memory", "tick_memory"}:
        tick_payload = dict(state.get("phase20_6_tick_memories", {}) if isinstance(state.get("phase20_6_tick_memories"), Mapping) else {})
        rows = [dict(row) for row in tick_payload.get("memories", []) if isinstance(row, Mapping)]
        memory_id = str(item.get("memory_id", ""))
        if memory_id and not any(str(row.get("memory_id", "")) == memory_id for row in rows):
            row = dict(payload)
            row.setdefault("memory_id", memory_id)
            row.setdefault("memory_tier", "fast" if kind == "fast_tick_memory" else "slow" if kind == "slow_tick_memory" else "tick")
            rows.append(row)
        tick_payload["schema_id"] = "apv3_phase20_6_tick_memory_store/v1"
        tick_payload["memories"] = rows
        state["phase20_6_tick_memories"] = tick_payload


def _registry(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = state.get(REGISTRY_KEY, [])
    return [dict(item) for item in raw if isinstance(item, Mapping)] if isinstance(raw, list) else []


def _filter_pairs(payload: object, targets: set[str], *, prefix: str) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    removed: list[str] = []
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, Mapping):
            continue
        memory_id = _pair_memory_id(str(item.get("key_a", "")), str(item.get("key_b", "")), prefix=prefix)
        if memory_id in targets:
            removed.append(memory_id)
            continue
        rows.append(dict(item))
    return rows, removed


def _pair_memory_id(key_a: str, key_b: str, *, prefix: str) -> str:
    return f"{prefix}::{_sha16(str(key_a) + '|' + str(key_b))}"


def _pair_payload(pair: Any) -> dict[str, Any]:
    return {
        "key_a": pair.key_a,
        "key_b": pair.key_b,
        "cumulative_weight": pair.cumulative_weight,
        "last_update_tick": pair.last_update_tick,
        "update_count": pair.update_count,
    }


def _search_blob(item: Mapping[str, Any]) -> str:
    return json.dumps(item, ensure_ascii=False, sort_keys=True)


def _kind_label(kind: str) -> str:
    if str(kind) == "fast_tick_memory":
        return "tick 快记忆"
    if str(kind) == "slow_tick_memory":
        return "tick 慢记忆"
    if str(kind) == "tick_memory":
        return "tick 记忆"
    return {
        "expression_phrase": "表达短句",
        "cooccurrence_pair": "共现边",
        "paradigm_pair": "范式共现",
    }.get(str(kind), str(kind))


def _phrase_kind_label(kind: str) -> str:
    if str(kind) == "user_observed_utterance":
        return "用户观察话语"
    return {
        "teacher_event_cooccurrence": "教师纠正短句",
        "styled_curriculum_example": "风格语料短句",
        "seed": "种子短句",
    }.get(str(kind), str(kind) or "短句")


def _phrase_title(phrase_id: str, text: str, phrase_kind: str) -> str:
    if str(phrase_id).startswith("user_utterance::"):
        return f"用户话语「{text}」"
    if str(phrase_id).startswith("style::"):
        return f"风格短句「{text}」"
    if str(phrase_id).startswith("teacher_phrase::"):
        return f"教师短句「{text}」"
    if phrase_kind:
        return f"{_phrase_kind_label(phrase_kind)}「{text}」"
    return f"表达短句「{text}」"


def _readable_key(
    key: str,
    phrase_text_by_id: Mapping[str, str],
    phrase_kind_by_id: Mapping[str, str],
) -> dict[str, str]:
    key = str(key)
    if key in phrase_text_by_id:
        text = phrase_text_by_id[key]
        return {
            "raw": key,
            "title": _phrase_title(key, text, phrase_kind_by_id.get(key, "")),
            "detail": key,
        }
    if key.startswith("style::"):
        text = phrase_text_by_id.get(key, key.removeprefix("style::"))
        return {"raw": key, "title": f"风格短句「{text}」", "detail": key}
    if key.startswith("style_paradigm::"):
        return {"raw": key, "title": f"风格范式 {key.removeprefix('style_paradigm::')}", "detail": key}
    if key.startswith("teacher_phrase::"):
        return {"raw": key, "title": f"教师短句 {key[-8:]}", "detail": key}
    if key.startswith("phase20ctx::"):
        return {"raw": key, "title": f"对话场景 {key[-8:]}", "detail": key}
    if key.startswith("visual_concept::"):
        return {"raw": key, "title": f"视觉概念 {key.removeprefix('visual_concept::')}", "detail": key}
    if key.startswith("visual_object::"):
        return {"raw": key, "title": f"视觉对象 {key[-8:]}", "detail": key}
    return {"raw": key, "title": key, "detail": key}


def _sha16(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]
