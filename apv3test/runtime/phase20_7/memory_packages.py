"""Phase20.7 记忆包 (skill/memory package) — 导出/预览/导入/卸载.

白皮书 §34.3/§39: 记忆包 = 经验流片段的携带形式, 不是技能插件/答案包.
导入 = 把包内 experience_alignment(+其输入事件) 追加进目标库经验流, 走
import_batch/package_membership 登记 (§132 可追溯可卸载); 召回/泛化/竞争
全部走既有 runtime 机制 — 包只带经验, 不带行为.

红线:
- 不导出/导入 counter_evidence 角色的对齐 (纠错史属于原会话的诚实历史,
  不作为可分享技能);
- 不导出 expression_role 对齐以外的表达内部态;
- 卸载 = tombstone 该批次成员事件 (append-only, 不物理删除).
"""
from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from .experience_log import (
    attach_package_membership,
    create_import_batch,
    from_json,
    initialize_phase20_7_store,
    insert_experience_event,
    is_tombstoned,
    to_json,
    tombstone_memory_entry,
    upsert_exact_b0_index,
    _alignment_support_count,
    _support_from_reward_punish,
)

PACKAGE_SCHEMA_ID = "apv3_phase20_7_memory_package/v1"


def preview_package_entries(
    db_path: str | Path,
    *,
    session_id: str | None = None,
    keyword: str = "",
    since_ms: int = 0,
    until_ms: int = 0,
    limit: int = 200,
    offset: int = 0,
) -> dict[str, Any]:
    """筛选可分享的记忆/范式条目 (供前端勾选). 只列 reward>punish 的教学对齐."""
    path = initialize_phase20_7_store(db_path)
    clauses = ["event_kind='experience_alignment'", "reward>=punish"]
    params: list[Any] = []
    if session_id:
        clauses.append("session_id=?")
        params.append(str(session_id))
    if since_ms > 0:
        clauses.append("created_at_ms>=?")
        params.append(int(since_ms))
    if until_ms > 0:
        clauses.append("created_at_ms<=?")
        params.append(int(until_ms))
    where = " AND ".join(clauses)
    items: list[dict[str, Any]] = []
    total = 0
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            f"SELECT event_id, session_id, payload_json, reward, punish, created_at_ms "
            f"FROM phase20_7_experience_events WHERE {where} "
            f"ORDER BY created_at_ms DESC",
            tuple(params),
        ).fetchall()
        for event_id, sid, payload_json, reward, punish, created_at_ms in rows:
            if is_tombstoned(conn, object_kind="event", object_ref=str(event_id)):
                continue
            payload = from_json(str(payload_json))
            if not isinstance(payload, dict):
                continue
            if str(payload.get("alignment_role") or "") == "counter_evidence":
                continue
            output_text = "".join(str(ch) for ch in payload.get("output_chars", ()))
            input_payload = _input_payload(conn, payload)
            input_text = str(input_payload.get("text", "") or "")
            if keyword and keyword not in input_text and keyword not in output_text:
                continue
            total += 1
            if total <= offset or len(items) >= limit:
                continue
            items.append(
                {
                    "event_id": str(event_id),
                    "session_id": str(sid),
                    "input_text": input_text,
                    "output_text": output_text,
                    "has_visual": bool(payload.get("visual_signature")),
                    "expression_role": str(payload.get("expression_role") or ""),
                    "reward": float(reward or 0.0),
                    "punish": float(punish or 0.0),
                    "created_at_ms": int(created_at_ms),
                }
            )
    return {
        "schema_id": PACKAGE_SCHEMA_ID,
        "items": items,
        "total": total,
        "offset": int(offset),
        "limit": int(limit),
    }


