"""Phase20.11 — L1 online text embedding wired into the existing B-recall path.

These tests prove the L1 layer is real, learnable, rebuildable, audited, and
non-regressive, without over-claiming L2/L3 or convergence. They read only the
existing RuntimeTickEvent / experience-flow surfaces; no new cognitive entity
is asserted to exist.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from apv3test.runtime.phase20_7 import (
    L1_VECTOR_DIM,
    L1_VECTOR_INDEX_NAME,
    TeacherFeedback,
    bytes_to_l1_vector,
    load_sa_type_vector_l1,
    rebuild_phase20_7_indexes,
    run_phase20_7_turn,
)


def _seed_teach(db_path: Path, *, session_id: str = "phase20-11-seed") -> None:
    """Teach one alignment so an experience_alignment event + L1 update exist."""
    run_phase20_7_turn(
        user_text="你好啊",
        teacher_feedback=TeacherFeedback(feedback_text="你也好", reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )


def _l1_deltas(result: Any) -> list[dict[str, Any]]:
    deltas: list[dict[str, Any]] = []
    for event in result.tick_trace:
        for delta in event.learning_deltas:
            if isinstance(delta, dict) and delta.get("delta_kind") == "l1_vector_triplet_update":
                deltas.append(dict(delta))
    return deltas


def _vector_rows(db_path: Path) -> dict[str, tuple[int, list[float]]]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT sa_type_id, vector_l1 FROM phase20_7_sa_types WHERE substrate='text'"
        ).fetchall()
    return {str(sid): bytes_to_l1_vector(raw) for sid, raw in rows}


def _nonzero_vector_count(vectors: dict[str, tuple[int, list[float]]]) -> int:
    return sum(1 for _sid, (_count, vec) in vectors.items() if any(abs(v) > 1e-9 for v in vec))


# ---------------------------------------------------------------------------
# 1. Learning actually happens: a teach turn fills vector_l1 on the taught
#    output char sa_types, and emits an audited l1_vector_triplet_update delta.
# ---------------------------------------------------------------------------
def test_phase20_11_teach_fills_vector_l1_and_emits_triplet_delta(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_11.sqlite"
    _seed_teach(db_path)

    vectors = _vector_rows(db_path)
    assert _nonzero_vector_count(vectors) >= 1, "no learned L1 vectors after teaching"

    # The taught output chars 你/也/好 must each have a stored vector + support_count.
    taught_ids = [f"text_unit::{_hash16(ch)}" for ch in "你也好"]
    loaded = load_sa_type_vector_l1(_connect(db_path), taught_ids)
    for sid in taught_ids:
        assert sid in loaded, f"taught sa_type {sid} missing vector_l1 row"
        _count, vec = loaded[sid]
        assert any(abs(v) > 1e-9 for v in vec), f"taught sa_type {sid} vector still zero"
        assert _count >= 1, f"taught sa_type {sid} support_count not incremented"

    # Re-run a query turn to capture the integrate_feedback delta from the seed
    # turn is not directly observable post-hoc, so re-teach and inspect the
    # returned tick_trace for the projection delta.
    result = run_phase20_7_turn(
        user_text="你好啊",
        teacher_feedback=TeacherFeedback(feedback_text="你也好", reward_mag=1.0),
        session_id="phase20-11-teach-again",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage1",
    )
    deltas = _l1_deltas(result)
    assert deltas, "integrate_feedback tick did not emit l1_vector_triplet_update delta"
    delta = deltas[0]
    assert delta["formula_id"] == "apv3_phase20_11_l1_online_embedding_triplet_update/v1"
    assert delta["projection_only"] is True
    assert delta["writes_answer_directly"] is False
    assert delta["creates_reply_candidate"] is False
    assert delta["anchor_kind"] == "taught_output_char"
    assert delta["positive_reference_kind"] == "co_occurring_input_context"
    assert delta["updated_vector_count"] >= 1
    assert delta["reward"] == 1.0


# ---------------------------------------------------------------------------
# 2. Vector evidence is directional: a taught pair's L1 cosine similarity is
#    higher than an unrelated pair's. This is the learned-signal evidence at the
#    vector layer (not a recall-generalization claim).
# ---------------------------------------------------------------------------
def test_phase20_11_taught_pair_l1_similarity_exceeds_unrelated_pair(tmp_path: Path) -> None:
    from apv3test.runtime.phase20_7.experience_log import l1_centroid, l1_cosine

    db_path = tmp_path / "phase20_11.sqlite"
    _seed_teach(db_path)

    conn = _connect(db_path)
    # taught input context 你/好/啊 -> taught output 你/也/好 were co-trained.
    taught_input_ids = [f"text_unit::{_hash16(ch)}" for ch in "你好啊"]
    taught_output_ids = [f"text_unit::{_hash16(ch)}" for ch in "你也好"]
    unrelated_ids = [f"text_unit::{_hash16(ch)}" for ch in "猫狗兔"]

    loaded = load_sa_type_vector_l1(conn, taught_input_ids + taught_output_ids + unrelated_ids)
    input_centroid = l1_centroid([loaded.get(sid, (0, [0.0] * L1_VECTOR_DIM))[1] for sid in taught_input_ids])
    output_centroid = l1_centroid([loaded.get(sid, (0, [0.0] * L1_VECTOR_DIM))[1] for sid in taught_output_ids])
    unrelated_centroid = l1_centroid([loaded.get(sid, (0, [0.0] * L1_VECTOR_DIM))[1] for sid in unrelated_ids])

    taught_sim = l1_cosine(input_centroid, output_centroid)
    unrelated_sim = l1_cosine(input_centroid, unrelated_centroid)
    assert taught_sim > unrelated_sim, (
        f"learned L1 similarity not directional: taught={taught_sim} unrelated={unrelated_sim}"
    )


# ---------------------------------------------------------------------------
# 3. The learned signal reaches the recall support formula: after teaching, a
#    near-text structural_b recall exposes l1_vector_similarity in its
#    support_terms and it is strictly positive.
# ---------------------------------------------------------------------------
def test_phase20_11_recall_support_terms_include_positive_l1_signal(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_11.sqlite"
    _seed_teach(db_path)

    result = run_phase20_7_turn(
        user_text="你好呀",
        session_id="phase20-11-recall",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    structural_events = [
        event.to_dict()
        for event in result.tick_trace
        if event.b_candidates and event.b_candidates[0]["kind"] == "structural_b"
    ]
    assert structural_events, "structural_b recall did not fire for near text"
    terms = structural_events[0]["b_candidates"][0]["support_terms"]
    l1_term = terms.get("l1_vector_similarity", 0.0)
    assert l1_term > 0.0, f"l1_vector_similarity support term not positive: {l1_term}"
    assert structural_events[0]["cstar_packet"]["writes_answer_directly"] is False


# ---------------------------------------------------------------------------
# 4. Rebuildability: wiping vector_l1 and running rebuild_phase20_7_indexes
#    restores the vectors from the experience_alignment truth source, and
#    registers the l1_vector_index/v1 derived-index row.
# ---------------------------------------------------------------------------
def test_phase20_11_l1_vector_index_is_rebuildable_from_experience_log(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_11.sqlite"
    _seed_teach(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE phase20_7_sa_types SET vector_l1=NULL WHERE substrate='text'")
        conn.commit()
    wiped = _nonzero_vector_count(_vector_rows(db_path))
    assert wiped == 0, "vector_l1 not actually wiped"

    status = rebuild_phase20_7_indexes(db_path)
    assert status["l1_vector_index"]["index_name"] == L1_VECTOR_INDEX_NAME
    assert status["l1_vector_index"]["indexed_rows"] >= 1
    assert status["l1_vector_index"]["vector_dim"] == L1_VECTOR_DIM

    restored = _nonzero_vector_count(_vector_rows(db_path))
    assert restored >= 1, "rebuild did not restore any L1 vectors"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT rebuildable, config_json FROM phase20_7_index_registry WHERE index_name=?",
            (L1_VECTOR_INDEX_NAME,),
        ).fetchone()
    assert row is not None, "l1_vector_index/v1 row not registered"
    assert int(row[0]) == 1
    assert "phase20_7_experience_events" in str(row[1])


# ---------------------------------------------------------------------------
# 5. No regression on teacher-off / cold-retest style far-text: an unrelated
#    query still requests the teacher instead of leaking the taught memory, and
#    no b_candidates fire. (The L1 term is gated by allow_context_bias, so a
#    zero-structural-overlap far query cannot summon the memory via L1 alone.)
# ---------------------------------------------------------------------------
def test_phase20_11_far_text_still_requests_teacher_no_l1_leak(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_11.sqlite"
    _seed_teach(db_path)

    result = run_phase20_7_turn(
        user_text="你是谁",
        session_id="phase20-11-far",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage3",
    )

    assert result.reply_text == "不太会,教教"
    assert not any(event.b_candidates for event in result.tick_trace)
    assert any(event.selected_action.get("action_type") == "request_teacher" for event in result.tick_trace)


# ---------------------------------------------------------------------------
# 6. No over-claiming: the serialized turn must not emit forbidden convergence
#    / completion strings. L1 is real but partial; L2/L3/convergence are not.
# ---------------------------------------------------------------------------
def test_phase20_11_runtime_does_not_claim_l1_convergence_or_l2_l3(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_11.sqlite"
    _seed_teach(db_path)

    result = run_phase20_7_turn(
        user_text="你好呀",
        session_id="phase20-11-boundary",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    serialized = repr(result.to_dict()).lower()
    assert "l1_vector_converged" not in serialized
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
