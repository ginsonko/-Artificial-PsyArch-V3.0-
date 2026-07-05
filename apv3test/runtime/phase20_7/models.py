from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence


PHASE20_7_STAGE0_SCHEMA_ID = "apv3_phase20_7_stage0_boundary/v1"
RUNTIME_EVENT_SCHEMA_ID = "apv3_phase20_7_runtime_tick_event/v2"


@dataclass(frozen=True)
class MediaInput:
    """AP-native sensor input descriptor.

    Stage 0 stores the boundary shape only. Later stages will turn these into
    text, visual, audio, canvas, or tool occurrences.
    """

    media_type: Literal["image", "audio", "canvas", "tool", "text"]
    path: str | None = None
    payload_ref: str | None = None
    source_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "media_type": self.media_type,
            "path": self.path,
            "payload_ref": self.payload_ref,
            "source_hash": self.source_hash,
        }


@dataclass(frozen=True)
class TeacherFeedback:
    feedback_text: str
    reward_mag: float = 0.0
    punish_mag: float = 0.0
    target_event_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "feedback_text": self.feedback_text,
            "reward_mag": float(self.reward_mag),
            "punish_mag": float(self.punish_mag),
            "target_event_id": self.target_event_id,
        }


@dataclass(frozen=True)
class SourceTrustKey:
    source_ref: str
    context: str
    modality: str

    def storage_key(self) -> str:
        return f"{self.source_ref}|{self.context}|{self.modality}"