def export_package(
    db_path: str | Path,
    *,
    event_ids: Sequence[str],
    package_name: str = "memory_package",
) -> dict[str, Any]:
    """按勾选的 alignment event_id 导出包 (含各自的输入观察事件)."""
    path = initialize_phase20_7_store(db_path)
    entries: list[dict[str, Any]] = []
    with sqlite3.connect(path) as conn:
        for event_id in list(dict.fromkeys(str(e) for e in event_ids))[:500]:
            row = conn.execute(
                "SELECT payload_json, reward, punish, tick FROM phase20_7_experience_events "
                "WHERE event_id=? AND event_kind='experience_alignment'",
                (event_id,),
            ).fetchone()
            if row is None or is_tombstoned(conn, object_kind="event", object_ref=event_id):
                continue
            payload = from_json(str(row[0]))
            if not isinstance(payload, dict):
                continue
            if str(payload.get("alignment_role") or "") == "counter_evidence":
                continue
            input_payload = _input_payload(conn, payload)
            entries.append(
                {
                    "alignment_payload": payload,
                    "input_text": str(input_payload.get("text", "") or ""),
                    "reward": float(row[1] or 0.0),
                    "punish": float(row[2] or 0.0),
                    "source_event_id": event_id,
                }
            )
    body = to_json({"entries": entries})
    package = {
        "schema_id": PACKAGE_SCHEMA_ID,
        "package_id": f"pkg_{hashlib.sha256(body.encode('utf-8')).hexdigest()[:16]}",
        "package_name": str(package_name)[:80],
        "exported_at_ms": int(time.time() * 1000),
        "entry_count": len(entries),
        "source_hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "entries": entries,
    }
    return package


def import_package(
    db_path: str | Path,
    package: Mapping[str, Any],
    *,
    session_id: str = "phase20_7_workbench",
) -> dict[str, Any]:
    """把包内经验追加进目标库经验流 (走 import_batch 登记, 可卸载).

    每条 entry 重放为: 输入观察事件 + 教学对齐事件 + exact_b0 索引 (支持度按目标库
    退火公式重算 — 包带来的是经验, 把握感由目标库自己的确认史决定, §173.5).
    """
    path = initialize_phase20_7_store(db_path)
    entries = package.get("entries")
    if not isinstance(entries, Sequence):
        return {"error": "invalid_package_no_entries"}
    package_id = str(package.get("package_id") or f"pkg_{int(time.time())}")
    batch_id = create_import_batch(
        path,
        package_id=package_id,
        package_name=str(package.get("package_name") or "memory_package"),
        source_hash=str(package.get("source_hash") or ""),
        dedup_policy="skip_same_output_hash",
        payload={"entry_count": len(entries), "import_session_id": session_id},
    )
    imported = 0
    skipped = 0
    membership_refs: list[str] = []
    with sqlite3.connect(path) as conn:
        base_tick_row = conn.execute(
            "SELECT COALESCE(MAX(tick),0) FROM phase20_7_experience_events WHERE session_id=?",
            (session_id,),
        ).fetchone()
        tick = int(base_tick_row[0] or 0)
        for entry in entries[:500]:
            if not isinstance(entry, Mapping):
                continue
            payload = entry.get("alignment_payload")
            if not isinstance(payload, Mapping):
                continue
            payload = dict(payload)
            if str(payload.get("alignment_role") or "") == "counter_evidence":
                skipped += 1
                continue
            output_hash = str(payload.get("output_hash") or "")
            input_signature = str(payload.get("input_signature") or "")
            if input_signature and output_hash:
                dup = conn.execute(
                    "SELECT COUNT(*) FROM phase20_7_experience_events "
                    "WHERE event_kind='experience_alignment' AND session_id=? "
                    "AND json_extract(payload_json,'$.input_signature')=? "
                    "AND json_extract(payload_json,'$.output_hash')=?",
                    (session_id, input_signature, output_hash),
                ).fetchone()
                if dup and int(dup[0]) > 0:
                    skipped += 1
                    continue
            tick += 1
            input_text = str(entry.get("input_text") or "")
            input_event_id = None
            if input_text:
                input_event_id = insert_experience_event(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    event_kind="text_receptor_observation",
                    payload={
                        "text": input_text,
                        "text_hash": _hash_text(input_text),
                        "char_count": len(input_text),
                        "structure_signature": input_signature,
                        "text_signature": str(payload.get("text_signature") or ""),
                        "visual_signature": payload.get("visual_signature"),
                        "structure_kind": "linear_text",
                        "imported_from_package": package_id,
                    },
                )
                payload["input_event_id"] = input_event_id
            reward = max(0.0, float(entry.get("reward", 1.0) or 0.0))
            punish = max(0.0, float(entry.get("punish", 0.0) or 0.0))
            payload["imported_from_package"] = package_id
            tick += 1
            alignment_event_id = insert_experience_event(
                conn,
                session_id=session_id,
                tick=tick,
                event_kind="experience_alignment",
                payload=payload,
                reward=reward,
                punish=punish,
            )
            output_chars = tuple(str(ch) for ch in payload.get("output_chars", ()))
            if input_signature and output_chars and reward >= punish and not payload.get("expression_role"):
                sc = _alignment_support_count(conn, input_signature=input_signature)
                upsert_exact_b0_index(
                    conn,
                    input_signature=input_signature,
                    alignment_event_id=alignment_event_id,
                    input_event_id=input_event_id or alignment_event_id,
                    output_chars=output_chars,
                    support=_support_from_reward_punish(reward, punish, support_count=sc),
                )
            # 成员登记推迟到连接关闭后 (attach_package_membership 自开连接, 嵌套会锁库)
            for ref in (alignment_event_id, input_event_id):
                if ref:
                    membership_refs.append(str(ref))
            imported += 1
        conn.commit()
    for ref in membership_refs:
        attach_package_membership(
            path,
            import_batch_id=batch_id,
            object_kind="event",
            object_ref=ref,
            was_new=True,
            event_id=ref,
        )
    return {
        "schema_id": PACKAGE_SCHEMA_ID,
        "import_batch_id": batch_id,
        "package_id": package_id,
        "imported": imported,
        "skipped_duplicates_or_counter": skipped,
        "session_id": session_id,
    }


