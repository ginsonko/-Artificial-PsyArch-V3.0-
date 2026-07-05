from __future__ import annotations

import json
import math
import struct
from pathlib import Path
import sqlite3
import time
import uuid
from typing import Any, Iterable, Mapping, Sequence

from .models import PHASE20_7_SCHEMA_SQL, REQUIRED_PHASE20_7_TABLES


def initialize_phase20_7_store(db_path: str | Path) -> Path:
    """Create the Stage 0 SQLite boundary schema.

    The schema is an empty AP-native truth-source boundary. Stage 1 will begin
    writing minimal ExperienceEvent rows; Stage 0 only proves that the isolated
    store and provenance tables exist.
    """

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        # §185/§42 性能: WAL 允许读写并发 (前端轮询 memory/unclosed 与 turn 写并存),
        # NORMAL 同步在 WAL 下足够安全 (进程崩溃不丢已提交事务, 只可能丢最后一个
        # checkpoint 后的 WAL 尾部 — 经验流可接受). 均为持久 PRAGMA/连接级安全默认.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        for statement in PHASE20_7_SCHEMA_SQL:
            conn.execute(statement)
        conn.commit()
    return path


def phase20_7_table_names(db_path: str | Path) -> tuple[str, ...]:
    path = Path(db_path)
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'phase20_7_%' ORDER BY name"
        ).fetchall()
    return tuple(str(row[0]) for row in rows)


def phase20_7_schema_status(db_path: str | Path) -> dict[str, object]:
    tables = set(phase20_7_table_names(db_path))
    required = set(REQUIRED_PHASE20_7_TABLES)
    missing = tuple(sorted(required - tables))
    return {
        "schema_id": "apv3_phase20_7_sqlite_boundary/v1",
        "ready": not missing,
        "table_count": len(tables),
        "required_table_count": len(required),
        "missing_tables": list(missing),
        "truth_source": "phase20_7_experience_events",
        "derived_snapshots_are_rebuildable": True,
    }


def now_ms() -> int:
    return int(time.time() * 1000)


def new_ref(prefix: str) -> str:
    return f"{prefix}::{uuid.uuid4().hex}"


