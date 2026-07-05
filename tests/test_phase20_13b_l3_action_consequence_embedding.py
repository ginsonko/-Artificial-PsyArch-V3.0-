"""Phase20.13b — L3 action-consequence online embedding wired into action competition.

These tests prove the L3 layer is real, learnable, rebuildable, audited, and
non-regressive, without over-claiming convergence or completion. L3 is the learned
soft-consequence layer over (state, action) edges (whitepaper §1657 "学场景-行动-
奖惩后果"; §173.2 "L3 行动后果与奖惩, 帮 action competition"; §173.3 line 7178-7181
"z_action_context += lr_L3 * outcome_value * direction"). It does not replace the
explicit action competition channel (§35.4 red line 1); it only adds a learned
consequence vector on the (state, action) key, used later as a bounded drive
modulation (§1726 "行动失败会降低相同状态下该行动 drive"). No new cognitive entity
is asserted to exist — vectors live on the existing vector_l3 column.

L3 triggers on the *second* teach of the same scene (the first teach has no prior
outward action for L3 to attribute the feedback to — §173.6). Tests therefore seed
at least twice with the same session_id so action-record recovery can find the
outward action being judged.
"""

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any

from apv3test.runtime.phase20_7 import (
    L3_VECTOR_DIM,
    L3_VECTOR_INDEX_NAME,
    TeacherFeedback,
    bytes_to_l3_vector,
    l3_action_context_code,
    l3_cosine,
    l3_edge_sa_type_id,
    load_sa_type_vector_l3,
    rebuild_phase20_7_indexes,
    run_phase20_7_turn,
)

