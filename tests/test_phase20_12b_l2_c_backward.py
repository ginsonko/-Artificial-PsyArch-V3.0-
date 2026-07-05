"""Phase20.12b — L2 temporal-edge predecessor attribution wired into C_backward.

The backward mirror of Phase20.12's C_forward successor prediction. L2 helps
C_backward per whitepaper §173.2; §1160 says C_backward answers "历史上这种现
状之前通常有什么条件" (what usually came before this). For a learned order edge
(a->b), the backward use is: given the current last char `b`, find edges whose
dst is `b` and surface the src `a` as the historical cause. This is the same
learned edge vectors, opposite query direction — the §173.3 order asymmetry.

No new cognitive entity: it reuses the existing vector_l2 / text_edge sa_types /
single-point C_backward convergence. C_forward (successor) and C_backward
(predecessor) are symmetric cuts over the same learned edges.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from apv3test.runtime.phase20_7 import (
    L2_RELATION_LINEAR_NEXT,
    TeacherFeedback,
    run_phase20_7_turn,
)


def _seed_teach(db_path: Path, *, session_id: str = "phase20-12b-seed") -> None:
    run_phase20_7_turn(
        user_text="你好啊",
        teacher_feedback=TeacherFeedback(feedback_text="你也好", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )


def _l2_predecessor_rows(result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in result.tick_trace:
        for row in event.c_backward:
            if isinstance(row, dict) and row.get("kind") == "l2_temporal_edge_predecessor":
                rows.append(dict(row))
    return rows


def _l2_successor_rows(result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in result.tick_trace:
        for row in event.c_forward:
            if isinstance(row, dict) and row.get("kind") == "l2_temporal_edge_prediction":
                rows.append(dict(row))
    return rows


# ---------------------------------------------------------------------------
# 1. After teaching 你也好 (edges 你->也, 也->好), a query ending in 好 surfaces
#    the 也->好 edge and attributes 也 as the predecessor cause.
# ---------------------------------------------------------------------------
def test_phase20_12b_query_ending_in_taught_dst_attributes_predecessor(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_12b.sqlite"
    _seed_teach(db_path)

    # Query ending in 好 — 好 is the dst of the taught edge 也->好, so the
    # predecessor cause should be 也.
    result = run_phase20_7_turn(
        user_text="天好",
        session_id="phase20-12b-attr",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )
    rows = _l2_predecessor_rows(result)
    assert rows, "no l2_temporal_edge_predecessor row in c_backward after teaching"
    row = rows[0]
    assert row["kind"] == "l2_temporal_edge_predecessor"
    assert row["edge_kind"] == L2_RELATION_LINEAR_NEXT
    assert row["projection_only"] is True
    assert row["writes_answer_directly"] is False
    assert row["l2_edge_support"] > 0.0
    # current dst is 好, attributed cause is 也 (src of 也->好)
    assert _hash16("好") in row["current_dst_sa_type_id"]
    assert _hash16("也") in row["attributed_cause_sa_type_id"]
    assert row["cause_grasp"] > 0.0
    assert 0.0 <= row["e_backward"] <= 1.0


# ---------------------------------------------------------------------------
# 2. Directional consistency: a query ending in 也 attributes 你 (src of 你->也)
#    as predecessor. Different dst -> different predecessor, over the same
#    learned edge set.
# ---------------------------------------------------------------------------
def test_phase20_12b_different_dst_attributes_different_predecessor(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_12b.sqlite"
    _seed_teach(db_path)

    result = run_phase20_7_turn(
        user_text="天也",
        session_id="phase20-12b-attr-ye",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )
    rows = _l2_predecessor_rows(result)
    assert rows, "no predecessor row for query ending in 也"
    # 也 is dst of 你->也, so attributed cause is 你
    assert _hash16("也") in rows[0]["current_dst_sa_type_id"]
    assert _hash16("你") in rows[0]["attributed_cause_sa_type_id"]


# ---------------------------------------------------------------------------
# 3. Order-asymmetry self-consistency: for a query ending in 也, the C_forward
#    successor prediction uses 也 as SRC (predict what comes after 也, i.e. 好),
#    while the C_backward predecessor attribution uses 也 as DST (attribute what
#    came before 也, i.e. 你). Same edge set, opposite direction.
# ---------------------------------------------------------------------------
def test_phase20_12b_forward_and_backward_use_opposite_edge_directions(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_12b.sqlite"
    _seed_teach(db_path)

    result = run_phase20_7_turn(
        user_text="天也",
        session_id="phase20-12b-both",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )
    succ = _l2_successor_rows(result)
    pred = _l2_predecessor_rows(result)
    # C_forward: 也 as src -> predicted dst 好
    assert succ, "C_forward successor row missing"
    assert _hash16("好") in succ[0]["predicted_dst_sa_type_id"]
    # C_backward: 也 as dst -> attributed cause 你
    assert pred, "C_backward predecessor row missing"
    assert _hash16("你") in pred[0]["attributed_cause_sa_type_id"]
    # The two rows use different edges (也->好 forward, 你->也 backward).
    assert succ[0]["source_edge_sa_type_id"] != pred[0]["source_edge_sa_type_id"]


# ---------------------------------------------------------------------------
# 4. No far-text leak: a query whose last char 谁 was never taught produces no
#    predecessor row (no edge ends at 谁), and the turn still requests teacher.
# ---------------------------------------------------------------------------
def test_phase20_12b_far_text_no_predecessor_leak(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_12b.sqlite"
    _seed_teach(db_path)

    result = run_phase20_7_turn(
        user_text="你是谁",
        session_id="phase20-12b-far",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )
    assert result.reply_text == "不太会,教教"
    assert not any(event.b_candidates for event in result.tick_trace)
    assert any(event.selected_action.get("action_type") == "request_teacher" for event in result.tick_trace)
    rows = _l2_predecessor_rows(result)
    assert not rows, "far-text produced an L2 predecessor leak"


# ---------------------------------------------------------------------------
# 5. Rebuildability preserves the predecessor attribution: after a rebuild, a
#    query ending in 好 still attributes 也 as predecessor (the rebuilt edges
#    carry the same dst/src structure).
# ---------------------------------------------------------------------------
def test_phase20_12b_predecessor_survives_rebuild(tmp_path: Path) -> None:
    from apv3test.runtime.phase20_7 import rebuild_phase20_7_indexes, L2_VECTOR_INDEX_NAME

    db_path = tmp_path / "phase20_12b.sqlite"
    _seed_teach(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE phase20_7_sa_types SET vector_l2=NULL WHERE substrate='text_edge'")
        conn.commit()
    status = rebuild_phase20_7_indexes(db_path)
    assert status["l2_vector_index"]["index_name"] == L2_VECTOR_INDEX_NAME
    assert status["l2_vector_index"]["indexed_rows"] >= 1

    result = run_phase20_7_turn(
        user_text="天好",
        session_id="phase20-12b-after-rebuild",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )
    rows = _l2_predecessor_rows(result)
    assert rows, "predecessor attribution lost after rebuild"
    assert _hash16("也") in rows[0]["attributed_cause_sa_type_id"]


# ---------------------------------------------------------------------------
# 6. No over-claiming: the serialized turn must not emit forbidden convergence
#    / completion strings.
# ---------------------------------------------------------------------------
def test_phase20_12b_runtime_does_not_claim_l2_convergence_or_l3(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_12b.sqlite"
    _seed_teach(db_path)

    result = run_phase20_7_turn(
        user_text="天好",
        session_id="phase20-12b-boundary",
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
def _hash16(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