def to_json(payload: Mapping[str, Any] | Iterable[Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def from_json(raw: str) -> Any:
    return json.loads(raw)


def insert_source_packet(
    conn: sqlite3.Connection,
    *,
    source_kind: str,
    source_ref: str | None,
    source_context: str,
    modality: str,
    trust_snapshot: float,
    tick: int,
    payload: Mapping[str, Any],
) -> str:
    source_packet_id = new_ref("srcpkt")
    conn.execute(
        """
        INSERT INTO phase20_7_source_packets(
          source_packet_id, source_kind, source_ref, source_context, modality,
          trust_snapshot, created_tick, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_packet_id,
            source_kind,
            source_ref,
            source_context,
            modality,
            float(trust_snapshot),
            int(tick),
            to_json(payload),
        ),
    )
    return source_packet_id


def insert_action_record(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    tick: int,
    action_type: str,
    selected: bool,
    drive: float,
    eligibility: Mapping[str, Any],
    target_refs: Mapping[str, Any],
    result_event_id: str | None = None,
) -> str:
    action_record_id = new_ref("act")
    conn.execute(
        """
        INSERT INTO phase20_7_action_records(
          action_record_id, session_id, tick, action_type, selected, drive,
          eligibility_json, target_refs_json, result_event_id, created_at_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            action_record_id,
            session_id,
            int(tick),
            action_type,
            1 if selected else 0,
            float(drive),
            to_json(eligibility),
            to_json(target_refs),
            result_event_id,
            now_ms(),
        ),
    )
    return action_record_id


def insert_experience_event(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    tick: int,
    event_kind: str,
    payload: Mapping[str, Any],
    source_packet_id: str | None = None,
    action_record_id: str | None = None,
    reward: float = 0.0,
    punish: float = 0.0,
) -> str:
    event_id = new_ref("evt")
    conn.execute(
        """
        INSERT INTO phase20_7_experience_events(
          event_id, session_id, tick, event_kind, source_packet_id, action_record_id,
          payload_json, reward, punish, created_at_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            session_id,
            int(tick),
            event_kind,
            source_packet_id,
            action_record_id,
            to_json(payload),
            float(reward),
            float(punish),
            now_ms(),
        ),
    )
    return event_id


def upsert_sa_type(
    conn: sqlite3.Connection,
    *,
    sa_type_id: str,
    substrate: str,
    modality: str,
    canonical_hint: str,
    tick: int,
) -> None:
    conn.execute(
        """
        INSERT INTO phase20_7_sa_types(
          sa_type_id, substrate, modality, canonical_hint, created_tick, updated_tick
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(sa_type_id) DO UPDATE SET
          canonical_hint=excluded.canonical_hint,
          updated_tick=excluded.updated_tick
        """,
        (sa_type_id, substrate, modality, canonical_hint, int(tick), int(tick)),
    )


# --- L1 online embedding storage (whitepaper §35.3 / §173.3) -----------------
# The vector_l1 BLOB column already exists on phase20_7_sa_types (see models.py).
# These helpers fill that existing column only; they introduce no new table and
# no new cognitive entity. The vector is a learned, receptor-local contrast
# representation derived from prediction error + reward/punish + co-occurrence.
# It is a derived, rebuildable index, never a truth source (§24 / §132).

L1_VECTOR_DIM = 24
L1_VECTOR_INDEX_NAME = "l1_vector_index/v1"


def l1_zero_vector() -> list[float]:
    return [0.0] * L1_VECTOR_DIM


def l1_initial_vector_for(sa_type_id: str) -> list[float]:
    """Deterministic, content-addressed initial L1 vector for a fresh sa_type.

    A learned embedding needs a non-degenerate starting point so that the first
    triplet step has a direction to move in; an all-zero anchor with an all-zero
    reference cannot learn (``positive - anchor == 0``). This derives a unit-norm
    deterministic vector from the sa_type_id hash, so the same sa_type always
    starts from the same point and different sa_types start spread apart. It
    introduces no new cognitive entity: it is only the initialization policy for
    the existing ``vector_l1`` column, and subsequent triplet updates overwrite
    it from prediction error + reward/punish + co-occurrence (whitepaper §173.3).
    """
    import hashlib

    digest = hashlib.sha256(str(sa_type_id).encode("utf-8")).digest()
    vec = [0.0] * L1_VECTOR_DIM
    for i in range(L1_VECTOR_DIM):
        byte = digest[i % len(digest)]
        # Map byte to [-1, 1] with a small magnitude so updates dominate quickly.
        vec[i] = ((byte / 255.0) * 2.0 - 1.0) * 0.15
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 1e-12:
        vec = [v / norm * 0.15 for v in vec]
    return vec


def l1_vector_to_bytes(support_count: int, vector: Sequence[float]) -> bytes:
    """Serialize (support_count, 24-dim float32 vector) into the vector_l1 BLOB."""
    vec = [float(v) for v in vector]
    if len(vec) < L1_VECTOR_DIM:
        vec = vec + [0.0] * (L1_VECTOR_DIM - len(vec))
    elif len(vec) > L1_VECTOR_DIM:
        vec = vec[:L1_VECTOR_DIM]
    return struct.pack("<" + "i" + "f" * L1_VECTOR_DIM, int(support_count), *vec)


def bytes_to_l1_vector(raw: bytes | None) -> tuple[int, list[float]]:
    """Inverse of l1_vector_to_bytes; tolerant of NULL / malformed blobs."""
    if not raw:
        return 0, l1_zero_vector()
    try:
        values = struct.unpack("<" + "i" + "f" * L1_VECTOR_DIM, raw)
    except struct.error:
        return 0, l1_zero_vector()
    return int(values[0]), [float(v) for v in values[1:]]


def update_sa_type_vector_l1(
    conn: sqlite3.Connection,
    *,
    sa_type_id: str,
    support_count: int,
    vector: Sequence[float],
    tick: int,
) -> None:
    """Write the learned L1 vector back to the existing vector_l1 column."""
    conn.execute(
        "UPDATE phase20_7_sa_types SET vector_l1=?, updated_tick=? WHERE sa_type_id=?",
        (l1_vector_to_bytes(support_count, vector), int(tick), sa_type_id),
    )


def load_sa_type_vector_l1(
    conn: sqlite3.Connection,
    sa_type_ids: Sequence[str],
) -> dict[str, tuple[int, list[float]]]:
    """Read (support_count, vector) for the requested sa_types.

    A sa_type that has a row but a NULL/zero vector_l1 (never triplet-updated)
    is given its deterministic content-addressed initial vector, so the first
    triplet step has a non-degenerate reference to move toward. A sa_type with no
    row at all also falls back to the initial vector with support_count 0. This
    keeps the learned signal directional from the first teaching event without
    introducing a new entity: it is only the initialization policy for the
    existing vector_l1 column.
    """
    ids = tuple(str(sid) for sid in sa_type_ids if sid)
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT sa_type_id, vector_l1 FROM phase20_7_sa_types WHERE sa_type_id IN ({placeholders})",
        ids,
    ).fetchall()
    loaded = {str(sid): bytes_to_l1_vector(raw) for sid, raw in rows}
    result: dict[str, tuple[int, list[float]]] = {}
    for sid in ids:
        if sid in loaded:
            count, vec = loaded[sid]
            if not any(abs(v) > 1e-9 for v in vec):
                vec = l1_initial_vector_for(sid)
            result[sid] = (count, vec)
        else:
            result[sid] = (0, l1_initial_vector_for(sid))
    return result


def l1_centroid(vectors: Sequence[Sequence[float]]) -> list[float]:
    """Elementwise mean of a set of L1 vectors; empty -> zero vector."""
    vecs = [list(v) for v in vectors if v]
    if not vecs:
        return l1_zero_vector()
    centroid = [0.0] * L1_VECTOR_DIM
    for vec in vecs:
        for i in range(min(L1_VECTOR_DIM, len(vec))):
            centroid[i] += float(vec[i])
    count = float(len(vecs))
    return [c / count for c in centroid]


def l1_cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine similarity clamped to [0, 1]; zero-norm side yields 0.0."""
    dot = 0.0
    norm_l = 0.0
    norm_r = 0.0
    for i in range(L1_VECTOR_DIM):
        a = float(left[i]) if i < len(left) else 0.0
        b = float(right[i]) if i < len(right) else 0.0
        dot += a * b
        norm_l += a * a
        norm_r += b * b
    if norm_l <= 1e-12 or norm_r <= 1e-12:
        return 0.0
    sim = dot / (math.sqrt(norm_l) * math.sqrt(norm_r))
    return max(0.0, min(1.0, sim))


def l1_triplet_update_vector(
    anchor_vector: Sequence[float],
    *,
    positive_centroid: Sequence[float],
    negative_centroid: Sequence[float] | None,
    prediction_error: float,
    reward: float,
    punish: float,
    support_count: int,
) -> tuple[list[float], int]:
    """One directional triplet step (whitepaper §13.3 / §33.1 / §173.3 / §173.5).

    The anchor is the *updated object* (the taught/predicted char sa_type, which
    carries the prediction error P=R−V); the positive centroid is the *reference*
    context (the co-occurring input chars); an optional negative centroid is a
    co-active non-target used for token contrast. Learning is asymmetric: the
    context is the reference, not co-updated. ``lr`` anneals as
    ``lr_min + (lr_max-lr_min)*exp(-support_count/tau)`` with surprise/teacher/
    reward boosts. Reward/closure pulls the anchor toward the context; a
    punish-dominant signal pushes it away. Returns (new_vector, new_support_count).
    """
    lr_max, lr_min, tau = 0.08, 0.008, 120.0
    lr = lr_min + (lr_max - lr_min) * math.exp(-max(0, int(support_count)) / tau)
    pe = max(0.0, min(1.0, float(prediction_error)))
    boost = 1.0 + 0.6 * pe + 0.3 * max(0.0, min(1.0, float(reward)))
    lr *= boost
    sign = 1.0 if float(reward) >= float(punish) else -1.0
    anchor = list(anchor_vector)
    if len(anchor) < L1_VECTOR_DIM:
        anchor = anchor + [0.0] * (L1_VECTOR_DIM - len(anchor))
    positive = list(positive_centroid)
    if len(positive) < L1_VECTOR_DIM:
        positive = positive + [0.0] * (L1_VECTOR_DIM - len(positive))
    new_vec = [0.0] * L1_VECTOR_DIM
    for i in range(L1_VECTOR_DIM):
        value = anchor[i] + lr * sign * (positive[i] - anchor[i])
        if negative_centroid is not None and i < len(negative_centroid):
            value -= lr * sign * 0.5 * (float(negative_centroid[i]) - anchor[i])
        new_vec[i] = max(-1.0, min(1.0, value))
    return new_vec, int(support_count) + 1


# --- L2 temporal/edge online embedding storage (whitepaper §35.3 / §173.3) ----
# Same shape as L1: the vector_l2 BLOB column already exists on phase20_7_sa_types
# (see models.py). These helpers fill that existing column only; no new table, no
# new cognitive entity. L2 differs from L1 in WHAT is embedded: not a single
# receptor-local sa_type, but a *type-pair + relation* edge (whitepaper §173.2
# "L2 顺序/空间/因果, 帮 C_forward/C_backward"; §173.3 "对边 e=(a relation b),
# z_relation_context = compose(z_a, relation_type, z_b), 顺序非对称").
#
# Layering vs SSP (§10): SSP is the explicit per-tick structure graph (occurrence
# edges with exact relation_type). L2 is the *learned soft-similarity* layer over
# type-pair edges, so a new (a->b) whose tokens are similar-but-not-identical to a
# historical edge can still recall that successor by cosine. §35.4 red line 1:
# "在线嵌入不替代白箱显式通道" — SSP occurrence edges stay; L2 only adds a
# learned vector on the type-pair key. The vector is a derived, rebuildable index,
# never a truth source (§24 / §132).

L2_VECTOR_DIM = 24
L2_VECTOR_INDEX_NAME = "l2_vector_index/v1"
L2_RELATION_LINEAR_NEXT = "linear_next"
L2_RELATION_FEEDBACK_LINEAR_NEXT = "feedback_linear_next"


def l2_zero_vector() -> list[float]:
    return [0.0] * L2_VECTOR_DIM


def l2_relation_code(relation_type: str) -> list[float]:
    """Deterministic, content-addressed relation encoding (one L2_VECTOR_DIM block).

    Mirrors l1_initial_vector_for: a unit-norm deterministic vector of magnitude
    0.15 derived from the relation_type hash, so different relations start spread
    apart and compose() can keep z_next(a->b) != z_next(b->a). This is an
    initialization/encoding policy, not a new entity.
    """
    import hashlib

    digest = hashlib.sha256(str(relation_type).encode("utf-8")).digest()
    vec = [0.0] * L2_VECTOR_DIM
    for i in range(L2_VECTOR_DIM):
        byte = digest[i % len(digest)]
        vec[i] = ((byte / 255.0) * 2.0 - 1.0) * 0.15
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 1e-12:
        vec = [v / norm * 0.15 for v in vec]
    return vec


def l2_edge_sa_type_id(relation_type: str, src_sa_type_id: str, dst_sa_type_id: str) -> str:
    """Type-pair + relation key for an L2 edge vector (whitepaper §173.3 e=(a relation b)).

    Order is significant: (a->b) and (b->a) yield different keys, so the asymmetry
    z_next(a->b) != z_next(b->a) is preserved at the storage key level (§173.3).
    """
    return f"text_edge::{relation_type}::{_hash_text(src_sa_type_id)}->{_hash_text(dst_sa_type_id)}"


def l2_initial_vector_for(edge_sa_type_id: str) -> list[float]:
    """Deterministic, content-addressed initial L2 vector for a fresh type-pair edge.

    Same policy as l1_initial_vector_for: a non-degenerate starting point so the
    first structure update has a direction; subsequent updates overwrite it. It is
    only the initialization policy for the existing vector_l2 column.
    """
    import hashlib

    digest = hashlib.sha256(str(edge_sa_type_id).encode("utf-8")).digest()
    vec = [0.0] * L2_VECTOR_DIM
    for i in range(L2_VECTOR_DIM):
        byte = digest[i % len(digest)]
        vec[i] = ((byte / 255.0) * 2.0 - 1.0) * 0.15
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 1e-12:
        vec = [v / norm * 0.15 for v in vec]
    return vec


def l2_vector_to_bytes(support_count: int, vector: Sequence[float]) -> bytes:
    """Serialize (support_count, 24-dim float32 vector) into the vector_l2 BLOB."""
    vec = [float(v) for v in vector]
    if len(vec) < L2_VECTOR_DIM:
        vec = vec + [0.0] * (L2_VECTOR_DIM - len(vec))
    elif len(vec) > L2_VECTOR_DIM:
        vec = vec[:L2_VECTOR_DIM]
    return struct.pack("<" + "i" + "f" * L2_VECTOR_DIM, int(support_count), *vec)


def bytes_to_l2_vector(raw: bytes | None) -> tuple[int, list[float]]:
    """Inverse of l2_vector_to_bytes; tolerant of NULL / malformed blobs."""
    if not raw:
        return 0, l2_zero_vector()
    try:
        values = struct.unpack("<" + "i" + "f" * L2_VECTOR_DIM, raw)
    except struct.error:
        return 0, l2_zero_vector()
    return int(values[0]), [float(v) for v in values[1:]]


def update_sa_type_vector_l2(
    conn: sqlite3.Connection,
    *,
    sa_type_id: str,
    support_count: int,
    vector: Sequence[float],
    tick: int,
) -> None:
    """Write the learned L2 edge vector back to the existing vector_l2 column."""
    conn.execute(
        "UPDATE phase20_7_sa_types SET vector_l2=?, updated_tick=? WHERE sa_type_id=?",
        (l2_vector_to_bytes(support_count, vector), int(tick), sa_type_id),
    )


def load_sa_type_vector_l2(
    conn: sqlite3.Connection,
    sa_type_ids: Sequence[str],
) -> dict[str, tuple[int, list[float]]]:
    """Read (support_count, vector) for the requested type-pair edge sa_types.

    Same contract as load_sa_type_vector_l1: every non-empty requested sid gets an
    entry; NULL/zero/missing rows fall back to the deterministic initial vector so
    the first structure update has a non-degenerate reference.
    """
    ids = tuple(str(sid) for sid in sa_type_ids if sid)
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT sa_type_id, vector_l2 FROM phase20_7_sa_types WHERE sa_type_id IN ({placeholders})",
        ids,
    ).fetchall()
    loaded = {str(sid): bytes_to_l2_vector(raw) for sid, raw in rows}
    result: dict[str, tuple[int, list[float]]] = {}
    for sid in ids:
        if sid in loaded:
            count, vec = loaded[sid]
            if not any(abs(v) > 1e-9 for v in vec):
                vec = l2_initial_vector_for(sid)
            result[sid] = (count, vec)
        else:
            result[sid] = (0, l2_initial_vector_for(sid))
    return result


def l2_compose(
    src_vector: Sequence[float],
    relation_type: str,
    dst_vector: Sequence[float],
) -> list[float]:
    """compose(z_a, relation_type, z_b) -> 24-dim edge relation context (§173.3).

    Order-asymmetric by construction: the first half carries src (a), the second
    half carries dst (b), and the relation code is folded in by elementwise mix so
    that compose(a,b) != compose(b,a). This is the §173.3 "顺序非对称" requirement
    realized at the vector level, not just the key level.
    """
    src = [float(v) for v in src_vector]
    dst = [float(v) for v in dst_vector]
    if len(src) < L2_VECTOR_DIM:
        src = src + [0.0] * (L2_VECTOR_DIM - len(src))
    if len(dst) < L2_VECTOR_DIM:
        dst = dst + [0.0] * (L2_VECTOR_DIM - len(dst))
    rel = l2_relation_code(relation_type)
    half = L2_VECTOR_DIM // 2
    out = [0.0] * L2_VECTOR_DIM
    for i in range(half):
        # first half dominated by src, modulated by relation
        out[i] = src[i] * 0.7 + rel[i] * 0.3
    for i in range(half, L2_VECTOR_DIM):
        # second half dominated by dst, modulated by relation
        out[i] = dst[i] * 0.7 + rel[i] * 0.3
    norm = math.sqrt(sum(v * v for v in out))
    if norm > 1e-12:
        out = [v / norm * 0.15 for v in out]
    return out


def l2_cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine similarity clamped to [0, 1]; zero-norm side yields 0.0."""
    dot = 0.0
    norm_l = 0.0
    norm_r = 0.0
    for i in range(L2_VECTOR_DIM):
        a = float(left[i]) if i < len(left) else 0.0
        b = float(right[i]) if i < len(right) else 0.0
        dot += a * b
        norm_l += a * a
        norm_r += b * b
    if norm_l <= 1e-12 or norm_r <= 1e-12:
        return 0.0
    sim = dot / (math.sqrt(norm_l) * math.sqrt(norm_r))
    return max(0.0, min(1.0, sim))


def l2_structure_update_vector(
    edge_vector: Sequence[float],
    *,
    relation_context: Sequence[float],
    structure_support: float,
    support_count: int,
) -> tuple[list[float], int]:
    """One L2 structure update step (whitepaper §173.3).

    z_edge <- z_edge + lr_L2 * structure_support * (z_relation_context - z_edge)
    with annealing lr_t = lr_0 / sqrt(1 + support_count) (§173.5). The edge is the
    updated object; the relation context (compose of the two endpoints + relation)
    is the reference and is not co-updated. No negative term at L2 in this step
    (§173.4 negatives come from unfulfilled prediction / failed action / teacher
    punish later; out of scope for the C_forward-only first cut).
    """
    lr_max, lr_min, tau = 0.08, 0.008, 120.0
    lr = lr_min + (lr_max - lr_min) * math.exp(-max(0, int(support_count)) / tau)
    sup = max(0.0, min(1.0, float(structure_support)))
    lr *= 1.0 + 0.6 * sup
    edge = list(edge_vector)
    if len(edge) < L2_VECTOR_DIM:
        edge = edge + [0.0] * (L2_VECTOR_DIM - len(edge))
    ctx = list(relation_context)
    if len(ctx) < L2_VECTOR_DIM:
        ctx = ctx + [0.0] * (L2_VECTOR_DIM - len(ctx))
    new_vec = [0.0] * L2_VECTOR_DIM
    for i in range(L2_VECTOR_DIM):
        value = edge[i] + lr * sup * (ctx[i] - edge[i])
        new_vec[i] = max(-1.0, min(1.0, value))
    return new_vec, int(support_count) + 1


# --- L3 action-consequence online embedding (whitepaper §35.3 / §173.2 / §173.3) ---
# L3 学"场景-行动-奖惩后果"(§1657), 帮 action competition(§173.2.3). 与 L1/L2 同构:
# 向量存在既有 vector_l3 BLOB 列(models.py), edge sa_type 只是该列的键, 不新增表/列/实体.
# edge = (state_signature, action_type), outcome = reward - punish(§173.3 line 7180).
# 退火 §173.5 lr_t = lr_0/sqrt(1+support_count), 与 L1/L2 同范式.
L3_VECTOR_DIM = 24
L3_VECTOR_INDEX_NAME = "l3_vector_index/v1"
L3_RELATION_ACTION_CONSEQUENCE = "action_consequence"
# L3 只调制这些外向动作的后果(§1657 学场景-行动-奖惩后果). 不含 idle/move_focus 等
# 内部 tick 动作, 避免把"想象火躲开"和"真实火躲开"混成同一行动后果(§1727/§37.3).
# Single source of truth — imported by runtime.py (live trigger + modulation) and
# used by rebuild_phase20_7_indexes (replay) so the two never diverge.
L3_OUTWARD_ACTION_TYPES = frozenset(
    {"write_cell", "request_teacher", "maintain_unclosed", "integrate_feedback", "commit_reply"}
)


def l3_zero_vector() -> list[float]:
    return [0.0] * L3_VECTOR_DIM


def l3_action_context_code(state_signature: str, action_type: str) -> list[float]:
    """Deterministic, content-addressed encoding of a (state, action) success anchor.

    Mirrors l2_relation_code / l2_initial_vector_for: a unit-norm deterministic
    vector of magnitude 0.15 derived from the (state_signature, action_type) hash.
    This is the "success pattern" the L3 edge vector is pulled toward on reward and
    pushed away from on punish (§173.3 direction_to_success_or_failure). It is an
    encoding policy for the existing vector_l3 column, not a new entity.
    """
    import hashlib

    digest = hashlib.sha256(
        f"{state_signature}::{action_type}".encode("utf-8")
    ).digest()
    vec = [0.0] * L3_VECTOR_DIM
    for i in range(L3_VECTOR_DIM):
        byte = digest[i % len(digest)]
        vec[i] = ((byte / 255.0) * 2.0 - 1.0) * 0.15
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 1e-12:
        vec = [v / norm * 0.15 for v in vec]
    return vec


def l3_edge_sa_type_id(state_signature: str, action_type: str) -> str:
    """Key for an L3 (state, action) edge vector (whitepaper §173.3).

    Order-asymmetric by construction: (state, action) is the only meaningful
    direction here (the consequence belongs to that specific state-action pair).
    """
    return f"action_edge::{L3_RELATION_ACTION_CONSEQUENCE}::{_hash_text(state_signature)}::{_hash_text(action_type)}"


def l3_initial_vector_for(edge_sa_type_id: str) -> list[float]:
    """Deterministic, content-addressed initial L3 vector for a fresh (state, action) edge.

    Same policy as l2_initial_vector_for: a non-degenerate starting point so the
    first action-consequence update has a direction. Only the initialization policy
    for the existing vector_l3 column.
    """
    import hashlib

    digest = hashlib.sha256(str(edge_sa_type_id).encode("utf-8")).digest()
    vec = [0.0] * L3_VECTOR_DIM
    for i in range(L3_VECTOR_DIM):
        byte = digest[i % len(digest)]
        vec[i] = ((byte / 255.0) * 2.0 - 1.0) * 0.15
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 1e-12:
        vec = [v / norm * 0.15 for v in vec]
    return vec


def l3_vector_to_bytes(support_count: int, vector: Sequence[float]) -> bytes:
    """Serialize (support_count, 24-dim float32 vector) into the vector_l3 BLOB."""
    vec = [float(v) for v in vector]
    if len(vec) < L3_VECTOR_DIM:
        vec = vec + [0.0] * (L3_VECTOR_DIM - len(vec))
    elif len(vec) > L3_VECTOR_DIM:
        vec = vec[:L3_VECTOR_DIM]
    return struct.pack("<" + "i" + "f" * L3_VECTOR_DIM, int(support_count), *vec)


def bytes_to_l3_vector(raw: object) -> tuple[int, list[float]]:
    """Deserialize the vector_l3 BLOB into (support_count, 24-dim float vector).

    NULL / short / malformed blobs fall back to (0, zero vector); callers replace
    the zero vector with l3_initial_vector_for when a deterministic start is needed.
    """
    if not raw:
        return 0, [0.0] * L3_VECTOR_DIM
    blob = bytes(raw)
    expected = struct.calcsize("<" + "i" + "f" * L3_VECTOR_DIM)
    if len(blob) < expected:
        return 0, [0.0] * L3_VECTOR_DIM
    values = struct.unpack("<" + "i" + "f" * L3_VECTOR_DIM, blob[:expected])
    return int(values[0]), [float(v) for v in values[1:]]


def update_sa_type_vector_l3(
    conn: sqlite3.Connection,
    *,
    sa_type_id: str,
    support_count: int,
    vector: Sequence[float],
    tick: int,
) -> None:
    conn.execute(
        "UPDATE phase20_7_sa_types SET vector_l3=?, updated_tick=? WHERE sa_type_id=?",
        (l3_vector_to_bytes(support_count, vector), int(tick), sa_type_id),
    )


def load_sa_type_vector_l3(
    conn: sqlite3.Connection,
    sa_type_ids: Sequence[str],
) -> dict[str, tuple[int, list[float]]]:
    """Read (support_count, vector) for the requested (state, action) edge sa_types.

    Same contract as load_sa_type_vector_l1/l2: every non-empty requested sid gets an
    entry; NULL/zero/missing rows fall back to the deterministic initial vector so
    the first action-consequence update has a non-degenerate reference.
    """
    ids = tuple(str(sid) for sid in sa_type_ids if sid)
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT sa_type_id, vector_l3 FROM phase20_7_sa_types WHERE sa_type_id IN ({placeholders})",
        ids,
    ).fetchall()
    loaded = {str(sid): bytes_to_l3_vector(raw) for sid, raw in rows}
    result: dict[str, tuple[int, list[float]]] = {}
    for sid in ids:
        if sid in loaded:
            count, vec = loaded[sid]
            if not any(abs(v) > 1e-9 for v in vec):
                vec = l3_initial_vector_for(sid)
            result[sid] = (count, vec)
        else:
            result[sid] = (0, l3_initial_vector_for(sid))
    return result


def l3_cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine similarity clamped to [0, 1]; zero-norm side yields 0.0."""
    dot = 0.0
    norm_l = 0.0
    norm_r = 0.0
    for i in range(L3_VECTOR_DIM):
        a = float(left[i]) if i < len(left) else 0.0
        b = float(right[i]) if i < len(right) else 0.0
        dot += a * b
        norm_l += a * a
        norm_r += b * b
    if norm_l <= 1e-12 or norm_r <= 1e-12:
        return 0.0
    sim = dot / (math.sqrt(norm_l) * math.sqrt(norm_r))
    return max(0.0, min(1.0, sim))


def l3_action_consequence_update_vector(
    edge_vector: Sequence[float],
    *,
    action_context: Sequence[float],
    outcome_value: float,
    support_count: int,
) -> tuple[list[float], int]:
    """One L3 action-consequence update step (whitepaper §173.3 line 7178-7181).

    z_action_context <- z_action_context + lr_L3 * outcome_value * direction
    where direction = (action_context - z_edge) for outcome>0 (pull toward success
    pattern) and the update sign flips for outcome<0 (push away from failure pattern,
    §173.4 "行动了但失败" negative update). lr anneals as
    lr_min + (lr_max-lr_min)*exp(-support_count/tau) (§173.5), same form as L1/L2.
    The action_context (success anchor) is the reference and is not co-updated
    (triplet asymmetry §33.1). Returns (new_vector, new_support_count).
    """
    lr_max, lr_min, tau = 0.08, 0.008, 120.0
    lr = lr_min + (lr_max - lr_min) * math.exp(-max(0, int(support_count)) / tau)
    outcome = max(-1.0, min(1.0, float(outcome_value)))
    lr *= 1.0 + 0.6 * abs(outcome)
    edge = list(edge_vector)
    if len(edge) < L3_VECTOR_DIM:
        edge = edge + [0.0] * (L3_VECTOR_DIM - len(edge))
    ctx = list(action_context)
    if len(ctx) < L3_VECTOR_DIM:
        ctx = ctx + [0.0] * (L3_VECTOR_DIM - len(ctx))
    new_vec = [0.0] * L3_VECTOR_DIM
    for i in range(L3_VECTOR_DIM):
        # outcome>0: z_edge += lr*(ctx - z_edge) (toward success)
        # outcome<0: z_edge += lr*outcome*(ctx - z_edge) = z_edge - lr*|outcome|*(ctx-z_edge) (away)
        value = edge[i] + lr * outcome * (ctx[i] - edge[i])
        new_vec[i] = max(-1.0, min(1.0, value))
    return new_vec, int(support_count) + 1


def insert_occurrence(
    conn: sqlite3.Connection,
    *,
    event_id: str,
    sa_type_id: str,
    tick: int,
    substrate: str,
    position: Mapping[str, Any],
    r: float,
    v: float,
    a: float,
    p: float,
    clarity: float,
    source_ref: str | None = None,
    payload_ref: str | None = None,
) -> str:
    occurrence_id = new_ref("occ")
    conn.execute(
        """
        INSERT INTO phase20_7_occurrences(
          occurrence_id, event_id, sa_type_id, tick, substrate, position_json,
          R, V, A, P, clarity, source_ref, payload_ref
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            occurrence_id,
            event_id,
            sa_type_id,
            int(tick),
            substrate,
            to_json(position),
            float(r),
            float(v),
            float(a),
            float(p),
            float(clarity),
            source_ref,
            payload_ref,
        ),
    )
    return occurrence_id


def insert_payload_blob(
    conn: sqlite3.Connection,
    *,
    payload_kind: str,
    media_type: str,
    blob_bytes: bytes | None,
    summary: Mapping[str, Any],
    source_hash: str,
    tick: int,
) -> str:
    payload_ref = new_ref("payload")
    conn.execute(
        """
        INSERT INTO phase20_7_payload_blobs(
          payload_ref, payload_kind, media_type, bytes, summary_json, source_hash, created_tick
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload_ref,
            payload_kind,
            media_type,
            blob_bytes,
            to_json(summary),
            source_hash,
            int(tick),
        ),
    )
    return payload_ref


def insert_structure_edge(
    conn: sqlite3.Connection,
    *,
    src_occurrence_id: str,
    dst_occurrence_id: str,
    edge_type: str,
    weight: float,
    learned_weight: float,
    tick: int,
) -> str:
    edge_id = new_ref("edge")
    conn.execute(
        """
        INSERT INTO phase20_7_structure_edges(
          edge_id, src_occurrence_id, dst_occurrence_id, edge_type, weight,
          learned_weight, created_tick, updated_tick
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            edge_id,
            src_occurrence_id,
            dst_occurrence_id,
            edge_type,
            float(weight),
            float(learned_weight),
            int(tick),
            int(tick),
        ),
    )
    return edge_id


def upsert_exact_b0_index(
    conn: sqlite3.Connection,
    *,
    input_signature: str,
    alignment_event_id: str,
    input_event_id: str | None,
    output_chars: Iterable[str],
    support: float,
) -> None:
    output = [str(ch) for ch in output_chars]
    output_hash = _hash_text("".join(output))
    conn.execute(
        """
        INSERT INTO phase20_7_exact_b0_index(
          input_signature, alignment_event_id, input_event_id, output_hash,
          output_json, support, updated_at_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(input_signature, alignment_event_id) DO UPDATE SET
          input_event_id=excluded.input_event_id,
          output_hash=excluded.output_hash,
          output_json=excluded.output_json,
          support=excluded.support,
          updated_at_ms=excluded.updated_at_ms
        """,
        (
            input_signature,
            alignment_event_id,
            input_event_id,
            output_hash,
            to_json(output),
            float(support),
            now_ms(),
        ),
    )


def rebuild_phase20_7_indexes(db_path: str | Path) -> dict[str, object]:
    """Rebuild derived indexes from the unified experience event source."""

    path = initialize_phase20_7_store(db_path)
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM phase20_7_exact_b0_index")
        rows = conn.execute(
            """
            SELECT event_id, payload_json, reward, punish
            FROM phase20_7_experience_events
            WHERE event_kind='experience_alignment'
            ORDER BY created_at_ms ASC
            """
        ).fetchall()
        indexed = 0
        # support_count 按 input_signature 累计确认次数(§173.5 退火输入). rebuild 按
        # created_at 升序遍历, 故此处维护一个运行计数器, 模拟运行时按时间序累计的确认数,
        # 与 _alignment_support_count 在运行时点的查询结果一致(同一 input_signature 下
        # 截至当前事件、reward>0 的累计数).
        rebuild_support_counts: dict[str, int] = {}
        for event_id, payload_json, reward, punish in rows:
            if is_tombstoned(conn, object_kind="event", object_ref=str(event_id)):
                continue
            payload = from_json(str(payload_json))
            # §2363/E4/C21: counter_evidence(惩罚主导反馈)不是答案, rebuild 时同样
            # 不进 exact_b0_index — 与运行时 _record_teacher_feedback 的门一致.
            if str(payload.get("alignment_role") or "") == "counter_evidence":
                continue
            input_signature = payload.get("input_signature")
            output_chars = payload.get("output_chars") or []
            if not input_signature or not output_chars:
                continue
            sig_key = str(input_signature)
            sc = rebuild_support_counts.get(sig_key, 0)
            support = _support_from_reward_punish(float(reward), float(punish), support_count=sc)
            upsert_exact_b0_index(
                conn,
                input_signature=sig_key,
                alignment_event_id=str(event_id),
                input_event_id=payload.get("input_event_id"),
                output_chars=output_chars,
                support=support,
            )
            if float(reward) > 0.0:
                rebuild_support_counts[sig_key] = sc + 1
            indexed += 1
        highwater = int(conn.execute("SELECT COUNT(*) FROM phase20_7_experience_events").fetchone()[0])
        conn.execute(
            """
            INSERT INTO phase20_7_index_registry(
              index_name, source_event_highwater, rebuildable, config_json, updated_at_ms
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(index_name) DO UPDATE SET
              source_event_highwater=excluded.source_event_highwater,
              rebuildable=excluded.rebuildable,
              config_json=excluded.config_json,
              updated_at_ms=excluded.updated_at_ms
            """,
            (
                "exact_b0_index/v1",
                highwater,
                1,
                to_json({"truth_source": "phase20_7_experience_events", "indexed_rows": indexed}),
                now_ms(),
            ),
        )
        # ---- L1 online embedding replay: re-derive vector_l1 from the truth ----
        # source (experience_alignment events). Wipe first, then replay triplets
        # in created_at order. Without a live StatePool the rebuild uses a
        # prediction-error proxy (a teaching event implies prediction error),
        # mirroring how the exact_b0 rebuild uses _support_from_reward_punish as a
        # proxy for the online observation-biased support.
        conn.execute("UPDATE phase20_7_sa_types SET vector_l1=NULL WHERE substrate='text'")
        l1_indexed = 0
        for event_id, payload_json, reward, punish in rows:
            if is_tombstoned(conn, object_kind="event", object_ref=str(event_id)):
                continue
            payload = from_json(str(payload_json))
            output_chars = payload.get("output_chars") or []
            if not output_chars:
                continue
            input_payload = _event_payload(conn, payload.get("input_event_id"))
            input_text = str(input_payload.get("text", "") or "")
            input_chars = [ch for ch in input_text if not ch.isspace()]
            input_sa_ids = [f"text_unit::{_hash_text(ch)}" for ch in input_chars]
            output_sa_ids = list(dict.fromkeys(f"text_unit::{_hash_text(str(ch))}" for ch in output_chars))
            input_loaded = load_sa_type_vector_l1(conn, input_sa_ids)
            positive_centroid = l1_centroid([input_loaded[sid][1] for sid in input_sa_ids])
            reward_value = float(reward)
            punish_value = float(punish)
            prediction_error = min(1.0, 0.5 + reward_value * 0.3 + punish_value * 0.3)
            output_loaded = load_sa_type_vector_l1(conn, output_sa_ids)
            for sid in output_sa_ids:
                support_count, vec = output_loaded[sid]
                new_vec, new_count = l1_triplet_update_vector(
                    vec,
                    positive_centroid=positive_centroid,
                    negative_centroid=None,
                    prediction_error=prediction_error,
                    reward=reward_value,
                    punish=punish_value,
                    support_count=support_count,
                )
                update_sa_type_vector_l1(
                    conn, sa_type_id=sid, support_count=new_count, vector=new_vec, tick=0,
                )
                l1_indexed += 1
        conn.execute(
            """
            INSERT INTO phase20_7_index_registry(
              index_name, source_event_highwater, rebuildable, config_json, updated_at_ms
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(index_name) DO UPDATE SET
              source_event_highwater=excluded.source_event_highwater,
              rebuildable=excluded.rebuildable,
              config_json=excluded.config_json,
              updated_at_ms=excluded.updated_at_ms
            """,
            (
                L1_VECTOR_INDEX_NAME,
                highwater,
                1,
                to_json(
                    {
                        "truth_source": "phase20_7_experience_events",
                        "indexed_rows": l1_indexed,
                        "vector_dim": L1_VECTOR_DIM,
                    }
                ),
                now_ms(),
            ),
        )
        # ---- L2 online embedding replay: re-derive vector_l2 (type-pair edge
        # vectors) from the truth source. Runs AFTER L1 replay so the endpoint
        # L1 vectors are already reconstructed; L2 composes those endpoints.
        # Wipe first, then replay structure updates in created_at order. For each
        # taught output sequence, form linear_next type-pair edges between adjacent
        # chars and update each edge's z_edge toward compose(z_a, rel, z_b).
        conn.execute("UPDATE phase20_7_sa_types SET vector_l2=NULL WHERE substrate='text_edge'")
        l2_indexed = 0
        for event_id, payload_json, reward, punish in rows:
            if is_tombstoned(conn, object_kind="event", object_ref=str(event_id)):
                continue
            payload = from_json(str(payload_json))
            output_chars = payload.get("output_chars") or []
            if len(output_chars) < 2:
                continue
            reward_value = float(reward)
            punish_value = float(punish)
            structure_support = min(1.0, 0.5 + reward_value * 0.3 + punish_value * 0.3)
            prev_sa_id = f"text_unit::{_hash_text(str(output_chars[0]))}"
            for ch in output_chars[1:]:
                dst_sa_id = f"text_unit::{_hash_text(str(ch))}"
                edge_sa_id = l2_edge_sa_type_id(L2_RELATION_LINEAR_NEXT, prev_sa_id, dst_sa_id)
                upsert_sa_type(
                    conn,
                    sa_type_id=edge_sa_id,
                    substrate="text_edge",
                    modality="structure",
                    canonical_hint=f"{prev_sa_id} -> {dst_sa_id}",
                    tick=0,
                )
                endpoint_loaded = load_sa_type_vector_l1(conn, (prev_sa_id, dst_sa_id))
                relation_context = l2_compose(
                    endpoint_loaded[prev_sa_id][1],
                    L2_RELATION_LINEAR_NEXT,
                    endpoint_loaded[dst_sa_id][1],
                )
                edge_loaded = load_sa_type_vector_l2(conn, (edge_sa_id,))
                support_count, edge_vec = edge_loaded[edge_sa_id]
                new_vec, new_count = l2_structure_update_vector(
                    edge_vec,
                    relation_context=relation_context,
                    structure_support=structure_support,
                    support_count=support_count,
                )
                update_sa_type_vector_l2(
                    conn, sa_type_id=edge_sa_id, support_count=new_count, vector=new_vec, tick=0,
                )
                l2_indexed += 1
                prev_sa_id = dst_sa_id
        conn.execute(
            """
            INSERT INTO phase20_7_index_registry(
              index_name, source_event_highwater, rebuildable, config_json, updated_at_ms
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(index_name) DO UPDATE SET
              source_event_highwater=excluded.source_event_highwater,
              rebuildable=excluded.rebuildable,
              config_json=excluded.config_json,
              updated_at_ms=excluded.updated_at_ms
            """,
            (
                L2_VECTOR_INDEX_NAME,
                highwater,
                1,
                to_json(
                    {
                        "truth_source": "phase20_7_experience_events",
                        "indexed_rows": l2_indexed,
                        "vector_dim": L2_VECTOR_DIM,
                        "relation_types": [L2_RELATION_LINEAR_NEXT],
                    }
                ),
                now_ms(),
            ),
        )
        # ---- L3 action-consequence embedding replay: re-derive vector_l3 from the
        # truth source (action_records + teacher_feedback_event experience_events).
        # §173.3 L3 学场景-行动-奖惩后果. 对每个 teacher_feedback_event, 恢复其
        # state(对应 observation 的 input_signature)+ action(该 session 中 tick<=
        # feedback_tick、selected=1 的最近外向 action_type)+ outcome(reward-punish),
        # 重跑 l3_action_consequence_update_vector. rebuild 无 live output_intent, 用
        # action_records 近似恢复(§132 索引可重建非真相源, 允许近似). Wipe first.
        conn.execute(
            "UPDATE phase20_7_sa_types SET vector_l3=NULL WHERE substrate='action_edge'"
        )
        l3_indexed = 0
        outward_action_types = tuple(L3_OUTWARD_ACTION_TYPES)
        feedback_rows = conn.execute(
            """
            SELECT e.event_id, e.session_id, e.tick, e.payload_json, e.reward, e.punish
            FROM phase20_7_experience_events e
            WHERE e.event_kind='teacher_feedback_event'
            ORDER BY e.created_at_ms ASC
            """
        ).fetchall()
        for fb_event_id, fb_session, fb_tick, fb_payload_json, fb_reward, fb_punish in feedback_rows:
            if is_tombstoned(conn, object_kind="event", object_ref=str(fb_event_id)):
                continue
            fb_payload = from_json(str(fb_payload_json))
            target_event_id = fb_payload.get("target_event_id")
            # state = the observation signature the teacher is responding to
            state_signature = ""
            if target_event_id:
                tgt_row = conn.execute(
                    "SELECT payload_json FROM phase20_7_experience_events WHERE event_id=?",
                    (str(target_event_id),),
                ).fetchone()
                if tgt_row:
                    tgt_payload = from_json(str(tgt_row[0]))
                    # target_event_id points to a text_receptor_observation whose
                    # payload stores observation.signature as "structure_signature"
                    # (== "text_signature" == the "input_signature" that
                    # experience_alignment payloads carry). Try all three so the
                    # rebuild recovers the same state key the live L3 trigger uses
                    # (observation.signature), regardless of which event kind the
                    # target is.
                    state_signature = str(
                        tgt_payload.get("input_signature")
                        or tgt_payload.get("structure_signature")
                        or tgt_payload.get("text_signature")
                        or ""
                    )
            if not state_signature:
                continue
            # action = nearest selected outward action strictly before this feedback
            # tick — matches the live L3 trigger's tick<? (runtime.py), so the
            # rebuild reproduces the same (state, action) edges the live path learns.
            act_row = conn.execute(
                """
                SELECT action_type FROM phase20_7_action_records
                WHERE session_id=? AND selected=1 AND tick<?
                  AND action_type IN (%s)
                ORDER BY tick DESC, created_at_ms DESC LIMIT 1
                """ % ",".join("?" for _ in outward_action_types),
                (str(fb_session), int(fb_tick), *outward_action_types),
            ).fetchone()
            if not act_row:
                continue
            action_type = str(act_row[0])
            outcome_value = float(fb_reward) - float(fb_punish)
            if abs(outcome_value) < 1e-6:
                continue
            edge_sa_id = l3_edge_sa_type_id(state_signature, action_type)
            upsert_sa_type(
                conn,
                sa_type_id=edge_sa_id,
                substrate="action_edge",
                modality="structure",
                canonical_hint=f"{state_signature} :: {action_type}",
                tick=0,
            )
            action_context = l3_action_context_code(state_signature, action_type)
            edge_loaded = load_sa_type_vector_l3(conn, (edge_sa_id,))
            support_count, edge_vec = edge_loaded[edge_sa_id]
            new_vec, new_count = l3_action_consequence_update_vector(
                edge_vec,
                action_context=action_context,
                outcome_value=outcome_value,
                support_count=support_count,
            )
            update_sa_type_vector_l3(
                conn, sa_type_id=edge_sa_id, support_count=new_count, vector=new_vec, tick=0,
            )
            l3_indexed += 1
        conn.execute(
            """
            INSERT INTO phase20_7_index_registry(
              index_name, source_event_highwater, rebuildable, config_json, updated_at_ms
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(index_name) DO UPDATE SET
              source_event_highwater=excluded.source_event_highwater,
              rebuildable=excluded.rebuildable,
              config_json=excluded.config_json,
              updated_at_ms=excluded.updated_at_ms
            """,
            (
                L3_VECTOR_INDEX_NAME,
                highwater,
                1,
                to_json(
                    {
                        "truth_source": "phase20_7_action_records+phase20_7_experience_events",
                        "indexed_rows": l3_indexed,
                        "vector_dim": L3_VECTOR_DIM,
                        "relation_types": [L3_RELATION_ACTION_CONSEQUENCE],
                    }
                ),
                now_ms(),
            ),
        )
        conn.commit()
    return {
        "index_name": "exact_b0_index/v1",
        "indexed_rows": indexed,
        "source_event_highwater": highwater,
        "l1_vector_index": {
            "index_name": L1_VECTOR_INDEX_NAME,
            "indexed_rows": l1_indexed,
            "vector_dim": L1_VECTOR_DIM,
        },
        "l2_vector_index": {
            "index_name": L2_VECTOR_INDEX_NAME,
            "indexed_rows": l2_indexed,
            "vector_dim": L2_VECTOR_DIM,
        },
        "l3_vector_index": {
            "index_name": L3_VECTOR_INDEX_NAME,
            "indexed_rows": l3_indexed,
            "vector_dim": L3_VECTOR_DIM,
        },
    }


def list_unified_memory_entries(
    db_path: str | Path,
    *,
    limit: int = 100,
    include_inactive: bool = False,
) -> tuple[dict[str, object], ...]:
    """Return one memory view backed by the event log, not separate stores."""

    path = initialize_phase20_7_store(db_path)
    entries: list[dict[str, object]] = []
    with sqlite3.connect(path) as conn:
        alignment_rows = conn.execute(
            """
            SELECT event_id, payload_json, reward, punish, created_at_ms
            FROM phase20_7_experience_events
            WHERE event_kind='experience_alignment'
            ORDER BY created_at_ms DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        for event_id, payload_json, reward, punish, created_at_ms in alignment_rows:
            active = not is_tombstoned(conn, object_kind="event", object_ref=str(event_id))
            if not include_inactive and not active:
                continue
            payload = from_json(str(payload_json))
            input_payload = _event_payload(conn, payload.get("input_event_id"))
            output_text = "".join(str(ch) for ch in payload.get("output_chars", ()))
            input_text = str(input_payload.get("text", ""))
            visual_signature = str(payload.get("visual_signature", "") or "")
            modality_note = " · 含视觉证据" if visual_signature else ""
            input_signature = str(payload.get("input_signature", "") or "")
            sc = _alignment_support_count(conn, input_signature=input_signature) if input_signature else 0
            support = _support_from_reward_punish(float(reward), float(punish), support_count=sc)
            entries.append(
                {
                    "memory_entry_id": str(event_id),
                    "active": active,
                    "memory_view": "local_memory_package_unified",
                    "processing_tendency": f"support_{support:.3f}",
                    "source_event_kind": "experience_alignment",
                    "input_text": input_text,
                    "output_text": output_text,
                    "visual_signature": visual_signature,
                    "display_text": (
                        f"[纠错] {input_text}{modality_note} -> {output_text}"
                        if str(payload.get("alignment_role") or "") == "counter_evidence"
                        else f"{input_text}{modality_note} -> {output_text}" if input_text else output_text
                    ),
                    "memory_role": str(payload.get("alignment_role") or ""),
                    "support": support,
                    "created_at_ms": int(created_at_ms),
                }
            )

        trace_rows = conn.execute(
            """
            SELECT event_id, payload_json, created_at_ms
            FROM phase20_7_experience_events
            WHERE event_kind='text_receptor_observation'
            ORDER BY created_at_ms DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        for event_id, payload_json, created_at_ms in trace_rows:
            active = not is_tombstoned(conn, object_kind="event", object_ref=str(event_id))
            if not include_inactive and not active:
                continue
            payload = from_json(str(payload_json))
            # text_receptor_observation 是未学习的输入观察, 不是学习结果. 其把握度是
            # 先验底噪(§737 Grasp 的 support_count=0 且无奖惩分量), 与退火底噪 _SUPPORT_BASE
            # 同源, 明确标注为先验而非学习出来的把握, 避免硬编码魔数伪装成学习结果(§3351红线3).
            entries.append(
                {
                    "memory_entry_id": str(event_id),
                    "active": active,
                    "memory_view": "local_memory_package_unified",
                    "processing_tendency": "support_prior_observation",
                    "source_event_kind": "text_receptor_observation",
                    "input_text": str(payload.get("text", "")),
                    "output_text": "",
                    "display_text": str(payload.get("text", "")) or str(payload.get("text_hash", "")),
                    "support": _SUPPORT_BASE,
                    "created_at_ms": int(created_at_ms),
                }
            )
    entries.sort(key=lambda item: int(item["created_at_ms"]), reverse=True)
    return tuple(entries[: int(limit)])


def tombstone_memory_entry(db_path: str | Path, *, memory_entry_id: str, reason: str) -> str:
    path = initialize_phase20_7_store(db_path)
    with sqlite3.connect(path) as conn:
        tombstone_id = insert_tombstone(conn, object_kind="event", object_ref=memory_entry_id, reason=reason)
        conn.commit()
    rebuild_phase20_7_indexes(path)
    return tombstone_id


def create_import_batch(
    db_path: str | Path,
    *,
    package_id: str,
    package_name: str,
    source_hash: str,
    dedup_policy: str = "event_log_identity",
    payload: Mapping[str, Any] | None = None,
) -> str:
    path = initialize_phase20_7_store(db_path)
    import_batch_id = new_ref("import")
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO phase20_7_import_batches(
              import_batch_id, package_id, package_name, imported_at_ms,
              source_hash, dedup_policy, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                import_batch_id,
                package_id,
                package_name,
                now_ms(),
                source_hash,
                dedup_policy,
                to_json(payload or {}),
            ),
        )
        conn.commit()
    return import_batch_id


def attach_package_membership(
    db_path: str | Path,
    *,
    import_batch_id: str,
    object_kind: str,
    object_ref: str,
    was_new: bool,
    event_id: str | None = None,
    occurrence_id: str | None = None,
    edge_id: str | None = None,
    sa_type_id: str | None = None,
    payload_ref: str | None = None,
    dedup_target_ref: str | None = None,
) -> str:
    path = initialize_phase20_7_store(db_path)
    membership_id = new_ref("membership")
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO phase20_7_package_memberships(
              membership_id, import_batch_id, object_kind, object_ref, event_id,
              occurrence_id, edge_id, sa_type_id, payload_ref, was_new, dedup_target_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                membership_id,
                import_batch_id,
                object_kind,
                object_ref,
                event_id,
                occurrence_id,
                edge_id,
                sa_type_id,
                payload_ref,
                1 if was_new else 0,
                dedup_target_ref,
            ),
        )
        conn.commit()
    return membership_id


def unload_import_batch(db_path: str | Path, *, import_batch_id: str, reason: str = "package_unload") -> dict[str, object]:
    path = initialize_phase20_7_store(db_path)
    tombstoned: list[str] = []
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            """
            SELECT object_kind, object_ref
            FROM phase20_7_package_memberships
            WHERE import_batch_id=? AND was_new=1
            """,
            (import_batch_id,),
        ).fetchall()
        for object_kind, object_ref in rows:
            if is_tombstoned(conn, object_kind=str(object_kind), object_ref=str(object_ref)):
                continue
            insert_tombstone(conn, object_kind=str(object_kind), object_ref=str(object_ref), reason=reason)
            tombstoned.append(str(object_ref))
        conn.commit()
    rebuild_phase20_7_indexes(path)
    return {"import_batch_id": import_batch_id, "tombstoned_count": len(tombstoned), "object_refs": tombstoned}


def active_unclosed_for_signature(
    conn: sqlite3.Connection,
    *,
    source_signature: str,
) -> dict[str, object] | None:
    row = conn.execute(
        """
        SELECT unclosed_id, session_id, source_event_id, source_signature, source_text,
               u_value, status, attempt_count, reason_json, created_at_ms, updated_at_ms
        FROM phase20_7_unclosed_items
        WHERE source_signature=? AND status='active'
        ORDER BY updated_at_ms DESC
        LIMIT 1
        """,
        (source_signature,),
    ).fetchone()
    return _unclosed_row_to_dict(row) if row else None


def upsert_unclosed_item(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    tick: int,
    source_event_id: str,
    source_signature: str,
    source_text: str,
    u_delta: float,
    reason: Mapping[str, Any],
) -> tuple[str, str]:
    existing = active_unclosed_for_signature(conn, source_signature=source_signature)
    if existing:
        unclosed_id = str(existing["unclosed_id"])
        u_value = min(1.0, float(existing["u_value"]) * 0.92 + float(u_delta))
        attempt_count = int(existing["attempt_count"]) + 1
        conn.execute(
            """
            UPDATE phase20_7_unclosed_items
            SET u_value=?, attempt_count=?, reason_json=?, updated_at_ms=?
            WHERE unclosed_id=?
            """,
            (u_value, attempt_count, to_json(reason), now_ms(), unclosed_id),
        )
    else:
        unclosed_id = new_ref("unclosed")
        u_value = min(1.0, max(0.0, float(u_delta)))
        attempt_count = 1
        current_ms = now_ms()
        conn.execute(
            """
            INSERT INTO phase20_7_unclosed_items(
              unclosed_id, session_id, source_event_id, source_signature, source_text,
              u_value, status, attempt_count, reason_json, created_at_ms, updated_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                unclosed_id,
                session_id,
                source_event_id,
                source_signature,
                source_text,
                u_value,
                "active",
                attempt_count,
                to_json(reason),
                current_ms,
                current_ms,
            ),
        )
    event_id = insert_experience_event(
        conn,
        session_id=session_id,
        tick=tick,
        event_kind="unclosed_item_update",
        payload={
            "unclosed_id": unclosed_id,
            "source_event_id": source_event_id,
            "source_signature": source_signature,
            "source_text": source_text,
            "u_value": u_value,
            "attempt_count": attempt_count,
            "reason": dict(reason),
        },
    )
    return unclosed_id, event_id


def resolve_unclosed_items(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    tick: int,
    source_signature: str,
    reason: str,
) -> tuple[str, ...]:
    rows = conn.execute(
        """
        SELECT unclosed_id, source_event_id, source_text
        FROM phase20_7_unclosed_items
        WHERE source_signature=? AND status='active'
        """,
        (source_signature,),
    ).fetchall()
    event_ids: list[str] = []
    for unclosed_id, source_event_id, source_text in rows:
        conn.execute(
            """
            UPDATE phase20_7_unclosed_items
            SET status='resolved', u_value=0.0, updated_at_ms=?
            WHERE unclosed_id=?
            """,
            (now_ms(), str(unclosed_id)),
        )
        event_ids.append(
            insert_experience_event(
                conn,
                session_id=session_id,
                tick=tick,
                event_kind="unclosed_item_resolved",
                payload={
                    "unclosed_id": str(unclosed_id),
                    "source_event_id": str(source_event_id),
                    "source_signature": source_signature,
                    "source_text": str(source_text),
                    "reason": reason,
                },
            )
        )
    return tuple(event_ids)


def list_active_unclosed_items(
    db_path: str | Path,
    *,
    limit: int = 20,
    session_id: str | None = None,
) -> tuple[dict[str, object], ...]:
    path = initialize_phase20_7_store(db_path)
    with sqlite3.connect(path) as conn:
        if session_id:
            rows = conn.execute(
                """
                SELECT unclosed_id, session_id, source_event_id, source_signature, source_text,
                       u_value, status, attempt_count, reason_json, created_at_ms, updated_at_ms
                FROM phase20_7_unclosed_items
                WHERE status='active' AND session_id=?
                ORDER BY u_value DESC, updated_at_ms DESC
                LIMIT ?
                """,
                (session_id, int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT unclosed_id, session_id, source_event_id, source_signature, source_text,
                       u_value, status, attempt_count, reason_json, created_at_ms, updated_at_ms
                FROM phase20_7_unclosed_items
                WHERE status='active'
                ORDER BY u_value DESC, updated_at_ms DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
    return tuple(item for row in rows if (item := _unclosed_row_to_dict(row)) is not None)


def insert_tombstone(conn: sqlite3.Connection, *, object_kind: str, object_ref: str, reason: str) -> str:
    tombstone_id = new_ref("tombstone")
    conn.execute(
        """
        INSERT INTO phase20_7_memory_tombstones(
          tombstone_id, object_kind, object_ref, reason, created_at_ms
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (tombstone_id, object_kind, object_ref, reason, now_ms()),
    )
    return tombstone_id


def is_tombstoned(conn: sqlite3.Connection, *, object_kind: str, object_ref: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM phase20_7_memory_tombstones
        WHERE object_kind=? AND object_ref=?
        LIMIT 1
        """,
        (object_kind, object_ref),
    ).fetchone()
    return row is not None


# --- support 退火后验把握感 (白皮书 §173.5 退火曲线 / §737 Grasp) ---
# support_count 是派生计数(同 input_signature 下 reward>0 的 experience_alignment 累计确认
# 次数), 真相源是 append-only 经验流(§24/§132), 不存表/不增列, 可由 rebuild 重建.
# 退火范式与 L1 向量嵌入(line 362 lr_min+(lr_max-lr_min)*exp(-support_count/tau))同源,
# 只是作用在把握感标量而非向量. 系数依据 §173.5/§173.6: 初学易被一次经验影响(sc=0 时
# lr=lr_max), 熟练后更稳定(sc 增大 lr 退火到 lr_min).
_SUPPORT_LR_MAX = 0.30   # 首次确认(support_count=0)的把握位移幅度上界
_SUPPORT_LR_MIN = 0.04   # 成熟后单次确认的把握位移幅度(退火下限)
_SUPPORT_TAU = 24.0      # 退火时间常数(拟人: 多次确认后趋稳, §173.6)
_SUPPORT_BASE = 0.34     # 未确认时的把握底噪(底噪, 非学习结果)


def _alignment_support_count(conn: sqlite3.Connection, *, input_signature: str) -> int:
    """派生计数: 同 input_signature 下 reward>0 的 experience_alignment 累计确认次数.

    真相源是 append-only 经验流(§24/§132), 不是新表/新列. 只读既有表, 用于 support
    退火计算(§173.5), 不直接决定答案, 不新增认知实体. 可由 rebuild_phase20_7_indexes
    重建.
    """
    row = conn.execute(
        """
        SELECT COUNT(*) FROM phase20_7_experience_events
        WHERE event_kind='experience_alignment'
          AND json_extract(payload_json, '$.input_signature')=?
          AND reward>0
        """,
        (str(input_signature),),
    ).fetchone()
    return int(row[0]) if row else 0


def _alignment_counter_count(conn: sqlite3.Connection, *, input_signature: str) -> int:
    """§2363 反例计数: 同 input_signature 下惩罚主导的 alignment 累计次数.

    数据源是两类经验后验反例(均为 append-only 经验流派生, §132 可重建):
    1. alignment_role=counter_evidence 的纠错反馈 (teacher_correction, §2363 第4类);
    2. punish>reward 的普通 alignment (failed_action_outcome 近似, §2363 第3类).
    用于把 §173.5 的 support_count 对称化为"确认数-反例数", 让"纠正过的更谨慎"
    成为数学结果而非措辞. 只读既有表, 不新增实体.
    """
    row = conn.execute(
        """
        SELECT COUNT(*) FROM phase20_7_experience_events
        WHERE event_kind='experience_alignment'
          AND json_extract(payload_json, '$.input_signature')=?
          AND punish>reward
        """,
        (str(input_signature),),
    ).fetchone()
    return int(row[0]) if row else 0


def _unit_evidence_count(conn: sqlite3.Connection, *, unit_text: str) -> int:
    """派生计数: 某文本单元(单字符)在经验流 occurrence 中的历史出现次数.

    白皮书 §8/§15: 单元自身的经验支持度决定它是"有独立含义的认知对象"还是噪声.
    用于 structural_b 泛化时评估 residual 单元的证据强度 — residual 含高证据单元
    (如数字位在大量上下文出现过)时, 子序列泛化应更谨慎 (§44.1 部分匹配审计).
    纯感受器级统计, 与单元的具体语义无关, 不是关键词路由. 只读既有表.
    """
    sa_type_id = f"text_unit::{_hash_text(str(unit_text))}"
    row = conn.execute(
        "SELECT COUNT(*) FROM phase20_7_occurrences WHERE sa_type_id=?",
        (sa_type_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def _support_from_reward_punish(
    reward: float,
    punish: float,
    *,
    support_count: int = 0,
) -> float:
    """白皮书 §173.5 退火后验把握感(§737 Grasp).

    support_count=0 时 lr=lr_max(初学易被一次经验影响, §173.6); support_count 增大,
    lr 退火到 lr_min(熟练后更稳定). §173.5 lr_eff = lr_t * (1 + reward_punish_boost),
    单一乘子; 位移由净奖惩量 (reward-punish) 决定, 奖惩等时净位移=0(不偏).

    实测边界: sc=0 r=1.0 p=0 -> 0.73(首教把握够高); sc=0 r=0 p=0 -> 0.34(底噪);
    sc=0 r=0 p=1.0 -> 0.18(纯惩低); sc=0 r=1.0 p=1.0 -> 0.34(奖惩等不偏);
    sc=10 r=1.0 -> 0.61; sc=50 r=1.0 -> 0.43(成熟趋稳).
    """
    lr = _SUPPORT_LR_MIN + (_SUPPORT_LR_MAX - _SUPPORT_LR_MIN) * math.exp(
        -max(0, int(support_count)) / _SUPPORT_TAU
    )
    boost = (
        1.0
        + 0.3 * max(0.0, min(1.0, float(reward)))
        + 0.2 * max(0.0, min(1.0, float(punish)))
    )
    lr_eff = lr * boost
    net_strength = max(0.0, min(1.0, float(reward))) - max(0.0, min(1.0, float(punish)))
    grasp = _SUPPORT_BASE + lr_eff * net_strength
    return max(0.18, min(0.96, grasp))


def _hash_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _event_payload(conn: sqlite3.Connection, event_id: object | None) -> dict[str, object]:
    if not event_id:
        return {}
    row = conn.execute(
        "SELECT payload_json FROM phase20_7_experience_events WHERE event_id=?",
        (str(event_id),),
    ).fetchone()
    if row is None:
        return {}
    payload = from_json(str(row[0]))
    return payload if isinstance(payload, dict) else {}


def _unclosed_row_to_dict(row: object) -> dict[str, object] | None:
    if row is None:
        return None
    (
        unclosed_id,
        session_id,
        source_event_id,
        source_signature,
        source_text,
        u_value,
        status,
        attempt_count,
        reason_json,
        created_at_ms,
        updated_at_ms,
    ) = row
    return {
        "unclosed_id": str(unclosed_id),
        "session_id": str(session_id),
        "source_event_id": str(source_event_id),
        "source_signature": str(source_signature),
        "source_text": str(source_text),
        "u_value": float(u_value),
        "status": str(status),
        "attempt_count": int(attempt_count),
        "reason": from_json(str(reason_json)),
        "created_at_ms": int(created_at_ms),
        "updated_at_ms": int(updated_at_ms),
    }