@dataclass
class EmotionField:
    """8-channel NT emotion field — all values clamped to [0.0, 1.0]."""
    da: float = 0.5   # dopamine — anticipatory reward drive
    adr: float = 0.3  # adrenaline — stress / alertness
    oxy: float = 0.5  # oxytocin — social connection
    ser: float = 0.5  # serotonin — baseline satisfaction
    end: float = 0.4  # endorphin — pleasure from completion
    cor: float = 0.3  # cortisol — sustained pressure
    nov: float = 0.5  # novelty — curiosity trigger
    foc: float = 0.6  # focus — attentional concentration

    def clamp(self) -> "EmotionField":
        return EmotionField(
            da=max(0.0, min(1.0, self.da)),
            adr=max(0.0, min(1.0, self.adr)),
            oxy=max(0.0, min(1.0, self.oxy)),
            ser=max(0.0, min(1.0, self.ser)),
            end=max(0.0, min(1.0, self.end)),
            cor=max(0.0, min(1.0, self.cor)),
            nov=max(0.0, min(1.0, self.nov)),
            foc=max(0.0, min(1.0, self.foc)),
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "da": self.da, "adr": self.adr, "oxy": self.oxy, "ser": self.ser,
            "end": self.end, "cor": self.cor, "nov": self.nov, "foc": self.foc,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "EmotionField":
        if not d:
            return cls()
        return cls(
            da=float(d.get("da", 0.5)),
            adr=float(d.get("adr", 0.3)),
            oxy=float(d.get("oxy", 0.5)),
            ser=float(d.get("ser", 0.5)),
            end=float(d.get("end", 0.4)),
            cor=float(d.get("cor", 0.3)),
            nov=float(d.get("nov", 0.5)),
            foc=float(d.get("foc", 0.6)),
        ).clamp()

    def apply_delta(self, delta: Mapping[str, float]) -> "EmotionField":
        """Return clamped copy after adding delta values."""
        return EmotionField(
            da=self.da + float(delta.get("da", 0.0)),
            adr=self.adr + float(delta.get("adr", 0.0)),
            oxy=self.oxy + float(delta.get("oxy", 0.0)),
            ser=self.ser + float(delta.get("ser", 0.0)),
            end=self.end + float(delta.get("end", 0.0)),
            cor=self.cor + float(delta.get("cor", 0.0)),
            nov=self.nov + float(delta.get("nov", 0.0)),
            foc=self.foc + float(delta.get("foc", 0.0)),
        ).clamp()

    def decay(self, rate: float = 0.02) -> "EmotionField":
        """Decay each channel toward its baseline by rate per tick."""
        _BASE = EmotionField()
        return EmotionField(
            da=self.da + rate * (_BASE.da - self.da),
            adr=self.adr + rate * (_BASE.adr - self.adr),
            oxy=self.oxy + rate * (_BASE.oxy - self.oxy),
            ser=self.ser + rate * (_BASE.ser - self.ser),
            end=self.end + rate * (_BASE.end - self.end),
            cor=self.cor + rate * (_BASE.cor - self.cor),
            nov=self.nov + rate * (_BASE.nov - self.nov),
            foc=self.foc + rate * (_BASE.foc - self.foc),
        ).clamp()


@dataclass(frozen=True)
class RuntimeTickEventV2:
    tick: int
    session_id: str
    selected_action: Mapping[str, Any]
    external_inputs: Sequence[Mapping[str, Any]] = ()
    receptor_outputs: Sequence[Mapping[str, Any]] = ()
    state_pool_top: Sequence[Mapping[str, Any]] = ()
    ssp_active_summary: Mapping[str, Any] = field(default_factory=dict)
    query_structures: Sequence[Mapping[str, Any]] = ()
    b_candidates: Sequence[Mapping[str, Any]] = ()
    c_forward: Sequence[Mapping[str, Any]] = ()
    c_backward: Sequence[Mapping[str, Any]] = ()
    cstar_packet: Mapping[str, Any] = field(default_factory=dict)
    feelings: Mapping[str, Any] = field(default_factory=dict)
    emotion: EmotionField = field(default_factory=EmotionField)
    unclosed_items: Sequence[Mapping[str, Any]] = ()
    action_competition: Sequence[Mapping[str, Any]] = ()
    draft_grid: Mapping[str, Any] = field(default_factory=dict)
    visual_inner_picture: Mapping[str, Any] | None = None
    audio_inner_sketch: Mapping[str, Any] | None = None
    learning_deltas: Sequence[Mapping[str, Any]] = ()
    experience_event_ids_written: Sequence[str] = ()
    source_refs: Sequence[Mapping[str, Any]] = ()
    action_record_ids: Sequence[str] = ()
    rejected_candidates: Sequence[Mapping[str, Any]] = ()
    index_query_trace: Sequence[Mapping[str, Any]] = ()
    package_delta_refs: Sequence[str] = ()
    timings_ms: Mapping[str, Any] = field(default_factory=dict)
    is_projection: Literal[False] = False
    schema_id: str = RUNTIME_EVENT_SCHEMA_ID
    no_write_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "tick": int(self.tick),
            "session_id": self.session_id,
            "is_projection": False,
            "external_inputs": list(self.external_inputs),
            "receptor_outputs": list(self.receptor_outputs),
            "state_pool_top": list(self.state_pool_top),
            "ssp_active_summary": dict(self.ssp_active_summary),
            "query_structures": list(self.query_structures),
            "b_candidates": list(self.b_candidates),
            "c_forward": list(self.c_forward),
            "c_backward": list(self.c_backward),
            "cstar_packet": dict(self.cstar_packet),
            "feelings": dict(self.feelings),
            "emotion": self.emotion.to_dict(),
            "unclosed_items": list(self.unclosed_items),
            "action_competition": list(self.action_competition),
            "selected_action": dict(self.selected_action),
            "draft_grid": dict(self.draft_grid),
            "visual_inner_picture": self.visual_inner_picture,
            "audio_inner_sketch": self.audio_inner_sketch,
            "learning_deltas": list(self.learning_deltas),
            "experience_event_ids_written": list(self.experience_event_ids_written),
            "source_refs": list(self.source_refs),
            "action_record_ids": list(self.action_record_ids),
            "rejected_candidates": list(self.rejected_candidates),
            "index_query_trace": list(self.index_query_trace),
            "package_delta_refs": list(self.package_delta_refs),
            "timings_ms": dict(self.timings_ms),
            "no_write_reason": self.no_write_reason,
        }