_SEED_SESSION = "phase20-13b-seed"
_TAUGHT_INPUT = "你好啊"
_TAUGHT_REPLY = "你也好"
_OUTWARD_ACTIONS = (
    "write_cell",
    "request_teacher",
    "maintain_unclosed",
    "integrate_feedback",
    "commit_reply",
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _seed_teach(
    db_path: Path,
    *,
    times: int = 2,
    session_id: str = _SEED_SESSION,
    reward: float = 1.0,
    punish: float = 0.0,
    feedback_text: str = _TAUGHT_REPLY,
) -> str:
    """Teach the same alignment ``times`` times so prior outward action records
    exist for L3 to attribute subsequent feedback to. Returns the observation
    signature for the taught input text."""
    for _ in range(int(times)):
        run_phase20_7_turn(
            user_text=_TAUGHT_INPUT,
            teacher_feedback=TeacherFeedback(
                feedback_text=feedback_text, reward_mag=reward, punish_mag=punish
            ),
            session_id=session_id,
            db_path=db_path,
            post_commit_idle_ticks=0,
            runtime_stage="stage1",
        )
    # observation.signature == structure_signature in the text_receptor_observation
    # payload (== input_signature in experience_alignment, which L3 keys on).
    # The text_receptor event carries the literal text for LIKE filtering.
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT payload_json FROM phase20_7_experience_events
            WHERE event_kind='text_receptor_observation' AND payload_json LIKE ?
            ORDER BY created_at_ms ASC LIMIT 1
            """,
            (f"%{_TAUGHT_INPUT}%",),
        ).fetchone()
    if row is None:
        return ""
    payload = json.loads(str(row[0]))
    return str(payload.get("structure_signature", "") or "")


def _l3_deltas(result: Any) -> list[dict[str, Any]]:
    deltas: list[dict[str, Any]] = []
    for event in result.tick_trace:
        for delta in event.learning_deltas:
            if isinstance(delta, dict) and delta.get("delta_kind") == "l3_action_consequence_update":
                deltas.append(dict(delta))
    return deltas


def _l3_modulation_rows(result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in result.tick_trace:
        for row in event.action_competition:
            if isinstance(row, dict) and "l3_action_consequence_modulation" in row:
                rows.append(dict(row))
    return rows


def _find_learned_action(
    db_path: Path, state_sig: str
) -> tuple[str, list[float]] | None:
    """Find the (state, action) edge with support_count>0 by matching sa_type_id
    against the deterministic L3 edge key. Returns (action_type, vector) or None."""
    if not state_sig:
        return None
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT sa_type_id, vector_l3 FROM phase20_7_sa_types WHERE substrate='action_edge'"
        ).fetchall()
    for action in _OUTWARD_ACTIONS:
        expected_id = l3_edge_sa_type_id(state_sig, action)
        for sid, raw in rows:
            if str(sid) == expected_id:
                sc, vec = bytes_to_l3_vector(raw)
                if sc > 0 and any(abs(v) > 1e-9 for v in vec):
                    return action, vec
    return None


def _euclidean(left: list[float], right: list[float]) -> float:
    return math.sqrt(
        sum((float(a) - float(b)) ** 2 for a, b in zip(left, right))
    )


# ---------------------------------------------------------------------------
# 1. Learning actually happens: a second teach of the same scene fills vector_l3
#    on the (state, action) edge and emits an l3_action_consequence_update delta.
#    The first teach cannot trigger L3 yet (no prior outward action to judge);
#    the second teach can, proving L3 learns from repeated experience (§173.6).
# ---------------------------------------------------------------------------
def test_phase20_13b_second_teach_fills_vector_l3_and_emits_delta(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_13b.sqlite"
    state_sig = _seed_teach(db_path, times=2)
    assert state_sig, "could not recover observation signature for taught input"

    # After 2 teaches, one L3 edge should exist with support_count>=1.
    learned = _find_learned_action(db_path, state_sig)
    assert learned is not None, "no L3 edge with support_count>0 after 2 reward teaches"
    _action, vec = learned
    assert any(abs(v) > 1e-9 for v in vec), "learned L3 vector is still zero"

    # A third teach of the same scene emits the delta in the returned tick_trace.
    result = run_phase20_7_turn(
        user_text=_TAUGHT_INPUT,
        teacher_feedback=TeacherFeedback(feedback_text=_TAUGHT_REPLY, reward_mag=1.0),
        session_id=_SEED_SESSION,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    deltas = _l3_deltas(result)
    assert deltas, "third teach of same scene did not emit l3_action_consequence_update delta"
    d = deltas[0]
    assert d["projection_only"] is True
    assert d["writes_answer_directly"] is False
    assert d["creates_reply_candidate"] is False
    assert d["outcome_value"] > 0.0, "reward should yield positive outcome_value"
    assert d["support_count"] >= 2, "support_count should have grown across repeated teaches"


# ---------------------------------------------------------------------------
# 2. Outcome direction: reward pulls the edge vector toward the success anchor
#    (distance shrinks); punish pushes it away (distance grows). §173.4 negative
#    update. This uses Euclidean distance rather than cosine because the update
#    formula scales the distance to the anchor by |1 - lr*outcome| exactly,
#    making the assertion sign-independent of the initial vector's alignment.
# ---------------------------------------------------------------------------
def test_phase20_13b_reward_pulls_punish_pushes_outcome_direction(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_13b_dir.sqlite"
    state_sig = _seed_teach(db_path, times=3)
    assert state_sig
    learned = _find_learned_action(db_path, state_sig)
    assert learned is not None, "no L3 edge with support_count>0 after reward teaches"
    action, vec_after_reward = learned
    anchor = l3_action_context_code(state_sig, action)
    dist_after_reward = _euclidean(vec_after_reward, anchor)
    assert dist_after_reward > 0.0, "vector already identical to anchor before punish"

    # Snapshot all outward-action edge vectors before punish so we can compare
    # the specific edge that the punish turn actually updates (which may differ
    # from `action` under warm-Python timing: write_cell ticks can appear after
    # commit_reply when the wall-clock budget still has room post-commit).
    with sqlite3.connect(db_path) as conn:
        pre_edge_ids = {a: l3_edge_sa_type_id(state_sig, a) for a in _OUTWARD_ACTIONS}
        pre_punish_edges = load_sa_type_vector_l3(conn, list(pre_edge_ids.values()))

    # Punish: push the edge vector away from the success anchor.
    punish_result = run_phase20_7_turn(
        user_text=_TAUGHT_INPUT,
        teacher_feedback=TeacherFeedback(feedback_text="不对", reward_mag=0.0, punish_mag=1.0),
        session_id=_SEED_SESSION,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    # Use the emitted L3 delta to find which (state, action) edge was updated —
    # timing-independent: we verify the edge that was actually judged, not one
    # we assumed based on seed-turn attribution.
    punish_deltas = _l3_deltas(punish_result)
    assert punish_deltas, "punish turn did not emit l3_action_consequence_update delta"
    punish_delta = punish_deltas[0]
    assert punish_delta["outcome_value"] < 0.0, "punish should yield negative outcome_value"

    punish_action = str(punish_delta["action_type"])
    punish_edge_id = str(punish_delta["edge_sa_type_id"])
    punish_anchor = l3_action_context_code(state_sig, punish_action)

    _, vec_before_punish = pre_punish_edges[punish_edge_id]
    dist_before_punish = _euclidean(vec_before_punish, punish_anchor)

    with sqlite3.connect(db_path) as conn:
        loaded = load_sa_type_vector_l3(conn, (punish_edge_id,))
    _sc, vec_after_punish = loaded[punish_edge_id]
    dist_after_punish = _euclidean(vec_after_punish, punish_anchor)

    assert dist_after_punish > dist_before_punish, (
        f"punish should push {punish_action!r} edge vector away from anchor: "
        f"before={dist_before_punish:.6f} after={dist_after_punish:.6f}"
    )


# ---------------------------------------------------------------------------
# 3. Rebuildability: wiping vector_l3 and running rebuild_phase20_7_indexes
#    restores the L3 edge vectors from the action_records + experience_events
#    truth source. §24/§132 truth source is the experience stream, not the index.
# ---------------------------------------------------------------------------
def test_phase20_13b_l3_vector_index_is_rebuildable(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_13b_rebuild.sqlite"
    state_sig = _seed_teach(db_path, times=2)
    assert state_sig

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE phase20_7_sa_types SET vector_l3=NULL WHERE substrate='action_edge'")
        conn.commit()
        wiped = conn.execute(
            "SELECT COUNT(*) FROM phase20_7_sa_types WHERE substrate='action_edge' AND vector_l3 IS NULL"
        ).fetchone()[0]
    assert wiped >= 1, "vector_l3 not actually wiped"

    status = rebuild_phase20_7_indexes(db_path)
    assert "l3_vector_index" in status, "rebuild did not return l3_vector_index sub-dict"
    l3_status = status["l3_vector_index"]
    assert l3_status["index_name"] == L3_VECTOR_INDEX_NAME
    assert l3_status["indexed_rows"] >= 1, "rebuild did not restore any L3 edge vectors"
    assert l3_status["vector_dim"] == L3_VECTOR_DIM

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT rebuildable, config_json FROM phase20_7_index_registry WHERE index_name=?",
            (L3_VECTOR_INDEX_NAME,),
        ).fetchone()
    assert row is not None, "l3_vector_index not registered in index_registry"
    assert int(row[0]) == 1, "l3_vector_index not marked rebuildable"
    assert "phase20_7_action_records" in str(row[1]), (
        "l3_vector_index config_json should declare action_records as truth source"
    )


# ---------------------------------------------------------------------------
# 4. No regression on far-text: an unrelated query still requests the teacher
#    instead of leaking the taught memory. The L3 modulation must not change the
#    request_teacher selection for an untaught state (support_count=0 -> neutral).
# ---------------------------------------------------------------------------
def test_phase20_13b_far_text_still_requests_teacher_no_l3_leak(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_13b_far.sqlite"
    _seed_teach(db_path, times=2)

    result = run_phase20_7_turn(
        user_text="你是谁",
        session_id="phase20-13b-far",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )
    assert result.reply_text == "不太会,教教"
    assert any(
        event.selected_action.get("action_type") == "request_teacher"
        for event in result.tick_trace
    )
    # Far-text state has no learned L3 edge -> any modulation rows must be neutral
    # (support_count=0, multiplier=1.0) or absent entirely.
    for row in _l3_modulation_rows(result):
        mod = row["l3_action_consequence_modulation"]
        assert mod["support_count"] == 0 or mod["drive_multiplier"] == 1.0, (
            f"far-text state should not be modulated by learned L3: {mod}"
        )


# ---------------------------------------------------------------------------
# 5. Action competition modulation is bounded and does not change `selected`:
#    the L3 modulation adjusts drive values within [0.7, 1.3] multiplier but the
#    `selected` flag on each row is preserved (§1742: no candidate may dominate
#    all context or be fully suppressed; L3 only modulates tendency). The turn
#    still produces a coherent reply — modulation does not break the main loop.
# ---------------------------------------------------------------------------
def test_phase20_13b_modulation_preserves_selected_and_is_bounded(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_13b_mod.sqlite"
    _seed_teach(db_path, times=3)

    # Query the taught scene (no feedback) — B recall finds the alignment, the
    # turn goes through write_cell selection where l3_context is wired.
    result = run_phase20_7_turn(
        user_text=_TAUGHT_INPUT,
        session_id=_SEED_SESSION,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )
    assert result.reply_text, "turn produced no reply — modulation may have broken the loop"
    mod_rows = _l3_modulation_rows(result)
    for row in mod_rows:
        mod = row["l3_action_consequence_modulation"]
        mult = float(mod["drive_multiplier"])
        assert 0.7 <= mult <= 1.3, f"modulation multiplier out of bounds [0.7,1.3]: {mult}"
    # Exactly one candidate should remain selected per competition tick — L3
    # must not erase or duplicate the selected flag.
    for event in result.tick_trace:
        if not event.action_competition:
            continue
        selected_count = sum(
            1 for row in event.action_competition
            if isinstance(row, dict) and row.get("selected") is True
        )
        assert selected_count == 1, (
            f"competition tick {event.tick} has {selected_count} selected rows, expected 1"
        )


# ---------------------------------------------------------------------------
# 6. No over-claiming: the serialized turn must not emit forbidden convergence
#    / completion strings. L3 is real but partial; convergence is not claimed.
# ---------------------------------------------------------------------------
def test_phase20_13b_runtime_does_not_claim_l3_convergence_or_completion(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_13b_boundary.sqlite"
    _seed_teach(db_path, times=2)

    result = run_phase20_7_turn(
        user_text="你好呀",
        session_id="phase20-13b-boundary",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )
    serialized = repr(result.to_dict()).lower()
    forbidden = (
        "l3_vector_converged",
        "l3_action_consequence_converged",
        "l1_l2_l3_complete",
        "online_embedding_converged",
        "six_stage_learning_complete",
    )
    for token in forbidden:
        assert token not in serialized, f"forbidden over-claim token {token!r} found in turn output"