def list_import_batches(db_path: str | Path) -> list[dict[str, Any]]:
    path = initialize_phase20_7_store(db_path)
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT import_batch_id, package_id, package_name, imported_at_ms, payload_json "
            "FROM phase20_7_import_batches ORDER BY imported_at_ms DESC LIMIT 50"
        ).fetchall()
        out = []
        for batch_id, package_id, package_name, imported_at_ms, payload_json in rows:
            member_count = conn.execute(
                "SELECT COUNT(*) FROM phase20_7_package_memberships WHERE import_batch_id=?",
                (batch_id,),
            ).fetchone()[0]
            out.append(
                {
                    "import_batch_id": str(batch_id),
                    "package_id": str(package_id),
                    "package_name": str(package_name),
                    "imported_at_ms": int(imported_at_ms),
                    "member_count": int(member_count),
                }
            )
        return out


def uninstall_import_batch(db_path: str | Path, *, import_batch_id: str) -> dict[str, Any]:
    """卸载 = tombstone 批次内全部成员事件 (append-only, 召回即刻失效)."""
    path = initialize_phase20_7_store(db_path)
    removed = 0
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT object_ref FROM phase20_7_package_memberships WHERE import_batch_id=?",
            (str(import_batch_id),),
        ).fetchall()
    for (object_ref,) in rows:
        tombstone_memory_entry(
            path,
            memory_entry_id=str(object_ref),
            reason=f"package_uninstall::{import_batch_id}",
        )
        removed += 1
    return {"import_batch_id": str(import_batch_id), "tombstoned": removed}


def _input_payload(conn: sqlite3.Connection, alignment_payload: Mapping[str, Any]) -> dict[str, Any]:
    input_event_id = str(alignment_payload.get("input_event_id") or "")
    if not input_event_id:
        return {}
    row = conn.execute(
        "SELECT payload_json FROM phase20_7_experience_events WHERE event_id=?",
        (input_event_id,),
    ).fetchone()
    if row is None:
        return {}
    payload = from_json(str(row[0]))
    return payload if isinstance(payload, dict) else {}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