@dataclass(frozen=True)
class Phase207TurnResult:
    schema_id: str
    stage_id: str
    session_id: str
    committed: bool
    reply_text: str
    tick_trace: tuple[RuntimeTickEventV2, ...]
    db_path: Path
    stage0_checks: Mapping[str, Any]
    emotion: dict[str, Any] = field(default_factory=dict)
    innate_rules: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "stage_id": self.stage_id,
            "session_id": self.session_id,
            "committed": bool(self.committed),
            "reply_text": self.reply_text,
            "tick_trace": [event.to_dict() for event in self.tick_trace],
            "db_path": str(self.db_path),
            "stage0_checks": dict(self.stage0_checks),
            "emotion": dict(self.emotion),
            "innate_rules": dict(self.innate_rules),
        }


PHASE20_7_SCHEMA_SQL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS phase20_7_sa_types (
      sa_type_id TEXT PRIMARY KEY,
      substrate TEXT NOT NULL,
      modality TEXT NOT NULL,
      canonical_hint TEXT,
      vector_l1 BLOB,
      vector_l2 BLOB,
      vector_l3 BLOB,
      created_tick INTEGER NOT NULL,
      updated_tick INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_source_packets (
      source_packet_id TEXT PRIMARY KEY,
      source_kind TEXT NOT NULL,
      source_ref TEXT,
      source_context TEXT NOT NULL,
      modality TEXT NOT NULL,
      trust_snapshot REAL NOT NULL,
      created_tick INTEGER NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_action_records (
      action_record_id TEXT PRIMARY KEY,
      session_id TEXT NOT NULL,
      tick INTEGER NOT NULL,
      action_type TEXT NOT NULL,
      selected INTEGER NOT NULL,
      drive REAL NOT NULL,
      eligibility_json TEXT NOT NULL,
      target_refs_json TEXT NOT NULL,
      result_event_id TEXT,
      created_at_ms INTEGER NOT NULL
    )
    """,
    # §185 性能: 行动统计 (经验调谐/范式偏置/自测计数) 每 turn 按 session 查行动记录
    # 多次; 该表此前无非主键索引, session 累积后退化为全表扫 → 加 (session, tick) 复合.
    """
    CREATE INDEX IF NOT EXISTS idx_phase20_7_action_records_session_tick
    ON phase20_7_action_records(session_id, tick)
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_experience_events (
      event_id TEXT PRIMARY KEY,
      session_id TEXT NOT NULL,
      tick INTEGER NOT NULL,
      event_kind TEXT NOT NULL,
      source_packet_id TEXT,
      action_record_id TEXT,
      payload_json TEXT NOT NULL,
      reward REAL NOT NULL DEFAULT 0,
      punish REAL NOT NULL DEFAULT 0,
      created_at_ms INTEGER NOT NULL
    )
    """,
    # §185 性能: 经验流按 (session, event_kind, tick) 取最近某类事件是热路径
    # (范式共现/自测/反例统计每 turn 查多次); 无此复合索引会退化为 session 全扫.
    """
    CREATE INDEX IF NOT EXISTS idx_phase20_7_events_session_kind_tick
    ON phase20_7_experience_events(session_id, event_kind, tick)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_phase20_7_events_tick
    ON phase20_7_experience_events(session_id, tick)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_phase20_7_events_kind_time
    ON phase20_7_experience_events(event_kind, created_at_ms)
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_occurrences (
      occurrence_id TEXT PRIMARY KEY,
      event_id TEXT NOT NULL,
      sa_type_id TEXT NOT NULL,
      tick INTEGER NOT NULL,
      substrate TEXT NOT NULL,
      position_json TEXT NOT NULL,
      R REAL NOT NULL,
      V REAL NOT NULL,
      A REAL NOT NULL,
      P REAL NOT NULL,
      clarity REAL NOT NULL,
      source_ref TEXT,
      payload_ref TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_phase20_7_occurrences_event
    ON phase20_7_occurrences(event_id, tick)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_phase20_7_occurrences_sa_type
    ON phase20_7_occurrences(sa_type_id)
    """,
    # §185 性能: 短结构流 occurrence 查询 WHERE sa_type_id LIKE 'prefix%' AND tick<?
    # 复合索引让 LIKE 前缀扫 + tick 范围一次命中, 不必对每条回表比 tick (实测 71ms→<1ms).
    """
    CREATE INDEX IF NOT EXISTS idx_phase20_7_occurrences_satype_tick
    ON phase20_7_occurrences(sa_type_id, tick)
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_structure_edges (
      edge_id TEXT PRIMARY KEY,
      src_occurrence_id TEXT NOT NULL,
      dst_occurrence_id TEXT NOT NULL,
      edge_type TEXT NOT NULL,
      weight REAL NOT NULL,
      learned_weight REAL NOT NULL,
      created_tick INTEGER NOT NULL,
      updated_tick INTEGER NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_phase20_7_edges_src
    ON phase20_7_structure_edges(src_occurrence_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_phase20_7_edges_dst
    ON phase20_7_structure_edges(dst_occurrence_id)
    """,
    # §185 性能: 短结构流召回 (_short_structure_next_candidates) 每 turn 调 ~13 次,
    # WHERE edge_type=? ORDER BY updated_tick DESC LIMIT n. 无此复合索引时规划器
    # 从 dst_event.session_id 驱动全会话扫 + TEMP B-TREE 排序 (实测 96ms/次).
    # (edge_type, updated_tick DESC) 让规划器直接走小的已排序边集, LIMIT 即停 (0.1ms).
    # 效率与全库规模弱相关 — 只读命中该 edge_type 的行, 不遍历全表.
    """
    CREATE INDEX IF NOT EXISTS idx_phase20_7_edges_type_tick
    ON phase20_7_structure_edges(edge_type, updated_tick DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_payload_blobs (
      payload_ref TEXT PRIMARY KEY,
      payload_kind TEXT NOT NULL,
      media_type TEXT NOT NULL,
      bytes BLOB,
      summary_json TEXT NOT NULL,
      source_hash TEXT NOT NULL,
      created_tick INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_import_batches (
      import_batch_id TEXT PRIMARY KEY,
      package_id TEXT NOT NULL,
      package_name TEXT NOT NULL,
      imported_at_ms INTEGER NOT NULL,
      source_hash TEXT NOT NULL,
      dedup_policy TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_package_memberships (
      membership_id TEXT PRIMARY KEY,
      import_batch_id TEXT NOT NULL,
      object_kind TEXT NOT NULL,
      object_ref TEXT NOT NULL,
      event_id TEXT,
      occurrence_id TEXT,
      edge_id TEXT,
      sa_type_id TEXT,
      payload_ref TEXT,
      was_new INTEGER NOT NULL,
      dedup_target_ref TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_derived_runtime_snapshots (
      snapshot_id TEXT PRIMARY KEY,
      session_id TEXT NOT NULL,
      tick INTEGER NOT NULL,
      rebuildable INTEGER NOT NULL,
      payload_json TEXT NOT NULL,
      created_at_ms INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_index_registry (
      index_name TEXT PRIMARY KEY,
      source_event_highwater INTEGER NOT NULL,
      rebuildable INTEGER NOT NULL,
      config_json TEXT NOT NULL,
      updated_at_ms INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_exact_b0_index (
      input_signature TEXT NOT NULL,
      alignment_event_id TEXT NOT NULL,
      input_event_id TEXT,
      output_hash TEXT NOT NULL,
      output_json TEXT NOT NULL,
      support REAL NOT NULL,
      updated_at_ms INTEGER NOT NULL,
      PRIMARY KEY(input_signature, alignment_event_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_phase20_7_exact_b0_lookup
    ON phase20_7_exact_b0_index(input_signature, support, updated_at_ms)
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_memory_tombstones (
      tombstone_id TEXT PRIMARY KEY,
      object_kind TEXT NOT NULL,
      object_ref TEXT NOT NULL,
      reason TEXT NOT NULL,
      created_at_ms INTEGER NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_phase20_7_memory_tombstones_ref
    ON phase20_7_memory_tombstones(object_kind, object_ref)
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_unclosed_items (
      unclosed_id TEXT PRIMARY KEY,
      session_id TEXT NOT NULL,
      source_event_id TEXT NOT NULL,
      source_signature TEXT NOT NULL,
      source_text TEXT NOT NULL,
      u_value REAL NOT NULL,
      status TEXT NOT NULL,
      attempt_count INTEGER NOT NULL,
      reason_json TEXT NOT NULL,
      created_at_ms INTEGER NOT NULL,
      updated_at_ms INTEGER NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_phase20_7_unclosed_status
    ON phase20_7_unclosed_items(status, u_value, updated_at_ms)
    """,
    # ── v0.2 new tables ───────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS phase20_7_emotion_snapshot (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      tick       INTEGER NOT NULL,
      turn_id    TEXT,
      da         REAL NOT NULL DEFAULT 0.5,
      adr        REAL NOT NULL DEFAULT 0.3,
      oxy        REAL NOT NULL DEFAULT 0.5,
      ser        REAL NOT NULL DEFAULT 0.5,
      end_val    REAL NOT NULL DEFAULT 0.4,
      cor        REAL NOT NULL DEFAULT 0.3,
      nov        REAL NOT NULL DEFAULT 0.5,
      foc        REAL NOT NULL DEFAULT 0.6,
      created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_emotion_snap_tick
    ON phase20_7_emotion_snapshot(tick DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_actuator_registry (
      actuator_id     TEXT PRIMARY KEY,
      conflict_group  TEXT NOT NULL DEFAULT 'default',
      action_type     TEXT NOT NULL,
      invocation_spec TEXT NOT NULL DEFAULT 'builtin',
      param_schema    TEXT NOT NULL DEFAULT '{}',
      result_sa_type  TEXT,
      description     TEXT,
      is_seed         INTEGER NOT NULL DEFAULT 0,
      created_at      INTEGER NOT NULL DEFAULT (strftime('%s','now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_paradigm_registry (
      id                INTEGER PRIMARY KEY AUTOINCREMENT,
      paradigm_key      TEXT NOT NULL UNIQUE,
      state_set         TEXT NOT NULL DEFAULT '[]',
      anchor_set        TEXT NOT NULL DEFAULT '[]',
      content_src_set   TEXT NOT NULL DEFAULT '[]',
      trigger_condition TEXT,
      is_seed           INTEGER NOT NULL DEFAULT 0,
      created_at        INTEGER NOT NULL DEFAULT (strftime('%s','now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS phase20_7_l2_cooccurrence_group (
      group_id   INTEGER PRIMARY KEY AUTOINCREMENT,
      tick       INTEGER NOT NULL,
      turn_id    TEXT,
      sa_ids     TEXT NOT NULL,
      modalities TEXT NOT NULL DEFAULT '[]',
      created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_l2_group_tick
    ON phase20_7_l2_cooccurrence_group(tick)
    """,
)


REQUIRED_PHASE20_7_TABLES: tuple[str, ...] = (
    "phase20_7_action_records",
    "phase20_7_actuator_registry",
    "phase20_7_derived_runtime_snapshots",
    "phase20_7_emotion_snapshot",
    "phase20_7_experience_events",
    "phase20_7_exact_b0_index",
    "phase20_7_import_batches",
    "phase20_7_index_registry",
    "phase20_7_l2_cooccurrence_group",
    "phase20_7_memory_tombstones",
    "phase20_7_occurrences",
    "phase20_7_package_memberships",
    "phase20_7_paradigm_registry",
    "phase20_7_payload_blobs",
    "phase20_7_sa_types",
    "phase20_7_source_packets",
    "phase20_7_structure_edges",
    "phase20_7_unclosed_items",
)
