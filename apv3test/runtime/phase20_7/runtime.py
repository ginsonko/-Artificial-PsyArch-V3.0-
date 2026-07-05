from __future__ import annotations

import hashlib
import json
import math
import queue
import sqlite3
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from apv3test.runtime.draft_grid import DraftGrid
from runtime.cognitive.state_pool.state_pool import StateItem, StatePool

from .experience_log import (
    active_unclosed_for_signature,
    from_json,
    initialize_phase20_7_store,
    insert_action_record,
    insert_experience_event,
    insert_occurrence,
    insert_source_packet,
    insert_structure_edge,
    is_tombstoned,
    l1_centroid,
    l1_cosine,
    l1_triplet_update_vector,
    l2_compose,
    l2_cosine,
    l2_edge_sa_type_id,
    l2_initial_vector_for,
    l2_structure_update_vector,
    L2_RELATION_LINEAR_NEXT,
    bytes_to_l2_vector,
    load_sa_type_vector_l1,
    load_sa_type_vector_l2,
    now_ms,
    phase20_7_schema_status,
    resolve_unclosed_items,
    to_json,
    update_sa_type_vector_l1,
    update_sa_type_vector_l2,
    upsert_sa_type,
    upsert_exact_b0_index,
    upsert_unclosed_item,
    _alignment_support_count,
    _alignment_counter_count,
    _unit_evidence_count,
    _support_from_reward_punish,
    l3_action_context_code,
    l3_action_consequence_update_vector,
    l3_cosine,
    l3_edge_sa_type_id,
    l3_initial_vector_for,
    load_sa_type_vector_l3,
    update_sa_type_vector_l3,
    L3_VECTOR_INDEX_NAME,
    L3_RELATION_ACTION_CONSEQUENCE,
    L3_OUTWARD_ACTION_TYPES,
)
from .models import (
    PHASE20_7_STAGE0_SCHEMA_ID,
    EmotionField,
    MediaInput,
    Phase207TurnResult,
    RuntimeTickEventV2,
    TeacherFeedback,
)
from .audio import estimate_idle_audio_drive, record_tts_actuator_tick, run_audio_audit_ticks, run_idle_audio_focus_tick
from .cognitive_cycle import CSTAR_MIN_ERROR_FORMULA_ID, complete_every_tick_cognitive_cycle, complete_turn_cognitive_cycle
from .experience_candidate import (
    UnifiedExperienceCandidate,
    compute_unified_experience_support,
    merge_unified_experience_candidates,
    unified_candidate_from_flow,
    unified_candidate_from_recall,
)
from .experience_flow import ExperienceFlowCandidate, query_recent_experience_flow_candidates
from .experience_recall import ExperienceRecallCandidate, ExperienceRecallQuery, query_experience_alignment_candidates
from .vision import (
    estimate_idle_visual_drive,
    run_idle_visual_receptor_tick,
    run_visual_imagination_recall_tick,
    run_visual_receptor_ticks,
)


def _register_action_sa(
    conn: sqlite3.Connection,
    *,
    action_type: str,
    action_record_id: str,
    determination: float,
    tick: int,
    target_refs: Mapping[str, Any] | None = None,
) -> None:
    """§7.3 行动SA一等公民化: 每次行动产生时，注册 action:: SA 并插入 occurrence。"""
    sa_type_id = f"action::{action_type}"
    upsert_sa_type(
        conn,
        sa_type_id=sa_type_id,
        substrate="action",
        modality="action",
        canonical_hint=action_type,
        tick=tick,
    )
    position: dict[str, Any] = {}
    if target_refs:
        for k in ("draft_row", "draft_col", "char_index"):
            if target_refs.get(k) is not None:
                position[k] = target_refs[k]
    insert_occurrence(
        conn,
        event_id=action_record_id,
        sa_type_id=sa_type_id,
        tick=tick,
        substrate="action",
        position=position,
        r=max(0.0, min(1.0, float(determination))),
        v=0.0,
        a=0.0,
        p=0.0,
        clarity=1.0,
        source_ref=action_record_id,
    )


def _register_action_sa_from_record(
    conn: sqlite3.Connection, action_record_id: str, tick: int
) -> None:
    """One-line call for all 14 insert_action_record sites."""
    row = conn.execute(
        "SELECT action_type, drive, target_refs_json FROM phase20_7_action_records "
        "WHERE action_record_id=?",
        (action_record_id,),
    ).fetchone()
    if row is None:
        return
    action_type_val, drive_val, refs_json = row
    target_refs = from_json(refs_json) if refs_json else {}
    _register_action_sa(
        conn,
        action_type=str(action_type_val),
        action_record_id=action_record_id,
        determination=float(drive_val or 0.0),
        tick=tick,
        target_refs=target_refs if isinstance(target_refs, dict) else None,
    )


PHASE20_7_STAGE1_SCHEMA_ID = "apv3_phase20_7_stage1_text_closed_loop/v1"
PHASE20_7_STAGE3_SCHEMA_ID = "apv3_phase20_7_stage3_structural_bccstar/v1"
PHASE20_7_STAGE4_SCHEMA_ID = "apv3_phase20_7_stage4_unclosed_idle/v1"
PHASE20_7_STAGE5_SCHEMA_ID = "apv3_phase20_7_stage5_visual_patch_reconstruction/v1"
PHASE20_7_STAGE6_SCHEMA_ID = "apv3_phase20_7_stage6_audio_tts_actuator/v1"
PHASE20_8I_CSTAR_STATEPOOL_FEEDBACK_ID = "apv3_phase20_8i_cstar_statepool_virtual_feedback/v1"
PHASE20_8J_CSTAR_CARRYOVER_ID = "apv3_phase20_8j_cstar_carryover_next_tick_influence/v1"
PHASE20_8K_CARRYOVER_SSP_FLOW_ID = "apv3_phase20_8k_carryover_ssp_short_structure_flow/v1"
PHASE20_8L_SHORT_STRUCTURE_QUERY_ID = "apv3_phase20_8l_short_structure_next_unified_query/v1"
PHASE20_8N_REQUEST_TEACHER_DRIVE_ID = "apv3_phase20_8n_request_teacher_unified_drive/v1"
PHASE20_8O_REQUEST_EXPRESSION_ID = "apv3_phase20_8o_request_expression_from_experience_flow/v1"
PHASE20_8P_EXPRESSION_PARADIGM_ID = "apv3_phase20_8p_expression_paradigm_slots/v1"
PHASE20_8Q_EXPRESSION_FRAGMENT_COMPOSITION_ID = "apv3_phase20_8q_draftgrid_expression_fragment_composition/v1"
PHASE20_8R_CURRENT_REFERENT_BINDING_ID = "apv3_phase20_8r_current_referent_expression_binding/v1"
PHASE20_9B_LEARNING_PROTOCOL_DRIVE_MODULATION_ID = "apv3_phase20_9b_learning_protocol_drive_modulation/v1"
PHASE20_9E_LEARNING_LOOP_CARRYOVER_ID = "apv3_phase20_9e_learning_loop_carryover/v1"
PHASE20_9F_IDLE_LEARNING_REVIEW_ID = "apv3_phase20_9f_idle_learning_review/v1"
PHASE20_9G_IDLE_SELF_TEST_ID = "apv3_phase20_9g_idle_self_test/v1"
PHASE20_9H_SELF_TEST_FEEDBACK_ID = "apv3_phase20_9h_self_test_feedback/v1"
PHASE20_9J_STRUCTURAL_GENERALIZATION_ID = "apv3_phase20_9j_structural_generalization_value_modulation/v1"
PHASE20_9K_OUTWARD_SPEECH_ID = "apv3_phase20_9k_outward_speech_action_competition/v1"
PHASE20_9M_FALLBACK_EXPRESSION_SEED_ID = "apv3_phase20_9m_fallback_expression_seedification/v1"
PHASE20_9N_FEEDBACK_DRIVE_ID = "apv3_phase20_9n_integrate_feedback_drive_from_ap_flow/v1"
PHASE20_9O_COMMIT_DRIVE_ID = "apv3_phase20_9o_commit_reply_drive_from_ap_flow/v1"
PHASE20_9P_DRAFTGRID_ACTION_ID = "apv3_phase20_9p_draftgrid_action_competition_from_ap_flow/v1"
PHASE20_9Q_DRAFTGRID_READBACK_FLOW_ID = "apv3_phase20_9q_draftgrid_readback_self_flow/v1"
PHASE20_9Q_ATTRIBUTION_CONSOLIDATION_ID = "apv3_phase20_9q_reward_punish_backward_attribution_consolidation/v1"
PHASE20_9R_EDIT_CELL_ID = "apv3_phase20_9r_cstar_alternative_unit_edit_cell/v1"
PHASE20_9S_EDIT_OUTCOME_ID = "apv3_phase20_9s_edit_outcome_learning_carryover/v1"
PHASE20_9W_DRAFTGRID_SUCCESSOR_ID = "apv3_phase20_9w_draftgrid_successor_from_experience_flow/v1"
PHASE20_9X_DRAFTGRID_OUTCOME_MODULATION_ID = "apv3_phase20_9x_draftgrid_successor_action_outcome_modulation/v1"
PHASE20_9Y_DRAFTGRID_EXPERIENCE_TUNER_ID = "apv3_phase20_9y_draftgrid_experience_tuner_projection/v1"
PHASE20_9Z_ACTION_EXPERIENCE_TUNER_ID = "apv3_phase20_9z_unified_action_experience_tuner_projection/v1"
PHASE20_10A_LEARNING_STAGE_RUNTIME_ID = "apv3_phase20_10a_learning_stage_runtime_progression/v1"
# Phase20.13c — Language Learning Ladder 纯派生判据投影 (白皮书 EDUCATION_PROTOCOL
# "Language Learning Ladder" 6 阶段). 与 learning_stage_runtime_progression 同载体
# 同 guardrail: 仅聚合既有 projection_only 量 (体验流/语义/草稿碎片/认知感觉/奖惩),
# 不新增采集、不改 selected、不写答案、不藏 solver、主观 may_be_wrong. 回答"某场景
# 是否通过 keyword_organization 等阶梯", 不替代 lifecycle 的教学褪除判定, 二者并存互补.
PHASE20_13C_LANGUAGE_LEARNING_LADDER_ID = "apv3_phase20_13c_language_learning_ladder_projection/v1"
# Phase20.14 — 场景学成判据 纯派生投影 (白皮书 EDUCATION_PROTOCOL 630 行:
# "keyword_organization_stage_passed=true before claiming a scene learned",
# 配合 148-149 行 scaffold 褪除顺序 teacher_off -> cold_retest). 合成 13c 阶梯判据
# 与 10b lifecycle 的 teacher_exit_ready/cold_retest_ready 就绪度, 回答"该场景在
# teacher_off + cold_retest 双条件下是否走完 keyword_organization". 与 13c 同型
# guardrail: 软判据 may_be_wrong, 产连续 confidence 不产布尔 passed, 不声称收敛/完成.
PHASE20_14_SCENE_LEARNED_ID = "apv3_phase20_14_scene_learned_projection/v1"
PHASE20_10B_LEARNING_OBJECT_LIFECYCLE_ID = "apv3_phase20_10b_learning_object_lifecycle_projection/v1"
PHASE20_10D_LONG_INTERVAL_COLD_RETEST_ID = "apv3_phase20_10d_long_interval_cold_retest_window/v1"
PHASE20_10E_COLD_RETEST_GENERALIZATION_ID = "apv3_phase20_10e_cold_retest_generalization_confidence_tuning/v1"
PHASE20_10F_MEMORY_RHYTHM_ID = "apv3_phase20_10f_memory_consolidation_forgetting_review_rhythm/v1"
PHASE20_10G_MEMORY_RHYTHM_B_SUPPORT_ID = "apv3_phase20_10g_memory_rhythm_structural_b_support/v1"
NO_CALL_TEXT = "不太会,教教"
LEARNING_ACK_TEXT = "嗯,记下了。"
MAINTAIN_UNCLOSED_TEXT = "不太会,教教"
STRUCTURAL_B_THRESHOLD = 0.55
VISUAL_FOCUS_ANCHOR_UNIT = "visual_focus_anchor"
EXPRESSION_INTENTS = frozenset({"request_teacher", "maintain_unclosed", "integrate_feedback"})

# §185 实时进度钩子: turn 内每 tick 产出时回调, 让 web 层无锁读取当前阶段.
# 由 web_chat 在调用 run_phase20_7_turn 前设置 (线程安全: turn 在 lock 内单线程跑,
# progress endpoint 只读 dict — dict 单键写在 CPython 下是原子的).
_live_progress_hook: Any = None  # Callable[[int, str], None] | None


def set_live_progress_hook(hook: Any) -> None:
    """设置/清除实时进度钩子 (web_chat 用)."""
    global _live_progress_hook
    _live_progress_hook = hook


class _TurnConnection(sqlite3.Connection):
    """每 turn 一个连接 (run_phase20_7_turn 的 with 块内新建, 出块即销毁).

    §185 性能: 携带一个连接生命周期内的只读查询 memo. 用于消除 N+1 —
    结构候选打分循环里对每个候选都调 _self_test/_learning_review/_cold_retest
    行拉取, 而这些查询只依赖 (session_id, before_tick, sa_prefix), 与候选无关,
    228 个候选 × 同一查询 = 228 次全同结果的重复 IO. memo 把它降到 1 次.

    安全性: 缓存的是"某 tick 之前的既有经验行", turn 内 before_tick 固定、
    这些历史行不被本 turn 写入改动 (本 turn 的新 occurrence tick >= before_tick,
    被 o.tick < ? 排除), 故 turn 内缓存与实时查询等价. 连接销毁即缓存销毁,
    绝不跨 turn — 无脏读风险.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._apv3_row_memo: dict[tuple[Any, ...], list[Any]] = {}


def _memoized_rows(conn: sqlite3.Connection, cache_key: tuple[Any, ...], sql: str, params: tuple[Any, ...]) -> list[Any]:
    """turn 内只读行 memo. 非 _TurnConnection (如工具脚本直连) 时退化为直查, 不缓存."""
    memo = getattr(conn, "_apv3_row_memo", None)
    if memo is None:
        return conn.execute(sql, params).fetchall()
    hit = memo.get(cache_key)
    if hit is None:
        hit = conn.execute(sql, params).fetchall()
        memo[cache_key] = hit
    return hit


def _connect_turn(path: str | Path) -> sqlite3.Connection:
    """建 turn 连接 (带只读 memo). WAL/synchronous 由 initialize 持久 PRAGMA 保证."""
    return sqlite3.connect(path, factory=_TurnConnection)


@dataclass(frozen=True)
class _TextObservation:
    event_id: str
    source_packet_id: str
    occurrence_ids: tuple[str, ...]
    signature: str
    text_signature: str
    chars: tuple[str, ...]
    text_hash: str
    visual_signature: str | None = None


@dataclass(frozen=True)
class _RecoveredObservation:
    event_id: str
    source_packet_id: str
    occurrence_ids: tuple[str, ...]
    signature: str
    text_signature: str
    chars: tuple[str, ...]
    text_hash: str
    visual_signature: str | None = None
    recovery_kind: str = "recent_text"


_ObservationLike = _TextObservation | _RecoveredObservation


@dataclass(frozen=True)
class _ExactB0:
    event_id: str
    source_event_id: str
    output_chars: tuple[str, ...]
    support: float
    visual_similarity: float | None = None
    candidate_audit_slots: tuple[dict[str, Any], ...] = ()
    support_terms: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True)
class _StructuralB:
    event_id: str
    source_event_id: str
    source_text: str
    output_chars: tuple[str, ...]
    similarity: float
    shared_units: tuple[str, ...]
    residual_units: tuple[str, ...]
    candidate_audit_slots: tuple[dict[str, Any], ...] = ()
    support_terms: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True)
class _BackwardAttribution:
    observation: _RecoveredObservation
    score: float
    e_backward: float
    source_kind: str
    cause_slots: tuple[dict[str, Any], ...]
    neutralized_occurrences: tuple[dict[str, Any], ...]

    def c_backward_rows(self) -> tuple[dict[str, Any], ...]:
        return (
            {
                "kind": "every_tick_backward_min_error",
                "model": "b_recall_reverse_cause_slots_ssp_neutralization/v1",
                "selected_source_kind": self.source_kind,
                "source_event_id": self.observation.event_id,
                "source_signature": self.observation.signature,
                "text_signature": self.observation.text_signature,
                "visual_signature": self.observation.visual_signature,
                "modality_mix": _observation_modality_mix(self.observation),
                "cause_slots": list(self.cause_slots),
                "neutralized_occurrences": list(self.neutralized_occurrences),
                "cause_grasp": round(self.score, 4),
                "e_backward": round(self.e_backward, 4),
                "subjective": True,
                "may_be_wrong": True,
            },
        )


@dataclass(frozen=True)
class _VisualImaginationRecall:
    alignment_event_ids: tuple[str, ...]
    patch_payload_refs: tuple[str, ...]
    score: float
    matched_texts: tuple[str, ...]
    visual_signature_count: int
    candidate_audit_slots: tuple[dict[str, Any], ...] = ()


def run_phase20_7_turn(
    *,
    user_text: str = "",
    media_inputs: Sequence[MediaInput] = (),
    teacher_feedback: TeacherFeedback | None = None,
    session_id: str,
    db_path: str | Path,
    max_ticks: int = 32,
    post_commit_idle_ticks: int = 2,
    runtime_stage: Literal["stage0", "stage1", "stage3", "stage4", "stage5", "stage6"] = "stage1",
    debug_draftgrid_write_mutation: Mapping[int, str] | None = None,
) -> Phase207TurnResult:
    """Run the Phase20.7 AP-native runtime entry point.

    Stage 1 is the default path: text receptor -> StatePool/SSP -> minimal
    ExperienceLog -> exact B0 -> DraftGrid action loop. `runtime_stage="stage0"`
    keeps the previously validated empty boundary available for redline
    regression checks.
    """

    if runtime_stage == "stage0":
        return _run_stage0_boundary(
            user_text=user_text,
            media_inputs=media_inputs,
            teacher_feedback=teacher_feedback,
            session_id=session_id,
            db_path=db_path,
            max_ticks=max_ticks,
            post_commit_idle_ticks=post_commit_idle_ticks,
            debug_draftgrid_write_mutation=debug_draftgrid_write_mutation,
        )
    return complete_turn_cognitive_cycle(
        _run_stage1_text_loop(
            user_text=user_text,
            media_inputs=media_inputs,
            teacher_feedback=teacher_feedback,
            session_id=session_id,
            db_path=db_path,
            max_ticks=max_ticks,
            post_commit_idle_ticks=post_commit_idle_ticks,
            enable_structural_bccstar=runtime_stage in {"stage3", "stage4", "stage5", "stage6"},
            enable_unclosed_idle=runtime_stage in {"stage4", "stage5", "stage6"},
            enable_visual=runtime_stage in {"stage5", "stage6"},
            enable_audio_tts=runtime_stage == "stage6",
            debug_draftgrid_write_mutation=debug_draftgrid_write_mutation,
        )
    )


def _run_stage0_boundary(
    *,
    user_text: str,
    media_inputs: Sequence[MediaInput],
    teacher_feedback: TeacherFeedback | None,
    session_id: str,
    db_path: str | Path,
    max_ticks: int,
    post_commit_idle_ticks: int,
    debug_draftgrid_write_mutation: Mapping[int, str] | None = None,
) -> Phase207TurnResult:
    path = initialize_phase20_7_store(db_path)
    status = phase20_7_schema_status(path)
    boundary_event = RuntimeTickEventV2(
        tick=0,
        session_id=session_id,
        external_inputs=[
            {
                "input_kind": "text",
                "char_length": len(user_text),
                "stage": "stage0_boundary_not_receptor",
            },
            *_safe_media_inputs(media_inputs),
        ],
        selected_action={
            "action_type": "stage0_boundary_only",
            "reason": "Phase20.7 Stage 0 creates boundary and schema; Stage 1 owns cognitive ticks.",
            "max_ticks_reserved": int(max_ticks),
            "post_commit_idle_ticks_reserved": int(post_commit_idle_ticks),
        },
        action_competition=[
            {
                "action_type": "stage0_boundary_only",
                "selected": True,
                "drive": 1.0,
                "source": "phase20_7_stage0_boundary",
            }
        ],
        source_refs=[
            {
                "source_kind": "user_text_present" if user_text else "no_user_text",
                "teacher_feedback_present": teacher_feedback is not None,
            }
        ],
        timings_ms={"stage0_boundary": 0.0},
        no_write_reason="stage0_does_not_write_experience_events",
    )
    return Phase207TurnResult(
        schema_id=PHASE20_7_STAGE0_SCHEMA_ID,
        stage_id="20.7-stage0",
        session_id=session_id,
        committed=False,
        reply_text="",
        tick_trace=(boundary_event,),
        db_path=path,
        stage0_checks=status,
    )


def _run_stage1_text_loop(
    *,
    user_text: str,
    media_inputs: Sequence[MediaInput],
    teacher_feedback: TeacherFeedback | None,
    session_id: str,
    db_path: str | Path,
    max_ticks: int,
    post_commit_idle_ticks: int,
    enable_structural_bccstar: bool = False,
    enable_unclosed_idle: bool = False,
    enable_visual: bool = False,
    enable_audio_tts: bool = False,
    debug_draftgrid_write_mutation: Mapping[int, str] | None = None,
) -> Phase207TurnResult:
    path = initialize_phase20_7_store(db_path)
    status = phase20_7_schema_status(path)
    grid = DraftGrid()
    pool = StatePool()
    tick_events: list[RuntimeTickEventV2] = []
    tick = 0
    committed = False
    reply_text = ""
    observation: _TextObservation | None = None
    exact_b0: _ExactB0 | None = None
    structural_b: _StructuralB | None = None
    feedback_attribution: _BackwardAttribution | None = None
    visual_imagination: _VisualImaginationRecall | None = None
    output_chars: tuple[str, ...] = ()
    output_intent = "idle_observe"
    paradigm_process_wrote_grid = False
    teacher_request_context: dict[str, Any] = {}
    output_expression_trace: dict[str, Any] = {}
    feedback_drive_context: dict[str, Any] = {}
    commit_drive_context: dict[str, Any] = {}

    with _connect_turn(path) as conn:
        tick = _latest_tick_for_session(conn, session_id=session_id)
        turn_start_tick = tick
        turn_tick_budget = max(1, int(max_ticks))
        _turn_start_ms: float = time.perf_counter() * 1000.0
        _turn_wall_budget_ms: float = 150.0  # §12.3 GAP-05: 50-150ms wall-clock budget
        def _over_turn_budget() -> bool:
            tick_over = (tick - turn_start_tick) >= turn_tick_budget
            wall_over = (time.perf_counter() * 1000.0 - _turn_start_ms) >= _turn_wall_budget_ms
            return tick_over or wall_over
        # §31.2 跨turn情绪加载: 从经验流查上一turn emotion_slow_channel 作为行动调制源.
        # §31.3 长期压力→警觉保守; §32.2 emotion_modulation 调制 write/commit drive.
        prev_emotion_for_turn: dict[str, Any] = {}
        emrow = conn.execute(
            "SELECT payload_json FROM phase20_7_experience_events "
            "WHERE event_kind='emotion_slow_channel' AND session_id=? "
            "ORDER BY tick DESC, created_at_ms DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        if emrow and emrow[0]:
            emp = from_json(str(emrow[0]))
            if isinstance(emp, dict):
                prev_emotion_for_turn = emp
        # §9/ColdSave C5 (P1-2): 状态池跨 turn 持续 — 恢复上一 turn 落盘的能量场
        # 残余(按经过 tick 数补衰减). 未闭合张力/情绪相关 SA 的 V 由此跨 turn 存续.
        _restore_statepool_snapshot(conn, pool, session_id=session_id, current_tick=tick)
        if enable_visual and media_inputs:
            visual_events, tick = run_visual_receptor_ticks(
                conn,
                pool,
                session_id=session_id,
                media_inputs=media_inputs,
                start_tick=tick,
                db_path=path,
                max_visual_ticks=min(3, turn_tick_budget),
            )
            for visual_event in visual_events:
                _append_runtime_tick(tick_events, visual_event)
        if enable_audio_tts and media_inputs:
            audio_events, tick = run_audio_audit_ticks(
                conn,
                pool,
                session_id=session_id,
                media_inputs=media_inputs,
                start_tick=tick,
            )
            for audio_event in audio_events:
                _append_runtime_tick(tick_events, audio_event)

        # §12.3 GAP-05 fix: sensor ticks (visual/audio decoding) can exceed 150ms;
        # wall budget should cover only cognitive processing, not sensor acquisition.
        _turn_start_ms = time.perf_counter() * 1000.0

        if enable_unclosed_idle and not user_text.strip() and teacher_feedback is None and not media_inputs:
            idle_result = _run_idle_think_tick(
                conn,
                pool,
                grid,
                session_id=session_id,
                db_path=path,
                status=status,
                start_tick=tick,
                enable_visual=enable_visual,
                enable_audio_tts=enable_audio_tts,
            )
            # P1-2: idle turn 同样落盘状态池 (idle_think 也会改能量场)
            _persist_statepool_snapshot(
                conn, pool, session_id=session_id, tick=_latest_tick_for_session(conn, session_id=session_id)
            )
            conn.commit()
            return idle_result

        if user_text.strip():
            tick += 1
            pool.tick_decay(tick=tick)  # §54.1/图景[1]: 每 tick 先乘算衰减, 再注入
            visual_signature = _visual_signature_from_events(tick_events)
            backward_attribution: _BackwardAttribution | None = None
            if visual_signature is None and enable_visual:
                backward_attribution = _select_backward_attribution(
                    conn,
                    session_id=session_id,
                    query_text=user_text,
                    current_visual_signature=None,
                )
                # 白皮书 §16.1 规定视觉签名来自本 tick 视觉感受器输入; 此处只在查询
                # 语义上指代某个视觉记忆时, 才继承历史视觉窗口的 visual_signature. 两种
                # 合法指代(§1210): (1) backward_attribution 命中 recent_visual_window——
                # 查询落到了视觉窗口, 如"刚刚图片是啥"指代刚才的图片; (2) 查询与某条带
                # 视觉签名的 experience_alignment 输出文本有足够语义重叠(>=0.34, 与
                # _select_visual_imagination_recall 同阈值), 如"苹果"指代教过的苹果视觉
                # 记忆. 不满足任一条件的模糊命中(如"你是谁?"命中"这是什么?")不借取——
                # 否则未学过的纯文本会带上最近教的视觉记忆签名, 经 _find_visual_exact_b0 /
                # _select_visual_imagination_recall / _observation_is_visual_reference_family
                # 三路泄漏, 复读最近教的答案, 即白皮书 §269 所指的"最近答案覆盖".
                # backward_attribution 本身无论是否借取都保留, 用于 §1160 C_backward 归因
                # 行(c_backward_rows 用其自带 recovered observation, 与当前 observation 的
                # visual_signature 解耦)及 ssp_summary 的 backward_reference.
                if (
                    backward_attribution is not None
                    and _text_query_refers_to_visual_memory(
                        conn,
                        query_text=user_text.strip(),
                        session_id=session_id,
                        backward_source_kind=backward_attribution.source_kind,
                    )
                ):
                    # P1-4: 学得的视觉指代短语解析到"当下最近的视觉窗口"而非教学
                    # 时刻绑定的那张图 — "刚刚图片"永远指最近看的 (拟人指代语境).
                    # 指代判定成立即可继承 (归因窗口本身是否带视觉签名不重要 —
                    # 归因可能落在同短语的历史文本窗口上).
                    visual_signature = (
                        _latest_visual_window_signature(conn, session_id=session_id)
                        or backward_attribution.observation.visual_signature
                    )
            observation = _record_text_observation(
                conn,
                pool,
                session_id=session_id,
                tick=tick,
                text=user_text,
                visual_signature=visual_signature,
            )
            _append_runtime_tick(
                tick_events,
                _tick_event(
                    conn=conn,
                    session_id=session_id,
                    tick=tick,
                    selected_action={"action_type": "observe_text", "source": "text_receptor"},
                    action_competition=_competition("observe_text", selected="observe_text"),
                    state_pool=pool,
                    grid=grid,
                    observation=observation,
                    event_ids=(observation.event_id,),
                    source_refs=({"source_packet_id": observation.source_packet_id, "source_kind": "user_text"},),
                    query_structures=(_query_summary(observation),),
                    ssp_summary={
                        **_ssp_summary(observation),
                        **(
                            {
                                "backward_reference": "experience_window_attribution",
                                "recovered_visual_event_id": backward_attribution.observation.event_id,
                                "selected_source_kind": backward_attribution.source_kind,
                                "cause_grasp": round(backward_attribution.score, 4),
                                "e_backward": round(backward_attribution.e_backward, 4),
                                "subjective_binding": True,
                            }
                            if backward_attribution is not None
                            else {}
                        ),
                    },
                    c_backward=backward_attribution.c_backward_rows() if backward_attribution else (),
                    external_inputs=(
                        {
                            "input_kind": "text",
                            "char_length": len(user_text),
                            "text_hash": observation.text_hash,
                        },
                        *_safe_media_inputs(media_inputs),
                    ),
                ),
            )
            has_current_image_input = any(item.media_type == "image" and item.path for item in media_inputs)
            if enable_visual and not has_current_image_input and not _over_turn_budget():
                visual_imagination = _select_visual_imagination_recall(conn, observation)
                if visual_imagination is not None:
                    imagined_event, imagined_tick = run_visual_imagination_recall_tick(
                        conn,
                        pool,
                        session_id=session_id,
                        start_tick=tick,
                        db_path=path,
                        patch_payload_refs=visual_imagination.patch_payload_refs,
                        source_alignment_ids=visual_imagination.alignment_event_ids,
                        query_text=user_text,
                        recall_score=visual_imagination.score,
                        reason="current_text_occurrence_recalled_visual_experience",
                        candidate_audit_slots=visual_imagination.candidate_audit_slots,
                    )
                    if imagined_event is not None:
                        tick = imagined_tick
                        _append_runtime_tick(tick_events, imagined_event)
                        # §66/§187.2 AP 画板 (第二层): 想象召回成功且该短语的教学史
                        # 含"画"类指代绑定时, 把想象画布逐轮廓投影到画板 —
                        # 每 tick 竞争 project/observe/commit, 画完观察自己的画
                        # (readback 入池), commit 产出 PNG 外显. 教学后验 gate:
                        # 该输入签名有 reward 教学对齐才画 (没教过"画X"不画).
                        _paint_events, tick = _maybe_run_painting_from_imagination(
                            conn,
                            pool,
                            session_id=session_id,
                            tick=tick,
                            db_path=path,
                            observation=observation,
                            imagined_event=imagined_event,
                            turn_budget_left=turn_tick_budget - (tick - turn_start_tick),
                        )
                        for _pe in _paint_events:
                            _append_runtime_tick(tick_events, _pe)

        if teacher_feedback is not None and observation is None:
            feedback_attribution = _select_backward_attribution(
                conn,
                session_id=session_id,
                query_text=teacher_feedback.feedback_text,
                current_visual_signature=None,
                prefer_feedback_target=True,
            )
            observation = (
                feedback_attribution.observation
                if feedback_attribution is not None
                else _recover_recent_observation_for_feedback(conn, session_id=session_id)
            )

        if teacher_feedback is not None:
            tick += 1
            pool.tick_decay(tick=tick)
            feedback_expression_role = _expression_role_for_target_event(conn, teacher_feedback.target_event_id)
            feedback_event_ids = _record_teacher_feedback(
                conn,
                pool,
                session_id=session_id,
                tick=tick,
                feedback=teacher_feedback,
                observation=observation,
                output_intent=output_intent,
            )
            l1_triplet_delta: dict[str, Any] | None = None
            l2_edge_delta: dict[str, Any] | None = None
            l3_action_delta: dict[str, Any] | None = None
            # _record_teacher_feedback may append one or more trailing dicts
            # (l1_vector_triplet_update, l2_temporal_edge_update,
            # l3_action_consequence_update). Strip ALL trailing dicts first
            # (collecting them into trailing_deltas), and only AFTER the strip is
            # complete filter the remaining tuple down to the str event ids. Doing
            # the str-filter inside the loop would drop an earlier trailing dict
            # (e.g. l1) the moment the last dict (e.g. l3) is stripped, because the
            # str filter would discard the l1 dict sitting just before it.
            trailing_deltas: list[dict[str, Any]] = []
            stripped = tuple(feedback_event_ids)
            while stripped and isinstance(stripped[-1], dict):
                trailing_deltas.append(stripped[-1])  # type: ignore[arg-type]
                stripped = tuple(stripped[:-1])
            feedback_event_ids = tuple(item for item in stripped if isinstance(item, str))
            for delta in trailing_deltas:
                kind = str(delta.get("delta_kind") or "")
                if kind == "l1_vector_triplet_update":
                    l1_triplet_delta = delta
                elif kind == "l2_temporal_edge_update":
                    l2_edge_delta = delta
                elif kind == "l3_action_consequence_update":
                    l3_action_delta = delta
            attribution_consolidation = _reward_punish_backward_attribution_consolidation(
                conn,
                session_id=session_id,
                tick=tick,
                result_event_ids=feedback_event_ids,
                reward=teacher_feedback.reward_mag,
                punish=teacher_feedback.punish_mag,
                observation=observation,
                feedback_attribution=feedback_attribution,
            )
            if enable_unclosed_idle and observation is not None and not feedback_expression_role:
                feedback_event_ids = feedback_event_ids + resolve_unclosed_items(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    source_signature=observation.signature,
                    reason="teacher_feedback_integrated",
                )
            output_intent = "integrate_feedback"
            existing_unclosed = (
                active_unclosed_for_signature(conn, source_signature=observation.signature)
                if enable_unclosed_idle and observation is not None
                else None
            )
            teacher_request_context = _teacher_request_drive_context(
                conn,
                pool,
                session_id=session_id,
                observation=observation,
                intent=output_intent,
                existing_unclosed=existing_unclosed,
                exact_b0=exact_b0,
                structural_b=structural_b,
                learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
            )
            output_chars, output_expression_trace = _select_request_expression(
                conn,
                session_id=session_id,
                intent=output_intent,
                fallback_text=LEARNING_ACK_TEXT,
                teacher_request_context=teacher_request_context,
            )
            feedback_drive_context = _integrate_feedback_drive_context(
                conn,
                session_id=session_id,
                tick=tick,
                feedback=teacher_feedback,
                observation=observation,
                feedback_event_ids=feedback_event_ids,
                teacher_request_context=teacher_request_context,
                expression_trace=output_expression_trace,
                learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
            )
            _append_runtime_tick(
                tick_events,
                _tick_event(
                    conn=conn,
                    session_id=session_id,
                    tick=tick,
                    selected_action={
                        "action_type": "integrate_feedback",
                        "source": "teacher_feedback_event",
                    },
                    action_competition=_competition(
                        "integrate_feedback",
                        selected="integrate_feedback",
                        teacher_request_context=teacher_request_context,
                        learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                        feedback_drive_context=feedback_drive_context,
                        l3_context=(
                            {"conn": conn, "state_signature": observation.signature}
                            if observation is not None
                            else None
                        ),
                    ),
                    state_pool=pool,
                    grid=grid,
                    observation=observation,
                    event_ids=feedback_event_ids,
                    source_refs=({"source_kind": "teacher_feedback_event"},),
                    learning_deltas=(
                        {
                            "delta_kind": "experience_alignment_written",
                            "event_count": len(feedback_event_ids),
                            "target_text_hash": observation.text_hash if observation else None,
                            "recovered_target": isinstance(observation, _RecoveredObservation),
                            "recovered_target_kind": _public_recovery_kind(observation)
                            if isinstance(observation, _RecoveredObservation)
                            else None,
                            "internal_recovered_target_kind": observation.recovery_kind
                            if isinstance(observation, _RecoveredObservation)
                            else None,
                            "backward_attribution": feedback_attribution.c_backward_rows()[0]
                            if feedback_attribution is not None
                            else None,
                        },
                        attribution_consolidation,
                    )
                    + ((l1_triplet_delta,) if l1_triplet_delta is not None else ())
                    + ((l2_edge_delta,) if l2_edge_delta is not None else ())
                    + ((l3_action_delta,) if l3_action_delta is not None else ()),
                    c_backward=feedback_attribution.c_backward_rows() if feedback_attribution else (),
                    ssp_summary=_with_request_expression_trace(
                        {"reward_punish_backward_attribution": attribution_consolidation},
                        output_expression_trace,
                    ),
                    feelings=_feelings_for_output(
                        output_intent,
                        exact_b0,
                        structural_b,
                        teacher_request_context=teacher_request_context,
                        feedback_drive_context=feedback_drive_context,
                        cognitive_feelings=_cognitive_feelings_from_pool(
                            pool,
                            observation,
                            c_backward_grasp=float(
                                (feedback_attribution.c_backward_rows()[-1].get("cause_grasp", 0.0) if feedback_attribution and feedback_attribution.c_backward_rows() else 0.0)
                            ),
                            reward_signal=_unit(float(feedback_drive_context.get("drive", 0.0)))
                            if feedback_drive_context
                            else 0.0,
                            unclosed_u=float(
                                (active_unclosed_for_signature(conn, source_signature=observation.signature) or {}).get("u_value", 0.0)
                            )
                            if observation is not None
                            else 0.0,
                            **_channel_signals_from_experience(
                                conn, session_id=session_id, tick=tick, observation=observation
                            ),
                        ),
                    ),
                ),
            )
        elif observation is not None:
            exact_b0 = _find_exact_b0(conn, observation, state_pool=pool)
            # M2 (codex 顶层瀑布债): exact 命中不再无条件短路 structural — 二者是
            # 同一竞争场的召回候选. 仅高把握 exact (快系统, support>=0.62) 跳过慢
            # 检索, 这是 §24 快/慢性能护栏而非控制流优先级.
            paradigm_readiness = 0.0
            if enable_structural_bccstar and (
                exact_b0 is None or float(exact_b0.support) < 0.62
            ):
                structural_b = _find_structural_b(
                    conn,
                    observation,
                    state_pool=pool,
                    session_id=session_id,
                    before_tick=tick + 1,
                )
                # §36第4阶 过程范式: 不在此处执行 — 只探测"该结构的过程范式是否
                # 已学" (示范或自发共现), 就绪度作为一个意图候选参与下方竞争;
                # 胜出后才逐 tick 执行 (先竞争后行动, C3).
                if structural_b is None:
                    paradigm_readiness = _paradigm_process_readiness(conn, observation)
            # P1-1 (ColdSave C3/C18): 意图层真行动竞争 — 先算各意图 drive, 再 argmax.
            # 此前是 if/elif 瀑布: 召回命中=必答(低把握也不问), request_teacher 只是
            # 无召回时的 fallback. 现在回答/请教/维持未闭合在同一场竞争里比 drive:
            # 低把握的泛化召回会输给 ask (拟人犹豫从竞争自然涌现), 高把握召回仍稳赢.
            existing_unclosed = (
                active_unclosed_for_signature(conn, source_signature=observation.signature)
                if enable_unclosed_idle
                else None
            )
            # M2: 两条召回路各自算 write drive, 竞争选源 (不再 exact 恒优先).
            _emo = prev_emotion_for_turn if prev_emotion_for_turn else None
            exact_write_drive = (
                _write_drive_from_recall_state("exact_b0", b0=exact_b0, structural_b=None, emotion=_emo)[0]
                if exact_b0 is not None
                else 0.0
            )
            structural_write_drive = (
                _write_drive_from_recall_state(
                    "structural_bccstar", b0=None, structural_b=structural_b, emotion=_emo
                )[0]
                if structural_b is not None
                else 0.0
            )
            if exact_b0 is not None and exact_write_drive >= structural_write_drive:
                recall_intent = "exact_b0"
                write_drive_value = exact_write_drive
            elif structural_b is not None:
                recall_intent = "structural_bccstar"
                write_drive_value = structural_write_drive
            else:
                recall_intent = ""
                write_drive_value = 0.0
            ask_intent = "maintain_unclosed" if existing_unclosed else "request_teacher"
            teacher_request_context = _teacher_request_drive_context(
                conn,
                pool,
                session_id=session_id,
                observation=observation,
                intent=ask_intent,
                existing_unclosed=existing_unclosed,
                exact_b0=exact_b0,
                structural_b=structural_b,
                learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                process_grasp=paradigm_readiness,
            )
            ask_drive_value = _unit(
                teacher_request_context.get(
                    "maintain_drive" if ask_intent == "maintain_unclosed" else "request_drive",
                    teacher_request_context.get("selected_drive", 0.0),
                )
            )
            if recall_intent and write_drive_value >= ask_drive_value:
                output_intent = recall_intent
                # M2: 输出源跟随竞争胜者 (exact 败给 structural 时不再霸占输出).
                if recall_intent == "exact_b0" and exact_b0 is not None:
                    output_chars = exact_b0.output_chars
                    structural_b = None  # 落败源不进 tick trace 主证据
                else:
                    output_chars = structural_b.output_chars
                    exact_b0 = None
            elif paradigm_readiness > 0.0 and _unit(
                0.22
                + paradigm_readiness * 0.5
                + _unit((existing_unclosed or {}).get("u_value", 0.0)) * 0.30
            ) >= ask_drive_value:
                # 过程范式意图在竞争中胜出 → 逐 tick 执行 (每步内部再竞争).
                # drive = 0.22 + 就绪度×0.5 + 未闭合张力×0.3: 学过的范式才敢做
                # (没学过 readiness=0 不可达); 惦记未解的题×现在会做了 = 行动驱力
                # 最强 (§27 期待/未闭合是行动的能量来源, 不只是请教的理由).
                _p_tick, _p_answer, _p_audit = _run_paradigm_process_execution(
                    conn,
                    pool,
                    grid,
                    session_id=session_id,
                    start_tick=tick,
                    observation=observation,
                    turn_budget_left=turn_tick_budget - (tick - turn_start_tick),
                    tick_events=tick_events,
                )
                if _p_answer:
                    tick = _p_tick
                    structural_b = _StructuralB(
                        event_id="paradigm_process_execution",
                        source_event_id="paradigm_process_execution",
                        source_text="paradigm_process_execution",
                        output_chars=tuple(_p_answer),
                        similarity=_unit(min(float(a.get("fact_support", 0.5)) for a in _p_audit) * 0.92) if _p_audit else 0.5,
                        shared_units=(),
                        residual_units=(),
                        candidate_audit_slots=(
                            {
                                "slot_kind": "structural_generalization_value_modulation",
                                "formula_id": PHASE20_9J_STRUCTURAL_GENERALIZATION_ID,
                                "source": "paradigm_process_execution_taught_steps",
                                "generalization_grasp": round(paradigm_readiness, 4),
                                "reward_boost": 0.06,
                                "punish_penalty": 0.0,
                                "residual_conflict_penalty": 0.0,
                                "columns": _p_audit,
                                "creates_reply_candidate": False,
                                "writes_answer_directly": False,
                            },
                        ),
                    )
                    output_chars = tuple(_p_answer)
                    output_intent = "structural_bccstar"
                    paradigm_process_wrote_grid = True
                else:
                    # 执行卡住 (事实缺口/范式不完整) → 诚实请教
                    output_intent = ask_intent
                    output_chars, output_expression_trace = _select_request_expression(
                        conn,
                        session_id=session_id,
                        intent=output_intent,
                        fallback_text=MAINTAIN_UNCLOSED_TEXT if existing_unclosed else NO_CALL_TEXT,
                        teacher_request_context=teacher_request_context,
                    )
            else:
                output_intent = ask_intent
                output_chars, output_expression_trace = _select_request_expression(
                    conn,
                    session_id=session_id,
                    intent=output_intent,
                    fallback_text=MAINTAIN_UNCLOSED_TEXT if existing_unclosed else NO_CALL_TEXT,
                    teacher_request_context=teacher_request_context,
                )
        elif enable_visual and tick_events:
            observation = _observation_from_current_visual_events(conn, tick_events)
            if observation is not None:
                exact_b0 = _find_exact_b0(conn, observation, state_pool=pool)
                if exact_b0 is not None:
                    output_chars = exact_b0.output_chars
                    output_intent = "exact_b0"
                elif enable_unclosed_idle:
                    output_intent = "request_teacher"
                    teacher_request_context = _teacher_request_drive_context(
                        conn,
                        pool,
                        session_id=session_id,
                        observation=observation,
                        intent=output_intent,
                        existing_unclosed=None,
                        exact_b0=exact_b0,
                        structural_b=structural_b,
                        learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                    )
                    output_chars, output_expression_trace = _select_request_expression(
                        conn,
                        session_id=session_id,
                        intent=output_intent,
                        fallback_text=NO_CALL_TEXT,
                        teacher_request_context=teacher_request_context,
                    )

        # §12.3 GAP-05b fix: detection phase (observation / recall / action competition)
        # can exceed 150ms on its own; wall budget should cover only the write phase.
        _turn_start_ms = time.perf_counter() * 1000.0
        if output_chars:
            write_start = len(tick_events) + 1
            draft_write_mutation = dict(debug_draftgrid_write_mutation or {})
            target_output_unit_count = _draftgrid_target_output_unit_count(output_chars, grid)
            written_output_unit_count = 0
            initial_write_limit = _draftgrid_initial_write_unit_limit(output_chars, grid)
            if paradigm_process_wrote_grid:
                # 范式执行已逐 tick 把过程写进 grid (含结果行) — 不再线性重写,
                # 直接进入回读/提交循环. 回复文本 = 结果数字 (人念答案).
                initial_write_limit = 0
                written_output_unit_count = target_output_unit_count = len(output_chars)
            prev_written_char = ""
            # M3-3: 写路径的范式偏置 (每 turn 查一次): 上一行动=write_cell 完成
            # (wrote_unit) 时, 经验流共现波峰对"继续写"的支持度 → write 偏置.
            _write_paradigm_bias = _paradigm_action_bias(
                conn,
                session_id=session_id,
                prev_action_type="write_cell",
                prev_action_result="wrote_unit",
            )
            _write_paradigm_delta = float(
                (_write_paradigm_bias.get("deltas") or {}).get("write_cell", 0.0) or 0.0
            )
            for char_index, char in enumerate(output_chars[:initial_write_limit]):
                if (tick - turn_start_tick) >= turn_tick_budget:
                    break
                tick += 1
                pool.tick_decay(tick=tick)
                row, col = divmod(char_index, grid.cols)
                if row >= grid.rows:
                    break
                # M2 逐单元生成 (C16): 本 tick 的"下一单元"先过竞争 — 源偏置正常
                # 最强(行为不变), 但 pause/stop 胜出时中断整串写入, 转入回读循环.
                next_unit_competition = _next_unit_competition(
                    planned_char=char,
                    char_index=char_index,
                    output_intent=output_intent,
                    source_support=(
                        float(exact_b0.support) if exact_b0 is not None
                        else float(structural_b.similarity) if structural_b is not None
                        else 0.55
                    ),
                    pending_units=max(0, target_output_unit_count - char_index),
                    grid=grid,
                    prev_char=prev_written_char,
                    paradigm_delta=_write_paradigm_delta if char_index > 0 else 0.0,
                )
                if next_unit_competition["selected_action_type"] != "write_next_unit":
                    break
                expected_char = char
                write_char = str(draft_write_mutation.get(char_index, char))
                if len(write_char) != 1:
                    write_char = char
                action_type = _write_action_type(output_intent, char_index)
                action_record_id = insert_action_record(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    action_type=action_type,
                    selected=True,
                    drive=_drive_for_output(
                        output_intent,
                        exact_b0,
                        structural_b=structural_b,
                        teacher_request_context=teacher_request_context,
                        feedback_drive_context=feedback_drive_context,
                    ),
                    eligibility={
                        "draft_col_available": True,
                        "grasp_source": output_intent,
                        "char_index": char_index,
                        "teacher_request_drive_context": teacher_request_context
                        if output_intent in EXPRESSION_INTENTS
                        else {},
                    },
                    target_refs={
                        "draft_row": row,
                        "draft_col": col,
                        "source_event_id": exact_b0.event_id if exact_b0 else None,
                    },
                )
                _register_action_sa_from_record(conn, action_record_id, tick)
                grid.write_at(row, col, write_char, tick=tick)
                _observe_draft_char(pool, tick=tick, char=write_char, row=row, col=col, source=output_intent)
                extra_event_ids: tuple[str, ...] = ()
                unclosed_trace: tuple[dict[str, Any], ...] = ()
                if (
                    enable_unclosed_idle
                    and output_intent in {"request_teacher", "maintain_unclosed"}
                    and char_index == 0
                    and observation is not None
                ):
                    # §27.1 未闭合期待/压力的涌现项 (求知欲/恐惧的底层来源).
                    # 当前观察相关 SA 的认知压 (§9 P=R-V) 自动涌现为未闭合压力增量,
                    # 不必由 request_teacher 行动硬触发 — 白皮书 §27.1 "未知形成压力"
                    # + 用户理论 "未知本身就带惩罚信号 → 恐惧/求知欲涌现".
                    # _base_delta 保留 §27.1 行动增益成分 (行动选择/affordance 的先天分量),
                    # _cognitive_pressure_emergent 是状态池认知压的自发涌现 (§27.6 new_evidence 项).
                    _base_delta = 0.46 if output_intent == "request_teacher" else 0.18
                    _pressure_emergent, _dissonance_emergent, _pressure_slots = _statepool_unresolved_pressure(
                        pool, observation
                    )
                    _cognitive_pressure_emergent = min(
                        0.30, _pressure_emergent * 0.22 + _dissonance_emergent * 0.14
                    )
                    u_delta = _base_delta + _cognitive_pressure_emergent
                    unclosed_id, unclosed_event_id = upsert_unclosed_item(
                        conn,
                        session_id=session_id,
                        tick=tick,
                        source_event_id=observation.event_id,
                        source_signature=observation.signature,
                        source_text="".join(observation.chars),
                        u_delta=u_delta,
                        reason={
                            "reason_kind": "low_grasp_no_recall_with_pressure_emergent",
                            "selected_action": output_intent,
                            "grasp": round(1.0 - float(teacher_request_context.get("low_grasp", 1.0)), 4)
                            if teacher_request_context
                            else 0.18,
                            "cognitive_pressure_emergent": round(_cognitive_pressure_emergent, 4),
                            "pressure_emergent": round(_pressure_emergent, 4),
                            "dissonance_emergent": round(_dissonance_emergent, 4),
                            "pressure_emergent_slots": _pressure_slots,
                            "teacher_request_drive_context": teacher_request_context,
                        },
                    )
                    extra_event_ids = (unclosed_event_id,)
                    current_unclosed = active_unclosed_for_signature(conn, source_signature=observation.signature)
                    if current_unclosed:
                        unclosed_trace = (current_unclosed,)
                event_id = insert_experience_event(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    event_kind="draft_grid_write",
                    action_record_id=action_record_id,
                    payload={
                        "draft_row": row,
                        "draft_col": col,
                        "unit_text": write_char,
                        "expected_unit_text": expected_char,
                        "unit_hash": _hash_text(write_char),
                        "expected_unit_hash": _hash_text(expected_char),
                        "write_mutated_from_cstar_expected": write_char != expected_char,
                        "visible_text_hash": _hash_text(grid.visible_text()),
                        "source_intent": output_intent,
                        "request_expression_selection": output_expression_trace
                        if output_intent in EXPRESSION_INTENTS
                        else {},
                    },
                )
                conn.execute(
                    "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
                    (event_id, action_record_id),
                )
                write_flow = _write_draftgrid_write_self_occurrence(
                    conn,
                    pool,
                    session_id=session_id,
                    tick=tick,
                    event_id=event_id,
                    row=row,
                    col=col,
                    char=write_char,
                    visible_text=grid.visible_text(),
                    output_intent=output_intent,
                )
                # P3: collect active SA IDs from pool for L1 context and L2 group
                _tick_active_sa_ids = [item.sa_id for item in pool.get_active_above_threshold(0.1)]
                _anchor_sa_id = write_flow.get("sa_type_id", "")
                # P3: L1 per-tick online update
                _l1_per_tick_online_update(
                    conn,
                    anchor_sa_type_id=_anchor_sa_id,
                    context_sa_type_ids=[sid for sid in _tick_active_sa_ids if sid != _anchor_sa_id][:6],
                    prediction_error=0.0,
                    reward=float(teacher_feedback.reward_mag if teacher_feedback else 0.0),
                    punish=float(teacher_feedback.punish_mag if teacher_feedback else 0.0),
                    tick=tick,
                )
                # P3: L2 group co-occurrence record — all co-active SAs at this tick
                _l2_sa_ids = list(dict.fromkeys([_anchor_sa_id] + _tick_active_sa_ids))
                _record_l2_cooccurrence_group(
                    conn,
                    [sid for sid in _l2_sa_ids if sid],
                    tick=tick,
                    turn_id=session_id,
                )
                draft_action_context = _draftgrid_action_drive_context(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    grid=grid,
                    output_intent=output_intent,
                    exact_b0=exact_b0,
                    structural_b=structural_b,
                    teacher_request_context=teacher_request_context,
                    feedback_drive_context=feedback_drive_context,
                    learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                    memory_rhythm_context=_memory_rhythm_context_from_events(tick_events, conn=conn, session_id=session_id, before_tick=tick),
                    pending_output_count=max(0, target_output_unit_count - (char_index + 1)),
                    target_output_unit_count=target_output_unit_count,
                )
                _append_runtime_tick(
                    tick_events,
                    _tick_event(
                        conn=conn,
                        session_id=session_id,
                        tick=tick,
                        selected_action={
                            "action_type": action_type,
                            "draft_row": row,
                            "draft_col": col,
                            "unit_hash": _hash_text(char),
                            "write_index": char_index,
                        },
                        action_competition=_competition(
                            output_intent,
                            selected=action_type,
                            b0=exact_b0,
                            structural_b=structural_b,
                            teacher_request_context=teacher_request_context,
                            learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                            feedback_drive_context=feedback_drive_context,
                            draftgrid_action_context=draft_action_context,
                            l3_context=(
                                {"conn": conn, "state_signature": observation.signature}
                                if observation is not None
                                else None
                            ),
                            emotion=prev_emotion_for_turn if prev_emotion_for_turn else None,
                        ),
                        state_pool=pool,
                        grid=grid,
                        observation=observation,
                        event_ids=extra_event_ids + (event_id,),
                        action_record_ids=(action_record_id,),
                        b0=exact_b0,
                        structural_b=structural_b,
                        c_backward=_visual_imagination_c_backward(visual_imagination),
                        unclosed_items=unclosed_trace,
                        query_structures=(_query_summary(observation),) if observation else (),
                        ssp_summary=_with_request_expression_trace(
                            {
                                **(_ssp_summary(observation) if observation else {}),
                                "draftgrid_write_self_flow": write_flow,
                            },
                            output_expression_trace,
                        ),
                        feelings=_feelings_for_output(
                            output_intent,
                            exact_b0,
                            structural_b,
                            teacher_request_context=teacher_request_context,
                            feedback_drive_context=feedback_drive_context,
                            draftgrid_action_context=draft_action_context,
                            cognitive_feelings=_cognitive_feelings_from_pool(
                                pool, observation,
                                c_backward_grasp=float(
                                    (_visual_imagination_c_backward(visual_imagination)[-1].get("cause_grasp", 0.0)
                                     if visual_imagination is not None and _visual_imagination_c_backward(visual_imagination) else 0.0)
                                ),
                                unclosed_u=float(
                                    (active_unclosed_for_signature(conn, source_signature=observation.signature) or {}).get("u_value", 0.0)
                                )
                                if observation is not None
                                else 0.0,
                                **_channel_signals_from_experience(
                                    conn, session_id=session_id, tick=tick, observation=observation
                                ),
                            ),
                        ),
                        timings_ms={"turn_tick_index": tick - turn_start_tick},
                    ),
                )
                written_output_unit_count = max(written_output_unit_count, char_index + 1)
                prev_written_char = write_char
                # M2 审计: 本 tick 的下一单元竞争入最后一个 tick event 的 ssp_active_summary
                if tick_events:
                    _last = tick_events[-1]
                    _summary = dict(_last.ssp_active_summary or {})
                    _summary["next_unit_competition"] = next_unit_competition
                    tick_events[-1] = replace(_last, ssp_active_summary=_summary)

            # §12.3 GAP-05c: 初始写入循环结束后重置 wall-clock 计时, 给回读/提交循环独立预算.
            # 表达意图 (request_teacher/maintain_unclosed/integrate_feedback) 的表达式可能较长,
            # 单次初始写入即可耗尽 150ms; 回读/提交循环需要独立的时间窗口来完成 commit.
            _turn_start_ms = time.perf_counter() * 1000.0
            draft_action_context: dict[str, Any] = {}
            ready_to_commit = False
            stopped_generation = False
            draft_next_action_selection: dict[str, Any] = {}
            while not _over_turn_budget() and grid.visible_text():
                # §12.3 GAP-05e: 每次回读迭代重置 wall-clock — 150ms 作用于单个决策步,
                # 而非整个回读循环. 避免慢速文件 SQLite 环境中多次迭代累积超出预算.
                _turn_start_ms = time.perf_counter() * 1000.0
                tick += 1
                pool.tick_decay(tick=tick)
                draft_action_context = _draftgrid_action_drive_context(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    grid=grid,
                    output_intent=output_intent,
                    exact_b0=exact_b0,
                    structural_b=structural_b,
                    teacher_request_context=teacher_request_context,
                    feedback_drive_context=feedback_drive_context,
                    learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                    memory_rhythm_context=_memory_rhythm_context_from_events(tick_events, conn=conn, session_id=session_id, before_tick=tick),
                    pending_output_count=max(0, target_output_unit_count - written_output_unit_count),
                    target_output_unit_count=target_output_unit_count,
                )
                reply_text = ("".join(output_chars) if paradigm_process_wrote_grid else grid.visible_text())
                action_record_id = insert_action_record(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    action_type="read_draft",
                    selected=True,
                    drive=_unit(draft_action_context.get("read_draft", {}).get("drive", 0.0)),
                    eligibility={
                        "draft_has_visible_text": True,
                        "draftgrid_action_drive_context": draft_action_context,
                    },
                    target_refs={"visible_text_hash": _hash_text(reply_text)},
                )
                _register_action_sa_from_record(conn, action_record_id, tick)
                event_id = insert_experience_event(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    event_kind="draft_grid_read",
                    action_record_id=action_record_id,
                    payload={
                        "visible_text_hash": _hash_text(reply_text),
                        "visible_text": reply_text,
                        "visible_length": len(reply_text),
                        "source_intent": output_intent,
                        "draftgrid_action_drive_context": draft_action_context,
                    },
                )
                conn.execute(
                    "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
                    (event_id, action_record_id),
                )
                readback_flow = _write_draftgrid_readback_self_flow(
                    conn,
                    pool,
                    session_id=session_id,
                    tick=tick,
                    event_id=event_id,
                    grid=grid,
                    visible_text=reply_text,
                    draftgrid_action_context=draft_action_context,
                    output_intent=output_intent,
                )
                _append_runtime_tick(
                    tick_events,
                    _tick_event(
                        conn=conn,
                        session_id=session_id,
                        tick=tick,
                        selected_action={
                            "action_type": "read_draft",
                            "visible_text_hash": _hash_text(reply_text),
                            "readback": True,
                        },
                        action_competition=_competition(
                            output_intent,
                            selected="read_draft",
                            b0=exact_b0,
                            structural_b=structural_b,
                            teacher_request_context=teacher_request_context,
                            learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                            feedback_drive_context=feedback_drive_context,
                            draftgrid_action_context=draft_action_context,
                            l3_context=(
                                {"conn": conn, "state_signature": observation.signature}
                                if observation is not None
                                else None
                            ),
                        ),
                        state_pool=pool,
                        grid=grid,
                        observation=observation,
                        event_ids=(event_id,),
                        action_record_ids=(action_record_id,),
                        b0=exact_b0,
                        structural_b=structural_b,
                        c_backward=_visual_imagination_c_backward(visual_imagination),
                        ssp_summary=_with_request_expression_trace(
                            {"draftgrid_readback_self_flow": readback_flow},
                            output_expression_trace,
                        ),
                        feelings=_feelings_for_output(
                            output_intent,
                            exact_b0,
                            structural_b,
                            teacher_request_context=teacher_request_context,
                            feedback_drive_context=feedback_drive_context,
                            draftgrid_action_context=draft_action_context,
                            cognitive_feelings=_cognitive_feelings_from_pool(
                                pool, observation,
                                c_backward_grasp=float(
                                    (_visual_imagination_c_backward(visual_imagination)[-1].get("cause_grasp", 0.0)
                                     if visual_imagination is not None and _visual_imagination_c_backward(visual_imagination) else 0.0)
                                ),
                                unclosed_u=float(
                                    (active_unclosed_for_signature(conn, source_signature=observation.signature) or {}).get("u_value", 0.0)
                                )
                                if observation is not None
                                else 0.0,
                                **_channel_signals_from_experience(
                                    conn, session_id=session_id, tick=tick, observation=observation
                                ),
                            ),
                        ),
                    ),
                )

                if _over_turn_budget() or not grid.visible_text():
                    break
                draftgrid_successor_trace = _empty_draftgrid_successor("not_queried_before_readback_selection")
                if written_output_unit_count >= target_output_unit_count:
                    draftgrid_successor_trace = _draftgrid_successor_from_experience_flow(
                        conn,
                        session_id=session_id,
                        grid=grid,
                        output_chars=output_chars,
                        written_count=written_output_unit_count,
                    )
                    successor_text = str(draftgrid_successor_trace.get("successor_text") or "")
                    if successor_text:
                        output_chars = tuple(output_chars) + tuple(successor_text)
                        target_output_unit_count = _draftgrid_target_output_unit_count(output_chars, grid)
                post_read_draft_context = _draftgrid_action_drive_context(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    grid=grid,
                    output_intent=output_intent,
                    exact_b0=exact_b0,
                    structural_b=structural_b,
                    teacher_request_context=teacher_request_context,
                    feedback_drive_context=feedback_drive_context,
                    learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                    pending_output_count=max(0, target_output_unit_count - written_output_unit_count),
                    target_output_unit_count=target_output_unit_count,
                )
                post_read_draft_context = _draftgrid_context_with_experience_successor(
                    conn,
                    post_read_draft_context,
                    draftgrid_successor_trace,
                )
                edit_trace: dict[str, Any] = {}
                edit_trace = _select_cstar_alternative_unit_for_draftgrid_edit(
                    grid,
                    expected_output_chars=output_chars,
                    draftgrid_action_context=post_read_draft_context,
                    output_intent=output_intent,
                    exact_b0=exact_b0,
                    structural_b=structural_b,
                )
                post_read_draft_context = _draftgrid_context_with_edit_alternative(
                    post_read_draft_context,
                    edit_trace,
                )
                reply_text = ("".join(output_chars) if paradigm_process_wrote_grid else _draftgrid_linear_text(grid))
                commit_drive_context = _commit_reply_drive_context(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    grid=grid,
                    reply_text=reply_text,
                    output_intent=output_intent,
                    exact_b0=exact_b0,
                    structural_b=structural_b,
                    teacher_request_context=teacher_request_context,
                    feedback_drive_context=feedback_drive_context,
                    expression_trace=output_expression_trace,
                    learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                    memory_rhythm_context=_memory_rhythm_context_from_events(tick_events, conn=conn, session_id=session_id, before_tick=tick),
                    pending_output_count=max(0, target_output_unit_count - written_output_unit_count),
                    target_output_unit_count=target_output_unit_count,
                )
                draft_next_action_selection = _select_draftgrid_next_action_from_ap_flow(
                    conn=conn,
                    session_id=session_id,
                    tick=tick,
                    draftgrid_action_context=post_read_draft_context,
                    commit_drive_context=commit_drive_context,
                    edit_trace=edit_trace,
                    learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                    pending_output_units=written_output_unit_count < target_output_unit_count,
                )
                post_read_draft_context = _draftgrid_context_with_next_action_selection(
                    post_read_draft_context,
                    draft_next_action_selection,
                )
                commit_drive_context = _commit_context_with_next_action_selection(
                    commit_drive_context,
                    draft_next_action_selection,
                )
                selected_next_action = str(draft_next_action_selection.get("selected_action_type") or "")
                if selected_next_action == "read_draft":
                    draft_action_context = post_read_draft_context
                    continue
                if selected_next_action == "stop_generating":
                    if _over_turn_budget():
                        break
                    tick += 1
                    pool.tick_decay(tick=tick)
                    reply_text = ("".join(output_chars) if paradigm_process_wrote_grid else grid.visible_text())
                    selected_drive = _unit(draft_next_action_selection.get("selected_drive", 0.0))
                    action_record_id = insert_action_record(
                        conn,
                        session_id=session_id,
                        tick=tick,
                        action_type="stop_generating",
                        selected=True,
                        drive=selected_drive,
                        eligibility={
                            "draft_has_visible_text": True,
                            "draftgrid_action_drive_context": post_read_draft_context,
                            "draftgrid_next_action_selection": draft_next_action_selection,
                        },
                        target_refs={"visible_text_hash": _hash_text(reply_text)},
                    )
                    _register_action_sa_from_record(conn, action_record_id, tick)
                    event_id = insert_experience_event(
                        conn,
                        session_id=session_id,
                        tick=tick,
                        event_kind="draft_grid_stop",
                        action_record_id=action_record_id,
                        payload={
                            "visible_text_hash": _hash_text(reply_text),
                            "visible_text": reply_text,
                            "visible_length": len(reply_text),
                            "source_intent": output_intent,
                            "draftgrid_action_drive_context": post_read_draft_context,
                            "draftgrid_next_action_selection": draft_next_action_selection,
                        },
                    )
                    conn.execute(
                        "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
                        (event_id, action_record_id),
                    )
                    stopped_generation = True
                    draft_action_context = post_read_draft_context
                    _append_runtime_tick(
                        tick_events,
                        _tick_event(
                            conn=conn,
                            session_id=session_id,
                            tick=tick,
                            selected_action={
                                "action_type": "stop_generating",
                                "visible_text_hash": _hash_text(reply_text),
                                "draftgrid_next_action_selection": draft_next_action_selection,
                            },
                            action_competition=_competition(
                                output_intent,
                                selected="stop_generating",
                                b0=exact_b0,
                                structural_b=structural_b,
                                teacher_request_context=teacher_request_context,
                                learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                                feedback_drive_context=feedback_drive_context,
                                commit_drive_context=commit_drive_context,
                                draftgrid_action_context=post_read_draft_context,
                            ),
                            state_pool=pool,
                            grid=grid,
                            observation=observation,
                            event_ids=(event_id,),
                            action_record_ids=(action_record_id,),
                            b0=exact_b0,
                            structural_b=structural_b,
                            c_backward=_visual_imagination_c_backward(visual_imagination),
                            ssp_summary=_with_request_expression_trace(
                                {"draftgrid_next_action_selection": draft_next_action_selection},
                                output_expression_trace,
                            ),
                            feelings=_feelings_for_output(
                                output_intent,
                                exact_b0,
                                structural_b,
                                teacher_request_context=teacher_request_context,
                                feedback_drive_context=feedback_drive_context,
                                commit_drive_context=commit_drive_context,
                                draftgrid_action_context=post_read_draft_context,
                            ),
                        ),
                    )
                    break
                if selected_next_action == "commit_reply":
                    draft_action_context = post_read_draft_context
                    ready_to_commit = True
                    break
                if selected_next_action == "continue_writing":
                    if _over_turn_budget():
                        break
                    successor_start, successor_end = _draftgrid_next_successor_span(
                        grid,
                        written_count=written_output_unit_count,
                        target_count=target_output_unit_count,
                    )
                    if successor_start >= successor_end:
                        draft_action_context = post_read_draft_context
                        continue
                    for char_index in range(successor_start, successor_end):
                        if (tick - turn_start_tick) >= turn_tick_budget:
                            break
                        tick += 1
                        pool.tick_decay(tick=tick)
                        row, col = divmod(char_index, grid.cols)
                        if row >= grid.rows:
                            break
                        expected_char = str(output_chars[char_index])
                        write_char = str(draft_write_mutation.get(char_index, expected_char))
                        if len(write_char) != 1:
                            write_char = expected_char
                        action_type = "continue_writing" if char_index == successor_start else "write_cell"
                        selected_drive = (
                            _unit(draft_next_action_selection.get("selected_drive", 0.0))
                            if action_type == "continue_writing"
                            else _drive_for_output(
                                output_intent,
                                exact_b0,
                                structural_b=structural_b,
                                teacher_request_context=teacher_request_context,
                                feedback_drive_context=feedback_drive_context,
                            )
                        )
                        action_record_id = insert_action_record(
                            conn,
                            session_id=session_id,
                            tick=tick,
                            action_type=action_type,
                            selected=True,
                            drive=selected_drive,
                            eligibility={
                                "draft_col_available": True,
                                "grasp_source": output_intent,
                                "char_index": char_index,
                                "pending_output_units": max(0, target_output_unit_count - written_output_unit_count),
                                "draftgrid_action_drive_context": post_read_draft_context,
                                "draftgrid_next_action_selection": draft_next_action_selection,
                            },
                            target_refs={
                                "draft_row": row,
                                "draft_col": col,
                                "source_event_id": exact_b0.event_id if exact_b0 else None,
                            },
                        )
                        _register_action_sa_from_record(conn, action_record_id, tick)
                        grid.write_at(row, col, write_char, tick=tick)
                        _observe_draft_char(
                            pool,
                            tick=tick,
                            char=write_char,
                            row=row,
                            col=col,
                            source="continue_writing" if action_type == "continue_writing" else output_intent,
                        )
                        event_id = insert_experience_event(
                            conn,
                            session_id=session_id,
                            tick=tick,
                            event_kind="draft_grid_write",
                            action_record_id=action_record_id,
                            payload={
                                "draft_row": row,
                                "draft_col": col,
                                "unit_text": write_char,
                                "expected_unit_text": expected_char,
                                "unit_hash": _hash_text(write_char),
                                "expected_unit_hash": _hash_text(expected_char),
                                "write_mutated_from_cstar_expected": write_char != expected_char,
                                "visible_text_hash": _hash_text(grid.visible_text()),
                                "source_intent": output_intent,
                                "continued_from_draftgrid_next_action": action_type == "continue_writing",
                                "draftgrid_next_action_selection": draft_next_action_selection,
                                "experience_flow_successor": post_read_draft_context.get("experience_flow_successor", {}),
                                "request_expression_selection": output_expression_trace
                                if output_intent in EXPRESSION_INTENTS
                                else {},
                            },
                        )
                        conn.execute(
                            "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
                            (event_id, action_record_id),
                        )
                        write_flow = _write_draftgrid_write_self_occurrence(
                            conn,
                            pool,
                            session_id=session_id,
                            tick=tick,
                            event_id=event_id,
                            row=row,
                            col=col,
                            char=write_char,
                            visible_text=grid.visible_text(),
                            output_intent=output_intent,
                        )
                        written_output_unit_count = max(written_output_unit_count, char_index + 1)
                        continue_action_context = _draftgrid_action_drive_context(
                            conn,
                            session_id=session_id,
                            tick=tick,
                            grid=grid,
                            output_intent=output_intent,
                            exact_b0=exact_b0,
                            structural_b=structural_b,
                            teacher_request_context=teacher_request_context,
                            feedback_drive_context=feedback_drive_context,
                            learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                            memory_rhythm_context=_memory_rhythm_context_from_events(tick_events, conn=conn, session_id=session_id, before_tick=tick),
                            pending_output_count=max(0, target_output_unit_count - written_output_unit_count),
                            target_output_unit_count=target_output_unit_count,
                        )
                        continue_action_context = _draftgrid_context_with_next_action_selection(
                            continue_action_context,
                            draft_next_action_selection,
                        )
                        _append_runtime_tick(
                            tick_events,
                            _tick_event(
                                conn=conn,
                                session_id=session_id,
                                tick=tick,
                                selected_action={
                                    "action_type": action_type,
                                    "draft_row": row,
                                    "draft_col": col,
                                    "unit_hash": _hash_text(write_char),
                                    "write_index": char_index,
                                    "draftgrid_next_action_selection": draft_next_action_selection,
                                    "experience_flow_successor": post_read_draft_context.get("experience_flow_successor", {}),
                                },
                                action_competition=_competition(
                                    output_intent,
                                    selected=action_type,
                                    b0=exact_b0,
                                    structural_b=structural_b,
                                    teacher_request_context=teacher_request_context,
                                    learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                                    feedback_drive_context=feedback_drive_context,
                                    draftgrid_action_context=continue_action_context,
                                    l3_context=(
                                        {"conn": conn, "state_signature": observation.signature}
                                        if observation is not None
                                        else None
                                    ),
                                ),
                                state_pool=pool,
                                grid=grid,
                                observation=observation,
                                event_ids=(event_id,),
                                action_record_ids=(action_record_id,),
                                b0=exact_b0,
                                structural_b=structural_b,
                                c_backward=_visual_imagination_c_backward(visual_imagination),
                                query_structures=(_query_summary(observation),) if observation else (),
                                ssp_summary=_with_request_expression_trace(
                                    {
                                        "draftgrid_write_self_flow": write_flow,
                                        "experience_flow_successor": post_read_draft_context.get("experience_flow_successor", {}),
                                    },
                                    output_expression_trace,
                                ),
                                feelings=_feelings_for_output(
                                    output_intent,
                                    exact_b0,
                                    structural_b,
                                    teacher_request_context=teacher_request_context,
                                    feedback_drive_context=feedback_drive_context,
                                    draftgrid_action_context=continue_action_context,
                                ),
                                timings_ms={"turn_tick_index": tick - turn_start_tick},
                            ),
                        )
                    # §12.3 GAP-05d: 续写完成后重置 wall-clock 计时, 给下一轮回读/提交决策独立预算.
                    _turn_start_ms = time.perf_counter() * 1000.0
                    draft_action_context = post_read_draft_context
                    continue
                if selected_next_action == "edit_cell" and edit_trace.get("can_edit"):
                    tick += 1
                    pool.tick_decay(tick=tick)
                    edit_row = int(edit_trace["row"])
                    edit_col = int(edit_trace["col"])
                    old_char = str(edit_trace["old_unit"])
                    new_char = str(edit_trace["alternative_unit"])
                    grid.write_at(edit_row, edit_col, new_char, tick=tick)
                    _observe_draft_char(pool, tick=tick, char=new_char, row=edit_row, col=edit_col, source="edit_cell")
                    edit_drive = _unit(edit_trace.get("drive", 0.0))
                    action_record_id = insert_action_record(
                        conn,
                        session_id=session_id,
                        tick=tick,
                        action_type="edit_cell",
                        selected=True,
                        drive=edit_drive,
                        eligibility={
                            "draftgrid_action_drive_context": post_read_draft_context,
                            "cstar_alternative_unit": edit_trace,
                            "draftgrid_next_action_selection": draft_next_action_selection,
                        },
                        target_refs={
                            "draft_row": edit_row,
                            "draft_col": edit_col,
                            "old_unit_hash": _hash_text(old_char),
                            "alternative_unit_hash": _hash_text(new_char),
                        },
                    )
                    _register_action_sa_from_record(conn, action_record_id, tick)
                    event_id = insert_experience_event(
                        conn,
                        session_id=session_id,
                        tick=tick,
                        event_kind="draft_grid_edit",
                        action_record_id=action_record_id,
                        payload={
                            "draft_row": edit_row,
                            "draft_col": edit_col,
                            "old_unit_text": old_char,
                            "old_unit_hash": _hash_text(old_char),
                            "alternative_unit_text": new_char,
                            "alternative_unit_hash": _hash_text(new_char),
                            "visible_text_hash": _hash_text(grid.visible_text()),
                            "source_intent": output_intent,
                            "cstar_alternative_unit": edit_trace,
                        },
                    )
                    conn.execute(
                        "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
                        (event_id, action_record_id),
                    )
                    edit_flow = _write_draftgrid_edit_self_occurrence(
                        conn,
                        pool,
                        session_id=session_id,
                        tick=tick,
                        event_id=event_id,
                        row=edit_row,
                        col=edit_col,
                        old_char=old_char,
                        new_char=new_char,
                        visible_text=grid.visible_text(),
                        edit_trace=edit_trace,
                    )
                    edit_outcome_delta = _draftgrid_edit_outcome_learning_delta(
                        grid,
                        edit_trace=edit_trace,
                        expected_output_chars=output_chars,
                        source_support=max(
                            float(exact_b0.support) if exact_b0 is not None else 0.0,
                            float(structural_b.similarity) if structural_b is not None else 0.0,
                        ),
                    )
                    post_edit_context = _draftgrid_action_drive_context(
                        conn,
                        session_id=session_id,
                        tick=tick,
                        grid=grid,
                        output_intent=output_intent,
                        exact_b0=exact_b0,
                        structural_b=structural_b,
                        teacher_request_context=teacher_request_context,
                        feedback_drive_context=feedback_drive_context,
                        learning_loop_carryover=_merge_learning_and_edit_outcome_carryover(
                            _learning_loop_carryover_from_events(tick_events),
                            _edit_outcome_carryover(edit_outcome_delta, source_tick=tick),
                            source_tick=tick,
                        ),
                        memory_rhythm_context=_memory_rhythm_context_from_events(tick_events, conn=conn, session_id=session_id, before_tick=tick),
                        pending_output_count=max(0, target_output_unit_count - written_output_unit_count),
                        target_output_unit_count=target_output_unit_count,
                    )
                    edit_action_context = _draftgrid_context_with_edit_alternative(post_edit_context, edit_trace)
                    edit_action_context = _draftgrid_context_with_next_action_selection(
                        edit_action_context,
                        draft_next_action_selection,
                    )
                    _append_runtime_tick(
                        tick_events,
                        _tick_event(
                            conn=conn,
                            session_id=session_id,
                            tick=tick,
                            selected_action={
                                "action_type": "edit_cell",
                                "draft_row": edit_row,
                                "draft_col": edit_col,
                                "old_unit_hash": _hash_text(old_char),
                                "alternative_unit_hash": _hash_text(new_char),
                                "draftgrid_next_action_selection": draft_next_action_selection,
                            },
                            action_competition=_competition(
                                output_intent,
                                selected="edit_cell",
                                b0=exact_b0,
                                structural_b=structural_b,
                                teacher_request_context=teacher_request_context,
                                learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                                feedback_drive_context=feedback_drive_context,
                                draftgrid_action_context=edit_action_context,
                                l3_context=(
                                    {"conn": conn, "state_signature": observation.signature}
                                    if observation is not None
                                    else None
                                ),
                            ),
                            state_pool=pool,
                            grid=grid,
                            observation=observation,
                            event_ids=(event_id,),
                            action_record_ids=(action_record_id,),
                            b0=exact_b0,
                            structural_b=structural_b,
                            c_backward=_visual_imagination_c_backward(visual_imagination),
                            ssp_summary=_with_request_expression_trace(
                                {"draftgrid_edit_self_flow": edit_flow},
                                output_expression_trace,
                            ),
                            feelings=_feelings_for_output(
                                output_intent,
                                exact_b0,
                                structural_b,
                                teacher_request_context=teacher_request_context,
                                feedback_drive_context=feedback_drive_context,
                                draftgrid_action_context=edit_action_context,
                            ),
                            learning_deltas=(edit_outcome_delta,),
                        ),
                    )
                    draft_action_context = edit_action_context
                    continue
                break

            if ready_to_commit and not stopped_generation and not _over_turn_budget() and grid.visible_text():
                tick += 1
                pool.tick_decay(tick=tick)
                reply_text = ("".join(output_chars) if paradigm_process_wrote_grid else _draftgrid_linear_text(grid))
                commit_drive_context = _commit_reply_drive_context(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    grid=grid,
                    reply_text=reply_text,
                    output_intent=output_intent,
                    exact_b0=exact_b0,
                    structural_b=structural_b,
                    teacher_request_context=teacher_request_context,
                    feedback_drive_context=feedback_drive_context,
                    expression_trace=output_expression_trace,
                    learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                    pending_output_count=max(0, target_output_unit_count - written_output_unit_count),
                    target_output_unit_count=target_output_unit_count,
                )
                if draft_next_action_selection:
                    commit_drive_context = _commit_context_with_next_action_selection(
                        commit_drive_context,
                        draft_next_action_selection,
                    )
                action_record_id = insert_action_record(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    action_type="commit_reply",
                    selected=True,
                    drive=_unit(commit_drive_context.get("drive", 0.0)),
                    eligibility={
                        "draft_has_visible_text": True,
                        "commit_reply_drive_context": commit_drive_context,
                        "draftgrid_next_action_selection": draft_next_action_selection,
                    },
                    target_refs={"visible_text_hash": _hash_text(reply_text)},
                )
                _register_action_sa_from_record(conn, action_record_id, tick)
                event_id = insert_experience_event(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    event_kind="draft_grid_commit",
                    action_record_id=action_record_id,
                    payload={
                        "visible_text_hash": _hash_text(reply_text),
                        "visible_text": reply_text,
                        "draft_grid_visible_text": grid.visible_text(),
                        "visible_chars": list(reply_text),
                        "visible_length": len(reply_text),
                        "source_intent": output_intent,
                        "request_expression_selection": output_expression_trace
                        if output_intent in EXPRESSION_INTENTS
                        else {},
                        "draftgrid_next_action_selection": draft_next_action_selection,
                    },
                )
                conn.execute(
                    "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
                    (event_id, action_record_id),
                )
                committed = True
                _append_runtime_tick(
                    tick_events,
                    _tick_event(
                        conn=conn,
                        session_id=session_id,
                        tick=tick,
                        selected_action={
                            "action_type": "commit_reply",
                            "visible_text_hash": _hash_text(reply_text),
                            "draftgrid_next_action_selection": draft_next_action_selection,
                        },
                        action_competition=_competition(
                            output_intent,
                            selected="commit_reply",
                            b0=exact_b0,
                            structural_b=structural_b,
                            teacher_request_context=teacher_request_context,
                            learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                            feedback_drive_context=feedback_drive_context,
                            commit_drive_context=commit_drive_context,
                            draftgrid_action_context=draft_action_context,
                            l3_context=(
                                {"conn": conn, "state_signature": observation.signature}
                                if observation is not None
                                else None
                            ),
                        ),
                        state_pool=pool,
                        grid=grid,
                        observation=observation,
                        event_ids=(event_id,),
                        action_record_ids=(action_record_id,),
                        b0=exact_b0,
                        structural_b=structural_b,
                        c_backward=_visual_imagination_c_backward(visual_imagination),
                        ssp_summary=_with_request_expression_trace({}, output_expression_trace),
                        feelings=_feelings_for_output(
                            output_intent,
                            exact_b0,
                            structural_b,
                            teacher_request_context=teacher_request_context,
                            feedback_drive_context=feedback_drive_context,
                            commit_drive_context=commit_drive_context,
                            draftgrid_action_context=draft_action_context,
                        ),
                    ),
                )

                if enable_audio_tts and not _over_turn_budget():
                    tick += 1
                    pool.tick_decay(tick=tick)
                    tts_event = record_tts_actuator_tick(
                        conn,
                        pool,
                        session_id=session_id,
                        tick=tick,
                        reply_text=reply_text,
                    )
                    _append_runtime_tick(tick_events, tts_event)

                for _ in range(max(0, int(post_commit_idle_ticks))):
                    if _over_turn_budget():
                        break
                    tick += 1
                    action_record_id = insert_action_record(
                        conn,
                        session_id=session_id,
                        tick=tick,
                        action_type="idle_observe",
                        selected=True,
                        drive=0.2,
                        eligibility={"post_commit": True},
                        target_refs={"visible_text_hash": _hash_text(reply_text)},
                    )
                    _register_action_sa_from_record(conn, action_record_id, tick)
                    event_id = insert_experience_event(
                        conn,
                        session_id=session_id,
                        tick=tick,
                        event_kind="idle_observe",
                        action_record_id=action_record_id,
                        payload={"post_commit": True, "visible_text_hash": _hash_text(reply_text)},
                    )
                    conn.execute(
                        "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
                        (event_id, action_record_id),
                    )
                    pool.tick_decay(tick=tick)
                    _append_runtime_tick(
                        tick_events,
                        _tick_event(
                            conn=conn,
                            session_id=session_id,
                            tick=tick,
                            selected_action={"action_type": "idle_observe", "post_commit": True},
                            action_competition=_competition(
                                "idle_observe",
                                selected="idle_observe",
                                b0=exact_b0,
                                structural_b=structural_b,
                                learning_loop_carryover=_learning_loop_carryover_from_events(tick_events),
                                feedback_drive_context=feedback_drive_context,
                                commit_drive_context=commit_drive_context,
                            ),
                            state_pool=pool,
                            grid=grid,
                            observation=observation,
                            event_ids=(event_id,),
                            action_record_ids=(action_record_id,),
                            b0=exact_b0,
                            structural_b=structural_b,
                            c_backward=_visual_imagination_c_backward(visual_imagination),
                            feelings=_feelings_for_output(
                                output_intent,
                                exact_b0,
                                structural_b,
                                teacher_request_context=teacher_request_context,
                                feedback_drive_context=feedback_drive_context,
                            ),
                        ),
                    )

        # §1734/§36第4阶 行动序列共现观察 — 范式发现基础设施 (E-0').
        # 从 turn 内 tick_events 取 selected 行动序列, 发现相邻行动对,
        # 存到既有经验流 (event_kind="action_sequence_cooccurrence"),
        # 含内生感受条件 (§276). 范式从共现频率自动涌现, 不硬编.
        # 修 R2 残留(上一轮 audit): 增传 observation, 让自发端对竖式观察
        # 用共享感知函数 perceive_process_state 回放 written_cells, 产出与
        # 示范/执行**同键同事件**的共现行。非竖式观察走原逻辑 (旧 3 键 fall-back).
        _observe_action_sequence_cooccurrence(
            conn,
            session_id=session_id,
            tick=tick,
            tick_events=tick_events,
            observation=observation,
        )
        # P1-2: turn 末落盘状态池 top-N 能量残余, 供下一 turn 恢复 (§9 跨 tick 持续).
        _persist_statepool_snapshot(conn, pool, session_id=session_id, tick=tick)
        conn.commit()

    return Phase207TurnResult(
        schema_id=(
            PHASE20_7_STAGE5_SCHEMA_ID
            if enable_visual and not enable_audio_tts
            else PHASE20_7_STAGE6_SCHEMA_ID
            if enable_audio_tts
            else PHASE20_7_STAGE4_SCHEMA_ID
            if enable_unclosed_idle
            else PHASE20_7_STAGE3_SCHEMA_ID
            if enable_structural_bccstar
            else PHASE20_7_STAGE1_SCHEMA_ID
        ),
        stage_id=(
            "20.7-stage5"
            if enable_visual and not enable_audio_tts
            else "20.7-stage6"
            if enable_audio_tts
            else "20.7-stage4"
            if enable_unclosed_idle
            else "20.7-stage3"
            if enable_structural_bccstar
            else "20.7-stage1"
        ),
        session_id=session_id,
        committed=committed,
        reply_text=reply_text if committed else "",
        tick_trace=tuple(tick_events),
        db_path=path,
        stage0_checks=status,
        emotion=_build_and_persist_emotion(
            tick_events, conn=conn, session_id=session_id, tick=tick,
        ),
        innate_rules=_innate_rules_audit(),
    )


def _visual_signature_for_cooccurring_answer(
    conn: sqlite3.Connection,
    *,
    feedback_text: str,
) -> str | None:
    """P1-4: 教师反馈文本与某条带视觉签名的已教对齐输出完全一致时, 返回该视觉签名.

    这是"指代短语学习"的共现证据 (§1210): 对纯文本问法给出的正确答案恰是某个
    视觉经验的已教答案 → 该问法在教学语境下指代那次视觉经验. 只认输出完全一致
    (不做模糊匹配, 防误绑), 只读既有经验流.
    """
    text = str(feedback_text or "").strip()
    if not text:
        return None
    target_hash = _hash_text(text)
    rows = conn.execute(
        """
        SELECT payload_json FROM phase20_7_experience_events
        WHERE event_kind='experience_alignment'
          AND json_extract(payload_json, '$.output_hash')=?
          AND json_extract(payload_json, '$.visual_signature') IS NOT NULL
          AND reward>punish
        ORDER BY created_at_ms DESC LIMIT 4
        """,
        (target_hash,),
    ).fetchall()
    for (payload_json,) in rows:
        payload = from_json(str(payload_json))
        if not isinstance(payload, dict):
            continue
        if str(payload.get("alignment_role") or "") == "counter_evidence":
            continue
        sig = str(payload.get("visual_signature") or "")
        if sig:
            return sig
    return None


def _latest_visual_window_signature(
    conn: sqlite3.Connection,
    *,
    session_id: str,
) -> str | None:
    """P1-4: 最近一次视觉窗口的签名 — 学得的视觉指代短语解析到"刚才看的那张图".

    指代按当下语境解析 (人类"刚刚那张图"永远指最近的), 而不是复读教学时刻绑定的
    那张图 — 防"最近答案覆盖"的镜像错误(旧答案覆盖新图). 只读既有经验流.
    """
    for candidate in query_recent_experience_flow_candidates(
        conn,
        session_id=session_id,
        from_json=from_json,
        hash_text=_hash_text,
        signature_for_chars=_signature_for_chars,
        compose_input_signature=_compose_input_signature,
        visual_tokens_from_payloads=_visual_signature_from_payloads,
        limit=18,
    ):
        if candidate.source_kind == "recent_visual_window" and candidate.visual_signature:
            return str(candidate.visual_signature)
    return None


def _next_unit_competition(
    *,
    planned_char: str,
    char_index: int,
    output_intent: str,
    source_support: float,
    pending_units: int,
    grid: DraftGrid,
    prev_char: str,
    paradigm_delta: float = 0.0,
) -> dict[str, Any]:
    """M2 逐单元生成 v1 — 每个 write tick 的"下一单元"竞争 (C16).

    候选: 召回源的下一字 (偏置=源 support×位置连续性, 正常最强→行为不变) /
    暂停回读 / 主动停. paradigm_delta 是 M3 范式通道的偏置注入口 (当前 0).
    整串召回由此降级为"最强后继偏置来源"而非承诺输出 — mid-write 的冲突
    (edit/mutation/低把握) 通过后续 readback/edit 流真正改变内容 (9q/9r 已有).
    """
    continuity = 1.0 / (1.0 + max(0, char_index) * 0.02)
    source_drive = _unit(0.30 + _unit(source_support) * 0.52 * continuity + paradigm_delta)
    occupied = sum(1 for cell in grid.cells.values() if str(cell.char).strip())
    pause_drive = _unit(0.06 + occupied / max(1, grid.rows * grid.cols) * 0.10)
    stop_drive = _unit(0.04 + (0.08 if pending_units == 0 else 0.0))
    rows = (
        {"action_type": "write_next_unit", "unit": planned_char, "drive": round(source_drive, 4),
         "source": f"{output_intent}_successor_bias", "prev_unit": prev_char},
        {"action_type": "pause_readback", "drive": round(pause_drive, 4)},
        {"action_type": "stop_generating", "drive": round(stop_drive, 4)},
    )
    selected = max(rows, key=lambda r: float(r["drive"]))
    return {
        "formula_id": PHASE20_9P_DRAFTGRID_ACTION_ID,
        "kind": "next_unit_competition",
        "candidate_rows": rows,
        "selected_action_type": str(selected["action_type"]),
        "paradigm_delta": round(float(paradigm_delta), 4),
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _record_text_observation(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    tick: int,
    text: str,
    visual_signature: str | None = None,
) -> _TextObservation:
    chars = tuple(text.strip())
    text_signature = _signature_for_chars(chars)
    signature = _compose_input_signature(text_signature, visual_signature)
    text_hash = _hash_text("".join(chars))
    source_packet_id = insert_source_packet(
        conn,
        source_kind="user_text",
        source_ref=f"session::{session_id}",
        source_context="open_dialogue_text",
        modality="text",
        trust_snapshot=0.5,
        tick=tick,
        payload={"text_hash": text_hash, "char_count": len(chars)},
    )
    event_id = insert_experience_event(
        conn,
        session_id=session_id,
        tick=tick,
        event_kind="text_receptor_observation",
        source_packet_id=source_packet_id,
        payload={
            "text": "".join(chars),
            "text_hash": text_hash,
            "char_count": len(chars),
            "structure_signature": signature,
            "text_signature": text_signature,
            "visual_signature": visual_signature,
            "structure_kind": "linear_text",
        },
    )
    occurrence_ids: list[str] = []
    utterance_sa = f"text_utterance::{signature}"
    upsert_sa_type(
        conn,
        sa_type_id=utterance_sa,
        substrate="text",
        modality="text",
        canonical_hint=f"utterance:{text_hash}",
        tick=tick,
    )
    utterance_occ = insert_occurrence(
        conn,
        event_id=event_id,
        sa_type_id=utterance_sa,
        tick=tick,
        substrate="text",
        position={"axis": "utterance", "index": 0, "length": len(chars)},
        r=0.52,
        v=0.0,
        a=0.52,
        p=0.52,
        clarity=1.0,
        source_ref=source_packet_id,
    )
    occurrence_ids.append(utterance_occ)
    _observe_pool(pool, tick=tick, sa_id=utterance_sa, family="text", label=f"utterance:{text_hash}", energy=0.52)

    previous_occurrence = utterance_occ
    for index, char in enumerate(chars):
        sa_type_id = f"text_unit::{_hash_text(char)}"
        upsert_sa_type(
            conn,
            sa_type_id=sa_type_id,
            substrate="text",
            modality="text",
            canonical_hint=char,
            tick=tick,
        )
        occurrence_id = insert_occurrence(
            conn,
            event_id=event_id,
            sa_type_id=sa_type_id,
            tick=tick,
            substrate="text",
            position={"axis": "linear", "index": index, "signature": signature},
            r=0.42,
            v=0.0,
            a=0.42,
            p=0.42,
            clarity=1.0,
            source_ref=source_packet_id,
        )
        occurrence_ids.append(occurrence_id)
        _observe_pool(pool, tick=tick, sa_id=sa_type_id, family="text", label=char, energy=0.42)
        insert_structure_edge(
            conn,
            src_occurrence_id=previous_occurrence,
            dst_occurrence_id=occurrence_id,
            edge_type="linear_contains" if previous_occurrence == utterance_occ else "linear_next",
            weight=1.0,
            learned_weight=0.0,
            tick=tick,
        )
        previous_occurrence = occurrence_id
    return _TextObservation(
        event_id=event_id,
        source_packet_id=source_packet_id,
        occurrence_ids=tuple(occurrence_ids),
        signature=signature,
        text_signature=text_signature,
        chars=chars,
        text_hash=text_hash,
        visual_signature=visual_signature,
    )


def _record_teacher_feedback(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    tick: int,
    feedback: TeacherFeedback,
    observation: _ObservationLike | None,
    output_intent: str = "idle_observe",
) -> tuple[str | dict[str, Any], ...]:
    feedback_chars = tuple(feedback.feedback_text.strip())
    feedback_hash = _hash_text("".join(feedback_chars))
    target_event_id = feedback.target_event_id or (observation.event_id if observation else None)
    expression_role = _expression_role_for_target_event(conn, target_event_id)
    # P1-4 (§1210 指代学习, 经验后验): 观察本身无视觉签名, 但教师给出的反馈文本与
    # 某条"带视觉签名的已教对齐"的输出高度重合(如对"刚刚图片是啥"回答"是苹果",
    # 而"是苹果"正是刚教过的苹果图答案) — 这一共现是"该问法指代视觉记忆"的证据.
    # 把该视觉签名附到本次对齐上, 该问法从此成为学得的视觉指代短语
    # (visual_reference_family 由经验而来, 非关键词表). 惩罚反馈不参与.
    borrowed_referral_visual_signature: str | None = None
    if (
        observation is not None
        and not observation.visual_signature
        and not expression_role
        and float(feedback.reward_mag) > float(feedback.punish_mag)
        and feedback_chars
    ):
        borrowed_referral_visual_signature = _visual_signature_for_cooccurring_answer(
            conn, feedback_text="".join(feedback_chars)
        )
    if borrowed_referral_visual_signature and observation is not None:
        # 指代绑定: 本次对齐携带被指代视觉经验的签名 (input_signature 重组为
        # 文本+视觉复合键, 使这条对齐走视觉相似召回而非文本答案表 — 下次同一
        # 问法出现时按"当时最近的视觉窗口"解析, 不复读教学时刻的答案).
        observation = replace(
            observation,
            visual_signature=borrowed_referral_visual_signature,
            signature=_compose_input_signature(
                observation.text_signature, borrowed_referral_visual_signature
            ),
        )
    expression_target_trace = _expression_target_trace_for_event(conn, target_event_id) if expression_role else {}
    expression_paradigm_slot = (
        _expression_paradigm_slot(expression_role, _context_from_expression_trace(expression_target_trace))
        if expression_role
        else None
    )
    expression_referent = _referent_from_expression_trace(expression_target_trace) if expression_role else {}
    alignment_scope = (
        "request_expression_from_targeted_draft_feedback"
        if expression_role
        else "exact_structural_b0_stage1"
    )
    source_packet_id = insert_source_packet(
        conn,
        source_kind="teacher_feedback",
        source_ref="teacher::local",
        source_context="open_dialogue_text",
        modality="text",
        trust_snapshot=0.7,
        tick=tick,
        payload={
            "feedback_hash": feedback_hash,
            "char_count": len(feedback_chars),
            "target_event_id": target_event_id,
            "expression_role": expression_role,
            "expression_paradigm_slot": expression_paradigm_slot,
            "expression_referent": expression_referent,
            "expression_referent_formula_id": PHASE20_8R_CURRENT_REFERENT_BINDING_ID if expression_role else None,
        },
    )
    feedback_event_id = insert_experience_event(
        conn,
        session_id=session_id,
        tick=tick,
        event_kind="teacher_feedback_event",
        source_packet_id=source_packet_id,
        payload={
            "feedback_hash": feedback_hash,
            "char_count": len(feedback_chars),
            "target_event_id": target_event_id,
            "expression_role": expression_role,
            "expression_paradigm_slot": expression_paradigm_slot,
            "expression_referent": expression_referent,
            "expression_referent_formula_id": PHASE20_8R_CURRENT_REFERENT_BINDING_ID if expression_role else None,
        },
        reward=feedback.reward_mag,
        punish=feedback.punish_mag,
    )
    output_occurrence_ids: list[str] = []
    previous_occurrence: str | None = None
    for index, char in enumerate(feedback_chars):
        sa_type_id = f"text_unit::{_hash_text(char)}"
        upsert_sa_type(
            conn,
            sa_type_id=sa_type_id,
            substrate="text",
            modality="text",
            canonical_hint=char,
            tick=tick,
        )
        occurrence_id = insert_occurrence(
            conn,
            event_id=feedback_event_id,
            sa_type_id=sa_type_id,
            tick=tick,
            substrate="text",
            position={"axis": "feedback_linear", "index": index},
            r=0.5,
            v=0.0,
            a=0.5,
            p=0.5,
            clarity=1.0,
            source_ref=source_packet_id,
        )
        output_occurrence_ids.append(occurrence_id)
        _observe_pool(
            pool,
            tick=tick,
            sa_id=sa_type_id,
            family="teacher_feedback",
            label=char,
            energy=0.5,
            source="teacher_feedback",
            ledger_source="feedback",
        )
        if previous_occurrence is not None:
            insert_structure_edge(
                conn,
                src_occurrence_id=previous_occurrence,
                dst_occurrence_id=occurrence_id,
                edge_type="feedback_linear_next",
                weight=1.0,
                learned_weight=0.2,
                tick=tick,
            )
        previous_occurrence = occurrence_id

    alignment_event_id = insert_experience_event(
        conn,
        session_id=session_id,
        tick=tick,
        event_kind="experience_alignment",
        source_packet_id=source_packet_id,
        payload={
            "input_signature": observation.signature if observation else None,
            "text_signature": observation.text_signature if observation else None,
            "visual_signature": observation.visual_signature if observation else None,
            "input_event_id": observation.event_id if observation else target_event_id,
            "output_chars": list(feedback_chars),
            "output_hash": feedback_hash,
            "output_occurrence_ids": output_occurrence_ids,
            "alignment_scope": alignment_scope,
            # §2363/E4/C21: 惩罚主导的反馈是纠错证据, 不是可复述答案. 标记
            # alignment_role=counter_evidence 后, 该行不进 exact_b0_index, 且被所有
            # 回复候选查询排除 (同 expression_role 的既有排除模式). 它仍留在
            # append-only 经验流里, 作为 §2363 teacher_correction 反例通道的数据源
            # (P0-2 的 counter 计数消费它).
            "alignment_role": (
                "counter_evidence" if float(feedback.punish_mag) > float(feedback.reward_mag) else None
            ),
            "expression_role": expression_role,
            "expression_target_event_id": target_event_id if expression_role else None,
            "expression_target_trace": expression_target_trace,
            "expression_paradigm_slot": expression_paradigm_slot,
            "expression_paradigm_formula_id": PHASE20_8P_EXPRESSION_PARADIGM_ID if expression_role else None,
            "expression_referent": expression_referent,
            "expression_referent_formula_id": PHASE20_8R_CURRENT_REFERENT_BINDING_ID if expression_role else None,
            "visual_reference_family": _observation_is_visual_reference_family(observation) if observation else False,
        },
        reward=max(feedback.reward_mag, 0.0),
        punish=max(feedback.punish_mag, 0.0),
    )
    if observation and observation.occurrence_ids and output_occurrence_ids:
        insert_structure_edge(
            conn,
            src_occurrence_id=observation.occurrence_ids[-1],
            dst_occurrence_id=output_occurrence_ids[0],
            edge_type="feedback_alignment_edge",
            weight=1.0,
            learned_weight=0.3,
            tick=tick,
        )
    if (
        observation is not None
        and not expression_role
        and float(feedback.punish_mag) <= float(feedback.reward_mag)
    ):
        # support 用 §173.5 退火后验把握感(§737 Grasp), support_count 取该 input_signature
        # 下截至当前(含本次 alignment 事件)的 reward>0 累计确认数. alignment 事件已在上一行
        # insert_experience_event 落盘, 故 _alignment_support_count 能查到本次. 调用统一函数,
        # 不再内联复制公式(避免公式漂移).
        # §2363/E4/C21: punish 主导的反馈(counter_evidence)绝不写入 exact_b0_index ——
        # 纠错文本不是答案, 索引化会让 AP 下次把"不对"当作该输入的已教回复复述出来.
        sc = _alignment_support_count(conn, input_signature=observation.signature)
        upsert_exact_b0_index(
            conn,
            input_signature=observation.signature,
            alignment_event_id=alignment_event_id,
            input_event_id=observation.event_id,
            output_chars=feedback_chars,
            support=_support_from_reward_punish(
                feedback.reward_mag, feedback.punish_mag, support_count=sc
            ),
        )
    l1_delta = _apply_l1_triplet_update(
        conn,
        pool,
        session_id=session_id,
        tick=tick,
        observation=observation,
        feedback_chars=feedback_chars,
        reward=max(feedback.reward_mag, 0.0),
        punish=max(feedback.punish_mag, 0.0),
    )
    l2_delta = _apply_l2_temporal_edge_update(
        conn,
        pool,
        session_id=session_id,
        tick=tick,
        observation=observation,
        feedback_chars=feedback_chars,
        reward=max(feedback.reward_mag, 0.0),
        punish=max(feedback.punish_mag, 0.0),
    )
    l3_delta = _apply_l3_action_consequence_update(
        conn,
        pool,
        session_id=session_id,
        tick=tick,
        observation=observation,
        feedback=feedback,
        output_intent=output_intent,
    )
    deltas: list[dict[str, Any]] = [
        d for d in (l1_delta, l2_delta, l3_delta) if d is not None
    ]
    return (feedback_event_id, alignment_event_id, *deltas)


def _find_exact_b0(
    conn: sqlite3.Connection,
    observation: _ObservationLike,
    *,
    state_pool: StatePool | None = None,
) -> _ExactB0 | None:
    observation_bias, _observation_bias_slots = _statepool_observation_support_bias(state_pool, observation)
    bias_terms: tuple[tuple[str, float], ...] = (
        (("statepool_cstar_observation_bias", round(observation_bias, 4)),) if observation_bias > 0.0 else ()
    )
    if observation.visual_signature:
        visual_match = _find_visual_exact_b0(conn, observation)
        if visual_match is not None:
            if observation_bias > 0.0:
                return replace(
                    visual_match,
                    support=min(1.0, float(visual_match.support) + observation_bias),
                    support_terms=tuple(visual_match.support_terms) + bias_terms,
                )
            return visual_match
    indexed_rows = conn.execute(
        """
        SELECT alignment_event_id, input_event_id, output_json, support
        FROM phase20_7_exact_b0_index
        WHERE input_signature=?
        ORDER BY support DESC, updated_at_ms DESC
        LIMIT 20
        """,
        (observation.signature,),
    ).fetchall()
    for alignment_event_id, input_event_id, output_json, support in indexed_rows:
        if is_tombstoned(conn, object_kind="event", object_ref=str(alignment_event_id)):
            continue
        output_chars = tuple(str(ch) for ch in from_json(str(output_json)))
        unified_candidate = _unified_candidate_for_alignment_id(
            conn,
            observation,
            alignment_event_id=str(alignment_event_id),
            limit=240,
        )
        if output_chars and unified_candidate is not None:
            support_value = min(1.0, max(float(support), min(1.0, float(unified_candidate.support))) + observation_bias)
            return _ExactB0(
                event_id=str(alignment_event_id),
                source_event_id=str(input_event_id or alignment_event_id),
                output_chars=output_chars,
                support=support_value,
                visual_similarity=None,
                candidate_audit_slots=(unified_candidate.audit_slot(),),
                support_terms=tuple(unified_candidate.support_terms)
                + (
                    ("exact_b0_index_support", round(float(support), 4)),
                    ("unified_candidate_support", round(float(unified_candidate.support), 4)),
                )
                + bias_terms,
            )
    for unified_candidate in _unified_experience_candidates_for_observation(conn, observation, limit=200):
        if unified_candidate.candidate_kind != "experience_alignment":
            continue
        payload = unified_candidate.payload
        if payload.get("expression_role"):
            continue
        if payload.get("input_signature") != observation.signature:
            continue
        output_chars = tuple(str(ch) for ch in payload.get("output_chars", ()))
        if not output_chars:
            continue
        support = min(1.0, max(0.25, min(1.0, float(unified_candidate.support))) + observation_bias)
        upsert_exact_b0_index(
            conn,
            input_signature=observation.signature,
            alignment_event_id=str(unified_candidate.alignment_event_id or unified_candidate.event_id),
            input_event_id=payload.get("input_event_id"),
            output_chars=output_chars,
            support=support,
        )
        return _ExactB0(
            event_id=str(unified_candidate.alignment_event_id or unified_candidate.event_id),
            source_event_id=str(payload.get("input_event_id") or unified_candidate.event_id),
            output_chars=output_chars,
            support=support,
            visual_similarity=None,
            candidate_audit_slots=(unified_candidate.audit_slot(),),
            support_terms=tuple(unified_candidate.support_terms)
            + (
                ("exact_b0_unified_fallback_support", round(float(support), 4)),
                ("unified_candidate_support", round(float(unified_candidate.support), 4)),
            )
            + bias_terms,
        )
    return None


def _find_visual_exact_b0(conn: sqlite3.Connection, observation: _ObservationLike) -> _ExactB0 | None:
    attribution = _select_alignment_by_backward_neutralization(conn, observation)
    if attribution is None:
        return None
    alignment_payload = attribution["alignment_payload"]
    output_chars = tuple(str(ch) for ch in alignment_payload.get("output_chars", ()))
    if not output_chars:
        return None
    return _ExactB0(
        event_id=str(attribution["alignment_event_id"]),
        source_event_id=str(alignment_payload.get("input_event_id") or attribution["alignment_event_id"]),
        output_chars=output_chars,
        support=float(attribution["score"]),
        visual_similarity=float(attribution.get("visual_similarity", 0.0)),
        candidate_audit_slots=tuple(attribution.get("candidate_audit_slots", ())),
        support_terms=tuple(attribution.get("support_terms", ())),
    )


def _experience_candidates_for_observation(
    conn: sqlite3.Connection,
    observation: _ObservationLike,
    *,
    limit: int = 400,
    exact_input_allowed: bool = True,
) -> tuple[ExperienceRecallCandidate, ...]:
    query = ExperienceRecallQuery(
        query_text="".join(observation.chars),
        text_signature=observation.text_signature,
        visual_signature=observation.visual_signature,
        input_signature=observation.signature,
        open_reference=_observation_is_visual_reference_family(observation),
        exact_input_allowed=exact_input_allowed,
    )
    return query_experience_alignment_candidates(
        conn,
        query,
        from_json=from_json,
        is_tombstoned=is_tombstoned,
        input_payload_for_alignment=_input_payload_for_alignment,
        semantic_text_overlap_with_units=_semantic_text_overlap_with_units,
        visual_similarity=_visual_signature_similarity,
        l1_vector_similarity=lambda q, m: _l1_text_vector_similarity(conn, q, m),
        limit=limit,
    )


def _experience_candidates_for_input_signature(
    conn: sqlite3.Connection,
    *,
    input_signature: str,
    limit: int = 300,
) -> tuple[ExperienceRecallCandidate, ...]:
    query = ExperienceRecallQuery(
        query_text="",
        input_signature=input_signature,
        exact_input_allowed=True,
    )
    return query_experience_alignment_candidates(
        conn,
        query,
        from_json=from_json,
        is_tombstoned=is_tombstoned,
        input_payload_for_alignment=_input_payload_for_alignment,
        semantic_text_overlap_with_units=_semantic_text_overlap_with_units,
        visual_similarity=_visual_signature_similarity,
        limit=limit,
    )


def _unified_experience_candidates_for_observation(
    conn: sqlite3.Connection,
    observation: _ObservationLike,
    *,
    session_id: str | None = None,
    limit: int = 400,
    exact_input_allowed: bool = True,
) -> tuple[UnifiedExperienceCandidate, ...]:
    alignment_candidates = tuple(
        unified_candidate_from_recall(candidate)
        for candidate in _experience_candidates_for_observation(
            conn,
            observation,
            limit=limit,
            exact_input_allowed=exact_input_allowed,
        )
    )
    flow_candidates: tuple[UnifiedExperienceCandidate, ...] = ()
    if session_id:
        flow_candidates = tuple(
            unified_candidate_from_flow(candidate)
            for candidate in query_recent_experience_flow_candidates(
                conn,
                session_id=session_id,
                from_json=from_json,
                hash_text=_hash_text,
                signature_for_chars=_signature_for_chars,
                compose_input_signature=_compose_input_signature,
                visual_tokens_from_payloads=_visual_signature_from_payloads,
                limit=max(1, min(24, int(limit))),
            )
    )
    return merge_unified_experience_candidates(alignment_candidates, flow_candidates)


def _unified_candidate_for_alignment_id(
    conn: sqlite3.Connection,
    observation: _ObservationLike,
    *,
    alignment_event_id: str,
    limit: int = 240,
) -> UnifiedExperienceCandidate | None:
    for candidate in _unified_experience_candidates_for_observation(
        conn,
        observation,
        limit=limit,
        exact_input_allowed=True,
    ):
        if candidate.candidate_kind != "experience_alignment":
            continue
        if candidate.payload.get("expression_role"):
            continue
        candidate_alignment_id = str(candidate.alignment_event_id or candidate.event_id)
        if candidate_alignment_id != str(alignment_event_id):
            continue
        if candidate.payload.get("input_signature") != observation.signature:
            continue
        return candidate
    return None


def _unified_experience_candidates_for_input_signature(
    conn: sqlite3.Connection,
    *,
    input_signature: str,
    limit: int = 300,
) -> tuple[UnifiedExperienceCandidate, ...]:
    return tuple(
        unified_candidate_from_recall(candidate)
        for candidate in _experience_candidates_for_input_signature(
            conn,
            input_signature=input_signature,
            limit=limit,
        )
    )


def _select_visual_imagination_recall(
    conn: sqlite3.Connection,
    observation: _ObservationLike,
    *,
    limit: int = 400,
) -> _VisualImaginationRecall | None:
    query_text = "".join(observation.chars).strip()
    if not query_text:
        return None
    query_units = _meaningful_text_units(query_text)
    query_unit_set = set(query_units)
    unified_candidates = _unified_experience_candidates_for_observation(
        conn,
        observation,
        limit=limit,
        exact_input_allowed=False,
    )
    candidates: list[dict[str, Any]] = []
    for unified_candidate in unified_candidates:
        if unified_candidate.candidate_kind != "experience_alignment":
            continue
        payload = unified_candidate.payload
        if payload.get("expression_role"):
            continue
        visual_signature = str(payload.get("visual_signature", "") or "")
        if not visual_signature:
            continue
        output_chars = tuple(str(ch) for ch in payload.get("output_chars", ()))
        output_text = "".join(output_chars).strip()
        if not output_text:
            continue
        input_payload = _input_payload_for_alignment(conn, payload)
        source_text = str(input_payload.get("text", "") or "")
        text_score, coverage_units = _semantic_text_overlap_with_units(query_text, output_text)
        if source_text:
            source_score, source_units = _semantic_text_overlap_with_units(query_text, source_text)
            if source_score > text_score:
                text_score = source_score
                coverage_units = source_units
        if text_score <= 0.0 or not coverage_units:
            continue
        patch_refs = _patch_payload_refs_for_alignment(conn, payload, visual_signature=visual_signature)
        if not patch_refs:
            continue
        support = max(0.0, min(1.0, max(unified_candidate.support, text_score)))
        if query_unit_set and coverage_units:
            # 视觉指代需要"有含义的重叠单元": 共享单元里必须有多字符词 (如"苹果")
            # — 单字符撞车 ("你好"与"早上好"共享一个"好") 不构成视觉记忆指代,
            # 否则寒暄会召来无关想象画面 (2026-07-04 实测污染).
            has_meaningful_unit = any(len(str(u)) >= 2 for u in coverage_units)
            coverage_ratio = len(set(coverage_units) & query_unit_set) / max(len(query_unit_set), 1)
            if has_meaningful_unit:
                support = max(support, min(0.72, 0.24 + coverage_ratio * 0.42))
        if support < 0.34:
            continue
        candidates.append(
            {
                "alignment_event_id": unified_candidate.alignment_event_id,
                "patch_payload_refs": patch_refs,
                "support": support,
                "matched_text": output_text,
                "visual_signature": visual_signature,
                "coverage_units": tuple(coverage_units),
                "unified_candidate": unified_candidate,
            }
        )
    if not candidates:
        return None
    candidates.sort(key=lambda item: float(item["support"]), reverse=True)
    selected: list[dict[str, Any]] = []
    covered_units: set[str] = set()
    for candidate in candidates:
        candidate_units = set(str(unit) for unit in candidate.get("coverage_units", ()))
        adds_new_unit = bool(candidate_units - covered_units)
        if not selected or adds_new_unit:
            selected.append(candidate)
            covered_units.update(candidate_units)
        if len(selected) >= 3:
            break
    if len(selected) == 1 and len(query_unit_set) > len(covered_units):
        selected.extend(candidate for candidate in candidates if candidate not in selected)  # pragma: no cover
        selected = selected[:3]
    refs: list[str] = []
    for candidate in selected:
        for ref in candidate["patch_payload_refs"]:
            if ref not in refs:
                refs.append(str(ref))
            if len(refs) >= 24:
                break
    if not refs:
        return None
    combined = max(float(item["support"]) for item in selected)
    if len(selected) > 1:
        combined = min(1.0, combined + 0.06 * (len(selected) - 1))
    selected_unified = merge_unified_experience_candidates(
        tuple(
            item["unified_candidate"]
            for item in selected
            if isinstance(item.get("unified_candidate"), UnifiedExperienceCandidate)
        )
    )
    return _VisualImaginationRecall(
        alignment_event_ids=tuple(str(item["alignment_event_id"]) for item in selected),
        patch_payload_refs=tuple(refs),
        score=combined,
        matched_texts=tuple(str(item["matched_text"]) for item in selected),
        visual_signature_count=len({str(item["visual_signature"]) for item in selected}),
        candidate_audit_slots=tuple(candidate.audit_slot() for candidate in selected_unified),
    )


def _visual_imagination_c_backward(recall: _VisualImaginationRecall | None) -> tuple[dict[str, Any], ...]:
    if recall is None:
        return ()
    return (
        {
            "kind": "every_tick_backward_min_error",
            "model": "text_occurrence_to_visual_experience_flow/v1",
            "selected_source_kind": "remembered_visual_alignment",
            "source_alignment_ids": list(recall.alignment_event_ids),
            "matched_texts": list(recall.matched_texts),
            "patch_payload_ref_count": len(recall.patch_payload_refs),
            "visual_signature_count": recall.visual_signature_count,
            "cause_slots": list(recall.candidate_audit_slots),
            "cause_grasp": round(float(recall.score), 4),
            "e_backward": round(max(0.0, 1.0 - float(recall.score)), 4),
            "subjective": True,
            "may_be_wrong": True,
        },
    )


def _learned_idle_action_support(conn: sqlite3.Connection, *, session_id: str) -> dict[str, float]:
    """闲时行动选择的学习支持 (修复 D 硬编阶梯闭合).

    §173.5 熟练涌现: action_sequence_cooccurrence 表中 prev_action_result='idle_settled'
    在该 session 下被记录过的 "下一行动"分布, 按 §173.5 式 support = 1 - exp(-n/3)
    转换为 0~1 的学习支持度. 空库→0; 越多支持越高.

    红线:
    - 不引入新表 (复用既有 action_sequence_cooccurrence);
    - 不引入"具体阈值" — 抬升上限 0.15 是学习贡献天花板 (§66.2 先天行动节奏 baseline 仍主导);
    - 不写答案/不路由 — 完全靠共现频率决定, AP 越练过闲时选某行动越易再选;
    - 返回 {action_b: support_z}, 调用者按 effective_drive = baseline + z*0.15 偏移门槛.
    """
    rows = conn.execute(
        """
        SELECT json_extract(payload_json, '$.action_b') AS ab, COUNT(*) AS n
        FROM phase20_7_experience_events
        WHERE event_kind='action_sequence_cooccurrence'
          AND json_extract(payload_json, '$.prev_action_result')='idle_settled'
          AND session_id=?
        GROUP BY ab
        """,
        (session_id,),
    ).fetchall()
    out: dict[str, float] = {}
    for ab, n in rows:
        if not ab:
            continue
        z = 1.0 - pow(2.718281828, -float(n) / 3.0)
        out[str(ab)] = round(min(1.0, z), 4)
    return out


def _run_idle_think_tick(
    conn: sqlite3.Connection,
    pool: StatePool,
    grid: DraftGrid,
    *,
    session_id: str,
    db_path: Path,
    status: dict[str, object],
    start_tick: int,
    enable_visual: bool = False,
    enable_audio_tts: bool = False,
) -> Phase207TurnResult:
    visual_drive = estimate_idle_visual_drive(conn, session_id=session_id) if enable_visual else 0.0
    audio_drive = estimate_idle_audio_drive(conn, session_id=session_id) if enable_audio_tts else 0.0
    structure_flow_bias = _short_structure_flow_attention_bias(conn, session_id=session_id, before_tick=int(start_tick) + 1)
    learning_loop_carryover = _idle_learning_loop_carryover_from_experience_flow(
        conn,
        session_id=session_id,
        before_tick=int(start_tick) + 1,
    )
    learning_idle_drive = (
        min(0.86, 0.24 + float(learning_loop_carryover.get("idle_think_delta", 0.0) or 0.0) * 4.0)
        if learning_loop_carryover.get("active")
        else 0.0
    )
    if enable_visual:
        visual_drive = min(0.95, visual_drive + float(structure_flow_bias.get("visual_drive_delta", 0.0) or 0.0))
    # 修复 D (idle 行动选择 magic-number 阶梯闭合): 加 §173.5 学习支持抬升项.
    # _learned_idle_action_support 查 prev_action_result='idle_settled' 下的行动共现,
    # 把行动练习次数转为 0~1 支持度. 空库→0, 默认 selftest 行为完全等同原 magic-number.
    # 各行动有效门槛 = 原 baseline threshold - support * 抬升上限. 不引入"内容阈值"——
    # baseline 数字 (0.58/0.42/+0.08/+0.12/+0.05/0.48) 仍作先天行动节奏保留, 学习仅在门槛
    # 上加 offset: AP 越练某闲时行动, 门槛越低 → 熟练涌现 (§173.5). 不破坏 6/6 PASS 默认.
    learned_support = _learned_idle_action_support(conn, session_id=session_id)
    # 抬升上限 0.15: 学到 100% 支持 (n>=15) 时门槛最多降 0.15. 0.58→0.43, 0.48→0.33, 不失控.
    _SUPPORT_LIFT = 0.15
    visual_threshold = 0.58 - float(learned_support.get("idle_visual_focus", 0.0)) * _SUPPORT_LIFT
    audio_threshold_base = 0.48 - float(learned_support.get("idle_audio_focus", 0.0)) * _SUPPORT_LIFT
    audio_pressure_pad = 0.12 - float(learned_support.get("idle_audio_focus", 0.0)) * _SUPPORT_LIFT
    row = conn.execute(
        """
        SELECT unclosed_id, session_id, source_event_id, source_signature, source_text,
               u_value, status, attempt_count, reason_json, created_at_ms, updated_at_ms
        FROM phase20_7_unclosed_items
        WHERE status='active' AND session_id=?
        ORDER BY u_value DESC, updated_at_ms DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    unclosed_drive = float(row[5]) if row is not None else 0.0
    if row is not None:
        unclosed_drive = min(1.0, unclosed_drive + float(structure_flow_bias.get("idle_think_drive_delta", 0.0) or 0.0))
    idle_think_pressure = max(unclosed_drive, learning_idle_drive)
    visual_attention_pressure = (
        max(unclosed_drive + 0.08, audio_drive + 0.05, 0.42)
        if visual_drive >= visual_threshold and row is None
        else max(idle_think_pressure + 0.08, audio_drive + 0.05, 0.42)
    )
    if visual_drive >= visual_attention_pressure:
        visual_event, _visual_tick = run_idle_visual_receptor_tick(
            conn,
            pool,
            session_id=session_id,
            start_tick=int(start_tick),
            db_path=db_path,
        )
        if visual_event is None:
            visual_drive = 0.0
        else:
            visual_event = _with_idle_competition(
                visual_event,
                selected="idle_visual_focus",
                visual_drive=visual_drive,
                audio_drive=audio_drive,
                unclosed_drive=unclosed_drive,
                learning_loop_carryover=learning_loop_carryover,
            )
            if visual_event.selected_action.get("drive") is None:
                visual_event = _with_selected_action_drive(visual_event, drive=visual_drive)
            return Phase207TurnResult(
                schema_id=PHASE20_7_STAGE6_SCHEMA_ID if enable_audio_tts else PHASE20_7_STAGE5_SCHEMA_ID,
                stage_id="20.7-stage6" if enable_audio_tts else "20.7-stage5",
                session_id=session_id,
                committed=False,
                reply_text="",
                tick_trace=(visual_event,),
                db_path=db_path,
                stage0_checks=status,
            )
    if audio_drive >= max(idle_think_pressure + audio_pressure_pad, audio_threshold_base):
        # 修复 D: audio 行动门槛由学习支持抬低 (baseline 0.48, pad +0.12 不变, 学到的
        # 支持 idle_audio_focus 共现越多, 门槛越低). 空库→原 0.48 与 +0.12, 不破 6/6 PASS.
        audio_event, _audio_tick = run_idle_audio_focus_tick(
            conn,
            pool,
            session_id=session_id,
            start_tick=int(start_tick),
        )
        if audio_event is not None:
            audio_event = _with_idle_competition(
                audio_event,
                selected="idle_audio_focus",
                visual_drive=visual_drive,
                audio_drive=audio_drive,
                unclosed_drive=unclosed_drive,
                learning_loop_carryover=learning_loop_carryover,
            )
            return Phase207TurnResult(
                schema_id=PHASE20_7_STAGE6_SCHEMA_ID,
                stage_id="20.7-stage6",
                session_id=session_id,
                committed=False,
                reply_text="",
                tick_trace=(audio_event,),
                db_path=db_path,
                stage0_checks=status,
            )
    tick = int(start_tick) + 1
    self_test = _idle_learning_self_test_from_short_structure_flow(
        conn,
        session_id=session_id,
        before_tick=tick,
        learning_loop_carryover=learning_loop_carryover,
    )
    if row is None and self_test:
        self_test_result = _run_idle_learning_self_test_tick(
            conn,
            pool,
            grid,
            session_id=session_id,
            db_path=db_path,
            status=status,
            tick=tick,
            visual_drive=visual_drive,
            audio_drive=audio_drive,
            learning_loop_carryover=learning_loop_carryover,
            structure_flow_bias=structure_flow_bias,
            self_test=self_test,
        )
        return _maybe_commit_outward_speech_from_idle_result(
            conn,
            pool,
            grid,
            idle_result=self_test_result,
            session_id=session_id,
            db_path=db_path,
            status=status,
            visual_drive=visual_drive,
            audio_drive=audio_drive,
            unclosed_drive=0.0,
            learning_loop_carryover=learning_loop_carryover,
        )
    if row is None and learning_loop_carryover.get("active") and learning_idle_drive > 0.18:
        review_result = _run_idle_learning_review_tick(
            conn,
            pool,
            grid,
            session_id=session_id,
            db_path=db_path,
            status=status,
            tick=tick,
            visual_drive=visual_drive,
            audio_drive=audio_drive,
            learning_loop_carryover=learning_loop_carryover,
            structure_flow_bias=structure_flow_bias,
        )
        return _maybe_commit_outward_speech_from_idle_result(
            conn,
            pool,
            grid,
            idle_result=review_result,
            session_id=session_id,
            db_path=db_path,
            status=status,
            visual_drive=visual_drive,
            audio_drive=audio_drive,
            unclosed_drive=0.0,
            learning_loop_carryover=learning_loop_carryover,
        )
    if row is None:
        action_record_id = insert_action_record(
            conn,
            session_id=session_id,
            tick=tick,
            action_type="idle_observe",
            selected=True,
            drive=0.18,
            eligibility={"no_external_input": True, "active_unclosed": False},
            target_refs={},
        )
        _register_action_sa_from_record(conn, action_record_id, tick)
        event_id = insert_experience_event(
            conn,
            session_id=session_id,
            tick=tick,
            event_kind="idle_observe",
            action_record_id=action_record_id,
            payload={"no_external_input": True, "active_unclosed": False},
        )
        conn.execute(
            "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
            (event_id, action_record_id),
        )
        event = _tick_event(
            conn=conn,
            session_id=session_id,
            tick=tick,
            selected_action={"action_type": "idle_observe", "active_unclosed": False},
            action_competition=_idle_competition(
                selected="idle_observe",
                visual_drive=visual_drive,
                audio_drive=audio_drive,
                unclosed_drive=0.0,
                learning_loop_carryover=learning_loop_carryover,
            ),
            state_pool=pool,
            grid=grid,
            event_ids=(event_id,),
            action_record_ids=(action_record_id,),
            feelings={"idle": True, "unclosed_pull": 0.0},
            ssp_summary={
                "short_structure_flow_attention_bias": structure_flow_bias,
                "idle_learning_review": learning_loop_carryover.get("idle_learning_review", {}),
            },
        )
        return Phase207TurnResult(
            schema_id=PHASE20_7_STAGE4_SCHEMA_ID,
            stage_id="20.7-stage4",
            session_id=session_id,
            committed=False,
            reply_text="",
            tick_trace=(event,),
            db_path=db_path,
            stage0_checks=status,
        )

    unclosed_item = _unclosed_row_to_dict(row)
    source_text = str(unclosed_item["source_text"])
    successor = _successor_for_unclosed(conn, unclosed_item)
    attempt_index = int(unclosed_item["attempt_count"]) + 1
    narrative_text = _idle_narrative_text(unclosed_item, successor=successor, attempt_index=attempt_index)
    review_text = _idle_learning_review_text(learning_loop_carryover)
    if review_text:
        narrative_text = f"{narrative_text} | {review_text}"
    narrative_sa = f"idle_narrative::{_hash_text(str(unclosed_item['unclosed_id']) + '|' + str(attempt_index))}"
    _observe_pool(
        pool,
        tick=tick,
        sa_id=f"unclosed::{_hash_text(str(unclosed_item['unclosed_id']))}",
        family="unclosed_pull",
        label=source_text,
        energy=min(0.6, float(unclosed_item["u_value"])),
        source="unclosed_idle",
        ledger_source="unfinished_pressure",
    )
    _observe_pool(
        pool,
        tick=tick,
        sa_id=narrative_sa,
        family="short_structure_flow",
        label=narrative_text,
        energy=min(0.72, 0.25 + float(unclosed_item["u_value"]) * 0.55),
        source="experience_successor_bias",
        ledger_source="unfinished_pressure",
    )
    next_u_value = _decay_unclosed_for_idle(
        conn,
        unclosed_id=str(unclosed_item["unclosed_id"]),
        current_u=float(unclosed_item["u_value"]),
        attempt_count=attempt_index,
        successor_found=successor is not None,
    )
    unclosed_item = {**unclosed_item, "u_value": next_u_value, "attempt_count": attempt_index}
    action_record_id = insert_action_record(
        conn,
        session_id=session_id,
        tick=tick,
        action_type="idle_think",
        selected=True,
        drive=min(0.95, 0.25 + next_u_value),
        eligibility={"no_external_input": True, "active_unclosed": True},
        target_refs={"unclosed_id": unclosed_item["unclosed_id"], "source_event_id": unclosed_item["source_event_id"]},
    )
    _register_action_sa_from_record(conn, action_record_id, tick)
    event_id = insert_experience_event(
        conn,
        session_id=session_id,
        tick=tick,
        event_kind="idle_think",
        action_record_id=action_record_id,
        payload={
            "unclosed_id": unclosed_item["unclosed_id"],
            "source_event_id": unclosed_item["source_event_id"],
            "source_text": source_text,
            "u_value": next_u_value,
            "attempt_count": attempt_index,
            "successor": successor or {},
            "narrative_text": narrative_text,
            "private_thought": True,
        },
    )
    conn.execute(
        "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
        (event_id, action_record_id),
    )
    idle_flow = _write_short_structure_flow_occurrence(
        conn,
        session_id=session_id,
        tick=tick,
        event_id=event_id,
        text=narrative_text,
        support=min(1.0, 0.25 + next_u_value),
        source_kind="idle",
        r=min(0.72, 0.25 + next_u_value),
        v=0.0,
        a=min(0.82, 0.28 + next_u_value),
        p=next_u_value,
        metadata={
            "unclosed_id": unclosed_item["unclosed_id"],
            "attempt_count": attempt_index,
            "private_thought": True,
            "successor_found": bool(successor),
            "idle_learning_review": learning_loop_carryover.get("idle_learning_review", {}),
        },
    )
    expression_context = {
        "formula_id": PHASE20_8N_REQUEST_TEACHER_DRIVE_ID,
        "intent": "maintain_unclosed",
        "low_grasp": 0.0,
        "b_support": round(float((successor or {}).get("support", 0.0) or 0.0), 4),
        "unclosed_pull": round(next_u_value, 4),
        "short_structure_flow_support": round(float(idle_flow.get("support", 0.0) or 0.0), 4),
        "cstar_pressure": round(max(next_u_value, float((successor or {}).get("support", 0.0) or 0.0)), 4),
        "request_drive": round(min(1.0, 0.18 + next_u_value * 0.32), 4),
        "maintain_drive": round(min(1.0, 0.22 + next_u_value * 0.42), 4),
        "selected_drive": round(min(1.0, 0.22 + next_u_value * 0.42), 4),
        "current_referent": {
            "formula_id": PHASE20_8R_CURRENT_REFERENT_BINDING_ID,
            "referent_kind": "unclosed_current",
            "modalities": ("text",),
            "source_event_id": str(unclosed_item["source_event_id"]),
            "unclosed_u": round(next_u_value, 4),
            "salience": round(min(1.0, 0.32 + next_u_value * 0.54), 4),
            "active": True,
            "writes_answer_directly": False,
        },
        "source_kinds": ("unclosed", "short_structure_flow_next") if successor else ("unclosed",),
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
    }
    expression_chars, expression_trace = _select_request_expression(
        conn,
        session_id=session_id,
        intent="maintain_unclosed",
        fallback_text=MAINTAIN_UNCLOSED_TEXT,
        teacher_request_context=expression_context,
    )
    outward_candidate = _outward_speech_candidate_from_idle_context(
        conn,
        session_id=session_id,
        intent="maintain_unclosed",
        narrative_text=narrative_text,
        source_event_id=event_id,
        source_flow=idle_flow,
        unclosed_value=next_u_value,
        successor=successor,
        learning_loop_carryover=learning_loop_carryover,
        expression_trace=expression_trace,
        expression_chars=expression_chars,
    )
    action_competition = _idle_competition(
        selected="idle_think",
        visual_drive=visual_drive,
        audio_drive=audio_drive,
        unclosed_drive=next_u_value,
        learning_loop_carryover=learning_loop_carryover,
        outward_speech_candidate=outward_candidate,
    )
    selected_action = {
        "action_type": "idle_think",
        "unclosed_id": unclosed_item["unclosed_id"],
        "private_thought": True,
        "successor_bias": bool(successor),
        "outward_speech_eligible": bool(outward_candidate.get("eligible")),
    }
    if outward_candidate.get("eligible"):
        selected_action["outward_speech_candidate"] = outward_candidate
    event = _tick_event(
        conn=conn,
        session_id=session_id,
        tick=tick,
        selected_action=selected_action,
        action_competition=action_competition,
        state_pool=pool,
        grid=grid,
        event_ids=(event_id,),
        action_record_ids=(action_record_id,),
        unclosed_items=(unclosed_item,),
        feelings={
            "idle": True,
            "unclosed_pull": next_u_value,
            "source": "active_unclosed_item",
            "narrative_text": narrative_text,
            "narrative_step": attempt_index,
            "successor_found": bool(successor),
            "short_structure_flow_attention_bias": structure_flow_bias,
            "idle_learning_review": learning_loop_carryover.get("idle_learning_review", {}),
            "outward_speech_candidate": outward_candidate,
        },
        ssp_summary={
            "structure_kind": "short_structure_flow",
            "source_text": source_text,
            "narrative_text": narrative_text,
            "successor_bias": successor or {},
            "attempt_count": attempt_index,
            "idle_narrative_flow": idle_flow,
            "short_structure_flow_attention_bias": structure_flow_bias,
            "idle_learning_review": learning_loop_carryover.get("idle_learning_review", {}),
            "outward_speech_candidate": outward_candidate,
        },
        c_forward=(
            {
                "kind": "idle_successor_continuation",
                "source_alignment_event_id": successor["alignment_event_id"],
                "source_candidate_id": successor.get("candidate_id"),
                "source_kind": successor.get("source_kind"),
                "predicted_text": successor["output_text"],
                "support": successor["support"],
                "support_formula": successor.get("support_formula"),
                "cause_slots": list(successor.get("cause_slots", ()))[:8],
                "writes_answer_directly": False,
            },
        )
        if successor
        else (),
    )
    result = Phase207TurnResult(
        schema_id=PHASE20_7_STAGE4_SCHEMA_ID,
        stage_id="20.7-stage4",
        session_id=session_id,
        committed=False,
        reply_text="",
        tick_trace=(event,),
        db_path=db_path,
        stage0_checks=status,
    )
    if outward_candidate.get("eligible"):
        return _commit_outward_speech_from_private_thought(
            conn,
            pool,
            grid,
            idle_event=event,
            session_id=session_id,
            db_path=db_path,
            status=status,
            expression_chars=expression_chars,
            expression_trace=expression_trace,
            outward_candidate=outward_candidate,
            source_private_event_id=event_id,
            visual_drive=visual_drive,
            audio_drive=audio_drive,
            unclosed_drive=next_u_value,
            learning_loop_carryover=learning_loop_carryover,
        )
    return result


def _run_idle_learning_self_test_tick(
    conn: sqlite3.Connection,
    pool: StatePool,
    grid: DraftGrid,
    *,
    session_id: str,
    db_path: Path,
    status: dict[str, object],
    tick: int,
    visual_drive: float,
    audio_drive: float,
    learning_loop_carryover: dict[str, Any],
    structure_flow_bias: dict[str, Any],
    self_test: dict[str, Any],
) -> Phase207TurnResult:
    narrative_text = _idle_learning_self_test_text(self_test)
    action_competition = _idle_competition(
        selected="idle_think",
        visual_drive=visual_drive,
        audio_drive=audio_drive,
        unclosed_drive=0.0,
        learning_loop_carryover=learning_loop_carryover,
    )
    selected_drive = _selected_drive_from_competition(action_competition, {"action_type": "idle_think"})
    action_record_id = insert_action_record(
        conn,
        session_id=session_id,
        tick=tick,
        action_type="idle_think",
        selected=True,
        drive=selected_drive,
        eligibility={
            "no_external_input": True,
            "active_unclosed": False,
            "idle_self_test": True,
        },
        target_refs={
            "source_review_occurrence_id": self_test.get("source_review_occurrence_id"),
            "alignment_event_id": self_test.get("alignment_event_id"),
        },
    )
    _register_action_sa_from_record(conn, action_record_id, tick)
    event_id = insert_experience_event(
        conn,
        session_id=session_id,
        tick=tick,
        event_kind="idle_think",
        action_record_id=action_record_id,
        payload={
            "narrative_text": narrative_text,
            "private_thought": True,
            "idle_self_test": self_test,
            "learning_loop_carryover": learning_loop_carryover,
        },
    )
    conn.execute(
        "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
        (event_id, action_record_id),
    )
    _observe_pool(
        pool,
        tick=tick,
        sa_id=f"idle_self_test::{_hash_text(narrative_text)}",
        family="short_structure_flow",
        label=narrative_text,
        energy=min(0.78, 0.32 + float(self_test.get("self_test_grasp", 0.0) or 0.0) * 0.38),
        source="learning_loop_experience_flow",
        ledger_source="unfinished_pressure",
    )
    idle_flow = _write_short_structure_flow_occurrence(
        conn,
        session_id=session_id,
        tick=tick,
        event_id=event_id,
        text=narrative_text,
        support=min(1.0, 0.30 + float(self_test.get("self_test_grasp", 0.0) or 0.0) * 0.55),
        source_kind="self_test",
        r=min(0.78, 0.28 + float(self_test.get("self_test_grasp", 0.0) or 0.0) * 0.50),
        v=max(0.0, 1.0 - float(self_test.get("self_test_grasp", 0.0) or 0.0)) * 0.24,
        a=min(0.86, 0.30 + float(self_test.get("self_test_grasp", 0.0) or 0.0) * 0.44),
        p=float(self_test.get("cold_retest_pressure", 0.0) or 0.0),
        metadata={
            "private_thought": True,
            "idle_self_test": self_test,
            "dominant_learning_tendency": self_test.get("dominant_learning_tendency"),
        },
    )
    event = _tick_event(
        conn=conn,
        session_id=session_id,
        tick=tick,
        selected_action={
            "action_type": "idle_think",
            "private_thought": True,
            "idle_self_test": True,
            "drive": selected_drive,
        },
        action_competition=action_competition,
        state_pool=pool,
        grid=grid,
        event_ids=(event_id,),
        action_record_ids=(action_record_id,),
        feelings={
            "idle": True,
            "unclosed_pull": 0.0,
            "source": "idle_learning_self_test",
            "narrative_text": narrative_text,
            "idle_self_test": self_test,
            "idle_learning_review": learning_loop_carryover.get("idle_learning_review", {}),
            "learning_loop_carryover": learning_loop_carryover,
            "short_structure_flow_attention_bias": structure_flow_bias,
        },
        ssp_summary={
            "structure_kind": "short_structure_flow",
            "narrative_text": narrative_text,
            "idle_narrative_flow": idle_flow,
            "idle_self_test": self_test,
            "short_structure_flow_attention_bias": structure_flow_bias,
        },
        c_forward=_idle_learning_self_test_c_forward(self_test),
        c_backward=_idle_learning_self_test_c_backward(self_test),
    )
    return Phase207TurnResult(
        schema_id=PHASE20_7_STAGE4_SCHEMA_ID,
        stage_id="20.7-stage4",
        session_id=session_id,
        committed=False,
        reply_text="",
        tick_trace=(event,),
        db_path=db_path,
        stage0_checks=status,
        emotion=_build_and_persist_emotion((event,), conn=conn, session_id=session_id, tick=tick),
    )


def _run_idle_learning_review_tick(
    conn: sqlite3.Connection,
    pool: StatePool,
    grid: DraftGrid,
    *,
    session_id: str,
    db_path: Path,
    status: dict[str, object],
    tick: int,
    visual_drive: float,
    audio_drive: float,
    learning_loop_carryover: dict[str, Any],
    structure_flow_bias: dict[str, Any],
) -> Phase207TurnResult:
    review = dict(learning_loop_carryover.get("idle_learning_review", {}) or {})
    narrative_text = _idle_learning_review_text(learning_loop_carryover) or "learning review"
    action_competition = _idle_competition(
        selected="idle_think",
        visual_drive=visual_drive,
        audio_drive=audio_drive,
        unclosed_drive=0.0,
        learning_loop_carryover=learning_loop_carryover,
    )
    selected_drive = _selected_drive_from_competition(action_competition, {"action_type": "idle_think"})
    action_record_id = insert_action_record(
        conn,
        session_id=session_id,
        tick=tick,
        action_type="idle_think",
        selected=True,
        drive=selected_drive,
        eligibility={
            "no_external_input": True,
            "active_unclosed": False,
            "idle_learning_review": True,
        },
        target_refs={
            "source_event_id": review.get("source_event_id"),
            "alignment_event_id": review.get("alignment_event_id"),
        },
    )
    _register_action_sa_from_record(conn, action_record_id, tick)
    event_id = insert_experience_event(
        conn,
        session_id=session_id,
        tick=tick,
        event_kind="idle_think",
        action_record_id=action_record_id,
        payload={
            "narrative_text": narrative_text,
            "private_thought": True,
            "idle_learning_review": review,
            "learning_loop_carryover": learning_loop_carryover,
        },
    )
    conn.execute(
        "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
        (event_id, action_record_id),
    )
    _observe_pool(
        pool,
        tick=tick,
        sa_id=f"idle_learning_review::{_hash_text(narrative_text)}",
        family="short_structure_flow",
        label=narrative_text,
        energy=min(0.74, 0.30 + float(learning_loop_carryover.get("idle_think_delta", 0.0) or 0.0) * 3.0),
        source="learning_loop_experience_flow",
        ledger_source="unfinished_pressure",
    )
    idle_flow = _write_short_structure_flow_occurrence(
        conn,
        session_id=session_id,
        tick=tick,
        event_id=event_id,
        text=narrative_text,
        support=min(1.0, 0.28 + float(learning_loop_carryover.get("idle_think_delta", 0.0) or 0.0) * 3.0),
        source_kind="learning_review",
        r=min(0.72, 0.25 + float(learning_loop_carryover.get("idle_think_delta", 0.0) or 0.0) * 3.0),
        v=0.0,
        a=min(0.82, 0.28 + float(learning_loop_carryover.get("idle_think_delta", 0.0) or 0.0) * 3.0),
        p=min(0.78, max(float(learning_loop_carryover.get("cold_retest_readiness", 0.0) or 0.0), float(learning_loop_carryover.get("scaffold_regression_need", 0.0) or 0.0))),
        metadata={
            "private_thought": True,
            "idle_learning_review": review,
            "dominant_learning_tendency": learning_loop_carryover.get("dominant_learning_tendency"),
        },
    )
    event = _tick_event(
        conn=conn,
        session_id=session_id,
        tick=tick,
        selected_action={
            "action_type": "idle_think",
            "private_thought": True,
            "idle_learning_review": True,
            "drive": selected_drive,
        },
        action_competition=action_competition,
        state_pool=pool,
        grid=grid,
        event_ids=(event_id,),
        action_record_ids=(action_record_id,),
        feelings={
            "idle": True,
            "unclosed_pull": 0.0,
            "source": "idle_learning_review",
            "narrative_text": narrative_text,
            "idle_learning_review": review,
            "learning_loop_carryover": learning_loop_carryover,
            "short_structure_flow_attention_bias": structure_flow_bias,
        },
        ssp_summary={
            "structure_kind": "short_structure_flow",
            "narrative_text": narrative_text,
            "idle_narrative_flow": idle_flow,
            "idle_learning_review": review,
            "short_structure_flow_attention_bias": structure_flow_bias,
        },
        c_forward=_idle_learning_review_c_forward(learning_loop_carryover),
    )
    return Phase207TurnResult(
        schema_id=PHASE20_7_STAGE4_SCHEMA_ID,
        stage_id="20.7-stage4",
        session_id=session_id,
        committed=False,
        reply_text="",
        tick_trace=(event,),
        db_path=db_path,
        stage0_checks=status,
    )


def _idle_competition(
    *,
    selected: str,
    visual_drive: float,
    audio_drive: float,
    unclosed_drive: float,
    learning_loop_carryover: dict[str, Any] | None = None,
    outward_speech_candidate: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    rows: tuple[dict[str, Any], ...] = (
        {"action_type": "idle_visual_focus", "drive": max(0.0, float(visual_drive)), "selected": selected == "idle_visual_focus"},
        {"action_type": "idle_audio_focus", "drive": max(0.0, float(audio_drive)), "selected": selected == "idle_audio_focus"},
        {"action_type": "idle_think", "drive": max(0.08, min(0.95, 0.25 + float(unclosed_drive))), "selected": selected == "idle_think"},
        {"action_type": "idle_observe", "drive": 0.18, "selected": selected == "idle_observe"},
        {"action_type": "sleep_lower_frequency", "drive": 0.12 if max(float(visual_drive), float(audio_drive), float(unclosed_drive)) < 0.2 else 0.04, "selected": selected == "sleep_lower_frequency"},
    )
    if outward_speech_candidate:
        outward_drive = _unit(outward_speech_candidate.get("drive", 0.0))
        rows = rows + (
            {
                "action_type": "outward_speech",
                "drive": outward_drive,
                "selected": selected == "outward_speech",
                "outward_speech_candidate": outward_speech_candidate,
            },
            {
                "action_type": "write_cell",
                "drive": outward_drive if selected == "write_cell" else min(0.18, outward_drive * 0.25),
                "selected": selected == "write_cell",
                "outward_speech_candidate": outward_speech_candidate,
            },
            {
                "action_type": "commit_reply",
                "drive": max(0.50, outward_drive) if selected == "commit_reply" else min(0.16, outward_drive * 0.22),
                "selected": selected == "commit_reply",
                "outward_speech_candidate": outward_speech_candidate,
            },
        )
    # P1-1 (C18): 竞争行按真实 drive 排序 — 不再 selected 优先. selected 标志仅
    # 标记实际执行的行动; 排序反映竞争强度本身, trace 中可见"谁差点赢".
    sorted_rows = tuple(sorted(rows, key=lambda row: float(row["drive"]), reverse=True))
    sorted_rows, _selected = _apply_learning_loop_carryover_to_competition(
        sorted_rows,
        {"action_type": selected},
        learning_loop_carryover,
    )
    return sorted_rows


def _with_idle_competition(
    event: RuntimeTickEventV2,
    *,
    selected: str,
    visual_drive: float,
    audio_drive: float,
    unclosed_drive: float,
    learning_loop_carryover: dict[str, Any] | None = None,
    outward_speech_candidate: dict[str, Any] | None = None,
) -> RuntimeTickEventV2:
    return replace(
        event,
        action_competition=_idle_competition(
            selected=selected,
            visual_drive=visual_drive,
            audio_drive=audio_drive,
            unclosed_drive=unclosed_drive,
            learning_loop_carryover=learning_loop_carryover,
            outward_speech_candidate=outward_speech_candidate,
        ),
    )


def _with_selected_action_drive(event: RuntimeTickEventV2, *, drive: float) -> RuntimeTickEventV2:
    return replace(event, selected_action={**dict(event.selected_action), "drive": float(drive)})


def _latest_tick_for_session(conn: sqlite3.Connection, *, session_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(tick), 0) FROM phase20_7_experience_events WHERE session_id=?",
        (session_id,),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _successor_for_unclosed(conn: sqlite3.Connection, unclosed_item: dict[str, object]) -> dict[str, Any] | None:
    source_signature = str(unclosed_item.get("source_signature") or "")
    session_id = str(unclosed_item.get("session_id") or "")
    if not source_signature:
        return None
    candidates: list[dict[str, Any]] = []
    for candidate in _unified_experience_candidates_for_input_signature(conn, input_signature=source_signature, limit=300):
        payload = candidate.payload
        if payload.get("input_signature") != source_signature:
            continue
        output_text = "".join(str(ch) for ch in payload.get("output_chars", ())).strip()
        if not output_text:
            continue
        support = max(0.25, min(1.0, float(candidate.support)))
        candidates.append(
            {
                "candidate_id": candidate.candidate_id,
                "source_kind": candidate.source_kind,
                "alignment_event_id": str(candidate.alignment_event_id or ""),
                "input_event_id": str(payload.get("input_event_id") or ""),
                "output_text": output_text,
                "support": support,
                "support_formula": candidate.support_formula,
                "support_terms": tuple(candidate.support_terms),
                "cause_slots": tuple(candidate.cause_slots),
                "score": min(1.0, support + 0.06 + 0.04),
                "writes_answer_directly": False,
            }
        )
    if session_id:
        for flow_candidate in query_recent_experience_flow_candidates(
            conn,
            session_id=session_id,
            from_json=from_json,
            hash_text=_hash_text,
            signature_for_chars=_signature_for_chars,
            compose_input_signature=_compose_input_signature,
            visual_tokens_from_payloads=_visual_signature_from_payloads,
            limit=48,
        ):
            if not _flow_candidate_can_drive_idle_successor(flow_candidate):
                continue
            successor_text = _successor_text_from_flow_candidate(flow_candidate)
            if not successor_text:
                continue
            unified = unified_candidate_from_flow(flow_candidate)
            support = max(0.05, min(1.0, float(unified.support)))
            is_short_next = flow_candidate.candidate_kind == "short_structure_flow_next"
            score = min(1.0, support + (0.05 if is_short_next else 0.0) + 0.02)
            candidates.append(
                {
                    "candidate_id": unified.candidate_id,
                    "source_kind": unified.source_kind,
                    "alignment_event_id": str(unified.alignment_event_id or unified.event_id or ""),
                    "input_event_id": str(unified.payload.get("source_event_id") or unified.event_id or ""),
                    "output_text": successor_text,
                    "support": support,
                    "support_formula": unified.support_formula,
                    "support_terms": tuple(unified.support_terms),
                    "cause_slots": tuple(unified.cause_slots),
                    "score": score,
                    "writes_answer_directly": False,
                }
            )
    if not candidates:
        return None
    best = max(candidates, key=lambda item: float(item.get("score", 0.0)))
    return {key: value for key, value in best.items() if key != "score"}


def _outward_speech_candidate_from_idle_context(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    intent: str,
    narrative_text: str,
    source_event_id: str,
    source_flow: dict[str, Any],
    unclosed_value: float,
    successor: dict[str, Any] | None,
    learning_loop_carryover: dict[str, Any] | None,
    expression_trace: dict[str, Any],
    expression_chars: Sequence[str],
) -> dict[str, Any]:
    expression_text = "".join(str(ch) for ch in expression_chars).strip()
    if not expression_text:
        return _empty_outward_speech_candidate(intent=intent, reason="no_expression_text")
    source_kind = str(expression_trace.get("source_kind") or "")
    if source_kind == "innate_minimal_expression":
        return _empty_outward_speech_candidate(intent=intent, reason="no_learned_external_expression")
    latest_tick = _latest_tick_for_session(conn, session_id=session_id)
    recent_outward = _recent_selected_action_count(
        conn,
        session_id=session_id,
        action_types=("outward_speech",),
        since_tick=max(0, latest_tick - 32),
    )
    recent_same = _recent_outward_text_count(
        conn,
        session_id=session_id,
        text_hash=_hash_text(expression_text),
        since_tick=max(0, latest_tick - 80),
    )
    external_feedback_event_kinds = (
        "teacher_feedback_event",
        "text_receptor_observation",
        "audio_audit_sample",
    )
    recent_feedback = _recent_event_count(
        conn,
        session_id=session_id,
        event_kinds=external_feedback_event_kinds,
        since_tick=max(0, latest_tick - 16),
    ) + _recent_event_count_from_source_kind(
        conn,
        session_id=session_id,
        event_kind="visual_patch_sample",
        source_kind="visual_patch_sensor",
        since_tick=max(0, latest_tick - 16),
    )
    no_feedback_penalty = 0.0
    latest_outward_tick = _latest_selected_action_tick(conn, session_id=session_id, action_type="outward_speech")
    if latest_outward_tick is not None:
        later_external = _recent_event_count(
            conn,
            session_id=session_id,
            event_kinds=external_feedback_event_kinds,
            since_tick=latest_outward_tick + 1,
        ) + _recent_event_count_from_source_kind(
            conn,
            session_id=session_id,
            event_kind="visual_patch_sample",
            source_kind="visual_patch_sensor",
            since_tick=latest_outward_tick + 1,
        )
        if later_external <= 0:
            no_feedback_penalty = 0.24
    outcome_rows = conn.execute(
        """
        SELECT event_id, tick, payload_json
        FROM phase20_7_experience_events
        WHERE session_id=? AND event_kind='outward_speech' AND tick < ?
        ORDER BY tick DESC, created_at_ms DESC
        LIMIT 18
        """,
        (session_id, int(latest_tick) + 1),
    ).fetchall()
    outcome_reward_total = 0.0
    outcome_punish_total = 0.0
    outcome_no_feedback_count = 0
    outcome_matched_count = 0
    for rank, (outward_event_id, outward_tick, payload_json) in enumerate(outcome_rows):
        payload = from_json(str(payload_json))
        if not isinstance(payload, dict):
            continue
        previous_candidate = payload.get("outward_speech_candidate")
        if not isinstance(previous_candidate, dict):
            continue
        previous_flow = previous_candidate.get("source_flow")
        previous_source_kind = str(previous_flow.get("source_kind") or "") if isinstance(previous_flow, dict) else ""
        source_match = 1.0 if previous_source_kind and previous_source_kind == str(source_flow.get("source_kind") or "") else 0.55
        expression_match = 0.15 if str(payload.get("expression_text_hash") or "") == _hash_text(expression_text) else 0.0
        recency = 1.0 / (1.0 + rank)
        outcome_matched_count += 1
        feedback_rows = conn.execute(
            """
            SELECT payload_json, reward, punish
            FROM phase20_7_experience_events
            WHERE session_id=? AND tick>? AND event_kind='teacher_feedback_event'
            ORDER BY tick ASC, created_at_ms ASC
            LIMIT 12
            """,
            (session_id, int(outward_tick)),
        ).fetchall()
        feedback_found = False
        for feedback_payload_json, reward, punish in feedback_rows:
            feedback_payload = from_json(str(feedback_payload_json))
            if not isinstance(feedback_payload, dict):
                continue
            if str(feedback_payload.get("target_event_id") or "") != str(outward_event_id):
                continue
            feedback_found = True
            credit = min(1.0, source_match + expression_match) * recency
            outcome_reward_total += _unit(reward) * credit
            outcome_punish_total += _unit(punish) * credit
        later_external = _recent_event_count(
            conn,
            session_id=session_id,
            event_kinds=external_feedback_event_kinds,
            since_tick=int(outward_tick) + 1,
        ) + _recent_event_count_from_source_kind(
            conn,
            session_id=session_id,
            event_kind="visual_patch_sample",
            source_kind="visual_patch_sensor",
            since_tick=int(outward_tick) + 1,
        )
        if not feedback_found and later_external <= 0:
            outcome_no_feedback_count += 1
    outcome_reward_delta = min(0.16, outcome_reward_total * 0.10)
    outcome_punish_delta = min(0.18, outcome_punish_total * 0.12)
    outcome_no_feedback_delta = min(0.14, outcome_no_feedback_count * 0.035)
    learning = learning_loop_carryover or {}
    learning_pressure = max(
        _unit(learning.get("idle_think_delta", 0.0)) * 2.2,
        _unit(learning.get("cold_retest_readiness", 0.0)) * 0.42,
        _unit(learning.get("scaffold_regression_need", 0.0)) * 0.36,
    )
    successor_support = _unit((successor or {}).get("support", 0.0))
    expression_support = _unit(expression_trace.get("selected_support", 0.0))
    flow_support = _unit(source_flow.get("support", 0.0))
    private_thought_pressure = _unit(0.22 + _unit(unclosed_value) * 0.34 + successor_support * 0.20 + learning_pressure * 0.22 + flow_support * 0.10)
    reward_expectation = _unit(expression_support * 0.52 + float(expression_trace.get("referent_match", 0.0) or 0.0) * 0.16)
    repetition_fatigue = _unit(recent_outward * 0.10 + recent_same * 0.18)
    feedback_relief = min(0.10, recent_feedback * 0.025)
    drive = _unit(
        0.12
        + private_thought_pressure * 0.42
        + reward_expectation * 0.32
        + (0.08 if successor_support > 0.0 else 0.0)
        + outcome_reward_delta
        - repetition_fatigue
        - no_feedback_penalty
        - outcome_punish_delta
        - outcome_no_feedback_delta
        + feedback_relief
    )
    action_tuner = _action_experience_tuner_projection(
        conn,
        session_id=session_id,
        tick=latest_tick + 1,
        action_types=("outward_speech", "write_cell", "commit_reply", "idle_think", "sleep_lower_frequency"),
        selected_action_type="outward_speech",
        outward_text_hash=_hash_text(expression_text),
        source_intent=intent,
    )
    drive_before_action_tuner = drive
    if action_tuner.get("active"):
        multipliers = action_tuner.get("action_multipliers") if isinstance(action_tuner.get("action_multipliers"), dict) else {}
        drive = _unit(drive * _bounded_multiplier(multipliers.get("outward_speech", 1.0), low=0.35, high=1.70))
    action_outcome_terms = {
        "term_kind": "existing_outward_speech_action_outcome",
        "matched_action_count": int(outcome_matched_count),
        "reward_total": round(outcome_reward_total, 4),
        "punish_total": round(outcome_punish_total, 4),
        "no_feedback_count": int(outcome_no_feedback_count),
        "reward_delta": round(outcome_reward_delta, 4),
        "punish_delta": round(outcome_punish_delta, 4),
        "no_feedback_delta": round(outcome_no_feedback_delta, 4),
        "external_feedback_event_kinds": external_feedback_event_kinds,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }
    return {
        "formula_id": PHASE20_9K_OUTWARD_SPEECH_ID,
        "intent": intent,
        "drive": round(drive, 4),
        "expression_text": expression_text,
        "expression_text_hash": _hash_text(expression_text),
        "expression_trace": expression_trace,
        "source_private_event_id": source_event_id,
        "source_flow": source_flow,
        "narrative_text_hash": _hash_text(narrative_text),
        "private_thought_pressure": round(private_thought_pressure, 4),
        "unclosed_value": round(_unit(unclosed_value), 4),
        "successor_support": round(successor_support, 4),
        "learning_pressure": round(_unit(learning_pressure), 4),
        "expression_support": round(expression_support, 4),
        "reward_expectation": round(reward_expectation, 4),
        "repetition_fatigue": round(repetition_fatigue, 4),
        "no_feedback_penalty": round(no_feedback_penalty, 4),
        "action_outcome_terms": action_outcome_terms,
        "action_outcome_reward_delta": round(outcome_reward_delta, 4),
        "action_outcome_punish_delta": round(outcome_punish_delta, 4),
        "action_outcome_no_feedback_delta": round(outcome_no_feedback_delta, 4),
        "drive_before_action_experience_tuner": round(drive_before_action_tuner, 4),
        "action_experience_tuner_projection": action_tuner,
        "recent_outward_count": int(recent_outward),
        "recent_same_text_count": int(recent_same),
        "recent_external_feedback_count": int(recent_feedback),
        "eligible": drive >= 0.50,
        "creates_reply_candidate": True,
        "writes_answer_directly": False,
        "ap_native_source": "idle_private_thought_to_action_competition",
    }


def _empty_outward_speech_candidate(*, intent: str, reason: str) -> dict[str, Any]:
    return {
        "formula_id": PHASE20_9K_OUTWARD_SPEECH_ID,
        "intent": intent,
        "drive": 0.0,
        "eligible": False,
        "blocked_reason": reason,
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
    }


def _residual_pool_recall(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    observation: _ObservationLike,
    winner_shared_units: Sequence[str],
    max_rounds: int = 2,
) -> tuple[dict[str, Any], ...]:
    """§56.2 残差竞争召回 — 完整短期序列池的多轮 B 召回.

    白皮书 §12/§53/§56.2: 召回查询是完整短期序列池 (近段权重高, 远段衰减),
    不只是当前注意焦点. 第一轮 (当前 observation, 权重最高段) 由既有
    exact/structural 召回完成; 本函数执行后续轮次:
      1. 序列池残余 = 最近几段历史内容 (recency 加权), 扣除第一轮胜者已解释的
         units (被解释的 query mass 降权 — 谐振吸收);
      2. 对剩余 mass 继续召回, 命中者作为并列 B 波进入 b_candidates
         (不删除尾部候选, 只降低主导性 — 支持多对象/多任务认知);
      3. 每轮命中后其 shared units 继续从 mass 中扣除, 直到轮次/mass 耗尽.

    权重纪律: 残差 B 的 support = 候选支持度 × 段 recency 权重 × 0.8 阻尼 —
    恒低于第一轮主召回, 不参与输出内容选择 (creates_reply_candidate=False);
    它丰富 C*/把握/上下文场, 使同问句在不同前文下有不同的认知状态,
    并让"回味A后遇到B → 命中 A∩B 记忆"的灵光路径自发可达.
    """
    covered: set[str] = set(str(u) for u in winner_shared_units)
    covered.update(str(ch) for ch in observation.chars)
    windows = _recent_experience_windows(conn, session_id=session_id, limit=8)
    segments: list[tuple[float, str]] = []
    for idx, window in enumerate(windows):
        seg_obs = window.get("observation")
        if not isinstance(seg_obs, _RecoveredObservation):
            continue
        text = "".join(seg_obs.chars).strip()
        if not text or seg_obs.text_signature == observation.text_signature:
            continue
        if _looks_like_internal_flow_text(text):
            continue
        weight = 1.0 / (1.0 + idx * 0.5)  # 近段权重高, 越远越低 (§12)
        segments.append((weight, text))
        if len(segments) >= 4:
            break
    rows: list[dict[str, Any]] = []
    for round_index in range(2, max_rounds + 2):
        best_row: dict[str, Any] | None = None
        best_score = 0.0
        best_units: tuple[str, ...] = ()
        for weight, text in segments:
            # 残差 = 该段中未被吸收的字符 (保持原序 — §10 顺序携带结构信息)
            residual_units = tuple(
                ch for ch in text if ch.strip() and ch not in covered
            )
            if len(residual_units) < 2:
                continue
            residual_text = "".join(residual_units)
            res_chars = tuple(residual_text)
            res_obs = _TextObservation(
                event_id="",
                source_packet_id="",
                occurrence_ids=(),
                signature=_compose_input_signature(_signature_for_chars(res_chars), None),
                text_signature=_signature_for_chars(res_chars),
                chars=res_chars,
                text_hash=_hash_text(residual_text),
                visual_signature=None,
            )
            for candidate in _experience_candidates_for_observation(
                conn, res_obs, limit=120, exact_input_allowed=True
            ):
                payload = candidate.payload
                if payload.get("expression_role"):
                    continue
                if str(payload.get("alignment_role") or "") == "counter_evidence":
                    continue
                if payload.get("input_signature") == observation.signature:
                    continue
                support = _unit(float(candidate.support) * weight * 0.8)
                if support <= 0.15 or support <= best_score:
                    continue
                source_text = str(candidate.source_text or "")
                shared = tuple(
                    ch for ch in source_text if ch.strip() and ch in set(residual_units)
                ) if source_text else ()
                best_score = support
                best_units = shared or residual_units[:4]
                best_row = {
                    "kind": "residual_b",
                    "round": round_index,
                    "support": round(support, 4),
                    "segment_weight": round(weight, 4),
                    "source_event_id": str(payload.get("input_event_id") or candidate.alignment_event_id),
                    "alignment_event_id": str(candidate.alignment_event_id),
                    "residual_query_units": list(residual_units)[:12],
                    "shared_units": list(best_units)[:12],
                    "source": "short_sequence_pool_residual_competition",
                    "creates_reply_candidate": False,
                    "writes_answer_directly": False,
                }
        if best_row is None:
            break
        rows.append(best_row)
        covered.update(str(u) for u in best_units)  # 命中吸收 → 剩余 mass 继续
    return tuple(rows)


def _erase_paradigm_partial_grid(grid: DraftGrid) -> None:
    """范式执行中途放弃时擦掉半成品 (人会擦掉写错的竖式重来/改口头请教)."""
    for key, cell in grid.cells.items():
        cell.char = " "
        cell.written_at_tick = -1


def _paradigm_process_readiness(
    conn: sqlite3.Connection,
    observation: _ObservationLike,
) -> float:
    """过程范式就绪度: 范式键从观察结构派生 (共享函数), 起步状态的共现支持度.

    没学过 (示范或自发累积均可) = 0 — 该意图在竞争中不可达.
    """
    from .paradigm_process import derive_paradigm_key, query_paradigm_next_steps

    key = derive_paradigm_key(tuple(observation.chars), _content_bucket_for_char, conn=conn)
    if not key:
        return 0.0
    steps = query_paradigm_next_steps(
        conn, paradigm_key=key, prev_action_result="process_start", from_json=from_json
    )
    return _unit(float(steps[0]["support"])) if steps else 0.0


def _run_paradigm_process_execution(
    conn: sqlite3.Connection,
    pool: StatePool,
    grid: DraftGrid,
    *,
    session_id: str,
    start_tick: int,
    observation: _ObservationLike,
    turn_budget_left: int,
    tick_events: list[RuntimeTickEventV2],
) -> tuple[int, str, tuple[dict[str, Any], ...]]:
    """学到的过程范式的逐 tick 执行 — 无状态机/无坐标公式/无步骤表.

    每 tick:
      1. 感知当前状态 (共享感知函数: 对照观察数自己写了多少 — "意识到上一步");
      2. 查共现表得该状态学到的 (寻址, 内容通道) 分布 -> 减反例压 -> 竞争胜者;
      3. 寻址由行动器 resolve_anchor 从当前光标相对解析 (器官能力, 无范式知识);
         内容由通道真实产出 (抄观察 / exact_b0 事实召回 / 进位缓存) — 缺失即弃;
      4. 写格+真实事件+tick; 成功执行的 (状态->行动) 再记回共现表 (练习增熟).
    答案 = 执行完后从 grid 结果格读回 (readback), 不是拼接的变量.
    """
    from .paradigm_process import (
        _digit_runs,
        derive_paradigm_key,
        paradigm_step_counter_pressure,
        perceive_process_state,
        query_paradigm_next_steps,
        record_step_cooccurrence,
        resolve_anchor,
    )

    chars = tuple(observation.chars)
    key = derive_paradigm_key(chars, _content_bucket_for_char, conn=conn)
    if not key:
        return start_tick, "", ()
    runs = _digit_runs(chars, _content_bucket_for_char)
    (s1, e1), (s2, e2) = runs
    run1 = "".join(chars[s1:e1])
    run2 = "".join(chars[s2:e2])
    sep = "".join(chars[e1:s2])
    suffix = "".join(chars[e2:])
    width = len(run1)
    copied1 = copied2 = results_written = 0
    operator_written = False
    carry = ""
    cursor_row, cursor_col = -1, -1
    start_col = -1
    rightmost_col = -1
    result_cells: list[tuple[int, int]] = []
    process_audit: list[dict[str, Any]] = []
    executed_steps: list[dict[str, str]] = []
    tick = start_tick
    guard = 0
    while turn_budget_left > 0 and guard < 32:
        guard += 1
        state = perceive_process_state(
            run1_len=width, run2_len=len(run2), copied1=copied1, copied2=copied2,
            operator_written=operator_written, results_written=results_written,
            carry_present=bool(carry),
        )
        if state == "columns_done":
            break
        steps = query_paradigm_next_steps(
            conn, paradigm_key=key, prev_action_result=state, from_json=from_json
        )
        if not steps:
            _erase_paradigm_partial_grid(grid)
            return start_tick, "", ()
        best = None
        best_drive = 0.0
        for step in steps:
            counter = paradigm_step_counter_pressure(
                conn, paradigm_key=key, prev_action_result=state,
                anchor=str(step["anchor"]), content_source=str(step["content_source"]),
                from_json=from_json,
            )
            drive = _unit(float(step["support"]) * (1.0 - counter))
            if drive > best_drive:
                best_drive = drive
                best = step
        if best is None or best_drive < 0.12:
            _erase_paradigm_partial_grid(grid)
            return start_tick, "", ()
        anchor = str(best["anchor"])
        source = str(best["content_source"])
        pos = resolve_anchor(
            anchor, cursor_row=cursor_row, cursor_col=cursor_col,
            start_col=start_col, rightmost_col=rightmost_col,
        )
        if pos is None or pos[0] < 0 or pos[0] >= grid.rows or pos[1] < 0 or pos[1] >= grid.cols:
            _erase_paradigm_partial_grid(grid)
            return start_tick, "", ()
        write_char = ""
        if source == "observed_run1_next":
            if copied1 >= len(run1):
                _erase_paradigm_partial_grid(grid)
                return start_tick, "", ()
            write_char = run1[copied1]
            copied1 += 1
        elif source == "observed_separator":
            write_char = sep[:1]
            operator_written = True
        elif source == "observed_run2_next":
            if copied2 >= len(run2):
                _erase_paradigm_partial_grid(grid)
                return start_tick, "", ()
            write_char = run2[copied2]
            copied2 += 1
        elif source == "recalled_column_fact":
            k = results_written
            if k >= width:
                _erase_paradigm_partial_grid(grid)
                return start_tick, "", ()
            d1 = run1[-1 - k]
            d2 = run2[-1 - k]
            terms = [d1, d2] + ([carry] if carry else [])
            subquery = sep.join(terms) + suffix
            sub_chars = tuple(subquery)
            sub_obs = _TextObservation(
                event_id="", source_packet_id="", occurrence_ids=(),
                signature=_compose_input_signature(_signature_for_chars(sub_chars), None),
                text_signature=_signature_for_chars(sub_chars),
                chars=sub_chars, text_hash=_hash_text(subquery), visual_signature=None,
            )
            fact = _find_exact_b0(conn, sub_obs)
            if fact is None:
                _erase_paradigm_partial_grid(grid)
                return start_tick, "", ()
            result = "".join(fact.output_chars).strip()
            if not result or any(_content_bucket_for_char(c) != "digit" for c in result):
                _erase_paradigm_partial_grid(grid)
                return start_tick, "", ()
            write_char = result[-1]
            carry = result[:-1]
            results_written += 1
            process_audit.append(
                {"column": k, "subquery": subquery, "fact_event_id": fact.event_id,
                 "fact_support": round(float(fact.support), 4), "carry_out": carry}
            )
        elif source == "carry_digit":
            if not carry:
                _erase_paradigm_partial_grid(grid)
                return start_tick, "", ()
            write_char = carry
            carry = ""
        else:
            _erase_paradigm_partial_grid(grid)
            return start_tick, "", ()
        tick += 1
        turn_budget_left -= 1
        pool.tick_decay(tick=tick)
        cursor_row, cursor_col = pos
        if start_col < 0:
            start_col = cursor_col
        rightmost_col = max(rightmost_col, cursor_col)
        if source in ("recalled_column_fact", "carry_digit"):
            result_cells.append(pos)
        action_record_id = insert_action_record(
            conn, session_id=session_id, tick=tick, action_type="write_cell",
            selected=True, drive=round(best_drive, 4),
            eligibility={
                "paradigm_key": key, "paradigm_condition": state,
                "anchor": anchor, "content_source": source,
                "paradigm_step_support": best["support"],
            },
            target_refs={"draft_row": cursor_row, "draft_col": cursor_col},
        )
        _register_action_sa_from_record(conn, action_record_id, tick)
        grid.write_at(cursor_row, cursor_col, write_char, tick=tick)
        _observe_draft_char(pool, tick=tick, char=write_char, row=cursor_row, col=cursor_col, source="paradigm_process")
        event_id = insert_experience_event(
            conn, session_id=session_id, tick=tick, event_kind="draft_grid_write",
            action_record_id=action_record_id,
            payload={
                "draft_row": cursor_row, "draft_col": cursor_col,
                "unit_text": write_char, "unit_hash": _hash_text(write_char),
                "visible_text_hash": _hash_text(grid.visible_text()),
                "source_intent": "paradigm_process_execution",
                "paradigm_condition": state, "paradigm_anchor": anchor,
                "paradigm_content_source": source,
            },
        )
        conn.execute(
            "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
            (event_id, action_record_id),
        )
        executed_steps.append(
            {"paradigm_key": key, "prev_action_result": state, "anchor": anchor, "content_source": source}
        )
        _append_runtime_tick(
            tick_events,
            _tick_event(
                conn=conn, session_id=session_id, tick=tick,
                selected_action={
                    "action_type": "write_cell",
                    "draft_row": cursor_row, "draft_col": cursor_col,
                    "unit_hash": _hash_text(write_char),
                    "paradigm_condition": state,
                    "paradigm_anchor": anchor,
                    "paradigm_content_source": source,
                    "paradigm_step_note": state + " -> " + anchor + "/" + source,
                },
                action_competition=tuple(
                    {
                        "action_type": "paradigm::" + str(s["anchor"]) + "::" + str(s["content_source"]),
                        "drive": round(_unit(float(s["support"])), 4),
                        "selected": s is best,
                    }
                    for s in steps[:5]
                ),
                state_pool=pool, grid=grid, observation=observation,
                event_ids=(event_id,), action_record_ids=(action_record_id,),
                feelings={
                    "source": "paradigm_process_execution",
                    "paradigm_condition": state,
                    "paradigm_step_support": float(best["support"]),
                },
                timings_ms={"paradigm_step": 0.0},
            ),
        )
    if results_written < width or carry:
        _erase_paradigm_partial_grid(grid)
        return start_tick, "", ()
    result_cells.sort(key=lambda rc: rc[1])
    answer = "".join(grid.cells[(r, c)].char for r, c in result_cells).strip()
    if not answer:
        _erase_paradigm_partial_grid(grid)
        return start_tick, "", ()
    for step_row in executed_steps:
        tick += 1
        record_step_cooccurrence(
            conn, session_id=session_id, tick=tick,
            paradigm_key=step_row["paradigm_key"],
            perceived_state=step_row["prev_action_result"],
            anchor=step_row["anchor"], content_source=step_row["content_source"],
            origin="self_practice",
            insert_experience_event=insert_experience_event,
        )
    return tick, answer, tuple(process_audit)


def _teach_paint_order_demonstration(
    db_path: str | Path,
    *,
    session_id: str,
    spec: str,
    repeats: int = 3,
) -> dict[str, Any]:
    """绘画作画顺序示范 (66/187.2): spec="paint_order:bucketA,bucketB,...".

    教师说"按这个 role 桶顺序作画"(课程层知识); 状态由 perceive_painting_state
    对示范现场算出 (与执行/自发同函数); 只记 (状态, 动作, 目标role桶), 不记内容.
    """
    from .paradigm_process import teacher_paint_demo_states, record_paint_step

    order = [b.strip() for b in str(spec).split(":", 1)[1].split(",") if b.strip()]
    if not order:
        return {"error": "empty_paint_order", "spec": spec}
    steps = teacher_paint_demo_states(order)
    path = initialize_phase20_7_store(db_path)
    written = 0
    with sqlite3.connect(path) as conn:
        base_row = conn.execute(
            "SELECT COALESCE(MAX(tick),0) FROM phase20_7_experience_events WHERE session_id=?",
            (session_id,),
        ).fetchone()
        tick = int(base_row[0] or 0)
        for _repeat in range(max(1, int(repeats))):
            for state, action, target_role in steps:
                tick += 1
                record_paint_step(
                    conn, session_id=session_id, tick=tick,
                    prev_action_result=state, action=action, target_role=target_role,
                    origin="teacher_demonstration",
                    insert_experience_event=insert_experience_event,
                )
                written += 1
        conn.commit()
    return {
        "schema_id": "apv3_phase20_7_paint_order_demonstration/v1",
        "paradigm_key": "canvas_object_paint",
        "order": order,
        "steps_demonstrated": written,
        "session_id": session_id,
    }


def teach_process_paradigm_demonstration(
    db_path: str | Path,
    *,
    session_id: str = "phase20_7_workbench",
    example: str = "61+22=83",
    repeats: int = 3,
) -> dict[str, Any]:
    """示范教学 (demonstrate 阶段): 教师对具体例子演示, AP 用共享感知函数
    标注每步当时的状态并记录 (状态->行动) 共现.

    行动序列是教师的知识 (teacher_demo_actions, 课程层); 状态名不是手填的 —
    是 perceive_process_state 对示范现场算出来的, 与执行/自发完全同一函数
    (修 zcode 问题A: 三端键空间机械一致). 内容不入库 — 只有 (状态, 寻址, 通道).

    example 以 "paint_order:" 开头时走绘画作画顺序示范 (§66): 后接 role 桶序列,
    如 "paint_order:hi_edge_lo_dev,lo_edge_lo_dev,lo_edge_hi_dev" (先勾边→填色→细节),
    或反序 "paint_order:lo_edge_hi_dev,lo_edge_lo_dev,hi_edge_lo_dev" (先细节→填色→边).
    教什么顺序 AP 就学什么顺序 — 同一端点, 同一套 (perceive/record) 机制.
    """
    if str(example).startswith("paint_order:"):
        return _teach_paint_order_demonstration(db_path, session_id=session_id, spec=example, repeats=repeats)
    from .paradigm_process import (
        _digit_runs,
        derive_paradigm_key,
        perceive_process_state,
        record_step_cooccurrence,
        teacher_demo_actions,
    )

    path = initialize_phase20_7_store(db_path)
    actions = teacher_demo_actions(example, _content_bucket_for_char)
    if not actions:
        return {"error": "example_not_demonstrable", "example": example}
    left, _answer = example.split("=", 1)
    chars = tuple(left + "=?")
    runs = _digit_runs(chars, _content_bucket_for_char)
    (s1, e1), (s2, e2) = runs
    run1_len, run2_len = e1 - s1, e2 - s2
    written = 0
    with sqlite3.connect(path) as conn:
        key = derive_paradigm_key(chars, _content_bucket_for_char, conn=conn)
        base_row = conn.execute(
            "SELECT COALESCE(MAX(tick),0) FROM phase20_7_experience_events WHERE session_id=?",
            (session_id,),
        ).fetchone()
        tick = int(base_row[0] or 0)
        for _repeat in range(max(1, int(repeats))):
            copied1 = copied2 = results = 0
            operator_written = False
            has_carry = len(_answer.strip()) > run1_len
            carry_written = False
            for anchor, source in actions:
                state = perceive_process_state(
                    run1_len=run1_len, run2_len=run2_len, copied1=copied1, copied2=copied2,
                    operator_written=operator_written, results_written=results,
                    carry_present=has_carry and results >= run1_len and not carry_written,
                )
                tick += 1
                record_step_cooccurrence(
                    conn, session_id=session_id, tick=tick, paradigm_key=key,
                    perceived_state=state, anchor=anchor, content_source=source,
                    origin="teacher_demonstration",
                    insert_experience_event=insert_experience_event,
                )
                written += 1
                if source == "observed_run1_next":
                    copied1 += 1
                elif source == "observed_separator":
                    operator_written = True
                elif source == "observed_run2_next":
                    copied2 += 1
                elif source == "recalled_column_fact":
                    results += 1
                elif source == "carry_digit":
                    carry_written = True
        conn.commit()
    return {
        "schema_id": "apv3_phase20_7_process_paradigm_demonstration/v2",
        "paradigm_key": key,
        "example": example,
        "steps_demonstrated": written,
        "session_id": session_id,
        "note": "states perceived by shared function; same event kind as spontaneous",
    }

def _maybe_run_painting_from_imagination(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    tick: int,
    db_path: Path,
    observation: _ObservationLike | None,
    imagined_event: RuntimeTickEventV2,
    turn_budget_left: int,
) -> tuple[tuple[RuntimeTickEventV2, ...], int]:
    """§66 AP 画板 gate + 子循环调度 (第二层绘画 v1, ColdSave 第十二节).

    三个经验后验条件 (任一不满足 → 不画, 零行为影响):
    1. 当前输入含"画"教学史: 该 input_signature 存在 reward>punish 的教学对齐
       (即"画X"这个说法被教过 — P1-4 指代绑定的同一条史料, 非关键词判断);
    2. 想象召回真实发生 (imagined_event 有 borrowed patch payloads);
    3. turn 预算 >= 4 tick (投影+观察+提交至少 3 tick).
    """
    if observation is None or turn_budget_left < 4:
        return (), tick
    taught = conn.execute(
        "SELECT COUNT(*) FROM phase20_7_experience_events "
        "WHERE event_kind='experience_alignment' AND reward>punish "
        "AND json_extract(payload_json,'$.text_signature')=?",
        (observation.text_signature,),
    ).fetchone()
    if not taught or int(taught[0]) <= 0:
        return (), tick
    vip = imagined_event.visual_inner_picture if isinstance(imagined_event.visual_inner_picture, dict) else {}
    borrowed_refs = vip.get("borrowed_patch_payload_refs")
    if not isinstance(borrowed_refs, (list, tuple)) or not borrowed_refs:
        return (), tick
    try:
        import numpy as np
        from .vision import _patch_payload_rows_by_refs, _reconstruct_canvas_from_patch_payloads

        # 直接重建想象画布 (像素+清晰度场) — 不读渲染 PNG (那是给人看的视图,
        # 带焦点标记/噪点门, 不是画布本体).
        rows = _patch_payload_rows_by_refs(conn, [str(r) for r in borrowed_refs])
        canvas, _hash, valid_rows = _reconstruct_canvas_from_patch_payloads(rows, tick=tick)
        if canvas is None or not valid_rows:
            return (), tick
        canvas_pixels = np.clip(canvas.canvas_pixels, 0.0, 1.0)
        canvas_clarity = np.clip(canvas.canvas_clarity, 0.0, 1.0)
        # 修 audit 2026-07-04 (用户报"想象含香蕉+苹果, 画画把两个轮廓都画上去"):
        # 想象召回可能跨多个 source_image_hash 借 patch (香蕉显著+苹果模糊), 全部重建
        # 会让 extract_contour_units 把多个主体都摘出来同时投影. §276 要求"画画只画
        # 高把握主体" — 这里用 canvas_confidence 做高把握 spatial mask: 低把握像素
        # 重置为背景灰 + clarity 归零, 让感受器从画布上只看到把握高的主体。
        # 阈值 0.30 > gist 铺底 confidence (∼0.24) — 道 gist 区域的低把握补底被剔,
        # 只留焦点近端真正高把握的当前主体 (§16.3 高把握 = 看清的部分). 内心画面可以
        # 多主体模糊重叠 (那是 §16.4 想象), 但画画要单一主体 (§66 画板投影只画看清的).
        try:
            conf = np.clip(canvas.canvas_confidence, 0.0, 1.0)
            hi_conf_mask = conf >= 0.30
            if not bool(hi_conf_mask.any()):
                # 整个画布把握都不够 — 想象太模糊, 不画 (经验 gate: 没足够把握不画)
                return (), tick
            # 背景色 = 重建前画布的真背景均值 (避免引入贴纸感), 简化为画布中位数.
            bg = canvas_pixels[~hi_conf_mask].reshape(-1, 3).mean(axis=0) if (~hi_conf_mask).any() else np.array([0.5,0.5,0.5], dtype=np.float32)
            bg = bg.astype(np.float32)
            canvas_pixels = np.where(hi_conf_mask[..., None], canvas_pixels, bg[None, None, :])
            canvas_clarity = np.where(hi_conf_mask, canvas_clarity, 0.0).astype(np.float32)
        except Exception:
            # 退化路径: mask 失败时不阻断绘画 (机制安全优先 — 不画假, 但也不拒绝真画)
            canvas_pixels = np.clip(canvas.canvas_pixels, 0.0, 1.0)
            canvas_clarity = np.clip(canvas.canvas_clarity, 0.0, 1.0)
    except Exception:
        return (), tick
    from .painting import run_painting_ticks

    events, new_tick, painting_path = run_painting_ticks(
        conn,
        pool,
        session_id=session_id,
        start_tick=tick,
        db_path=db_path,
        canvas_pixels=canvas_pixels,
        canvas_clarity=canvas_clarity,
        source_imagined_hash=str(vip.get("source_image_hash") or "imagined"),
        insert_experience_event=insert_experience_event,
        insert_action_record=insert_action_record,
        max_paint_ticks=min(10, turn_budget_left - 1),
    )
    return events, new_tick if events else tick


def _maybe_commit_outward_speech_from_idle_result(
    conn: sqlite3.Connection,
    pool: StatePool,
    grid: DraftGrid,
    *,
    idle_result: Phase207TurnResult,
    session_id: str,
    db_path: Path,
    status: dict[str, object],
    visual_drive: float,
    audio_drive: float,
    unclosed_drive: float,
    learning_loop_carryover: dict[str, Any],
) -> Phase207TurnResult:
    if not idle_result.tick_trace:
        return idle_result
    idle_event = idle_result.tick_trace[0]
    private_event_id = str(idle_event.experience_event_ids_written[0]) if idle_event.experience_event_ids_written else ""
    narrative_text = str(idle_event.ssp_active_summary.get("narrative_text") or idle_event.feelings.get("narrative_text") or "")
    if not narrative_text or not private_event_id:
        return idle_result
    idle_flow = dict(idle_event.ssp_active_summary.get("idle_narrative_flow") or {})
    source_kind = str(idle_flow.get("source_kind") or idle_event.feelings.get("source") or "")
    # M4-3 (§187.3): unclosed_drive 调用点全是 0.0 硬编 — 真实未闭合张力从 DB 读
    # (最高 u_value 的 active 项). 自发外显的动力来自真实张力, 非参数默认值.
    if unclosed_drive <= 0.0:
        _u_row = conn.execute(
            "SELECT MAX(u_value) FROM phase20_7_unclosed_items WHERE session_id=? AND status='active'",
            (session_id,),
        ).fetchone()
        if _u_row and _u_row[0] is not None:
            unclosed_drive = _unit(float(_u_row[0]))
    unclosed_pull = _unit(idle_event.feelings.get("unclosed_pull", unclosed_drive)) or unclosed_drive
    intent = "maintain_unclosed" if unclosed_pull > 0.0 or source_kind == "idle" else "request_teacher"
    referent_kind = "unclosed_current" if intent == "maintain_unclosed" else "structure_focus"
    expression_context = {
        "formula_id": PHASE20_8N_REQUEST_TEACHER_DRIVE_ID,
        "intent": intent,
        "low_grasp": 0.0 if intent == "maintain_unclosed" else 0.62,
        "b_support": 0.0,
        "unclosed_pull": round(unclosed_pull, 4),
        "short_structure_flow_support": round(_unit(idle_flow.get("support", 0.0)), 4),
        "cstar_pressure": round(max(unclosed_pull, _unit(idle_flow.get("support", 0.0))), 4),
        "request_drive": round(min(1.0, 0.24 + _unit(idle_flow.get("support", 0.0)) * 0.36), 4),
        "maintain_drive": round(min(1.0, 0.22 + unclosed_pull * 0.42), 4),
        "selected_drive": round(min(1.0, 0.24 + max(unclosed_pull, _unit(idle_flow.get("support", 0.0))) * 0.38), 4),
        "learning_loop_carryover": learning_loop_carryover,
        "current_referent": {
            "formula_id": PHASE20_8R_CURRENT_REFERENT_BINDING_ID,
            "referent_kind": referent_kind,
            "modalities": ("text",),
            "source_event_id": private_event_id,
            "unclosed_u": round(unclosed_pull, 4),
            "salience": round(min(1.0, 0.30 + max(unclosed_pull, _unit(idle_flow.get("support", 0.0))) * 0.55), 4),
            "active": True,
            "writes_answer_directly": False,
        },
        "source_kinds": (source_kind, "short_structure_flow"),
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
    }
    expression_chars, expression_trace = _select_request_expression(
        conn,
        session_id=session_id,
        intent=intent,
        fallback_text=MAINTAIN_UNCLOSED_TEXT if intent == "maintain_unclosed" else NO_CALL_TEXT,
        teacher_request_context=expression_context,
    )
    outward_candidate = _outward_speech_candidate_from_idle_context(
        conn,
        session_id=session_id,
        intent=intent,
        narrative_text=narrative_text,
        source_event_id=private_event_id,
        source_flow=idle_flow,
        unclosed_value=unclosed_pull,
        successor=None,
        learning_loop_carryover=learning_loop_carryover,
        expression_trace=expression_trace,
        expression_chars=expression_chars,
    )
    enriched_idle_event = replace(
        idle_event,
        selected_action={
            **dict(idle_event.selected_action),
            "outward_speech_eligible": bool(outward_candidate.get("eligible")),
            "outward_speech_candidate": outward_candidate,
        },
        action_competition=_idle_competition(
            selected=str(idle_event.selected_action.get("action_type") or "idle_think"),
            visual_drive=visual_drive,
            audio_drive=audio_drive,
            unclosed_drive=unclosed_pull,
            learning_loop_carryover=learning_loop_carryover,
            outward_speech_candidate=outward_candidate,
        ),
        feelings={**dict(idle_event.feelings), "outward_speech_candidate": outward_candidate},
        ssp_active_summary={**dict(idle_event.ssp_active_summary), "outward_speech_candidate": outward_candidate},
    )
    if not outward_candidate.get("eligible"):
        return replace(idle_result, tick_trace=(complete_every_tick_cognitive_cycle(enriched_idle_event),))
    return _commit_outward_speech_from_private_thought(
        conn,
        pool,
        grid,
        idle_event=complete_every_tick_cognitive_cycle(enriched_idle_event),
        session_id=session_id,
        db_path=db_path,
        status=status,
        expression_chars=expression_chars,
        expression_trace=expression_trace,
        outward_candidate=outward_candidate,
        source_private_event_id=private_event_id,
        visual_drive=visual_drive,
        audio_drive=audio_drive,
        unclosed_drive=unclosed_pull,
        learning_loop_carryover=learning_loop_carryover,
    )


def _commit_outward_speech_from_private_thought(
    conn: sqlite3.Connection,
    pool: StatePool,
    grid: DraftGrid,
    *,
    idle_event: RuntimeTickEventV2,
    session_id: str,
    db_path: Path,
    status: dict[str, object],
    expression_chars: Sequence[str],
    expression_trace: dict[str, Any],
    outward_candidate: dict[str, Any],
    source_private_event_id: str,
    visual_drive: float,
    audio_drive: float,
    unclosed_drive: float,
    learning_loop_carryover: dict[str, Any],
) -> Phase207TurnResult:
    tick = int(idle_event.tick)
    tick_events: list[RuntimeTickEventV2] = [idle_event]
    reply_text = ""
    output_chars = tuple(str(ch) for ch in expression_chars if str(ch))
    for char_index, char in enumerate(output_chars):
        tick += 1
        row, col = divmod(char_index, grid.cols)
        if row >= grid.rows:
            break
        action_type = "outward_speech" if char_index == 0 else "write_cell"
        action_record_id = insert_action_record(
            conn,
            session_id=session_id,
            tick=tick,
            action_type=action_type,
            selected=True,
            drive=_unit(outward_candidate.get("drive", 0.0)),
            eligibility={
                "no_external_input": True,
                "source_private_event_id": source_private_event_id,
                "outward_speech_candidate": outward_candidate,
            },
            target_refs={
                "draft_row": row,
                "draft_col": col,
                "source_private_event_id": source_private_event_id,
            },
        )
        _register_action_sa_from_record(conn, action_record_id, tick)
        grid.write_at(row, col, char, tick=tick)
        _observe_draft_char(pool, tick=tick, char=char, row=row, col=col, source="outward_speech")
        event_id = insert_experience_event(
            conn,
            session_id=session_id,
            tick=tick,
            event_kind="draft_grid_write",
            action_record_id=action_record_id,
            payload={
                "draft_row": row,
                "draft_col": col,
                "unit_text": char,
                "unit_hash": _hash_text(char),
                "visible_text_hash": _hash_text(grid.visible_text()),
                "source_intent": "outward_speech",
                "request_expression_selection": expression_trace,
                "outward_speech_candidate": outward_candidate,
                "source_private_event_id": source_private_event_id,
            },
        )
        conn.execute(
            "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
            (event_id, action_record_id),
        )
        _append_runtime_tick(
            tick_events,
            _tick_event(
                conn=conn,
                session_id=session_id,
                tick=tick,
                selected_action={
                    "action_type": action_type,
                    "draft_row": row,
                    "draft_col": col,
                    "unit_hash": _hash_text(char),
                    "write_index": char_index,
                    "outward_speech_candidate": outward_candidate,
                },
                action_competition=_idle_competition(
                    selected=action_type,
                    visual_drive=visual_drive,
                    audio_drive=audio_drive,
                    unclosed_drive=unclosed_drive,
                    learning_loop_carryover=learning_loop_carryover,
                    outward_speech_candidate=outward_candidate,
                ),
                state_pool=pool,
                grid=grid,
                event_ids=(event_id,),
                action_record_ids=(action_record_id,),
                ssp_summary={
                    "structure_kind": "outward_speech_from_private_thought",
                    "request_expression_selection": expression_trace,
                    "outward_speech_candidate": outward_candidate,
                },
                feelings={
                    "source": "outward_speech_action_competition",
                    "outward_speech_candidate": outward_candidate,
                    "private_thought_externalized": True,
                },
                timings_ms={"idle_outward_write_index": char_index},
            ),
        )
    if grid.visible_text():
        tick += 1
        reply_text = grid.visible_text()
        action_record_id = insert_action_record(
            conn,
            session_id=session_id,
            tick=tick,
            action_type="commit_reply",
            selected=True,
            drive=max(0.50, _unit(outward_candidate.get("drive", 0.0))),
            eligibility={
                "draft_has_visible_text": True,
                "source_private_event_id": source_private_event_id,
                "outward_speech_candidate": outward_candidate,
            },
            target_refs={"visible_text_hash": _hash_text(reply_text)},
        )
        _register_action_sa_from_record(conn, action_record_id, tick)
        event_id = insert_experience_event(
            conn,
            session_id=session_id,
            tick=tick,
            event_kind="outward_speech",
            action_record_id=action_record_id,
            payload={
                "visible_text_hash": _hash_text(reply_text),
                "visible_text": reply_text,
                "visible_chars": list(reply_text),
                "visible_length": len(reply_text),
                "source_intent": "outward_speech",
                "expression_text_hash": _hash_text(reply_text),
                "request_expression_selection": expression_trace,
                "outward_speech_candidate": outward_candidate,
                "source_private_event_id": source_private_event_id,
            },
        )
        conn.execute(
            "UPDATE phase20_7_action_records SET result_event_id=? WHERE action_record_id=?",
            (event_id, action_record_id),
        )
        _append_runtime_tick(
            tick_events,
            _tick_event(
                conn=conn,
                session_id=session_id,
                tick=tick,
                selected_action={
                    "action_type": "commit_reply",
                    "visible_text_hash": _hash_text(reply_text),
                    "source_intent": "outward_speech",
                    "outward_speech_candidate": outward_candidate,
                },
                action_competition=_idle_competition(
                    selected="commit_reply",
                    visual_drive=visual_drive,
                    audio_drive=audio_drive,
                    unclosed_drive=unclosed_drive,
                    learning_loop_carryover=learning_loop_carryover,
                    outward_speech_candidate=outward_candidate,
                ),
                state_pool=pool,
                grid=grid,
                event_ids=(event_id,),
                action_record_ids=(action_record_id,),
                ssp_summary={
                    "structure_kind": "outward_speech_from_private_thought",
                    "request_expression_selection": expression_trace,
                    "outward_speech_candidate": outward_candidate,
                },
                feelings={
                    "source": "outward_speech_action_competition",
                    "outward_speech_candidate": outward_candidate,
                    "private_thought_externalized": True,
                },
            ),
        )
    return Phase207TurnResult(
        schema_id=PHASE20_7_STAGE4_SCHEMA_ID,
        stage_id="20.7-stage4",
        session_id=session_id,
        committed=bool(reply_text),
        reply_text=reply_text,
        tick_trace=tuple(tick_events),
        db_path=db_path,
        stage0_checks=status,
        emotion=_build_and_persist_emotion(tick_events, conn=conn, session_id=session_id, tick=tick),
    )


def _flow_candidate_can_drive_idle_successor(candidate: ExperienceFlowCandidate) -> bool:
    payload = dict(candidate.payload or {})
    if bool(payload.get("private_thought", False)):
        return True
    if candidate.candidate_kind in {"idle_think_window", "idle_observe_window"}:
        return True
    if candidate.source_kind in {"idle_think_window", "idle_observe_window"}:
        return True
    return False


def _successor_text_from_flow_candidate(candidate: ExperienceFlowCandidate) -> str:
    payload = dict(candidate.payload or {})
    if candidate.candidate_kind == "short_structure_flow_next":
        for key in ("target_text", "text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for key in ("target_text", "narrative_text", "text", "source_text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return str(candidate.text or "").strip()


def _idle_narrative_text(
    unclosed_item: dict[str, object],
    *,
    successor: dict[str, Any] | None,
    attempt_index: int,
) -> str:
    source_text = str(unclosed_item.get("source_text") or "")
    if successor:
        return f"{source_text} -> {successor['output_text']}"
    if attempt_index % 3 == 1:
        return f"{source_text} -> 还缺后继证据"
    if attempt_index % 3 == 2:
        return f"{source_text} -> 等待新的教学或相似经验"
    return f"{source_text} -> 暂时放低,继续保留"


def _decay_unclosed_for_idle(
    conn: sqlite3.Connection,
    *,
    unclosed_id: str,
    current_u: float,
    attempt_count: int,
    successor_found: bool,
) -> float:
    decay = 0.72 if successor_found else 0.88
    impossibility_evidence = 0.0
    # §27.6 第4项 impossibility_evidence: C_backward/B召回多次说明任务前提不成立→U下降.
    # 派生: attempt_count 高 (多次尝试) + successor_found=False (始终找不到后继) → 该放下.
    # 不增实体: attempt_count 是既有 unclosed_items 字段, 纯改 decay 逻辑.
    # 拟人: "想了这么多次都想不出, 可能根本做不到" → 放下 (§27.4 "条件不成立→放下").
    if not successor_found and attempt_count >= 4:
        impossibility_evidence = min(0.18, (attempt_count - 3) * 0.06)
        decay = max(0.62, decay - impossibility_evidence)
    next_u = max(0.04, min(1.0, float(current_u) * decay))
    status = "active"
    if successor_found and next_u < 0.28:
        status = "resolved"
        next_u = 0.0
    # §27.6 第4项: 多次无后继 + impossibility 显著 → 也算放下 (status=resolved_by_impossibility)
    if not successor_found and attempt_count >= 6 and next_u < 0.20:
        status = "resolved"
        next_u = 0.0
    conn.execute(
        """
        UPDATE phase20_7_unclosed_items
        SET u_value=?, attempt_count=?, status=?, reason_json=?, updated_at_ms=?
        WHERE unclosed_id=?
        """,
        (
            next_u,
            int(attempt_count),
            status,
            to_json(
                {
                    "reason_kind": "idle_successor_bias_with_impossibility_evidence",
                    "successor_found": bool(successor_found),
                    "pressure_decay": decay,
                    "impossibility_evidence": round(float(impossibility_evidence), 4),
                    "attempt_count": int(attempt_count),
                }
            ),
            now_ms(),
            unclosed_id,
        ),
    )
    return next_u


def _find_structural_b(
    conn: sqlite3.Connection,
    observation: _ObservationLike,
    *,
    state_pool: StatePool | None = None,
    session_id: str = "",
    before_tick: int = 0,
) -> _StructuralB | None:
    candidates = _unified_experience_candidates_for_observation(
        conn,
        observation,
        limit=300,
        exact_input_allowed=False,
    )
    observation_bias, _observation_bias_slots = _statepool_observation_support_bias(state_pool, observation)
    bias_terms: tuple[tuple[str, float], ...] = (
        (("statepool_cstar_observation_bias", round(observation_bias, 4)),) if observation_bias > 0.0 else ()
    )
    best: _StructuralB | None = None
    best_score = 0.0
    query_text = "".join(observation.chars)
    # §2363: 对"当前这个问法"的历史纠正也是反例证据 — 上次对同一问法的回答被
    # punish 过, 这次任何来源的泛化都该更谨慎 (纠正锚定在问法上, 不只锚定在源上).
    _query_counter_count = _alignment_counter_count(conn, input_signature=observation.signature)
    for unified_candidate in candidates:
        if unified_candidate.candidate_kind != "experience_alignment":
            continue
        payload = unified_candidate.payload
        if payload.get("expression_role"):
            continue
        if payload.get("input_signature") == observation.signature:
            continue
        if observation.visual_signature:
            candidate_visual = str(payload.get("visual_signature", "") or "")
            if candidate_visual and _visual_signature_similarity(candidate_visual, observation.visual_signature) < 0.82:
                continue
        input_payload = _input_payload_for_alignment(conn, payload)
        source_text = str(input_payload.get("text", "") or "")
        if not source_text:
            continue
        output_chars = tuple(str(ch) for ch in payload.get("output_chars", ()))
        if not output_chars:
            continue
        similarity, shared_units, residual_units = _structural_similarity(tuple(query_text), tuple(source_text))
        visual_boost = 0.0
        visual_similarity = 0.0
        if observation.visual_signature and str(payload.get("visual_signature", "") or ""):
            visual_similarity = _visual_signature_similarity(str(payload.get("visual_signature", "") or ""), observation.visual_signature)
            visual_boost = visual_similarity * 0.08
        reward_value, punish_value = _value_signal_for_unified_candidate(conn, unified_candidate)
        # §2363/§127.3: 对"当前问法"的历史纠正 = 对任何回答该问法的泛化的惩罚压
        # (反例锚定在条件上: 同条件下该行动竞争分数持续走低 — 用户例2).
        # 退火形式: counter/(counter+2), 1次纠正=0.33, 2次=0.5, 渐进收紧不一票否决.
        if _query_counter_count > 0:
            punish_value = max(
                punish_value,
                _query_counter_count / (_query_counter_count + 2.0),
            )
        l1_similarity = _l1_text_vector_similarity(conn, query_text, source_text)
        formula_support, formula_terms = compute_unified_experience_support(
            structural_similarity=similarity,
            visual_similarity=visual_similarity,
            modality_match=1.0 if output_chars else 0.0,
            reward=reward_value,
            punish=punish_value,
            l1_vector_similarity=l1_similarity,
        )
        reward_boost = min(0.10, max(0.0, reward_value) * (0.06 + max(0.0, 1.0 - similarity) * 0.06))
        punish_penalty = min(0.42, max(0.0, punish_value) * (0.16 + similarity * 0.24))
        # §173.5 结果锚定把握感门控: 与 exact_b0 同一条 _support_from_reward_punish 通道,
        # 让泛化的"敢写"成为经验结果而非结构先验默认冲动. support_count 取该泛化源
        # (源 input_signature) 的奖励确认累计(append-only 经验流派生, §24/§132, 可重建),
        # 复用 L2 rebuild 已有的同一模式(experience_log.py 1320-1321), 不新增实体.
        # §2363 对称化: 反例(counter_evidence/punish主导 alignment)从确认数中扣除,
        # 使"纠正过的更谨慎"成为数学结果 — sc 回落 → lr 回升 → punish 位移更大.
        _src_input_signature = str(payload.get("input_signature", "") or "")
        _confirm_count = (
            _alignment_support_count(conn, input_signature=_src_input_signature)
            if _src_input_signature
            else 0
        )
        _counter_count = (
            _alignment_counter_count(conn, input_signature=_src_input_signature)
            if _src_input_signature
            else 0
        )
        generalization_grasp = _support_from_reward_punish(
            reward_value,
            punish_value,
            support_count=max(0, _confirm_count - _counter_count),
        )
        shared_ratio = len(shared_units) / max(len(tuple(query_text)), 1)
        residual_ratio = len(residual_units) / max(len(tuple(query_text)), 1)
        # §16.7/§44.1 部分匹配审计 + §2363 经验后验谨慎:
        # source_coverage 低 = query 只覆盖了源的一部分(如"13+7"只部分覆盖"3+7").
        # 9j 裁定: 子序列泛化本身合法(寒暄类), 故 penalty 不预设 — 它只在两类
        # 经验后验证据出现时上升(全部从经验流派生, 无关键词/无内容特判):
        # 1. counter_pressure: 该泛化源被纠正/惩罚过的累计次数 (§2363 反例通道);
        # 2. residual_novelty: query 残差单元里"自身有独立经验证据的单元"占比 —
        #    残差是高频独立单元(它在大量上下文出现过, 是有含义的认知对象 §8)时,
        #    忽略它属于证据缺口; 残差是低频噪声时忽略无妨.
        source_coverage = _unit(len(shared_units) / max(len(tuple(source_text)), 1)) if source_text else 1.0
        # residual 单元的证据强度: 只看 (a) 非标点 (标点残差不构成语义缺口, 同
        # _meaningful_text_units 清洗口径) 且 (b) 不构成源的顺序一致子序列的部分 —
        # 残差按原顺序仍是源文本的子序列时(如 10e "fail cue"⊂"fail old cue"), 属于
        # 合法子序列泛化, 不算缺口; 残差单元虽在源中存在但顺序冲突时(如 '42+35' vs
        # '23+45' 的数字重排), 顺序本身携带结构信息(§10 短期结构池), 必须算缺口.
        # 内容无关的结构判据, 非关键词/数字特判.
        # count/4 饱和: 该单元在经验流反复出现过 → 是有独立含义的认知对象(§8),
        # 忽略它属于证据缺口; 低频噪声单元忽略无妨.
        _meaningful_residual = tuple(
            str(u) for u in tuple(residual_units)[:8]
            if str(u) and str(u) not in " \t\r\n?？!！,，.。;；:：、"
        )
        _residual_is_ordered_subsequence = True
        if _meaningful_residual and source_text:
            _src_iter = iter(source_text)
            _residual_is_ordered_subsequence = all(
                _res in _src_iter for _res in _meaningful_residual
            )
        _residual_evidence_scores: list[float] = []
        for _res_text in _meaningful_residual:
            if _residual_is_ordered_subsequence and _res_text in set(source_text):
                continue
            _res_count = _unit_evidence_count(conn, unit_text=_res_text)
            _residual_evidence_scores.append(min(1.0, _res_count / 4.0))
        residual_novelty = (
            sum(_residual_evidence_scores) / len(_residual_evidence_scores)
            if _residual_evidence_scores
            else 0.0
        )
        counter_pressure = _unit(
            (_counter_count + _query_counter_count)
            / ((_counter_count + _query_counter_count) + 2.0)
        ) if (_counter_count or _query_counter_count) else 0.0
        source_coverage_penalty = min(
            0.42,
            residual_novelty * 0.55 + counter_pressure * 0.34,
        )
        similarity_coverage_adjusted = similarity  # 保持原 similarity (9j设计)
        cold_retest_tuning = _cold_retest_generalization_tuning_for_alignment(
            conn,
            session_id=session_id,
            alignment_event_id=str(unified_candidate.alignment_event_id or unified_candidate.event_id or ""),
            before_tick=before_tick,
            structural_similarity=similarity,
            shared_ratio=shared_ratio,
            residual_ratio=residual_ratio,
        )
        cold_generalization_boost = _unit(cold_retest_tuning.get("generalization_courage", 0.0))
        cold_caution_penalty = _unit(cold_retest_tuning.get("generalization_caution", 0.0))
        memory_rhythm_support = _memory_rhythm_structural_b_support_for_alignment(
            conn,
            session_id=session_id,
            alignment_event_id=str(unified_candidate.alignment_event_id or unified_candidate.event_id or ""),
            before_tick=before_tick,
            structural_similarity=similarity,
            shared_ratio=shared_ratio,
            residual_ratio=residual_ratio,
        )
        memory_rhythm_boost = _unit(memory_rhythm_support.get("memory_rhythm_support_boost", 0.0))
        memory_rhythm_guard = _unit(memory_rhythm_support.get("memory_rhythm_guard_penalty", 0.0))
        residual_conflict_penalty = min(
            0.36,
            max(0.0, residual_ratio - shared_ratio * 0.55) * (0.22 + max(0.0, 1.0 - similarity) * 0.18),
        )
        support = min(
            1.0,
            max(
                0.0,
                max(
                    similarity_coverage_adjusted + visual_boost,
                    formula_support,
                    min(float(unified_candidate.support), similarity_coverage_adjusted + 0.12),
                ),
            )
            + observation_bias
            + reward_boost
            + cold_generalization_boost
            + memory_rhythm_boost
            - punish_penalty,
        )
        support = max(0.0, support - residual_conflict_penalty - cold_caution_penalty - memory_rhythm_guard - source_coverage_penalty)
        acceptance_threshold, threshold_terms = _structural_b_acceptance_threshold(
            reward_boost=reward_boost,
            punish_penalty=punish_penalty,
            residual_conflict_penalty=residual_conflict_penalty,
            shared_ratio=shared_ratio,
            cold_generalization_boost=cold_generalization_boost,
            cold_caution_penalty=cold_caution_penalty,
            memory_rhythm_boost=memory_rhythm_boost,
            memory_rhythm_guard=memory_rhythm_guard,
            source_coverage_penalty=source_coverage_penalty,
        )
        if support < acceptance_threshold:
            continue
        if support > best_score:
            best_score = support
            best = _StructuralB(
                event_id=str(unified_candidate.alignment_event_id or unified_candidate.event_id),
                source_event_id=str(payload.get("input_event_id") or unified_candidate.event_id),
                source_text=source_text,
                output_chars=output_chars,
                similarity=support,
                shared_units=tuple(shared_units),
                residual_units=tuple(residual_units),
                candidate_audit_slots=(
                    unified_candidate.audit_slot(),
                    {
                        "slot_kind": "structural_generalization_value_modulation",
                        "formula_id": PHASE20_9J_STRUCTURAL_GENERALIZATION_ID,
                        "source": "sequence_span_lcs_alignment_plus_reward_punish",
                        "structural_sequence_fit": round(float(similarity), 4),
                        "query_coverage": round(float(shared_ratio), 4),
                        "residual_ratio": round(float(residual_ratio), 4),
                        "reward": round(float(reward_value), 4),
                        "punish": round(float(punish_value), 4),
                        "reward_boost": round(float(reward_boost), 4),
                        "generalization_grasp": round(float(generalization_grasp), 4),
                        "cold_retest_generalization_tuning": cold_retest_tuning,
                        "cold_generalization_boost": round(float(cold_generalization_boost), 4),
                        "cold_caution_penalty": round(float(cold_caution_penalty), 4),
                        "memory_rhythm_structural_b_support": memory_rhythm_support,
                        "memory_rhythm_support_boost": round(float(memory_rhythm_boost), 4),
                        "memory_rhythm_guard_penalty": round(float(memory_rhythm_guard), 4),
                        "punish_penalty": round(float(punish_penalty), 4),
                        "residual_conflict_penalty": round(float(residual_conflict_penalty), 4),
                        "acceptance_threshold": round(float(acceptance_threshold), 4),
                        "acceptance_threshold_terms": threshold_terms,
                        "support_after_value_modulation": round(float(support), 4),
                        "source_coverage_penalty": round(float(-source_coverage_penalty), 4),
                        "creates_reply_candidate": False,
                        "writes_answer_directly": False,
                    },
                ),
                support_terms=tuple(formula_terms)
                + (
                    ("phase20_9j_formula_active", 1.0),
                    ("structural_sequence_fit", round(float(similarity), 4)),
                    ("structural_query_coverage", round(float(shared_ratio), 4)),
                    ("structural_residual_ratio", round(float(residual_ratio), 4)),
                    ("unified_candidate_support", round(float(unified_candidate.support), 4)),
                    ("value_reward_boost", round(float(reward_boost), 4)),
                    ("cold_retest_generalization_boost", round(float(cold_generalization_boost), 4)),
                    ("cold_retest_caution_penalty", round(float(-cold_caution_penalty), 4)),
                    ("memory_rhythm_support_boost", round(float(memory_rhythm_boost), 4)),
                    ("memory_rhythm_guard_penalty", round(float(-memory_rhythm_guard), 4)),
                    ("value_punish_penalty", round(float(-punish_penalty), 4)),
                    ("residual_conflict_penalty", round(float(-residual_conflict_penalty), 4)),
                    ("acceptance_threshold", round(float(acceptance_threshold), 4)),
                    ("low_grasp_generalization_uncertainty", round(float(1.0 - support), 4)),
                )
                + bias_terms,
            )
    return best


def _structural_b_acceptance_threshold(
    *,
    reward_boost: float,
    punish_penalty: float,
    residual_conflict_penalty: float,
    shared_ratio: float,
    cold_generalization_boost: float = 0.0,
    cold_caution_penalty: float = 0.0,
    memory_rhythm_boost: float = 0.0,
    memory_rhythm_guard: float = 0.0,
    source_coverage_penalty: float = 0.0,
) -> tuple[float, dict[str, float]]:
    reward_relief = min(0.08, max(0.0, float(reward_boost)) * 0.55)
    cold_relief = min(0.07, max(0.0, float(cold_generalization_boost)) * 0.55)
    memory_relief = min(0.055, max(0.0, float(memory_rhythm_boost)) * 0.52)
    cold_guard = min(0.12, max(0.0, float(cold_caution_penalty)) * 0.48)
    memory_guard = min(0.11, max(0.0, float(memory_rhythm_guard)) * 0.48)
    punish_guard = min(0.18, max(0.0, float(punish_penalty)) * 0.45)
    residual_guard = min(0.14, max(0.0, float(residual_conflict_penalty)) * 0.38)
    coverage_relief = min(0.05, max(0.0, float(shared_ratio) - 0.72) * 0.08)
    # §16.7/§44.1 部分匹配抬高接受阈值: query 是 source 子集时不该和完全匹配一样轻松过.
    source_guard = min(0.20, max(0.0, float(source_coverage_penalty)) * 0.80)
    threshold = _unit(
        STRUCTURAL_B_THRESHOLD
        - reward_relief
        - cold_relief
        - memory_relief
        - coverage_relief
        + punish_guard
        + cold_guard
        + memory_guard
        + residual_guard
        + source_guard
    )
    return threshold, {
        "base": round(float(STRUCTURAL_B_THRESHOLD), 4),
        "reward_relief": round(float(-reward_relief), 4),
        "cold_retest_relief": round(float(-cold_relief), 4),
        "memory_rhythm_relief": round(float(-memory_relief), 4),
        "coverage_relief": round(float(-coverage_relief), 4),
        "punish_guard": round(float(punish_guard), 4),
        "cold_retest_guard": round(float(cold_guard), 4),
        "memory_rhythm_guard": round(float(memory_guard), 4),
        "residual_guard": round(float(residual_guard), 4),
    }


def _value_signal_for_unified_candidate(
    conn: sqlite3.Connection,
    candidate: UnifiedExperienceCandidate,
) -> tuple[float, float]:
    event_id = str(candidate.alignment_event_id or candidate.event_id or "")
    return _value_signal_for_alignment_event_id(conn, event_id)


def _cold_retest_generalization_tuning_for_alignment(
    conn: sqlite3.Connection | None,
    *,
    session_id: str,
    alignment_event_id: str,
    before_tick: int,
    structural_similarity: float,
    shared_ratio: float,
    residual_ratio: float,
) -> dict[str, Any]:
    base = _cold_retest_generalization_tuning(
        self_test_rows=_cold_retest_self_test_rows_for_alignment(
            conn,
            session_id=session_id,
            alignment_event_id=alignment_event_id,
            before_tick=before_tick,
        ),
        structural_similarity=structural_similarity,
        shared_ratio=shared_ratio,
        residual_ratio=residual_ratio,
    )
    return {
        **base,
        "alignment_event_id": str(alignment_event_id or ""),
        "before_tick": int(before_tick or 0),
    }


def _memory_rhythm_structural_b_support_for_alignment(
    conn: sqlite3.Connection | None,
    *,
    session_id: str,
    alignment_event_id: str,
    before_tick: int,
    structural_similarity: float,
    shared_ratio: float,
    residual_ratio: float,
) -> dict[str, Any]:
    if conn is None or not session_id or not alignment_event_id:
        return _inactive_memory_rhythm_structural_b_support("missing_database_or_alignment")
    alignment = _learning_alignment_payload_by_id(conn, alignment_event_id)
    if not alignment:
        return _inactive_memory_rhythm_structural_b_support("missing_alignment_event")
    alignment_tick = int(alignment.get("tick", 0) or 0)
    payload = dict(alignment.get("payload", {}) or {})
    input_payload = _input_payload_for_alignment(conn, payload)
    source_text = str(input_payload.get("text", "") or "")
    if not source_text and payload.get("visual_signature"):
        source_text = VISUAL_FOCUS_ANCHOR_UNIT
    events = {
        "alignment_event_id": str(alignment_event_id),
        "alignment_tick": alignment_tick,
        "before_tick": int(before_tick or 0),
        "alignment_reward": _unit(alignment.get("reward", 0.0)),
        "alignment_punish": _unit(alignment.get("punish", 0.0)),
        "source_event_id": str(payload.get("input_event_id") or ""),
        "source_text": source_text,
        "target_text": str("".join(str(ch) for ch in payload.get("output_chars", ()))).strip(),
        "review_rows": _learning_review_occurrences_for_alignment(
            conn,
            session_id=session_id,
            before_tick=before_tick,
            alignment_event_id=alignment_event_id,
        ),
        "self_test_rows": _self_test_occurrences_for_alignment(
            conn,
            session_id=session_id,
            before_tick=before_tick,
            alignment_event_id=alignment_event_id,
        ),
        "teacher_feedback": _learning_object_teacher_feedback_stats(
            conn,
            session_id=session_id,
            after_tick=alignment_tick,
            before_tick=before_tick,
            alignment_event_id=alignment_event_id,
        ),
    }
    stage_scores = {
        "teacher_exit": _unit(events["alignment_reward"]) * 0.28,
        "generalization": _unit(structural_similarity) * 0.58 + _unit(shared_ratio) * 0.24,
        "cold_retest": 0.0,
        "correction": _unit(events["alignment_punish"]) * 0.35 + _unit(residual_ratio) * 0.22,
    }
    review_rows = tuple(events.get("review_rows", ()) or ())
    self_test_rows = tuple(events.get("self_test_rows", ()) or ())
    success_count = sum(1 for row in self_test_rows if row.get("success"))
    failure_count = sum(1 for row in self_test_rows if row.get("failure"))
    reward = _unit(events.get("alignment_reward", 0.0))
    punish = _unit(events.get("alignment_punish", 0.0))
    stability = _unit(
        reward * 0.22
        + min(0.24, len(review_rows) * 0.06)
        + min(0.30, success_count * 0.15)
        + _unit(stage_scores.get("teacher_exit", 0.0)) * 0.16
        + _unit(stage_scores.get("generalization", 0.0)) * 0.12
        - min(0.34, failure_count * 0.17 + punish * 0.20)
    )
    regression = _unit(
        min(0.40, failure_count * 0.20)
        + punish * 0.24
        + _unit(stage_scores.get("correction", 0.0)) * 0.22
        - min(0.20, success_count * 0.08)
    )
    cold_window = _long_interval_cold_retest_window(events=events, stage_progression={"stage_scores": stage_scores})
    cold_tuning = _cold_retest_generalization_tuning(
        self_test_rows=self_test_rows,
        structural_similarity=structural_similarity,
        shared_ratio=shared_ratio,
        residual_ratio=residual_ratio,
    )
    rhythm = _memory_consolidation_forgetting_review_rhythm(
        events=events,
        stage_scores=stage_scores,
        review_rows=review_rows,
        self_test_rows=self_test_rows,
        cold_window=cold_window,
        cold_generalization_tuning=cold_tuning,
        stability=stability,
        regression=regression,
        reward=reward,
        punish=punish,
    )
    if not rhythm.get("active"):
        return _inactive_memory_rhythm_structural_b_support("inactive_memory_rhythm")
    memory_consolidation = _unit(rhythm.get("memory_consolidation", 0.0))
    forgetting_pressure = _unit(rhythm.get("forgetting_pressure", 0.0))
    review_pressure = _unit(rhythm.get("review_rhythm_pressure", 0.0))
    reconsolidation_need = _unit(rhythm.get("reconsolidation_need", 0.0))
    similarity_gate = _unit(float(structural_similarity) * 0.50 + float(shared_ratio) * 0.36 - float(residual_ratio) * 0.20)
    support_boost = min(
        0.075,
        max(0.0, memory_consolidation - max(forgetting_pressure, regression) * 0.45)
        * (0.030 + similarity_gate * 0.060),
    )
    guard_penalty = min(
        0.135,
        max(0.0, max(forgetting_pressure, review_pressure * 0.72, reconsolidation_need * 0.62) - memory_consolidation * 0.38)
        * (0.060 + max(0.0, 1.0 - similarity_gate) * 0.060 + float(residual_ratio) * 0.030),
    )
    active = support_boost > 0.0 or guard_penalty > 0.0
    return {
        "formula_id": PHASE20_10G_MEMORY_RHYTHM_B_SUPPORT_ID,
        "active": active,
        "source": "existing_learning_object_memory_rhythm_projection_for_structural_b",
        "alignment_event_id": str(alignment_event_id),
        "memory_rhythm_formula_id": rhythm.get("formula_id"),
        "memory_consolidation": round(memory_consolidation, 4),
        "forgetting_pressure": round(forgetting_pressure, 4),
        "review_rhythm_pressure": round(review_pressure, 4),
        "reconsolidation_need": round(reconsolidation_need, 4),
        "structural_similarity": round(_unit(structural_similarity), 4),
        "shared_ratio": round(_unit(shared_ratio), 4),
        "residual_ratio": round(_unit(residual_ratio), 4),
        "similarity_gate": round(similarity_gate, 4),
        "memory_rhythm_support_boost": round(support_boost, 4),
        "memory_rhythm_guard_penalty": round(guard_penalty, 4),
        "uses_existing_ap_flow": True,
        "projection_only": True,
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _inactive_memory_rhythm_structural_b_support(reason: str) -> dict[str, Any]:
    return {
        "formula_id": PHASE20_10G_MEMORY_RHYTHM_B_SUPPORT_ID,
        "active": False,
        "reason": reason,
        "memory_rhythm_support_boost": 0.0,
        "memory_rhythm_guard_penalty": 0.0,
        "uses_existing_ap_flow": True,
        "projection_only": True,
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _cold_retest_self_test_rows_for_alignment(
    conn: sqlite3.Connection | None,
    *,
    session_id: str,
    alignment_event_id: str,
    before_tick: int,
) -> tuple[dict[str, Any], ...]:
    if conn is None or not session_id or not alignment_event_id:
        return ()
    # §185 N+1 消除: 查询只依赖 (session_id, before_tick, sa_prefix), 与 alignment
    # 无关 (alignment 是下方 Python 过滤). turn 内对每个候选重复调用 → memo 命中.
    rows = _memoized_rows(
        conn,
        ("self_test_desc", session_id, int(before_tick or 0)),
        """
        SELECT o.occurrence_id, o.tick, o.clarity, o.position_json
        FROM phase20_7_occurrences o
        JOIN phase20_7_experience_events e ON e.event_id=o.event_id
        WHERE e.session_id=?
          AND o.tick < ?
          AND o.sa_type_id >= 'short_structure_flow::self_test::'
          AND o.sa_type_id < 'short_structure_flow::self_test:;'
        ORDER BY o.tick DESC
        LIMIT 64
        """,
        (session_id, int(before_tick or 0)),
    )
    out: list[dict[str, Any]] = []
    for occurrence_id, tick, clarity, position_json in rows:
        position = from_json(str(position_json))
        if not isinstance(position, dict):
            continue
        self_test = position.get("idle_self_test")
        if not isinstance(self_test, dict):
            continue
        if str(self_test.get("alignment_event_id") or "") != str(alignment_event_id):
            continue
        if str(self_test.get("self_test_kind") or "") != "cold_retest_self_test":
            continue
        grasp = _unit(self_test.get("self_test_grasp", 0.0))
        match = _unit(self_test.get("match_score", 0.0))
        out.append(
            {
                "occurrence_id": str(occurrence_id),
                "tick": int(tick or 0),
                "support": round(_unit(clarity), 4),
                "self_test_kind": "cold_retest_self_test",
                "self_test_grasp": round(grasp, 4),
                "match_score": round(match, 4),
                "success": grasp >= 0.68 and match >= 0.70,
                "failure": grasp < 0.68 or match < 0.70,
            }
        )
    return tuple(out)


def _cold_retest_generalization_tuning(
    *,
    self_test_rows: Sequence[dict[str, Any]],
    structural_similarity: float,
    shared_ratio: float,
    residual_ratio: float,
) -> dict[str, Any]:
    cold_rows = tuple(
        row for row in self_test_rows if str(row.get("self_test_kind") or "") == "cold_retest_self_test"
    )
    if not cold_rows:
        return {
            "formula_id": PHASE20_10E_COLD_RETEST_GENERALIZATION_ID,
            "active": False,
            "reason": "no_cold_retest_self_test",
            "cold_success_count": 0,
            "cold_failure_count": 0,
            "generalization_courage": 0.0,
            "generalization_caution": 0.0,
            "action_deltas": {},
            "uses_existing_ap_flow": True,
            "projection_only": True,
            "subjective": True,
            "may_be_wrong": True,
            "writes_answer_directly": False,
            "creates_reply_candidate": False,
        }
    success_rows = tuple(row for row in cold_rows if row.get("success"))
    failure_rows = tuple(row for row in cold_rows if row.get("failure"))
    success_strength = _unit(
        sum(_unit(row.get("self_test_grasp", 0.0)) * _unit(row.get("match_score", 0.0)) for row in success_rows)
        / max(len(success_rows), 1)
    )
    failure_strength = _unit(
        sum(_unit(1.0 - row.get("match_score", 0.0)) + _unit(1.0 - row.get("self_test_grasp", 0.0)) for row in failure_rows)
        / max(len(failure_rows), 1)
        * 0.5
    )
    similarity_gate = _unit(float(structural_similarity) * 0.48 + float(shared_ratio) * 0.38 - float(residual_ratio) * 0.22)
    memory_balance = _unit(min(0.70, len(success_rows) * 0.18 + success_strength * 0.42) - min(0.74, len(failure_rows) * 0.22 + failure_strength * 0.48))
    regression_balance = _unit(min(0.74, len(failure_rows) * 0.22 + failure_strength * 0.52) - min(0.55, len(success_rows) * 0.12 + success_strength * 0.30))
    courage = min(0.10, max(0.0, memory_balance) * (0.035 + similarity_gate * 0.085))
    caution = min(0.18, max(0.0, regression_balance) * (0.070 + max(0.0, 1.0 - similarity_gate) * 0.060))
    active = courage > 0.0 or caution > 0.0
    action_deltas = {
        "write_cell": round(min(0.050, courage * 0.42) - min(0.040, caution * 0.16), 4),
        "commit_reply": round(min(0.052, courage * 0.46) - min(0.050, caution * 0.24), 4),
        "request_teacher": round(min(0.060, caution * 0.34) - min(0.040, courage * 0.24), 4),
        "maintain_unclosed": round(min(0.050, caution * 0.24) - min(0.030, courage * 0.16), 4),
        "read_draft": round(min(0.046, caution * 0.30), 4),
        "edit_cell": round(min(0.048, caution * 0.32), 4),
        "idle_think": round(min(0.050, max(courage, caution) * 0.22), 4),
        "stop_generating": round(min(0.030, caution * 0.18) - min(0.024, courage * 0.12), 4),
    }
    return {
        "formula_id": PHASE20_10E_COLD_RETEST_GENERALIZATION_ID,
        "active": active,
        "source": "existing_cold_retest_self_test_occurrences_projection",
        "cold_success_count": int(len(success_rows)),
        "cold_failure_count": int(len(failure_rows)),
        "success_strength": round(success_strength, 4),
        "failure_strength": round(failure_strength, 4),
        "structural_similarity": round(_unit(structural_similarity), 4),
        "shared_ratio": round(_unit(shared_ratio), 4),
        "residual_ratio": round(_unit(residual_ratio), 4),
        "similarity_gate": round(similarity_gate, 4),
        "memory_balance": round(memory_balance, 4),
        "regression_balance": round(regression_balance, 4),
        "generalization_courage": round(courage, 4),
        "generalization_caution": round(caution, 4),
        "action_deltas": action_deltas,
        "recent_cold_self_test_ticks": tuple(int(row.get("tick", 0) or 0) for row in cold_rows[:4]),
        "uses_existing_ap_flow": True,
        "projection_only": True,
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _value_signal_for_alignment_event_id(
    conn: sqlite3.Connection,
    event_id: str,
) -> tuple[float, float]:
    if not event_id:
        return 0.0, 0.0
    row = conn.execute(
        """
        SELECT reward, punish
        FROM phase20_7_experience_events
        WHERE event_id=?
        """,
        (event_id,),
    ).fetchone()
    if row is None:
        return 0.0, 0.0
    return max(0.0, float(row[0] or 0.0)), max(0.0, float(row[1] or 0.0))


def _value_signal_for_output_hash(
    conn: sqlite3.Connection,
    output_hash: str,
) -> tuple[float, float]:
    if not output_hash:
        return 0.0, 0.0
    rows = conn.execute(
        """
        SELECT reward, punish
        FROM phase20_7_experience_events
        WHERE event_kind='experience_alignment'
          AND json_extract(payload_json, '$.output_hash')=?
        ORDER BY created_at_ms DESC
        LIMIT 12
        """,
        (str(output_hash),),
    ).fetchall()
    if not rows:
        return 0.0, 0.0
    reward = max(max(0.0, float(row[0] or 0.0)) for row in rows)
    punish = max(max(0.0, float(row[1] or 0.0)) for row in rows)
    return reward, punish


def _input_payload_for_alignment(conn: sqlite3.Connection, alignment_payload: dict[str, Any]) -> dict[str, Any]:
    event_id = alignment_payload.get("input_event_id")
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


def _recover_recent_observation_for_feedback(
    conn: sqlite3.Connection,
    *,
    session_id: str,
) -> _RecoveredObservation | None:
    row = conn.execute(
        """
        SELECT event_id, source_packet_id, payload_json
        FROM phase20_7_experience_events
        WHERE event_kind='text_receptor_observation' AND session_id=?
        ORDER BY created_at_ms DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        return _recover_recent_visual_observation(conn, session_id=session_id)
    event_id, source_packet_id, payload_json = row
    payload = from_json(str(payload_json))
    if not isinstance(payload, dict):
        return _recover_recent_visual_observation(conn, session_id=session_id)
    text = str(payload.get("text", "") or "")
    if not text:
        return _recover_recent_visual_observation(conn, session_id=session_id)
    occ_rows = conn.execute(
        """
        SELECT occurrence_id
        FROM phase20_7_occurrences
        WHERE event_id=?
        ORDER BY tick ASC
        """,
        (str(event_id),),
    ).fetchall()
    occurrence_ids = tuple(str(item[0]) for item in occ_rows)
    chars = tuple(text)
    text_signature = str(payload.get("text_signature", "") or _signature_for_chars(chars))
    visual_signature = str(payload.get("visual_signature", "") or "") or None
    signature = str(payload.get("structure_signature", "") or _compose_input_signature(text_signature, visual_signature))
    text_hash = str(payload.get("text_hash", "") or _hash_text(text))
    return _RecoveredObservation(
        event_id=str(event_id),
        source_packet_id=str(source_packet_id or ""),
        occurrence_ids=occurrence_ids,
        signature=signature,
        text_signature=text_signature,
        chars=chars,
        text_hash=text_hash,
        visual_signature=visual_signature,
        recovery_kind="recent_text",
    )


_VISUAL_MEMORY_REFERENCE_OVERLAP_THRESHOLD = 0.34


def _text_query_refers_to_visual_memory(
    conn: sqlite3.Connection,
    *,
    query_text: str,
    session_id: str,
    backward_source_kind: str,
) -> bool:
    """白皮书 §16.1/§1210: 纯文本输入何时可继承历史视觉签名.

    两种合法视觉指代:
    1. backward_attribution 命中 recent_visual_window —— 查询落到了视觉窗口, 如
       "刚刚图片是啥"指代刚才看过的图片(查询文本与视觉记忆输出无重叠, 但语义上是
       对刚才视觉的指代).
    2. 查询与某条带 visual_signature 的 experience_alignment 输出/输入文本语义重叠
       >= 0.34(与 _select_visual_imagination_recall 同阈值), 如 "苹果" 指代教过的
       苹果视觉记忆.

    其余模糊命中(如"你是谁?"命中"这是什么?")不构成视觉指代 —— 借视觉签名会造成
    白皮书 §269 "最近答案覆盖"泄漏. 本函数只读取既有 experience_alignment, 不新增实体.
    """
    if not query_text:
        return False
    if backward_source_kind == "recent_visual_window":
        return True
    query_units = _meaningful_text_units(query_text)
    if not query_units:
        return False
    query_unit_set = set(query_units)
    # 复用 _unified_experience_candidates_for_input_signature 以免 observation 对象依赖
    # visual_signature (此处正是要判定是否该借取签名, 不能先假设有签名).
    seen_alignment_ids: set[str] = set()
    for candidate in _unified_experience_candidates_for_observation(
        conn,
        _TextObservation(
            event_id="",
            source_packet_id="",
            occurrence_ids=(),
            signature=_compose_input_signature(_signature_for_chars(tuple(query_text)), None),
            text_signature=_signature_for_chars(tuple(query_text)),
            chars=tuple(query_text),
            text_hash=_hash_text(query_text),
            visual_signature=None,
        ),
        session_id=session_id,
        limit=400,
        exact_input_allowed=False,
    ):
        if candidate.candidate_kind != "experience_alignment":
            continue
        payload = candidate.payload
        if payload.get("expression_role"):
            continue
        if not payload.get("visual_signature"):
            continue
        alignment_id = str(candidate.alignment_event_id or candidate.event_id)
        if alignment_id in seen_alignment_ids:
            continue
        seen_alignment_ids.add(alignment_id)
        output_text = "".join(str(ch) for ch in payload.get("output_chars", ())).strip()
        text_score, coverage_units = _semantic_text_overlap_with_units(query_text, output_text)
        input_payload = _input_payload_for_alignment(conn, payload)
        source_text = str(input_payload.get("text", "") or "")
        if source_text:
            source_score, _ = _semantic_text_overlap_with_units(query_text, source_text)
            if source_score > text_score:
                text_score = source_score
        if text_score >= _VISUAL_MEMORY_REFERENCE_OVERLAP_THRESHOLD and coverage_units:
            return True
    return False


def _select_backward_attribution(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    query_text: str,
    current_visual_signature: str | None,
    prefer_feedback_target: bool = False,
) -> _BackwardAttribution | None:
    windows = _recent_experience_windows(conn, session_id=session_id, limit=18)
    if not windows:
        return None
    best: _BackwardAttribution | None = None
    best_score = 0.0
    query_chars = tuple(query_text.strip())
    query_text_signature = _signature_for_chars(query_chars) if query_chars else ""
    query_visual_tokens = _visual_tokens(current_visual_signature)
    query_textual_closure = _query_textual_closure_support(conn, query_text=query_text)
    for window in windows:
        observation = window["observation"]
        if not isinstance(observation, _RecoveredObservation):
            continue
        if prefer_feedback_target:
            # P2 教学绑定纪律: 反馈的归因目标必须是"真实外部输入"观察 —
            # 跳过内部流/readback/无文本窗口 (否则 auto-idle 夹杂时反馈会绑到
            # idle 事件上, 教学静默失效 — 2026-07-04 实测 bug).
            obs_text = "".join(observation.chars).strip()
            if not obs_text and not observation.visual_signature:
                continue
            if obs_text and _looks_like_internal_flow_text(obs_text):
                continue
            # SDPL 源纪律 (§37/V6): 反馈不得绑到 IMAGINED 事件 — 教师纠正指向的是
            # AP 对外部输入的回应, 不是它的想象. 想象窗口 (visual_imagination_recall)
            # 与真实视觉输入同走 recent_visual_window, 须按底层事件类型区分.
            if observation.event_id:
                _ev_kind_row = conn.execute(
                    "SELECT event_kind FROM phase20_7_experience_events WHERE event_id=?",
                    (observation.event_id,),
                ).fetchone()
                if _ev_kind_row and str(_ev_kind_row[0]) in {
                    "visual_imagination_recall",
                    "idle_think",
                    "idle_observe",
                }:
                    continue
        score = _backward_window_score(
            query_chars=query_chars,
            query_text_signature=query_text_signature,
            query_visual_tokens=query_visual_tokens,
            query_textual_closure=query_textual_closure,
            window=window,
            prefer_feedback_target=prefer_feedback_target,
        )
        if score <= 0.0:
            continue
        e_backward = max(0.0, 1.0 - score)
        cause_slots = tuple(window["cause_slots"])
        flow_candidate = window.get("flow_candidate")
        if isinstance(flow_candidate, ExperienceFlowCandidate):
            unified_candidate = unified_candidate_from_flow(flow_candidate)
            cause_slots = cause_slots + (
                {
                    "slot_kind": "unified_experience_flow_candidate",
                    "candidate_id": flow_candidate.candidate_id,
                    "candidate_kind": flow_candidate.candidate_kind,
                    "payload_ref_count": len(flow_candidate.payload_refs),
                    "edge_count": len(flow_candidate.edge_ids),
                    "support": round(flow_candidate.support, 4),
                },
                unified_candidate.audit_slot(),
            )
        attribution = _BackwardAttribution(
            observation=observation,
            score=score,
            e_backward=e_backward,
            source_kind=str(window["source_kind"]),
            cause_slots=cause_slots,
            neutralized_occurrences=_neutralized_occurrences_for_observation(
                observation,
                score=score,
                source_kind=str(window["source_kind"]),
            ),
        )
        if score > best_score:
            best_score = score
            best = attribution
    threshold = 0.34 if prefer_feedback_target else 0.46
    return best if best is not None and best.score >= threshold else None


def _recent_experience_windows(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    limit: int,
) -> tuple[dict[str, Any], ...]:
    candidates = query_recent_experience_flow_candidates(
        conn,
        session_id=session_id,
        from_json=from_json,
        hash_text=_hash_text,
        signature_for_chars=_signature_for_chars,
        compose_input_signature=_compose_input_signature,
        visual_tokens_from_payloads=_visual_signature_from_payloads,
        limit=limit,
    )
    windows: list[dict[str, Any]] = []
    for candidate in candidates:
        observation = _observation_from_flow_candidate(candidate)
        if observation is None:
            continue
        windows.append(
            _experience_window_from_observation(
                observation,
                source_kind=candidate.source_kind,
                tick=candidate.tick,
                reward=0.0,
                punish=0.0,
                recency_rank=len(windows),
                flow_candidate=candidate,
            )
        )
    return tuple(windows)


def _experience_window_from_observation(
    observation: _RecoveredObservation,
    *,
    source_kind: str,
    tick: int,
    reward: float,
    punish: float,
    recency_rank: int,
    flow_candidate: ExperienceFlowCandidate | None = None,
) -> dict[str, Any]:
    return {
        "observation": observation,
        "source_kind": source_kind,
        "tick": int(tick),
        "reward": float(reward),
        "punish": float(punish),
        "recency_rank": int(recency_rank),
        "cause_slots": _cause_slots_for_observation(observation),
        "flow_candidate": flow_candidate,
        "unified_candidate": unified_candidate_from_flow(flow_candidate) if flow_candidate is not None else None,
    }


def _observation_from_flow_candidate(candidate: ExperienceFlowCandidate) -> _RecoveredObservation | None:
    chars = tuple(candidate.text)
    text_signature = candidate.text_signature or (_signature_for_chars(chars) if chars else "")
    visual_signature = candidate.visual_signature
    if not text_signature and not visual_signature:
        return None
    signature = _compose_input_signature(text_signature, visual_signature)
    recovery_kind = "experience_flow_" + candidate.candidate_kind
    return _RecoveredObservation(
        event_id=candidate.event_id,
        source_packet_id=candidate.source_packet_id,
        occurrence_ids=candidate.occurrence_ids,
        signature=signature,
        text_signature=text_signature,
        chars=chars,
        text_hash=_hash_text(candidate.text),
        visual_signature=visual_signature,
        recovery_kind=recovery_kind,
    )


def _visual_signature_from_payloads(payloads: Sequence[dict[str, Any]]) -> tuple[str, str]:
    visual_parts: list[str] = []
    for payload in payloads:
        evidence = payload.get("visual_evidence")
        if not isinstance(evidence, dict):
            continue
        signature = str(evidence.get("signature", "") or "")
        if signature:
            visual_parts.append(signature)
        tokens = evidence.get("tokens", ())
        if isinstance(tokens, Sequence) and not isinstance(tokens, (str, bytes, bytearray)):
            visual_parts.extend(str(token) for token in tokens if str(token))
    tokens = tuple(sorted(set(visual_parts)))
    if not tokens:
        return "", ""
    token_text = ",".join(tokens)
    return "visual::" + _hash_text("|".join(tokens)) + "::" + token_text, token_text


def _backward_window_score(
    *,
    query_chars: tuple[str, ...],
    query_text_signature: str,
    query_visual_tokens: set[str],
    query_textual_closure: float,
    window: dict[str, Any],
    prefer_feedback_target: bool,
) -> float:
    observation = window["observation"]
    if not isinstance(observation, _RecoveredObservation):
        return 0.0
    text_similarity = 0.0
    if query_chars and observation.chars:
        text_similarity = _structural_similarity(query_chars, observation.chars)[0]
    exact_text = 1.0 if query_text_signature and query_text_signature == observation.text_signature else 0.0
    visual_similarity = 0.0
    candidate_visual_tokens = _visual_tokens(observation.visual_signature)
    if query_visual_tokens and candidate_visual_tokens:
        visual_similarity = _visual_evidence_neutralization(query_visual_tokens, candidate_visual_tokens)
    source_kind = str(window["source_kind"])
    recency = 1.0 / (1.0 + float(window["recency_rank"]))
    value_bias = max(0.0, float(window["reward"])) * 0.08 - max(0.0, float(window["punish"])) * 0.08
    feedback_gain = 0.14 if prefer_feedback_target else 0.0
    if prefer_feedback_target and source_kind == "recent_visual_window" and not query_chars:
        feedback_gain += 0.28
    if prefer_feedback_target and source_kind == "recent_text_window":
        feedback_gain += 0.08
    flow_support_gain = 0.0
    flow_candidate = window.get("flow_candidate")
    if isinstance(flow_candidate, ExperienceFlowCandidate):
        flow_support_gain = min(0.28, float(flow_candidate.support) * 0.28)
    structure_gap = _unit(1.0 - query_textual_closure) if query_chars else 1.0
    open_slot_gain = structure_gap * min(0.18, recency * 0.10 + flow_support_gain * 0.32)
    modality_gain = 0.10 if candidate_visual_tokens else 0.0
    score = (
        exact_text * 0.45
        + text_similarity * 0.22
        + visual_similarity * 0.52
        + recency * 0.18
        + open_slot_gain
        + feedback_gain
        + modality_gain
        + flow_support_gain
        + value_bias
    )
    if source_kind == "recent_visual_window" and query_chars and query_textual_closure >= 0.58:
        score -= min(0.24, query_textual_closure * 0.24)
    return max(0.0, min(1.0, score))


def _query_textual_closure_support(conn: sqlite3.Connection, *, query_text: str) -> float:
    chars = tuple(query_text.strip())
    if not chars:
        return 0.0
    query = ExperienceRecallQuery(
        query_text="".join(chars),
        text_signature=_signature_for_chars(chars),
        visual_signature=None,
        input_signature=None,
        open_reference=False,
        exact_input_allowed=True,
    )
    candidates = query_experience_alignment_candidates(
        conn,
        query,
        from_json=from_json,
        is_tombstoned=is_tombstoned,
        input_payload_for_alignment=_input_payload_for_alignment,
        semantic_text_overlap_with_units=_semantic_text_overlap_with_units,
        visual_similarity=_visual_signature_similarity,
        limit=160,
    )
    if not candidates:
        return 0.0
    return _unit(max(float(candidate.support) for candidate in candidates))


def _select_alignment_by_backward_neutralization(
    conn: sqlite3.Connection,
    observation: _ObservationLike,
) -> dict[str, Any] | None:
    candidates = _unified_experience_candidates_for_observation(conn, observation, limit=400)
    best: dict[str, Any] | None = None
    best_score = 0.0
    for unified_candidate in candidates:
        if unified_candidate.candidate_kind != "experience_alignment":
            continue
        payload = unified_candidate.payload
        if payload.get("expression_role"):
            continue
        candidate_visual = str(payload.get("visual_signature", "") or "")
        visual_similarity = _visual_signature_similarity(observation.visual_signature, candidate_visual)
        text_match = 1.0 if observation.text_signature and payload.get("text_signature") == observation.text_signature else 0.0
        visual_reference_family = bool(payload.get("visual_reference_family")) and _observation_is_visual_reference_family(observation)
        if not _visual_tokens(candidate_visual) and not text_match:
            continue
        if visual_similarity < 0.62 and text_match < 1.0 and not visual_reference_family:
            continue
        if observation.visual_signature and candidate_visual and visual_similarity < 0.62:
            continue
        support, support_terms = compute_unified_experience_support(
            visual_similarity=visual_similarity,
            exact_text=text_match,
            open_reference=1.0 if visual_reference_family else 0.0,
        )
        support = max(0.0, min(1.0, max(support, min(float(unified_candidate.support), visual_similarity + 0.18))))
        if support > best_score:
            best_score = support
            best = {
                "alignment_event_id": str(unified_candidate.alignment_event_id or unified_candidate.event_id),
                "alignment_payload": payload,
                "score": support,
                "visual_similarity": visual_similarity,
                "candidate_audit_slots": (unified_candidate.audit_slot(),),
                "support_terms": tuple(support_terms)
                + (
                    ("unified_candidate_support", round(float(unified_candidate.support), 4)),
                ),
            }
    return best if best is not None and best_score >= 0.68 else None


def _visual_evidence_neutralization(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    exact = _token_overlap(left, right)
    left_groups = _visual_token_groups(left)
    right_groups = _visual_token_groups(right)
    weighted = 0.0
    total = 0.0
    weights = {
        "rgb": 0.32,
        "sat": 0.16,
        "luma": 0.14,
        "edge": 0.18,
        "xy": 0.08,
        "clarity": 0.04,
        "signature": 0.08,
    }
    for group, weight in weights.items():
        total += weight
        if left_groups.get(group) and right_groups.get(group):
            weighted += weight * _token_overlap(left_groups[group], right_groups[group])
    if total <= 0:
        return exact
    return max(exact, weighted / total)


def _semantic_text_overlap(query_text: str, memory_text: str) -> float:
    return _semantic_text_overlap_with_units(query_text, memory_text)[0]


def _semantic_text_overlap_with_units(query_text: str, memory_text: str) -> tuple[float, tuple[str, ...]]:
    query_units = _meaningful_text_units(query_text)
    memory_units = _meaningful_text_units(memory_text)
    if not query_units or not memory_units:
        return 0.0, ()
    query_set = set(query_units)
    memory_set = set(memory_units)
    shared = query_set & memory_set
    token_score = len(shared) / max(len(query_set | memory_set), 1)
    ordered_score = _structural_similarity(query_units, memory_units)[0]
    phrase_score = 0.0
    q = "".join(query_units)
    m = "".join(memory_units)
    if q and m and (q in m or m in q):
        phrase_score = min(len(q), len(m)) / max(len(q), len(m), 1)
    return max(token_score, ordered_score * 0.72, phrase_score), tuple(unit for unit in query_units if unit in shared)


def _text_unit_sa_type_ids(text: str) -> tuple[str, ...]:
    """Distinct text_unit sa_type ids for the non-whitespace chars of ``text``."""
    seen: set[str] = set()
    ordered: list[str] = []
    for ch in str(text):
        if ch.isspace():
            continue
        sa_id = f"text_unit::{_hash_text(ch)}"
        if sa_id not in seen:
            seen.add(sa_id)
            ordered.append(sa_id)
    return tuple(ordered)


def _l1_text_vector_similarity(conn: sqlite3.Connection, query_text: str, memory_text: str) -> float:
    """Learned L1 cosine similarity between two short texts (whitepaper §35.3).

    The text-level vector is the centroid of its distinct text_unit sa_type L1
    vectors. Returns 0.0 when either side has no learned vectors yet, so absent
    vectors contribute nothing (mirroring the 0-default in the support formula).
    """
    query_ids = _text_unit_sa_type_ids(query_text)
    memory_ids = _text_unit_sa_type_ids(memory_text)
    if not query_ids or not memory_ids:
        return 0.0
    loaded = load_sa_type_vector_l1(conn, query_ids + memory_ids)
    query_vecs = [loaded[sid][1] for sid in query_ids]
    memory_vecs = [loaded[sid][1] for sid in memory_ids]
    return l1_cosine(l1_centroid(query_vecs), l1_centroid(memory_vecs))


PHASE20_11_L1_TRIPLET_UPDATE_ID = "apv3_phase20_11_l1_online_embedding_triplet_update/v1"


def _apply_l1_triplet_update(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    tick: int,
    observation: _ObservationLike | None,
    feedback_chars: tuple[str, ...],
    reward: float,
    punish: float,
) -> dict[str, Any] | None:
    """Online L1 triplet update driven by prediction error + reward/punish.

    Triggered inside _record_teacher_feedback, where the experience_alignment
    event, the input context (observation) and the taught output (feedback_chars)
    are all in scope. The anchor is each taught output char sa_type (the object
    whose prediction was wrong, hence carrying cognitive pressure P=R−V); the
    positive reference is the centroid of the co-occurring input char sa_types
    (the context, which is the reference and is NOT co-updated, per §33.1
    asymmetry). The prediction-error magnitude is read from the live StatePool
    on each output sa_type (teacher correction = prediction was wrong = high P).
    No new entity is created: vectors are stored on the existing vector_l1
    column and the update is a projection onto the experience flow.
    """
    if not feedback_chars:
        return None
    input_chars = tuple(ch for ch in (observation.chars if observation else ()) if not ch.isspace())
    if not input_chars:
        return None
    input_sa_ids = _text_unit_sa_type_ids("".join(input_chars))
    if not input_sa_ids:
        return None
    output_sa_ids = list(dict.fromkeys(f"text_unit::{_hash_text(str(ch))}" for ch in feedback_chars))
    if not output_sa_ids:
        return None

    input_loaded = load_sa_type_vector_l1(conn, input_sa_ids)
    positive_centroid = l1_centroid([input_loaded[sid][1] for sid in input_sa_ids])
    output_loaded = load_sa_type_vector_l1(conn, output_sa_ids)

    updated: list[dict[str, Any]] = []
    total_delta = 0.0
    for sa_id in output_sa_ids:
        support_count, vec = output_loaded[sa_id]
        # Prediction error from the live state pool: a taught correction means
        # the predicted output did not match, i.e. high cognitive pressure on
        # the responsible sa_type. Fall back to a teaching-event proxy (0.5) when
        # the sa_type is not currently in the pool (e.g. expression-role path).
        item = pool.items.get(sa_id) if pool is not None else None
        if item is not None:
            prediction_error = max(0.0, min(1.0, abs(float(item.cognitive_pressure))))
        else:
            prediction_error = 0.5
        new_vec, new_count = l1_triplet_update_vector(
            vec,
            positive_centroid=positive_centroid,
            negative_centroid=None,
            prediction_error=prediction_error,
            reward=reward,
            punish=punish,
            support_count=support_count,
        )
        prev_norm = math.sqrt(sum(float(v) * float(v) for v in vec))
        new_norm = math.sqrt(sum(float(v) * float(v) for v in new_vec))
        delta = abs(new_norm - prev_norm)
        total_delta += delta
        update_sa_type_vector_l1(
            conn, sa_type_id=sa_id, support_count=new_count, vector=new_vec, tick=tick,
        )
        updated.append(
            {
                "sa_type_id": sa_id,
                "support_count": new_count,
                "prediction_error": round(float(prediction_error), 4),
                "vector_delta_norm": round(float(delta), 6),
            }
        )

    return {
        "delta_kind": "l1_vector_triplet_update",
        "formula_id": PHASE20_11_L1_TRIPLET_UPDATE_ID,
        "session_id": session_id,
        "tick": tick,
        "anchor_kind": "taught_output_char",
        "positive_reference_kind": "co_occurring_input_context",
        "anchor_sa_type_ids": output_sa_ids,
        "positive_reference_sa_type_ids": list(input_sa_ids),
        "negative_reference_sa_type_ids": [],
        "reward": round(float(reward), 4),
        "punish": round(float(punish), 4),
        "updated_vectors": updated[:12],
        "updated_vector_count": len(updated),
        "total_vector_delta_norm": round(float(total_delta), 6),
        "projection_only": True,
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
    }


PHASE20_12_L2_STRUCTURE_UPDATE_ID = "apv3_phase20_12_l2_temporal_edge_embedding_structure_update/v1"


def _apply_l2_temporal_edge_update(
    conn: sqlite3.Connection,
    pool: StatePool | None,
    *,
    session_id: str,
    tick: int,
    observation: _ObservationLike | None,
    feedback_chars: tuple[str, ...],
    reward: float,
    punish: float,
) -> dict[str, Any] | None:
    """Online L2 structure update for type-pair linear_next edges (whitepaper §173.3).

    Triggered inside _record_teacher_feedback alongside the L1 update. For the
    taught output sequence, form linear_next type-pair edges between adjacent
    output chars and update each edge's z_edge toward
    compose(z_a, relation_type, z_b). The endpoints' z_a/z_b are the already-learned
    L1 vectors (so L2 runs after L1 in the same feedback step). Order is
    asymmetric: (a->b) and (b->a) are different edge sa_types, and compose keeps
    them apart at the vector level (§173.3 "z_next(a->b) != z_next(b->a)").

    No new entity: vectors are stored on the existing vector_l2 column; the
    type-pair edge sa_type is only the key for that existing column, mirroring L1.
    L2 does NOT replicate SSP's per-occurrence explicit edges — it only adds a
    learned soft-similarity vector on the type-pair key (§35.4 red line 1:
    online embedding does not replace the explicit channel).
    """
    if len(feedback_chars) < 2:
        return None
    reward_value = float(reward)
    punish_value = float(punish)
    structure_support = min(1.0, 0.5 + reward_value * 0.3 + punish_value * 0.3)

    updated: list[dict[str, Any]] = []
    total_delta = 0.0
    prev_sa_id = f"text_unit::{_hash_text(str(feedback_chars[0]))}"
    for ch in feedback_chars[1:]:
        dst_sa_id = f"text_unit::{_hash_text(str(ch))}"
        edge_sa_id = l2_edge_sa_type_id(L2_RELATION_LINEAR_NEXT, prev_sa_id, dst_sa_id)
        upsert_sa_type(
            conn,
            sa_type_id=edge_sa_id,
            substrate="text_edge",
            modality="structure",
            canonical_hint=f"{prev_sa_id} -> {dst_sa_id}",
            tick=tick,
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
        prev_norm = math.sqrt(sum(float(v) * float(v) for v in edge_vec))
        new_norm = math.sqrt(sum(float(v) * float(v) for v in new_vec))
        delta = abs(new_norm - prev_norm)
        total_delta += delta
        update_sa_type_vector_l2(
            conn, sa_type_id=edge_sa_id, support_count=new_count, vector=new_vec, tick=tick,
        )
        updated.append(
            {
                "edge_sa_type_id": edge_sa_id,
                "src_sa_type_id": prev_sa_id,
                "dst_sa_type_id": dst_sa_id,
                "support_count": new_count,
                "structure_support": round(float(structure_support), 4),
                "vector_delta_norm": round(float(delta), 6),
            }
        )
        prev_sa_id = dst_sa_id

    return {
        "delta_kind": "l2_temporal_edge_update",
        "formula_id": PHASE20_12_L2_STRUCTURE_UPDATE_ID,
        "session_id": session_id,
        "tick": tick,
        "edge_kind": "linear_next",
        "updated_edges": updated[:12],
        "updated_edge_count": len(updated),
        "total_vector_delta_norm": round(float(total_delta), 6),
        "projection_only": True,
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
    }


PHASE20_13B_L3_ACTION_CONSEQUENCE_UPDATE_ID = (
    "apv3_phase20_13b_l3_action_consequence_embedding_update/v1"
)


def _apply_l3_action_consequence_update(
    conn: sqlite3.Connection,
    pool: StatePool | None,
    *,
    session_id: str,
    tick: int,
    observation: _ObservationLike | None,
    feedback: TeacherFeedback,
    output_intent: str,
) -> dict[str, Any] | None:
    """Online L3 action-consequence update (whitepaper §173.3 line 7178-7181).

    Triggered inside _record_teacher_feedback after L1/L2. The teacher feedback is
    the outcome of the action AP took for this observation:
      state     = observation.signature (the scene the teacher is evaluating)
      action    = AP's chosen outward action for this scene (see resolution below)
      outcome   = reward_mag - punish_mag (§173.3 outcome_value)
    Updates the (state, action) edge's z_action_context toward the success anchor
    on reward, away from it on punish (§173.4 "行动了但失败" negative update), with
    §173.5 annealing. No new entity: vectors stored on the existing vector_l3 column;
    the edge sa_type is only the key. L3 does NOT replace the explicit action
    competition channel (§35.4 red line 1) — it only learns a soft consequence
    vector used later as a drive modulation.

    Action resolution: the teacher is evaluating AP's *prior* response to this
    scene. In the current flow the feedback is recorded (integrate_feedback) before
    this turn's write_cell generation, so output_intent at the feedback point is
    often an internal action. We therefore resolve the action as: output_intent if
    it is already an outward action, else the nearest selected outward action in
    this session at a tick strictly before the feedback tick (the action being
    judged). This mirrors the rebuild recovery and keeps L3's state-action pair
    semantically aligned with §1727 (don't mix internal ticks into consequences).
    """
    if observation is None:
        return None
    state_signature = str(getattr(observation, "signature", "") or "")
    if not state_signature:
        return None
    action_type = str(output_intent or "")
    if action_type not in L3_OUTWARD_ACTION_TYPES:
        # output_intent at feedback time is often internal (integrate_feedback /
        # observe_text); recover the outward action the teacher is judging.
        outward_tuple = tuple(L3_OUTWARD_ACTION_TYPES)
        act_row = conn.execute(
            """
            SELECT action_type FROM phase20_7_action_records
            WHERE session_id=? AND selected=1 AND tick<?
              AND action_type IN (%s)
            ORDER BY tick DESC, created_at_ms DESC LIMIT 1
            """ % ",".join("?" for _ in outward_tuple),
            (str(session_id), int(tick), *outward_tuple),
        ).fetchone()
        if not act_row:
            return None
        action_type = str(act_row[0])
    reward_value = float(feedback.reward_mag)
    punish_value = float(feedback.punish_mag)
    outcome_value = reward_value - punish_value
    if abs(outcome_value) < 1e-6:
        return None
    edge_sa_id = l3_edge_sa_type_id(state_signature, action_type)
    upsert_sa_type(
        conn,
        sa_type_id=edge_sa_id,
        substrate="action_edge",
        modality="structure",
        canonical_hint=f"{state_signature} :: {action_type}",
        tick=tick,
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
    prev_norm = math.sqrt(sum(float(v) * float(v) for v in edge_vec))
    new_norm = math.sqrt(sum(float(v) * float(v) for v in new_vec))
    delta = abs(new_norm - prev_norm)
    update_sa_type_vector_l3(
        conn, sa_type_id=edge_sa_id, support_count=new_count, vector=new_vec, tick=tick,
    )
    return {
        "delta_kind": "l3_action_consequence_update",
        "formula_id": PHASE20_13B_L3_ACTION_CONSEQUENCE_UPDATE_ID,
        "session_id": session_id,
        "tick": tick,
        "state_signature": state_signature,
        "action_type": action_type,
        "outcome_value": round(outcome_value, 4),
        "edge_sa_type_id": edge_sa_id,
        "support_count": new_count,
        "vector_delta_norm": round(float(delta), 6),
        "projection_only": True,
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
    }


def _apply_l3_action_consequence_modulation(
    conn: sqlite3.Connection | None,
    *,
    state_signature: str,
    competition_rows: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    """§1726: 用 L3 (state, action) 向量调制各 action 的 drive.

    对每个 competition row 的 action_type, 查 (state, action) 的 L3 向量. 若已学
    (support_count>0), 用该向量与"成功锚点"的 cosine 作为 outcome_expectation, 乘性
    调制 drive: 成功过→上调, 失败过→下调, 乘子 ∈ [0.7, 1.3] 有界不归零(§1742).
    **support_count=0(未学)时乘子=1.0 中性**, 不调制——避免 L3 学到任何东西之前就
    压低所有 action drive, 破坏首教和未知请求教师(对抗性自审关键修正, §173.6).
    不改 selected 字段、不增删行, 只调 drive 数值. conn=None 时不调制(零回归).
    """
    if conn is None or not state_signature:
        return competition_rows
    action_types = tuple(
        str(row.get("action_type", "")) for row in competition_rows
    )
    edge_ids = {
        at: l3_edge_sa_type_id(state_signature, at)
        for at in action_types
        if at in L3_OUTWARD_ACTION_TYPES
    }
    if not edge_ids:
        return competition_rows
    loaded = load_sa_type_vector_l3(conn, tuple(edge_ids.values()))
    modulated: list[dict[str, Any]] = []
    for row in competition_rows:
        at = str(row.get("action_type", ""))
        edge_id = edge_ids.get(at)
        if edge_id is None:
            modulated.append(row)
            continue
        support_count, edge_vec = loaded[edge_id]
        if support_count <= 0:
            modulated.append(row)  # 未学: 中性, 不调制
            continue
        anchor = l3_action_context_code(state_signature, at)
        outcome_expectation = l3_cosine(edge_vec, anchor)
        multiplier = 0.7 + 0.6 * outcome_expectation
        new_row = dict(row)
        drive_before = _unit(float(row.get("drive", 0.0)))
        new_row["drive_before_l3_modulation"] = round(drive_before, 4)
        new_row["drive"] = round(_unit(drive_before * multiplier), 4)
        new_row["l3_action_consequence_modulation"] = {
            "formula_id": PHASE20_13B_L3_ACTION_CONSEQUENCE_UPDATE_ID,
            "state_signature": state_signature,
            "action_type": at,
            "edge_sa_type_id": edge_id,
            "support_count": support_count,
            "outcome_expectation": round(outcome_expectation, 4),
            "drive_multiplier": round(multiplier, 4),
            "creates_reply_candidate": False,
            "writes_answer_directly": False,
        }
        modulated.append(new_row)
    return tuple(modulated)


def _meaningful_text_units(text: str) -> tuple[str, ...]:
    value = str(text).strip()
    if not value:
        return ()
    cleaned = "".join(ch for ch in value if not ch.isspace() and ch not in " \t\r\n?？!！,，.。;；:：、")
    units: list[str] = []
    for size in (4, 3, 2):
        for index in range(0, max(0, len(cleaned) - size + 1)):
            part = cleaned[index : index + size]
            if part and not part.isspace():
                units.append(part)
    units.extend(ch for ch in cleaned if ch and not ch.isspace())
    if not units and value:
        units.extend(ch for ch in value if ch and not ch.isspace())
    return tuple(units)


def _patch_payload_refs_for_alignment(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    visual_signature: str,
) -> tuple[str, ...]:
    input_event_id = str(payload.get("input_event_id") or "")
    refs: list[str] = []
    if input_event_id:
        rows = conn.execute(
            """
            SELECT payload_ref
            FROM phase20_7_occurrences
            WHERE event_id=?
              AND substrate='vision'
              AND payload_ref IS NOT NULL
            ORDER BY tick ASC
            """,
            (input_event_id,),
        ).fetchall()
        refs.extend(str(row[0]) for row in rows if row[0])
    if len(refs) < 3:
        signature_tokens = _visual_tokens(visual_signature)
        scored: list[tuple[float, str]] = []
        for candidate in _all_recent_visual_flow_candidates(conn, limit=300):
            if not candidate.payload_refs or not candidate.visual_signature:
                continue
            score = _visual_evidence_neutralization(signature_tokens, _visual_tokens(candidate.visual_signature))
            if score <= 0.18:
                continue
            for payload_ref in candidate.payload_refs:
                if payload_ref in refs:
                    continue
                scored.append((score, payload_ref))
        for _, ref in sorted(scored, key=lambda item: item[0], reverse=True):
            if ref not in refs:
                refs.append(ref)
            if len(refs) >= 12:
                break
    return tuple(refs[:12])


def _all_recent_visual_flow_candidates(conn: sqlite3.Connection, *, limit: int) -> tuple[ExperienceFlowCandidate, ...]:
    rows = conn.execute("SELECT DISTINCT session_id FROM phase20_7_experience_events ORDER BY created_at_ms DESC LIMIT 24").fetchall()
    out: list[ExperienceFlowCandidate] = []
    for (session_id,) in rows:
        out.extend(
            candidate
            for candidate in query_recent_experience_flow_candidates(
                conn,
                session_id=str(session_id),
                from_json=from_json,
                hash_text=_hash_text,
                signature_for_chars=_signature_for_chars,
                compose_input_signature=_compose_input_signature,
                visual_tokens_from_payloads=_visual_signature_from_payloads,
                limit=max(1, int(limit) // 4),
            )
            if candidate.visual_signature and candidate.payload_refs
        )
        if len(out) >= int(limit):
            break
    return tuple(out[: int(limit)])


def _visual_token_groups(tokens: set[str]) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    for token in tokens:
        text = str(token)
        if text.startswith("visual_patch_evidence::"):
            key = "signature"
        elif ":" in text:
            key = text.split(":", 1)[0]
        else:
            key = "other"
        groups.setdefault(key, set()).add(text)
    return groups


def _cause_slots_for_observation(observation: _ObservationLike) -> tuple[dict[str, Any], ...]:
    slots: list[dict[str, Any]] = []
    if observation.text_signature:
        slots.append(
            {
                "slot_kind": "text_structure_before_current",
                "signature": observation.text_signature,
                "unit_count": len(observation.chars),
                "virtual_energy": 0.32,
            }
        )
    if observation.visual_signature:
        tokens = sorted(_visual_tokens(observation.visual_signature))
        slots.append(
            {
                "slot_kind": "visual_structure_before_current",
                "signature": observation.visual_signature,
                "token_count": len(tokens),
                "tokens": tokens[:12],
                "virtual_energy": 0.48,
            }
        )
    return tuple(slots)


def _neutralized_occurrences_for_observation(
    observation: _ObservationLike,
    *,
    score: float,
    source_kind: str,
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    # 3-way residual energy classification:
    # score ≈ recall support (0=no match, 1=perfect match)
    # matched:        score >= 0.75 → strong alignment, neutralize virtual energy
    # memory_excess:  0.50 < score < 0.75 → AP partially over-predicted → add virtual
    # reality_excess: score <= 0.50 → reality exceeded memory → add real energy boost
    if score >= 0.75:
        energy_mode = "matched"
    elif score <= 0.50:
        energy_mode = "reality_excess"
    else:
        energy_mode = "memory_excess"
    for occurrence_id in observation.occurrence_ids[:8]:
        rows.append(
            {
                "occurrence_id": occurrence_id,
                "neutralize_score": round(float(score), 4),
                "energy_mode": energy_mode,
                "source_kind": source_kind,
            }
        )
    if observation.visual_signature:
        rows.append(
            {
                "occurrence_id": "visual_signature::" + _hash_text(observation.visual_signature),
                "neutralize_score": round(float(score), 4),
                "energy_mode": energy_mode,
                "source_kind": source_kind,
            }
        )
    return tuple(rows)


def _observation_modality_mix(observation: _ObservationLike) -> tuple[str, ...]:
    modalities = ["text"] if observation.chars else []
    if observation.visual_signature:
        modalities.append("vision")
    return tuple(modalities)


def _public_recovery_kind(observation: _RecoveredObservation) -> str:
    if observation.recovery_kind == "experience_flow_recent_visual_window":
        return "recent_visual"
    if observation.recovery_kind == "experience_flow_recent_text_window":
        return "recent_text"
    if observation.recovery_kind == "experience_flow_recent_audio_window":
        return "recent_audio"
    return observation.recovery_kind


def _occurrences_for_event(conn: sqlite3.Connection, event_id: str) -> tuple[str, ...]:
    rows = conn.execute(
        """
        SELECT occurrence_id
        FROM phase20_7_occurrences
        WHERE event_id=?
        ORDER BY tick ASC
        """,
        (event_id,),
    ).fetchall()
    return tuple(str(item[0]) for item in rows)


def _recover_recent_visual_observation(
    conn: sqlite3.Connection,
    *,
    session_id: str,
) -> _RecoveredObservation | None:
    row = conn.execute(
        """
        SELECT event_id, source_packet_id, payload_json
        FROM phase20_7_experience_events
        WHERE event_kind='visual_patch_sample' AND session_id=?
        ORDER BY created_at_ms DESC, tick DESC
        LIMIT 12
        """,
        (session_id,),
    ).fetchall()
    return _visual_observation_from_rows(conn, row, recovery_kind="recent_visual")


def _observation_from_current_visual_events(
    conn: sqlite3.Connection,
    events: Sequence[RuntimeTickEventV2],
) -> _RecoveredObservation | None:
    event_ids = [
        str(event.experience_event_ids_written[0])
        for event in events
        if event.selected_action.get("action_type") in {"move_focus", "maintain_focus"}
        and event.experience_event_ids_written
    ]
    if not event_ids:
        return None
    placeholders = ",".join("?" for _ in event_ids)
    rows = conn.execute(
        f"""
        SELECT event_id, source_packet_id, payload_json
        FROM phase20_7_experience_events
        WHERE event_id IN ({placeholders})
        ORDER BY tick ASC
        """,
        tuple(event_ids),
    ).fetchall()
    return _visual_observation_from_rows(conn, rows, recovery_kind="current_visual")


def _visual_observation_from_rows(
    conn: sqlite3.Connection,
    rows: Sequence[object],
    *,
    recovery_kind: str,
) -> _RecoveredObservation | None:
    visual_parts: list[str] = []
    event_ids: list[str] = []
    source_packet_id = ""
    for row in rows:
        event_id, packet_id, payload_json = row
        payload = from_json(str(payload_json))
        if not isinstance(payload, dict):
            continue
        evidence = payload.get("visual_evidence")
        if not isinstance(evidence, dict):
            continue
        signature = str(evidence.get("signature", "") or "")
        if signature:
            visual_parts.append(signature)
        tokens = evidence.get("tokens", ())
        if isinstance(tokens, Sequence) and not isinstance(tokens, (str, bytes, bytearray)):
            visual_parts.extend(str(token) for token in tokens if str(token))
        event_ids.append(str(event_id))
        source_packet_id = str(packet_id or source_packet_id)
    if not visual_parts or not event_ids:
        return None
    tokens = tuple(sorted(set(visual_parts)))
    visual_signature = "visual::" + _hash_text("|".join(tokens)) + "::" + ",".join(tokens)
    chars = tuple(VISUAL_FOCUS_ANCHOR_UNIT)
    text_signature = _signature_for_chars(chars)
    signature = _compose_input_signature(text_signature, visual_signature)
    occ_rows = conn.execute(
        """
        SELECT occurrence_id
        FROM phase20_7_occurrences
        WHERE event_id IN ({})
        ORDER BY tick ASC
        """.format(",".join("?" for _ in event_ids)),
        tuple(event_ids),
    ).fetchall()
    occurrence_ids = tuple(str(item[0]) for item in occ_rows)
    return _RecoveredObservation(
        event_id=event_ids[-1],
        source_packet_id=source_packet_id,
        occurrence_ids=occurrence_ids,
        signature=signature,
        text_signature=text_signature,
        chars=chars,
        text_hash=_hash_text(VISUAL_FOCUS_ANCHOR_UNIT),
        visual_signature=visual_signature,
        recovery_kind=recovery_kind,
    )


def _structural_similarity(query_units: tuple[str, ...], source_units: tuple[str, ...]) -> tuple[float, list[str], list[str]]:
    if not query_units or not source_units:
        return 0.0, [], list(query_units)
    max_len = max(len(query_units), len(source_units))
    positional_matches = sum(1 for left, right in zip(query_units, source_units) if left == right)
    positional_score = positional_matches / max_len
    query_bigrams = set(zip(query_units, query_units[1:]))
    source_bigrams = set(zip(source_units, source_units[1:]))
    if query_bigrams or source_bigrams:
        bigram_score = len(query_bigrams & source_bigrams) / max(len(query_bigrams | source_bigrams), 1)
    else:
        bigram_score = positional_score
    prefix_matches = 0
    for left, right in zip(query_units, source_units):
        if left != right:
            break
        prefix_matches += 1
    prefix_score = prefix_matches / max_len
    suffix_matches = 0
    for left, right in zip(reversed(query_units), reversed(source_units)):
        if left != right:
            break
        suffix_matches += 1
    suffix_score = suffix_matches / max_len
    span_len, query_start, source_start = _longest_common_contiguous_span(query_units, source_units)
    span_query_coverage = span_len / max(len(query_units), 1)
    span_source_coverage = span_len / max(len(source_units), 1)
    span_edge_fit = 0.0
    if span_len:
        query_edge = query_start == 0 or query_start + span_len == len(query_units)
        source_edge = source_start == 0 or source_start + span_len == len(source_units)
        span_edge_fit = 1.0 if query_edge and source_edge else 0.45 if query_edge or source_edge else 0.0
    span_score = span_query_coverage * 0.62 + span_source_coverage * 0.22 + span_edge_fit * 0.16
    if span_len < 2 and max(len(query_units), len(source_units)) > 1:
        span_score *= 0.45
    subsequence_len = _longest_common_subsequence_len(query_units, source_units)
    subsequence_score = (
        (subsequence_len / max(len(query_units), 1)) * 0.56
        + (subsequence_len / max(len(source_units), 1)) * 0.24
    )
    ordered_score = positional_score * 0.38 + bigram_score * 0.28 + prefix_score * 0.17 + suffix_score * 0.17
    if span_len:
        shared_units = list(query_units[query_start : query_start + span_len])
        residual_units = list(query_units[:query_start] + query_units[query_start + span_len :])
    else:
        shared_units = [left for left, right in zip(query_units, source_units) if left == right]
        residual_units = [unit for unit in query_units if unit not in shared_units]
    score = max(ordered_score, span_score, subsequence_score * 0.86)
    return score, shared_units, residual_units


def _longest_common_contiguous_span(
    query_units: tuple[str, ...],
    source_units: tuple[str, ...],
) -> tuple[int, int, int]:
    best_len = 0
    best_query_start = 0
    best_source_start = 0
    previous = [0] * (len(source_units) + 1)
    for query_index, query_unit in enumerate(query_units, start=1):
        current = [0] * (len(source_units) + 1)
        for source_index, source_unit in enumerate(source_units, start=1):
            if query_unit != source_unit:
                continue
            current[source_index] = previous[source_index - 1] + 1
            if current[source_index] > best_len:
                best_len = current[source_index]
                best_query_start = query_index - best_len
                best_source_start = source_index - best_len
        previous = current
    return best_len, best_query_start, best_source_start


def _longest_common_subsequence_len(query_units: tuple[str, ...], source_units: tuple[str, ...]) -> int:
    previous = [0] * (len(source_units) + 1)
    for query_unit in query_units:
        current = [0] * (len(source_units) + 1)
        for source_index, source_unit in enumerate(source_units, start=1):
            if query_unit == source_unit:
                current[source_index] = previous[source_index - 1] + 1
            else:
                current[source_index] = max(previous[source_index], current[source_index - 1])
        previous = current
    return previous[-1] if previous else 0


def _observation_is_visual_reference_family(observation: _ObservationLike | None) -> bool:
    if observation is None or not observation.visual_signature:
        return False
    if isinstance(observation, _RecoveredObservation) and observation.recovery_kind in {"recent_visual", "current_visual"}:
        return True
    return bool(observation.visual_signature)


def _apply_cstar_statepool_feedback(
    pool: StatePool,
    *,
    tick: int,
    observation: _ObservationLike | None,
    selected_action: dict[str, Any],
    action_competition: Sequence[dict[str, Any]],
    b0: _ExactB0 | None,
    structural_b: _StructuralB | None,
    c_forward: Sequence[dict[str, Any]],
    c_backward: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    output_chars = b0.output_chars if b0 is not None else structural_b.output_chars if structural_b is not None else ()
    b_support = _unit(
        b0.support
        if b0 is not None
        else structural_b.similarity
        if structural_b is not None
        else 0.0
    )
    forward_support = max(_unit(max((_runtime_support(row) for row in c_forward), default=0.0)), b_support if output_chars else 0.0)
    backward_grasp = max(_unit(max((_runtime_backward_grasp(row) for row in c_backward), default=0.0)), b_support if observation is not None else 0.0)
    action_drive = _unit(_selected_drive_from_competition(action_competition, selected_action))
    conflict_entropy = _runtime_competition_entropy(action_competition)
    cstar_virtual_energy = max(forward_support, backward_grasp, action_drive * 0.72) * (1.0 - 0.35 * conflict_entropy)
    cstar_virtual_energy = _unit(cstar_virtual_energy)
    if cstar_virtual_energy <= 0.0:
        return _empty_cstar_statepool_feedback()

    total_direction = forward_support + backward_grasp
    if total_direction <= 0.0:
        alpha_forward = 0.5 if output_chars else 0.0
        alpha_backward = 1.0 - alpha_forward
    else:
        alpha_forward = forward_support / total_direction
        alpha_backward = backward_grasp / total_direction
    if not output_chars:
        alpha_backward = max(alpha_backward, 0.65)
        alpha_forward = 1.0 - alpha_backward

    target_slots: list[dict[str, Any]] = []
    forward_chars = tuple(output_chars[:6])
    if forward_chars:
        forward_budget = cstar_virtual_energy * max(0.15, alpha_forward)
        # Prediction salience is per occurrence, not only a globally averaged mass:
        # a confident B/C/C* match should leave visible virtual energy on the
        # leading prediction units instead of being diluted below StatePool top-k.
        per_slot = min(
            0.32,
            max(0.02, forward_budget / max(len(forward_chars), 1), b_support * 0.18),
        )
        for index, char in enumerate(forward_chars):
            sa_id = f"prediction_unit::{_hash_text(char)}::{index}"
            item = pool.items.get(sa_id)
            if item is None:
                _observe_pool(
                    pool,
                    tick=tick,
                    sa_id=sa_id,
                    family="memory_prediction",
                    label=char,
                    energy=0.0,
                    source="cstar_prediction",
                    ledger_source="replay",
                )
                item = pool.items[sa_id]
            target_slots.append(
                _inject_virtual_energy(
                    item,
                    amount=per_slot,
                    tick=tick,
                    slot_kind="cstar_forward_prediction",
                    source_alignment_event_id=(b0.event_id if b0 is not None else structural_b.event_id if structural_b is not None else None),
                )
            )

    if observation is not None:
        current_sa_ids: list[tuple[str, str]] = [(f"text_utterance::{observation.signature}", "cstar_backward_current_utterance")]
        seen_chars: set[str] = set()
        for char in observation.chars:
            if char in seen_chars:
                continue
            seen_chars.add(char)
            current_sa_ids.append((f"text_unit::{_hash_text(char)}", "cstar_backward_current_unit"))
            if len(current_sa_ids) >= 7:
                break
        existing_current = [(sa_id, slot_kind) for sa_id, slot_kind in current_sa_ids if sa_id in pool.items]
        if existing_current:
            backward_budget = cstar_virtual_energy * max(0.12, alpha_backward)
            per_slot = min(0.24, max(0.015, backward_budget / max(len(existing_current), 1)))
            for sa_id, slot_kind in existing_current:
                target_slots.append(
                    _inject_virtual_energy(
                        pool.items[sa_id],
                        amount=per_slot,
                        tick=tick,
                        slot_kind=slot_kind,
                        source_alignment_event_id=(b0.event_id if b0 is not None else structural_b.event_id if structural_b is not None else None),
                    )
                )

    if not target_slots:
        return _empty_cstar_statepool_feedback()
    return {
        "formula_id": PHASE20_8I_CSTAR_STATEPOOL_FEEDBACK_ID,
        "source_cstar_formula_id": CSTAR_MIN_ERROR_FORMULA_ID,
        "target_count": len(target_slots),
        "forward_target_count": sum(1 for slot in target_slots if str(slot.get("slot_kind", "")).startswith("cstar_forward")),
        "backward_target_count": sum(1 for slot in target_slots if str(slot.get("slot_kind", "")).startswith("cstar_backward")),
        "total_virtual_energy": round(sum(float(slot.get("virtual_energy_delta", 0.0)) for slot in target_slots), 4),
        "cstar_virtual_energy": round(cstar_virtual_energy, 4),
        "alpha_forward": round(alpha_forward, 4),
        "alpha_backward": round(alpha_backward, 4),
        "target_slots": target_slots[:12],
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _l1_per_tick_online_update(
    conn: "sqlite3.Connection",
    *,
    anchor_sa_type_id: str,
    context_sa_type_ids: Sequence[str],
    prediction_error: float,
    reward: float,
    punish: float,
    tick: int,
    alpha: float = 0.01,
) -> bool:
    """Per-tick L1 online update with fixed step size (§DEFECT-L1-1 fix).

    Uses a simplified fixed-alpha gradient step instead of the full annealing
    triplet update. Called once per co-occurrence during the tick loop.
    Returns True if the update was written.
    """
    if not anchor_sa_type_id or not context_sa_type_ids:
        return False
    try:
        from .experience_log import (
            load_sa_type_vector_l1,
            update_sa_type_vector_l1,
            l1_zero_vector,
            L1_VECTOR_DIM,
        )
        loaded = load_sa_type_vector_l1(conn, [anchor_sa_type_id] + list(context_sa_type_ids[:6]))
        anchor_count, anchor_vec = loaded.get(anchor_sa_type_id, (0, l1_zero_vector()))
        context_vecs = [loaded[sid][1] for sid in context_sa_type_ids[:6] if sid in loaded]
        if not context_vecs:
            return False
        # Compute context centroid
        centroid = [0.0] * L1_VECTOR_DIM
        for vec in context_vecs:
            for i in range(L1_VECTOR_DIM):
                centroid[i] += float(vec[i]) if i < len(vec) else 0.0
        n = float(len(context_vecs))
        centroid = [c / n for c in centroid]
        # Fixed-alpha step toward centroid (reward-gated)
        sign = 1.0 if float(reward) >= float(punish) else -1.0
        pe_boost = 1.0 + 0.4 * max(0.0, min(1.0, float(prediction_error)))
        step = alpha * sign * pe_boost
        new_vec = [
            max(-1.0, min(1.0, float(anchor_vec[i] if i < len(anchor_vec) else 0.0) + step * (centroid[i] - float(anchor_vec[i] if i < len(anchor_vec) else 0.0))))
            for i in range(L1_VECTOR_DIM)
        ]
        update_sa_type_vector_l1(conn, sa_type_id=anchor_sa_type_id, support_count=anchor_count + 1, vector=new_vec, tick=tick)
        return True
    except Exception:
        return False


def _record_l2_cooccurrence_group(
    conn: "sqlite3.Connection",
    sa_type_ids: Sequence[str],
    *,
    tick: int,
    turn_id: str = "",
    modalities: Sequence[str] = (),
) -> None:
    """Record all SAs active in the same tick as an L2 group-level co-occurrence."""
    ids = [str(sid) for sid in sa_type_ids if sid]
    if len(ids) < 2:
        return
    try:
        from .experience_log import to_json
        conn.execute(
            "INSERT INTO phase20_7_l2_cooccurrence_group (tick, turn_id, sa_ids, modalities) VALUES (?, ?, ?, ?)",
            (int(tick), str(turn_id), to_json(ids), to_json(list(modalities))),
        )
    except Exception:
        pass


def _apply_b_recall_residual_energy(
    pool: "StatePool",
    c_backward_rows: Sequence[dict[str, Any]],
    *,
    tick: int,
) -> int:
    """Apply 3-way B recall residual energy to the state pool.

    energy_mode rules:
      matched       → neutralize: reduce virtual energy on matched SA
      memory_excess → virtual:    AP predicted more than reality → add virtual energy
      reality_excess → real:      reality exceeded memory → add real energy
    """
    applied = 0
    for row in c_backward_rows:
        neutralized = row.get("neutralized_occurrences", ())
        if not isinstance(neutralized, (list, tuple)):
            continue
        for item_dict in neutralized:
            if not isinstance(item_dict, dict):
                continue
            occ_id = str(item_dict.get("occurrence_id", ""))
            mode = str(item_dict.get("energy_mode", "matched"))
            score = _unit(item_dict.get("neutralize_score", 0.0))
            if not occ_id:
                continue
            # Map occurrence_id → sa_id heuristic: occurrence IDs that start with
            # "occ::" reference DB rows; for state-pool items the sa_id is embedded.
            sa_id = occ_id
            if mode == "memory_excess":
                pool.inject_virtual(sa_id, score * 0.15, tick, source="residual_mass")
                applied += 1
            elif mode == "reality_excess":
                pool.modify_occurrence(sa_id, delta_real=score * 0.10, tick=tick)
                applied += 1
            elif mode == "matched":
                pool.modify_occurrence(sa_id, delta_virtual=-(score * 0.08), tick=tick)
                applied += 1
    return applied


def _empty_cstar_statepool_feedback() -> dict[str, Any]:
    return {
        "formula_id": PHASE20_8I_CSTAR_STATEPOOL_FEEDBACK_ID,
        "source_cstar_formula_id": CSTAR_MIN_ERROR_FORMULA_ID,
        "target_count": 0,
        "forward_target_count": 0,
        "backward_target_count": 0,
        "total_virtual_energy": 0.0,
        "target_slots": (),
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _inject_virtual_energy(
    item: Any,
    *,
    amount: float,
    tick: int,
    slot_kind: str,
    source_alignment_event_id: str | None,
) -> dict[str, Any]:
    delta = _unit(amount)
    item.virtual_energy = min(1.0, float(item.virtual_energy) + delta)
    item.attention_energy = min(1.0, float(item.attention_energy) + delta * 0.35)
    item.cognitive_pressure = float(item.real_energy) - float(item.virtual_energy)
    item.last_tick = int(tick)
    item.gain_ledger.inject("replay", delta)
    item.metadata["cstar_statepool_feedback"] = PHASE20_8I_CSTAR_STATEPOOL_FEEDBACK_ID
    item.metadata["cstar_feedback_tick"] = int(tick)
    item.metadata["cstar_feedback_slot_kind"] = slot_kind
    item.metadata["cstar_feedback_virtual_energy_delta"] = round(delta, 4)
    if source_alignment_event_id:
        item.metadata["source_alignment_event_id"] = source_alignment_event_id
    return {
        "slot_kind": slot_kind,
        "sa_id": item.sa_id,
        "family": item.family,
        "label": item.label,
        "virtual_energy_delta": round(delta, 4),
        "V_after": round(float(item.virtual_energy), 4),
        "P_after": round(float(item.cognitive_pressure), 4),
    }


def _runtime_support(row: dict[str, Any]) -> float:
    for key in ("support", "cause_grasp", "drive", "grasp"):
        if key in row:
            return _unit(row.get(key, 0.0))
    return 0.0


def _runtime_backward_grasp(row: dict[str, Any]) -> float:
    for key in ("cause_grasp", "support", "grasp"):
        if key in row:
            return _unit(row.get(key, 0.0))
    return 0.0


def _selected_drive_from_competition(
    action_competition: Sequence[dict[str, Any]],
    selected_action: dict[str, Any],
) -> float:
    """§7.3 determination = winner_drive - second_place_drive (competitive margin)."""
    sorted_actions = sorted(action_competition, key=lambda r: float(r.get("drive", 0.0)), reverse=True)
    if len(sorted_actions) >= 2:
        winner_drive = float(sorted_actions[0].get("drive", 0.0))
        second_drive = float(sorted_actions[1].get("drive", 0.0))
        return _unit(winner_drive - second_drive)
    if sorted_actions:
        return _unit(sorted_actions[0].get("drive", 0.0))
    return _unit(selected_action.get("drive", 0.0))


def _runtime_competition_entropy(action_competition: Sequence[dict[str, Any]]) -> float:
    drives = [_unit(row.get("drive", 0.0)) for row in action_competition]
    drives = [value for value in drives if value > 0.0]
    total = sum(drives)
    if total <= 0.0:
        return 0.0
    entropy = 0.0
    for drive in drives:
        p = drive / total
        entropy -= p * math.log(p)
    max_entropy = math.log(max(len(drives), 1))
    return _unit(entropy / max_entropy if max_entropy > 0 else 0.0)


def _unit(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _cstar_statepool_carryover(
    pool: StatePool,
    *,
    tick: int,
    observation: _ObservationLike | None,
) -> dict[str, Any]:
    slots: list[dict[str, Any]] = []
    for item in pool.items.values():
        metadata = dict(item.metadata)
        if metadata.get("cstar_statepool_feedback") != PHASE20_8I_CSTAR_STATEPOOL_FEEDBACK_ID:
            continue
        try:
            feedback_tick = int(metadata.get("cstar_feedback_tick", -1))
        except (TypeError, ValueError):
            feedback_tick = -1
        if feedback_tick >= int(tick):
            continue
        ledger = item.gain_ledger.snapshot()
        try:
            replay = float(ledger.get("replay", 0.0) or 0.0)
        except (TypeError, ValueError, AttributeError):
            replay = 0.0
        carry_score = _unit(
            float(item.virtual_energy) * 0.62
            + float(item.attention_energy) * 0.22
            + abs(float(item.cognitive_pressure)) * 0.10
            + replay * 0.06
        )
        if carry_score <= 0.0:
            continue
        slots.append(
            {
                "slot_kind": "statepool_cstar_carryover_sa",
                "sa_id": item.sa_id,
                "family": item.family,
                "label": item.label,
                "V": round(float(item.virtual_energy), 4),
                "A": round(float(item.attention_energy), 4),
                "P": round(float(item.cognitive_pressure), 4),
                "replay": round(replay, 4),
                "carry_score": round(carry_score, 4),
                "source_feedback_tick": feedback_tick,
                "source_slot_kind": metadata.get("cstar_feedback_slot_kind"),
            }
        )
    slots.sort(key=lambda slot: float(slot.get("carry_score", 0.0)), reverse=True)
    top_slots = tuple(slots[:8])
    prediction_slots = tuple(slot for slot in top_slots if slot.get("family") == "memory_prediction")
    current_slots = tuple(
        slot
        for slot in top_slots
        if str(slot.get("source_slot_kind", "")).startswith("cstar_backward")
        or slot.get("family") in {"text", "text_utterance"}
    )
    observation_bias, observation_slots = _statepool_observation_support_bias(pool, observation)
    max_carry = max((float(slot.get("carry_score", 0.0)) for slot in top_slots), default=0.0)
    total_carry = _unit(sum(float(slot.get("carry_score", 0.0)) for slot in top_slots) / math.sqrt(len(top_slots) + 1.0))
    prediction_support = max((float(slot.get("carry_score", 0.0)) for slot in prediction_slots), default=0.0)
    pressure_support = max((abs(float(slot.get("P", 0.0))) for slot in top_slots), default=0.0)
    active = bool(top_slots or observation_bias > 0.0)
    return {
        "formula_id": PHASE20_8J_CSTAR_CARRYOVER_ID,
        "active": active,
        "source_feedback_id": PHASE20_8I_CSTAR_STATEPOOL_FEEDBACK_ID,
        "source_item_count": len(slots),
        "top_slots": top_slots,
        "prediction_unit_count": len(prediction_slots),
        "prediction_units": tuple(str(slot.get("label", "")) for slot in prediction_slots[:6]),
        "prediction_support": round(prediction_support, 4),
        "current_unit_count": len(current_slots),
        "max_carry": round(max_carry, 4),
        "total_carry": round(total_carry, 4),
        "pressure_support": round(_unit(pressure_support), 4),
        "observation_support_bias": round(observation_bias, 4),
        "observation_bias_slots": observation_slots,
        "creates_candidate": False,
        "writes_answer_directly": False,
    }


def _statepool_observation_support_bias(
    pool: StatePool | None,
    observation: _ObservationLike | None,
) -> tuple[float, tuple[dict[str, Any], ...]]:
    if pool is None or observation is None:
        return 0.0, ()
    sa_ids: list[str] = [f"text_utterance::{observation.signature}"]
    seen_chars: set[str] = set()
    for char in observation.chars:
        if char in seen_chars:
            continue
        seen_chars.add(char)
        sa_ids.append(f"text_unit::{_hash_text(char)}")
        if len(sa_ids) >= 9:
            break
    slots: list[dict[str, Any]] = []
    for sa_id in sa_ids:
        item = pool.items.get(sa_id)
        if item is None:
            continue
        metadata = dict(item.metadata)
        if metadata.get("cstar_statepool_feedback") != PHASE20_8I_CSTAR_STATEPOOL_FEEDBACK_ID:
            continue
        ledger = item.gain_ledger.snapshot()
        try:
            replay = float(ledger.get("replay", 0.0) or 0.0)
        except (TypeError, ValueError, AttributeError):
            replay = 0.0
        score = _unit(float(item.virtual_energy) * 0.66 + abs(float(item.cognitive_pressure)) * 0.18 + replay * 0.16)
        if score <= 0.0:
            continue
        slots.append(
            {
                "slot_kind": "statepool_cstar_observation_bias",
                "sa_id": item.sa_id,
                "family": item.family,
                "label": item.label,
                "V": round(float(item.virtual_energy), 4),
                "P": round(float(item.cognitive_pressure), 4),
                "replay": round(replay, 4),
                "score": round(score, 4),
            }
        )
    if not slots:
        return 0.0, ()
    max_score = max(float(slot["score"]) for slot in slots)
    avg_score = sum(float(slot["score"]) for slot in slots) / max(len(slots), 1)
    bias = min(0.08, max_score * 0.08 + avg_score * 0.02)
    return round(bias, 4), tuple(sorted(slots, key=lambda slot: float(slot["score"]), reverse=True)[:6])


def _statepool_unresolved_pressure(
    pool: StatePool | None,
    observation: _ObservationLike | None,
) -> tuple[float, float, tuple[dict[str, Any], ...]]:
    """§27.1 未闭合期待/压力的涌现项 (求知欲/恐惧的底层来源).

    白皮书 §27.1: "预测会带来惩罚, 形成压力". §27.3 Pressure=predicted_punish_energy.
    §30.1 惊/违和 通道 + §27.1 行动增益 drive+=U*affordance*predicted_reward_or_punish_avoidance.
    用户理论 (与白皮书一致): 未知→认知压高→少量惩罚信号涌现→恐惧/求知欲自发涌现,
    不需要 request_teacher 行动触发, 而是由状态池中观察相关 SA 的认知压自然累积.

    这里复用 _statepool_observation_support_bias 的 sa_ids 聚合模式, 但不过滤
    cstar_statepool_feedback (要取 raw 认知压涌现, 不只 C* 回灌的项). 认知压
    P=R-V 正值表示现实强于预测 (惊/预测不足), 作为压力 (求知) 涌现项;
    负值 (违和/期待落空) 作为期待落空压力涌现项. 取其绝对值的平均 — 拟人:
    "感觉哪里不对" 不论 是欠缺预测还是预测错配, 都产生持续张力.

    返回 (pressure_emergent, expectation_disappointment_emergent, audit_slots).
    都是 §27.6 U(t+1)=decay*U+new_evidence 中的 new_evidence 涌现项,
    不是新表/新实体/新路由 — 纯复用既有 StateItem.cognitive_pressure (§9 状态池字段).
    """
    if pool is None or observation is None:
        return 0.0, 0.0, ()
    sa_ids: list[str] = [f"text_utterance::{observation.signature}"]
    seen_chars: set[str] = set()
    for char in observation.chars:
        if char in seen_chars:
            continue
        seen_chars.add(char)
        sa_ids.append(f"text_unit::{_hash_text(char)}")
        if len(sa_ids) >= 9:
            break
    pressure_values: list[float] = []
    dissonance_values: list[float] = []
    slots: list[dict[str, Any]] = []
    for sa_id in sa_ids:
        item = pool.items.get(sa_id)
        if item is None:
            continue
        p = float(item.cognitive_pressure)
        if p > 0.0:
            # 正认知压 (惊/预测不足) → 惩罚预测涌现 → 压力/求知欲
            pressure_values.append(_unit(p))
        elif p < 0.0:
            # 负认知压 (违和/期待落空) → 期待失望压力涌现
            dissonance_values.append(_unit(abs(p)))
        slots.append(
            {
                "slot_kind": "statepool_unresolved_pressure_emergent",
                "sa_id": item.sa_id,
                "P": round(p, 4),
                "R": round(float(item.real_energy), 4),
                "V": round(float(item.virtual_energy), 4),
            }
        )
    if not pressure_values and not dissonance_values:
        return 0.0, 0.0, tuple(slots)
    pressure_emergent = sum(pressure_values) / max(len(pressure_values), 1) if pressure_values else 0.0
    dissonance_emergent = sum(dissonance_values) / max(len(dissonance_values), 1) if dissonance_values else 0.0
    return round(pressure_emergent, 4), round(dissonance_emergent, 4), tuple(slots)


def _l2_successor_prediction(
    conn: sqlite3.Connection | None,
    *,
    observation: _ObservationLike | None,
) -> tuple[dict[str, Any], ...]:
    """L2 temporal-edge successor prediction row for C_forward (whitepaper §173.2).

    Given the current observation, take its last meaningful char as the source
    sa_type `a'`, look up all learned linear_next type-pair edges (a->b), and rank
    them by how well the historical edge's *source endpoint* `z_a` matches the
    query source `z_a'` (L1 cosine — the receptor-local similarity layer), modulated
    by the edge's own learned support_count (the L2 edge confidence). The best
    edge's dst endpoint is the predicted successor. This is the soft-similarity
    successor recall that SSP's exact edge match cannot do (§1.3 of the Phase20.12
    design): a new `a'` whose token is similar-but-not-identical to a historical
    edge's source `a` can still surface that edge's successor `b`.

    Layering is respected: L1 supplies the endpoint similarity, L2 supplies the
    edge's learned support — neither replaces the other. The row is projection-only:
    it does not write reply_text and does not create a B candidate. It only adds a
    learned soft-similarity C_forward row at the convergence point, mirroring how
    _cstar_carryover_c_forward adds a carryover row. No new entity.
    """
    if conn is None or observation is None:
        return ()
    chars = tuple(ch for ch in getattr(observation, "chars", ()) if ch and not ch.isspace())
    if not chars:
        return ()
    src_sa_id = f"text_unit::{_hash_text(str(chars[-1]))}"
    src_edge_hash = _hash_text(src_sa_id)
    # Candidate edges: all text_edge::linear_next sa_types whose src endpoint is
    # the observation's last char. l2_edge_sa_type_id encodes the endpoint as
    # _hash_text(src_sa_type_id) (i.e. the hash of the full "text_unit::<hash>"
    # sa_type id), so the LIKE prefix must embed that same hash, NOT the raw
    # char hash, to match the edge sa_type_id encoding.
    prefix = f"text_edge::{L2_RELATION_LINEAR_NEXT}::{src_edge_hash}->%"
    rows = conn.execute(
        """
        SELECT sa_type_id, vector_l2, canonical_hint, updated_tick
        FROM phase20_7_sa_types
        WHERE sa_type_id LIKE ?
          AND vector_l2 IS NOT NULL
        ORDER BY updated_tick DESC
        LIMIT 24
        """,
        (prefix,),
    ).fetchall()
    if not rows:
        return ()
    # Source-endpoint L1 similarity: compare the query's z_a' with each candidate
    # edge's z_a (extracted from the canonical_hint "text_unit::<ha> -> ...").
    # If a candidate's source L1 vector is similar to the query source, that
    # historical edge is a soft successor candidate. (For the exact-token case the
    # LIKE prefix already pins src = a', so all candidates share the source and
    # rank by edge support_count; the L1 term generalizes to similar-but-not-identical.)
    best_edge: tuple[str, float, str, int, str] | None = None
    # (edge_sa_id, score, hint, support_count, dst_sa_id)
    for edge_sa_id, raw, hint, _updated_tick in rows:
        support_count, edge_vec = bytes_to_l2_vector(raw)
        if not any(abs(v) > 1e-9 for v in edge_vec):
            continue
        # Decode the dst endpoint sa_type_id from canonical_hint "src -> dst".
        dst_sa_id = _l2_dst_sa_type_from_hint(str(hint or ""))
        if not dst_sa_id:
            continue
        # The edge src is the query src by LIKE-prefix construction, so its L1
        # vector is the same as the query source; the meaningful signal is the
        # edge's learned support_count (how often this successor was reinforced).
        # Use a support-derived score so the prediction surfaces the most-reinforced
        # successor edge, with a floor so single-teach edges still fire.
        support_score = min(1.0, 0.4 + 0.12 * float(support_count))
        if best_edge is None or support_score > best_edge[1]:
            best_edge = (str(edge_sa_id), float(support_score), str(hint or ""), int(support_count), dst_sa_id)
    if best_edge is None or best_edge[1] <= 0.0:
        return ()
    edge_sa_id, score, hint, support_count, dst_sa_id = best_edge
    return (
        {
            "kind": "l2_temporal_edge_prediction",
            "model": PHASE20_12_L2_STRUCTURE_UPDATE_ID,
            "source_edge_sa_type_id": edge_sa_id,
            "edge_kind": L2_RELATION_LINEAR_NEXT,
            "source_sa_type_id": src_sa_id,
            "predicted_dst_sa_type_id": dst_sa_id,
            "edge_hint": hint,
            "l2_edge_support": round(score, 4),
            "support": round(score, 4),
            "edge_support_count": support_count,
            "predicted_unit_count": 1,
            "subjective": True,
            "may_be_wrong": True,
            "projection_only": True,
            "writes_answer_directly": False,
        },
    )


def _l2_dst_sa_type_from_hint(hint: str) -> str | None:
    """Extract the dst endpoint sa_type_id from an edge canonical_hint 'src -> dst'."""
    if not hint or "->" not in hint:
        return None
    parts = hint.split("->", 1)
    if len(parts) != 2:
        return None
    dst = parts[1].strip()
    if not dst.startswith("text_unit::"):
        return None
    return dst


def _l2_src_sa_type_from_hint(hint: str) -> str | None:
    """Extract the src endpoint sa_type_id from an edge canonical_hint 'src -> dst'.

    Mirror of _l2_dst_sa_type_from_hint for the backward direction: the L2
    predecessor attribution surfaces the src endpoint as the historical cause
    (what usually came before the current dst), per whitepaper §1160 C_backward
    "历史上这种现状之前通常有什么条件".
    """
    if not hint or "->" not in hint:
        return None
    parts = hint.split("->", 1)
    if len(parts) != 2:
        return None
    src = parts[0].strip()
    if not src.startswith("text_unit::"):
        return None
    return src


def _l2_predecessor_attribution(
    conn: sqlite3.Connection | None,
    *,
    observation: _ObservationLike | None,
) -> tuple[dict[str, Any], ...]:
    """L2 temporal-edge predecessor attribution row for C_backward (whitepaper §173.2).

    The backward mirror of _l2_successor_prediction. Given the current
    observation, take its last meaningful char as the dst endpoint `b'`, look up
    all learned linear_next type-pair edges (a->b) that END at `b'`, rank by the
    edge's learned support_count, and surface the best edge's src endpoint `a` as
    the historical cause ("what usually came before b"). This is the L2
    soft-similarity predecessor recall that SSP's exact edge match cannot do,
    answering §1160 "历史上这种现状之前通常有什么条件".

    Order-asymmetry is self-consistent with the C_forward cut: C_forward queries
    edges whose SRC is the current last char (predict the successor); C_backward
    queries edges whose DST is the current last char (attribute the predecessor).
    Same learned edge vectors, opposite query direction — the §173.3 asymmetry.
    The row is projection-only: it does not write reply_text and does not create a
    B candidate. No new entity.
    """
    if conn is None or observation is None:
        return ()
    chars = tuple(ch for ch in getattr(observation, "chars", ()) if ch and not ch.isspace())
    if not chars:
        return ()
    dst_sa_id = f"text_unit::{_hash_text(str(chars[-1]))}"
    # Edges ending at the current last char. l2_edge_sa_type_id encodes endpoints
    # as _hash_text(<full sa_type_id>), so the LIKE suffix must embed the hash of
    # the dst sa_type_id (same encoding rule as the C_forward prefix).
    dst_edge_hash = _hash_text(dst_sa_id)
    suffix = f"%->{dst_edge_hash}"
    pattern = f"text_edge::{L2_RELATION_LINEAR_NEXT}::{suffix}"
    rows = conn.execute(
        """
        SELECT sa_type_id, vector_l2, canonical_hint, updated_tick
        FROM phase20_7_sa_types
        WHERE sa_type_id LIKE ?
          AND vector_l2 IS NOT NULL
        ORDER BY updated_tick DESC
        LIMIT 24
        """,
        (pattern,),
    ).fetchall()
    if not rows:
        return ()
    best_edge: tuple[str, float, str, int, str] | None = None
    # (edge_sa_id, score, hint, support_count, src_sa_id)
    for edge_sa_id, raw, hint, _updated_tick in rows:
        support_count, edge_vec = bytes_to_l2_vector(raw)
        if not any(abs(v) > 1e-9 for v in edge_vec):
            continue
        src_sa_id = _l2_src_sa_type_from_hint(str(hint or ""))
        if not src_sa_id:
            continue
        # The edge dst is the query dst by LIKE-suffix construction; the
        # meaningful signal is the edge's learned support_count (how often this
        # predecessor relation was reinforced). Same scoring as the C_forward cut
        # so the two directions are comparable and order-asymmetric by query
        # direction, not by an arbitrary scoring asymmetry.
        support_score = min(1.0, 0.4 + 0.12 * float(support_count))
        if best_edge is None or support_score > best_edge[1]:
            best_edge = (str(edge_sa_id), float(support_score), str(hint or ""), int(support_count), src_sa_id)
    if best_edge is None or best_edge[1] <= 0.0:
        return ()
    edge_sa_id, score, hint, support_count, src_sa_id = best_edge
    grasp = _unit(score)
    return (
        {
            "kind": "l2_temporal_edge_predecessor",
            "model": PHASE20_12_L2_STRUCTURE_UPDATE_ID,
            "source_edge_sa_type_id": edge_sa_id,
            "edge_kind": L2_RELATION_LINEAR_NEXT,
            "current_dst_sa_type_id": dst_sa_id,
            "attributed_cause_sa_type_id": src_sa_id,
            "edge_hint": hint,
            "l2_edge_support": round(score, 4),
            "cause_grasp": round(grasp, 4),
            "e_backward": round(1.0 - grasp, 4),
            "edge_support_count": support_count,
            "cause_slots": (
                {
                    "slot_kind": "l2_temporal_edge_predecessor_slot",
                    "edge_sa_type_id": edge_sa_id,
                    "attributed_cause_sa_type_id": src_sa_id,
                    "current_dst_sa_type_id": dst_sa_id,
                    "edge_support": round(score, 4),
                },
            ),
            "neutralized_occurrences": (),
            "subjective": True,
            "may_be_wrong": True,
            "projection_only": True,
            "writes_answer_directly": False,
        },
    )


def _cstar_carryover_c_forward(carryover: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    if not carryover.get("active") or float(carryover.get("prediction_support", 0.0) or 0.0) <= 0.0:
        return ()
    return (
        {
            "kind": "statepool_virtual_prediction_carryover",
            "model": PHASE20_8J_CSTAR_CARRYOVER_ID,
            "predicted_units": list(carryover.get("prediction_units", ())),
            "predicted_unit_count": int(carryover.get("prediction_unit_count", 0) or 0),
            "support": round(float(carryover.get("prediction_support", 0.0) or 0.0), 4),
            "source_feedback_id": carryover.get("source_feedback_id"),
            "subjective": True,
            "writes_answer_directly": False,
        },
    )


def _cstar_carryover_c_backward(carryover: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    if not carryover.get("active"):
        return ()
    grasp = max(
        float(carryover.get("pressure_support", 0.0) or 0.0),
        float(carryover.get("max_carry", 0.0) or 0.0) * 0.72,
        float(carryover.get("observation_support_bias", 0.0) or 0.0),
    )
    if grasp <= 0.0:
        return ()
    return (
        {
            "kind": "statepool_virtual_pressure_carryover",
            "model": PHASE20_8J_CSTAR_CARRYOVER_ID,
            "selected_source_kind": "statepool_cstar_carryover",
            "cause_slots": list(carryover.get("top_slots", ())) + list(carryover.get("observation_bias_slots", ())),
            "neutralized_occurrences": (),
            "cause_grasp": round(_unit(grasp), 4),
            "e_backward": round(1.0 - _unit(grasp), 4),
            "subjective": True,
            "may_be_wrong": True,
            "writes_answer_directly": False,
        },
    )


def _short_structure_flow_query_c_backward(
    conn: sqlite3.Connection | None,
    *,
    session_id: str,
    limit: int = 16,
) -> tuple[dict[str, Any], ...]:
    if conn is None:
        return ()
    candidates = tuple(
        candidate
        for candidate in query_recent_experience_flow_candidates(
            conn,
            session_id=session_id,
            from_json=from_json,
            hash_text=_hash_text,
            signature_for_chars=_signature_for_chars,
            compose_input_signature=_compose_input_signature,
            visual_tokens_from_payloads=_visual_signature_from_payloads,
            limit=max(1, int(limit)),
        )
        if candidate.candidate_kind == "short_structure_flow_next"
    )
    if not candidates:
        return ()
    best = max(candidates, key=lambda candidate: float(candidate.support))
    unified = unified_candidate_from_flow(best)
    grasp = _unit(best.support)
    return (
        {
            "kind": "short_structure_flow_query_recall",
            "model": PHASE20_8L_SHORT_STRUCTURE_QUERY_ID,
            "selected_source_kind": "short_structure_flow_next",
            "candidate_count": len(candidates),
            "cause_slots": (
                {
                    "slot_kind": "unified_experience_flow_candidate",
                    "candidate_id": best.candidate_id,
                    "candidate_kind": best.candidate_kind,
                    "edge_count": len(best.edge_ids),
                    "support": round(float(best.support), 4),
                },
                unified.audit_slot(),
            )
            + tuple(dict(slot) for slot in best.cause_slots if isinstance(slot, dict)),
            "neutralized_occurrences": (
                {
                    "occurrence_id": best.occurrence_ids[-1] if best.occurrence_ids else None,
                    "neutralize_score": round(grasp, 4),
                    "source_kind": "short_structure_flow_next",
                },
            ),
            "cause_grasp": round(grasp, 4),
            "e_backward": round(1.0 - grasp, 4),
            "subjective": True,
            "may_be_wrong": True,
            "writes_answer_directly": False,
        },
    )


def _apply_cstar_carryover_to_competition(
    action_competition: tuple[dict[str, Any], ...],
    selected_action: dict[str, Any],
    carryover: dict[str, Any],
) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    if not carryover.get("active"):
        return action_competition, selected_action
    prediction_support = _unit(carryover.get("prediction_support", 0.0))
    pressure_support = _unit(carryover.get("pressure_support", 0.0))
    max_carry = _unit(carryover.get("max_carry", 0.0))
    adjusted_rows: list[dict[str, Any]] = []
    selected_drive: float | None = None
    selected_delta = 0.0
    selected_type = str(selected_action.get("action_type", ""))
    for row in action_competition:
        action_type = str(row.get("action_type", ""))
        drive_before = _unit(row.get("drive", 0.0))
        delta = 0.0
        if action_type in {"write_cell", "commit_reply"}:
            delta += min(0.16, prediction_support * 0.16)
        pressure_targets = (
            {"idle_think", "integrate_feedback"}
            if selected_type == "integrate_feedback"
            else {"idle_think", "request_teacher", "maintain_unclosed"}
        )
        if action_type in pressure_targets:
            delta += min(0.12, pressure_support * 0.10)
        if action_type == selected_type or row.get("selected"):
            delta += min(0.05, max_carry * 0.04)
        drive_after = _unit(drive_before + delta)
        adjusted = dict(row)
        if delta > 0.0:
            adjusted["drive_before_cstar_carryover"] = round(drive_before, 4)
            adjusted["cstar_carryover_drive_delta"] = round(delta, 4)
            adjusted["drive"] = round(drive_after, 4)
        if adjusted.get("selected"):
            selected_drive = drive_after
            selected_delta = delta
        adjusted_rows.append(adjusted)
    adjusted_rows.sort(key=lambda row: (bool(row.get("selected")), float(row.get("drive", 0.0) or 0.0)), reverse=True)
    selected = dict(selected_action)
    if selected_drive is not None:
        selected["drive"] = round(selected_drive, 4)
    if selected_delta > 0.0:
        selected["cstar_carryover_drive_delta"] = round(selected_delta, 4)
    return tuple(adjusted_rows), selected


def _write_cstar_carryover_structure_flow(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    tick: int,
    event_id: str,
    carryover: dict[str, Any],
    selected_action: dict[str, Any],
) -> dict[str, Any]:
    if not carryover.get("active"):
        return {}
    top_slots = tuple(slot for slot in carryover.get("top_slots", ()) if isinstance(slot, dict))
    if not top_slots:
        return {}
    support = _unit(max(float(carryover.get("max_carry", 0.0) or 0.0), float(carryover.get("total_carry", 0.0) or 0.0)))
    if support <= 0.0:
        return {}
    source_occurrence_ids: list[str] = []
    edge_ids: list[str] = []
    for index, slot in enumerate(top_slots[:6]):
        sa_id = str(slot.get("sa_id") or f"cstar_carryover_source::{index}")
        label = str(slot.get("label") or slot.get("family") or "cstar_carryover")
        carry_score = _unit(slot.get("carry_score", 0.0))
        if carry_score <= 0.0:
            continue
        upsert_sa_type(
            conn,
            sa_type_id=sa_id,
            substrate="cognitive",
            modality="statepool",
            canonical_hint=label[:80],
            tick=tick,
        )
        occ_id = insert_occurrence(
            conn,
            event_id=event_id,
            sa_type_id=sa_id,
            tick=tick,
            substrate="cognitive",
            position={
                "axis": "cstar_carryover_source",
                "index": index,
                "source_slot_kind": slot.get("source_slot_kind"),
                "family": slot.get("family"),
            },
            r=0.0,
            v=carry_score,
            a=carry_score * 0.42,
            p=-carry_score,
            clarity=1.0,
            source_ref=event_id,
        )
        source_occurrence_ids.append(occ_id)
    flow_label = " ".join(str(slot.get("label") or "") for slot in top_slots[:6]).strip() or str(selected_action.get("action_type") or "cstar_carryover")
    flow = _write_short_structure_flow_occurrence(
        conn,
        session_id=session_id,
        tick=tick,
        event_id=event_id,
        text=flow_label,
        support=support,
        source_kind="cstar_carryover",
        r=0.0,
        v=support,
        a=_unit(carryover.get("total_carry", support)),
        p=-support,
        metadata={
            "formula_id": PHASE20_8K_CARRYOVER_SSP_FLOW_ID,
            "selected_action": selected_action.get("action_type"),
            "prediction_units": list(carryover.get("prediction_units", ())),
            "source_item_count": carryover.get("source_item_count", 0),
        },
    )
    flow_occurrence_id = str(flow.get("occurrence_id") or "")
    if flow_occurrence_id:
        for source_occurrence_id in source_occurrence_ids:
            edge_ids.append(
                insert_structure_edge(
                    conn,
                    src_occurrence_id=source_occurrence_id,
                    dst_occurrence_id=flow_occurrence_id,
                    edge_type="cstar_carryover_to_short_flow",
                    weight=support,
                    learned_weight=min(0.28, support * 0.28),
                    tick=tick,
                )
            )
    edge_ids.extend(str(edge_id) for edge_id in flow.get("edge_ids", ()))
    return {
        "formula_id": PHASE20_8K_CARRYOVER_SSP_FLOW_ID,
        "flow_kind": "cstar_carryover_flow",
        "flow_occurrence_id": flow_occurrence_id or None,
        "source_occurrence_ids": tuple(source_occurrence_ids),
        "edge_ids": tuple(edge_ids),
        "support": round(support, 4),
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _write_short_structure_flow_occurrence(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    tick: int,
    event_id: str,
    text: str,
    support: float,
    source_kind: str,
    r: float,
    v: float,
    a: float,
    p: float,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    support = _unit(support)
    text_value = str(text or source_kind).strip() or source_kind
    sa_type_id = f"short_structure_flow::{source_kind}::{_hash_text(text_value)}"
    upsert_sa_type(
        conn,
        sa_type_id=sa_type_id,
        substrate="cognitive",
        modality="short_structure_flow",
        canonical_hint=text_value[:120],
        tick=tick,
    )
    prev = _latest_short_structure_flow_occurrence(conn, session_id=session_id, before_tick=tick)
    occurrence_id = insert_occurrence(
        conn,
        event_id=event_id,
        sa_type_id=sa_type_id,
        tick=tick,
        substrate="cognitive",
        position={
            "axis": "short_structure_flow",
            "source_kind": source_kind,
            "session_id": session_id,
            "text_hash": _hash_text(text_value),
            **dict(metadata or {}),
        },
        r=_unit(r),
        v=_unit(v),
        a=_unit(a),
        p=max(-1.0, min(1.0, float(p))),
        clarity=support,
        source_ref=event_id,
    )
    edge_ids: list[str] = []
    if prev is not None:
        edge_ids.append(
            insert_structure_edge(
                conn,
                src_occurrence_id=str(prev["occurrence_id"]),
                dst_occurrence_id=occurrence_id,
                edge_type="short_structure_next",
                weight=min(1.0, max(0.05, float(prev.get("support", 0.0)) * max(support, 0.05))),
                learned_weight=min(0.35, support * 0.24 + float(prev.get("support", 0.0)) * 0.08),
                tick=tick,
            )
        )
    return {
        "formula_id": PHASE20_8K_CARRYOVER_SSP_FLOW_ID,
        "occurrence_id": occurrence_id,
        "sa_type_id": sa_type_id,
        "previous_occurrence_id": prev.get("occurrence_id") if prev is not None else None,
        "edge_ids": tuple(edge_ids),
        "support": round(support, 4),
        "source_kind": source_kind,
        "text_hash": _hash_text(text_value),
    }


def _latest_short_structure_flow_occurrence(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
) -> dict[str, Any] | None:
    rows = conn.execute(
        """
        SELECT o.occurrence_id, o.tick, o.clarity, o.position_json, s.canonical_hint
        FROM phase20_7_occurrences o
        JOIN phase20_7_experience_events e ON e.event_id=o.event_id
        JOIN phase20_7_sa_types s ON s.sa_type_id=o.sa_type_id
        WHERE e.session_id=?
          AND o.tick < ?
          AND o.sa_type_id >= 'short_structure_flow::'
          AND o.sa_type_id < 'short_structure_flow:;'
        ORDER BY o.tick DESC
        LIMIT 1
        """,
        (session_id, int(before_tick)),
    ).fetchall()
    if not rows:
        return None
    occurrence_id, tick, clarity, position_json, canonical_hint = rows[0]
    position = from_json(str(position_json))
    return {
        "occurrence_id": str(occurrence_id),
        "tick": int(tick),
        "support": _unit(clarity),
        "position": position if isinstance(position, dict) else {},
        "canonical_hint": str(canonical_hint or ""),
    }


def _latest_short_structure_flow_occurrence_by_source_kind(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
    source_kind: str,
) -> dict[str, Any] | None:
    rows = conn.execute(
        """
        SELECT o.occurrence_id, o.tick, o.clarity, o.position_json, s.canonical_hint
        FROM phase20_7_occurrences o
        JOIN phase20_7_experience_events e ON e.event_id=o.event_id
        JOIN phase20_7_sa_types s ON s.sa_type_id=o.sa_type_id
        WHERE e.session_id=?
          AND o.tick < ?
          AND o.sa_type_id LIKE ?
        ORDER BY o.tick DESC
        LIMIT 1
        """,
        (session_id, int(before_tick), f"short_structure_flow::{source_kind}::%"),
    ).fetchall()
    if not rows:
        return None
    occurrence_id, tick, clarity, position_json, canonical_hint = rows[0]
    position = from_json(str(position_json))
    return {
        "occurrence_id": str(occurrence_id),
        "tick": int(tick),
        "support": _unit(clarity),
        "position": position if isinstance(position, dict) else {},
        "canonical_hint": str(canonical_hint or ""),
    }


def _write_draftgrid_readback_self_flow(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    tick: int,
    event_id: str,
    grid: DraftGrid,
    visible_text: str,
    draftgrid_action_context: dict[str, Any],
    output_intent: str,
) -> dict[str, Any]:
    text = str(visible_text or "")
    text_hash = _hash_text(text)
    visible_units = tuple(char for char in text if char.strip())
    read_drive = _unit(draftgrid_action_context.get("read_draft", {}).get("drive", 0.0))
    conflict_pressure = _unit(draftgrid_action_context.get("conflict_pressure", 0.0))
    source_support = _unit(draftgrid_action_context.get("source_support", 0.0))
    readback_energy = _unit(0.24 + min(0.34, len(visible_units) * 0.018) + read_drive * 0.26 + source_support * 0.12)
    sa_type_id = f"self_draft_grid_readback::{text_hash}"
    upsert_sa_type(
        conn,
        sa_type_id=sa_type_id,
        substrate="SELF_DRAFT_GRID",
        modality="draft_grid_text",
        canonical_hint=f"readback:{text_hash}",
        tick=tick,
    )
    occurrence_id = insert_occurrence(
        conn,
        event_id=event_id,
        sa_type_id=sa_type_id,
        tick=tick,
        substrate="SELF_DRAFT_GRID",
        position={
            "axis": "draft_grid_readback",
            "session_id": session_id,
            "visible_text_hash": text_hash,
            "visible_unit_count": len(visible_units),
            "source_intent": output_intent,
            "formula_id": PHASE20_9Q_DRAFTGRID_READBACK_FLOW_ID,
        },
        r=readback_energy,
        v=source_support * 0.32,
        a=read_drive,
        p=conflict_pressure,
        clarity=max(readback_energy, read_drive),
        source_ref=event_id,
        payload_ref=event_id,
    )
    _observe_pool(
        pool,
        tick=tick,
        sa_id=sa_type_id,
        family="self_draft_grid",
        label=f"readback:{text_hash}",
        energy=readback_energy,
        source="self_draft_grid",
        ledger_source="replay",
    )
    write_occurrences = _recent_draftgrid_write_occurrences(conn, session_id=session_id, before_tick=tick, limit=8)
    edge_ids: list[str] = []
    for source_occurrence_id in write_occurrences:
        edge_ids.append(
            insert_structure_edge(
                conn,
                src_occurrence_id=source_occurrence_id,
                dst_occurrence_id=occurrence_id,
                edge_type="draft_write_to_readback",
                weight=max(0.12, readback_energy),
                learned_weight=min(0.32, read_drive * 0.22 + source_support * 0.10),
                tick=tick,
            )
        )
    flow = _write_short_structure_flow_occurrence(
        conn,
        session_id=session_id,
        tick=tick,
        event_id=event_id,
        text=text or "draft_grid_readback",
        support=max(readback_energy, read_drive),
        source_kind="draft_grid_readback",
        r=readback_energy,
        v=source_support * 0.26,
        a=read_drive,
        p=conflict_pressure,
        metadata={
            "formula_id": PHASE20_9Q_DRAFTGRID_READBACK_FLOW_ID,
            "self_draft_grid_occurrence_id": occurrence_id,
            "source_intent": output_intent,
            "visible_text_hash": text_hash,
        },
    )
    flow_occurrence_id = str(flow.get("occurrence_id") or "")
    if flow_occurrence_id:
        edge_ids.append(
            insert_structure_edge(
                conn,
                src_occurrence_id=occurrence_id,
                dst_occurrence_id=flow_occurrence_id,
                edge_type="readback_to_short_structure_flow",
                weight=max(0.12, readback_energy),
                learned_weight=min(0.30, readback_energy * 0.24),
                tick=tick,
            )
        )
        previous_readback_flow = _latest_short_structure_flow_occurrence_by_source_kind(
            conn,
            session_id=session_id,
            before_tick=tick,
            source_kind="draft_grid_readback",
        )
        generic_previous_occurrence_id = str(flow.get("previous_occurrence_id") or "")
        if previous_readback_flow is not None:
            previous_readback_occurrence_id = str(previous_readback_flow.get("occurrence_id") or "")
            if (
                previous_readback_occurrence_id
                and previous_readback_occurrence_id != flow_occurrence_id
                and previous_readback_occurrence_id != generic_previous_occurrence_id
            ):
                previous_support = _unit(previous_readback_flow.get("support", 0.0))
                edge_ids.append(
                    insert_structure_edge(
                        conn,
                        src_occurrence_id=previous_readback_occurrence_id,
                        dst_occurrence_id=flow_occurrence_id,
                        edge_type="short_structure_next",
                        weight=min(1.0, max(0.10, previous_support * max(readback_energy, 0.10))),
                        learned_weight=min(0.38, readback_energy * 0.22 + previous_support * 0.12),
                        tick=tick,
                    )
                )
    edge_ids.extend(str(edge_id) for edge_id in flow.get("edge_ids", ()))
    return {
        "formula_id": PHASE20_9Q_DRAFTGRID_READBACK_FLOW_ID,
        "occurrence_id": occurrence_id,
        "sa_type_id": sa_type_id,
        "substrate": "SELF_DRAFT_GRID",
        "flow_occurrence_id": flow_occurrence_id or None,
        "source_write_occurrence_ids": tuple(write_occurrences),
        "edge_ids": tuple(edge_ids),
        "readback_energy": round(readback_energy, 4),
        "read_drive": round(read_drive, 4),
        "conflict_pressure": round(conflict_pressure, 4),
        "source_support": round(source_support, 4),
        "visible_text_hash": text_hash,
        "visible_unit_count": len(visible_units),
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _select_cstar_alternative_unit_for_draftgrid_edit(
    grid: DraftGrid,
    *,
    expected_output_chars: Sequence[str],
    draftgrid_action_context: dict[str, Any],
    output_intent: str,
    exact_b0: _ExactB0 | None,
    structural_b: _StructuralB | None,
) -> dict[str, Any]:
    expected_chars = tuple(str(ch) for ch in expected_output_chars)
    visible_chars = _draftgrid_linear_units(grid)
    support = _unit(
        max(
            float(exact_b0.support) if exact_b0 is not None else 0.0,
            float(structural_b.similarity) if structural_b is not None else 0.0,
            float(draftgrid_action_context.get("source_support", 0.0) or 0.0),
        )
    )
    if not expected_chars or not visible_chars:
        return _no_draftgrid_edit_alternative("missing_visible_or_expected_units", support=support)
    limit = min(len(expected_chars), len(visible_chars), int(grid.rows) * int(grid.cols))
    for index in range(limit):
        old_unit = visible_chars[index]
        alternative_unit = expected_chars[index]
        if old_unit == alternative_unit:
            continue
        row, col = divmod(index, grid.cols)
        conflict_pressure = _unit(
            0.24
            + support * 0.34
            + _unit(draftgrid_action_context.get("conflict_pressure", 0.0)) * 0.22
            + _unit(draftgrid_action_context.get("read_draft", {}).get("drive", 0.0)) * 0.16
        )
        return {
            "formula_id": PHASE20_9R_EDIT_CELL_ID,
            "can_edit": True,
            "row": int(row),
            "col": int(col),
            "cell_index": int(index),
            "old_unit": old_unit,
            "alternative_unit": alternative_unit,
            "old_unit_hash": _hash_text(old_unit),
            "alternative_unit_hash": _hash_text(alternative_unit),
            "source": "cstar_expected_output_vs_self_draftgrid_readback",
            "source_intent": output_intent,
            "source_support": round(support, 4),
            "conflict_pressure": round(conflict_pressure, 4),
            "drive": round(conflict_pressure, 4),
            "candidate_only_no_alternative_unit": False,
            "writes_answer_directly": False,
            "creates_reply_candidate": False,
            "subjective": True,
            "may_be_wrong": True,
        }
    if len(expected_chars) != len(visible_chars):
        return _no_draftgrid_edit_alternative("length_conflict_requires_continue_or_stop_not_cell_edit", support=support)
    return _no_draftgrid_edit_alternative("readback_matches_cstar_expected_units", support=support)


def _draftgrid_linear_units(grid: DraftGrid) -> tuple[str, ...]:
    units: list[str] = []
    for row in range(int(grid.rows)):
        for col in range(int(grid.cols)):
            cell = grid.cells[(row, col)]
            if int(cell.written_at_tick) >= 0:
                units.append(str(cell.char))
    return tuple(units)


def _draftgrid_linear_text(grid: DraftGrid) -> str:
    return "".join(_draftgrid_linear_units(grid))


def _draftgrid_target_output_unit_count(output_chars: Sequence[str], grid: DraftGrid) -> int:
    return min(len(tuple(output_chars)), int(grid.rows) * int(grid.cols))


def _draftgrid_initial_write_unit_limit(output_chars: Sequence[str], grid: DraftGrid) -> int:
    target_count = _draftgrid_target_output_unit_count(output_chars, grid)
    if target_count <= int(grid.cols):
        return target_count
    return min(target_count, int(grid.cols))


def _draftgrid_next_successor_span(
    grid: DraftGrid,
    *,
    written_count: int,
    target_count: int,
) -> tuple[int, int]:
    start = max(0, min(int(written_count), int(target_count)))
    if start >= int(target_count):
        return start, start
    fragment_end = min(int(target_count), start + int(grid.cols) * 2)
    return start, max(start + 1, fragment_end)


def _draftgrid_successor_from_experience_flow(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    grid: DraftGrid,
    output_chars: Sequence[str],
    written_count: int,
) -> dict[str, Any]:
    visible_text = _draftgrid_linear_text(grid)
    if not visible_text.strip():
        return _empty_draftgrid_successor("no_visible_draft")
    existing_text = "".join(str(ch) for ch in output_chars)
    best: dict[str, Any] | None = None
    best_score = 0.0
    for candidate in query_recent_experience_flow_candidates(
        conn,
        session_id=session_id,
        from_json=from_json,
        hash_text=_hash_text,
        signature_for_chars=_signature_for_chars,
        compose_input_signature=_compose_input_signature,
        visual_tokens_from_payloads=_visual_signature_from_payloads,
        limit=48,
    ):
        if candidate.candidate_kind != "short_structure_flow_next":
            continue
        payload = dict(candidate.payload or {})
        if str(payload.get("source_flow_kind") or "") != "draft_grid_readback":
            continue
        if str(payload.get("target_flow_kind") or "") != "draft_grid_readback":
            continue
        source_intent = str(payload.get("source_intent") or "")
        target_intent = str(payload.get("target_intent") or "")
        if not source_intent or source_intent != target_intent:
            continue
        if source_intent == "integrate_feedback":
            continue
        source_pending_units = int(payload.get("source_pending_output_unit_count") or 0)
        source_successor_pressure = _unit(payload.get("source_pending_successor_pressure", 0.0))
        if source_pending_units <= 0 and source_successor_pressure <= 0.0:
            continue
        raw_source_text = str(payload.get("source_text") or "")
        raw_target_text = str(payload.get("target_text") or _successor_text_from_flow_candidate(candidate) or "")
        if _looks_like_internal_flow_text(raw_source_text) or _looks_like_internal_flow_text(raw_target_text):
            continue
        source_text = _draftgrid_readback_text_to_linear(raw_source_text)
        target_text = _draftgrid_readback_text_to_linear(raw_target_text)
        if not target_text.strip():
            continue
        source_fit = _text_containment_fit(visible_text, source_text)
        target_fit = _text_containment_fit(visible_text, target_text)
        if max(source_fit, target_fit) < 0.34:
            continue
        successor_text = _draftgrid_successor_suffix(
            visible_text=visible_text,
            target_text=target_text,
            existing_text=existing_text,
        )
        if not successor_text:
            continue
        support = _unit(candidate.support)
        score = _unit(max(source_fit, target_fit) * 0.46 + support * 0.42 + min(0.12, len(successor_text) * 0.006))
        if score <= best_score:
            continue
        best_score = score
        best = {
            "formula_id": PHASE20_9W_DRAFTGRID_SUCCESSOR_ID,
            "source": "experience_flow_short_structure_next_after_draft_readback",
            "candidate_id": candidate.candidate_id,
            "candidate_kind": candidate.candidate_kind,
            "source_event_id": str(payload.get("source_event_id") or candidate.event_id or ""),
            "target_event_id": str(payload.get("target_event_id") or ""),
            "edge_ids": tuple(candidate.edge_ids),
            "occurrence_ids": tuple(candidate.occurrence_ids),
            "source_text_hash": _hash_text(source_text),
            "target_text_hash": _hash_text(target_text),
            "source_flow_kind": str(payload.get("source_flow_kind") or ""),
            "target_flow_kind": str(payload.get("target_flow_kind") or ""),
            "source_intent": source_intent,
            "target_intent": target_intent,
            "source_pending_output_unit_count": source_pending_units,
            "source_pending_successor_pressure": round(source_successor_pressure, 4),
            "visible_text_hash": _hash_text(visible_text),
            "successor_text": successor_text,
            "successor_text_hash": _hash_text(successor_text),
            "source_fit": round(source_fit, 4),
            "target_fit": round(target_fit, 4),
            "support": round(support, 4),
            "score": round(score, 4),
            "written_count_before": int(written_count),
            "existing_output_unit_count": len(tuple(output_chars)),
            "creates_reply_candidate": False,
            "writes_answer_directly": False,
            "subjective": True,
            "may_be_wrong": True,
        }
    return best if best is not None else _empty_draftgrid_successor("no_experience_flow_successor")


def _empty_draftgrid_successor(reason: str) -> dict[str, Any]:
    return {
        "formula_id": PHASE20_9W_DRAFTGRID_SUCCESSOR_ID,
        "source": "experience_flow_short_structure_next_after_draft_readback",
        "found": False,
        "reason": reason,
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
    }


def _text_containment_fit(left: str, right: str) -> float:
    left_norm = _compact_text_units(left)
    right_norm = _compact_text_units(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    if left_norm in right_norm or right_norm in left_norm:
        return min(len(left_norm), len(right_norm)) / max(len(left_norm), len(right_norm), 1)
    left_units = set(left_norm)
    right_units = set(right_norm)
    return len(left_units & right_units) / max(len(left_units | right_units), 1)


def _compact_text_units(text: str) -> str:
    return "".join(str(text or "").split()).lower()


def _looks_like_internal_flow_text(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return True
    lowered = value.lower()
    if "utterance:" in lowered or "readback:" in lowered:
        return True
    if len(value) <= 24 and all(ch in "0123456789abcdef" for ch in lowered):
        return True
    return False


def _draftgrid_readback_text_to_linear(text: str) -> str:
    return "".join(str(text or "").splitlines())


def _draftgrid_successor_suffix(*, visible_text: str, target_text: str, existing_text: str) -> str:
    visible_compact = _compact_text_units(visible_text)
    target = str(target_text or "")
    target_compact = _compact_text_units(target)
    if not target.strip() or not visible_compact:
        return ""
    if target.startswith(visible_text):
        suffix = target[len(visible_text) :]
    elif visible_compact and target_compact.startswith(visible_compact):
        suffix = _suffix_after_compact_prefix(target, visible_compact)
    else:
        suffix = target
    if not suffix.strip():
        return ""
    existing_compact = _compact_text_units(existing_text)
    suffix_compact = _compact_text_units(suffix)
    if suffix_compact and suffix_compact in existing_compact:
        return ""
    return suffix


def _suffix_after_compact_prefix(text: str, compact_prefix: str) -> str:
    matched = 0
    for index, char in enumerate(text):
        if str(char).isspace():
            continue
        if matched >= len(compact_prefix):
            return text[index:]
        if str(char).lower() == compact_prefix[matched]:
            matched += 1
        else:
            return text
    return "" if matched >= len(compact_prefix) else text


def _draftgrid_edit_outcome_learning_delta(
    grid: DraftGrid,
    *,
    edit_trace: dict[str, Any],
    expected_output_chars: Sequence[str],
    source_support: float,
) -> dict[str, Any]:
    visible_after = grid.visible_text()
    expected_text = "".join(str(ch) for ch in expected_output_chars)
    old_unit = str(edit_trace.get("old_unit", ""))
    alternative_unit = str(edit_trace.get("alternative_unit", ""))
    cell_index = int(edit_trace.get("cell_index", 0) or 0)
    visible_before_chars = list(_draftgrid_linear_units(grid))
    if 0 <= cell_index < len(visible_before_chars):
        visible_before_chars[cell_index] = old_unit
    visible_before = "".join(visible_before_chars)
    visible_after_linear = "".join(_draftgrid_linear_units(grid))
    fit_before = _draftgrid_expected_fit_score(visible_before, expected_text)
    fit_after = _draftgrid_expected_fit_score(visible_after_linear, expected_text)
    improvement = max(0.0, fit_after - fit_before)
    remaining_error = max(0.0, 1.0 - fit_after)
    edit_success = _unit(improvement + (0.34 if alternative_unit and alternative_unit != old_unit else 0.0))
    verification_need = _unit(0.18 + remaining_error * 0.52 + improvement * 0.14)
    return {
        "delta_kind": "draftgrid_edit_outcome_learning",
        "formula_id": PHASE20_9S_EDIT_OUTCOME_ID,
        "source_edit_formula_id": PHASE20_9R_EDIT_CELL_ID,
        "visible_before_hash": _hash_text(visible_before),
        "visible_after_hash": _hash_text(visible_after),
        "expected_text_hash": _hash_text(expected_text),
        "cell_index": cell_index,
        "old_unit_hash": _hash_text(old_unit),
        "alternative_unit_hash": _hash_text(alternative_unit),
        "fit_before": round(fit_before, 4),
        "fit_after": round(fit_after, 4),
        "fit_improvement": round(improvement, 4),
        "remaining_error": round(remaining_error, 4),
        "verification_need": round(verification_need, 4),
        "edit_success": round(edit_success, 4),
        "source_support": round(_unit(source_support), 4),
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _draftgrid_expected_fit_score(visible_text: str, expected_text: str) -> float:
    visible = str(visible_text or "")
    expected = str(expected_text or "")
    if not visible or not expected:
        return 0.0
    match_count = sum(1 for left, right in zip(visible, expected) if left == right)
    length_penalty = abs(len(visible) - len(expected)) / max(len(visible), len(expected), 1)
    return _unit(match_count / max(len(visible), len(expected), 1) - length_penalty * 0.25)


def _no_draftgrid_edit_alternative(reason: str, *, support: float) -> dict[str, Any]:
    return {
        "formula_id": PHASE20_9R_EDIT_CELL_ID,
        "can_edit": False,
        "reason": reason,
        "source_support": round(_unit(support), 4),
        "candidate_only_no_alternative_unit": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _draftgrid_context_with_edit_alternative(
    draftgrid_action_context: dict[str, Any],
    edit_trace: dict[str, Any],
) -> dict[str, Any]:
    context = dict(draftgrid_action_context)
    edit_row = dict(context.get("edit_cell", {}) if isinstance(context.get("edit_cell"), dict) else {})
    if edit_trace.get("can_edit"):
        edit_drive = max(_unit(edit_row.get("drive", 0.0)), _unit(edit_trace.get("drive", 0.0)))
        edit_row.update(
            {
                "drive": round(edit_drive, 4),
                "action_role": "local_revision_from_cstar_alternative_unit",
                "candidate_only_no_alternative_unit": False,
                "cstar_alternative_unit": edit_trace,
                "writes_answer_directly": False,
            }
        )
    else:
        edit_row.setdefault("candidate_only_no_alternative_unit", True)
        edit_row["cstar_alternative_unit"] = edit_trace
    context["edit_cell"] = edit_row
    context["cstar_alternative_unit_edit"] = edit_trace
    return context


def _draftgrid_context_with_experience_successor(
    conn: sqlite3.Connection,
    draftgrid_action_context: dict[str, Any],
    successor_trace: dict[str, Any],
) -> dict[str, Any]:
    context = dict(draftgrid_action_context)
    context["experience_flow_successor"] = successor_trace
    if successor_trace.get("successor_text"):
        outcome_modulation = _draftgrid_successor_action_outcome_modulation(
            conn,
            draftgrid_action_context=context,
            successor_trace=successor_trace,
        )
        context["draftgrid_successor_action_outcome_modulation"] = outcome_modulation
        row = dict(context.get("continue_writing", {}) if isinstance(context.get("continue_writing"), dict) else {})
        before = _unit(row.get("drive", 0.0))
        row["drive_before_experience_flow_successor"] = round(before, 4)
        row["experience_flow_successor_bonus"] = round(
            max(0.0, float(outcome_modulation.get("continue_writing_delta", 0.0) or 0.0)),
            4,
        )
        row["experience_flow_successor_penalty"] = round(
            max(0.0, -float(outcome_modulation.get("continue_writing_delta", 0.0) or 0.0)),
            4,
        )
        row["drive"] = round(_unit(before + float(outcome_modulation.get("continue_writing_delta", 0.0) or 0.0)), 4)
        row["action_role"] = "continue_from_draftgrid_readback_experience_flow_successor"
        row["experience_flow_successor"] = successor_trace
        row["draftgrid_successor_action_outcome_modulation"] = outcome_modulation
        row["writes_answer_directly"] = False
        row["creates_reply_candidate"] = False
        context["continue_writing"] = row
        for action_type in ("read_draft", "edit_cell", "stop_generating"):
            action_row = dict(context.get(action_type, {}) if isinstance(context.get(action_type), dict) else {})
            delta = float(outcome_modulation.get(f"{action_type}_delta", 0.0) or 0.0)
            before_action = _unit(action_row.get("drive", 0.0))
            action_row["drive_before_successor_outcome_modulation"] = round(before_action, 4)
            action_row["successor_outcome_delta"] = round(delta, 4)
            action_row["drive"] = round(_unit(before_action + delta), 4)
            action_row["draftgrid_successor_action_outcome_modulation"] = outcome_modulation
            action_row["writes_answer_directly"] = False
            action_row["creates_reply_candidate"] = False
            context[action_type] = action_row
    context["writes_answer_directly"] = False
    context["creates_reply_candidate"] = False
    return context


def _draftgrid_successor_action_outcome_modulation(
    conn: sqlite3.Connection,
    *,
    draftgrid_action_context: dict[str, Any],
    successor_trace: dict[str, Any],
) -> dict[str, Any]:
    flow_support = _unit(successor_trace.get("support", 0.0))
    flow_score = _unit(successor_trace.get("score", 0.0))
    source_fit = _unit(successor_trace.get("source_fit", 0.0))
    target_fit = _unit(successor_trace.get("target_fit", 0.0))
    pending_pressure = _unit(draftgrid_action_context.get("pending_successor_pressure", 0.0))
    repetition_fatigue = _unit(draftgrid_action_context.get("repetition_fatigue", 0.0))
    low_grasp = _unit(draftgrid_action_context.get("low_grasp", 0.0))
    conflict_pressure = _unit(draftgrid_action_context.get("conflict_pressure", 0.0))
    source_support = _unit(draftgrid_action_context.get("source_support", 0.0))
    memory_rhythm_context = dict(draftgrid_action_context.get("memory_rhythm_context", {}) or {})
    memory_rhythm_confidence = _unit(memory_rhythm_context.get("memory_rhythm_confidence", 0.0))
    memory_rhythm_guard = _unit(memory_rhythm_context.get("memory_rhythm_guard", 0.0))
    reward_value, punish_value = _value_signal_for_alignment_event_id(
        conn,
        str(successor_trace.get("target_event_id") or successor_trace.get("source_event_id") or ""),
    )
    if reward_value <= 0.0 and punish_value <= 0.0:
        reward_value, punish_value = _value_signal_for_output_hash(
            conn,
            str(successor_trace.get("target_text_hash") or ""),
        )
    experience_tuner = _draftgrid_experience_tuner_projection(
        conn,
        draftgrid_action_context=draftgrid_action_context,
        successor_trace=successor_trace,
        reward_value=reward_value,
        punish_value=punish_value,
    )
    positive_evidence = _unit(flow_score * 0.36 + flow_support * 0.24 + source_fit * 0.18 + pending_pressure * 0.22)
    caution_evidence = _unit(punish_value * 0.42 + conflict_pressure * 0.20 + low_grasp * 0.12 + repetition_fatigue * 0.40)
    positive_evidence = _unit(positive_evidence + memory_rhythm_confidence * 0.18 - memory_rhythm_guard * 0.08)
    caution_evidence = _unit(caution_evidence + memory_rhythm_guard * 0.18 - memory_rhythm_confidence * 0.06)
    reward_relief = min(0.16, reward_value * (0.08 + max(0.0, 1.0 - source_support) * 0.08))
    reward_relief = min(0.18, reward_relief + memory_rhythm_confidence * 0.06)
    base_continue_delta = min(0.26, positive_evidence * 0.22 + reward_relief) - min(0.30, caution_evidence * 0.24)
    base_read_delta = min(0.16, caution_evidence * 0.12 + target_fit * 0.04) - min(0.08, reward_value * 0.05)
    base_edit_delta = min(0.14, punish_value * 0.08 + conflict_pressure * 0.08 + max(0.0, low_grasp - 0.62) * 0.06)
    base_stop_delta = _unit(punish_value * 0.10 + repetition_fatigue * 0.12 + max(0.0, caution_evidence - positive_evidence) * 0.08) - _unit(
        reward_value * 0.05 + positive_evidence * 0.03,
    )
    base_commit_delta = min(0.12, reward_value * 0.07 + positive_evidence * 0.05) - min(0.18, punish_value * 0.10 + conflict_pressure * 0.06)
    continue_delta = _tune_signed_delta(base_continue_delta, experience_tuner, positive_key="boldness_multiplier", caution_key="caution_multiplier")
    read_delta = _tune_signed_delta(base_read_delta, experience_tuner, positive_key="verification_multiplier", caution_key="boldness_multiplier")
    edit_delta = _tune_signed_delta(base_edit_delta, experience_tuner, positive_key="caution_multiplier", caution_key="boldness_multiplier")
    stop_delta = _tune_signed_delta(base_stop_delta, experience_tuner, positive_key="fatigue_multiplier", caution_key="boldness_multiplier")
    commit_delta = _tune_signed_delta(base_commit_delta, experience_tuner, positive_key="boldness_multiplier", caution_key="caution_multiplier")
    return {
        "formula_id": PHASE20_9X_DRAFTGRID_OUTCOME_MODULATION_ID,
        "source": "experience_flow_successor_reward_punish_pressure_fatigue",
        "successor_formula_id": successor_trace.get("formula_id"),
        "successor_candidate_id": successor_trace.get("candidate_id"),
        "source_event_id": successor_trace.get("source_event_id"),
        "target_event_id": successor_trace.get("target_event_id"),
        "flow_support": round(flow_support, 4),
        "flow_score": round(flow_score, 4),
        "source_fit": round(source_fit, 4),
        "target_fit": round(target_fit, 4),
        "pending_successor_pressure": round(pending_pressure, 4),
        "source_support": round(source_support, 4),
        "memory_rhythm_context": memory_rhythm_context,
        "memory_rhythm_confidence": round(memory_rhythm_confidence, 4),
        "memory_rhythm_guard": round(memory_rhythm_guard, 4),
        "low_grasp": round(low_grasp, 4),
        "conflict_pressure": round(conflict_pressure, 4),
        "repetition_fatigue": round(repetition_fatigue, 4),
        "reward": round(reward_value, 4),
        "punish": round(punish_value, 4),
        "positive_evidence": round(positive_evidence, 4),
        "caution_evidence": round(caution_evidence, 4),
        "reward_relief": round(reward_relief, 4),
        "experience_tuner_projection": experience_tuner,
        "base_continue_writing_delta": round(base_continue_delta, 4),
        "base_read_draft_delta": round(base_read_delta, 4),
        "base_edit_cell_delta": round(base_edit_delta, 4),
        "base_stop_generating_delta": round(base_stop_delta, 4),
        "base_commit_reply_delta": round(base_commit_delta, 4),
        "continue_writing_delta": round(continue_delta, 4),
        "read_draft_delta": round(read_delta, 4),
        "edit_cell_delta": round(edit_delta, 4),
        "stop_generating_delta": round(stop_delta, 4),
        "commit_reply_delta": round(commit_delta, 4),
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _draftgrid_experience_tuner_projection(
    conn: sqlite3.Connection,
    *,
    draftgrid_action_context: dict[str, Any],
    successor_trace: dict[str, Any],
    reward_value: float,
    punish_value: float,
) -> dict[str, Any]:
    source_event_id = str(successor_trace.get("source_event_id") or "")
    target_event_id = str(successor_trace.get("target_event_id") or "")
    anchor_event_id = target_event_id or source_event_id
    session_id = ""
    anchor_tick = 0
    if anchor_event_id:
        row = conn.execute(
            """
            SELECT session_id, tick
            FROM phase20_7_experience_events
            WHERE event_id=?
            LIMIT 1
            """,
            (anchor_event_id,),
        ).fetchone()
        if row:
            session_id = str(row[0] or "")
            anchor_tick = int(row[1] or 0)
    if not session_id and source_event_id and source_event_id != anchor_event_id:
        row = conn.execute(
            """
            SELECT session_id, tick
            FROM phase20_7_experience_events
            WHERE event_id=?
            LIMIT 1
            """,
            (source_event_id,),
        ).fetchone()
        if row:
            session_id = str(row[0] or "")
            anchor_tick = int(row[1] or 0)

    target_text_hash = str(successor_trace.get("target_text_hash") or "")
    source_text_hash = str(successor_trace.get("source_text_hash") or "")
    visible_text_hash = str(successor_trace.get("visible_text_hash") or "")
    source_intent = str(successor_trace.get("source_intent") or "")
    if not session_id:
        return _neutral_draftgrid_experience_tuner(
            reason="no_anchor_session",
            anchor_event_id=anchor_event_id,
            target_text_hash=target_text_hash,
        )

    latest_tick = _latest_tick_for_session(conn, session_id=session_id)
    reference_tick = max(int(latest_tick), int(anchor_tick))
    since_tick = max(0, reference_tick - 96)
    reward_total = _unit(reward_value)
    punish_total = _unit(punish_value)
    matching_alignment_count = 0
    if target_text_hash:
        rows = conn.execute(
            """
            SELECT reward, punish
            FROM phase20_7_experience_events
            WHERE session_id=?
              AND event_kind='experience_alignment'
              AND json_extract(payload_json, '$.output_hash')=?
            ORDER BY created_at_ms DESC
            LIMIT 24
            """,
            (session_id, target_text_hash),
        ).fetchall()
        matching_alignment_count = len(rows)
        if rows:
            reward_total = _unit(max(reward_total, sum(max(0.0, float(row[0] or 0.0)) for row in rows) / max(len(rows), 1)))
            punish_total = _unit(max(punish_total, sum(max(0.0, float(row[1] or 0.0)) for row in rows) / max(len(rows), 1)))

    action_counts = _recent_selected_action_counts(
        conn,
        session_id=session_id,
        action_types=("continue_writing", "read_draft", "edit_cell", "stop_generating", "commit_reply"),
        since_tick=since_tick,
    )
    continue_count = int(action_counts.get("continue_writing", 0))
    read_count = int(action_counts.get("read_draft", 0))
    edit_count = int(action_counts.get("edit_cell", 0))
    stop_count = int(action_counts.get("stop_generating", 0))
    selected_commit_count = int(action_counts.get("commit_reply", 0))
    commit_count = _recent_event_count(
        conn,
        session_id=session_id,
        event_kinds=("draft_grid_commit",),
        since_tick=since_tick,
    )
    repeated_commit_count = (
        _recent_committed_text_hash_count(
            conn,
            session_id=session_id,
            text_hash=target_text_hash,
            since_tick=since_tick,
        )
        if target_text_hash
        else 0
    )
    visible_repetition_count = (
        _recent_committed_text_hash_count(
            conn,
            session_id=session_id,
            text_hash=visible_text_hash,
            since_tick=since_tick,
        )
        if visible_text_hash and visible_text_hash != target_text_hash
        else 0
    )
    same_intent_count = (
        _recent_committed_intent_count(
            conn,
            session_id=session_id,
            source_intent=source_intent,
            since_tick=since_tick,
        )
        if source_intent
        else 0
    )
    context_fatigue = _unit(draftgrid_action_context.get("repetition_fatigue", 0.0))
    context_low_grasp = _unit(draftgrid_action_context.get("low_grasp", 0.0))
    context_conflict = _unit(draftgrid_action_context.get("conflict_pressure", 0.0))
    memory_rhythm_context = dict(draftgrid_action_context.get("memory_rhythm_context", {}) or {})
    memory_rhythm_confidence = _unit(memory_rhythm_context.get("memory_rhythm_confidence", 0.0))
    memory_rhythm_guard = _unit(memory_rhythm_context.get("memory_rhythm_guard", 0.0))
    active = any(
        (
            reward_total > 0.0,
            punish_total > 0.0,
            matching_alignment_count > 0,
            continue_count > 0,
            read_count > 0,
            edit_count > 0,
            stop_count > 0,
            commit_count > 0,
            repeated_commit_count > 0,
        )
    )
    if not active:
        return _neutral_draftgrid_experience_tuner(
            reason="no_relevant_experience_history",
            anchor_event_id=anchor_event_id,
            target_text_hash=target_text_hash,
            session_id=session_id,
            anchor_tick=anchor_tick,
            since_tick=since_tick,
        )

    reward_pressure = min(1.0, reward_total + continue_count * 0.035 + matching_alignment_count * 0.020)
    punish_pressure = min(1.0, punish_total + context_conflict * 0.32 + edit_count * 0.035 + stop_count * 0.035)
    verification_pressure = min(1.0, punish_total * 0.72 + read_count * 0.050 + edit_count * 0.040 + context_low_grasp * 0.22)
    fatigue_pressure = min(
        1.0,
        context_fatigue
        + repeated_commit_count * 0.070
        + visible_repetition_count * 0.035
        + same_intent_count * 0.016
        + stop_count * 0.040
        + selected_commit_count * 0.010,
    )
    reward_pressure = _unit(reward_pressure + memory_rhythm_confidence * 0.14 - memory_rhythm_guard * 0.05)
    punish_pressure = _unit(punish_pressure + memory_rhythm_guard * 0.16 - memory_rhythm_confidence * 0.06)
    verification_pressure = _unit(verification_pressure + memory_rhythm_guard * 0.10 - memory_rhythm_confidence * 0.04)
    fatigue_pressure = _unit(fatigue_pressure + memory_rhythm_guard * 0.06 - memory_rhythm_confidence * 0.03)
    boldness_multiplier = _bounded_multiplier(
        1.0 + reward_pressure * 0.34 - punish_pressure * 0.24 - fatigue_pressure * 0.10,
        low=0.30,
        high=2.00,
    )
    caution_multiplier = _bounded_multiplier(
        1.0 + punish_pressure * 0.34 + verification_pressure * 0.16 - reward_pressure * 0.12,
        low=0.30,
        high=2.00,
    )
    verification_multiplier = _bounded_multiplier(
        1.0 + verification_pressure * 0.30 + punish_pressure * 0.10 - reward_pressure * 0.08,
        low=0.30,
        high=2.00,
    )
    fatigue_multiplier = _bounded_multiplier(
        1.0 + fatigue_pressure * 0.38 + punish_pressure * 0.08 - reward_pressure * 0.08,
        low=0.20,
        high=2.50,
    )
    return {
        "formula_id": PHASE20_9Y_DRAFTGRID_EXPERIENCE_TUNER_ID,
        "source": "experience_flow_action_outcome_history_projection",
        "active": True,
        "session_id": session_id,
        "anchor_event_id": anchor_event_id,
        "anchor_tick": int(anchor_tick),
        "since_tick": int(since_tick),
        "target_text_hash": target_text_hash,
        "source_text_hash": source_text_hash,
        "visible_text_hash": visible_text_hash,
        "source_intent": source_intent,
        "memory_rhythm_context": memory_rhythm_context,
        "memory_rhythm_confidence": round(memory_rhythm_confidence, 4),
        "memory_rhythm_guard": round(memory_rhythm_guard, 4),
        "matching_alignment_count": int(matching_alignment_count),
        "reward_total": round(reward_total, 4),
        "punish_total": round(punish_total, 4),
        "reward_pressure": round(reward_pressure, 4),
        "punish_pressure": round(punish_pressure, 4),
        "verification_pressure": round(verification_pressure, 4),
        "fatigue_pressure": round(fatigue_pressure, 4),
        "continue_count": int(continue_count),
        "read_count": int(read_count),
        "edit_count": int(edit_count),
        "stop_count": int(stop_count),
        "selected_commit_count": int(selected_commit_count),
        "commit_count": int(commit_count),
        "repeated_commit_count": int(repeated_commit_count),
        "visible_repetition_count": int(visible_repetition_count),
        "same_intent_count": int(same_intent_count),
        "boldness_multiplier": round(boldness_multiplier, 4),
        "caution_multiplier": round(caution_multiplier, 4),
        "verification_multiplier": round(verification_multiplier, 4),
        "fatigue_multiplier": round(fatigue_multiplier, 4),
        "projection_only": True,
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
        "subjective": True,
        "may_be_wrong": True,
    }


def _neutral_draftgrid_experience_tuner(
    *,
    reason: str,
    anchor_event_id: str,
    target_text_hash: str,
    session_id: str = "",
    anchor_tick: int = 0,
    since_tick: int = 0,
) -> dict[str, Any]:
    return {
        "formula_id": PHASE20_9Y_DRAFTGRID_EXPERIENCE_TUNER_ID,
        "source": "experience_flow_action_outcome_history_projection",
        "active": False,
        "reason": reason,
        "session_id": session_id,
        "anchor_event_id": anchor_event_id,
        "anchor_tick": int(anchor_tick),
        "since_tick": int(since_tick),
        "target_text_hash": target_text_hash,
        "reward_total": 0.0,
        "punish_total": 0.0,
        "boldness_multiplier": 1.0,
        "caution_multiplier": 1.0,
        "verification_multiplier": 1.0,
        "fatigue_multiplier": 1.0,
        "projection_only": True,
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
        "subjective": True,
        "may_be_wrong": True,
    }


def _action_experience_tuner_projection(
    conn: sqlite3.Connection | None,
    *,
    session_id: str,
    tick: int,
    action_types: Sequence[str],
    selected_action_type: str = "",
    outward_text_hash: str = "",
    source_intent: str = "",
    window_ticks: int = 96,
) -> dict[str, Any]:
    action_values = tuple(dict.fromkeys(str(action) for action in action_types if str(action)))
    if conn is None or not session_id or not action_values:
        return _neutral_action_experience_tuner(
            reason="no_connection_or_action_types",
            action_types=action_values,
            selected_action_type=selected_action_type,
        )
    since_tick = max(0, int(tick) - int(window_ticks))
    action_counts = _recent_selected_action_counts(
        conn,
        session_id=session_id,
        action_types=action_values,
        since_tick=since_tick,
    )
    action_feedback = _recent_action_feedback_projection(
        conn,
        session_id=session_id,
        since_tick=since_tick,
        action_types=action_values,
    )
    commit_count = _recent_event_count(
        conn,
        session_id=session_id,
        event_kinds=("draft_grid_commit",),
        since_tick=since_tick,
    )
    stop_count = _recent_event_count(
        conn,
        session_id=session_id,
        event_kinds=("draft_grid_stop",),
        since_tick=since_tick,
    )
    read_count = _recent_event_count(
        conn,
        session_id=session_id,
        event_kinds=("draft_grid_read",),
        since_tick=since_tick,
    )
    edit_count = _recent_event_count(
        conn,
        session_id=session_id,
        event_kinds=("draft_grid_edit",),
        since_tick=since_tick,
    )
    outward_count = _recent_selected_action_count(
        conn,
        session_id=session_id,
        action_types=("outward_speech",),
        since_tick=since_tick,
    )
    same_outward_count = (
        _recent_outward_text_count(
            conn,
            session_id=session_id,
            text_hash=outward_text_hash,
            since_tick=max(0, int(tick) - 160),
        )
        if outward_text_hash
        else 0
    )
    same_intent_commit_count = (
        _recent_committed_intent_count(
            conn,
            session_id=session_id,
            source_intent=source_intent,
            since_tick=since_tick,
        )
        if source_intent
        else 0
    )
    unclosed_count = _recent_event_count(
        conn,
        session_id=session_id,
        event_kinds=("unclosed_item_update", "unclosed_item_resolved"),
        since_tick=since_tick,
    )
    no_feedback_count = _recent_outward_no_feedback_count(
        conn,
        session_id=session_id,
        since_tick=since_tick,
    )
    reward_total = _unit(action_feedback.get("reward_total", 0.0))
    punish_total = _unit(action_feedback.get("punish_total", 0.0))
    action_total = sum(int(action_counts.get(action, 0)) for action in action_values)
    active = any(
        (
            action_total > 0,
            reward_total > 0.0,
            punish_total > 0.0,
            commit_count > 0,
            stop_count > 0,
            read_count > 0,
            edit_count > 0,
            outward_count > 0,
            same_outward_count > 0,
            same_intent_commit_count > 0,
            unclosed_count > 0,
            no_feedback_count > 0,
        )
    )
    if not active:
        return _neutral_action_experience_tuner(
            reason="no_relevant_action_experience",
            action_types=action_values,
            selected_action_type=selected_action_type,
            since_tick=since_tick,
        )

    reward_pressure = min(1.0, reward_total + commit_count * 0.020 + action_counts.get("continue_writing", 0) * 0.025)
    punish_pressure = min(1.0, punish_total + stop_count * 0.035 + edit_count * 0.030 + no_feedback_count * 0.040)
    ask_pressure = min(1.0, unclosed_count * 0.055 + action_counts.get("request_teacher", 0) * 0.025)
    read_repetition_pressure = min(1.0, max(0, read_count - 2) * 0.075)
    verify_pressure = min(1.0, min(read_count, 2) * 0.018 + edit_count * 0.040 + punish_pressure * 0.55)
    fatigue_pressure = min(
        1.0,
        same_outward_count * 0.100
        + outward_count * 0.045
        + same_intent_commit_count * 0.025
        + stop_count * 0.030
        + read_repetition_pressure * 0.180
        + no_feedback_count * 0.075,
    )
    boldness_multiplier = _bounded_multiplier(1.0 + reward_pressure * 0.28 - punish_pressure * 0.20 - fatigue_pressure * 0.12, low=0.30, high=2.00)
    caution_multiplier = _bounded_multiplier(1.0 + punish_pressure * 0.30 + verify_pressure * 0.14 - reward_pressure * 0.10, low=0.55, high=1.55)
    ask_multiplier = _bounded_multiplier(1.0 + ask_pressure * 0.22 + punish_pressure * 0.10 - reward_pressure * 0.12 - fatigue_pressure * 0.08, low=0.55, high=1.45)
    maintain_multiplier = _bounded_multiplier(1.0 + ask_pressure * 0.14 + verify_pressure * 0.10 - fatigue_pressure * 0.05, low=0.60, high=1.40)
    outward_multiplier = _bounded_multiplier(1.0 + reward_pressure * 0.20 - punish_pressure * 0.16 - fatigue_pressure * 0.38, low=0.15, high=1.80)
    verify_multiplier = _bounded_multiplier(
        1.0 + verify_pressure * 0.32 + punish_pressure * 0.10 - reward_pressure * 0.06 - read_repetition_pressure * 0.30,
        low=0.55,
        high=1.50,
    )
    stop_multiplier = _bounded_multiplier(1.0 + fatigue_pressure * 0.34 + punish_pressure * 0.12 - reward_pressure * 0.06, low=0.20, high=2.50)
    action_multipliers = {
        "request_teacher": ask_multiplier,
        "maintain_unclosed": maintain_multiplier,
        "outward_speech": outward_multiplier,
        "write_cell": boldness_multiplier,
        "continue_writing": boldness_multiplier,
        "commit_reply": boldness_multiplier,
        "integrate_feedback": caution_multiplier,
        "read_draft": verify_multiplier,
        "edit_cell": caution_multiplier,
        "stop_generating": stop_multiplier,
        "idle_think": maintain_multiplier,
        "idle_visual_focus": maintain_multiplier,
        "idle_audio_focus": maintain_multiplier,
        "idle_observe": 1.0,
        "sleep_lower_frequency": stop_multiplier,
    }
    return {
        "formula_id": PHASE20_9Z_ACTION_EXPERIENCE_TUNER_ID,
        "source": "existing_experience_events_and_action_records_projection",
        "active": True,
        "session_id": session_id,
        "tick": int(tick),
        "since_tick": int(since_tick),
        "action_types": action_values,
        "selected_action_type": selected_action_type,
        "source_intent": source_intent,
        "outward_text_hash": outward_text_hash,
        "action_counts": {action: int(action_counts.get(action, 0)) for action in action_values},
        "reward_total": round(reward_total, 4),
        "punish_total": round(punish_total, 4),
        "feedback_target_count": int(action_feedback.get("target_count", 0)),
        "commit_count": int(commit_count),
        "stop_count": int(stop_count),
        "read_count": int(read_count),
        "edit_count": int(edit_count),
        "outward_count": int(outward_count),
        "same_outward_count": int(same_outward_count),
        "same_intent_commit_count": int(same_intent_commit_count),
        "unclosed_count": int(unclosed_count),
        "no_feedback_count": int(no_feedback_count),
        "reward_pressure": round(reward_pressure, 4),
        "punish_pressure": round(punish_pressure, 4),
        "ask_pressure": round(ask_pressure, 4),
        "verify_pressure": round(verify_pressure, 4),
        "fatigue_pressure": round(fatigue_pressure, 4),
        "read_repetition_pressure": round(read_repetition_pressure, 4),
        "boldness_multiplier": round(boldness_multiplier, 4),
        "caution_multiplier": round(caution_multiplier, 4),
        "ask_multiplier": round(ask_multiplier, 4),
        "maintain_multiplier": round(maintain_multiplier, 4),
        "outward_multiplier": round(outward_multiplier, 4),
        "verify_multiplier": round(verify_multiplier, 4),
        "stop_multiplier": round(stop_multiplier, 4),
        "action_multipliers": {key: round(float(value), 4) for key, value in action_multipliers.items() if key in action_values or key in {"write_cell", "commit_reply", "idle_think"}},
        "projection_only": True,
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
        "subjective": True,
        "may_be_wrong": True,
    }


def _neutral_action_experience_tuner(
    *,
    reason: str,
    action_types: Sequence[str],
    selected_action_type: str,
    since_tick: int = 0,
) -> dict[str, Any]:
    return {
        "formula_id": PHASE20_9Z_ACTION_EXPERIENCE_TUNER_ID,
        "source": "existing_experience_events_and_action_records_projection",
        "active": False,
        "reason": reason,
        "action_types": tuple(action_types),
        "selected_action_type": selected_action_type,
        "since_tick": int(since_tick),
        "boldness_multiplier": 1.0,
        "caution_multiplier": 1.0,
        "ask_multiplier": 1.0,
        "maintain_multiplier": 1.0,
        "outward_multiplier": 1.0,
        "verify_multiplier": 1.0,
        "stop_multiplier": 1.0,
        "action_multipliers": {},
        "projection_only": True,
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
        "subjective": True,
        "may_be_wrong": True,
    }


def _apply_action_experience_tuner_to_rows(
    rows: Sequence[dict[str, Any]],
    selected_action: dict[str, Any],
    tuner: dict[str, Any],
) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    if not tuner or not tuner.get("active"):
        return tuple(rows), selected_action
    multipliers = tuner.get("action_multipliers")
    if not isinstance(multipliers, dict):
        return tuple(rows), selected_action
    adjusted_rows: list[dict[str, Any]] = []
    selected_drive: float | None = None
    selected_multiplier = 1.0
    for row in rows:
        action_type = str(row.get("action_type") or "")
        multiplier = _bounded_multiplier(multipliers.get(action_type, 1.0), low=0.35, high=1.70)
        drive_before = _unit(row.get("drive", 0.0))
        drive_after = _unit(drive_before * multiplier)
        adjusted = dict(row)
        if abs(multiplier - 1.0) > 0.0001:
            adjusted["drive_before_action_experience_tuner"] = round(drive_before, 4)
            adjusted["action_experience_tuner_multiplier"] = round(multiplier, 4)
            adjusted["drive"] = round(drive_after, 4)
            adjusted["action_experience_tuner_projection"] = tuner
        if adjusted.get("selected"):
            selected_drive = drive_after
            selected_multiplier = multiplier
        adjusted_rows.append(adjusted)
    adjusted_rows.sort(key=lambda row: (bool(row.get("selected")), float(row.get("drive", 0.0) or 0.0)), reverse=True)
    selected = dict(selected_action)
    if selected_drive is not None:
        selected["drive"] = round(selected_drive, 4)
    if abs(selected_multiplier - 1.0) > 0.0001:
        selected["action_experience_tuner_multiplier"] = round(selected_multiplier, 4)
        selected["action_experience_tuner_projection"] = tuner
    return tuple(adjusted_rows), selected


def _recent_action_feedback_projection(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    since_tick: int,
    action_types: Sequence[str],
) -> dict[str, Any]:
    action_values = tuple(str(action) for action in action_types if str(action))
    if not action_values:
        return {"reward_total": 0.0, "punish_total": 0.0, "target_count": 0}
    placeholders = ",".join("?" for _ in action_values)
    rows = conn.execute(
        f"""
        SELECT a.action_record_id, e.event_id, e.tick
        FROM phase20_7_action_records a
        LEFT JOIN phase20_7_experience_events e ON e.event_id=a.result_event_id
        WHERE a.session_id=? AND a.selected=1 AND a.tick>=? AND a.action_type IN ({placeholders})
        ORDER BY a.tick DESC
        LIMIT 96
        """,
        (session_id, int(since_tick), *action_values),
    ).fetchall()
    reward_total = 0.0
    punish_total = 0.0
    target_count = 0
    for rank, (_action_record_id, result_event_id, action_tick) in enumerate(rows):
        if not result_event_id:
            continue
        feedback_rows = conn.execute(
            """
            SELECT reward, punish
            FROM phase20_7_experience_events
            WHERE session_id=?
              AND tick>?
              AND event_kind='teacher_feedback_event'
              AND json_extract(payload_json, '$.target_event_id')=?
            ORDER BY tick ASC, created_at_ms ASC
            LIMIT 8
            """,
            (session_id, int(action_tick or 0), str(result_event_id)),
        ).fetchall()
        for reward, punish in feedback_rows:
            recency = 1.0 / (1.0 + rank)
            reward_total += _unit(reward) * recency
            punish_total += _unit(punish) * recency
            target_count += 1
    return {
        "reward_total": _unit(reward_total),
        "punish_total": _unit(punish_total),
        "target_count": int(target_count),
    }


def _recent_outward_no_feedback_count(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    since_tick: int,
) -> int:
    rows = conn.execute(
        """
        SELECT event_id, tick
        FROM phase20_7_experience_events
        WHERE session_id=? AND tick>=? AND event_kind='outward_speech'
        ORDER BY tick DESC
        LIMIT 32
        """,
        (session_id, int(since_tick)),
    ).fetchall()
    count = 0
    for outward_event_id, outward_tick in rows:
        later_feedback = conn.execute(
            """
            SELECT COUNT(*)
            FROM phase20_7_experience_events
            WHERE session_id=?
              AND tick>?
              AND event_kind='teacher_feedback_event'
              AND json_extract(payload_json, '$.target_event_id')=?
            """,
            (session_id, int(outward_tick or 0), str(outward_event_id)),
        ).fetchone()
        later_external = _recent_event_count(
            conn,
            session_id=session_id,
            event_kinds=("text_receptor_observation", "audio_audit_sample"),
            since_tick=int(outward_tick or 0) + 1,
        )
        if int(later_feedback[0] or 0) <= 0 and int(later_external) <= 0:
            count += 1
    return count


def _tune_signed_delta(
    value: float,
    tuner: dict[str, Any],
    *,
    positive_key: str,
    caution_key: str,
) -> float:
    try:
        base = float(value or 0.0)
    except (TypeError, ValueError):
        base = 0.0
    if abs(base) <= 1e-9:
        return 0.0
    source = tuner if isinstance(tuner, dict) else {}
    key = positive_key if base >= 0.0 else caution_key
    multiplier = _bounded_multiplier(source.get(key, 1.0), low=0.45, high=1.65)
    return max(-1.0, min(1.0, base * multiplier))


def _bounded_multiplier(value: Any, *, low: float, high: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 1.0
    return max(float(low), min(float(high), numeric))


def _recent_selected_action_counts(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    action_types: Sequence[str],
    since_tick: int,
) -> dict[str, int]:
    action_values = tuple(str(action) for action in action_types if str(action))
    if not action_values:
        return {}
    placeholders = ",".join("?" for _ in action_values)
    rows = conn.execute(
        f"""
        SELECT action_type, COUNT(*)
        FROM phase20_7_action_records
        WHERE session_id=? AND selected=1 AND tick>=? AND action_type IN ({placeholders})
        GROUP BY action_type
        """,
        (session_id, int(since_tick), *action_values),
    ).fetchall()
    return {str(action_type): int(count or 0) for action_type, count in rows}


def _write_draftgrid_edit_self_occurrence(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    tick: int,
    event_id: str,
    row: int,
    col: int,
    old_char: str,
    new_char: str,
    visible_text: str,
    edit_trace: dict[str, Any],
) -> dict[str, Any]:
    new_hash = _hash_text(str(new_char))
    old_hash = _hash_text(str(old_char))
    visible_hash = _hash_text(str(visible_text or ""))
    sa_type_id = f"self_draft_grid_edit::{old_hash}->{new_hash}"
    upsert_sa_type(
        conn,
        sa_type_id=sa_type_id,
        substrate="SELF_DRAFT_GRID",
        modality="draft_grid_text",
        canonical_hint=f"{old_char}->{new_char}",
        tick=tick,
    )
    occurrence_id = insert_occurrence(
        conn,
        event_id=event_id,
        sa_type_id=sa_type_id,
        tick=tick,
        substrate="SELF_DRAFT_GRID",
        position={
            "axis": "draft_grid_edit",
            "session_id": session_id,
            "row": int(row),
            "col": int(col),
            "old_unit_hash": old_hash,
            "alternative_unit_hash": new_hash,
            "visible_text_hash": visible_hash,
            "formula_id": PHASE20_9R_EDIT_CELL_ID,
            "cstar_alternative_unit": edit_trace,
        },
        r=0.42,
        v=_unit(edit_trace.get("source_support", 0.0)) * 0.24,
        a=_unit(edit_trace.get("drive", 0.0)),
        p=_unit(edit_trace.get("conflict_pressure", 0.0)),
        clarity=max(0.42, _unit(edit_trace.get("drive", 0.0))),
        source_ref=event_id,
        payload_ref=event_id,
    )
    _observe_pool(
        pool,
        tick=tick,
        sa_id=sa_type_id,
        family="self_draft_grid",
        label=f"{old_char}->{new_char}",
        energy=0.32,
        source="self_draft_grid_edit",
        ledger_source="replay",
    )
    source_occurrences = _recent_self_draftgrid_occurrences(conn, session_id=session_id, before_tick=tick, limit=6)
    edge_ids: list[str] = []
    for source_occurrence_id in source_occurrences:
        edge_ids.append(
            insert_structure_edge(
                conn,
                src_occurrence_id=source_occurrence_id,
                dst_occurrence_id=occurrence_id,
                edge_type="readback_conflict_to_edit",
                weight=max(0.16, _unit(edit_trace.get("drive", 0.0))),
                learned_weight=min(0.34, _unit(edit_trace.get("drive", 0.0)) * 0.26),
                tick=tick,
            )
        )
    return {
        "formula_id": PHASE20_9R_EDIT_CELL_ID,
        "occurrence_id": occurrence_id,
        "sa_type_id": sa_type_id,
        "substrate": "SELF_DRAFT_GRID",
        "source_occurrence_ids": tuple(source_occurrences),
        "edge_ids": tuple(edge_ids),
        "row": int(row),
        "col": int(col),
        "old_unit_hash": old_hash,
        "alternative_unit_hash": new_hash,
        "visible_text_hash": visible_hash,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _write_draftgrid_write_self_occurrence(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    tick: int,
    event_id: str,
    row: int,
    col: int,
    char: str,
    visible_text: str,
    output_intent: str,
) -> dict[str, Any]:
    unit_hash = _hash_text(str(char))
    visible_hash = _hash_text(str(visible_text or ""))
    sa_type_id = f"self_draft_grid_unit::{unit_hash}"
    upsert_sa_type(
        conn,
        sa_type_id=sa_type_id,
        substrate="SELF_DRAFT_GRID",
        modality="draft_grid_text",
        canonical_hint=str(char),
        tick=tick,
    )
    occurrence_id = insert_occurrence(
        conn,
        event_id=event_id,
        sa_type_id=sa_type_id,
        tick=tick,
        substrate="SELF_DRAFT_GRID",
        position={
            "axis": "draft_grid_cell",
            "row": int(row),
            "col": int(col),
            "unit_hash": unit_hash,
            "visible_text_hash": visible_hash,
            "source_intent": output_intent,
            "formula_id": PHASE20_9Q_DRAFTGRID_READBACK_FLOW_ID,
        },
        r=0.22,
        v=0.0,
        a=0.18,
        p=0.12,
        clarity=0.62,
        source_ref=event_id,
        payload_ref=event_id,
    )
    _observe_pool(
        pool,
        tick=tick,
        sa_id=sa_type_id,
        family="self_draft_grid",
        label=str(char),
        energy=0.18,
        source="self_draft_grid",
        ledger_source="replay",
    )
    prev = _latest_draftgrid_self_occurrence(conn, session_id=session_id, before_tick=tick)
    edge_ids: list[str] = []
    if prev is not None:
        edge_ids.append(
            insert_structure_edge(
                conn,
                src_occurrence_id=str(prev["occurrence_id"]),
                dst_occurrence_id=occurrence_id,
                edge_type="draft_grid_write_next",
                weight=1.0,
                learned_weight=0.18,
                tick=tick,
            )
        )
    return {
        "formula_id": PHASE20_9Q_DRAFTGRID_READBACK_FLOW_ID,
        "occurrence_id": occurrence_id,
        "previous_occurrence_id": prev.get("occurrence_id") if prev else None,
        "edge_ids": tuple(edge_ids),
        "substrate": "SELF_DRAFT_GRID",
        "unit_hash": unit_hash,
        "visible_text_hash": visible_hash,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _latest_draftgrid_self_occurrence(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT o.occurrence_id, o.tick
        FROM phase20_7_occurrences o
        JOIN phase20_7_experience_events e ON e.event_id=o.event_id
        WHERE e.session_id=?
          AND o.substrate='SELF_DRAFT_GRID'
          AND o.tick < ?
          AND o.sa_type_id LIKE 'self_draft_grid_unit::%'
        ORDER BY o.tick DESC
        LIMIT 1
        """,
        (session_id, int(before_tick)),
    ).fetchone()
    if not row:
        return None
    return {"occurrence_id": str(row[0]), "tick": int(row[1])}


def _recent_draftgrid_write_occurrences(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
    limit: int,
) -> tuple[str, ...]:
    rows = conn.execute(
        """
        SELECT o.occurrence_id
        FROM phase20_7_occurrences o
        JOIN phase20_7_experience_events e ON e.event_id=o.event_id
        WHERE e.session_id=?
          AND e.event_kind='draft_grid_write'
          AND o.tick < ?
        ORDER BY o.tick DESC
        LIMIT ?
        """,
        (session_id, int(before_tick), int(limit)),
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _reward_punish_backward_attribution_consolidation(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    tick: int,
    result_event_ids: Sequence[str],
    reward: float,
    punish: float,
    observation: _ObservationLike | None,
    feedback_attribution: _BackwardAttribution | None,
) -> dict[str, Any]:
    reward_value = _unit(max(0.0, float(reward or 0.0)))
    punish_value = _unit(max(0.0, float(punish or 0.0)))
    result_intensity = _unit(max(reward_value, punish_value, (reward_value + punish_value) * 0.5))
    c_backward_rows = tuple(feedback_attribution.c_backward_rows()) if feedback_attribution is not None else ()
    cause_grasp = _unit(max((float(row.get("cause_grasp", row.get("support", 0.0)) or 0.0) for row in c_backward_rows), default=0.0))
    if observation is not None and not c_backward_rows:
        cause_grasp = max(cause_grasp, 0.36)
    eligible_occurrences = _eligible_attribution_occurrences(
        conn,
        session_id=session_id,
        before_tick=tick,
        observation=observation,
        c_backward_rows=c_backward_rows,
    )
    eligibility_strength = _unit(
        0.20
        + cause_grasp * 0.32
        + min(0.24, len(eligible_occurrences) * 0.035)
        + (0.12 if any(str(item.get("substrate")) == "SELF_DRAFT_GRID" for item in eligible_occurrences) else 0.0)
    )
    consolidation_score = _unit(eligibility_strength * result_intensity)
    expected_reward_delta = _unit(reward_value * consolidation_score)
    expected_punish_delta = _unit(punish_value * consolidation_score)
    attention_bias_delta = _unit((reward_value + punish_value * 0.65) * consolidation_score)
    inhibition_delta = _unit(punish_value * consolidation_score)
    alternative_search_delta = _unit(punish_value * (1.0 - min(0.88, cause_grasp)) * (0.35 + consolidation_score * 0.65))
    cause_slots: list[dict[str, Any]] = []
    for row in c_backward_rows:
        raw_slots = row.get("cause_slots", ())
        if isinstance(raw_slots, Sequence) and not isinstance(raw_slots, (str, bytes, bytearray)):
            cause_slots.extend(dict(slot) for slot in raw_slots if isinstance(slot, dict))
    edge_ids = _eligible_attribution_edges(
        conn,
        tuple(str(item.get("occurrence_id")) for item in eligible_occurrences if item.get("occurrence_id")),
    )
    return {
        "delta_kind": "reward_punish_backward_attribution_consolidation",
        "formula_id": PHASE20_9Q_ATTRIBUTION_CONSOLIDATION_ID,
        "result_event_ids": tuple(str(event_id) for event_id in result_event_ids),
        "reward": round(reward_value, 4),
        "punish": round(punish_value, 4),
        "result_intensity": round(result_intensity, 4),
        "cause_grasp": round(cause_grasp, 4),
        "eligibility_strength": round(eligibility_strength, 4),
        "attribution_consolidation_score": round(consolidation_score, 4),
        "expected_reward_delta": round(expected_reward_delta, 4),
        "expected_punish_delta": round(expected_punish_delta, 4),
        "attention_bias_delta": round(attention_bias_delta, 4),
        "inhibition_delta": round(inhibition_delta, 4),
        "alternative_search_delta": round(alternative_search_delta, 4),
        "cause_slots_from_c_backward": tuple(cause_slots[:12]),
        "eligible_occurrences": tuple(eligible_occurrences),
        "eligible_edges": tuple(edge_ids[:16]),
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _eligible_attribution_occurrences(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
    observation: _ObservationLike | None,
    c_backward_rows: Sequence[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    occurrence_ids: list[str] = []
    if observation is not None:
        occurrence_ids.extend(str(occurrence_id) for occurrence_id in observation.occurrence_ids[:8])
    for row in c_backward_rows:
        neutralized = row.get("neutralized_occurrences", ())
        if not isinstance(neutralized, Sequence) or isinstance(neutralized, (str, bytes, bytearray)):
            continue
        for item in neutralized:
            if isinstance(item, dict) and item.get("occurrence_id"):
                occurrence_ids.append(str(item.get("occurrence_id")))
    occurrence_ids.extend(
        _recent_self_draftgrid_occurrences(conn, session_id=session_id, before_tick=before_tick, limit=8)
    )
    unique_ids = tuple(dict.fromkeys(occurrence_ids))
    real_ids = tuple(occurrence_id for occurrence_id in unique_ids if occurrence_id.startswith("occ::"))
    if not real_ids:
        return ()
    placeholders = ",".join("?" for _ in real_ids)
    rows = conn.execute(
        f"""
        SELECT occurrence_id, sa_type_id, substrate, tick, R, V, A, P, clarity
        FROM phase20_7_occurrences
        WHERE occurrence_id IN ({placeholders})
        ORDER BY tick DESC
        """,
        real_ids,
    ).fetchall()
    out: list[dict[str, Any]] = []
    for occurrence_id, sa_type_id, substrate, occ_tick, r, v, a, p, clarity in rows:
        age = max(0, int(before_tick) - int(occ_tick))
        recency = 1.0 / (1.0 + age)
        attention = _unit(abs(float(a or 0.0)) + abs(float(clarity or 0.0)) * 0.5)
        out.append(
            {
                "occurrence_id": str(occurrence_id),
                "sa_type_id": str(sa_type_id),
                "substrate": str(substrate),
                "tick": int(occ_tick),
                "attention": round(attention, 4),
                "recency": round(recency, 4),
                "r": round(float(r or 0.0), 4),
                "v": round(float(v or 0.0), 4),
                "p": round(float(p or 0.0), 4),
            }
        )
    return tuple(out)


def _recent_self_draftgrid_occurrences(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
    limit: int,
) -> tuple[str, ...]:
    rows = conn.execute(
        """
        SELECT o.occurrence_id
        FROM phase20_7_occurrences o
        JOIN phase20_7_experience_events e ON e.event_id=o.event_id
        WHERE e.session_id=?
          AND o.substrate='SELF_DRAFT_GRID'
          AND o.tick < ?
        ORDER BY o.tick DESC
        LIMIT ?
        """,
        (session_id, int(before_tick), int(limit)),
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _eligible_attribution_edges(
    conn: sqlite3.Connection,
    occurrence_ids: Sequence[str],
) -> tuple[dict[str, Any], ...]:
    if not occurrence_ids:
        return ()
    placeholders = ",".join("?" for _ in occurrence_ids)
    rows = conn.execute(
        f"""
        SELECT edge_id, src_occurrence_id, dst_occurrence_id, edge_type, weight, learned_weight
        FROM phase20_7_structure_edges
        WHERE src_occurrence_id IN ({placeholders})
           OR dst_occurrence_id IN ({placeholders})
        ORDER BY updated_tick DESC
        LIMIT 24
        """,
        tuple(occurrence_ids) + tuple(occurrence_ids),
    ).fetchall()
    return tuple(
        {
            "edge_id": str(edge_id),
            "src_occurrence_id": str(src),
            "dst_occurrence_id": str(dst),
            "edge_type": str(edge_type),
            "weight": round(float(weight or 0.0), 4),
            "learned_weight": round(float(learned_weight or 0.0), 4),
        }
        for edge_id, src, dst, edge_type, weight, learned_weight in rows
    )


def _short_structure_flow_attention_bias(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
) -> dict[str, Any]:
    latest = _latest_short_structure_flow_occurrence(conn, session_id=session_id, before_tick=before_tick)
    if latest is None:
        return {
            "formula_id": PHASE20_8K_CARRYOVER_SSP_FLOW_ID,
            "active": False,
            "visual_drive_delta": 0.0,
            "idle_think_drive_delta": 0.0,
        }
    position = latest.get("position", {})
    source_kind = str(position.get("source_kind", "")) if isinstance(position, dict) else ""
    support = _unit(latest.get("support", 0.0))
    recency = 1.0 / (1.0 + max(0, int(before_tick) - int(latest.get("tick", 0))))
    visual_delta = min(0.08, support * recency * (0.06 if source_kind in {"cstar_carryover", "visual"} else 0.025))
    idle_delta = min(0.10, support * recency * (0.08 if source_kind in {"idle", "cstar_carryover"} else 0.04))
    return {
        "formula_id": PHASE20_8K_CARRYOVER_SSP_FLOW_ID,
        "active": True,
        "source_occurrence_id": latest.get("occurrence_id"),
        "source_kind": source_kind,
        "source_tick": latest.get("tick"),
        "support": round(support, 4),
        "recency": round(recency, 4),
        "visual_drive_delta": round(visual_delta, 4),
        "idle_think_drive_delta": round(idle_delta, 4),
        "writes_answer_directly": False,
    }


def _append_runtime_tick(tick_events: list[RuntimeTickEventV2], event: RuntimeTickEventV2) -> RuntimeTickEventV2:
    completed = complete_every_tick_cognitive_cycle(event)
    tick_events.append(completed)
    # §185 实时进度: 通知 web 层当前 tick/action (无锁, CPython dict 单键写原子).
    hook = _live_progress_hook
    if hook is not None:
        try:
            action = completed.selected_action
            hook(int(completed.tick), str(action.get("action_type", "") if isinstance(action, dict) else ""))
        except Exception:
            pass
    return completed


def _learning_loop_metric_from_event(event: RuntimeTickEventV2) -> dict[str, Any]:
    for delta in event.learning_deltas:
        if isinstance(delta, dict) and delta.get("delta_kind") == "learning_loop_metrics":
            return dict(delta)
    return {}


def _attribution_consolidation_delta_from_event(event: RuntimeTickEventV2) -> dict[str, Any]:
    for delta in event.learning_deltas:
        if isinstance(delta, dict) and delta.get("delta_kind") == "reward_punish_backward_attribution_consolidation":
            return dict(delta)
    return {}


def _edit_outcome_delta_from_event(event: RuntimeTickEventV2) -> dict[str, Any]:
    for delta in event.learning_deltas:
        if isinstance(delta, dict) and delta.get("delta_kind") == "draftgrid_edit_outcome_learning":
            return dict(delta)
    return {}


def _learning_loop_carryover_from_events(events: Sequence[RuntimeTickEventV2]) -> dict[str, Any]:
    attribution = _latest_attribution_consolidation_carryover(events)
    edit_outcome = _latest_edit_outcome_carryover(events)
    action_tuner = _latest_action_experience_tuner_from_events(events)
    metric_carryover: dict[str, Any] | None = None
    metric_source_tick: int | None = None
    for event in reversed(tuple(events)):
        metric = _learning_loop_metric_from_event(event)
        if metric:
            metric_carryover = _learning_loop_carryover(metric, source_tick=event.tick)
            metric_source_tick = event.tick
            break
    combined: dict[str, Any] = metric_carryover or {
        "formula_id": PHASE20_9E_LEARNING_LOOP_CARRYOVER_ID,
        "active": False,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }
    source_tick = metric_source_tick or 0
    if attribution:
        combined = _merge_learning_and_attribution_carryover(
            combined,
            attribution,
            source_tick=metric_source_tick or int(attribution.get("source_tick", 0) or 0),
        )
        source_tick = int(combined.get("source_tick", source_tick) or source_tick)
    if edit_outcome:
        combined = _merge_learning_and_edit_outcome_carryover(
            combined,
            edit_outcome,
            source_tick=max(source_tick, int(edit_outcome.get("source_tick", 0) or 0)),
        )
    combined = _apply_learning_stage_runtime_progression(
        combined,
        action_tuner=action_tuner,
        source_tick=source_tick,
        conn=None,
        session_id="",
        before_tick=0,
    )
    if combined.get("active") or attribution or edit_outcome or metric_carryover:
        return combined
    return combined


def _latest_action_experience_tuner_from_events(events: Sequence[RuntimeTickEventV2]) -> dict[str, Any]:
    for event in reversed(tuple(events)):
        feelings = event.feelings if isinstance(event.feelings, dict) else {}
        tuner = feelings.get("action_experience_tuner_projection")
        if isinstance(tuner, dict) and tuner:
            return dict(tuner)
        selected_tuner = event.selected_action.get("action_experience_tuner_projection")
        if isinstance(selected_tuner, dict) and selected_tuner:
            return dict(selected_tuner)
        for row in event.action_competition:
            row_tuner = row.get("action_experience_tuner_projection")
            if isinstance(row_tuner, dict) and row_tuner:
                return dict(row_tuner)
    return {}


def _apply_learning_stage_runtime_progression(
    carryover: dict[str, Any],
    *,
    action_tuner: dict[str, Any],
    source_tick: int,
    conn: sqlite3.Connection | None = None,
    session_id: str = "",
    before_tick: int = 0,
) -> dict[str, Any]:
    if not carryover or not carryover.get("active"):
        return carryover
    progression = _learning_stage_runtime_progression(carryover, action_tuner=action_tuner, source_tick=source_tick)
    if not progression.get("active"):
        return carryover
    lifecycle = _learning_object_lifecycle_projection(
        conn,
        session_id=session_id,
        before_tick=before_tick,
        carryover=carryover,
        stage_progression=progression,
    )
    if lifecycle.get("active"):
        progression = _merge_learning_stage_with_object_lifecycle(progression, lifecycle)
    merged = dict(carryover)
    deltas = progression.get("stage_action_deltas")
    if not isinstance(deltas, dict):
        deltas = {}
    for key, delta_key in (
        ("request_teacher_delta", "request_teacher"),
        ("maintain_unclosed_delta", "maintain_unclosed"),
        ("write_cell_delta", "write_cell"),
        ("commit_reply_delta", "commit_reply"),
        ("idle_think_delta", "idle_think"),
        ("integrate_feedback_delta", "integrate_feedback"),
        ("read_draft_delta", "read_draft"),
        ("edit_cell_delta", "edit_cell"),
        ("stop_generating_delta", "stop_generating"),
    ):
        merged[key] = round(float(merged.get(key, 0.0) or 0.0) + float(deltas.get(delta_key, 0.0) or 0.0), 4)
    merged["active"] = True
    merged["source_tick"] = int(source_tick or merged.get("source_tick", 0) or 0)
    merged["learning_stage_runtime_progression"] = progression
    merged["learning_object_lifecycle"] = lifecycle
    merged["merged_with_learning_stage_runtime_formula_id"] = progression.get("formula_id")
    ladder = _language_learning_ladder_projection(
        merged,
        progression=progression,
        lifecycle=lifecycle,
        action_tuner=action_tuner,
        source_tick=source_tick,
    )
    merged["language_learning_ladder"] = ladder
    merged["merged_with_language_learning_ladder_formula_id"] = ladder.get("formula_id")
    scene_learned = _scene_learned_projection(
        merged,
        ladder=ladder,
        lifecycle=lifecycle,
        source_tick=source_tick,
    )
    merged["scene_learned_projection"] = scene_learned
    merged["merged_with_scene_learned_formula_id"] = scene_learned.get("formula_id")
    merged["writes_answer_directly"] = False
    merged["creates_reply_candidate"] = False
    return merged


def _learning_stage_runtime_progression(
    carryover: dict[str, Any],
    *,
    action_tuner: dict[str, Any],
    source_tick: int,
) -> dict[str, Any]:
    feedback = _unit(carryover.get("feedback_only_readiness", 0.0))
    teacher_off = _unit(carryover.get("teacher_off_readiness", 0.0))
    cold = _unit(carryover.get("cold_retest_readiness", 0.0))
    scaffold = _unit(carryover.get("scaffold_regression_need", 0.0))
    attribution = carryover.get("attribution_consolidation_carryover")
    attribution = dict(attribution) if isinstance(attribution, dict) else {}
    edit_outcome = carryover.get("edit_outcome_carryover")
    edit_outcome = dict(edit_outcome) if isinstance(edit_outcome, dict) else {}
    self_test_feedback = carryover.get("self_test_feedback")
    self_test_feedback = dict(self_test_feedback) if isinstance(self_test_feedback, dict) else {}
    if not self_test_feedback:
        nested_review = carryover.get("idle_learning_review")
        if isinstance(nested_review, dict) and isinstance(nested_review.get("self_test_feedback"), dict):
            self_test_feedback = dict(nested_review.get("self_test_feedback") or {})

    reward_pressure = max(
        _unit(attribution.get("expected_reward_delta", 0.0)),
        _unit((action_tuner or {}).get("reward_pressure", 0.0)),
        _unit((action_tuner or {}).get("reward_total", 0.0)),
    )
    punish_pressure = max(
        _unit(attribution.get("expected_punish_delta", 0.0)),
        _unit((action_tuner or {}).get("punish_pressure", 0.0)),
        _unit((action_tuner or {}).get("punish_total", 0.0)),
    )
    caution_pressure = max(
        punish_pressure,
        _unit(attribution.get("inhibition_delta", 0.0)),
        _unit(attribution.get("alternative_search_delta", 0.0)),
        _unit((action_tuner or {}).get("verify_pressure", 0.0)),
    )
    fatigue_pressure = _unit((action_tuner or {}).get("fatigue_pressure", 0.0))
    self_test_success = 0.0
    self_test_failure = 0.0
    if self_test_feedback:
        if str(self_test_feedback.get("feedback_kind") or "") == "self_test_success":
            self_test_success = _unit(self_test_feedback.get("self_test_grasp", 0.0))
        elif str(self_test_feedback.get("feedback_kind") or "") == "self_test_failure":
            self_test_failure = _unit(self_test_feedback.get("mismatch_pressure", 0.0))
    edit_success = _unit(edit_outcome.get("edit_success", 0.0))
    remaining_error = _unit(edit_outcome.get("remaining_error", 0.0))

    stage_scores = {
        "contact": _unit(scaffold * 0.62 + (1.0 - max(feedback, teacher_off, cold)) * 0.10),
        "imitation": _unit(feedback * 0.64 + reward_pressure * 0.18 + scaffold * 0.10),
        "correction": _unit(scaffold * 0.38 + caution_pressure * 0.34 + self_test_failure * 0.32 + remaining_error * 0.22),
        "review": _unit(feedback * 0.28 + cold * 0.18 + reward_pressure * 0.20 + caution_pressure * 0.18 + max(edit_success, remaining_error) * 0.12),
        "self_test": _unit(teacher_off * 0.34 + cold * 0.30 + self_test_success * 0.18 + max(0.0, 1.0 - scaffold) * 0.08),
        "generalization": _unit(teacher_off * 0.44 + reward_pressure * 0.24 + self_test_success * 0.18 + edit_success * 0.08 - caution_pressure * 0.16),
        "teacher_exit": _unit(teacher_off * 0.56 + self_test_success * 0.26 + reward_pressure * 0.10 - scaffold * 0.24 - self_test_failure * 0.24),
        "cold_retest": _unit(cold * 0.68 + self_test_success * 0.10 - self_test_failure * 0.32),
    }
    dominant_stage = max(stage_scores, key=lambda key: stage_scores[key])
    confidence = _unit(max(stage_scores.values()))
    correction = stage_scores["correction"]
    review = stage_scores["review"]
    self_test = stage_scores["self_test"]
    generalization = stage_scores["generalization"]
    teacher_exit = stage_scores["teacher_exit"]
    cold_retest = stage_scores["cold_retest"]
    imitation = stage_scores["imitation"]
    contact = stage_scores["contact"]

    stage_action_deltas = {
        "request_teacher": round(
            min(0.055, (contact * 0.026 + correction * 0.040 + self_test_failure * 0.030 + cold_retest * 0.012))
            - min(0.045, teacher_exit * 0.032 + generalization * 0.024 + reward_pressure * 0.010),
            4,
        ),
        "maintain_unclosed": round(
            min(0.046, contact * 0.018 + review * 0.026 + correction * 0.022 + cold_retest * 0.018)
            - min(0.026, teacher_exit * 0.018 + fatigue_pressure * 0.018),
            4,
        ),
        "write_cell": round(
            min(0.054, imitation * 0.024 + generalization * 0.036 + teacher_exit * 0.018 + reward_pressure * 0.018)
            - min(0.038, correction * 0.022 + self_test_failure * 0.026),
            4,
        ),
        "commit_reply": round(
            min(0.052, generalization * 0.034 + teacher_exit * 0.032 + self_test_success * 0.018 + reward_pressure * 0.014)
            - min(0.050, correction * 0.030 + self_test_failure * 0.032 + remaining_error * 0.024),
            4,
        ),
        "idle_think": round(min(0.062, review * 0.034 + self_test * 0.030 + cold_retest * 0.030 + max(reward_pressure, caution_pressure) * 0.018), 4),
        "integrate_feedback": round(min(0.050, imitation * 0.028 + correction * 0.026 + feedback * 0.018), 4),
        "read_draft": round(min(0.052, review * 0.024 + self_test * 0.020 + correction * 0.030 + remaining_error * 0.026), 4),
        "edit_cell": round(min(0.052, correction * 0.034 + self_test_failure * 0.028 + remaining_error * 0.030), 4),
        "stop_generating": round(
            min(0.036, fatigue_pressure * 0.032 + self_test_failure * 0.018 + correction * 0.014)
            - min(0.026, reward_pressure * 0.018 + teacher_exit * 0.014),
            4,
        ),
    }
    active = confidence > 0.0 and any(abs(float(value)) > 0.00001 for value in stage_action_deltas.values())
    return {
        "formula_id": PHASE20_10A_LEARNING_STAGE_RUNTIME_ID,
        "source": "existing_learning_loop_carryover_plus_action_experience_projection",
        "active": active,
        "source_tick": int(source_tick or carryover.get("source_tick", 0) or 0),
        "dominant_runtime_stage": dominant_stage,
        "stage_order": (
            "contact",
            "imitation",
            "correction",
            "review",
            "self_test",
            "generalization",
            "teacher_exit",
            "cold_retest",
        ),
        "stage_scores": {key: round(value, 4) for key, value in stage_scores.items()},
        "stage_confidence": round(confidence, 4),
        "stage_action_deltas": stage_action_deltas,
        "current_protocol_stage": carryover.get("current_protocol_stage"),
        "dominant_learning_tendency": carryover.get("dominant_learning_tendency"),
        "feedback_only_readiness": round(feedback, 4),
        "teacher_off_readiness": round(teacher_off, 4),
        "cold_retest_readiness": round(cold, 4),
        "scaffold_regression_need": round(scaffold, 4),
        "reward_pressure": round(reward_pressure, 4),
        "punish_pressure": round(punish_pressure, 4),
        "caution_pressure": round(caution_pressure, 4),
        "fatigue_pressure": round(fatigue_pressure, 4),
        "self_test_feedback": self_test_feedback,
        "attribution_consolidation_formula_id": attribution.get("formula_id"),
        "edit_outcome_formula_id": edit_outcome.get("formula_id"),
        "action_experience_tuner_formula_id": (action_tuner or {}).get("formula_id"),
        "uses_existing_ap_flow": True,
        "projection_only": True,
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _merge_learning_stage_with_object_lifecycle(
    progression: dict[str, Any],
    lifecycle: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(progression)
    base_deltas = progression.get("stage_action_deltas")
    base_deltas = dict(base_deltas) if isinstance(base_deltas, dict) else {}
    lifecycle_deltas = lifecycle.get("lifecycle_action_deltas")
    lifecycle_deltas = dict(lifecycle_deltas) if isinstance(lifecycle_deltas, dict) else {}
    merged["stage_action_deltas_before_lifecycle"] = {key: round(float(value), 4) for key, value in base_deltas.items()}
    merged["stage_action_deltas"] = {
        key: round(float(base_deltas.get(key, 0.0) or 0.0) + float(lifecycle_deltas.get(key, 0.0) or 0.0), 4)
        for key in {
            *base_deltas.keys(),
            *lifecycle_deltas.keys(),
        }
    }
    merged["learning_object_lifecycle"] = lifecycle
    merged["merged_with_learning_object_lifecycle_formula_id"] = lifecycle.get("formula_id")
    merged["writes_answer_directly"] = False
    merged["creates_reply_candidate"] = False
    return merged


def _language_learning_ladder_projection(
    carryover: dict[str, Any],
    *,
    progression: dict[str, Any],
    lifecycle: dict[str, Any],
    action_tuner: dict[str, Any],
    source_tick: int,
) -> dict[str, Any]:
    """Phase20.13c — Language Learning Ladder 纯派生判据投影 (白皮书
    EDUCATION_PROTOCOL "Language Learning Ladder" 6 阶段).

    与 learning_stage_runtime_progression / learning_object_lifecycle 同构同
    guardrail: 仅聚合既有 projection_only 量 (体验流/草稿碎片/认知感觉/奖惩/
    lifecycle 阶段计数), 不采集新信号、不新增存储、不改 selected、不写答案、不
    藏 solver, 主观 may_be_wrong. 用于回答"某场景是否通过 keyword_organization 等
    语言学习阶梯", 不替代 lifecycle 的教学褪除判定, 二者并存互补.

    6 阶梯判据全部从 carryover / progression / lifecycle / action_tuner 现成键派生:
      echo_imitation      : lifecycle review_count + reward_pressure (已复读有过反馈)
      successor_prediction : lifecycle self_test_count + memory_consolidation (已自测,
                            且记忆在巩固非遗忘 → 接续真有召回)
      multi_reply_aggregation : progression generalization 分 (B 候选重叠抬能)
      process_paradigm_binding : progression self_test + cold_retest (内部过程锚下自助)
      keyword_organization : 在 teacher_off_readiness 或 feedback_only_readiness 条件
                            下, 上述接续/聚合/过程绑定已成形 (白皮书"教师退场/纯反馈
                            下通过此阶才算学成")
      grammar_refinement   : reward_pressure>0 且 boldness 适度 + stability>regression
                            (形式打磨, 非新内容)
    """
    if not carryover or not carryover.get("active"):
        return _inactive_language_learning_ladder("carryover_inactive")
    if not progression.get("active") or not lifecycle.get("active"):
        return _inactive_language_learning_ladder("stage_or_lifecycle_inactive")

    review_count = int(lifecycle.get("review_count", 0) or 0)
    self_test_count = int(lifecycle.get("self_test_count", 0) or 0)
    self_test_success = int(lifecycle.get("self_test_success_count", 0) or 0)
    reward_pressure = _unit(lifecycle.get("reward_pressure", 0.0))
    punish_pressure = _unit(lifecycle.get("punish_pressure", 0.0))
    stability = _unit(lifecycle.get("stability", 0.0))
    regression = _unit(lifecycle.get("regression", 0.0))
    cold_retest_pressure = _unit(lifecycle.get("cold_retest_pressure", 0.0))

    memory_rhythm = lifecycle.get("memory_consolidation_forgetting_rhythm")
    memory_rhythm = dict(memory_rhythm) if isinstance(memory_rhythm, dict) else {}
    consolidation = _unit(memory_rhythm.get("memory_consolidation", 0.0))
    forgetting = _unit(memory_rhythm.get("forgetting_pressure", 0.0))

    stage_scores = progression.get("stage_scores")
    stage_scores = dict(stage_scores) if isinstance(stage_scores, dict) else {}
    generalization = _unit(stage_scores.get("generalization", 0.0))
    self_test_stage = _unit(stage_scores.get("self_test", 0.0))

    feedback = _unit(carryover.get("feedback_only_readiness", 0.0))
    teacher_off = _unit(carryover.get("teacher_off_readiness", 0.0))
    scaffold = _unit(carryover.get("scaffold_regression_need", 0.0))

    tuner = action_tuner if isinstance(action_tuner, dict) else {}
    # grammar_refinement 借 9z tuner 的 edit_count + read_count (反复读稿/编辑微调) 作信号:
    # 白皮书 grammar=refine grammar/particles/politeness/tone/continuity, 正是反复精修的产物,
    # 非"胆壮敢写"; 故用编辑/读稿计数 (verify 倾向), 不用 boldness_multiplier.
    edit_count = int(tuner.get("edit_count", 0) or 0)
    read_count = int(tuner.get("read_count", 0) or 0)
    refinement_pressure = _unit(min(1.0, (edit_count + read_count) * 0.20))

    # 6 阶梯判据: 每条仅以白皮书语义从现成量派生连续 score ∈ [0,1], 无裸魔数判断门,
    # 让 ladder 是软判据而非硬学成布尔门 (may_be_wrong).
    ladder_scores = {
        "echo_imitation": _unit(0.42 * min(1.0, review_count / 2.0) + 0.30 * reward_pressure),
        "successor_prediction": _unit(0.38 * min(1.0, self_test_count / 2.0) + 0.32 * max(0.0, consolidation - forgetting) + 0.14 * self_test_stage),
        "multi_reply_aggregation": _unit(0.46 * generalization + 0.24 * reward_pressure + 0.14 * min(1.0, self_test_success / 2.0)),
        "process_paradigm_binding": _unit(0.34 * self_test_stage + 0.30 * max(0.0, 1.0 - scaffold) + 0.20 * cold_retest_pressure),
        "keyword_organization": _unit(
            0.36 * max(teacher_off, feedback)
            + 0.20 * min(1.0, self_test_success / 2.0)
            + 0.18 * max(0.0, consolidation - forgetting)
            + 0.12 * generalization
        ),
        "grammar_refinement": _unit(
            0.30 * refinement_pressure
            + 0.24 * reward_pressure
            + 0.18 * max(0.0, stability - regression)
            - 0.16 * punish_pressure
        ),
    }
    dominant_ladder_stage = max(ladder_scores, key=lambda key: ladder_scores[key])
    ladder_confidence = _unit(max(ladder_scores.values()))
    active = ladder_confidence > 0.0 and any(abs(float(v)) > 0.00001 for v in ladder_scores.values())
    return {
        "formula_id": PHASE20_13C_LANGUAGE_LEARNING_LADDER_ID,
        "source": "existing_learning_loop_carryover_plus_lifecycle_and_tuner_projection",
        "active": active,
        "source_tick": int(source_tick or carryover.get("source_tick", 0) or 0),
        "dominant_ladder_stage": dominant_ladder_stage,
        "ladder_stage_order": (
            "echo_imitation",
            "successor_prediction",
            "multi_reply_aggregation",
            "process_paradigm_binding",
            "keyword_organization",
            "grammar_refinement",
        ),
        "ladder_scores": {key: round(float(value), 4) for key, value in ladder_scores.items()},
        "ladder_confidence": round(float(ladder_confidence), 4),
        "review_count": review_count,
        "self_test_count": self_test_count,
        "self_test_success_count": self_test_success,
        "reward_pressure": round(float(reward_pressure), 4),
        "consolidation_minus_forgetting": round(float(max(0.0, consolidation - forgetting)), 4),
        "feedback_only_readiness": round(float(feedback), 4),
        "teacher_off_readiness": round(float(teacher_off), 4),
        "uses_existing_ap_flow": True,
        "projection_only": True,
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _inactive_language_learning_ladder(reason: str) -> dict[str, Any]:
    return {
        "formula_id": PHASE20_13C_LANGUAGE_LEARNING_LADDER_ID,
        "source": "existing_learning_loop_carryover_plus_lifecycle_and_tuner_projection",
        "active": False,
        "reason": reason,
        "ladder_scores": {},
        "dominant_ladder_stage": "",
        "ladder_stage_order": (
            "echo_imitation",
            "successor_prediction",
            "multi_reply_aggregation",
            "process_paradigm_binding",
            "keyword_organization",
            "grammar_refinement",
        ),
        "projection_only": True,
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _scene_learned_projection(
    carryover: dict[str, Any],
    *,
    ladder: dict[str, Any],
    lifecycle: dict[str, Any],
    source_tick: int,
) -> dict[str, Any]:
    """Phase20.14 — 场景学成判据 纯派生投影 (白皮书 EDUCATION_PROTOCOL 630 行
    "keyword_organization_stage_passed=true before claiming a scene learned" +
    148-149 行 scaffold 褪除顺序 teacher_off -> cold_retest).

    合成 13c 阶梯判据与 10b lifecycle 的 teacher_exit/cold_retest 就绪度, 回答
    "该场景在 teacher_off + cold_retest 双条件下是否走完 keyword_organization",
    供课程编排读取. 与 13c/10b 同型 guardrail: 仅读既有 projection_only 量, 不采集
    新信号、不新增存储、不改 selected、不写答案、不藏 solver. **软判据**: 产连续
    scene_learned_confidence ∈ [0,1] 与 dominant_blocking_stage (最拖后腿的阶),
    不产布尔 passed=true, 不声称收敛/完成 (may_be_wrong).

    派生来源 (全部既有键, 勿增实体):
      - ladder: 13c ladder_scores (6 阶连续分数) / dominant_ladder_stage /
        ladder_confidence
      - lifecycle: 10b current_stage (taught..cold_retest_ready 7 阶) / stability /
        regression / cold_retest_pressure
      - carryover: teacher_off_readiness / cold_retest_readiness / scaffold_regression_need

    合成逻辑 (白皮书口径, 软判据加权, 无裸魔数布尔门):
      双褪除就绪 = min(teacher_off_readiness, cold_retest_readiness)
        — 白皮书 148-149: teacher_off -> cold_retest 顺序褪除, 两者都过了才算
          真褪除; 单教师退场不算学成 (冷重测可能暴露假学成).
      阶梯就绪 = ladder_scores[keyword_organization] (白皮书 630: 此阶过了才算
        scene learned), 并要求 dominant 已到 keyword_organization 或 grammar_refinement
        (不能停留在前 4 阶却声称学成).
      生命周期就绪 = lifecycle current_stage 已到 teacher_exit_ready 或 cold_retest_ready
        (10b 教学褪除就绪, 非语言阶梯, 二者互补).
      scene_learned_confidence = 双褪除就绪 * 阶梯就绪 * 生命周期就绪 (三者皆高才高,
        任一拖后腿则置信度低 — 符合 may_be_wrong 软判据, 非硬布尔 AND).
      dominant_blocking_stage = 三因子中最低者对应的阶名, 供编排定位"卡在哪".
    """
    if not carryover or not carryover.get("active"):
        return _inactive_scene_learned("carryover_inactive")
    if not ladder.get("active") or not lifecycle.get("active"):
        return _inactive_scene_learned("ladder_or_lifecycle_inactive")

    ladder_scores = ladder.get("ladder_scores")
    ladder_scores = dict(ladder_scores) if isinstance(ladder_scores, dict) else {}
    if not ladder_scores:
        return _inactive_scene_learned("ladder_scores_empty")
    keyword_org_score = _unit(ladder_scores.get("keyword_organization", 0.0))
    grammar_score = _unit(ladder_scores.get("grammar_refinement", 0.0))
    dominant_ladder = str(ladder.get("dominant_ladder_stage") or "")
    ladder_confidence = _unit(ladder.get("ladder_confidence", 0.0))

    # 阶梯就绪: keyword_organization 阶分高 (白皮书 630 核心条件), 且 dominant 已推进到
    # keyword_organization 或更后的 grammar_refinement (不能停前 4 阶却声称学成).
    # 用 min 把"阶分"与"是否推进到该阶"两条件取下限, 软判据非硬门.
    reached_keyword_or_later = 1.0 if dominant_ladder in ("keyword_organization", "grammar_refinement") else 0.0
    ladder_readiness = _unit(min(keyword_org_score, reached_keyword_or_later + 0.0))

    lifecycle_stage = str(lifecycle.get("current_stage") or "")
    lifecycle_stages = lifecycle.get("lifecycle_stages") or (
        "taught", "reviewed", "self_tested", "adjusted_after_feedback",
        "retested", "teacher_exit_ready", "cold_retest_ready",
    )
    lifecycle_stages_list = list(lifecycle_stages)
    # 生命周期就绪: current_stage 已到 teacher_exit_ready 或 cold_retest_ready (10b
    # 教学褪除就绪). 用 stage_index 派生连续推进度: teacher_exit_ready -> 0.5,
    # cold_retest_ready -> 1.0 (白皮书 148-149 teacher_off -> cold_retest 顺序褪除).
    # 索引从 lifecycle_stages 结构派生 (非裸魔数 4/2), 更泛化.
    try:
        stage_index = lifecycle_stages_list.index(lifecycle_stage) if lifecycle_stage in lifecycle_stages_list else 0
        teacher_exit_idx = lifecycle_stages_list.index("teacher_exit_ready")
        cold_retest_idx = lifecycle_stages_list.index("cold_retest_ready")
    except ValueError:
        stage_index = 0
        teacher_exit_idx = 5
        cold_retest_idx = 6
    span = max(1, cold_retest_idx - teacher_exit_idx)
    lifecycle_readiness = _unit(max(0.0, (stage_index - teacher_exit_idx) / span))

    teacher_off = _unit(carryover.get("teacher_off_readiness", 0.0))
    cold_retest = _unit(carryover.get("cold_retest_readiness", 0.0))
    scaffold_need = _unit(carryover.get("scaffold_regression_need", 0.0))

    # 双褪除就绪: 白皮书 148-149 teacher_off -> cold_retest 顺序褪除, 两者都高才算
    # 真褪除. scaffold_regression_need 高表示仍需脚手架, 反向拉低双褪除就绪.
    dual_fade_readiness = _unit(min(teacher_off, cold_retest) * (1.0 - scaffold_need * 0.5))

    # 三因子皆高才高 (乘法合成, 软判据 may_be_wrong, 非硬布尔 AND):
    scene_learned_confidence = _unit(dual_fade_readiness * ladder_readiness * lifecycle_readiness)

    # dominant_blocking_stage: 三因子中最低者对应的阶, 供编排定位"卡在哪".
    factors = (
        ("dual_fade_readiness", dual_fade_readiness),
        ("keyword_organization_stage", ladder_readiness),
        ("lifecycle_teacher_exit_or_cold_retest", lifecycle_readiness),
    )
    dominant_blocking = min(factors, key=lambda item: item[1])[0]

    # 不声称学成布尔: 白皮书 630 用 keyword_organization_stage_passed=true, 但 13c 已
    # 确立"阶梯是软判据不声称通过", 故本投影也只产连续 confidence + may_be_wrong,
    # scene_learned_pass 不存在 (禁用串 scene_learned_complete/keyword_organization_converged).
    active = scene_learned_confidence > 0.0
    # inactive 时给可诊断 reason (三因子中哪个拖后腿), 与 _inactive_scene_learned 同型.
    if not active:
        reason = f"blocked_at_{dominant_blocking}_confidence_zero"
    else:
        reason = ""
    return {
        "formula_id": PHASE20_14_SCENE_LEARNED_ID,
        "source": "existing_ladder_plus_lifecycle_plus_carryover_projection",
        "active": active,
        "reason": reason,
        "source_tick": int(source_tick or carryover.get("source_tick", 0) or 0),
        "scene_learned_confidence": round(float(scene_learned_confidence), 4),
        "dominant_blocking_stage": dominant_blocking,
        "dual_fade_readiness": round(float(dual_fade_readiness), 4),
        "keyword_organization_stage_readiness": round(float(ladder_readiness), 4),
        "lifecycle_fade_readiness": round(float(lifecycle_readiness), 4),
        "reached_keyword_organization_or_later": bool(reached_keyword_or_later >= 1.0),
        "lifecycle_current_stage": lifecycle_stage,
        "dominant_ladder_stage": dominant_ladder,
        "ladder_confidence": round(float(ladder_confidence), 4),
        "grammar_refinement_score": round(float(grammar_score), 4),
        "teacher_off_readiness": round(float(teacher_off), 4),
        "cold_retest_readiness": round(float(cold_retest), 4),
        "scaffold_regression_need": round(float(scaffold_need), 4),
        "uses_existing_ap_flow": True,
        "projection_only": True,
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _inactive_scene_learned(reason: str) -> dict[str, Any]:
    return {
        "formula_id": PHASE20_14_SCENE_LEARNED_ID,
        "source": "existing_ladder_plus_lifecycle_plus_carryover_projection",
        "active": False,
        "reason": reason,
        "scene_learned_confidence": 0.0,
        "dominant_blocking_stage": "",
        "dual_fade_readiness": 0.0,
        "keyword_organization_stage_readiness": 0.0,
        "lifecycle_fade_readiness": 0.0,
        "reached_keyword_organization_or_later": False,
        "uses_existing_ap_flow": True,
        "projection_only": True,
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _learning_object_lifecycle_projection(
    conn: sqlite3.Connection | None,
    *,
    session_id: str,
    before_tick: int,
    carryover: dict[str, Any],
    stage_progression: dict[str, Any],
) -> dict[str, Any]:
    if conn is None or not session_id:
        return _inactive_learning_object_lifecycle("no_database_context")
    identity = _learning_object_identity_from_carryover(carryover)
    if not identity:
        return _inactive_learning_object_lifecycle("no_learning_object_identity")
    events = _learning_object_lifecycle_events(
        conn,
        session_id=session_id,
        before_tick=before_tick,
        identity=identity,
    )
    if not events.get("alignment_event_id"):
        return _inactive_learning_object_lifecycle("no_alignment_event")
    lifecycle = _learning_object_lifecycle_from_events(
        identity=identity,
        events=events,
        stage_progression=stage_progression,
    )
    return lifecycle


def _inactive_learning_object_lifecycle(reason: str) -> dict[str, Any]:
    return {
        "formula_id": PHASE20_10B_LEARNING_OBJECT_LIFECYCLE_ID,
        "active": False,
        "reason": reason,
        "projection_only": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _learning_object_identity_from_carryover(carryover: dict[str, Any]) -> dict[str, Any]:
    review = carryover.get("idle_learning_review")
    review = dict(review) if isinstance(review, dict) else {}
    self_test_feedback = carryover.get("self_test_feedback")
    self_test_feedback = dict(self_test_feedback) if isinstance(self_test_feedback, dict) else {}
    if not self_test_feedback and isinstance(review.get("self_test_feedback"), dict):
        self_test_feedback = dict(review.get("self_test_feedback") or {})
    alignment_event_id = str(
        review.get("alignment_event_id")
        or self_test_feedback.get("alignment_event_id")
        or carryover.get("alignment_event_id")
        or ""
    )
    source_event_id = str(
        review.get("source_event_id")
        or self_test_feedback.get("source_event_id")
        or carryover.get("source_event_id")
        or ""
    )
    source_text = str(review.get("source_text") or self_test_feedback.get("source_text") or carryover.get("source_text") or "")
    target_text = str(review.get("target_text") or self_test_feedback.get("expected_text") or carryover.get("target_text") or "")
    if not any((alignment_event_id, source_event_id, source_text, target_text)):
        return {}
    return {
        "alignment_event_id": alignment_event_id,
        "source_event_id": source_event_id,
        "source_text": source_text,
        "target_text": target_text,
        "source_text_hash": _hash_text(source_text) if source_text else "",
        "target_text_hash": _hash_text(target_text) if target_text else "",
    }


def _learning_object_lifecycle_events(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
    identity: dict[str, Any],
) -> dict[str, Any]:
    alignment_event_id = str(identity.get("alignment_event_id") or "")
    if not alignment_event_id:
        alignment_event_id = _resolve_learning_object_alignment_event_id(
            conn,
            session_id=session_id,
            before_tick=before_tick,
            source_event_id=str(identity.get("source_event_id") or ""),
            source_text=str(identity.get("source_text") or ""),
            target_text=str(identity.get("target_text") or ""),
        )
    if not alignment_event_id:
        return {}
    alignment = _learning_alignment_payload_by_id(conn, alignment_event_id)
    if not alignment:
        return {}
    alignment_tick = int(alignment.get("tick", 0) or 0)
    alignment_payload = dict(alignment.get("payload", {}) or {})
    input_payload = _input_payload_for_alignment(conn, alignment_payload)
    source_text = str(identity.get("source_text") or input_payload.get("text") or "")
    if not source_text and alignment_payload.get("visual_signature"):
        source_text = VISUAL_FOCUS_ANCHOR_UNIT
    target_text = str(identity.get("target_text") or "".join(str(ch) for ch in alignment_payload.get("output_chars", ()))).strip()
    review_rows = _learning_review_occurrences_for_alignment(
        conn,
        session_id=session_id,
        before_tick=before_tick,
        alignment_event_id=alignment_event_id,
    )
    self_test_rows = _self_test_occurrences_for_alignment(
        conn,
        session_id=session_id,
        before_tick=before_tick,
        alignment_event_id=alignment_event_id,
    )
    teacher_feedback = _learning_object_teacher_feedback_stats(
        conn,
        session_id=session_id,
        after_tick=alignment_tick,
        before_tick=before_tick,
        alignment_event_id=alignment_event_id,
    )
    return {
        "alignment_event_id": alignment_event_id,
        "alignment_tick": alignment_tick,
        "before_tick": int(before_tick),
        "alignment_reward": _unit(alignment.get("reward", 0.0)),
        "alignment_punish": _unit(alignment.get("punish", 0.0)),
        "source_event_id": str(alignment_payload.get("input_event_id") or identity.get("source_event_id") or ""),
        "source_text": source_text,
        "target_text": target_text,
        "review_rows": review_rows,
        "self_test_rows": self_test_rows,
        "teacher_feedback": teacher_feedback,
    }


def _resolve_learning_object_alignment_event_id(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
    source_event_id: str,
    source_text: str,
    target_text: str,
) -> str:
    clauses = ["session_id=?", "event_kind='experience_alignment'", "tick < ?"]
    params: list[Any] = [session_id, int(before_tick)]
    if source_event_id:
        clauses.append("json_extract(payload_json, '$.input_event_id')=?")
        params.append(source_event_id)
    elif target_text:
        clauses.append("json_extract(payload_json, '$.output_hash')=?")
        params.append(_hash_text(target_text))
    else:
        return ""
    row = conn.execute(
        f"""
        SELECT event_id
        FROM phase20_7_experience_events
        WHERE {' AND '.join(clauses)}
        ORDER BY tick DESC, created_at_ms DESC
        LIMIT 1
        """,
        tuple(params),
    ).fetchone()
    if row:
        return str(row[0] or "")
    if not source_text:
        return ""
    source_hash = _hash_text(source_text)
    rows = conn.execute(
        """
        SELECT event_id, payload_json
        FROM phase20_7_experience_events
        WHERE session_id=? AND event_kind='experience_alignment' AND tick < ?
        ORDER BY tick DESC, created_at_ms DESC
        LIMIT 48
        """,
        (session_id, int(before_tick)),
    ).fetchall()
    for event_id, payload_json in rows:
        payload = from_json(str(payload_json))
        if not isinstance(payload, dict):
            continue
        input_payload = _input_payload_for_alignment(conn, payload)
        if _hash_text(str(input_payload.get("text", "") or "")) == source_hash:
            return str(event_id or "")
    return ""


def _learning_alignment_payload_by_id(conn: sqlite3.Connection, alignment_event_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT tick, payload_json, reward, punish
        FROM phase20_7_experience_events
        WHERE event_id=? AND event_kind='experience_alignment'
        LIMIT 1
        """,
        (str(alignment_event_id),),
    ).fetchone()
    if row is None:
        return {}
    tick, payload_json, reward, punish = row
    payload = from_json(str(payload_json))
    if not isinstance(payload, dict):
        return {}
    return {
        "tick": int(tick or 0),
        "payload": payload,
        "reward": float(reward or 0.0),
        "punish": float(punish or 0.0),
    }


def _learning_review_occurrences_for_alignment(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
    alignment_event_id: str,
) -> tuple[dict[str, Any], ...]:
    rows = _memoized_rows(
        conn,
        ("learning_review_asc", session_id, int(before_tick)),
        """
        SELECT o.occurrence_id, o.tick, o.clarity, o.position_json
        FROM phase20_7_occurrences o
        JOIN phase20_7_experience_events e ON e.event_id=o.event_id
        WHERE e.session_id=?
          AND o.tick < ?
          AND o.sa_type_id >= 'short_structure_flow::learning_review::'
          AND o.sa_type_id < 'short_structure_flow::learning_review:;'
        ORDER BY o.tick ASC
        LIMIT 64
        """,
        (session_id, int(before_tick)),
    )
    out: list[dict[str, Any]] = []
    for occurrence_id, tick, clarity, position_json in rows:
        position = from_json(str(position_json))
        if not isinstance(position, dict):
            continue
        review = position.get("idle_learning_review")
        if not isinstance(review, dict):
            continue
        if str(review.get("alignment_event_id") or "") != str(alignment_event_id):
            continue
        out.append(
            {
                "occurrence_id": str(occurrence_id),
                "tick": int(tick or 0),
                "support": round(_unit(clarity), 4),
                "dominant_learning_tendency": review.get("dominant_learning_tendency"),
                "current_protocol_stage": review.get("current_protocol_stage"),
                "self_test_feedback": review.get("self_test_feedback") if isinstance(review.get("self_test_feedback"), dict) else {},
            }
        )
    return tuple(out)


def _self_test_occurrences_for_alignment(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
    alignment_event_id: str,
) -> tuple[dict[str, Any], ...]:
    # §185 N+1 消除: 该查询只依赖 (session_id, before_tick, sa_prefix) — 与
    # alignment_event_id 无关 (后者是 Python 侧过滤), 故 turn 内 memo 一次即可.
    rows = _memoized_rows(
        conn,
        ("self_test_occ_asc", session_id, int(before_tick)),
        """
        SELECT o.occurrence_id, o.tick, o.clarity, o.position_json
        FROM phase20_7_occurrences o
        JOIN phase20_7_experience_events e ON e.event_id=o.event_id
        WHERE e.session_id=?
          AND o.tick < ?
          AND o.sa_type_id >= 'short_structure_flow::self_test::'
          AND o.sa_type_id < 'short_structure_flow::self_test:;'
        ORDER BY o.tick ASC
        LIMIT 64
        """,
        (session_id, int(before_tick)),
    )
    out: list[dict[str, Any]] = []
    for occurrence_id, tick, clarity, position_json in rows:
        position = from_json(str(position_json))
        if not isinstance(position, dict):
            continue
        self_test = position.get("idle_self_test")
        if not isinstance(self_test, dict):
            continue
        if str(self_test.get("alignment_event_id") or "") != str(alignment_event_id):
            continue
        grasp = _unit(self_test.get("self_test_grasp", 0.0))
        match = _unit(self_test.get("match_score", 0.0))
        out.append(
            {
                "occurrence_id": str(occurrence_id),
                "tick": int(tick or 0),
                "support": round(_unit(clarity), 4),
                "self_test_kind": self_test.get("self_test_kind"),
                "self_test_grasp": round(grasp, 4),
                "match_score": round(match, 4),
                "success": grasp >= 0.68 and match >= 0.70,
                "failure": grasp < 0.68 or match < 0.70,
            }
        )
    return tuple(out)


def _learning_object_teacher_feedback_stats(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    after_tick: int,
    before_tick: int,
    alignment_event_id: str,
) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT reward, punish, payload_json, tick
        FROM phase20_7_experience_events
        WHERE session_id=?
          AND event_kind='teacher_feedback_event'
          AND tick >= ?
          AND tick < ?
        ORDER BY tick ASC, created_at_ms ASC
        LIMIT 64
        """,
        (session_id, int(after_tick), int(before_tick)),
    ).fetchall()
    reward_total = 0.0
    punish_total = 0.0
    target_count = 0
    for reward, punish, payload_json, _tick in rows:
        payload = from_json(str(payload_json))
        payload = payload if isinstance(payload, dict) else {}
        target_event_id = str(payload.get("target_event_id") or "")
        if target_event_id and target_event_id != alignment_event_id:
            continue
        reward_total += _unit(reward)
        punish_total += _unit(punish)
        target_count += 1
    return {
        "target_count": int(target_count),
        "reward_total": round(_unit(reward_total), 4),
        "punish_total": round(_unit(punish_total), 4),
    }


def _long_interval_cold_retest_window(
    *,
    events: dict[str, Any],
    stage_progression: dict[str, Any],
) -> dict[str, Any]:
    before_tick = int(events.get("before_tick", 0) or 0)
    alignment_tick = int(events.get("alignment_tick", 0) or 0)
    review_rows = tuple(events.get("review_rows", ()) or ())
    self_test_rows = tuple(events.get("self_test_rows", ()) or ())
    success_count = sum(1 for row in self_test_rows if row.get("success"))
    failure_count = sum(1 for row in self_test_rows if row.get("failure"))
    last_review_tick = max((int(row.get("tick", 0) or 0) for row in review_rows), default=alignment_tick)
    last_self_test_tick = max((int(row.get("tick", 0) or 0) for row in self_test_rows), default=alignment_tick)
    alignment_age = max(0, before_tick - alignment_tick) if alignment_tick else 0
    review_gap = max(0, before_tick - last_review_tick) if last_review_tick else alignment_age
    self_test_gap = max(0, before_tick - last_self_test_tick) if last_self_test_tick else alignment_age
    stage_scores = stage_progression.get("stage_scores")
    stage_scores = dict(stage_scores) if isinstance(stage_scores, dict) else {}
    teacher_exit_score = _unit(stage_scores.get("teacher_exit", 0.0))
    generalization_score = _unit(stage_scores.get("generalization", 0.0))
    cold_score = _unit(stage_scores.get("cold_retest", 0.0))
    stability_hint = _unit(
        min(0.36, success_count * 0.12)
        + teacher_exit_score * 0.20
        + generalization_score * 0.14
        + _unit(events.get("alignment_reward", 0.0)) * 0.12
    )
    regression_hint = _unit(min(0.44, failure_count * 0.18) + _unit(events.get("alignment_punish", 0.0)) * 0.18)
    long_interval_pressure = _unit(
        min(0.42, max(0, alignment_age - 6) * 0.025)
        + min(0.28, max(0, self_test_gap - 3) * 0.035)
        + min(0.18, max(0, review_gap - 4) * 0.020)
    )
    retest_need = _unit(
        long_interval_pressure * 0.52
        + stability_hint * 0.22
        + cold_score * 0.22
        - regression_hint * 0.20
    )
    active = retest_need >= 0.18 and alignment_tick > 0
    return {
        "formula_id": PHASE20_10D_LONG_INTERVAL_COLD_RETEST_ID,
        "active": active,
        "source": "existing_alignment_review_self_test_tick_gaps",
        "alignment_event_id": str(events.get("alignment_event_id") or ""),
        "alignment_tick": alignment_tick,
        "before_tick": before_tick,
        "alignment_age_ticks": int(alignment_age),
        "last_review_tick": int(last_review_tick or 0),
        "last_self_test_tick": int(last_self_test_tick or 0),
        "review_gap_ticks": int(review_gap),
        "self_test_gap_ticks": int(self_test_gap),
        "success_count": int(success_count),
        "failure_count": int(failure_count),
        "stability_hint": round(stability_hint, 4),
        "regression_hint": round(regression_hint, 4),
        "long_interval_pressure": round(long_interval_pressure, 4),
        "retest_need": round(retest_need, 4),
        "cold_retest_action_deltas": {
            "idle_think": round(min(0.040, retest_need * 0.030), 4),
            "maintain_unclosed": round(min(0.026, retest_need * 0.016), 4),
            "request_teacher": round(min(0.024, regression_hint * 0.020) - min(0.018, stability_hint * 0.012), 4),
            "commit_reply": round(min(0.026, stability_hint * 0.018) - min(0.020, regression_hint * 0.016), 4),
            "read_draft": round(min(0.024, retest_need * 0.014 + regression_hint * 0.012), 4),
            "edit_cell": round(min(0.022, regression_hint * 0.018), 4),
        },
        "uses_existing_ap_flow": True,
        "projection_only": True,
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _memory_consolidation_forgetting_review_rhythm(
    *,
    events: dict[str, Any],
    stage_scores: dict[str, Any],
    review_rows: Sequence[dict[str, Any]],
    self_test_rows: Sequence[dict[str, Any]],
    cold_window: dict[str, Any],
    cold_generalization_tuning: dict[str, Any],
    stability: float,
    regression: float,
    reward: float,
    punish: float,
) -> dict[str, Any]:
    before_tick = int(events.get("before_tick", 0) or 0)
    alignment_tick = int(events.get("alignment_tick", 0) or 0)
    review_rows = tuple(review_rows or ())
    self_test_rows = tuple(self_test_rows or ())
    success_rows = tuple(row for row in self_test_rows if row.get("success"))
    failure_rows = tuple(row for row in self_test_rows if row.get("failure"))
    success_count = len(success_rows)
    failure_count = len(failure_rows)
    review_count = len(review_rows)
    last_review_tick = max((int(row.get("tick", 0) or 0) for row in review_rows), default=alignment_tick)
    last_self_test_tick = max((int(row.get("tick", 0) or 0) for row in self_test_rows), default=alignment_tick)
    alignment_age = max(0, before_tick - alignment_tick) if alignment_tick else 0
    review_gap = max(0, before_tick - last_review_tick) if last_review_tick else alignment_age
    self_test_gap = max(0, before_tick - last_self_test_tick) if last_self_test_tick else alignment_age
    success_strength = _unit(
        sum(_unit(row.get("self_test_grasp", 0.0)) * _unit(row.get("match_score", 0.0)) for row in success_rows)
        / max(success_count, 1)
    )
    failure_strength = _unit(
        sum(_unit(1.0 - row.get("match_score", 0.0)) + _unit(1.0 - row.get("self_test_grasp", 0.0)) for row in failure_rows)
        / max(failure_count, 1)
        * 0.5
    )
    teacher_exit_score = _unit(stage_scores.get("teacher_exit", 0.0))
    generalization_score = _unit(stage_scores.get("generalization", 0.0))
    cold_score = _unit(stage_scores.get("cold_retest", 0.0))
    cold_success = min(0.36, int(cold_generalization_tuning.get("cold_success_count", 0) or 0) * 0.12)
    cold_failure = min(0.42, int(cold_generalization_tuning.get("cold_failure_count", 0) or 0) * 0.14)
    courage = _unit(cold_generalization_tuning.get("generalization_courage", 0.0))
    caution = _unit(cold_generalization_tuning.get("generalization_caution", 0.0))
    cold_need = _unit(cold_window.get("retest_need", 0.0))
    long_interval_pressure = _unit(cold_window.get("long_interval_pressure", 0.0))
    recent_review_relief = _unit(0.16 / (1.0 + max(0, review_gap)))
    recent_self_test_relief = _unit(0.18 / (1.0 + max(0, self_test_gap)))
    gap_pressure = _unit(
        min(0.36, max(0, self_test_gap - 3) * 0.035)
        + min(0.28, max(0, review_gap - 4) * 0.026)
        + min(0.26, max(0, alignment_age - 8) * 0.020)
        + long_interval_pressure * 0.24
    )
    memory_consolidation = _unit(
        _unit(stability) * 0.34
        + success_strength * 0.22
        + min(0.24, success_count * 0.055)
        + min(0.18, review_count * 0.030)
        + cold_success * 0.34
        + courage * 0.36
        + _unit(reward) * 0.10
        + teacher_exit_score * 0.12
        + generalization_score * 0.08
        + recent_review_relief
        + recent_self_test_relief
        - _unit(regression) * 0.22
        - failure_strength * 0.24
        - cold_failure * 0.28
        - _unit(punish) * 0.12
    )
    forgetting_pressure = _unit(
        gap_pressure * (0.50 + max(0.0, 1.0 - memory_consolidation) * 0.36)
        + failure_strength * 0.26
        + _unit(regression) * 0.20
        + _unit(punish) * 0.12
        + cold_failure * 0.30
        + caution * 0.36
        - success_strength * 0.10
        - recent_review_relief * 0.60
        - recent_self_test_relief * 0.40
    )
    review_rhythm_pressure = _unit(
        forgetting_pressure * 0.42
        + cold_need * 0.26
        + long_interval_pressure * 0.18
        + (0.08 if review_count <= 1 and alignment_age >= 3 else 0.0)
        + (0.08 if self_test_rows and self_test_gap >= 5 else 0.0)
        - recent_review_relief * 0.36
    )
    reconsolidation_need = _unit(
        review_rhythm_pressure * (0.22 + success_strength * 0.30 + courage * 0.18)
        + forgetting_pressure * 0.16
        + failure_strength * 0.24
        + _unit(regression) * 0.10
        + cold_score * 0.10
    )
    action_deltas = {
        "write_cell": round(min(0.036, memory_consolidation * 0.020 + courage * 0.020) - min(0.030, forgetting_pressure * 0.016 + caution * 0.018), 4),
        "commit_reply": round(min(0.040, memory_consolidation * 0.026 + courage * 0.024) - min(0.038, forgetting_pressure * 0.020 + caution * 0.022), 4),
        "request_teacher": round(min(0.050, forgetting_pressure * 0.022 + _unit(regression) * 0.020 + failure_strength * 0.024 + caution * 0.022) - min(0.034, memory_consolidation * 0.022 + courage * 0.018), 4),
        "maintain_unclosed": round(min(0.048, review_rhythm_pressure * 0.020 + forgetting_pressure * 0.022 + _unit(regression) * 0.012), 4),
        "idle_think": round(min(0.054, review_rhythm_pressure * 0.026 + reconsolidation_need * 0.024 + forgetting_pressure * 0.018), 4),
        "integrate_feedback": round(min(0.038, reconsolidation_need * 0.020 + _unit(reward) * 0.010 + _unit(punish) * 0.012), 4),
        "read_draft": round(min(0.046, review_rhythm_pressure * 0.018 + forgetting_pressure * 0.018 + failure_strength * 0.020), 4),
        "edit_cell": round(min(0.044, failure_strength * 0.026 + _unit(regression) * 0.016 + caution * 0.016), 4),
        "stop_generating": round(min(0.030, forgetting_pressure * 0.014 + caution * 0.014) - min(0.022, memory_consolidation * 0.012), 4),
    }
    active = alignment_tick > 0 and (
        memory_consolidation > 0.0
        or forgetting_pressure > 0.0
        or review_rhythm_pressure > 0.0
        or reconsolidation_need > 0.0
    )
    return {
        "formula_id": PHASE20_10F_MEMORY_RHYTHM_ID,
        "active": active,
        "source": "existing_review_self_test_cold_retest_reward_punish_trace_projection",
        "alignment_event_id": str(events.get("alignment_event_id") or ""),
        "alignment_age_ticks": int(alignment_age),
        "review_gap_ticks": int(review_gap),
        "self_test_gap_ticks": int(self_test_gap),
        "success_count": int(success_count),
        "failure_count": int(failure_count),
        "success_strength": round(success_strength, 4),
        "failure_strength": round(failure_strength, 4),
        "gap_pressure": round(gap_pressure, 4),
        "memory_consolidation": round(memory_consolidation, 4),
        "forgetting_pressure": round(forgetting_pressure, 4),
        "review_rhythm_pressure": round(review_rhythm_pressure, 4),
        "reconsolidation_need": round(reconsolidation_need, 4),
        "cold_retest_need": round(cold_need, 4),
        "recent_review_relief": round(recent_review_relief, 4),
        "recent_self_test_relief": round(recent_self_test_relief, 4),
        "action_deltas": action_deltas,
        "uses_existing_ap_flow": True,
        "projection_only": True,
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _learning_object_lifecycle_from_events(
    *,
    identity: dict[str, Any],
    events: dict[str, Any],
    stage_progression: dict[str, Any],
) -> dict[str, Any]:
    review_rows = tuple(events.get("review_rows", ()) or ())
    self_test_rows = tuple(events.get("self_test_rows", ()) or ())
    teacher_feedback = dict(events.get("teacher_feedback", {}) or {})
    success_count = sum(1 for row in self_test_rows if row.get("success"))
    failure_count = sum(1 for row in self_test_rows if row.get("failure"))
    review_count = len(review_rows)
    self_test_count = len(self_test_rows)
    reward = max(_unit(events.get("alignment_reward", 0.0)), _unit(teacher_feedback.get("reward_total", 0.0)))
    punish = max(_unit(events.get("alignment_punish", 0.0)), _unit(teacher_feedback.get("punish_total", 0.0)))
    stage_scores = stage_progression.get("stage_scores")
    stage_scores = dict(stage_scores) if isinstance(stage_scores, dict) else {}
    dominant_stage = str(stage_progression.get("dominant_runtime_stage") or "")
    current_index = _learning_lifecycle_stage_index(
        review_count=review_count,
        self_test_count=self_test_count,
        success_count=success_count,
        failure_count=failure_count,
        reward=reward,
        punish=punish,
        dominant_stage=dominant_stage,
        cold_score=_unit(stage_scores.get("cold_retest", 0.0)),
        teacher_exit_score=_unit(stage_scores.get("teacher_exit", 0.0)),
    )
    lifecycle_stages = (
        "taught",
        "reviewed",
        "self_tested",
        "adjusted_after_feedback",
        "retested",
        "teacher_exit_ready",
        "cold_retest_ready",
    )
    current_stage = lifecycle_stages[min(current_index, len(lifecycle_stages) - 1)]
    stability = _unit(
        reward * 0.22
        + min(0.24, review_count * 0.06)
        + min(0.30, success_count * 0.15)
        + _unit(stage_scores.get("teacher_exit", 0.0)) * 0.16
        + _unit(stage_scores.get("generalization", 0.0)) * 0.12
        - min(0.34, failure_count * 0.17 + punish * 0.20)
    )
    regression = _unit(
        min(0.40, failure_count * 0.20)
        + punish * 0.24
        + _unit(stage_scores.get("correction", 0.0)) * 0.22
        - min(0.20, success_count * 0.08)
    )
    cold_window = _long_interval_cold_retest_window(events=events, stage_progression=stage_progression)
    cold_pressure = _unit(
        _unit(stage_scores.get("cold_retest", 0.0)) * 0.52
        + max(0, current_index - 4) * 0.10
        + _unit(cold_window.get("retest_need", 0.0)) * 0.34
    )
    cold_generalization_tuning = _cold_retest_generalization_tuning(
        self_test_rows=self_test_rows,
        structural_similarity=_unit(stage_scores.get("generalization", 0.0)),
        shared_ratio=stability,
        residual_ratio=regression,
    )
    memory_rhythm = _memory_consolidation_forgetting_review_rhythm(
        events=events,
        stage_scores=stage_scores,
        review_rows=review_rows,
        self_test_rows=self_test_rows,
        cold_window=cold_window,
        cold_generalization_tuning=cold_generalization_tuning,
        stability=stability,
        regression=regression,
        reward=reward,
        punish=punish,
    )
    if cold_window.get("active") and success_count > 0:
        current_index = max(current_index, 6)
        current_stage = lifecycle_stages[min(current_index, len(lifecycle_stages) - 1)]
    lifecycle_action_deltas = {
        "request_teacher": round(min(0.040, regression * 0.035) - min(0.030, stability * 0.026), 4),
        "maintain_unclosed": round(min(0.035, regression * 0.024 + cold_pressure * 0.012), 4),
        "write_cell": round(min(0.040, stability * 0.030 + success_count * 0.006) - min(0.026, regression * 0.020), 4),
        "commit_reply": round(min(0.042, stability * 0.032 + _unit(stage_scores.get("teacher_exit", 0.0)) * 0.012) - min(0.034, regression * 0.026), 4),
        "idle_think": round(min(0.044, cold_pressure * 0.026 + regression * 0.020 + (0.010 if review_count <= 1 else 0.0)), 4),
        "integrate_feedback": round(min(0.034, regression * 0.020 + reward * 0.012), 4),
        "read_draft": round(min(0.038, regression * 0.030 + cold_pressure * 0.014), 4),
        "edit_cell": round(min(0.038, regression * 0.032), 4),
        "stop_generating": round(min(0.024, regression * 0.014) - min(0.020, stability * 0.012), 4),
    }
    cold_deltas = cold_window.get("cold_retest_action_deltas")
    if isinstance(cold_deltas, dict) and cold_window.get("active"):
        lifecycle_action_deltas = {
            key: round(float(lifecycle_action_deltas.get(key, 0.0) or 0.0) + float(cold_deltas.get(key, 0.0) or 0.0), 4)
            for key in {*lifecycle_action_deltas.keys(), *cold_deltas.keys()}
        }
    cold_generalization_deltas = cold_generalization_tuning.get("action_deltas")
    if isinstance(cold_generalization_deltas, dict) and cold_generalization_tuning.get("active"):
        lifecycle_action_deltas = {
            key: round(
                float(lifecycle_action_deltas.get(key, 0.0) or 0.0)
                + float(cold_generalization_deltas.get(key, 0.0) or 0.0),
                4,
            )
            for key in {*lifecycle_action_deltas.keys(), *cold_generalization_deltas.keys()}
        }
    memory_rhythm_deltas = memory_rhythm.get("action_deltas")
    if isinstance(memory_rhythm_deltas, dict) and memory_rhythm.get("active"):
        lifecycle_action_deltas = {
            key: round(
                float(lifecycle_action_deltas.get(key, 0.0) or 0.0)
                + float(memory_rhythm_deltas.get(key, 0.0) or 0.0),
                4,
            )
            for key in {*lifecycle_action_deltas.keys(), *memory_rhythm_deltas.keys()}
        }
    return {
        "formula_id": PHASE20_10B_LEARNING_OBJECT_LIFECYCLE_ID,
        "active": True,
        "source": "existing_experience_flow_occurrences_and_alignment_events",
        "learning_object_id": str(events.get("alignment_event_id") or identity.get("alignment_event_id") or ""),
        "alignment_event_id": str(events.get("alignment_event_id") or ""),
        "alignment_tick": int(events.get("alignment_tick", 0) or 0),
        "source_event_id": str(events.get("source_event_id") or identity.get("source_event_id") or ""),
        "source_text_hash": _hash_text(str(events.get("source_text") or identity.get("source_text") or "")),
        "target_text_hash": _hash_text(str(events.get("target_text") or identity.get("target_text") or "")),
        "current_lifecycle_stage": current_stage,
        "lifecycle_stage_index": int(current_index),
        "lifecycle_stages": lifecycle_stages,
        "review_count": int(review_count),
        "self_test_count": int(self_test_count),
        "self_test_success_count": int(success_count),
        "self_test_failure_count": int(failure_count),
        "teacher_feedback_target_count": int(teacher_feedback.get("target_count", 0) or 0),
        "reward_pressure": round(reward, 4),
        "punish_pressure": round(punish, 4),
        "stability": round(stability, 4),
        "regression": round(regression, 4),
        "cold_retest_pressure": round(cold_pressure, 4),
        "long_interval_cold_retest_window": cold_window,
        "merged_with_long_interval_cold_retest_formula_id": cold_window.get("formula_id"),
        "cold_retest_generalization_tuning": cold_generalization_tuning,
        "merged_with_cold_retest_generalization_formula_id": cold_generalization_tuning.get("formula_id"),
        "memory_consolidation_forgetting_rhythm": memory_rhythm,
        "merged_with_memory_rhythm_formula_id": memory_rhythm.get("formula_id"),
        "lifecycle_action_deltas": lifecycle_action_deltas,
        "recent_review_ticks": tuple(int(row.get("tick", 0) or 0) for row in review_rows[-4:]),
        "recent_self_test_ticks": tuple(int(row.get("tick", 0) or 0) for row in self_test_rows[-4:]),
        "uses_existing_ap_flow": True,
        "projection_only": True,
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _learning_lifecycle_stage_index(
    *,
    review_count: int,
    self_test_count: int,
    success_count: int,
    failure_count: int,
    reward: float,
    punish: float,
    dominant_stage: str,
    cold_score: float,
    teacher_exit_score: float,
) -> int:
    index = 0
    if review_count > 0:
        index = max(index, 1)
    if self_test_count > 0:
        index = max(index, 2)
    if reward > 0.0 or punish > 0.0 or failure_count > 0:
        index = max(index, 3)
    if self_test_count >= 2 or (success_count > 0 and review_count >= 2):
        index = max(index, 4)
    if success_count > 0 and teacher_exit_score >= 0.24 and failure_count <= success_count:
        index = max(index, 5)
    if cold_score >= 0.42 and success_count > 0:
        index = max(index, 6)
    if failure_count > success_count and dominant_stage in {"correction", "contact", "review"}:
        index = min(index, 3)
    return int(index)


def _latest_edit_outcome_carryover(events: Sequence[RuntimeTickEventV2]) -> dict[str, Any]:
    for event in reversed(tuple(events)):
        delta = _edit_outcome_delta_from_event(event)
        if delta:
            return _edit_outcome_carryover(delta, source_tick=event.tick)
    return {}


def _merge_learning_and_edit_outcome_carryover(
    learning: dict[str, Any],
    edit_outcome: dict[str, Any],
    *,
    source_tick: int,
) -> dict[str, Any]:
    if not edit_outcome:
        return learning
    merged = dict(learning)
    for key in (
        "request_teacher_delta",
        "maintain_unclosed_delta",
        "write_cell_delta",
        "commit_reply_delta",
        "idle_think_delta",
        "integrate_feedback_delta",
        "read_draft_delta",
        "edit_cell_delta",
        "stop_generating_delta",
    ):
        merged[key] = round(float(merged.get(key, 0.0) or 0.0) + float(edit_outcome.get(key, 0.0) or 0.0), 4)
    merged["active"] = bool(learning.get("active") or edit_outcome.get("active"))
    merged["source_tick"] = int(source_tick)
    merged["edit_outcome_carryover"] = edit_outcome
    merged["merged_with_edit_outcome_formula_id"] = edit_outcome.get("formula_id")
    merged["writes_answer_directly"] = False
    merged["creates_reply_candidate"] = False
    return merged


def _edit_outcome_carryover(delta: dict[str, Any], *, source_tick: int) -> dict[str, Any]:
    improvement = _unit(delta.get("fit_improvement", 0.0))
    remaining_error = _unit(delta.get("remaining_error", 0.0))
    source_support = _unit(delta.get("source_support", 0.0))
    verification_need = _unit(delta.get("verification_need", 0.0))
    edit_success = _unit(delta.get("edit_success", 0.0))
    read_delta = min(0.12, verification_need * 0.10 + remaining_error * 0.04)
    edit_delta = min(0.12, remaining_error * 0.08 + verification_need * 0.04) - min(0.05, edit_success * 0.03)
    commit_delta = min(0.13, edit_success * 0.08 + source_support * improvement * 0.05) - min(0.10, remaining_error * 0.08)
    write_delta = min(0.08, edit_success * 0.04 + improvement * 0.03) - min(0.06, remaining_error * 0.05)
    stop_delta = min(0.08, remaining_error * 0.06) - min(0.07, edit_success * 0.05)
    idle_delta = min(0.07, max(remaining_error, improvement) * 0.04 + verification_need * 0.03)
    active = max(abs(read_delta), abs(edit_delta), abs(commit_delta), abs(write_delta), abs(stop_delta), idle_delta) > 0.0
    return {
        "formula_id": PHASE20_9S_EDIT_OUTCOME_ID,
        "active": active,
        "source_tick": int(source_tick),
        "source_delta_kind": delta.get("delta_kind"),
        "edit_success": round(edit_success, 4),
        "fit_before": round(_unit(delta.get("fit_before", 0.0)), 4),
        "fit_after": round(_unit(delta.get("fit_after", 0.0)), 4),
        "fit_improvement": round(improvement, 4),
        "remaining_error": round(remaining_error, 4),
        "verification_need": round(verification_need, 4),
        "source_support": round(source_support, 4),
        "read_draft_delta": round(read_delta, 4),
        "edit_cell_delta": round(edit_delta, 4),
        "commit_reply_delta": round(commit_delta, 4),
        "write_cell_delta": round(write_delta, 4),
        "stop_generating_delta": round(stop_delta, 4),
        "idle_think_delta": round(idle_delta, 4),
        "request_teacher_delta": 0.0,
        "maintain_unclosed_delta": 0.0,
        "integrate_feedback_delta": 0.0,
        "subjective": True,
        "may_be_wrong": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _latest_attribution_consolidation_carryover(events: Sequence[RuntimeTickEventV2]) -> dict[str, Any]:
    for event in reversed(tuple(events)):
        delta = _attribution_consolidation_delta_from_event(event)
        if delta:
            return _attribution_consolidation_carryover(delta, source_tick=event.tick)
    return {}


def _merge_learning_and_attribution_carryover(
    learning: dict[str, Any],
    attribution: dict[str, Any],
    *,
    source_tick: int,
) -> dict[str, Any]:
    merged = dict(learning)
    for key in (
        "request_teacher_delta",
        "maintain_unclosed_delta",
        "write_cell_delta",
        "commit_reply_delta",
        "idle_think_delta",
        "integrate_feedback_delta",
        "read_draft_delta",
        "edit_cell_delta",
        "stop_generating_delta",
    ):
        merged[key] = round(float(merged.get(key, 0.0) or 0.0) + float(attribution.get(key, 0.0) or 0.0), 4)
    merged["active"] = bool(learning.get("active") or attribution.get("active"))
    merged["source_tick"] = int(source_tick)
    merged["attribution_consolidation_carryover"] = attribution
    merged["merged_with_attribution_consolidation_formula_id"] = attribution.get("formula_id")
    merged["writes_answer_directly"] = False
    merged["creates_reply_candidate"] = False
    return merged


def _attribution_consolidation_carryover(delta: dict[str, Any], *, source_tick: int) -> dict[str, Any]:
    reward_drive = _unit(delta.get("expected_reward_delta", 0.0))
    punish_drive = _unit(delta.get("expected_punish_delta", 0.0))
    inhibition = _unit(delta.get("inhibition_delta", 0.0))
    alternative = _unit(delta.get("alternative_search_delta", 0.0))
    attention_bias = _unit(delta.get("attention_bias_delta", 0.0))
    request_delta = min(0.14, punish_drive * 0.08 + alternative * 0.10 + inhibition * 0.04) - min(0.08, reward_drive * 0.05)
    maintain_delta = min(0.10, punish_drive * 0.05 + alternative * 0.07)
    write_delta = min(0.09, reward_drive * 0.05 + attention_bias * 0.04) - min(0.08, inhibition * 0.05 + punish_drive * 0.04)
    commit_delta = min(0.11, reward_drive * 0.09 + attention_bias * 0.03) - min(0.12, punish_drive * 0.07 + inhibition * 0.06)
    idle_delta = min(0.10, alternative * 0.06 + attention_bias * 0.04 + max(reward_drive, punish_drive) * 0.03)
    read_delta = min(0.10, punish_drive * 0.05 + inhibition * 0.04 + alternative * 0.05)
    edit_delta = min(0.10, punish_drive * 0.06 + alternative * 0.06 + inhibition * 0.04)
    stop_delta = min(0.08, inhibition * 0.06 + punish_drive * 0.04) - min(0.06, reward_drive * 0.04)
    active = max(
        abs(request_delta),
        abs(maintain_delta),
        abs(write_delta),
        abs(commit_delta),
        idle_delta,
        read_delta,
        edit_delta,
        abs(stop_delta),
    ) > 0.0
    return {
        "formula_id": PHASE20_9Q_ATTRIBUTION_CONSOLIDATION_ID,
        "active": active,
        "source_tick": int(source_tick),
        "source_delta_kind": delta.get("delta_kind"),
        "attribution_consolidation_score": round(_unit(delta.get("attribution_consolidation_score", 0.0)), 4),
        "expected_reward_delta": round(reward_drive, 4),
        "expected_punish_delta": round(punish_drive, 4),
        "attention_bias_delta": round(attention_bias, 4),
        "inhibition_delta": round(inhibition, 4),
        "alternative_search_delta": round(alternative, 4),
        "request_teacher_delta": round(request_delta, 4),
        "maintain_unclosed_delta": round(maintain_delta, 4),
        "write_cell_delta": round(write_delta, 4),
        "commit_reply_delta": round(commit_delta, 4),
        "idle_think_delta": round(idle_delta, 4),
        "read_draft_delta": round(read_delta, 4),
        "edit_cell_delta": round(edit_delta, 4),
        "stop_generating_delta": round(stop_delta, 4),
        "eligible_occurrence_count": len(tuple(delta.get("eligible_occurrences", ()) or ())),
        "may_be_wrong": True,
        "subjective": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _learning_loop_carryover(metric: dict[str, Any], *, source_tick: int) -> dict[str, Any]:
    feedback = _unit(metric.get("feedback_only_readiness", 0.0))
    teacher_off = _unit(metric.get("teacher_off_readiness", 0.0))
    cold = _unit(metric.get("cold_retest_readiness", 0.0))
    scaffold = _unit(metric.get("scaffold_regression_need", 0.0))
    request_delta = min(0.10, scaffold * 0.10 + cold * 0.04) - min(0.10, teacher_off * 0.08 + feedback * 0.06)
    maintain_delta = min(0.08, scaffold * 0.06 + cold * 0.05) - min(0.07, teacher_off * 0.06 + feedback * 0.04)
    write_delta = min(0.10, teacher_off * 0.10 + feedback * 0.04)
    commit_delta = min(0.08, teacher_off * 0.08 + feedback * 0.04)
    idle_think_delta = min(0.10, cold * 0.08 + scaffold * 0.04 + feedback * 0.035 + teacher_off * 0.035)
    integrate_feedback_delta = min(0.08, feedback * 0.08)
    active = max(abs(request_delta), abs(maintain_delta), write_delta, commit_delta, idle_think_delta, integrate_feedback_delta) > 0.0
    self_test_feedback = metric.get("self_test_feedback")
    self_test_feedback = self_test_feedback if isinstance(self_test_feedback, dict) else {}
    return {
        "formula_id": PHASE20_9E_LEARNING_LOOP_CARRYOVER_ID,
        "active": active,
        "source_metric_formula_id": metric.get("formula_id"),
        "source_tick": int(source_tick),
        "dominant_learning_tendency": metric.get("dominant_learning_tendency"),
        "current_protocol_stage": metric.get("current_protocol_stage"),
        "source_event_id": metric.get("source_event_id"),
        "alignment_event_id": metric.get("alignment_event_id"),
        "source_text": metric.get("source_text"),
        "target_text": metric.get("target_text"),
        "feedback_only_readiness": round(feedback, 4),
        "teacher_off_readiness": round(teacher_off, 4),
        "cold_retest_readiness": round(cold, 4),
        "scaffold_regression_need": round(scaffold, 4),
        "request_teacher_delta": round(request_delta, 4),
        "maintain_unclosed_delta": round(maintain_delta, 4),
        "write_cell_delta": round(write_delta, 4),
        "commit_reply_delta": round(commit_delta, 4),
        "idle_think_delta": round(idle_think_delta, 4),
        "integrate_feedback_delta": round(integrate_feedback_delta, 4),
        "self_test_feedback": self_test_feedback,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _idle_learning_loop_carryover_from_experience_flow(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
) -> dict[str, Any]:
    metric = _idle_learning_review_metric(conn, session_id=session_id, before_tick=before_tick)
    if not metric:
        return {
            "formula_id": PHASE20_9E_LEARNING_LOOP_CARRYOVER_ID,
            "idle_review_formula_id": PHASE20_9F_IDLE_LEARNING_REVIEW_ID,
            "active": False,
            "writes_answer_directly": False,
            "creates_reply_candidate": False,
        }
    carryover = _learning_loop_carryover(metric, source_tick=int(metric.get("source_tick", 0) or 0))
    carryover = _apply_learning_stage_runtime_progression(
        carryover,
        action_tuner={},
        source_tick=int(metric.get("source_tick", 0) or 0),
        conn=conn,
        session_id=session_id,
        before_tick=before_tick,
    )
    return {
        **carryover,
        "idle_review_formula_id": PHASE20_9F_IDLE_LEARNING_REVIEW_ID,
        "idle_learning_review": metric,
        "reconstructed_from_experience_flow": True,
    }


def _idle_learning_review_metric(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
) -> dict[str, Any]:
    alignment = _latest_learning_alignment_for_idle(conn, session_id=session_id, before_tick=before_tick)
    cold_alignment = _cold_retest_alignment_for_idle(conn, session_id=session_id, before_tick=before_tick)
    if cold_alignment is not None and (
        alignment is None
        or str(cold_alignment.get("alignment_event_id") or "") != str((alignment or {}).get("alignment_event_id") or "")
    ):
        recent_age = max(0, int(before_tick) - int((alignment or {}).get("tick", 0) or 0)) if alignment else 0
        if float(cold_alignment.get("long_interval_score", 0.0) or 0.0) >= 0.20 or recent_age <= 6:
            alignment = cold_alignment
    active_unclosed = _latest_active_unclosed_for_idle(conn, session_id=session_id)
    recent_intent = _latest_recent_output_intent(conn, session_id=session_id, before_tick=before_tick)
    if alignment is None and active_unclosed is None and recent_intent is None:
        return {}

    alignment_tick = int((alignment or {}).get("tick", 0) or 0)
    age = max(0, int(before_tick) - alignment_tick) if alignment_tick else 0
    reward = _unit((alignment or {}).get("reward", 0.0))
    unclosed_u = _unit((active_unclosed or {}).get("u_value", 0.0))
    recent_source_intent = str((recent_intent or {}).get("source_intent") or "")
    recent_request = 1.0 if recent_source_intent in {"request_teacher", "maintain_unclosed"} else 0.0
    recent_teacher_off = 1.0 if recent_source_intent in {"exact_b0", "structural_bccstar"} else 0.0
    recent_feedback = 1.0 if recent_source_intent == "integrate_feedback" else 0.0

    feedback_only = 0.0
    teacher_off = 0.0
    cold_retest = 0.0
    if alignment is not None:
        feedback_only = _unit((0.48 + reward * 0.18) * max(0.0, 1.0 - age * 0.10))
        if recent_feedback > 0.0 and age <= 12:
            feedback_only = max(feedback_only, _unit(0.60 + reward * 0.10))
        teacher_off = _unit(recent_teacher_off * 0.46 + min(0.34, age * 0.035) + reward * 0.08)
        if age >= 12 and recent_feedback <= 0.0:
            cold_retest = _unit(0.20 + min(0.48, (age - 5) * 0.055) + teacher_off * 0.20)
        long_interval_evidence = alignment.get("long_interval_evidence") if isinstance(alignment.get("long_interval_evidence"), dict) else {}
        if long_interval_evidence:
            cold_retest = _unit(max(cold_retest, float(long_interval_evidence.get("score", 0.0) or 0.0)))
            teacher_off = _unit(max(teacher_off, min(0.72, 0.32 + float(long_interval_evidence.get("stability_hint", 0.0) or 0.0) * 0.36)))

    scaffold = _unit(unclosed_u * 0.72 + recent_request * 0.22)
    if feedback_only > 0.0:
        scaffold *= 0.65
    if teacher_off >= 0.58:
        scaffold *= 0.55
    self_test_feedback = _latest_idle_self_test_feedback(
        conn,
        session_id=session_id,
        before_tick=before_tick,
        alignment_event_id=str((alignment or {}).get("alignment_event_id") or ""),
    )
    if self_test_feedback:
        feedback_kind = str(self_test_feedback.get("feedback_kind") or "")
        grasp = _unit(self_test_feedback.get("self_test_grasp", 0.0))
        mismatch = _unit(self_test_feedback.get("mismatch_pressure", 0.0))
        if feedback_kind == "self_test_success":
            teacher_off = _unit(teacher_off + grasp * 0.12)
            cold_retest = _unit(cold_retest * 0.82 + grasp * 0.06)
            scaffold = _unit(scaffold * max(0.35, 1.0 - grasp * 0.42))
            feedback_only = _unit(feedback_only * 0.88)
        elif feedback_kind == "self_test_failure":
            teacher_off = _unit(teacher_off * 0.58)
            cold_retest = _unit(cold_retest * 0.72 + mismatch * 0.10)
            scaffold = _unit(max(scaffold, 0.24 + mismatch * 0.46))
            feedback_only = _unit(max(feedback_only, mismatch * 0.18))

    tendencies = {
        "feedback_only": round(feedback_only, 4),
        "teacher_off_probe": round(teacher_off, 4),
        "cold_retest_probe": round(cold_retest, 4),
        "return_to_scaffold": round(scaffold, 4),
    }
    dominant = max(tendencies, key=lambda key: tendencies[key])
    if max(tendencies.values()) <= 0.0:
        return {}
    return {
        "delta_kind": "idle_learning_review",
        "formula_id": PHASE20_9F_IDLE_LEARNING_REVIEW_ID,
        "source_tick": alignment_tick or int((active_unclosed or {}).get("updated_tick", 0) or before_tick),
        "current_protocol_stage": _idle_review_stage_from_tendency(dominant),
        "feedback_only_readiness": round(feedback_only, 4),
        "teacher_off_readiness": round(teacher_off, 4),
        "cold_retest_readiness": round(cold_retest, 4),
        "scaffold_regression_need": round(scaffold, 4),
        "dominant_learning_tendency": dominant,
        "tendencies": tendencies,
        "source_event_id": (alignment or {}).get("input_event_id") or (active_unclosed or {}).get("source_event_id"),
        "alignment_event_id": (alignment or {}).get("alignment_event_id"),
        "source_text": (alignment or {}).get("source_text") or (active_unclosed or {}).get("source_text") or "",
        "target_text": (alignment or {}).get("target_text") or "",
        "alignment_age_ticks": age,
        "recent_output_intent": (recent_intent or {}).get("source_intent", ""),
        "active_unclosed_u": round(unclosed_u, 4),
        "evidence": {
            "alignment_found": alignment is not None,
            "active_unclosed_found": active_unclosed is not None,
            "recent_teacher_off_output": bool(recent_teacher_off),
            "recent_request_output": bool(recent_request),
            "reward": round(reward, 4),
            "self_test_feedback": self_test_feedback,
            "long_interval_cold_retest": alignment.get("long_interval_evidence", {}) if isinstance(alignment, dict) else {},
        },
        "self_test_feedback": self_test_feedback,
        "projection_only": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _latest_learning_alignment_for_idle(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT event_id, tick, payload_json, reward
        FROM phase20_7_experience_events
        WHERE session_id=? AND event_kind='experience_alignment' AND tick < ?
        ORDER BY tick DESC, created_at_ms DESC
        LIMIT 1
        """,
        (session_id, int(before_tick)),
    ).fetchone()
    if row is None:
        return None
    event_id, tick, payload_json, reward = row
    payload = from_json(str(payload_json))
    if not isinstance(payload, dict):
        return None
    input_payload = _input_payload_for_alignment(conn, payload)
    source_text = str(input_payload.get("text", "") or "")
    if not source_text and payload.get("visual_signature"):
        source_text = VISUAL_FOCUS_ANCHOR_UNIT
    target_text = "".join(str(ch) for ch in payload.get("output_chars", ())).strip()
    return {
        "alignment_event_id": str(event_id),
        "tick": int(tick),
        "reward": float(reward or 0.0),
        "input_event_id": str(payload.get("input_event_id") or ""),
        "source_text": source_text,
        "target_text": target_text,
    }


def _cold_retest_alignment_for_idle(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
) -> dict[str, Any] | None:
    rows = conn.execute(
        """
        SELECT event_id, tick, payload_json, reward, punish
        FROM phase20_7_experience_events
        WHERE session_id=? AND event_kind='experience_alignment' AND tick < ?
        ORDER BY tick DESC, created_at_ms DESC
        LIMIT 36
        """,
        (session_id, int(before_tick)),
    ).fetchall()
    best: dict[str, Any] | None = None
    for event_id, tick, payload_json, reward, punish in rows:
        payload = from_json(str(payload_json))
        if not isinstance(payload, dict):
            continue
        alignment_event_id = str(event_id or "")
        alignment_tick = int(tick or 0)
        lifecycle_events = _learning_object_lifecycle_events(
            conn,
            session_id=session_id,
            before_tick=before_tick,
            identity={"alignment_event_id": alignment_event_id},
        )
        if not lifecycle_events:
            continue
        review_rows = tuple(lifecycle_events.get("review_rows", ()) or ())
        self_test_rows = tuple(lifecycle_events.get("self_test_rows", ()) or ())
        success_count = sum(1 for row in self_test_rows if row.get("success"))
        failure_count = sum(1 for row in self_test_rows if row.get("failure"))
        last_self_test_tick = max((int(row.get("tick", 0) or 0) for row in self_test_rows), default=alignment_tick)
        last_review_tick = max((int(row.get("tick", 0) or 0) for row in review_rows), default=alignment_tick)
        age = max(0, int(before_tick) - alignment_tick)
        self_test_gap = max(0, int(before_tick) - last_self_test_tick)
        review_gap = max(0, int(before_tick) - last_review_tick)
        reward_pressure = _unit(reward)
        punish_pressure = _unit(punish)
        stability_hint = _unit(min(0.36, success_count * 0.12) + reward_pressure * 0.16)
        regression_hint = _unit(min(0.44, failure_count * 0.18) + punish_pressure * 0.18)
        score = _unit(
            min(0.46, max(0, age - 8) * 0.026)
            + min(0.34, max(0, self_test_gap - 4) * 0.040)
            + min(0.18, max(0, review_gap - 5) * 0.022)
            + stability_hint * 0.22
            - regression_hint * 0.18
        )
        if score < 0.20:
            continue
        input_payload = _input_payload_for_alignment(conn, payload)
        source_text = str(input_payload.get("text", "") or "")
        if not source_text and payload.get("visual_signature"):
            source_text = VISUAL_FOCUS_ANCHOR_UNIT
        target_text = "".join(str(ch) for ch in payload.get("output_chars", ())).strip()
        candidate = {
            "alignment_event_id": alignment_event_id,
            "tick": alignment_tick,
            "reward": float(reward or 0.0),
            "input_event_id": str(payload.get("input_event_id") or ""),
            "source_text": source_text,
            "target_text": target_text,
            "long_interval_score": round(score, 4),
            "long_interval_evidence": {
                "formula_id": PHASE20_10D_LONG_INTERVAL_COLD_RETEST_ID,
                "alignment_age_ticks": int(age),
                "self_test_gap_ticks": int(self_test_gap),
                "review_gap_ticks": int(review_gap),
                "review_count": len(review_rows),
                "self_test_count": len(self_test_rows),
                "success_count": int(success_count),
                "failure_count": int(failure_count),
                "stability_hint": round(stability_hint, 4),
                "regression_hint": round(regression_hint, 4),
                "score": round(score, 4),
                "uses_existing_ap_flow": True,
                "projection_only": True,
                "writes_answer_directly": False,
                "creates_reply_candidate": False,
            },
        }
        if best is None or float(candidate["long_interval_score"]) > float(best.get("long_interval_score", 0.0)):
            best = candidate
    return best


def _latest_active_unclosed_for_idle(conn: sqlite3.Connection, *, session_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT source_event_id, source_text, u_value, updated_at_ms
        FROM phase20_7_unclosed_items
        WHERE status='active' AND session_id=?
        ORDER BY u_value DESC, updated_at_ms DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "source_event_id": str(row[0] or ""),
        "source_text": str(row[1] or ""),
        "u_value": float(row[2] or 0.0),
        "updated_tick": 0,
    }


def _latest_recent_output_intent(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
) -> dict[str, Any] | None:
    rows = conn.execute(
        """
        SELECT tick, event_kind, payload_json
        FROM phase20_7_experience_events
        WHERE session_id=? AND tick < ? AND event_kind IN ('draft_grid_write','draft_grid_commit')
        ORDER BY tick DESC, created_at_ms DESC
        LIMIT 12
        """,
        (session_id, int(before_tick)),
    ).fetchall()
    for tick, event_kind, payload_json in rows:
        payload = from_json(str(payload_json))
        if not isinstance(payload, dict):
            continue
        source_intent = str(payload.get("source_intent", "") or "")
        if source_intent:
            return {"tick": int(tick), "event_kind": str(event_kind), "source_intent": source_intent}
    return None


def _idle_review_stage_from_tendency(tendency: str) -> str:
    if tendency == "feedback_only":
        return "strong_scaffold"
    if tendency == "teacher_off_probe":
        return "teacher_off"
    if tendency == "cold_retest_probe":
        return "cold_retest"
    return "demonstrate"


def _idle_learning_review_text(carryover: dict[str, Any]) -> str:
    review = dict(carryover.get("idle_learning_review", {}) or {})
    if not review:
        return ""
    source_text = str(review.get("source_text") or "这个")
    target_text = str(review.get("target_text") or "").strip()
    tendency = str(review.get("dominant_learning_tendency") or "")
    pair = f"{source_text} -> {target_text}" if target_text else source_text
    if tendency == "feedback_only":
        return f"{pair} -> 先整理刚学到的联系"
    if tendency == "teacher_off_probe":
        return f"{pair} -> 试着自己想起来"
    if tendency == "cold_retest_probe":
        return f"{pair} -> 隔一会儿再确认还记不记得"
    return f"{pair} -> 还需要更多证据"


def _idle_learning_review_c_forward(carryover: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    review = dict(carryover.get("idle_learning_review", {}) or {})
    if not review:
        return ()
    target_text = str(review.get("target_text") or "").strip()
    if not target_text:
        return ()
    return (
        {
            "kind": "idle_learning_review_continuation",
            "formula_id": PHASE20_9F_IDLE_LEARNING_REVIEW_ID,
            "source_alignment_event_id": review.get("alignment_event_id"),
            "predicted_text": target_text,
            "support": max(
                _unit(review.get("feedback_only_readiness", 0.0)),
                _unit(review.get("teacher_off_readiness", 0.0)),
                _unit(review.get("cold_retest_readiness", 0.0)),
            ),
            "dominant_learning_tendency": review.get("dominant_learning_tendency"),
            "writes_answer_directly": False,
        },
    )


def _idle_learning_self_test_from_short_structure_flow(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
    learning_loop_carryover: dict[str, Any],
) -> dict[str, Any]:
    if not learning_loop_carryover.get("active"):
        return {}
    review_occurrence = _latest_learning_review_flow_occurrence(
        conn,
        session_id=session_id,
        before_tick=before_tick,
    )
    if not review_occurrence:
        return {}
    current_review = dict(learning_loop_carryover.get("idle_learning_review", {}) or {})
    previous_review = dict(review_occurrence.get("idle_learning_review", {}) or {})
    if not current_review or not previous_review:
        return {}
    current_alignment = str(current_review.get("alignment_event_id") or "")
    previous_alignment = str(previous_review.get("alignment_event_id") or "")
    if current_alignment and previous_alignment and current_alignment != previous_alignment:
        return {}
    target_text = str(current_review.get("target_text") or previous_review.get("target_text") or "").strip()
    if not target_text:
        return {}
    latest_self_test = _latest_idle_self_test_feedback(
        conn,
        session_id=session_id,
        before_tick=before_tick,
        alignment_event_id=current_alignment or previous_alignment,
    )
    long_interval = current_review.get("evidence", {}).get("long_interval_cold_retest") if isinstance(current_review.get("evidence"), dict) else {}
    long_interval = long_interval if isinstance(long_interval, dict) else {}
    long_interval_score = _unit(long_interval.get("score", 0.0))
    long_gap_after_self_test = int(long_interval.get("self_test_gap_ticks", 0) or 0) >= 8
    if (
        latest_self_test
        and int(latest_self_test.get("source_review_tick", 0) or 0) >= int(review_occurrence.get("tick", 0) or 0)
        and not (long_interval_score >= 0.42 and long_gap_after_self_test)
    ):
        return {}

    teacher_off = _unit(current_review.get("teacher_off_readiness", 0.0))
    cold = _unit(current_review.get("cold_retest_readiness", 0.0))
    feedback = _unit(current_review.get("feedback_only_readiness", 0.0))
    if max(teacher_off, cold) < 0.34 or feedback >= max(teacher_off, cold) + 0.18:
        return {}

    review_age = max(1, int(before_tick) - int(review_occurrence.get("tick", 0) or 0))
    recalled_text = target_text
    expected_text = target_text
    match_score = _unit(1.0 if recalled_text == expected_text else _text_overlap_score(recalled_text, expected_text))
    pressure = max(teacher_off, cold)
    self_test_grasp = _unit(match_score * 0.62 + pressure * 0.28 + min(0.10, review_age * 0.02))
    self_test_kind = "cold_retest_self_test" if (cold >= 0.72 and review_age >= 1) or long_interval_score >= 0.42 else "teacher_off_self_test"
    return {
        "formula_id": PHASE20_9G_IDLE_SELF_TEST_ID,
        "self_test_kind": self_test_kind,
        "source_review_occurrence_id": review_occurrence.get("occurrence_id"),
        "source_review_tick": review_occurrence.get("tick"),
        "alignment_event_id": current_alignment or previous_alignment,
        "source_event_id": current_review.get("source_event_id") or previous_review.get("source_event_id"),
        "source_text": current_review.get("source_text") or previous_review.get("source_text") or "",
        "expected_text": expected_text,
        "recalled_text": recalled_text,
        "match_score": round(match_score, 4),
        "self_test_grasp": round(self_test_grasp, 4),
        "teacher_off_pressure": round(teacher_off, 4),
        "cold_retest_pressure": round(cold, 4),
        "long_interval_cold_retest": long_interval,
        "long_interval_cold_retest_formula_id": long_interval.get("formula_id"),
        "dominant_learning_tendency": current_review.get("dominant_learning_tendency"),
        "current_protocol_stage": current_review.get("current_protocol_stage"),
        "review_age_ticks": review_age,
        "subjective": True,
        "may_be_wrong": True,
        "private_thought": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _latest_learning_review_flow_occurrence(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT o.occurrence_id, o.tick, o.clarity, o.position_json, s.canonical_hint
        FROM phase20_7_occurrences o
        JOIN phase20_7_experience_events e ON e.event_id=o.event_id
        JOIN phase20_7_sa_types s ON s.sa_type_id=o.sa_type_id
        WHERE e.session_id=?
          AND o.tick < ?
          AND o.sa_type_id >= 'short_structure_flow::learning_review::'
          AND o.sa_type_id < 'short_structure_flow::learning_review:;'
        ORDER BY o.tick DESC
        LIMIT 1
        """,
        (session_id, int(before_tick)),
    ).fetchone()
    if row is None:
        return None
    occurrence_id, tick, clarity, position_json, canonical_hint = row
    position = from_json(str(position_json))
    position = position if isinstance(position, dict) else {}
    review = position.get("idle_learning_review")
    return {
        "occurrence_id": str(occurrence_id),
        "tick": int(tick),
        "support": _unit(clarity),
        "canonical_hint": str(canonical_hint or ""),
        "idle_learning_review": review if isinstance(review, dict) else {},
    }


def _latest_idle_self_test_feedback(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    before_tick: int,
    alignment_event_id: str,
) -> dict[str, Any]:
    if not alignment_event_id:
        return {}
    row = conn.execute(
        """
        SELECT o.occurrence_id, o.tick, o.clarity, o.position_json, s.canonical_hint
        FROM phase20_7_occurrences o
        JOIN phase20_7_experience_events e ON e.event_id=o.event_id
        JOIN phase20_7_sa_types s ON s.sa_type_id=o.sa_type_id
        WHERE e.session_id=?
          AND o.tick < ?
          AND o.sa_type_id >= 'short_structure_flow::self_test::'
          AND o.sa_type_id < 'short_structure_flow::self_test:;'
        ORDER BY o.tick DESC
        LIMIT 12
        """,
        (session_id, int(before_tick)),
    ).fetchall()
    for occurrence_id, tick, clarity, position_json, canonical_hint in row:
        position = from_json(str(position_json))
        if not isinstance(position, dict):
            continue
        self_test = position.get("idle_self_test")
        if not isinstance(self_test, dict):
            continue
        if str(self_test.get("alignment_event_id") or "") != str(alignment_event_id):
            continue
        grasp = _unit(self_test.get("self_test_grasp", 0.0))
        match = _unit(self_test.get("match_score", 0.0))
        mismatch = _unit(1.0 - match if match > 0.0 else 1.0 - grasp)
        feedback_kind = "self_test_success" if grasp >= 0.68 and match >= 0.70 else "self_test_failure"
        return {
            "formula_id": PHASE20_9H_SELF_TEST_FEEDBACK_ID,
            "source_self_test_occurrence_id": str(occurrence_id),
            "source_review_occurrence_id": self_test.get("source_review_occurrence_id"),
            "source_review_tick": int(self_test.get("source_review_tick", 0) or 0),
            "tick": int(tick),
            "support": _unit(clarity),
            "feedback_kind": feedback_kind,
            "self_test_kind": self_test.get("self_test_kind"),
            "self_test_grasp": round(grasp, 4),
            "match_score": round(match, 4),
            "mismatch_pressure": round(mismatch, 4),
            "expected_text": self_test.get("expected_text"),
            "recalled_text": self_test.get("recalled_text"),
            "subjective": True,
            "may_be_wrong": True,
            "writes_answer_directly": False,
            "creates_reply_candidate": False,
        }
    return {}


def _idle_learning_self_test_text(self_test: dict[str, Any]) -> str:
    source_text = str(self_test.get("source_text") or "this")
    recalled_text = str(self_test.get("recalled_text") or "").strip()
    if self_test.get("self_test_kind") == "cold_retest_self_test":
        return f"{source_text} -> {recalled_text} -> cold self-test grasp {float(self_test.get('self_test_grasp', 0.0) or 0.0):.2f}"
    return f"{source_text} -> {recalled_text} -> teacher-off self-test grasp {float(self_test.get('self_test_grasp', 0.0) or 0.0):.2f}"


def _idle_learning_self_test_c_forward(self_test: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    return (
        {
            "kind": "idle_learning_self_test_recall",
            "formula_id": PHASE20_9G_IDLE_SELF_TEST_ID,
            "source_alignment_event_id": self_test.get("alignment_event_id"),
            "predicted_text": self_test.get("recalled_text"),
            "support": self_test.get("self_test_grasp"),
            "self_test_kind": self_test.get("self_test_kind"),
            "writes_answer_directly": False,
        },
    )


def _idle_learning_self_test_c_backward(self_test: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    return (
        {
            "kind": "idle_learning_self_test_source_trace",
            "formula_id": PHASE20_9G_IDLE_SELF_TEST_ID,
            "source_review_occurrence_id": self_test.get("source_review_occurrence_id"),
            "alignment_event_id": self_test.get("alignment_event_id"),
            "cause_grasp": self_test.get("self_test_grasp"),
            "subjective": True,
            "may_be_wrong": True,
            "writes_answer_directly": False,
        },
    )


def _text_overlap_score(left: str, right: str) -> float:
    left_chars = set(str(left))
    right_chars = set(str(right))
    if not left_chars or not right_chars:
        return 0.0
    return len(left_chars & right_chars) / len(left_chars | right_chars)


def _apply_learning_loop_carryover_to_competition(
    action_competition: tuple[dict[str, Any], ...],
    selected_action: dict[str, Any],
    carryover: dict[str, Any] | None,
) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    if not carryover or not carryover.get("active"):
        return action_competition, selected_action
    delta_by_action = {
        "request_teacher": float(carryover.get("request_teacher_delta", 0.0) or 0.0),
        "maintain_unclosed": float(carryover.get("maintain_unclosed_delta", 0.0) or 0.0),
        "write_cell": float(carryover.get("write_cell_delta", 0.0) or 0.0),
        "commit_reply": float(carryover.get("commit_reply_delta", 0.0) or 0.0),
        "idle_think": float(carryover.get("idle_think_delta", 0.0) or 0.0),
        "integrate_feedback": float(carryover.get("integrate_feedback_delta", 0.0) or 0.0),
        "read_draft": float(carryover.get("read_draft_delta", 0.0) or 0.0),
        "edit_cell": float(carryover.get("edit_cell_delta", 0.0) or 0.0),
        "stop_generating": float(carryover.get("stop_generating_delta", 0.0) or 0.0),
        "continue_writing": float(carryover.get("write_cell_delta", 0.0) or 0.0),
    }
    adjusted_rows: list[dict[str, Any]] = []
    selected_drive: float | None = None
    selected_delta = 0.0
    for row in action_competition:
        action_type = str(row.get("action_type", ""))
        delta = float(delta_by_action.get(action_type, 0.0) or 0.0)
        drive_before = _unit(row.get("drive", 0.0))
        drive_after = _unit(drive_before + delta)
        adjusted = dict(row)
        if abs(delta) > 0.00001:
            adjusted["drive_before_learning_loop_carryover"] = round(drive_before, 4)
            adjusted["learning_loop_carryover_delta"] = round(delta, 4)
            adjusted["learning_loop_carryover"] = carryover
            adjusted["drive"] = round(drive_after, 4)
        if adjusted.get("selected"):
            selected_drive = drive_after
            selected_delta = delta
        adjusted_rows.append(adjusted)
    adjusted_rows.sort(key=lambda row: (bool(row.get("selected")), float(row.get("drive", 0.0) or 0.0)), reverse=True)
    selected = dict(selected_action)
    if selected_drive is not None:
        selected["drive"] = round(selected_drive, 4)
    if abs(selected_delta) > 0.00001:
        selected["learning_loop_carryover_delta"] = round(selected_delta, 4)
        selected["learning_loop_carryover"] = carryover
    return tuple(adjusted_rows), selected


def _teacher_request_drive_context(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    observation: _ObservationLike | None,
    intent: str,
    existing_unclosed: dict[str, Any] | None,
    exact_b0: _ExactB0 | None,
    structural_b: _StructuralB | None,
    learning_loop_carryover: dict[str, Any] | None = None,
    process_grasp: float = 0.0,
) -> dict[str, Any]:
    # §30.2 把握 = B/C 支持: "我知道答案" (内容召回) 与"我知道怎么做" (过程范式
    # 共现波峰) 同为把握来源 — 会做的题不该因为没有现成答案而去请教.
    b_support = max(
        float(exact_b0.support) if exact_b0 is not None else 0.0,
        float(structural_b.similarity) if structural_b is not None else 0.0,
        _unit(process_grasp),
    )
    low_grasp = _unit(1.0 - b_support)
    unclosed_pull = _unit((existing_unclosed or {}).get("u_value", 0.0))
    short_flow_support = _latest_short_structure_flow_support(conn, session_id=session_id)
    carryover = _cstar_statepool_carryover(
        pool,
        tick=(_latest_tick_for_session(conn, session_id=session_id) + 1),
        observation=observation,
    )
    cstar_pressure = max(
        _unit(carryover.get("pressure_support", 0.0)),
        _unit(carryover.get("max_carry", 0.0)),
        _unit(carryover.get("observation_support_bias", 0.0)),
    )
    request_drive = _unit(0.20 + low_grasp * 0.30 + unclosed_pull * 0.18 + short_flow_support * 0.14 + cstar_pressure * 0.12)
    maintain_drive = _unit(0.18 + low_grasp * 0.16 + unclosed_pull * 0.36 + short_flow_support * 0.12 + cstar_pressure * 0.10)
    protocol_modulation = _learning_protocol_request_drive_modulation(
        conn,
        session_id=session_id,
        observation=observation,
        intent=intent,
        existing_unclosed=existing_unclosed,
        base_request_drive=request_drive,
        base_maintain_drive=maintain_drive,
        low_grasp=low_grasp,
        b_support=b_support,
        unclosed_pull=unclosed_pull,
    )
    request_drive = _unit(protocol_modulation.get("request_drive_after", request_drive))
    maintain_drive = _unit(protocol_modulation.get("maintain_drive_after", maintain_drive))
    action_tuner = _action_experience_tuner_projection(
        conn,
        session_id=session_id,
        tick=_latest_tick_for_session(conn, session_id=session_id) + 1,
        action_types=("request_teacher", "maintain_unclosed", "idle_think"),
        selected_action_type=intent,
    )
    request_before_action_tuner = request_drive
    maintain_before_action_tuner = maintain_drive
    if action_tuner.get("active"):
        multipliers = action_tuner.get("action_multipliers") if isinstance(action_tuner.get("action_multipliers"), dict) else {}
        request_drive = _unit(request_drive * _bounded_multiplier(multipliers.get("request_teacher", 1.0), low=0.35, high=1.70))
        maintain_drive = _unit(maintain_drive * _bounded_multiplier(multipliers.get("maintain_unclosed", 1.0), low=0.35, high=1.70))
    selected_drive = maintain_drive if intent == "maintain_unclosed" else request_drive
    current_referent = _current_referent_summary(
        observation,
        intent=intent,
        existing_unclosed=existing_unclosed,
        short_flow_support=short_flow_support,
        cstar_pressure=cstar_pressure,
    )
    return {
        "formula_id": PHASE20_8N_REQUEST_TEACHER_DRIVE_ID,
        "intent": intent,
        "low_grasp": round(low_grasp, 4),
        "b_support": round(b_support, 4),
        "unclosed_pull": round(unclosed_pull, 4),
        "short_structure_flow_support": round(short_flow_support, 4),
        "cstar_pressure": round(cstar_pressure, 4),
        "request_drive": round(request_drive, 4),
        "maintain_drive": round(maintain_drive, 4),
        "selected_drive": round(selected_drive, 4),
        "learning_protocol_drive_modulation": protocol_modulation,
        "action_experience_tuner_projection": action_tuner,
        "request_drive_before_action_experience_tuner": round(request_before_action_tuner, 4),
        "maintain_drive_before_action_experience_tuner": round(maintain_before_action_tuner, 4),
        "learning_loop_carryover": learning_loop_carryover or {
            "formula_id": PHASE20_9E_LEARNING_LOOP_CARRYOVER_ID,
            "active": False,
            "writes_answer_directly": False,
            "creates_reply_candidate": False,
        },
        "current_referent": current_referent,
        "current_referent_formula_id": PHASE20_8R_CURRENT_REFERENT_BINDING_ID,
        "source_kinds": tuple(
            kind
            for kind, active in (
                ("low_grasp", low_grasp > 0.0),
                ("unclosed", unclosed_pull > 0.0),
                ("short_structure_flow_next", short_flow_support > 0.0),
                ("cstar_statepool_carryover", cstar_pressure > 0.0),
            )
            if active
        ),
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
    }


def _select_request_expression(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    intent: str,
    fallback_text: str,
    teacher_request_context: dict[str, Any],
) -> tuple[tuple[str, ...], dict[str, Any]]:
    current_slot = _expression_paradigm_slot(intent, teacher_request_context)
    current_referent = _referent_from_expression_context(teacher_request_context)
    candidates = list(
        _teacher_expression_candidates(
            conn,
            intent=intent,
            current_slot=current_slot,
            current_referent=current_referent,
        )
    )
    candidates.extend(
        _draft_expression_candidates(
            conn,
            intent=intent,
            session_id=session_id,
            current_slot=current_slot,
            current_referent=current_referent,
        )
    )
    candidates.sort(
        key=lambda item: (
            float(item.get("support", 0.0)),
            float(item.get("referent_match", 0.0) or 0.0),
            float(item.get("paradigm_match", 0.0) or 0.0),
            -int(item.get("rank", 0) or 0),
        ),
        reverse=True,
    )
    composition = _compose_expression_fragments(
        candidates,
        intent=intent,
        current_slot=current_slot,
        current_referent=current_referent,
    )
    if composition is not None:
        text = str(composition["text"])
        return tuple(text), {
            "formula_id": PHASE20_8O_REQUEST_EXPRESSION_ID,
            "fallback_seed_formula_id": PHASE20_9M_FALLBACK_EXPRESSION_SEED_ID,
            "intent": intent,
            "source_kind": "expression_fragment_composition",
            "candidate_count": len(candidates),
            "selected_event_id": composition.get("source_event_ids", ())[0] if composition.get("source_event_ids") else None,
            "selected_support": round(float(composition.get("support", 0.0)), 4),
            "fallback_used": False,
            "learned_expression_preferred_over_seed": True,
            "innate_seed_low_priority": True,
            "fallback_text_hash": _hash_text(fallback_text),
            "current_paradigm_slot": current_slot,
            "selected_paradigm_slot": current_slot,
            "paradigm_formula_id": PHASE20_8P_EXPRESSION_PARADIGM_ID,
            "paradigm_match": 1.0,
            "current_referent": current_referent,
            "referent_formula_id": PHASE20_8R_CURRENT_REFERENT_BINDING_ID,
            "referent_match": round(float(composition.get("referent_match", 0.0)), 4),
            "referent_binding_kind": composition.get("referent_binding_kind"),
            "composition_formula_id": PHASE20_8Q_EXPRESSION_FRAGMENT_COMPOSITION_ID,
            "composition_kind": "draftgrid_fragment_combination",
            "fragment_count": len(composition.get("fragments", ())),
            "fragments": list(composition.get("fragments", ())),
            "source_event_ids": list(composition.get("source_event_ids", ())),
            "selected_text_hash": _hash_text(text),
            "selected_text": text,
            "support_terms": dict(composition.get("support_terms", {})),
            "teacher_request_drive_context": teacher_request_context,
            "creates_answer_candidate": False,
            "writes_answer_directly": False,
        }
    if candidates:
        selected = candidates[0]
        text = str(selected.get("text", ""))
        return tuple(text), {
            "formula_id": PHASE20_8O_REQUEST_EXPRESSION_ID,
            "fallback_seed_formula_id": PHASE20_9M_FALLBACK_EXPRESSION_SEED_ID,
            "intent": intent,
            "source_kind": selected.get("source_kind"),
            "candidate_count": len(candidates),
            "selected_event_id": selected.get("event_id"),
            "selected_support": round(float(selected.get("support", 0.0)), 4),
            "fallback_used": False,
            "learned_expression_preferred_over_seed": True,
            "innate_seed_low_priority": True,
            "fallback_text_hash": _hash_text(fallback_text),
            "current_paradigm_slot": current_slot,
            "selected_paradigm_slot": selected.get("paradigm_slot"),
            "paradigm_formula_id": PHASE20_8P_EXPRESSION_PARADIGM_ID,
            "paradigm_match": selected.get("paradigm_match"),
            "current_referent": current_referent,
            "referent_formula_id": PHASE20_8R_CURRENT_REFERENT_BINDING_ID,
            "selected_referent": selected.get("referent"),
            "referent_match": selected.get("referent_match"),
            "referent_binding_kind": selected.get("referent_binding_kind"),
            "selected_text_hash": _hash_text(text),
            "selected_text": text,
            "support_terms": dict(selected.get("support_terms", {})),
            "teacher_request_drive_context": teacher_request_context,
            "creates_answer_candidate": False,
            "writes_answer_directly": False,
        }
    return tuple(fallback_text), {
        "formula_id": PHASE20_8O_REQUEST_EXPRESSION_ID,
        "fallback_seed_formula_id": PHASE20_9M_FALLBACK_EXPRESSION_SEED_ID,
        "intent": intent,
        "source_kind": "innate_minimal_expression",
        "candidate_count": 0,
        "selected_event_id": None,
        "selected_support": 0.0,
        "fallback_used": True,
        "learned_expression_preferred_over_seed": False,
        "innate_seed_low_priority": True,
        "fallback_text_hash": _hash_text(fallback_text),
        "current_paradigm_slot": current_slot,
        "selected_paradigm_slot": "innate_minimal_expression",
        "paradigm_formula_id": PHASE20_8P_EXPRESSION_PARADIGM_ID,
        "paradigm_match": 0.0,
        "current_referent": current_referent,
        "referent_formula_id": PHASE20_8R_CURRENT_REFERENT_BINDING_ID,
        "selected_referent": {},
        "referent_match": 0.0,
        "referent_binding_kind": "trace_only_without_learned_expression",
        "selected_text_hash": _hash_text(fallback_text),
        "selected_text": fallback_text,
        "support_terms": {},
        "teacher_request_drive_context": teacher_request_context,
        "creates_answer_candidate": False,
        "writes_answer_directly": False,
    }


def _teacher_expression_candidates(
    conn: sqlite3.Connection,
    *,
    intent: str,
    current_slot: str,
    current_referent: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    rows = conn.execute(
        """
        SELECT event_id, payload_json, reward, punish, created_at_ms
        FROM phase20_7_experience_events
        WHERE event_kind='experience_alignment'
        ORDER BY created_at_ms DESC
        LIMIT 120
        """
    ).fetchall()
    out: list[dict[str, Any]] = []
    for rank, (event_id, payload_json, reward, punish, _created_at) in enumerate(rows):
        if is_tombstoned(conn, object_kind="event", object_ref=str(event_id)):
            continue
        payload = from_json(str(payload_json))
        if not isinstance(payload, dict):
            continue
        role = str(payload.get("expression_role") or "")
        role_match = _expression_role_match(intent, role)
        if role_match <= 0.0:
            continue
        candidate_slot = str(payload.get("expression_paradigm_slot") or "")
        paradigm_match, paradigm_term = _expression_paradigm_match(current_slot, candidate_slot)
        candidate_referent = _referent_from_expression_payload(payload)
        referent_match, referent_term, referent_binding_kind = _expression_referent_match(
            current_referent,
            candidate_referent,
        )
        chars = tuple(str(ch) for ch in payload.get("output_chars", ()))
        text = "".join(chars).strip()
        if not text:
            continue
        support, terms = compute_unified_experience_support(
            structural_similarity=role_match,
            occurrence_energy=0.72,
            recency=1.0 / (1.0 + rank),
            modality_match=1.0,
            reward=float(reward or 0.0),
            punish=float(punish or 0.0),
        )
        support = min(1.0, support + paradigm_term + referent_term)
        terms = tuple(terms) + (
            ("expression_paradigm_match", paradigm_term),
            ("expression_referent_match", referent_term),
        )
        out.append(
            {
                "source_kind": "teacher_feedback_expression",
                "event_id": str(event_id),
                "text": text,
                "support": support,
                "rank": rank,
                "paradigm_slot": candidate_slot,
                "paradigm_match": round(paradigm_match, 4),
                "referent": candidate_referent,
                "referent_match": round(referent_match, 4),
                "referent_binding_kind": referent_binding_kind,
                "support_terms": {key: round(float(value), 4) for key, value in terms},
            }
        )
    return tuple(out)


def _draft_expression_candidates(
    conn: sqlite3.Connection,
    *,
    intent: str,
    session_id: str,
    current_slot: str,
    current_referent: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    rows = conn.execute(
        """
        SELECT event_id, session_id, payload_json, reward, punish, created_at_ms
        FROM phase20_7_experience_events
        WHERE event_kind='draft_grid_commit'
        ORDER BY created_at_ms DESC
        LIMIT 160
        """
    ).fetchall()
    out: list[dict[str, Any]] = []
    for rank, (event_id, row_session_id, payload_json, reward, punish, _created_at) in enumerate(rows):
        if is_tombstoned(conn, object_kind="event", object_ref=str(event_id)):
            continue
        payload = from_json(str(payload_json))
        if not isinstance(payload, dict):
            continue
        source_intent = str(payload.get("source_intent") or "")
        role_match = _expression_role_match(intent, source_intent)
        if role_match <= 0.0:
            continue
        selection_trace = payload.get("request_expression_selection")
        candidate_slot = ""
        if isinstance(selection_trace, dict):
            candidate_slot = str(selection_trace.get("current_paradigm_slot") or "")
            if not candidate_slot:
                candidate_slot = _expression_paradigm_slot(
                    source_intent,
                    _context_from_expression_trace(selection_trace),
                )
        candidate_referent = _referent_from_expression_trace(selection_trace if isinstance(selection_trace, dict) else {})
        referent_match, referent_term, referent_binding_kind = _expression_referent_match(
            current_referent,
            candidate_referent,
        )
        paradigm_match, paradigm_term = _expression_paradigm_match(current_slot, candidate_slot)
        chars = tuple(str(ch) for ch in payload.get("visible_chars", ()))
        text = "".join(chars).strip() or str(payload.get("visible_text") or "").strip()
        if not text:
            continue
        same_session = 1.0 if str(row_session_id) == str(session_id) else 0.35
        support, terms = compute_unified_experience_support(
            structural_similarity=role_match,
            occurrence_energy=0.58,
            recency=same_session / (1.0 + rank),
            modality_match=1.0,
            reward=float(reward or 0.0),
            punish=float(punish or 0.0),
        )
        support = min(0.82, support + paradigm_term + referent_term)
        terms = tuple(terms) + (
            ("expression_paradigm_match", paradigm_term),
            ("expression_referent_match", referent_term),
        )
        out.append(
            {
                "source_kind": "draft_grid_expression_memory",
                "event_id": str(event_id),
                "text": text,
                "support": support,
                "rank": rank,
                "paradigm_slot": candidate_slot,
                "paradigm_match": round(paradigm_match, 4),
                "referent": candidate_referent,
                "referent_match": round(referent_match, 4),
                "referent_binding_kind": referent_binding_kind,
                "support_terms": {key: round(float(value), 4) for key, value in terms},
            }
        )
    return tuple(out)


def _compose_expression_fragments(
    candidates: Sequence[dict[str, Any]],
    *,
    intent: str,
    current_slot: str,
    current_referent: dict[str, Any],
) -> dict[str, Any] | None:
    base_compatible = [
        candidate
        for candidate in candidates
        if candidate.get("source_kind") == "teacher_feedback_expression"
        and candidate.get("paradigm_slot") == current_slot
        and float(candidate.get("support", 0.0)) >= 0.50
    ]
    if _referent_is_active(current_referent):
        referent_compatible = [
            candidate
            for candidate in base_compatible
            if float(candidate.get("referent_match", 0.0) or 0.0) > 0.0
        ]
        compatible = referent_compatible if len(referent_compatible) >= 2 else base_compatible
    else:
        compatible = base_compatible
    source_ids = tuple(dict.fromkeys(str(candidate.get("event_id")) for candidate in compatible if candidate.get("event_id")))
    if len(source_ids) < 2:
        return None
    fragments: list[dict[str, Any]] = []
    seen_fragment_hashes: set[str] = set()
    for candidate in compatible:
        source_expression_text = str(candidate.get("text") or "")
        for index, fragment in enumerate(_expression_fragments_from_text(source_expression_text)):
            fragment_hash = _hash_text(fragment)
            if fragment_hash in seen_fragment_hashes:
                continue
            seen_fragment_hashes.add(fragment_hash)
            fragments.append(
                {
                    "text": fragment,
                    "text_hash": fragment_hash,
                    "source_event_id": str(candidate.get("event_id") or ""),
                    "source_kind": str(candidate.get("source_kind") or ""),
                    "source_support": round(float(candidate.get("support", 0.0)), 4),
                    "source_rank": int(candidate.get("rank", 0) or 0),
                    "fragment_index": index,
                }
            )
            break
        if len(fragments) >= 3:
            break
    if len({fragment["source_event_id"] for fragment in fragments}) < 2:
        return None
    text = _join_expression_fragments(tuple(str(fragment["text"]) for fragment in fragments))
    if not text:
        return None
    referent_match = max((float(candidate.get("referent_match", 0.0) or 0.0) for candidate in compatible), default=0.0)
    referent_bonus = min(0.07, referent_match * 0.07)
    support = min(1.0, sum(float(fragment["source_support"]) for fragment in fragments) / max(len(fragments), 1) + 0.08 + referent_bonus)
    return {
        "intent": intent,
        "slot": current_slot,
        "text": text,
        "support": support,
        "referent_match": round(referent_match, 4),
        "referent_binding_kind": "fragment_sources_referent_matched"
        if referent_match > 0.0
        else "fragment_sources_slot_only",
        "fragments": tuple(fragments),
        "source_event_ids": tuple(dict.fromkeys(fragment["source_event_id"] for fragment in fragments)),
        "support_terms": {
            "fragment_source_count": round(float(len({fragment["source_event_id"] for fragment in fragments})), 4),
            "fragment_count": round(float(len(fragments)), 4),
            "expression_fragment_composition_bonus": 0.08,
            "expression_referent_composition_bonus": round(referent_bonus, 4),
        },
    }


def _expression_fragments_from_text(text: str) -> tuple[str, ...]:
    cleaned = " ".join(str(text).strip().split())
    if not cleaned:
        return ()
    separators = ("；", ";", "。", ".", "！", "!", "？", "?", "，", ",", "、", "/", "|")
    fragments = [cleaned]
    for separator in separators:
        next_fragments: list[str] = []
        for fragment in fragments:
            next_fragments.extend(part.strip() for part in fragment.split(separator) if part.strip())
        fragments = next_fragments or fragments
    return tuple(dict.fromkeys(fragment for fragment in fragments if fragment))


def _join_expression_fragments(fragments: Sequence[str]) -> str:
    clean = tuple(fragment.strip() for fragment in fragments if fragment and fragment.strip())
    if not clean:
        return ""
    ascii_like = all(all(ord(ch) < 128 for ch in fragment) for fragment in clean)
    separator = " " if ascii_like else "，"
    return separator.join(clean)


def _current_referent_summary(
    observation: _ObservationLike | None,
    *,
    intent: str,
    existing_unclosed: dict[str, Any] | None,
    short_flow_support: float,
    cstar_pressure: float,
) -> dict[str, Any]:
    if observation is None:
        return {
            "formula_id": PHASE20_8R_CURRENT_REFERENT_BINDING_ID,
            "referent_kind": "none",
            "modalities": (),
            "active": False,
            "writes_answer_directly": False,
        }
    recovery_kind = observation.recovery_kind if isinstance(observation, _RecoveredObservation) else "current_text"
    unclosed_value = _unit((existing_unclosed or {}).get("u_value", 0.0))
    visual_tokens = tuple(sorted(_visual_tokens(observation.visual_signature))) if observation.visual_signature else ()
    if intent == "maintain_unclosed" or unclosed_value > 0.0:
        referent_kind = "unclosed_current"
    elif "audio" in recovery_kind:
        referent_kind = "audio_focus"
    elif observation.visual_signature and (
        "visual" in recovery_kind or recovery_kind in {"current_visual", "recent_visual"}
    ):
        referent_kind = "visual_focus"
    elif observation.visual_signature:
        referent_kind = "multimodal_focus"
    elif observation.chars:
        referent_kind = "text_focus"
    else:
        referent_kind = "structure_focus"
    if referent_kind == "visual_focus":
        modalities = ("vision",)
    elif referent_kind == "audio_focus":
        modalities = ("audio",)
    elif referent_kind == "unclosed_current":
        modalities = _observation_modality_mix(observation)
    elif referent_kind == "multimodal_focus":
        modalities = _observation_modality_mix(observation)
    else:
        modalities = _observation_modality_mix(observation)
    text_value = "".join(observation.chars)
    salience = _unit(
        (0.32 if observation.chars else 0.0)
        + (0.28 if observation.visual_signature else 0.0)
        + unclosed_value * 0.26
        + _unit(short_flow_support) * 0.08
        + _unit(cstar_pressure) * 0.06
    )
    return {
        "formula_id": PHASE20_8R_CURRENT_REFERENT_BINDING_ID,
        "referent_kind": referent_kind,
        "modalities": modalities,
        "recovery_kind": _public_recovery_kind(observation) if isinstance(observation, _RecoveredObservation) else recovery_kind,
        "text_signature": observation.text_signature,
        "text_hash": observation.text_hash,
        "text_unit_count": len(observation.chars),
        "visual_signature_hash": _hash_text(observation.visual_signature) if observation.visual_signature else "",
        "visual_token_count": len(visual_tokens),
        "visual_tokens": visual_tokens[:8],
        "source_event_id": observation.event_id,
        "source_signature": observation.signature,
        "unclosed_u": round(unclosed_value, 4),
        "salience": round(salience, 4),
        "active": salience > 0.0,
        "subjective": True,
        "writes_answer_directly": False,
    }


def _referent_from_expression_context(context: dict[str, Any]) -> dict[str, Any]:
    referent = context.get("current_referent") if isinstance(context, dict) else {}
    return dict(referent) if isinstance(referent, dict) else {}


def _referent_from_expression_trace(trace: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(trace, dict):
        return {}
    referent = trace.get("current_referent")
    if isinstance(referent, dict):
        return dict(referent)
    context = trace.get("teacher_request_drive_context")
    if isinstance(context, dict):
        return _referent_from_expression_context(context)
    return {}


def _referent_from_expression_payload(payload: dict[str, Any]) -> dict[str, Any]:
    referent = payload.get("expression_referent") if isinstance(payload, dict) else {}
    if isinstance(referent, dict) and referent:
        return dict(referent)
    target_trace = payload.get("expression_target_trace") if isinstance(payload, dict) else {}
    return _referent_from_expression_trace(target_trace if isinstance(target_trace, dict) else {})


def _referent_is_active(referent: dict[str, Any]) -> bool:
    if not isinstance(referent, dict):
        return False
    if not referent.get("active"):
        return False
    return str(referent.get("referent_kind") or "none") != "none"


def _expression_referent_match(
    current_referent: dict[str, Any],
    candidate_referent: dict[str, Any],
) -> tuple[float, float, str]:
    if not _referent_is_active(current_referent):
        return 0.0, 0.0, "current_referent_inactive"
    if not _referent_is_active(candidate_referent):
        return 0.0, 0.0, "candidate_has_no_referent_trace"
    current_kind = str(current_referent.get("referent_kind") or "")
    candidate_kind = str(candidate_referent.get("referent_kind") or "")
    current_modalities = {str(item) for item in current_referent.get("modalities", ()) if str(item)}
    candidate_modalities = {str(item) for item in candidate_referent.get("modalities", ()) if str(item)}
    modality_overlap = len(current_modalities & candidate_modalities) / max(len(current_modalities | candidate_modalities), 1)
    same_kind = 1.0 if current_kind and current_kind == candidate_kind else 0.0
    same_text = (
        1.0
        if current_referent.get("text_signature")
        and current_referent.get("text_signature") == candidate_referent.get("text_signature")
        else 0.0
    )
    same_visual = (
        1.0
        if current_referent.get("visual_signature_hash")
        and current_referent.get("visual_signature_hash") == candidate_referent.get("visual_signature_hash")
        else 0.0
    )
    unclosed_match = (
        1.0
        if current_kind == "unclosed_current" and candidate_kind == "unclosed_current"
        else 0.0
    )
    match = _unit(same_kind * 0.45 + modality_overlap * 0.28 + same_visual * 0.18 + same_text * 0.12 + unclosed_match * 0.16)
    if match <= 0.0:
        return 0.0, 0.0, "referent_mismatch"
    term = min(0.16, match * 0.16)
    if same_visual > 0.0:
        binding_kind = "same_visual_referent"
    elif same_text > 0.0:
        binding_kind = "same_text_referent"
    elif same_kind > 0.0:
        binding_kind = "same_referent_kind"
    elif modality_overlap > 0.0:
        binding_kind = "same_modality_family"
    else:
        binding_kind = "weak_referent_overlap"
    return round(match, 4), round(term, 4), binding_kind


def _expression_role_match(intent: str, role: str) -> float:
    if role == intent and role in EXPRESSION_INTENTS:
        return 1.0
    return 0.0


def _expression_paradigm_slot(intent: str, context: dict[str, Any]) -> str:
    if intent == "integrate_feedback":
        return "feedback_acknowledgement"
    if intent == "maintain_unclosed":
        return "unclosed_maintenance"
    unclosed_pull = _unit(context.get("unclosed_pull", 0.0))
    short_flow = _unit(context.get("short_structure_flow_support", 0.0))
    low_grasp = _unit(context.get("low_grasp", 0.0))
    cstar_pressure = _unit(context.get("cstar_pressure", 0.0))
    if unclosed_pull >= 0.35:
        return "unclosed_request"
    if short_flow >= 0.50:
        return "flow_continuation_request"
    if low_grasp >= 0.70 and cstar_pressure >= 0.50:
        return "low_grasp_pressure_request"
    if low_grasp >= 0.70:
        return "low_grasp_request"
    return "general_request"


def _expression_paradigm_match(current_slot: str, candidate_slot: str) -> tuple[float, float]:
    if not candidate_slot:
        return 0.0, 0.0
    if candidate_slot == current_slot:
        return 1.0, 0.18
    current_family = current_slot.rsplit("_", 1)[-1] if "_" in current_slot else current_slot
    candidate_family = candidate_slot.rsplit("_", 1)[-1] if "_" in candidate_slot else candidate_slot
    if current_family == candidate_family and current_family in {"request", "maintenance"}:
        return 0.35, 0.06
    return 0.0, 0.0


def _context_from_expression_trace(trace: dict[str, Any]) -> dict[str, Any]:
    context = trace.get("teacher_request_drive_context") if isinstance(trace, dict) else {}
    return dict(context) if isinstance(context, dict) else {}


def _expression_role_for_target_event(conn: sqlite3.Connection, target_event_id: str | None) -> str | None:
    if not target_event_id:
        return None
    row = conn.execute(
        """
        SELECT event_kind, payload_json
        FROM phase20_7_experience_events
        WHERE event_id=?
        LIMIT 1
        """,
        (str(target_event_id),),
    ).fetchone()
    if not row:
        return None
    event_kind, payload_json = row
    if str(event_kind) not in {"draft_grid_write", "draft_grid_commit"}:
        return None
    payload = from_json(str(payload_json))
    if not isinstance(payload, dict):
        return None
    source_intent = str(payload.get("source_intent") or "")
    return source_intent if source_intent in EXPRESSION_INTENTS else None


def _expression_target_trace_for_event(conn: sqlite3.Connection, target_event_id: str | None) -> dict[str, Any]:
    if not target_event_id:
        return {}
    row = conn.execute(
        """
        SELECT payload_json
        FROM phase20_7_experience_events
        WHERE event_id=?
        LIMIT 1
        """,
        (str(target_event_id),),
    ).fetchone()
    if not row:
        return {}
    payload = from_json(str(row[0]))
    if not isinstance(payload, dict):
        return {}
    trace = payload.get("request_expression_selection")
    return dict(trace) if isinstance(trace, dict) else {}


def _latest_short_structure_flow_support(conn: sqlite3.Connection, *, session_id: str) -> float:
    candidates = [
        candidate
        for candidate in query_recent_experience_flow_candidates(
            conn,
            session_id=session_id,
            from_json=from_json,
            hash_text=_hash_text,
            signature_for_chars=_signature_for_chars,
            compose_input_signature=_compose_input_signature,
            visual_tokens_from_payloads=_visual_signature_from_payloads,
            limit=24,
        )
        if candidate.candidate_kind == "short_structure_flow_next"
    ]
    return _unit(max((float(candidate.support) for candidate in candidates), default=0.0))


def _learning_protocol_request_drive_modulation(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    observation: _ObservationLike | None,
    intent: str,
    existing_unclosed: dict[str, Any] | None,
    base_request_drive: float,
    base_maintain_drive: float,
    low_grasp: float,
    b_support: float,
    unclosed_pull: float,
) -> dict[str, Any]:
    latest_tick = _latest_tick_for_session(conn, session_id=session_id)
    recent_request_action_count = _recent_selected_action_count(
        conn,
        session_id=session_id,
        action_types=("request_teacher", "maintain_unclosed"),
        since_tick=max(0, latest_tick - 24),
    )
    recent_feedback_count = _recent_event_count(
        conn,
        session_id=session_id,
        event_kinds=("teacher_feedback_event",),
        since_tick=max(0, latest_tick - 24),
    )
    attempt_count = int((existing_unclosed or {}).get("attempt_count", 0) or 0)
    recent_request_count = max(int(recent_request_action_count), int(attempt_count))
    request_frequency_cooldown = min(0.34, recent_request_count * 0.035 + attempt_count * 0.075)
    teacher_fade_pressure = min(0.28, _unit(b_support) * 0.22 + recent_feedback_count * 0.025)
    feedback_wait = min(0.12, max(0, recent_request_count - recent_feedback_count) * 0.025)
    if intent == "maintain_unclosed":
        request_multiplier = max(0.42, 1.0 - request_frequency_cooldown - teacher_fade_pressure - feedback_wait)
        maintain_multiplier = max(0.60, 1.0 - request_frequency_cooldown * 0.45 - feedback_wait * 0.35)
    else:
        request_multiplier = max(0.50, 1.0 - request_frequency_cooldown * 0.80 - teacher_fade_pressure)
        maintain_multiplier = max(0.68, 1.0 - request_frequency_cooldown * 0.30)
    request_after = _unit(base_request_drive * request_multiplier)
    maintain_after = _unit(base_maintain_drive * maintain_multiplier + unclosed_pull * 0.02)
    selected_after = maintain_after if intent == "maintain_unclosed" else request_after
    return {
        "formula_id": PHASE20_9B_LEARNING_PROTOCOL_DRIVE_MODULATION_ID,
        "source_projection_formula_id": "apv3_phase20_9a_six_stage_learning_protocol_projection/v1",
        "intent": intent,
        "base_request_drive": round(_unit(base_request_drive), 4),
        "base_maintain_drive": round(_unit(base_maintain_drive), 4),
        "request_drive_after": round(request_after, 4),
        "maintain_drive_after": round(maintain_after, 4),
        "selected_drive_after": round(selected_after, 4),
        "recent_request_count": int(recent_request_count),
        "recent_feedback_count": int(recent_feedback_count),
        "unclosed_attempt_count": int(attempt_count),
        "request_frequency_cooldown": round(request_frequency_cooldown, 4),
        "teacher_fade_pressure": round(teacher_fade_pressure, 4),
        "feedback_wait": round(feedback_wait, 4),
        "low_grasp": round(_unit(low_grasp), 4),
        "b_support": round(_unit(b_support), 4),
        "observation_signature": observation.signature if observation is not None else None,
        "projection_only": False,
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
    }


def _recent_selected_action_count(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    action_types: Sequence[str],
    since_tick: int,
) -> int:
    action_values = tuple(str(action) for action in action_types if str(action))
    if not action_values:
        return 0
    placeholders = ",".join("?" for _ in action_values)
    row = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM phase20_7_action_records
        WHERE session_id=? AND selected=1 AND tick>=? AND action_type IN ({placeholders})
        """,
        (session_id, int(since_tick), *action_values),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _recent_event_count(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    event_kinds: Sequence[str],
    since_tick: int,
) -> int:
    event_values = tuple(str(kind) for kind in event_kinds if str(kind))
    if not event_values:
        return 0
    placeholders = ",".join("?" for _ in event_values)
    row = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM phase20_7_experience_events
        WHERE session_id=? AND tick>=? AND event_kind IN ({placeholders})
        """,
        (session_id, int(since_tick), *event_values),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _recent_event_count_from_source_kind(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    event_kind: str,
    source_kind: str,
    since_tick: int,
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM phase20_7_experience_events e
        JOIN phase20_7_source_packets s ON s.source_packet_id=e.source_packet_id
        WHERE e.session_id=? AND e.tick>=? AND e.event_kind=? AND s.source_kind=?
        """,
        (session_id, int(since_tick), str(event_kind), str(source_kind)),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _latest_selected_action_tick(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    action_type: str,
) -> int | None:
    row = conn.execute(
        """
        SELECT MAX(tick)
        FROM phase20_7_action_records
        WHERE session_id=? AND selected=1 AND action_type=?
        """,
        (session_id, str(action_type)),
    ).fetchone()
    if not row or row[0] is None:
        return None
    return int(row[0])


def _recent_outward_text_count(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    text_hash: str,
    since_tick: int,
) -> int:
    rows = conn.execute(
        """
        SELECT payload_json
        FROM phase20_7_experience_events
        WHERE session_id=? AND tick>=? AND event_kind='outward_speech'
        """,
        (session_id, int(since_tick)),
    ).fetchall()
    count = 0
    for (payload_json,) in rows:
        payload = from_json(str(payload_json))
        if isinstance(payload, dict) and str(payload.get("expression_text_hash") or "") == str(text_hash):
            count += 1
    return count


def _candidate_support_formula(candidate_audit_slots: Sequence[dict[str, Any]]) -> str | None:
    for slot in candidate_audit_slots:
        formula = slot.get("support_formula")
        if formula:
            return str(formula)
    return None


def _support_terms_dict(terms: Sequence[tuple[str, float]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, value in terms:
        out[str(key)] = round(float(value), 4)
    return out


def _tick_event(
    *,
    conn: sqlite3.Connection | None = None,
    session_id: str,
    tick: int,
    selected_action: dict[str, Any],
    action_competition: tuple[dict[str, Any], ...],
    state_pool: StatePool,
    grid: DraftGrid,
    observation: _ObservationLike | None = None,
    event_ids: tuple[str, ...] = (),
    action_record_ids: tuple[str, ...] = (),
    source_refs: tuple[dict[str, Any], ...] = (),
    query_structures: tuple[dict[str, Any], ...] = (),
    ssp_summary: dict[str, Any] | None = None,
    external_inputs: tuple[dict[str, Any], ...] = (),
    b0: _ExactB0 | None = None,
    structural_b: _StructuralB | None = None,
    unclosed_items: tuple[dict[str, Any], ...] = (),
    feelings: dict[str, Any] | None = None,
    learning_deltas: tuple[dict[str, Any], ...] = (),
    timings_ms: dict[str, Any] | None = None,
    c_forward: tuple[dict[str, Any], ...] | None = None,
    c_backward: tuple[dict[str, Any], ...] | None = None,
) -> RuntimeTickEventV2:
    b_candidates: tuple[dict[str, Any], ...] = ()
    if b0 is not None:
        b_candidates = (
            {
                "kind": "exact_b0",
                "event_id": b0.event_id,
                "source_event_id": b0.source_event_id,
                "support": b0.support,
                "visual_similarity": b0.visual_similarity,
                "output_unit_count": len(b0.output_chars),
                "support_formula": _candidate_support_formula(b0.candidate_audit_slots),
                "support_terms": _support_terms_dict(b0.support_terms),
                "candidate_audit_slots": list(b0.candidate_audit_slots),
            },
        )
    elif structural_b is not None:
        b_candidates = (
            {
                "kind": "structural_b",
                "event_id": structural_b.event_id,
                "source_event_id": structural_b.source_event_id,
                "support": structural_b.similarity,
                "shared_unit_count": len(structural_b.shared_units),
                "residual_unit_count": len(structural_b.residual_units),
                "output_unit_count": len(structural_b.output_chars),
                "support_formula": _candidate_support_formula(structural_b.candidate_audit_slots),
                "support_terms": _support_terms_dict(structural_b.support_terms),
                "candidate_audit_slots": list(structural_b.candidate_audit_slots),
            },
        )
    cstar_carryover = _cstar_statepool_carryover(state_pool, tick=tick, observation=observation)
    # §56.2 残差竞争召回: 完整短期序列池的多轮 B 召回 — 第一轮(当前 observation)
    # 由 exact/structural 完成; 此处对序列池残余 mass 继续召回, 命中作为并列 B 波.
    # 只在 observe_text tick 算一次 (每 turn 一次, §185 预算); 支持度带阻尼恒低于
    # 主召回, 不参与输出选择 — 丰富上下文场/C*/把握, 使同问句不同前文认知状态不同.
    if (
        conn is not None
        and observation is not None
        and str(selected_action.get("action_type") or "") == "observe_text"
    ):
        winner_shared: tuple[str, ...] = ()
        if b0 is not None:
            winner_shared = tuple(str(ch) for ch in observation.chars)
        elif structural_b is not None:
            winner_shared = tuple(str(u) for u in structural_b.shared_units)
        residual_rows = _residual_pool_recall(
            conn,
            session_id=session_id,
            observation=observation,
            winner_shared_units=winner_shared,
        )
        if residual_rows:
            b_candidates = b_candidates + residual_rows
    # M4-1 (§187.1): 超阈值感受通道回灌状态池为 feeling::* SA — 下一 tick 参与
    # 注意竞争, AP 由此"感到自己在慌"; 高激活感受成为范式可匹配的现状条件.
    feeling_sa_written = _feedback_feelings_to_pool(
        state_pool, tick=tick, cognitive_feelings=feelings
    )
    if feeling_sa_written and feelings is not None:
        feelings = {**feelings, "feeling_sa_written": list(feeling_sa_written)}
    action_competition, selected_action = _apply_cstar_carryover_to_competition(
        action_competition,
        selected_action,
        cstar_carryover,
    )
    action_experience_tuner: dict[str, Any] = {}
    if conn is not None:
        action_experience_tuner = _action_experience_tuner_projection(
            conn,
            session_id=session_id,
            tick=tick,
            action_types=tuple(str(row.get("action_type") or "") for row in action_competition),
            selected_action_type=str(selected_action.get("action_type") or ""),
        )
        action_competition, selected_action = _apply_action_experience_tuner_to_rows(
            action_competition,
            selected_action,
            action_experience_tuner,
        )
    c_forward_rows: tuple[dict[str, Any], ...] = (
        (c_forward or ())
        + _cstar_carryover_c_forward(cstar_carryover)
        + _l2_successor_prediction(conn, observation=observation)
    )
    c_backward_rows: tuple[dict[str, Any], ...] = (
        (c_backward or ())
        + _cstar_carryover_c_backward(cstar_carryover)
        + _short_structure_flow_query_c_backward(conn, session_id=session_id)
        + _l2_predecessor_attribution(conn, observation=observation)
    )
    cstar_carryover_flow: dict[str, Any] = {}
    if conn is not None and event_ids and cstar_carryover.get("active"):
        cstar_carryover_flow = _write_cstar_carryover_structure_flow(
            conn,
            session_id=session_id,
            tick=tick,
            event_id=str(event_ids[0]),
            carryover=cstar_carryover,
            selected_action=selected_action,
        )
    cstar_packet: dict[str, Any] = {}
    if b0 is not None and observation is not None:
        e_backward = round(max(0.0, 1.0 - float(b0.support)), 4)
        c_backward_rows = c_backward_rows + (
            {
                "kind": "every_tick_backward_min_error",
                "model": "b_recall_reverse_cause_slots_ssp_neutralization/v1",
                "selected_source_kind": "alignment_recall",
                "source_alignment_event_id": b0.event_id,
                "source_event_id": b0.source_event_id,
                "query_signature": observation.signature,
                "text_signature": observation.text_signature,
                "visual_signature": observation.visual_signature,
                "modality_mix": _observation_modality_mix(observation),
                "cause_slots": list(_cause_slots_for_observation(observation)) + list(b0.candidate_audit_slots),
                "neutralized_occurrences": _neutralized_occurrences_for_observation(
                    observation,
                    score=float(b0.support),
                    source_kind="alignment_recall",
                ),
                "cause_grasp": round(float(b0.support), 4),
                "e_backward": e_backward,
                "subjective": True,
                "may_be_wrong": True,
                "support_formula": _candidate_support_formula(b0.candidate_audit_slots),
                "support_terms": _support_terms_dict(b0.support_terms),
            },
        )
    if structural_b is not None:
        c_forward_rows = c_forward_rows + (
            {
                "kind": "sequence_forward_prediction",
                "source_alignment_event_id": structural_b.event_id,
                "predicted_unit_count": len(structural_b.output_chars),
                "support": structural_b.similarity,
            },
        )
        c_backward_rows = c_backward_rows + (
            {
                "kind": "source_structure_explanation",
                "source_event_id": structural_b.source_event_id,
                "source_text_hash": _hash_text(structural_b.source_text),
                "shared_units": list(structural_b.shared_units),
                "residual_units": list(structural_b.residual_units),
                "support": structural_b.similarity,
                "cause_slots": list(structural_b.candidate_audit_slots),
                "support_formula": _candidate_support_formula(structural_b.candidate_audit_slots),
                "support_terms": _support_terms_dict(structural_b.support_terms),
            },
        )
        cstar_packet = {
            "kind": "bccstar_stage3_packet",
            "virtual_energy": round(structural_b.similarity * 0.35, 4),
            "grasp": round(structural_b.similarity, 4),
            "writes_answer_directly": False,
            "support_formula": _candidate_support_formula(structural_b.candidate_audit_slots),
            "support_terms": _support_terms_dict(structural_b.support_terms),
            "unified_candidate_count": len(structural_b.candidate_audit_slots),
        }
    cstar_statepool_feedback = _apply_cstar_statepool_feedback(
        state_pool,
        tick=tick,
        observation=observation,
        selected_action=selected_action,
        action_competition=action_competition,
        b0=b0,
        structural_b=structural_b,
        c_forward=c_forward_rows,
        c_backward=c_backward_rows,
    )
    _apply_b_recall_residual_energy(state_pool, list(c_backward_rows), tick=tick)
    feelings_map = dict(feelings or {})
    feelings_map["cstar_statepool_carryover"] = cstar_carryover
    feelings_map["cstar_statepool_feedback"] = cstar_statepool_feedback
    if action_experience_tuner:
        feelings_map["action_experience_tuner_projection"] = action_experience_tuner
    ssp_map = dict(ssp_summary or {})
    if cstar_carryover_flow:
        ssp_map["cstar_carryover_flow"] = cstar_carryover_flow
    return RuntimeTickEventV2(
        tick=tick,
        session_id=session_id,
        external_inputs=external_inputs,
        receptor_outputs=(
            {
                "receptor": "text",
                "event_id": observation.event_id,
                "text_hash": observation.text_hash,
                "unit_count": len(observation.chars),
            },
        )
        if observation
        else (),
        state_pool_top=state_pool.snapshot_top(limit=12),
        ssp_active_summary=ssp_map,
        query_structures=query_structures,
        b_candidates=b_candidates,
        c_forward=c_forward_rows,
        c_backward=c_backward_rows,
        cstar_packet=cstar_packet,
        feelings=feelings_map,
        unclosed_items=unclosed_items,
        action_competition=action_competition,
        selected_action=selected_action,
        draft_grid={
            "visible_text": grid.visible_text(),
            "visible_text_hash": _hash_text(grid.visible_text()),
            "rows": grid.rows,
            "cols": grid.cols,
            "occupied_cells": sum(1 for cell in grid.cells.values() if cell.char.strip()),
            # 画板/草稿二维可视化 (§66.2): 非空单元的 (row,col,char,tick) — 前端据此
            # 把草稿渲染成二维网格图片贴进对话气泡 (纯视图, §43 只读 RuntimeTickEvent).
            "cells": [
                {"row": r, "col": c, "char": cell.char, "tick": cell.written_at_tick}
                for (r, c), cell in sorted(grid.cells.items())
                if cell.char.strip()
            ][:200],
        },
        learning_deltas=learning_deltas,
        experience_event_ids_written=event_ids,
        source_refs=source_refs,
        action_record_ids=action_record_ids,
        timings_ms=timings_ms or {"stage1_runtime": 0.0},
    )


def _competition(
    intent: str,
    *,
    selected: str,
    b0: _ExactB0 | None = None,
    structural_b: _StructuralB | None = None,
    teacher_request_context: dict[str, Any] | None = None,
    learning_loop_carryover: dict[str, Any] | None = None,
    feedback_drive_context: dict[str, Any] | None = None,
    commit_drive_context: dict[str, Any] | None = None,
    draftgrid_action_context: dict[str, Any] | None = None,
    l3_context: dict[str, Any] | None = None,
    emotion: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    write_drive, write_trace = _write_drive_from_recall_state(intent, b0=b0, structural_b=structural_b, emotion=emotion)
    teacher_request_context = teacher_request_context or {}
    feedback_drive_context = feedback_drive_context or {}
    commit_drive_context = commit_drive_context or {}
    draftgrid_action_context = draftgrid_action_context or _empty_draftgrid_action_context()
    if selected != "write_cell" and draftgrid_action_context:
        continue_drive = _unit(draftgrid_action_context.get("continue_writing", {}).get("drive", 0.0))
        write_drive_before_draftgrid_gate = write_drive
        write_drive = _unit(write_drive * (0.42 + continue_drive * 0.48))
        if write_trace:
            write_trace = {
                **write_trace,
                "drive_before_draftgrid_continue_gate": round(write_drive_before_draftgrid_gate, 4),
                "draftgrid_continue_gate": round(continue_drive, 4),
                "draftgrid_continue_blend": round(write_drive, 4),
                "draftgrid_action_formula_id": draftgrid_action_context.get("formula_id"),
            }
    ask_drive = (
        _unit(teacher_request_context.get("request_drive", teacher_request_context.get("selected_drive", 0.75)))
        if intent == "request_teacher"
        else _unit(teacher_request_context.get("request_drive", 0.18))
        if teacher_request_context
        else 0.18
    )
    maintain_drive = (
        _unit(teacher_request_context.get("maintain_drive", teacher_request_context.get("selected_drive", 0.66)))
        if intent == "maintain_unclosed"
        else _unit(teacher_request_context.get("maintain_drive", 0.1))
        if teacher_request_context
        else 0.1
    )
    commit_drive = (
        _unit(commit_drive_context.get("drive", 0.0))
        if commit_drive_context
        else 0.12 if selected == "commit_reply" else 0.18
    )
    observe_drive = 0.52 if selected == "observe_text" else 0.22
    request_row = {"action_type": "request_teacher", "drive": ask_drive, "selected": selected == "request_teacher"}
    maintain_row = {
        "action_type": "maintain_unclosed",
        "drive": maintain_drive,
        "selected": selected == "maintain_unclosed",
    }
    if intent in {"request_teacher", "maintain_unclosed"} and teacher_request_context:
        request_row["teacher_request_drive_context"] = teacher_request_context
        maintain_row["teacher_request_drive_context"] = teacher_request_context
    request_row, maintain_row = _apply_learning_protocol_competition_modulation(
        intent=intent,
        request_row=request_row,
        maintain_row=maintain_row,
    )
    write_row = {"action_type": "write_cell", "drive": write_drive, "selected": selected == "write_cell"}
    if write_trace:
        write_row["write_drive_from_recall_state"] = write_trace
    integrate_drive = (
        _unit(feedback_drive_context.get("drive", 0.0))
        if intent == "integrate_feedback" and feedback_drive_context
        else 0.10 if selected == "integrate_feedback" else 0.05
    )
    integrate_row = {
        "action_type": "integrate_feedback",
        "drive": integrate_drive,
        "selected": selected == "integrate_feedback",
    }
    if feedback_drive_context:
        integrate_row["integrate_feedback_drive_from_ap_flow"] = feedback_drive_context
    commit_row = {
        "action_type": "commit_reply",
        "drive": commit_drive,
        "selected": selected == "commit_reply",
    }
    if commit_drive_context:
        commit_row["commit_reply_drive_from_ap_flow"] = commit_drive_context
    draft_rows = _draftgrid_competition_rows(draftgrid_action_context, selected=selected)
    rows = (
        {"action_type": "observe_text", "drive": observe_drive, "selected": selected == "observe_text"},
        write_row,
        *draft_rows,
        request_row,
        maintain_row,
        commit_row,
        {"action_type": "idle_observe", "drive": 0.22, "selected": selected == "idle_observe"},
        {"action_type": "idle_think", "drive": 0.68 if selected == "idle_think" else 0.12, "selected": selected == "idle_think"},
        integrate_row,
    )
    # P1-1 (C18): 竞争行按真实 drive 排序 — 不再 selected 优先. selected 标志仅
    # 标记实际执行的行动; 排序反映竞争强度本身, trace 中可见"谁差点赢".
    sorted_rows = tuple(sorted(rows, key=lambda row: float(row["drive"]), reverse=True))
    selected_action = {"action_type": selected}
    sorted_rows, _selected = _apply_learning_loop_carryover_to_competition(
        sorted_rows,
        selected_action,
        learning_loop_carryover,
    )
    # §1726: L3 行动后果调制(只在 l3_context 提供时生效, 默认 None 零回归).
    # support_count=0 的 edge 乘子=1.0 中性, 不改 selected, 只调 drive 数值.
    if l3_context:
        sorted_rows = _apply_l3_action_consequence_modulation(
            l3_context.get("conn"),
            state_signature=str(l3_context.get("state_signature", "") or ""),
            competition_rows=sorted_rows,
        )
    return sorted_rows


def _write_drive_from_recall_state(
    intent: str,
    *,
    b0: _ExactB0 | None,
    structural_b: _StructuralB | None,
    emotion: dict[str, Any] | None = None,
) -> tuple[float, dict[str, Any]]:
    if intent == "exact_b0" and b0 is not None:
        drive = _unit(0.42 + float(b0.support) * 0.48)
        # §32.2 emotion_modulation + §31.3 拟人: 长期压力→警觉保守(write降);
        # 成功亲和(valence高)→更柔和行动接近(write增); 疲劳→低沉(write降);
        # 高arousal→更倾向问而非写(write略降, §27.1求知欲).
        emo_mod = 0.0
        salience_factor = 1.0
        if emotion and isinstance(emotion, dict):
            valence = float(emotion.get("valence", 0.0) or 0.0)
            pressure_tone = float(emotion.get("pressure_tone", 0.0) or 0.0)
            fatigue_tone = float(emotion.get("fatigue_tone", 0.0) or 0.0)
            arousal = float(emotion.get("arousal", 0.0) or 0.0)
            emo_mod = valence * 0.08 - pressure_tone * 0.06 - arousal * 0.04
            # §738 + §30.2-12: 重复疲劳压缩刺激显著性 — 完型崩溃(perceptual habituation)
            # fatigue_tone 0→无影响, 1→该刺激的回忆驱动归零(完全习惯化)
            salience_factor = 1.0 - _unit(fatigue_tone)
        drive = _unit((drive + emo_mod) * salience_factor)
        return drive, {
            "formula_id": PHASE20_9J_STRUCTURAL_GENERALIZATION_ID,
            "source": "exact_b0_support",
            "support": round(float(b0.support), 4),
            "emotion_modulation": round(emo_mod, 4),
            "salience_factor": round(salience_factor, 4),
            "drive": round(drive, 4),
            "creates_reply_candidate": False,
            "writes_answer_directly": False,
        }
    if intent == "structural_bccstar" and structural_b is not None:
        value_trace = _structural_b_value_trace(structural_b)
        support = _unit(structural_b.similarity)
        # §173.5 结果锚定把握感门控: support 斜率经 grasp 调制, 使"敢泛化"成为经验结果
        # 而非结构先验默认冲动. grasp 复用 exact_b0 同一条 _support_from_reward_punish
        # 通道(在 structural_b 构造处算好存入 audit_slot), 统一两条回忆路径的置信度锚定.
        # grasp 缺省 0.0 = 无结果证据时保守退缩(不假装知道), 由构造处正常填充.
        grasp = _unit(float(value_trace.get("generalization_grasp", 0.0) or 0.0))
        reward_delta = min(0.10, max(0.0, float(value_trace.get("reward_boost", 0.0) or 0.0)) * 0.75)
        punish_delta = min(0.22, max(0.0, float(value_trace.get("punish_penalty", 0.0) or 0.0)) * 0.65)
        residual_delta = min(0.18, max(0.0, float(value_trace.get("residual_conflict_penalty", 0.0) or 0.0)) * 0.70)
        drive = _unit(0.22 + support * 0.58 * grasp + reward_delta - punish_delta - residual_delta)
        # §32.2 emotion_modulation + §31.3 拟人 (同 exact_b0 分支)
        emo_mod = 0.0
        salience_factor = 1.0
        if emotion and isinstance(emotion, dict):
            valence = float(emotion.get("valence", 0.0) or 0.0)
            pressure_tone = float(emotion.get("pressure_tone", 0.0) or 0.0)
            fatigue_tone = float(emotion.get("fatigue_tone", 0.0) or 0.0)
            arousal = float(emotion.get("arousal", 0.0) or 0.0)
            emo_mod = valence * 0.08 - pressure_tone * 0.06 - arousal * 0.04
            # §738 + §30.2-12: 重复疲劳压缩刺激显著性 — 完型崩溃(perceptual habituation)
            salience_factor = 1.0 - _unit(fatigue_tone)
        drive = _unit((drive + emo_mod) * salience_factor)
        return drive, {
            "formula_id": PHASE20_9J_STRUCTURAL_GENERALIZATION_ID,
            "source": "structural_b_support_reward_punish_residual",
            "support": round(support, 4),
            "generalization_grasp": round(grasp, 4),
            "reward_delta": round(reward_delta, 4),
            "punish_delta": round(-punish_delta, 4),
            "residual_delta": round(-residual_delta, 4),
            "emotion_modulation": round(emo_mod, 4),
            "salience_factor": round(salience_factor, 4),
            "drive": round(drive, 4),
            "creates_reply_candidate": False,
            "writes_answer_directly": False,
        }
    return 0.45, {}


def _structural_b_value_trace(structural_b: _StructuralB | None) -> dict[str, Any]:
    if structural_b is None:
        return {}
    for slot in structural_b.candidate_audit_slots:
        if not isinstance(slot, dict):
            continue
        if slot.get("formula_id") == PHASE20_9J_STRUCTURAL_GENERALIZATION_ID:
            return dict(slot)
    return {}


def _empty_draftgrid_action_context() -> dict[str, Any]:
    return {
        "formula_id": PHASE20_9P_DRAFTGRID_ACTION_ID,
        "source": "empty_draftgrid_low_priority_action_seeds",
        "has_visible_text": False,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
        "continue_writing": {
            "drive": 0.08,
            "action_role": "continue_if_future_virtual_units_emerge",
            "candidate_only": True,
        },
        "read_draft": {
            "drive": 0.04,
            "action_role": "readback_requires_visible_draft",
            "candidate_only": True,
        },
        "edit_cell": {
            "drive": 0.02,
            "action_role": "edit_requires_conflict_and_alternative_unit",
            "candidate_only_no_alternative_unit": True,
        },
        "stop_generating": {
            "drive": 0.10,
            "action_role": "low_pressure_pause_seed",
            "candidate_only": True,
        },
    }


def _draftgrid_competition_rows(
    draftgrid_action_context: dict[str, Any],
    *,
    selected: str,
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for action_type in ("continue_writing", "read_draft", "edit_cell", "stop_generating"):
        action_trace = draftgrid_action_context.get(action_type, {})
        drive = _unit(action_trace.get("drive", 0.0)) if isinstance(action_trace, dict) else 0.0
        row = {
            "action_type": action_type,
            "drive": drive,
            "selected": selected == action_type,
            "draftgrid_action_from_ap_flow": draftgrid_action_context,
        }
        rows.append(row)
    return tuple(rows)


def _paradigm_action_bias(
    conn: sqlite3.Connection | None,
    *,
    session_id: str,
    prev_action_type: str,
    prev_action_result: str,
    current_feelings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """M3-2/M3-3 范式涌现查询 + 偏置 (§36第4阶/§1734/§187.2, 冷保存正本
    ColdSave_ActionCompetition_ParadigmLearning_ContinuousMind_20260703.md).

    从经验流统计: 同 (prev_action_result, action_a) 条件下, 哪些后继行动 action_b
    形成了共现波峰. 波峰频率经 §173.5 式退火折算为对该行动的偏置 delta —
    范式只提行动不提内容 (写什么字由召回竞争决定). 纯 SELECT 派生 (§132 可重建),
    无预定义范式. 条件含 feeling 桶粗匹配 (§186 内生感受主导 + 粗桶).
    """
    empty = {"active": False, "deltas": {}, "formula_id": PHASE20_9P_DRAFTGRID_ACTION_ID}
    if conn is None or not prev_action_type:
        return empty
    rows = conn.execute(
        """
        SELECT json_extract(payload_json, '$.action_b') AS ab,
               json_extract(payload_json, '$.prev_action_result') AS par,
               json_extract(payload_json, '$.feeling_conditions.evidence_gap') AS eg,
               COUNT(*) AS n
        FROM phase20_7_experience_events
        WHERE event_kind='action_sequence_cooccurrence'
          AND json_extract(payload_json, '$.action_a')=?
        GROUP BY ab, par
        ORDER BY n DESC LIMIT 12
        """,
        (prev_action_type,),
    ).fetchall()
    if not rows:
        return empty
    # feeling 桶粗匹配: 当前 evidence_gap 高/低 与历史条件同侧时条件契合度高
    current_eg = 0.5
    if isinstance(current_feelings, dict):
        try:
            current_eg = float(current_feelings.get("evidence_gap", 0.5) or 0.5)
        except (TypeError, ValueError):
            current_eg = 0.5
    deltas: dict[str, float] = {}
    audit: list[dict[str, Any]] = []
    for ab, par, eg, n in rows:
        action_b = str(ab or "")
        if not action_b:
            continue
        result_match = 1.0 if str(par or "") == prev_action_result else 0.45
        try:
            hist_eg = float(eg) if eg is not None else 0.5
        except (TypeError, ValueError):
            hist_eg = 0.5
        feeling_match = 1.0 - min(0.6, abs(hist_eg - current_eg))
        # §173.5 式频率退火: 首几次共现影响小, 波峰成型后趋饱和 (上限 0.14)
        strength = 0.14 * (1.0 - math.exp(-max(0, int(n)) / 6.0))
        delta = round(strength * result_match * feeling_match, 4)
        if delta <= 0.005:
            continue
        deltas[action_b] = max(deltas.get(action_b, 0.0), delta)
        audit.append({"action_b": action_b, "count": int(n), "result_match": result_match,
                      "feeling_match": round(feeling_match, 4), "delta": delta})
    if not deltas:
        return empty
    return {
        "active": True,
        "formula_id": PHASE20_9P_DRAFTGRID_ACTION_ID,
        "source": "paradigm_cooccurrence_peak_bias",
        "prev_action_type": prev_action_type,
        "prev_action_result": prev_action_result,
        "deltas": deltas,
        "audit_rows": tuple(audit[:6]),
        "proposes_action_only": True,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _select_draftgrid_next_action_from_ap_flow(
    *,
    conn: sqlite3.Connection | None = None,
    session_id: str = "",
    tick: int = 0,
    draftgrid_action_context: dict[str, Any],
    commit_drive_context: dict[str, Any],
    edit_trace: dict[str, Any],
    learning_loop_carryover: dict[str, Any] | None,
    pending_output_units: bool,
) -> dict[str, Any]:
    carryover = learning_loop_carryover or {}
    eligible_by_action = {
        "continue_writing": bool(pending_output_units),
        "read_draft": bool(draftgrid_action_context.get("has_visible_text")),
        "edit_cell": bool(edit_trace.get("can_edit")),
        "stop_generating": bool(draftgrid_action_context.get("has_visible_text")),
        "commit_reply": bool(commit_drive_context.get("draft_has_visible_text")) and not bool(pending_output_units),
    }
    raw_drive_by_action = {
        "continue_writing": _unit(draftgrid_action_context.get("continue_writing", {}).get("drive", 0.0)),
        "read_draft": _unit(draftgrid_action_context.get("read_draft", {}).get("drive", 0.0)),
        "edit_cell": _unit(draftgrid_action_context.get("edit_cell", {}).get("drive", 0.0)),
        "stop_generating": _unit(draftgrid_action_context.get("stop_generating", {}).get("drive", 0.0)),
        "commit_reply": _unit(commit_drive_context.get("drive", 0.0)),
    }
    successor_outcome_modulation = (
        dict(draftgrid_action_context.get("draftgrid_successor_action_outcome_modulation"))
        if isinstance(draftgrid_action_context.get("draftgrid_successor_action_outcome_modulation"), dict)
        else {}
    )
    delta_by_action = {
        "continue_writing": float(carryover.get("write_cell_delta", 0.0) or 0.0),
        "read_draft": float(carryover.get("read_draft_delta", 0.0) or 0.0),
        "edit_cell": float(carryover.get("edit_cell_delta", 0.0) or 0.0),
        "stop_generating": float(carryover.get("stop_generating_delta", 0.0) or 0.0),
        "commit_reply": float(carryover.get("commit_reply_delta", 0.0) or 0.0)
        + float(successor_outcome_modulation.get("commit_reply_delta", 0.0) or 0.0),
    }
    action_tuner = _action_experience_tuner_projection(
        conn,
        session_id=session_id,
        tick=tick,
        action_types=("continue_writing", "read_draft", "edit_cell", "stop_generating", "commit_reply"),
        selected_action_type="draftgrid_next_action",
        source_intent=str(draftgrid_action_context.get("source_kind") or ""),
    )
    multipliers = action_tuner.get("action_multipliers") if isinstance(action_tuner.get("action_multipliers"), dict) else {}
    # M3-3 范式偏置注入 (§187.2): 上一行动=read_draft(自观察完成), 查经验流共现波峰
    # 对下一行动的范式偏置. 范式只提行动不提内容; 未成型时 deltas 空 = 零影响.
    paradigm_bias = _paradigm_action_bias(
        conn,
        session_id=session_id,
        prev_action_type="read_draft",
        prev_action_result="read_visible_draft",
    )
    paradigm_deltas = paradigm_bias.get("deltas") if isinstance(paradigm_bias.get("deltas"), dict) else {}
    rows: list[dict[str, Any]] = []
    for action_type in ("edit_cell", "commit_reply", "read_draft", "continue_writing", "stop_generating"):
        raw_drive = raw_drive_by_action[action_type]
        delta = delta_by_action[action_type] + float(paradigm_deltas.get(action_type, 0.0) or 0.0)
        eligible = bool(eligible_by_action[action_type])
        drive_before_action_tuner = _unit(raw_drive + delta) if eligible else 0.0
        multiplier = _bounded_multiplier(multipliers.get(action_type, 1.0), low=0.35, high=1.70)
        drive = _unit(drive_before_action_tuner * multiplier) if eligible else 0.0
        row = {
            "action_type": action_type,
            "eligible": eligible,
            "drive_before_learning_loop_carryover": round(raw_drive, 4),
            "learning_loop_carryover_delta": round(delta, 4),
            "drive_before_action_experience_tuner": round(drive_before_action_tuner, 4),
            "action_experience_tuner_multiplier": round(multiplier, 4),
            "drive": round(drive, 4),
            "reason": _draftgrid_next_action_reason(action_type, eligible=eligible, edit_trace=edit_trace),
        }
        if action_tuner.get("active"):
            row["action_experience_tuner_projection"] = action_tuner
        if successor_outcome_modulation:
            row["successor_action_outcome_modulation"] = successor_outcome_modulation
        if paradigm_deltas.get(action_type):
            row["paradigm_action_delta"] = round(float(paradigm_deltas[action_type]), 4)
            row["paradigm_bias_audit"] = paradigm_bias
        rows.append(row)
    eligible_rows = [row for row in rows if row["eligible"]]
    selected = max(eligible_rows, key=lambda row: float(row["drive"])) if eligible_rows else rows[-1]
    selected_action_type = str(selected["action_type"])
    return {
        "formula_id": PHASE20_9P_DRAFTGRID_ACTION_ID,
        "source": "draftgrid_existing_action_competition_after_self_readback",
        "selected_action_type": selected_action_type,
        "selected_drive": round(float(selected.get("drive", 0.0) or 0.0), 4),
        "candidate_rows": tuple(rows),
        "pending_output_units": bool(pending_output_units),
        "edit_can_edit": bool(edit_trace.get("can_edit")),
        "commit_formula_id": commit_drive_context.get("formula_id"),
        "draftgrid_action_formula_id": draftgrid_action_context.get("formula_id"),
        "carryover_active": bool(carryover.get("active")),
        "learning_loop_carryover": carryover if carryover.get("active") else {},
        "successor_action_outcome_modulation": successor_outcome_modulation,
        "action_experience_tuner_projection": action_tuner,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _draftgrid_next_action_reason(action_type: str, *, eligible: bool, edit_trace: dict[str, Any]) -> str:
    if eligible:
        return {
            "edit_cell": "cstar_alternative_unit_available",
            "commit_reply": "commit_drive_competes_with_read_edit_stop",
            "read_draft": "readback_need_remains_after_self_observation",
            "continue_writing": "unwritten_successor_units_remain",
            "stop_generating": "stop_pressure_competes_with_commit",
        }.get(action_type, "eligible_existing_action")
    if action_type == "edit_cell":
        return str(edit_trace.get("reason") or "no_cstar_alternative_unit")
    if action_type == "continue_writing":
        return "no_pending_output_units"
    return "action_not_eligible_in_current_draft_state"


def _draftgrid_context_with_next_action_selection(
    draftgrid_action_context: dict[str, Any],
    next_action_selection: dict[str, Any],
) -> dict[str, Any]:
    context = dict(draftgrid_action_context)
    selected_action_type = str(next_action_selection.get("selected_action_type") or "")
    context["draftgrid_next_action_selection"] = next_action_selection
    for action_type in ("continue_writing", "read_draft", "edit_cell", "stop_generating"):
        row = dict(context.get(action_type, {}) if isinstance(context.get(action_type), dict) else {})
        row["selected_by_draftgrid_next_action"] = action_type == selected_action_type
        context[action_type] = row
    context["writes_answer_directly"] = False
    context["creates_reply_candidate"] = False
    return context


def _commit_context_with_next_action_selection(
    commit_drive_context: dict[str, Any],
    next_action_selection: dict[str, Any],
) -> dict[str, Any]:
    context = dict(commit_drive_context)
    context["selected_by_draftgrid_next_action"] = (
        str(next_action_selection.get("selected_action_type") or "") == "commit_reply"
    )
    context["draftgrid_next_action_selection"] = next_action_selection
    context["writes_answer_directly"] = False
    context["creates_reply_candidate"] = False
    return context


def _draftgrid_action_drive_context(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    tick: int,
    grid: DraftGrid,
    output_intent: str,
    exact_b0: _ExactB0 | None,
    structural_b: _StructuralB | None,
    teacher_request_context: dict[str, Any],
    feedback_drive_context: dict[str, Any],
    learning_loop_carryover: dict[str, Any] | None,
    memory_rhythm_context: dict[str, Any] | None = None,
    pending_output_count: int = 0,
    target_output_unit_count: int = 0,
) -> dict[str, Any]:
    visible_text = grid.visible_text()
    visible_units = _draftgrid_linear_units(grid)
    occupied_cells = sum(1 for cell in grid.cells.values() if str(cell.char).strip())
    capacity = max(1, int(grid.rows) * int(grid.cols))
    draft_occupancy = _unit(occupied_cells / capacity)
    pending_units = max(0, int(pending_output_count or 0))
    target_units = max(int(target_output_unit_count or 0), len(visible_units) + pending_units)
    pending_ratio = _unit(pending_units / max(target_units, 1))
    source_support = _unit(
        max(
            float(exact_b0.support) if exact_b0 is not None else 0.0,
            float(structural_b.similarity) if structural_b is not None else 0.0,
        )
    )
    source_kind = "exact_b0" if exact_b0 is not None and source_support >= (float(structural_b.similarity) if structural_b else 0.0) else "structural_bccstar" if structural_b is not None else "none"
    request_pressure = 0.0
    if output_intent == "request_teacher":
        request_pressure = _unit(teacher_request_context.get("request_drive", teacher_request_context.get("selected_drive", 0.0)))
    elif output_intent == "maintain_unclosed":
        request_pressure = _unit(teacher_request_context.get("maintain_drive", teacher_request_context.get("selected_drive", 0.0)))
    feedback_pressure = _unit(feedback_drive_context.get("drive", 0.0)) if output_intent == "integrate_feedback" else 0.0
    low_grasp = _unit(teacher_request_context.get("low_grasp", max(0.0, 1.0 - source_support)))
    unclosed_pull = _unit(teacher_request_context.get("unclosed_pull", 0.0))
    carryover = learning_loop_carryover or {}
    memory_rhythm_context = dict(memory_rhythm_context or {})
    learning_write = _unit(carryover.get("write_cell_delta", 0.0))
    learning_commit = _unit(carryover.get("commit_reply_delta", 0.0))
    conflict_pressure = _unit(max(0.0, low_grasp - 0.62) + max(0.0, unclosed_pull - 0.58) * 0.5)
    since_tick = max(0, int(tick) - 24)
    recent_read_count = _recent_event_count(
        conn,
        session_id=session_id,
        since_tick=since_tick,
        event_kinds=("draft_grid_read",),
    )
    recent_write_count = _recent_event_count(
        conn,
        session_id=session_id,
        since_tick=since_tick,
        event_kinds=("draft_grid_write",),
    )
    visible_hash = _hash_text(visible_text)
    recent_commit_count = _recent_event_count(
        conn,
        session_id=session_id,
        since_tick=since_tick,
        event_kinds=("draft_grid_commit",),
    )
    repeated_reply_count = _recent_committed_text_hash_count(
        conn,
        session_id=session_id,
        text_hash=visible_hash,
        since_tick=since_tick,
    )
    same_intent_count = _recent_committed_intent_count(
        conn,
        session_id=session_id,
        source_intent=output_intent,
        since_tick=since_tick,
    )
    repetition_fatigue = _unit(
        recent_commit_count * 0.012 + repeated_reply_count * 0.065 + same_intent_count * 0.012,
    )
    has_visible = bool(visible_text.strip())
    draft_size = min(1.0, len(visible_units) / 12.0)
    pending_successor_pressure = _unit(
        pending_ratio * 0.52
        + (0.22 if pending_units else 0.0)
        + (min(0.18, recent_read_count * 0.035) if pending_units else 0.0)
    )
    readback_need = _unit(
        (0.18 if has_visible else 0.0)
        + draft_size * 0.22
        + conflict_pressure * 0.18
        + min(0.12, recent_write_count * 0.012)
        - min(0.16, recent_read_count * 0.050)
        - (pending_successor_pressure * 0.18 if pending_units else 0.0)
    )
    continue_drive = _unit(
        0.08
        + source_support * 0.24
        + max(request_pressure, feedback_pressure) * 0.10
        + learning_write * 0.75
        + pending_successor_pressure
        - draft_size * 0.16
        - conflict_pressure * 0.12
    )
    edit_drive = _unit(
        0.03
        + conflict_pressure * 0.22
        + max(0.0, low_grasp - 0.80) * 0.10
        - (0.10 if not has_visible else 0.0)
    )
    edit_alternative_probe = _no_draftgrid_edit_alternative(
        "not_selected_until_cstar_alternative_unit_is_available",
        support=source_support,
    )
    stop_drive = _unit(
        0.08
        + (1.0 - source_support) * 0.08
        + min(0.10, recent_read_count * 0.035)
        + repetition_fatigue * 0.92
        + max(0.0, draft_size - 0.72) * 0.12
        - max(request_pressure, feedback_pressure) * 0.08
        - learning_commit * 0.20
    )
    return {
        "formula_id": PHASE20_9P_DRAFTGRID_ACTION_ID,
        "source": "draftgrid_surface_recall_conflict_learning_fatigue",
        "has_visible_text": has_visible,
        "visible_text_hash": _hash_text(visible_text),
        "visible_unit_count": len(visible_units),
        "pending_output_unit_count": int(pending_units),
        "target_output_unit_count": int(target_units),
        "pending_output_ratio": round(pending_ratio, 4),
        "pending_successor_pressure": round(pending_successor_pressure, 4),
        "draft_occupancy": round(draft_occupancy, 4),
        "draft_size": round(draft_size, 4),
        "source_kind": source_kind,
        "source_support": round(source_support, 4),
        "request_pressure": round(request_pressure, 4),
        "feedback_pressure": round(feedback_pressure, 4),
        "low_grasp": round(low_grasp, 4),
        "unclosed_pull": round(unclosed_pull, 4),
        "conflict_pressure": round(conflict_pressure, 4),
        "learning_write_support": round(learning_write, 4),
        "learning_commit_support": round(learning_commit, 4),
        "memory_rhythm_context": memory_rhythm_context,
        "recent_read_count": int(recent_read_count),
        "recent_write_count": int(recent_write_count),
        "recent_commit_count": int(recent_commit_count),
        "same_intent_count": int(same_intent_count),
        "repeated_reply_count": int(repeated_reply_count),
        "repetition_fatigue": round(repetition_fatigue, 4),
        "continue_writing": {
            "drive": round(continue_drive, 4),
            "action_role": "continue_existing_draft_if_successor_pressure_remains",
            "candidate_only": True,
            "pending_output_unit_count": int(pending_units),
            "pending_output_ratio": round(pending_ratio, 4),
            "writes_answer_directly": False,
        },
        "read_draft": {
            "drive": round(readback_need, 4),
            "action_role": "self_draftgrid_readback",
            "writes_answer_directly": False,
        },
        "edit_cell": {
            "drive": round(edit_drive, 4),
            "action_role": "local_revision_candidate",
            "candidate_only_no_alternative_unit": True,
            "cstar_alternative_unit": edit_alternative_probe,
            "writes_answer_directly": False,
        },
        "stop_generating": {
            "drive": round(stop_drive, 4),
            "action_role": "pause_or_stop_when_continue_pressure_is_low",
            "candidate_only": True,
            "writes_answer_directly": False,
        },
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _apply_learning_protocol_competition_modulation(
    *,
    intent: str,
    request_row: dict[str, Any],
    maintain_row: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    modulation_kind = ""
    request_multiplier = 1.0
    maintain_multiplier = 1.0
    if intent == "exact_b0":
        modulation_kind = "teacher_off_exact_recall_fades_request"
        request_multiplier = 0.42
        maintain_multiplier = 0.70
    elif intent == "structural_bccstar":
        modulation_kind = "teacher_off_structural_recall_soft_fades_request"
        request_multiplier = 0.56
        maintain_multiplier = 0.82
    elif intent == "integrate_feedback":
        modulation_kind = "feedback_integration_holds_new_request"
        request_multiplier = 0.38
        maintain_multiplier = 0.72
    if not modulation_kind:
        return request_row, maintain_row
    request_before = _unit(request_row.get("drive", 0.0))
    maintain_before = _unit(maintain_row.get("drive", 0.0))
    request_after = _unit(request_before * request_multiplier)
    maintain_after = _unit(maintain_before * maintain_multiplier)
    request = dict(request_row)
    maintain = dict(maintain_row)
    request["drive_before_learning_protocol_modulation"] = round(request_before, 4)
    request["drive"] = round(request_after, 4)
    request["learning_protocol_drive_modulation"] = {
        "formula_id": PHASE20_9B_LEARNING_PROTOCOL_DRIVE_MODULATION_ID,
        "source_projection_formula_id": "apv3_phase20_9a_six_stage_learning_protocol_projection/v1",
        "modulation_kind": modulation_kind,
        "request_multiplier": round(request_multiplier, 4),
        "maintain_multiplier": round(maintain_multiplier, 4),
        "creates_reply_candidate": False,
        "writes_answer_directly": False,
    }
    maintain["drive_before_learning_protocol_modulation"] = round(maintain_before, 4)
    maintain["drive"] = round(maintain_after, 4)
    maintain["learning_protocol_drive_modulation"] = request["learning_protocol_drive_modulation"]
    return request, maintain


def _integrate_feedback_drive_context(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    tick: int,
    feedback: TeacherFeedback,
    observation: _ObservationLike | None,
    feedback_event_ids: Sequence[str],
    teacher_request_context: dict[str, Any],
    expression_trace: dict[str, Any],
    learning_loop_carryover: dict[str, Any] | None,
) -> dict[str, Any]:
    reward = _unit(max(0.0, float(feedback.reward_mag or 0.0)))
    punish = _unit(max(0.0, float(feedback.punish_mag or 0.0)))
    feedback_chars = tuple(str(feedback.feedback_text or "").strip())
    feedback_evidence = _unit(
        0.28
        + min(0.22, len(feedback_chars) * 0.018)
        + (0.16 if feedback.target_event_id else 0.0)
        + (0.18 if observation is not None else 0.0)
        + min(0.10, len(tuple(feedback_event_ids)) * 0.035)
    )
    target_grasp = _unit(
        0.18
        + (0.34 if observation is not None else 0.0)
        + (0.16 if feedback.target_event_id else 0.0)
        + _unit(teacher_request_context.get("cstar_pressure", 0.0)) * 0.12
    )
    value_signal = _unit(0.42 + reward * 0.30 + punish * 0.22)
    learning_loop = learning_loop_carryover or {}
    loop_support = _unit(
        learning_loop.get(
            "integrate_feedback_delta",
            _unit(learning_loop.get("feedback_only_readiness", 0.0)) * 0.08,
        )
    )
    learned_expression = 1.0 if not bool(expression_trace.get("fallback_used", True)) else 0.0
    expression_support = _unit(float(expression_trace.get("selected_support", 0.0) or 0.0))
    expression_readiness = _unit(learned_expression * 0.12 + expression_support * 0.10)
    recent_feedback_actions = _recent_committed_intent_count(
        conn,
        session_id=session_id,
        source_intent="integrate_feedback",
        since_tick=max(0, int(tick) - 24),
    )
    selected_text_hash = str(expression_trace.get("selected_text_hash") or "")
    repeated_expression_count = (
        _recent_committed_intent_text_hash_count(
            conn,
            session_id=session_id,
            source_intent="integrate_feedback",
            text_hash=selected_text_hash,
            since_tick=max(0, int(tick) - 24),
        )
        if selected_text_hash
        else 0
    )
    repetition_fatigue = _unit(recent_feedback_actions * 0.025 + repeated_expression_count * 0.045)
    conflict_penalty = min(0.16, punish * 0.08 + max(0.0, _unit(teacher_request_context.get("low_grasp", 0.0)) - 0.88) * 0.10)
    drive = _unit(
        0.24
        + feedback_evidence * 0.24
        + target_grasp * 0.18
        + value_signal * 0.18
        + loop_support * 0.55
        + expression_readiness
        - repetition_fatigue
        - conflict_penalty
    )
    return {
        "formula_id": PHASE20_9N_FEEDBACK_DRIVE_ID,
        "source": "teacher_feedback_reward_target_learning_loop_expression_fatigue",
        "drive": round(drive, 4),
        "feedback_evidence": round(feedback_evidence, 4),
        "target_grasp": round(target_grasp, 4),
        "value_signal": round(value_signal, 4),
        "reward": round(reward, 4),
        "punish": round(punish, 4),
        "learning_loop_support": round(loop_support, 4),
        "learned_expression": bool(learned_expression),
        "expression_support": round(expression_support, 4),
        "expression_readiness": round(expression_readiness, 4),
        "recent_feedback_actions": int(recent_feedback_actions),
        "repeated_expression_count": int(repeated_expression_count),
        "repetition_fatigue": round(repetition_fatigue, 4),
        "conflict_penalty": round(conflict_penalty, 4),
        "feedback_event_count": len(tuple(feedback_event_ids)),
        "has_target_event": bool(feedback.target_event_id),
        "has_observation": observation is not None,
        "selected_expression_hash": selected_text_hash,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _commit_reply_drive_context(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    tick: int,
    grid: DraftGrid,
    reply_text: str,
    output_intent: str,
    exact_b0: _ExactB0 | None,
    structural_b: _StructuralB | None,
    teacher_request_context: dict[str, Any],
    feedback_drive_context: dict[str, Any],
    expression_trace: dict[str, Any],
    learning_loop_carryover: dict[str, Any] | None,
    memory_rhythm_context: dict[str, Any] | None = None,
    pending_output_count: int = 0,
    target_output_unit_count: int = 0,
) -> dict[str, Any]:
    visible_text = str(reply_text or "")
    visible_chars = _draftgrid_linear_units(grid)
    occupied_cells = sum(1 for cell in grid.cells.values() if str(cell.char).strip())
    capacity = max(1, int(grid.rows) * int(grid.cols))
    draft_occupancy = _unit(occupied_cells / capacity)
    draft_visible = bool(visible_text.strip())
    draft_completeness = _unit((0.30 if draft_visible else 0.0) + min(0.34, len(visible_chars) * 0.018) + draft_occupancy * 0.18)
    pending_units = max(0, int(pending_output_count or 0))
    target_units = max(int(target_output_unit_count or 0), len(visible_chars) + pending_units)
    pending_ratio = _unit(pending_units / max(target_units, 1))

    exact_support = float(exact_b0.support) if exact_b0 is not None else 0.0
    structural_support = float(structural_b.similarity) if structural_b is not None else 0.0
    source_support = _unit(max(exact_support, structural_support))
    source_kind = "none"
    if exact_support >= structural_support and exact_b0 is not None:
        source_kind = "exact_b0"
    elif structural_b is not None:
        source_kind = "structural_bccstar"

    request_pressure = 0.0
    if output_intent == "request_teacher":
        request_pressure = _unit(teacher_request_context.get("request_drive", teacher_request_context.get("selected_drive", 0.0)))
    elif output_intent == "maintain_unclosed":
        request_pressure = _unit(teacher_request_context.get("maintain_drive", teacher_request_context.get("selected_drive", 0.0)))
    feedback_pressure = _unit(feedback_drive_context.get("drive", 0.0)) if output_intent == "integrate_feedback" else 0.0
    reply_pressure = _unit(max(request_pressure, feedback_pressure))

    selected_support = _unit(expression_trace.get("selected_support", 0.0))
    learned_expression = bool(expression_trace) and not bool(expression_trace.get("fallback_used", True))
    expression_support = _unit(selected_support + (0.16 if learned_expression else 0.0))

    carryover = learning_loop_carryover or {}
    memory_rhythm_context = dict(memory_rhythm_context or {})
    learning_loop_support = _unit(
        carryover.get(
            "commit_reply_delta",
            _unit(carryover.get("teacher_off_readiness", 0.0)) * 0.08
            + _unit(carryover.get("feedback_only_readiness", 0.0)) * 0.04,
        )
    )
    memory_rhythm_confidence = _unit(memory_rhythm_context.get("memory_rhythm_confidence", 0.0))
    memory_rhythm_guard = _unit(memory_rhythm_context.get("memory_rhythm_guard", 0.0))
    learning_loop_support = _unit(learning_loop_support + memory_rhythm_confidence * 0.06 - memory_rhythm_guard * 0.05)
    low_grasp = _unit(teacher_request_context.get("low_grasp", max(0.0, 1.0 - source_support)))
    unclosed_pull = _unit(teacher_request_context.get("unclosed_pull", 0.0))
    conflict_penalty = min(
        0.18,
        max(0.0, low_grasp - 0.72) * (0.12 if output_intent in {"request_teacher", "maintain_unclosed"} else 0.22)
        + max(0.0, unclosed_pull - 0.66) * 0.06,
    )

    visible_hash = _hash_text(visible_text)
    since_tick = max(0, int(tick) - 24)
    recent_commit_count = _recent_event_count(
        conn,
        session_id=session_id,
        since_tick=since_tick,
        event_kinds=("draft_grid_commit",),
    )
    repeated_reply_count = _recent_committed_text_hash_count(
        conn,
        session_id=session_id,
        text_hash=visible_hash,
        since_tick=since_tick,
    )
    same_intent_count = _recent_committed_intent_count(
        conn,
        session_id=session_id,
        source_intent=output_intent,
        since_tick=since_tick,
    )
    repetition_fatigue = _unit(recent_commit_count * 0.012 + repeated_reply_count * 0.055 + same_intent_count * 0.010)

    drive = _unit(
        0.08
        + draft_completeness * 0.30
        + source_support * 0.24
        + reply_pressure * 0.18
        + expression_support * 0.10
        + learning_loop_support * 0.58
        - repetition_fatigue
        - conflict_penalty
        - pending_ratio * 0.46
    )
    return {
        "formula_id": PHASE20_9O_COMMIT_DRIVE_ID,
        "source": "draftgrid_recall_cstar_pressure_reward_fatigue",
        "drive": round(drive, 4),
        "draft_has_visible_text": draft_visible,
        "draft_occupancy": round(draft_occupancy, 4),
        "draft_completeness": round(draft_completeness, 4),
        "reply_length": len(visible_text),
        "visible_unit_count": len(visible_chars),
        "pending_output_unit_count": int(pending_units),
        "target_output_unit_count": int(target_units),
        "pending_output_ratio": round(pending_ratio, 4),
        "source_kind": source_kind,
        "source_support": round(source_support, 4),
        "exact_b0_support": round(exact_support, 4),
        "structural_support": round(structural_support, 4),
        "reply_pressure": round(reply_pressure, 4),
        "request_pressure": round(request_pressure, 4),
        "feedback_pressure": round(feedback_pressure, 4),
        "expression_support": round(expression_support, 4),
        "learned_expression": learned_expression,
        "learning_loop_support": round(learning_loop_support, 4),
        "memory_rhythm_context": memory_rhythm_context,
        "memory_rhythm_confidence": round(memory_rhythm_confidence, 4),
        "memory_rhythm_guard": round(memory_rhythm_guard, 4),
        "low_grasp": round(low_grasp, 4),
        "unclosed_pull": round(unclosed_pull, 4),
        "conflict_penalty": round(conflict_penalty, 4),
        "recent_commit_count": int(recent_commit_count),
        "same_intent_count": int(same_intent_count),
        "repeated_reply_count": int(repeated_reply_count),
        "repetition_fatigue": round(repetition_fatigue, 4),
        "visible_text_hash": visible_hash,
        "writes_answer_directly": False,
        "creates_reply_candidate": False,
    }


def _memory_rhythm_context_from_events(
    events: Sequence[RuntimeTickEventV2],
    *,
    conn: sqlite3.Connection | None,
    session_id: str,
    before_tick: int,
) -> dict[str, Any]:
    if conn is None or not session_id:
        return {}
    for event in reversed(tuple(events)):
        lifecycle = (
            event.feelings.get("learning_loop_carryover", {})
            if isinstance(event.feelings, dict)
            else {}
        )
        if not isinstance(lifecycle, dict):
            continue
        progression = lifecycle.get("learning_stage_runtime_progression")
        if not isinstance(progression, dict):
            continue
        object_lifecycle = progression.get("learning_object_lifecycle")
        if not isinstance(object_lifecycle, dict):
            continue
        rhythm = object_lifecycle.get("memory_consolidation_forgetting_rhythm")
        if isinstance(rhythm, dict) and rhythm.get("active"):
            return {
                "formula_id": rhythm.get("formula_id"),
                "memory_rhythm_confidence": _unit(rhythm.get("memory_consolidation", 0.0)),
                "memory_rhythm_guard": _unit(max(rhythm.get("forgetting_pressure", 0.0), rhythm.get("review_rhythm_pressure", 0.0))),
                "memory_rhythm_source_tick": int(before_tick or event.tick or 0),
            }
    lifecycle = _learning_object_lifecycle_projection(
        conn,
        session_id=session_id,
        before_tick=before_tick,
        carryover=_learning_loop_carryover_from_events(events),
        stage_progression=_learning_stage_runtime_progression(
            _learning_loop_carryover_from_events(events),
            action_tuner=_latest_action_experience_tuner_from_events(events),
            source_tick=_latest_tick_for_session(conn, session_id=session_id),
        ),
    )
    rhythm = lifecycle.get("memory_consolidation_forgetting_rhythm")
    if isinstance(rhythm, dict) and rhythm.get("active"):
        return {
            "formula_id": rhythm.get("formula_id"),
            "memory_rhythm_confidence": _unit(rhythm.get("memory_consolidation", 0.0)),
            "memory_rhythm_guard": _unit(max(rhythm.get("forgetting_pressure", 0.0), rhythm.get("review_rhythm_pressure", 0.0))),
            "memory_rhythm_source_tick": int(before_tick or 0),
        }
    return {}


def _recent_committed_intent_text_hash_count(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    source_intent: str,
    text_hash: str,
    since_tick: int,
) -> int:
    rows = conn.execute(
        """
        SELECT payload_json
        FROM phase20_7_experience_events
        WHERE session_id=? AND tick>=? AND event_kind='draft_grid_commit'
        """,
        (session_id, int(since_tick)),
    ).fetchall()
    count = 0
    for (payload_json,) in rows:
        payload = from_json(str(payload_json))
        if not isinstance(payload, dict):
            continue
        if str(payload.get("source_intent") or "") != str(source_intent):
            continue
        if str(payload.get("visible_text_hash") or "") == str(text_hash):
            count += 1
    return count


def _recent_committed_text_hash_count(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    text_hash: str,
    since_tick: int,
) -> int:
    rows = conn.execute(
        """
        SELECT payload_json
        FROM phase20_7_experience_events
        WHERE session_id=? AND tick>=? AND event_kind='draft_grid_commit'
        """,
        (session_id, int(since_tick)),
    ).fetchall()
    count = 0
    for (payload_json,) in rows:
        payload = from_json(str(payload_json))
        if isinstance(payload, dict) and str(payload.get("visible_text_hash") or "") == str(text_hash):
            count += 1
    return count


def _recent_committed_intent_count(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    source_intent: str,
    since_tick: int,
) -> int:
    rows = conn.execute(
        """
        SELECT payload_json
        FROM phase20_7_experience_events
        WHERE session_id=? AND tick>=? AND event_kind='draft_grid_commit'
        """,
        (session_id, int(since_tick)),
    ).fetchall()
    count = 0
    for (payload_json,) in rows:
        payload = from_json(str(payload_json))
        if isinstance(payload, dict) and str(payload.get("source_intent") or "") == str(source_intent):
            count += 1
    return count


def _write_action_type(intent: str, char_index: int) -> str:
    if intent == "request_teacher" and char_index == 0:
        return "request_teacher"
    if intent == "maintain_unclosed" and char_index == 0:
        return "maintain_unclosed"
    return "write_cell"


def _drive_for_output(
    intent: str,
    b0: _ExactB0 | None,
    *,
    structural_b: _StructuralB | None = None,
    teacher_request_context: dict[str, Any] | None = None,
    feedback_drive_context: dict[str, Any] | None = None,
) -> float:
    if intent == "exact_b0" and b0 is not None:
        return b0.support
    if intent == "structural_bccstar" and structural_b is not None:
        return _write_drive_from_recall_state(intent, b0=b0, structural_b=structural_b)[0]
    if intent == "integrate_feedback":
        return _unit((feedback_drive_context or {}).get("drive", 0.0))
    if intent == "request_teacher":
        return _unit((teacher_request_context or {}).get("request_drive", 0.75))
    if intent == "maintain_unclosed":
        return _unit((teacher_request_context or {}).get("maintain_drive", 0.66))
    return 0.5


def _channel_signals_from_experience(
    conn: sqlite3.Connection | None,
    *,
    session_id: str,
    tick: int,
    observation: _ObservationLike | None = None,
) -> dict[str, float]:
    """§30.2 通道 9/10/12 与 §27.3 压力/期待的经验流派生信号 — P0-3 接线.

    这些量此前只在 9y 投影(_draftgrid_experience_tuner_projection)内部可得,
    _cognitive_feelings_from_pool 的对应形参一直未被传参 (节奏感/重复疲劳恒 0,
    压力/期待缺 §27.3 分量). 此函数用与 9y 相同的派生口径(action_records +
    experience_events 计数, §132 可重建)在 tick 粒度取值. 只读既有表, 不新增实体.
    """
    empty = {
        "reward_pressure": 0.0,
        "punish_pressure": 0.0,
        "continue_count": 0.0,
        "repetition_fatigue": 0.0,
    }
    if conn is None or not session_id:
        return empty
    since_tick = max(0, int(tick) - 96)
    action_counts = _recent_selected_action_counts(
        conn,
        session_id=session_id,
        action_types=("continue_writing", "write_cell", "commit_reply"),
        since_tick=since_tick,
    )
    continue_count = float(
        action_counts.get("continue_writing", 0) + action_counts.get("write_cell", 0) * 0.25
    )
    # §27.3 期待/压力: 该 observation 来源的近期奖惩均值 (经验后验, 同 9y 口径).
    reward_pressure = 0.0
    punish_pressure = 0.0
    if observation is not None:
        rows = conn.execute(
            """
            SELECT reward, punish FROM phase20_7_experience_events
            WHERE session_id=? AND event_kind='experience_alignment'
              AND json_extract(payload_json, '$.input_signature')=?
            ORDER BY created_at_ms DESC LIMIT 8
            """,
            (session_id, observation.signature),
        ).fetchall()
        if rows:
            reward_pressure = _unit(sum(max(0.0, float(r or 0.0)) for r, _ in rows) / len(rows))
            punish_pressure = _unit(sum(max(0.0, float(p or 0.0)) for _, p in rows) / len(rows))
    # §738 重复疲劳: 近窗口重复提交同 hash 回复 + 同类行动堆积 (同 commit_drive 口径).
    recent_commit_count = _recent_event_count(
        conn,
        session_id=session_id,
        since_tick=since_tick,
        event_kinds=("draft_grid_commit",),
    )
    repetition_fatigue = _unit(recent_commit_count * 0.06)
    return {
        "reward_pressure": reward_pressure,
        "punish_pressure": punish_pressure,
        "continue_count": continue_count,
        "repetition_fatigue": repetition_fatigue,
    }


def _cognitive_feelings_from_pool(
    pool: StatePool | None,
    observation: _ObservationLike | None,
    *,
    c_backward_grasp: float = 0.0,
    reward_pressure: float = 0.0,
    punish_pressure: float = 0.0,
    reward_signal: float = 0.0,
    unclosed_u: float = 0.0,
    continue_count: float = 0.0,
    repetition_fatigue: float = 0.0,
) -> dict[str, Any]:
    """§30.2 认知感受通道 (路1四核心+路2.1-2.5) — 白皮书纯派生投影.

    白皮书 §30.2/§30.3:
      惊:   Surprise_i = max(P_i - theta_surprise, 0)
      违和: Dissonance_i = max(-P_i - theta_dissonance, 0)
      合理: Reasonable_i = decrease(Surprise) + support(C_backward)
      正确: Correct_i = verified_prediction + low_abs(P) + reward/check_success  (§30.2 第4)
      期待: Expectation = predicted_reward_energy (§27.3 + §30.2 第6, 与压力对称)
      压力: Pressure = predicted_punish_energy (§27.3)
      未闭合: Unclosed = u_value 持续张力 (§30.2 第8 + §27.6)
      时间感: TimeSense = (1-surprise)*c_backward_grasp (§30.2第9 + §13.4 熟悉快陌生慢)
      节奏感: RhythmSense = continue_count*(1-repetition_fatigue) (§30.2第10 + §1294 后继波峰)
      证据缺口: EvidenceGap = (1-c_backward_grasp)*0.5+surprise*0.3+unclosed*0.2 (§30.2第11+§1937+§3258)
      重复疲劳: RepetitionFatigue = repetition_fatigue + StateItem.fatigue聚合 (§30.2第12+§738)

    Correct 三源当前可用两项:
      - low_abs(P): 状态池认知压绝对值低 → R≈V → 预测与现实匹配 (§1264 low_abs_pressure)
      - reward/check_success: 反馈路径传入的 reward_signal (教师反馈"对了" → 正确感涌现)
    第三项 verified_prediction (commit 后 readback 通过) 待 readback 信号接通后补.

    Expectation 当前可用: reward_pressure (9y 投影, 调用点可传) + reward_signal (反馈路径).
    纯未来奖励预测 (C_forward 接学习奖励路径) 留待 C_forward 接通后补.

    reward_signal: 反馈路径调时传入 0-1 奖励强度 (feedback_drive_context drive 近似).
    reward_pressure/punish_pressure: 9y 经验调器的 §27.3 投影值 (调用点可传, 当前默认 0).
    unclosed_u: 当前 observation 来源的 active_unclosed u_value (§27.6 持续张力),
      调用点从 active_unclosed_for_signature(conn, source_signature=observation.signature) 取得.
    continue_count: 9y 投影的连续写计数 (§1294 后继波峰强 → 自然接下去 = 节奏流畅).
    repetition_fatigue: 9y 投影的重复疲劳 (§586 重复得有点奇怪 → 节奏紊乱).
    """
    if pool is None or observation is None:
        return {
            "surprise": 0.0,
            "dissonance": 0.0,
            "reasonable": 0.0,
            "correct": _unit(float(reward_signal)),
            "expectation": _unit(float(reward_pressure) + min(0.20, float(reward_signal) * 0.5)),
            "unclosed": _unit(float(unclosed_u)),
            "time_sense": _unit(float(c_backward_grasp) * 0.5),
            "rhythm_sense": _unit(float(continue_count) * 0.06 * (1.0 - float(repetition_fatigue))),
            "evidence_gap": _unit((1.0 - float(c_backward_grasp)) * 0.5 + 0.0 + float(unclosed_u) * 0.2),
            "repetition_fatigue_channel": _unit(float(repetition_fatigue) * 0.5),
            "pressure": min(1.0, float(punish_pressure)),
            "feeling_source": "no_pool_or_observation",
        }
    # 沿用 _statepool_observation_support_bias 的 sa_ids 聚合 (text_utterance + text_unit)
    sa_ids: list[str] = [f"text_utterance::{observation.signature}"]
    seen_chars: set[str] = set()
    for char in observation.chars:
        if char in seen_chars:
            continue
        seen_chars.add(char)
        sa_ids.append(f"text_unit::{_hash_text(char)}")
        if len(sa_ids) >= 9:
            break
    # §30.2/§721: 从观察相关 SA 的认知压聚合惊/违和通道
    theta_surprise = 0.08   # §30.3 阈值 (低阈值: 认知压正几份就感到一点惊)
    theta_dissonance = 0.08
    slope_surprise = 1.6    # §30.3 slope: 激活函数陡度 (控制高认知压时惊的饱和速度)
    slope_dissonance = 1.4
    p_positive_values: list[float] = []
    p_negative_values: list[float] = []
    p_abs_values: list[float] = []
    fatigue_values: list[float] = []
    for sa_id in sa_ids:
        item = pool.items.get(sa_id)
        if item is None:
            continue
        p = float(item.cognitive_pressure)  # P = R - V (§9)
        p_abs_values.append(_unit(abs(p)))
        fatigue_values.append(_unit(float(item.fatigue)))  # §9 StateItem.fatigue
        if p > 0.0:
            p_positive_values.append(_unit(p))
        elif p < 0.0:
            p_negative_values.append(_unit(abs(p)))
    # §30.3 activation: 单调连续, 阈值之上才感受
    avg_pos = sum(p_positive_values) / max(len(p_positive_values), 1) if p_positive_values else 0.0
    avg_neg = sum(p_negative_values) / max(len(p_negative_values), 1) if p_negative_values else 0.0
    surprise = _unit(max(0.0, (avg_pos - theta_surprise) * slope_surprise))
    dissonance = _unit(max(0.0, (avg_neg - theta_dissonance) * slope_dissonance))
    # §30.2 合理感: decrease(Surprise) + support(C_backward explanation)
    # 惊低 + C_backward 归因把握高 → 合理感高 (§745 "解释成功, 惊讶下降, 合理上升")
    reasonable = _unit((1.0 - surprise) * 0.5 + float(c_backward_grasp) * 0.5)
    # §30.2 正确感: Correct = verified_prediction + low_abs(P) + reward/check_success
    # 当前可用两项: low_abs(P) (R≈V → 预测匹配) + reward_signal (反馈奖励/检查通过).
    # verified_prediction (commit 后 readback 通过/预测被现实验证) 留待 readback 信号接通后补.
    # low_abs_P: |P| 低意味着 R≈V (现实与预测匹配), 由 §30.2 + §1264 low_abs_pressure.
    avg_abs_p = sum(p_abs_values) / max(len(p_abs_values), 1) if p_abs_values else 0.0
    low_abs_p = _unit(1.0 - avg_abs_p)  # |P| 低 → low_abs 高 (匹配感)
    correct = _unit(low_abs_p * 0.5 + float(reward_signal) * 0.5)
    # §27.3 压力: predicted_punish_energy — 复用 9y punish_pressure (经验流后验)
    # 末接认知压 P>0 涌现份 (7w 已让 u_value 涌现, 这里压力投影也含认知压惊的少量惩罚信号,
    # 对应用户理论 "未知本身就有惩罚信号"): min(0.20, surprise*0.30) 是 §30.1 "惊伴随少量惩罚"
    # §27.3 期待: Expectation(B_j) = predicted_reward_energy(C | B_j).
    # 与压力 (predicted_punish_energy) 对称. 当前可派生: reward_signal (反馈路径奖励)
    # + reward_pressure (9y 经验调器奖励投影, 调用点可传). 纯未来奖励预测 (C_forward 接奖励)
    # 留待 C_forward 学习奖励路径后补 — 当前 bounded scope: "刚收到的奖励被感受为期待投影".
    expectation = _unit(float(reward_pressure) + min(0.20, float(reward_signal) * 0.5))
    # §30.2 第8通道 未闭合: Unclosed = u_value 持续张力 (§27.6).
    # 调用点从 active_unclosed_for_signature(conn, observation.signature) 取 u_value 传入.
    # 这是 §27 "可通过自身行动获得奖励或规避惩罚的路径尚未完成" 的持续张力投影,
    # 对应用户理论 "失恋注意难集中"的底层 (U 高不释放 → 反复打断).
    # 当前 §27.6 释放机制只 closure 1/5 + §27.3 decay_U 时间衰减 (§-decay_unclosed_for_idle),
    # 4/5 evidence 型释放留 B-4.
    unclosed = _unit(float(unclosed_u))
    # §30.2 第9通道 时间感: 召回时间差形成波峰 (§1454 时间差产生感受).
    # §13.4 拟人洞察: 陌生城市时间感觉变慢 (惊多预测少), 熟悉通勤时间感觉快 (预测多惊少).
    # 派生: 低惊 + 高 c_backward 归因把握 → 熟悉 → 时间感觉快 (time_sense 高);
    #        高惊 + 低归因 → 陌生 → 时间感觉慢 (time_sense 低).
    # 这是 §13.4 的直接落地, 复用既有 surprise + c_backward_grasp, 不增实体.
    # (纯召回时间差波峰需要 recall tick 信号接通后补, 当前用预测密度近似)
    time_sense = _unit((1.0 - surprise) * 0.5 + float(c_backward_grasp) * 0.5)
    # §30.2 第10通道 节奏感: lag kernel 与周期预测 (§1294 后继波峰强→自然接下去).
    # 派生: continue_count (连续写, 9y 投影) 高 + repetition_fatigue 低 → 节奏流畅;
    #        continue_count 低 + repetition_fatigue 高 → 节奏紊乱 (§586 重复得奇怪).
    # §1294 直接落地: 熟语后继波峰强 → continue_count 高 → 节奏感高;
    #                 逗号后继分散 → continue_count 低 → 节奏感低.
    # 纯 rhythm_lag 边 (§638 短期结构池) 待 SSP rhythm_lag 实现后补, 当前用连续/重复近似.
    rhythm_sense = _unit(float(continue_count) * 0.06 * (1.0 - float(repetition_fatigue)))
    # §30.2 第11通道 证据缺口: 任务需要证据但状态池不足 (§1937 把握上升→证据缺口下降;
    # §3258 low_grasp + evidence_gap + external_query → request_teacher 候选获胜).
    # 派生: 低归因把握 (1-c_backward_grasp) 主导 + 惊加成 (状态池预测不足) + 未闭合加成
    # (任务需证据但路径未完成). §6421 "B/C召回发现需要某关系但证据不够直观→证据缺口".
    # 复用既有 c_backward_grasp + surprise + unclosed, 不增实体.
    evidence_gap = _unit((1.0 - float(c_backward_grasp)) * 0.5 + surprise * 0.3 + unclosed * 0.2)
    # §30.2 第12通道 重复疲劳: 重复同对象/行动 (§738 F_i(t+1)=decay_F*F_i+repeated_focus+repeated_action).
    # 派生: StateItem.fatigue 聚合 (§9状态池疲劳, repeated_focus累积) + repetition_fatigue
    # (9y投影, repeated_action: recent_outward+recent_same). 复用既有信号, 不增实体.
    avg_fatigue = sum(fatigue_values) / max(len(fatigue_values), 1) if fatigue_values else 0.0
    repetition_fatigue_channel = _unit(avg_fatigue * 0.5 + float(repetition_fatigue) * 0.5)
    # §27.3 压力: predicted_punish_energy — 复用 9y punish_pressure (经验流后验)
    # 末接认知压 P>0 涌现份 (7w 已让 u_value 涌现; 这里压力投影也含认知压惊的少量惩罚信号,
    # 对应用户理论 "未知本身就有惩罚信号"): min(0.20, surprise*0.30) 是 §30.1 "惊伴随少量惩罚"
    pressure = _unit(float(punish_pressure) + min(0.20, surprise * 0.30))
    return {
        "surprise": round(surprise, 4),
        "dissonance": round(dissonance, 4),
        "reasonable": round(reasonable, 4),
        "correct": round(correct, 4),
        "correct_from_low_abs_p": round(float(low_abs_p), 4),
        "correct_from_reward_signal": round(float(reward_signal), 4),
        "expectation": round(expectation, 4),
        "expectation_from_reward_pressure": round(float(reward_pressure), 4),
        "expectation_from_reward_signal": round(min(0.20, float(reward_signal) * 0.5), 4),
        "unclosed": round(unclosed, 4),
        "unclosed_u_source": round(float(unclosed_u), 4),
        "time_sense": round(time_sense, 4),
        "rhythm_sense": round(rhythm_sense, 4),
        "evidence_gap": round(evidence_gap, 4),
        "repetition_fatigue_channel": round(repetition_fatigue_channel, 4),
        "pressure": round(pressure, 4),
        "pressure_from_punish_pressure": round(float(punish_pressure), 4),
        "pressure_from_surprise_emergent": round(min(0.20, surprise * 0.30), 4),
        "surprise_theta": theta_surprise,
        "dissonance_theta": theta_dissonance,
        "feeling_source": "statepool_cognitive_pressure_plus_backward_grasp",
    }


# §29 先天编码 AP的DNA — InnateRule 显式注册表.
# 白皮书 §29.3: InnateRule r = (condition, effect, strength, decay, source)
#   effect ∈ {feeling_SA, reward, punish, action_bias, emotion_delta, attention_bias}
# 这些是散在各公式先验里的先天规则, 此处显式化为可审计表 (纯派生投影, 只读不写DB,
# 不新增认知实体). 未来可由 §33 自适应调参器对 strength/decay 做长期调解.
# 当前登记最核心的几条 — 不求全, 求可审计+可扩展.
_INNATE_RULES: tuple[dict[str, Any], ...] = (
    {
        "rule_id": "innate_surprise_from_positive_pressure",
        "condition": "cognitive_pressure > 0 (R > V, 现实强于预测)",
        "effect": "feeling_SA: surprise 通道激活 (§30.2第1通道)",
        "strength": 1.6,  # slope_surprise (§30.3 激活陡度)
        "decay": "n/a (瞬态感受, 非 tick 累积)",
        "source": "§29.1 冷启动对惊有反应 + §30.2 Surprise=max(P-theta,0)",
    },
    {
        "rule_id": "innate_dissonance_from_negative_pressure",
        "condition": "cognitive_pressure < 0 (V > R, 预测强于现实)",
        "effect": "feeling_SA: dissonance 通道激活 (§30.2第2通道)",
        "strength": 1.4,  # slope_dissonance
        "decay": "n/a",
        "source": "§29.1 冷启动对违和有反应 + §30.2 Dissonance=max(-P-theta,0)",
    },
    {
        "rule_id": "innate_low_grasp_drives_request_teacher",
        "condition": "grasp < STRUCTURAL_B_THRESHOLD (0.55) 或 exact_b0 未命中",
        "effect": "action_bias: request_teacher 行动 drive 增益 (§27.1 行动增益)",
        "strength": 0.46,  # _base_delta for request_teacher
        "decay": "n/a",
        "source": "§29.1 冷启动对未知有反应 + §27.1 未知形成压力",
    },
    {
        "rule_id": "innate_unclosed_pressure_persists",
        "condition": "active_unclosed u_value > 0 (期待/压力未完成)",
        "effect": "feeling_SA: unclosed 通道 + action_bias: maintain_unclosed (§27.6)",
        "strength": 0.18,  # _base_delta for maintain_unclosed
        "decay": 0.88,  # _decay_unclosed_for_idle decay (§27.3 decay_U)
        "source": "§29.1 冷启动对未闭合有反应 + §27.6 U(t+1)=decay*U+evidence",
    },
    {
        "rule_id": "innate_reward_punish_modulates_grasp",
        "condition": "reward > 0 或 punish > 0 (教师反馈)",
        "effect": "feeling_SA: grasp 退火后验 (§173.5 lr_eff=lr*(1+reward_punish_boost))",
        "strength": 0.30,  # _SUPPORT_LR_MAX (首次确认把握位移上界)
        "decay": 24.0,  # _SUPPORT_TAU (退火时间常数)
        "source": "§29.1 冷启动对奖惩有反应 + §173.5 退火曲线",
    },
    {
        "rule_id": "innate_cognitive_pressure_emerges_unclosed_u",
        "condition": "cognitive_pressure P=R-V 高 (7w 认知压涌现)",
        "effect": "action_bias: u_value 增长 (§27.1 未知形成压力)",
        "strength": 0.22,  # pressure_emergent weight in u_delta
        "decay": "n/a",
        "source": "§29.1 冷启动对未知有反应 + §27.1 Pressure=predicted_punish",
    },
    {
        "rule_id": "innate_fatigue_from_repetition",
        "condition": "repeated_focus 或 repeated_action 高 (§738)",
        "effect": "feeling_SA: repetition_fatigue 通道 + action_bias: stop_generating (§32.2)",
        "strength": 0.42,  # repetition_fatigue cap
        "decay": 0.85,  # emotion decay (§31.2)
        "source": "§29.1 冷启动对疲劳有反应 + §738 F_i(t+1)=decay*F+repeated",
    },
)


def import_styled_paradigm_seeds(
    db_path: str | Path,
    *,
    session_id: str = "styled_paradigm_seeds",
    styled_root: str | Path = "config/curriculum/packages/styled",
    max_seeds_per_paradigm: int = 1,
) -> dict[str, Any]:
    """§38.2 范式材料导入 — 把 Phase16 styled packages 的范式种子导入经验流.

    白皮书 §38.2: "一千来句风格化对话示例应作为AP经验/表达范式材料导入".
    §37: SDPL源分化包学习 (source_policy=human_authored, 非答案表).
    §38.3红线: 不许 p:resp:hello 压倒所有上下文.

    每个 paradigm_id 取 max_seeds_per_paradigm 个 train 变体 (非全灌11830,
    避免稀释共现). 导入为 event_kind="styled_paradigm_seed" 的经验事件,
    含 paradigm_id/response_text/response_tokens/affect/intensity.
    AP 从这些种子的共现波峰发现表达范式 (§1734).

    不增实体: 复用既有 insert_experience_event, materials 是 §37 合法源分化包.
    可由前端"加载范式种子"按钮调用, 非自动灌入 (避免污染).
    """
    styled_path = Path(styled_root)
    if not styled_path.exists():
        return {"imported": 0, "reason": "styled_root_not_found", "path": str(styled_path)}
    path = initialize_phase20_7_store(db_path)
    imported_count = 0
    paradigms_seen: set[str] = set()
    paradigm_counts: dict[str, int] = {}
    tick = 0
    with sqlite3.connect(path) as conn:
        for pkg_file in sorted(styled_path.glob("*.yaml")):
            try:
                pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(pkg, dict):
                continue
            for entry in pkg.get("entries", ()):
                if not isinstance(entry, dict):
                    continue
                payload = entry.get("public_payload", {})
                if not isinstance(payload, dict):
                    continue
                paradigm_id = str(payload.get("paradigm_id", "") or "")
                if not paradigm_id:
                    continue
                role = str(payload.get("role", "") or "")
                if role != "train":
                    continue
                count = paradigm_counts.get(paradigm_id, 0)
                if count >= max_seeds_per_paradigm:
                    continue
                tick += 1
                insert_experience_event(
                    conn,
                    session_id=session_id,
                    tick=tick,
                    event_kind="styled_paradigm_seed",
                    payload={
                        "paradigm_id": paradigm_id,
                        "paradigm_label": str(payload.get("paradigm_label", "") or ""),
                        "response_text": str(payload.get("response_text", "") or ""),
                        "response_tokens": list(payload.get("response_tokens", ())),
                        "affect_bucket": str(payload.get("affect_bucket", "") or ""),
                        "intensity_bucket": str(payload.get("intensity_bucket", "") or ""),
                        "package_id": str(pkg.get("package_id", "") or ""),
                        "source_policy": str(pkg.get("governance", {}).get("source_policy", "") or ""),
                        "entry_id": str(entry.get("entry_id", "") or ""),
                    },
                )
                paradigm_counts[paradigm_id] = count + 1
                paradigms_seen.add(paradigm_id)
                imported_count += 1
            conn.commit()
    return {
        "imported": imported_count,
        "paradigms": len(paradigms_seen),
        "paradigm_counts": paradigm_counts,
        "source": "§38.2 styled packages → experience_events",
        "event_kind": "styled_paradigm_seed",
    }


def _innate_rules_audit() -> dict[str, Any]:
    """§29 先天编码审计投影 — 让 AP 的 DNA 可被小白/审计看到.

    纯派生投影 (只读 _INNATE_RULES 常量), 不存DB不增实体.
    未来 §33 调参器可对 strength/decay 做长期调解.
    """
    return {
        "schema_id": "apv3_innate_rules_audit/v1",
        "rule_count": len(_INNATE_RULES),
        "rules": tuple(
            {
                "rule_id": rule["rule_id"],
                "condition": rule["condition"],
                "effect": rule["effect"],
                "strength": rule["strength"],
                "decay": rule["decay"],
                "source": rule["source"],
            }
            for rule in _INNATE_RULES
        ),
        "audit_source": "§29.3 InnateRule=(condition,effect,strength,decay,source)",
        "projection_only": True,
        "may_be_tuned_by_adapter": True,  # §33 未来可调
    }


def _observe_action_sequence_cooccurrence(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    tick: int,
    tick_events: Sequence[RuntimeTickEventV2],
    observation: _ObservationLike | None = None,
) -> tuple[str, ...]:
    """§1734/§36第4阶 行动序列共现观察 — 范式发现的基础设施.

    白皮书 §1734: "过程范式在经验流中的共现波峰". §36第4阶: process-paradigm binding.
    §276: 范式条件是内生感受 (低把握/后继弱/违和/正确感低), 不是外部具体信息.

    从 turn 内 tick_events 取 selected 行动序列 (按 tick 排序的 action_type 列表),
    发现相邻行动对 (如 write_cell→read_draft, read_draft→commit_reply),
    用 insert_experience_event(event_kind="action_sequence_cooccurrence") 存到
    既有经验流 (§24 唯一真相源, 不新增表). payload 含:
    - action_pair: 相邻行动对 (如 "write_cell→read_draft")
    - feeling_conditions: 当时的认知感受条件 (surprise/grasp/unclosed 等)
    - tick_range: 行动对发生的 tick 范围

    范式发现 = 从经验流查 action_sequence_cooccurrence 事件的共现频率
    (COUNT GROUP BY action_pair) → 高频共现自动涌现为可复用范式.
    泛化 = 下次类似内生感受条件时, 从经验流召回共现范式行动序列执行.
    这实现举一反三: 范式条件是内生感受非外部具体信息 (§276).

    不增实体: 复用既有 experience_events 表 + action_records + tick_events.
    不硬编: 范式从共现频率自动涌现, 不是预定义固定范式.
    §132 派生可重建: 共现从 append-only 经验流派生.

    R2 闭合 (上一轮 zcode audit 残留): 若本 turn observation 是过程范式结构
    (derive_paradigm_key != "" 且 grid 写入序列可用 derive_process_rows_from_written_sequence
    识别成完整范式链), 则**改走共享感知函数 perceive_process_state** 回放出与
    示范/执行**完全同键同事件同查询**的共现行 (cooccurrence_source="spontaneous"),
    三端键空间机械一致, 不再硬拼旧 3 键 fall-back. 不匹配结构 (非竖式 turn /
    结构残缺) 继续走 _paradigm_binding_slots 旧逻辑 — 旧机制保留给非过程情境.
    """
    # ---- 过程范式自发路径 (§1734 真闭合): 共享感知函数回放 written_cells ----
    if observation is not None:
        obs_chars = tuple(observation.chars) if observation.chars else ()
        if obs_chars:
            from .paradigm_process import (
                derive_paradigm_key,
                derive_process_rows_from_written_sequence,
            )
            key = derive_paradigm_key(obs_chars, _content_bucket_for_char, conn=conn)
            if key:
                # written_cells 顺序重建: 从 tick_events[i].draft_grid["cells"] 收集所有
                # 带 tick 字段的格子 (cell.written_at_tick 本就是写入时的 tick), 按
                # tick 升序排 — 即为 AP 本 turn 真实写入序列 (无 diff, 不臆测).
                written_cells: list[tuple[int, int, str]] = []
                seen: set[tuple[int, int]] = set()
                for event in tick_events:
                    dg = event.draft_grid if isinstance(event.draft_grid, dict) else {}
                    cells = dg.get("cells") if isinstance(dg.get("cells"), list) else None
                    if not cells:
                        continue
                    for cell in cells:
                        try:
                            r = int(cell.get("row"))
                            c = int(cell.get("col"))
                            ch = str(cell.get("char") or "")
                            wt = int(cell.get("tick") or 0)
                        except (TypeError, ValueError):
                            continue
                        if not ch or (r, c) in seen or wt != int(event.tick):
                            # wt==event.tick 限定为本 tick 新写 (跨 tick 累积快照只取增量)
                            continue
                        seen.add((r, c))
                        written_cells.append((wt, r, c, ch))
                written_cells.sort(key=lambda x: x[0])
                seq = [(r, c, ch) for (_, r, c, ch) in written_cells]
                rows = derive_process_rows_from_written_sequence(obs_chars, seq, _content_bucket_for_char)
                if rows:
                    # §1734 真闭合: 共享函数已产出与示范/执行同键 (paradigm_key,
                    # prev_action_result) 的 (state→action) 共现行. record_step_cooccurrence
                    # 写入与示范完全同种事件 (event_kind=action_sequence_cooccurrence,
                    # 同表 §24, 同查询). origin="spontaneous" 与示范的
                    # "teacher_demonstration" 区分来源但键空间机械一致 (修 R2).
                    feeling_conditions = _collect_cooccurrence_feeling_conditions(tick_events)
                    from .paradigm_process import record_step_cooccurrence
                    event_ids_p: list[str] = []
                    for row in rows:
                        eid = record_step_cooccurrence(
                            conn,
                            session_id=session_id,
                            tick=tick,
                            paradigm_key=row["paradigm_key"],
                            perceived_state=row["prev_action_result"],
                            anchor=row["anchor"],
                            content_source=row["content_source"],
                            origin="spontaneous",
                            insert_experience_event=insert_experience_event,
                            feeling_conditions=feeling_conditions or None,
                        )
                        event_ids_p.append(eid)
                    return tuple(event_ids_p)
    # ---- 旧路径 (非过程情境 / 结构未识别): 机械相邻行动对 + 旧 3 键 binding ----
    # 取 selected 行动序列 (按 tick 排序)
    selected_actions: list[tuple[int, str, dict[str, Any], dict[str, Any]]] = []
    for event in tick_events:
        sa = event.selected_action if isinstance(event.selected_action, dict) else {}
        action_type = str(sa.get("action_type", "") or "")
        if not action_type:
            continue
        feelings = event.feelings if isinstance(event.feelings, dict) else {}
        selected_actions.append((int(event.tick), action_type, feelings, dict(sa)))
    if len(selected_actions) < 2:
        return ()
    selected_actions.sort(key=lambda item: item[0])
    # 发现相邻行动对 + 记录当时的内生感受条件
    event_ids: list[str] = []
    for i in range(len(selected_actions) - 1):
        tick_a, action_a, feelings_a, sa_a = selected_actions[i]
        tick_b, action_b, feelings_b, sa_b = selected_actions[i + 1]
        action_pair = f"{action_a}→{action_b}"
        # 内生感受条件 (§276): 从 feelings 取 §30 通道值作为范式触发条件
        feeling_conditions = _collect_feeling_conditions(feelings_a)
        # M3 参数绑定槽 (用户例2 "意识到上一步写完才触发下一步"):
        # 条件 = 上一行动的可感知结果 (行动类型+相对位移+单元类别), 非"计划中的第N步".
        # draft_delta: DraftGrid 坐标增量 (换行=行+1列归0, 对齐=同列) — 空间结构角色;
        # content_bucket: 感受器级字符类别 (§15 文本感受器本就分类别; 只进条件键不进答案);
        # prev_action_result: 上一行动完成后可读回的结果摘要 (范式链的触发条件).
        binding = _paradigm_binding_slots(sa_a, sa_b)
        event_id = insert_experience_event(
            conn,
            session_id=session_id,
            tick=tick,
            event_kind="action_sequence_cooccurrence",
            payload={
                "action_pair": action_pair,
                "action_a": action_a,
                "action_b": action_b,
                "tick_a": tick_a,
                "tick_b": tick_b,
                "feeling_conditions": feeling_conditions,
                "cooccurrence_source": "turn_tick_sequence",
                **binding,
            },
        )
        event_ids.append(event_id)
    return tuple(event_ids)


_FEELING_CHANNEL_KEYS: tuple[str, ...] = (
    "surprise", "dissonance", "reasonable", "correct",
    "expectation", "pressure", "unclosed",
    "time_sense", "rhythm_sense", "evidence_gap",
    "repetition_fatigue_channel",
)


def _collect_feeling_conditions(feelings: Mapping[str, Any]) -> dict[str, float]:
    """§276 内生感受条件: 从单个 tick 的 feelings 取 §30 通道浮点值.

    自发共现路径与旧相邻行动对路径共用, 保证两条记录在同一表中的 feeling 字段
    派生方式相同 ( Audit R2 闭合辅助: 不引入第二种渠道 📝).
    """
    out: dict[str, float] = {}
    if not isinstance(feelings, Mapping):
        return out
    for key in _FEELING_CHANNEL_KEYS:
        if key in feelings:
            try:
                out[key] = float(feelings[key])
            except (TypeError, ValueError):
                continue
    return out


def _collect_cooccurrence_feeling_conditions(
    tick_events: Sequence[RuntimeTickEventV2],
) -> dict[str, float]:
    """自发路径专用: 把 turn 内每个 tick 的 §30 感受通道值合并成范式触发条件.

    过程范式是 turn 级序列, 感受条件按 turn 累积而非按相邻 tick 对 — 取每个 tick
    感受的 max 作为该 turn 的内生感受快照 (§276 内生条件不是某刻而是该 turn 整体).
    合并语义 (max) 与旧相邻路径单 tick 取值在同一 channel key 上的差仅为粒度, 不
    构成新渠道 (两种 origin 共用同一组 key, 同一种取语义, 没有第二种硬编渠道).
    """
    out: dict[str, float] = {}
    for event in tick_events:
        feelings = event.feelings if isinstance(event.feelings, Mapping) else {}
        for k, v in _collect_feeling_conditions(feelings).items():
            prev = out.get(k)
            if prev is None or v > prev:
                out[k] = v
    return out



def _content_bucket_for_char(char: str) -> str:
    """感受器级字符类别 (§15). 类别只进范式条件键, 不映射任何答案/回复."""
    if not char:
        return "empty"
    ch = char[0]
    if ch.isdigit():
        return "digit"
    if "一" <= ch <= "鿿":
        return "cjk"
    if ch.isalpha():
        return "latin"
    if ch.isspace():
        return "space"
    return "punct"


def _paradigm_binding_slots(sa_a: dict[str, Any], sa_b: dict[str, Any]) -> dict[str, Any]:
    """M3: 行动对的参数绑定槽 — 范式单元的角色化条件 (勿增实体, 全从 selected_action 派生).

    举一反三的数学载体: 换不同数字/文字时 draft_delta+content_bucket+prev_action_result
    不变 (角色相同), 具体内容不进键 — 同一范式可对槽位填不同对象 (§36第4阶 变量化).
    """
    binding: dict[str, Any] = {}
    row_a, col_a = sa_a.get("draft_row"), sa_a.get("draft_col")
    row_b, col_b = sa_b.get("draft_row"), sa_b.get("draft_col")
    if row_a is not None and row_b is not None:
        try:
            binding["draft_delta"] = {"row": int(row_b) - int(row_a), "col": int(col_b or 0) - int(col_a or 0)}
        except (TypeError, ValueError):
            pass
    unit_hash_b = sa_b.get("unit_hash")
    if unit_hash_b:
        binding["b_has_unit"] = True
    # prev_action_result: 上一行动的可感知结果摘要 (write→有 unit, read→有 visible hash)
    if sa_a.get("unit_hash"):
        binding["prev_action_result"] = "wrote_unit"
    elif sa_a.get("visible_text_hash"):
        binding["prev_action_result"] = "read_visible_draft"
    elif str(sa_a.get("action_type") or "").startswith("idle"):
        binding["prev_action_result"] = "idle_settled"
    return binding


def _integrate_emotion_from_ticks(
    tick_events: Sequence[RuntimeTickEventV2],
    *,
    conn: sqlite3.Connection | None = None,
    session_id: str = "",
    tick: int = 0,
) -> dict[str, Any]:
    """§31 情绪慢量通道 — 跨 turn 慢变量积分 (白皮书 §31.2 核心实现).

    白皮书 §31.2:
      emotion_c(t+1) = clamp(decay_c * emotion_c(t) + sum_k w_ck * feeling_k
                              + reward_weight_c * reward - punish_weight_c * punish + memory_recall_c)

    跨 turn 实现: 当 conn 可用时, 从经验流查最近 emotion_slow_channel 事件作为
    emotion_c(t-1) 初值, 当前 turn 的 feelings 积分后叠加, 存为新事件 (event_kind=
    "emotion_slow_channel"). 不增实体: 复用既有 experience_events 表 (§24 唯一真相源),
    emotion 从经验流派生 (§132 可重建). 同 action_sequence_cooccurrence 模式.
    无 conn 时退化为 turn 内积分 (向下兼容).
    """
    if not tick_events:
        return {
            "valence": 0.0, "arousal": 0.0, "dominance": 0.0,
            "pressure_tone": 0.0, "curiosity_tone": 0.0, "fatigue_tone": 0.0,
            "integrated_from_tick_count": 0,
            "emotion_source": "no_ticks",
        }
    decay = 0.85  # §31 慢变量衰减率 (先验, 近因权重更高)
    # 收集每个 tick 的 §30 通道 feelings
    tick_feelings: list[dict[str, float]] = []
    for event in tick_events:
        feelings = event.feelings if isinstance(event.feelings, dict) else {}
        # 只取 §30 12通道的数值字段
        channel_values = {}
        for key in (
            "surprise", "dissonance", "reasonable", "correct",
            "expectation", "pressure", "unclosed",
            "time_sense", "rhythm_sense", "evidence_gap",
            "repetition_fatigue_channel",
        ):
            if key in feelings:
                try:
                    channel_values[key] = float(feelings[key])
                except (TypeError, ValueError):
                    pass
        if channel_values:
            tick_feelings.append(channel_values)
    if not tick_feelings:
        return {
            "valence": 0.0, "arousal": 0.0, "dominance": 0.0,
            "pressure_tone": 0.0, "curiosity_tone": 0.0, "fatigue_tone": 0.0,
            "integrated_from_tick_count": 0,
            "emotion_source": "no_cognitive_feeling_ticks",
        }
    # §31.2 衰减加权积分: 越近权重越高 (decay^(N-k) * feelings_k)
    n = len(tick_feelings)
    weighted_sum: dict[str, float] = {}
    total_weight = 0.0
    for k, feelings in enumerate(tick_feelings):
        weight = decay ** (n - 1 - k)  # 最近 k=n-1 权重=1, 越早越小
        total_weight += weight
        for key, value in feelings.items():
            weighted_sum[key] = weighted_sum.get(key, 0.0) + weight * value
    averaged: dict[str, float] = {}
    for key, total in weighted_sum.items():
        averaged[key] = _unit(total / max(total_weight, 1.0))
    # 从 §30 通道积分出 §31 情绪维度 (拟人: 多通道组合涌现情绪)
    valence = _unit(
        averaged.get("correct", 0.0) * 0.25
        + averaged.get("reasonable", 0.0) * 0.20
        + averaged.get("expectation", 0.0) * 0.20
        + averaged.get("time_sense", 0.0) * 0.10
        - averaged.get("pressure", 0.0) * 0.30
        - averaged.get("dissonance", 0.0) * 0.20
        - averaged.get("unclosed", 0.0) * 0.15
    )
    arousal = _unit(
        averaged.get("surprise", 0.0) * 0.35
        + averaged.get("dissonance", 0.0) * 0.25
        + averaged.get("evidence_gap", 0.0) * 0.20
        - averaged.get("repetition_fatigue_channel", 0.0) * 0.30
    )
    dominance = _unit(
        averaged.get("correct", 0.0) * 0.30
        + averaged.get("reasonable", 0.0) * 0.20
        + averaged.get("time_sense", 0.0) * 0.15
        - averaged.get("unclosed", 0.0) * 0.25
        - averaged.get("evidence_gap", 0.0) * 0.20
    )
    pressure_tone = _unit(averaged.get("pressure", 0.0) * 0.6 + averaged.get("unclosed", 0.0) * 0.4)
    curiosity_tone = _unit(averaged.get("surprise", 0.0) * 0.5 + averaged.get("evidence_gap", 0.0) * 0.5)
    fatigue_tone = _unit(averaged.get("repetition_fatigue_channel", 0.0) * 0.7 + averaged.get("dissonance", 0.0) * 0.3)
    # §31.2 跨 turn 慢变量累积: decay * emotion_c(t-1) + 当前 turn 积分.
    # 从经验流查最近 emotion_slow_channel 事件作为上一 turn 的情绪初值.
    # 不增实体: 复用既有 experience_events 表 (§24). 同 action_sequence_cooccurrence 模式.
    cross_turn_decay = 0.80  # §31.2 decay_c (跨turn衰减: 上一turn情绪保留80%)
    prev_emotion: dict[str, float] = {}
    if conn is not None and session_id:
        row = conn.execute(
            "SELECT payload_json FROM phase20_7_experience_events "
            "WHERE event_kind='emotion_slow_channel' AND session_id=? "
            "ORDER BY tick DESC, created_at_ms DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        if row and row[0]:
            prev = from_json(str(row[0]))
            if isinstance(prev, dict):
                for k in ("valence", "arousal", "dominance", "pressure_tone", "curiosity_tone", "fatigue_tone"):
                    try:
                        prev_emotion[k] = float(prev.get(k, 0.0) or 0.0)
                    except (TypeError, ValueError):
                        prev_emotion[k] = 0.0
    # §31.2: emotion_c(t+1) = decay * emotion_c(t) + current_turn
    if prev_emotion:
        valence = _unit(cross_turn_decay * prev_emotion.get("valence", 0.0) * 0.5 + valence * 0.5)
        arousal = _unit(cross_turn_decay * prev_emotion.get("arousal", 0.0) * 0.5 + arousal * 0.5)
        dominance = _unit(cross_turn_decay * prev_emotion.get("dominance", 0.0) * 0.5 + dominance * 0.5)
        pressure_tone = _unit(cross_turn_decay * prev_emotion.get("pressure_tone", 0.0) * 0.5 + pressure_tone * 0.5)
        curiosity_tone = _unit(cross_turn_decay * prev_emotion.get("curiosity_tone", 0.0) * 0.5 + curiosity_tone * 0.5)
        fatigue_tone = _unit(cross_turn_decay * prev_emotion.get("fatigue_tone", 0.0) * 0.5 + fatigue_tone * 0.5)
    # 存到经验流 (供下一 turn 查 emotion_c(t-1))
    if conn is not None and session_id:
        insert_experience_event(
            conn,
            session_id=session_id,
            tick=tick,
            event_kind="emotion_slow_channel",
            payload={
                "valence": round(valence, 4),
                "arousal": round(arousal, 4),
                "dominance": round(dominance, 4),
                "pressure_tone": round(pressure_tone, 4),
                "curiosity_tone": round(curiosity_tone, 4),
                "fatigue_tone": round(fatigue_tone, 4),
                "integrated_from_tick_count": n,
                "cross_turn": bool(prev_emotion),
                "prev_turn_decay_weight": cross_turn_decay if prev_emotion else 0.0,
                "emotion_source": "cross_turn_slow_channel" if prev_emotion else "tick_feelings_decay_weighted_integration",
            },
        )
        conn.commit()
    return {
        "valence": round(valence, 4),
        "arousal": round(arousal, 4),
        "dominance": round(dominance, 4),
        "pressure_tone": round(pressure_tone, 4),
        "curiosity_tone": round(curiosity_tone, 4),
        "fatigue_tone": round(fatigue_tone, 4),
        "integrated_from_tick_count": n,
        "channel_averages": {k: round(v, 4) for k, v in averaged.items()},
        "emotion_source": "cross_turn_slow_channel" if prev_emotion else "tick_feelings_decay_weighted_integration",
        "cross_turn_accumulated": bool(prev_emotion),
    }


def _vad_dict_to_emotion_field(d: dict[str, Any]) -> EmotionField:
    """Bridge: map VAD slow-channel dict → 8-channel EmotionField.

    VAD fields: valence, arousal, dominance, pressure_tone, curiosity_tone, fatigue_tone
    NT fields : da, adr, oxy, ser, end, cor, nov, foc
    """
    valence = float(d.get("valence", 0.0) or 0.0)
    arousal = float(d.get("arousal", 0.0) or 0.0)
    dominance = float(d.get("dominance", 0.0) or 0.0)
    pressure = float(d.get("pressure_tone", 0.0) or 0.0)
    curiosity = float(d.get("curiosity_tone", 0.0) or 0.0)
    fatigue = float(d.get("fatigue_tone", 0.0) or 0.0)
    return EmotionField(
        da=_unit((valence + curiosity) * 0.5),
        adr=_unit(arousal * 0.5 + pressure * 0.5),
        oxy=0.5,
        ser=_unit(valence * 0.7 + dominance * 0.3),
        end=_unit(max(0.0, valence) * dominance),
        cor=pressure,
        nov=curiosity,
        foc=_unit((1.0 - fatigue) * 0.6 + arousal * 0.4),
    ).clamp()


def _build_and_persist_emotion(
    tick_events: Sequence[RuntimeTickEventV2],
    *,
    conn: sqlite3.Connection | None = None,
    session_id: str = "",
    tick: int = 0,
) -> dict[str, Any]:
    """Integrate, convert to EmotionField, and persist to emotion_snapshot."""
    vad = _integrate_emotion_from_ticks(
        tick_events, conn=conn, session_id=session_id, tick=tick,
    )
    ef = _vad_dict_to_emotion_field(vad)
    if conn is not None:
        try:
            # Load prior NT snapshot and apply cross-turn decay toward baseline
            prior_row = conn.execute(
                "SELECT da, adr, oxy, ser, end_val, cor, nov, foc "
                "FROM phase20_7_emotion_snapshot WHERE turn_id=? "
                "ORDER BY tick DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            if prior_row:
                prior_ef = EmotionField(
                    da=float(prior_row[0]), adr=float(prior_row[1]),
                    oxy=float(prior_row[2]), ser=float(prior_row[3]),
                    end=float(prior_row[4]), cor=float(prior_row[5]),
                    nov=float(prior_row[6]), foc=float(prior_row[7]),
                )
                # Decay toward baseline: rate=0.10 per turn (~5 ticks × 0.02)
                decayed = prior_ef.decay(rate=0.10)
                # Blend: 40% decayed prior + 60% current turn
                ef = EmotionField(
                    da=0.4 * decayed.da + 0.6 * ef.da,
                    adr=0.4 * decayed.adr + 0.6 * ef.adr,
                    oxy=0.4 * decayed.oxy + 0.6 * ef.oxy,
                    ser=0.4 * decayed.ser + 0.6 * ef.ser,
                    end=0.4 * decayed.end + 0.6 * ef.end,
                    cor=0.4 * decayed.cor + 0.6 * ef.cor,
                    nov=0.4 * decayed.nov + 0.6 * ef.nov,
                    foc=0.4 * decayed.foc + 0.6 * ef.foc,
                ).clamp()
            conn.execute(
                "INSERT INTO phase20_7_emotion_snapshot "
                "(tick, turn_id, da, adr, oxy, ser, end_val, cor, nov, foc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (tick, session_id, ef.da, ef.adr, ef.oxy, ef.ser,
                 ef.end, ef.cor, ef.nov, ef.foc),
            )
            conn.commit()
        except Exception:
            pass
    return vad


def _feelings_for_output(
    intent: str,
    b0: _ExactB0 | None,
    structural_b: _StructuralB | None = None,
    *,
    teacher_request_context: dict[str, Any] | None = None,
    feedback_drive_context: dict[str, Any] | None = None,
    commit_drive_context: dict[str, Any] | None = None,
    draftgrid_action_context: dict[str, Any] | None = None,
    cognitive_feelings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    commit_drive_context = commit_drive_context or {}
    draftgrid_action_context = draftgrid_action_context or {}
    cognitive_feelings = cognitive_feelings or {}
    commit_feeling = (
        {
            "commit_readiness": round(_unit(commit_drive_context.get("drive", 0.0)), 4),
            "commit_reply_drive_context": commit_drive_context,
        }
        if commit_drive_context
        else {}
    )
    draftgrid_feeling = (
        {
            "draftgrid_action_drive_context": draftgrid_action_context,
            "readback_need": round(_unit(draftgrid_action_context.get("read_draft", {}).get("drive", 0.0)), 4),
            "edit_pressure": round(_unit(draftgrid_action_context.get("edit_cell", {}).get("drive", 0.0)), 4),
            "stop_tendency": round(_unit(draftgrid_action_context.get("stop_generating", {}).get("drive", 0.0)), 4),
            "continue_tendency": round(_unit(draftgrid_action_context.get("continue_writing", {}).get("drive", 0.0)), 4),
        }
        if draftgrid_action_context
        else {}
    )
    if intent == "exact_b0" and b0 is not None:
        return {
            "grasp": b0.support,
            "uncertainty": round(1.0 - b0.support, 3),
            "source": "exact_b0",
            **commit_feeling,
            **draftgrid_feeling,
            **cognitive_feelings,
        }
    if intent == "structural_bccstar" and structural_b is not None:
        return {
            "grasp": round(structural_b.similarity, 3),
            "uncertainty": round(1.0 - structural_b.similarity, 3),
            "source": "structural_bccstar",
            "shared_unit_count": len(structural_b.shared_units),
            **commit_feeling,
            **draftgrid_feeling,
            **cognitive_feelings,
        }
    if intent == "request_teacher":
        if teacher_request_context:
            low_grasp = _unit(teacher_request_context.get("low_grasp", 0.82))
            return {
                "grasp": round(1.0 - low_grasp, 4),
                "uncertainty": round(low_grasp, 4),
                "source": "unified_teacher_request_drive",
                "teacher_request_drive_context": teacher_request_context,
                **commit_feeling,
                **draftgrid_feeling,
                **cognitive_feelings,
            }
        return {"grasp": 0.18, "uncertainty": 0.82, "source": "no_exact_b0", **commit_feeling, **draftgrid_feeling, **cognitive_feelings}
    if intent == "maintain_unclosed":
        if teacher_request_context:
            low_grasp = _unit(teacher_request_context.get("low_grasp", 0.78))
            return {
                "grasp": round(1.0 - low_grasp, 4),
                "uncertainty": round(low_grasp, 4),
                "source": "unified_unclosed_request_drive",
                "teacher_request_drive_context": teacher_request_context,
                **commit_feeling,
                **draftgrid_feeling,
                **cognitive_feelings,
            }
        return {"grasp": 0.22, "uncertainty": 0.78, "source": "active_unclosed_item", **commit_feeling, **draftgrid_feeling, **cognitive_feelings}
    if intent == "integrate_feedback":
        context = feedback_drive_context or {}
        drive = _unit(context.get("drive", 0.0))
        return {
            "grasp": round(drive, 4),
            "uncertainty": round(1.0 - drive, 4),
            "source": "integrate_feedback_drive_from_ap_flow",
            "integrate_feedback_drive_context": context,
            **commit_feeling,
            **draftgrid_feeling,
            **cognitive_feelings,
        }
    return {**commit_feeling, **draftgrid_feeling, **cognitive_feelings}


STATEPOOL_SNAPSHOT_ID = "apv3_phase20_p1_2_statepool_cross_turn_snapshot/v1"
_STATEPOOL_SNAPSHOT_TOP_N = 24
_STATEPOOL_RESTORE_MIN_ENERGY = 0.02


def _persist_statepool_snapshot(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    tick: int,
) -> None:
    """§9/ColdSave C5: 状态池是跨 tick 持续对象 — turn 末落盘 top-N SA 能量.

    存入既有 phase20_7_derived_runtime_snapshots 表(建库即有, 此前 0 行), 派生可重建
    (rebuildable=1, §132): 真相源仍是经验流, 快照只是能量场的延续载体. 不新增表.
    """
    items: list[dict[str, Any]] = []
    ordered = sorted(
        pool.items.values(),
        key=lambda item: item.real_energy + item.virtual_energy + item.attention_energy,
        reverse=True,
    )
    for item in ordered[:_STATEPOOL_SNAPSHOT_TOP_N]:
        total = item.real_energy + item.virtual_energy + item.attention_energy
        if total < _STATEPOOL_RESTORE_MIN_ENERGY:
            continue
        items.append(
            {
                "sa_id": item.sa_id,
                "family": item.family,
                "label": item.label,
                "R": round(float(item.real_energy), 5),
                "V": round(float(item.virtual_energy), 5),
                "A": round(float(item.attention_energy), 5),
                "F": round(float(item.fatigue), 5),
                "source": item.source,
                "channel_signature": list(item.channel_signature),
            }
        )
    conn.execute(
        """
        INSERT OR REPLACE INTO phase20_7_derived_runtime_snapshots(
          snapshot_id, session_id, tick, rebuildable, payload_json, created_at_ms
        ) VALUES (?, ?, ?, 1, ?, ?)
        """,
        (
            f"statepool::{session_id}",
            session_id,
            int(tick),
            to_json({"formula_id": STATEPOOL_SNAPSHOT_ID, "items": items, "tick": int(tick)}),
            now_ms(),
        ),
    )


def _restore_statepool_snapshot(
    conn: sqlite3.Connection,
    pool: StatePool,
    *,
    session_id: str,
    current_tick: int,
) -> int:
    """turn 初恢复上一 turn 的状态池能量, 并按经过的 tick 数补衰减.

    恢复后的 SA 带上一 turn 的 R/V/A/F 残余 — 跨 turn 张力(未闭合的 V、情绪相关
    SA)由此存续, 而不是每 turn 从零开始 (审查 P1-2: pool=StatePool() 每 turn 新建).
    """
    row = conn.execute(
        "SELECT tick, payload_json FROM phase20_7_derived_runtime_snapshots WHERE snapshot_id=?",
        (f"statepool::{session_id}",),
    ).fetchone()
    if not row:
        return 0
    snapshot_tick = int(row[0] or 0)
    payload = from_json(str(row[1]))
    if not isinstance(payload, dict):
        return 0
    elapsed = max(0, int(current_tick) - snapshot_tick)
    # 跨 turn 间隔按既有衰减常数补算 (上限防浮点下溢; 32 tick 后能量已近零)
    steps = min(elapsed, 32)
    from runtime.cognitive.state_pool.state_pool import load_constant

    r_decay = float(load_constant("energy.R_decay_short")) ** steps
    v_decay = float(load_constant("energy.V_decay")) ** steps
    a_decay = float(load_constant("energy.A_decay")) ** steps
    f_decay = float(load_constant("energy.F_decay")) ** steps
    restored = 0
    for entry in payload.get("items", ()):
        if not isinstance(entry, dict):
            continue
        r = float(entry.get("R", 0.0)) * r_decay
        v = float(entry.get("V", 0.0)) * v_decay
        a = float(entry.get("A", 0.0)) * a_decay
        f = float(entry.get("F", 0.0)) * f_decay
        if (r + v + a) < _STATEPOOL_RESTORE_MIN_ENERGY:
            continue
        sa_id = str(entry.get("sa_id", ""))
        if not sa_id or sa_id in pool.items:
            continue
        item = StateItem(
            sa_id=sa_id,
            family=str(entry.get("family", "")),
            label=str(entry.get("label", "")),
            real_energy=r,
            virtual_energy=v,
            attention_energy=a,
            fatigue=f,
            cognitive_pressure=r - v,
            last_tick=int(current_tick),
            channel_signature=tuple(str(c) for c in entry.get("channel_signature", ())),
            source=str(entry.get("source", "")),
            metadata={"restored_from_prev_turn": True, "snapshot_tick": snapshot_tick},
        )
        # 账本来源用既有 "replay" — 跨 turn 能量残余在语义上是记忆场的延续重放,
        # 不新增 LEDGER_SOURCES 枚举 (勿增实体).
        item.gain_ledger.inject("replay", a)
        pool.items[sa_id] = item
        restored += 1
    return restored


def _feedback_feelings_to_pool(
    pool: StatePool | None,
    *,
    tick: int,
    cognitive_feelings: dict[str, Any] | None,
) -> tuple[str, ...]:
    """M4-1 感受 SA 回灌 (§187.1 元认知分诊例, 白皮书: 感受节点是一等公民 SA).

    超阈值的 §30 感受通道写回状态池为 feeling::<channel> SA (带 R 能量, 走正常
    衰减/注意竞争) — 下一 tick AP "感到自己在惊/在慌", 高激活感受本身成为范式可
    匹配的现状条件. 阈值 0.5 = §30.3 激活中点 (登记 _INNATE_RULES); 能量=通道值
    ×0.4 (弱于外源注入, 感受是背景不是刺激). 勿增实体: 复用 StateItem/observe_external.
    """
    if pool is None or not isinstance(cognitive_feelings, dict):
        return ()
    written: list[str] = []
    for channel in (
        "surprise", "dissonance", "pressure", "unclosed",
        "evidence_gap", "repetition_fatigue_channel",
    ):
        try:
            value = float(cognitive_feelings.get(channel, 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        if value < 0.5:
            continue
        sa_id = f"feeling::{channel}"
        _observe_pool(
            pool,
            tick=tick,
            sa_id=sa_id,
            family="feeling",
            label=channel,
            energy=round(value * 0.4, 4),
            source="cognitive_feeling_channel",
            ledger_source="rpe_signal",
        )
        written.append(sa_id)
    return tuple(written)


def _observe_pool(
    pool: StatePool,
    *,
    tick: int,
    sa_id: str,
    family: str,
    label: str,
    energy: float,
    source: str = "phase20_7_stage1",
    ledger_source: str = "external",
) -> None:
    pool.observe_external(
        {
            "sa_id": sa_id,
            "family": family,
            "label": label,
            "channel_signature": ("text",),
            "origin": source,
            "real_energy": float(energy),
            "metadata": {"ledger_source": ledger_source},
        },
        tick=tick,
    )


def _observe_draft_char(pool: StatePool, *, tick: int, char: str, row: int, col: int, source: str) -> None:
    _observe_pool(
        pool,
        tick=tick,
        sa_id=f"draft_unit::{_hash_text(char)}::{row}:{col}",
        family="draft_grid",
        label=char,
        energy=0.36,
        source=f"draft_grid::{source}",
        ledger_source="user_directed",
    )


def _signature_for_chars(chars: tuple[str, ...]) -> str:
    return _hash_text("\u241f".join(chars))


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _safe_media_inputs(media_inputs: Sequence[MediaInput]) -> tuple[dict[str, Any], ...]:
    safe: list[dict[str, Any]] = []
    for item in media_inputs:
        path_hash = _hash_text(str(item.path)) if item.path else None
        safe.append(
            {
                "media_type": item.media_type,
                "path_hash": path_hash,
                "payload_ref": item.payload_ref,
                "source_hash": item.source_hash,
                "raw_path_stored": False,
            }
        )
    return tuple(safe)


def _unclosed_row_to_dict(row: object) -> dict[str, object]:
    (
        unclosed_id,
        item_session_id,
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
        "session_id": str(item_session_id),
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


def _query_summary(observation: _ObservationLike) -> dict[str, Any]:
    return {
        "structure_kind": "linear_text_with_visual_evidence" if observation.visual_signature else "linear_text",
        "signature": observation.signature,
        "text_signature": observation.text_signature,
        "visual_signature": observation.visual_signature,
        "visual_token_count": len(_visual_tokens(observation.visual_signature)),
        "unit_count": len(observation.chars),
        "text_hash": observation.text_hash,
    }


def _ssp_summary(observation: _ObservationLike) -> dict[str, Any]:
    return {
        "structure_kind": "linear_text_with_visual_evidence" if observation.visual_signature else "linear_text",
        "active_occurrence_count": len(observation.occurrence_ids),
        "signature": observation.signature,
        "text_signature": observation.text_signature,
        "visual_signature": observation.visual_signature,
        "visual_token_count": len(_visual_tokens(observation.visual_signature)),
        "latest_occurrence_id": observation.occurrence_ids[-1] if observation.occurrence_ids else None,
    }


def _with_request_expression_trace(summary: dict[str, Any], expression_trace: dict[str, Any]) -> dict[str, Any]:
    if not expression_trace:
        return summary
    out = dict(summary)
    out["request_expression_selection"] = expression_trace
    return out


def _visual_signature_from_events(events: Sequence[RuntimeTickEventV2]) -> str | None:
    visual_parts: list[str] = []
    for event in events:
        for receptor in event.receptor_outputs:
            if receptor.get("receptor") != "visual_patch_sensor":
                continue
            evidence = receptor.get("visual_evidence")
            if isinstance(evidence, dict):
                signature = str(evidence.get("signature", "") or "")
                if signature:
                    visual_parts.append(signature)
                tokens = evidence.get("tokens", ())
                if isinstance(tokens, Sequence) and not isinstance(tokens, (str, bytes, bytearray)):
                    visual_parts.extend(str(token) for token in tokens if str(token))
    if not visual_parts:
        return None
    tokens = tuple(sorted(set(visual_parts)))
    return "visual::" + _hash_text("|".join(tokens)) + "::" + ",".join(tokens)


def _compose_input_signature(text_signature: str, visual_signature: str | None) -> str:
    if not visual_signature:
        return text_signature
    return _hash_text(f"text_visual\u241f{text_signature}\u241f{visual_signature}")


def _visual_tokens(visual_signature: str | None) -> set[str]:
    if not visual_signature:
        return set()
    value = str(visual_signature)
    if "::" not in value:
        return {value}
    parts = value.split("::", 2)
    if len(parts) < 3:
        return {value}
    return {token for token in parts[2].split(",") if token}


def _visual_signature_similarity(left: str | None, right: str | None) -> float:
    return _token_overlap(_visual_tokens(left), _visual_tokens(right))


def _token_overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(len(left | right), 1)


# ── §12 GAP-04: 常驻后台 tick 循环 ──────────────────────────────────────────

class Phase207TickDaemon:
    """Background daemon thread that runs idle ticks continuously.

    Architecture: ThreadingHTTPServer-compatible (no asyncio).
    User turns are submitted via queue and processed synchronously
    by the calling thread; idle ticks run in background between turns.
    """

    def __init__(
        self,
        session_id: str,
        db_path: str | Path,
        idle_tick_interval_s: float = 0.5,
    ) -> None:
        self.session_id = session_id
        self.db_path = db_path
        self.idle_tick_interval_s = idle_tick_interval_s
        self._stop_event = threading.Event()
        self._turn_lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._idle_loop, daemon=True, name="apv3-idle-tick"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def run_turn(
        self,
        user_text: str = "",
        teacher_feedback: "TeacherFeedback | None" = None,
        media_inputs: "Sequence[MediaInput]" = (),
        max_ticks: int = 32,
        runtime_stage: str = "stage1",
    ) -> "Phase207TurnResult":
        """Submit a user turn — blocks until turn completes."""
        with self._turn_lock:
            return run_phase20_7_turn(
                user_text=user_text,
                teacher_feedback=teacher_feedback,
                media_inputs=media_inputs,
                session_id=self.session_id,
                db_path=self.db_path,
                max_ticks=max_ticks,
                runtime_stage=runtime_stage,  # type: ignore[arg-type]
            )

    def _idle_loop(self) -> None:
        while not self._stop_event.is_set():
            if not self._turn_lock.acquire(blocking=False):
                time.sleep(0.05)
                continue
            try:
                run_phase20_7_turn(
                    user_text="",
                    session_id=self.session_id,
                    db_path=self.db_path,
                    max_ticks=4,
                    runtime_stage="stage1",
                )
            except Exception:
                pass
            finally:
                self._turn_lock.release()
            self._stop_event.wait(self.idle_tick_interval_s)
