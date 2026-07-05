"""Phase20.12 — L2 temporal/edge online embedding wired into the C_forward path.

These tests prove the L2 layer is real, learnable, order-asymmetric,
rebuildable, audited, and non-regressive, without over-claiming L3 or
convergence. L2 is the learned soft-similarity layer over type-pair edges
(whitepaper §173.2 "L2 顺序/空间/因果, 帮 C_forward/C_backward"; §173.3
"z_next(a->b) != z_next(b->a)"). It does not replace SSP's explicit per-tick
edges (§35.4 red line 1); it only adds a learned vector on the type-pair key.
No new cognitive entity is asserted to exist.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from apv3test.runtime.phase20_7 import (
    L2_RELATION_LINEAR_NEXT,
    L2_VECTOR_DIM,
    L2_VECTOR_INDEX_NAME,
    TeacherFeedback,
    bytes_to_l2_vector,
    l2_compose,
    l2_cosine,
    l2_edge_sa_type_id,
    load_sa_type_vector_l1,
    load_sa_type_vector_l2,
    rebuild_phase20_7_indexes,
    run_phase20_7_turn,
)


def _seed_teach(db_path: Path, *, session_id: str = "phase20-12-seed") -> None:
    """Teach one alignment so an experience_alignment event + L2 edge update exist."""
    run_phase20_7_turn(
        user_text="你好啊",
        teacher_feedback=TeacherFeedback(feedback_text="你也好", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )


def _l2_deltas(result: Any) -> list[dict[str, Any]]:
    deltas: list[dict[str, Any]] = []
    for event in result.tick_trace:
        for delta in event.learning_deltas:
            if isinstance(delta, dict) and delta.get("delta_kind") == "l2_temporal_edge_update":
                deltas.append(dict(delta))
    return deltas


def _l2_prediction_rows(result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in result.tick_trace:
        for row in event.c_forward:
            if isinstance(row, dict) and row.get("kind") == "l2_temporal_edge_prediction":
                rows.append(dict(row))
    return rows


def _vector_rows(db_path: Path) -> dict[str, tuple[int, list[float]]]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT sa_type_id, vector_l2 FROM phase20_7_sa_types WHERE substrate='text_edge'"
        ).fetchall()
    return {str(sid): bytes_to_l2_vector(raw) for sid, raw in rows}


def _nonzero_vector_count(vectors: dict[str, tuple[int, list[float]]]) -> int:
    return sum(1 for _sid, (_count, vec) in vectors.items() if any(abs(v) > 1e-9 for v in vec))


# ---------------------------------------------------------------------------
# 1. Learning actually happens: a teach turn fills vector_l2 on the taught
#    output's linear_next type-pair edge sa_types, and emits an audited
#    l2_temporal_edge_update delta.
# ---------------------------------------------------------------------------
def test_phase20_12_teach_fills_vector_l2_and_emits_edge_delta(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_12.sqlite"
    _seed_teach(db_path)

    vectors = _vector_rows(db_path)
    assert _nonzero_vector_count(vectors) >= 1, "no learned L2 edge vectors after teaching"

    # The taught output 你也好 has two adjacent pairs: 你->也, 也->好.
    # Each must have a stored edge vector + support_count >= 1.
    conn = _connect(db_path)
    taught = "你也好"
    expected_edges = [
        l2_edge_sa_type_id(
            L2_RELATION_LINEAR_NEXT,
            f"text_unit::{_hash16(taught[i])}",
            f"text_unit::{_hash16(taught[i + 1])}",
        )
        for i in range(len(taught) - 1)
    ]
    loaded = load_sa_type_vector_l2(conn, expected_edges)
    for edge_id in expected_edges:
        assert edge_id in loaded, f"taught edge {edge_id} missing vector_l2 row"
        count, vec = loaded[edge_id]
        assert any(abs(v) > 1e-9 for v in vec), f"taught edge {edge_id} vector still zero"
        assert count >= 1, f"taught edge {edge_id} support_count not incremented"

    # Re-teach to capture the integrate_feedback delta in the returned tick_trace.
    result = run_phase20_7_turn(
        user_text="你好啊",
        teacher_feedback=TeacherFeedback(feedback_text="你也好", reward_mag=1.0),
        session_id="phase20-12-teach-again",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    deltas = _l2_deltas(result)
    assert deltas, "integrate_feedback tick did not emit l2_temporal_edge_update delta"
    delta = deltas[0]
    assert delta["formula_id"] == "apv3_phase20_12_l2_temporal_edge_embedding_structure_update/v1"
    assert delta["projection_only"] is True
    assert delta["writes_answer_directly"] is False
    assert delta["creates_reply_candidate"] is False
    assert delta["edge_kind"] == "linear_next"
    assert delta["updated_edge_count"] >= 1
    assert all("edge_sa_type_id" in edge for edge in delta["updated_edges"])


# ---------------------------------------------------------------------------
# 2. Order asymmetry (whitepaper §173.3 "z_next(a->b) != z_next(b->a)" and
#    §173.8 "狗咬我/我咬狗顺序不同"): a forward edge (你->好) and its reverse
#    (好->你) must yield different L2 vectors. This is the core §173.3 property.
# ---------------------------------------------------------------------------
def test_phase20_12_order_asymmetric_forward_and_reverse_edges_differ(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_12.sqlite"
    _seed_teach(db_path)

    conn = _connect(db_path)
    a_sa = f"text_unit::{_hash16('你')}"
    b_sa = f"text_unit::{_hash16('好')}"
    fwd_id = l2_edge_sa_type_id(L2_RELATION_LINEAR_NEXT, a_sa, b_sa)
    rev_id = l2_edge_sa_type_id(L2_RELATION_LINEAR_NEXT, b_sa, a_sa)
    loaded = load_sa_type_vector_l2(conn, (fwd_id, rev_id))
    fwd_vec = loaded[fwd_id][1]
    rev_vec = loaded[rev_id][1]

    # The two edge vectors must not be identical (order asymmetry).
    diff = sum(abs(f - r) for f, r in zip(fwd_vec, rev_vec))
    assert diff > 1e-6, f"forward and reverse L2 edge vectors identical (diff={diff})"

    # And their self-similarity should be high but their cross-similarity lower:
    # compose() keeps a/b in different halves, so fwd vs rev cosine < fwd vs fwd.
    self_sim = l2_cosine(fwd_vec, fwd_vec)
    cross_sim = l2_cosine(fwd_vec, rev_vec)
    assert self_sim > cross_sim, (
        f"order asymmetry violated at cosine level: self={self_sim} cross={cross_sim}"
    )

    # The compose() primitive itself must be order-asymmetric even before learning.
    loaded_l1 = load_sa_type_vector_l1(conn, (a_sa, b_sa))
    ctx_fwd = l2_compose(loaded_l1[a_sa][1], L2_RELATION_LINEAR_NEXT, loaded_l1[b_sa][1])
    ctx_rev = l2_compose(loaded_l1[b_sa][1], L2_RELATION_LINEAR_NEXT, loaded_l1[a_sa][1])
    ctx_diff = sum(abs(f - r) for f, r in zip(ctx_fwd, ctx_rev))
    assert ctx_diff > 1e-6, "compose() not order-asymmetric at the primitive level"


# ---------------------------------------------------------------------------
# 3. The learned signal reaches C_forward: after teaching, a near-text query
#    whose last char matches a taught edge source produces an
#    l2_temporal_edge_prediction row in c_forward, marked projection_only.
# ---------------------------------------------------------------------------
def test_phase20_12_c_forward_includes_l2_prediction_row(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_12.sqlite"
    _seed_teach(db_path)

    # Query ending in 好 (a taught edge source for 好 in 你也好 has edges 好->...?;
    # the taught edges are 你->也, 也->好. Query ending in 也 should match 你->也.)
    result = run_phase20_7_turn(
        user_text="你也",
        session_id="phase20-12-predict",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )
    rows = _l2_prediction_rows(result)
    assert rows, "no l2_temporal_edge_prediction row in c_forward after teaching"
    row = rows[0]
    assert row["kind"] == "l2_temporal_edge_prediction"
    assert row["projection_only"] is True
    assert row["writes_answer_directly"] is False
    assert row["edge_kind"] == L2_RELATION_LINEAR_NEXT
    assert row["l2_edge_support"] > 0.0
    assert row["predicted_dst_sa_type_id"].startswith("text_unit::")


# ---------------------------------------------------------------------------
# 4. Rebuildability: wiping vector_l2 and running rebuild_phase20_7_indexes
#    restores the edge vectors from the experience_alignment truth source, and
#    registers the l2_vector_index/v1 derived-index row.
# ---------------------------------------------------------------------------
def test_phase20_12_l2_vector_index_is_rebuildable_from_experience_log(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_12.sqlite"
    _seed_teach(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE phase20_7_sa_types SET vector_l2=NULL WHERE substrate='text_edge'")
        conn.commit()
    wiped = _nonzero_vector_count(_vector_rows(db_path))
    assert wiped == 0, "vector_l2 not actually wiped"

    status = rebuild_phase20_7_indexes(db_path)
    assert "l2_vector_index" in status, "rebuild did not return l2_vector_index sub-dict"
    assert status["l2_vector_index"]["index_name"] == L2_VECTOR_INDEX_NAME
    assert status["l2_vector_index"]["indexed_rows"] >= 1
    assert status["l2_vector_index"]["vector_dim"] == L2_VECTOR_DIM

    restored = _nonzero_vector_count(_vector_rows(db_path))
    assert restored >= 1, "rebuild did not restore any L2 edge vectors"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT rebuildable, config_json FROM phase20_7_index_registry WHERE index_name=?",
            (L2_VECTOR_INDEX_NAME,),
        ).fetchone()
    assert row is not None, "l2_vector_index/v1 row not registered"
    assert int(row[0]) == 1
    assert "phase20_7_experience_events" in str(row[1])


# ---------------------------------------------------------------------------
# 5. No regression on far-text: an unrelated query still requests the teacher
#    instead of leaking the taught memory, and no b_candidates fire. The L2
#    prediction row, if any, must not change the request_teacher selection.
# ---------------------------------------------------------------------------
def test_phase20_12_far_text_still_requests_teacher_no_l2_leak(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_12.sqlite"
    _seed_teach(db_path)

    result = run_phase20_7_turn(
        user_text="你是谁",
        session_id="phase20-12-far",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    assert result.reply_text == "不太会,教教"
    assert not any(event.b_candidates for event in result.tick_trace)
    assert any(event.selected_action.get("action_type") == "request_teacher" for event in result.tick_trace)
    # A far-text query whose last char 谁 was never taught must not produce an
    # L2 prediction row (no edge starts from 谁).
    rows = _l2_prediction_rows(result)
    assert not rows, "far-text produced an L2 prediction leak"


# ---------------------------------------------------------------------------
# 6. No over-claiming: the serialized turn must not emit forbidden convergence
#    / completion strings. L2 is real but partial; L3/convergence are not.
# ---------------------------------------------------------------------------
def test_phase20_12_runtime_does_not_claim_l2_convergence_or_l3(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_12.sqlite"
    _seed_teach(db_path)

    result = run_phase20_7_turn(
        user_text="你好呀",
        session_id="phase20-12-boundary",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    serialized = repr(result.to_dict()).lower()
    assert "l2_vector_converged" not in serialized
    assert "l1_l2_l3_complete" not in serialized
    assert "online_embedding_converged" not in serialized
    assert "six_stage_learning_complete" not in serialized


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _connect(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def _hash16(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
