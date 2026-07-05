# Phase20.11 L1 Online Text Embedding

Date: 2026-06-29

Formula:

`apv3_phase20_11_l1_online_embedding_triplet_update/v1`

## 1. Design

The Phase20.8e read-only audit found the true runtime gap: whitepaper §35.3 / §173.3
mandate L1/L2/L3 online embedding, but `phase20_7_sa_types.vector_l1/l2/l3` were empty
since the table was created. Phase20.11 wires in **L1 only** (receptor-local text
similarity), filling the existing `vector_l1` column with no new cognitive entity:

- on teacher feedback, triplet-update the taught output chars' `text_unit` sa_types;
- use L1 vector cosine as an additive term in `compute_unified_experience_support`
  at both recall injection points;
- register `l1_vector_index/v1` as `rebuildable=1`, replayable from the experience log;
- emit the L1 delta into `learning_deltas` as `projection_only=True`,
  `writes_answer_directly=False`.

L2/L3 are out of scope. This step does not claim convergence or L1/L2/L3 completion.

## 2. No-New-Entity Review

Phase20.11 does not add:

- a new answer table, keyword/regex route, or hidden solver;
- an external LLM vector as student-side semantic authority (§19.3b) — the L1 vector
  is produced by the runtime's own triplet learning;
- a new cognitive entity — the deterministic initial vector is only the initialization
  policy for the existing `vector_l1` column;
- a new module — it reuses StatePool / SSP / B recall / C* / ExperienceFlow / DraftGrid
  / action competition as-is.

Triplet asymmetry (§33.1) is respected: the anomaly object (taught output char
sa_type) is updated; the co-occurring input char sa_types are reference-only and not
co-updated. The annealing schedule `lr_t = lr_0 / sqrt(1 + support_count)` (§173.5) is
applied with defaults `lr_max=0.08, lr_min=0.008, tau=120`.

## 3. Implementation

Files:

- `apv3test/runtime/phase20_7/experience_candidate.py`
  - added `l1_vector_similarity: float = 0.0` keyword param to
    `compute_unified_experience_support`;
  - added term `("l1_vector_similarity", l1_term)` where
    `l1_term = unit(l1_sim) * (0.28 if allow_context_bias else 0.0)`;
  - **not** added to the `primary` max, so `l1_vector_similarity=0.0` (default) is
    bit-identical to the 8e formula; formula id kept v1.

- `apv3test/runtime/phase20_7/experience_log.py`
  - constants `L1_VECTOR_DIM = 24`, `L1_VECTOR_INDEX_NAME = "l1_vector_index/v1"`;
  - `l1_zero_vector`, `l1_initial_vector_for(sa_type_id)` (deterministic
    content-addressed unit-norm vector, magnitude 0.15, from sha256);
  - `l1_vector_to_bytes` / `bytes_to_l1_vector` (support_count + 24-dim float32 BLOB);
  - `update_sa_type_vector_l1` / `load_sa_type_vector_l1` (loader falls back to the
    initial vector for NULL/zero/missing rows, so the first triplet step has
    direction);
  - `l1_centroid`, `l1_cosine`, `l1_triplet_update_vector`;
  - `rebuild_phase20_7_indexes`: after exact_b0 rebuild, wipes `vector_l1` for text
    substrate, replays L1 triplet learning from `experience_alignment` events in
    `created_at` order, upserts `l1_vector_index/v1` registry row, returns the
    `l1_vector_index` sub-dict. Rebuild uses direct indexing
    (`input_loaded[sid][1]`, `output_loaded[sid]`), matching the loader's
    always-returns-entry contract.

- `apv3test/runtime/phase20_7/experience_recall.py`
  - `L1VectorSimilarityFn = Callable[[str, str], float]` type alias;
  - `l1_vector_similarity: L1VectorSimilarityFn | None = None` param on
    `query_experience_alignment_candidates`;
  - `l1_vector_score: float = 0.0` field on `ExperienceRecallCandidate`;
  - in the candidate loop, computes `l1_score`, passes it to
    `compute_unified_experience_support`, sets `l1_vector_score` on the candidate.

- `apv3test/runtime/phase20_7/__init__.py`
  - exported the new L1 helpers.

- `apv3test/runtime/phase20_7/runtime.py`
  - `_text_unit_sa_type_ids(text)` helper;
  - `_l1_text_vector_similarity(conn, query_text, memory_text)`: centroids of the
    distinct text_unit sa_type L1 vectors, returns `l1_cosine`; direct indexing;
  - `PHASE20_11_L1_TRIPLET_UPDATE_ID`;
  - `_apply_l1_triplet_update(conn, pool, *, session_id, tick, observation,
    feedback_chars, reward, punish)`: anchor = taught output char sa_types,
    positive_centroid = co-occurring input char sa_types centroid, prediction_error
    from the live pool item's `cognitive_pressure` (fallback 0.5), calls
    `l1_triplet_update_vector` + `update_sa_type_vector_l1`, returns a delta dict with
    `delta_kind="l1_vector_triplet_update"`, `projection_only=True`,
    `writes_answer_directly=False`; direct indexing;
  - `_record_teacher_feedback` now calls `_apply_l1_triplet_update` and returns the
    delta as the last tuple element;
  - the call site strips the delta from `feedback_event_ids` and adds it to the
    `integrate_feedback` tick's `learning_deltas`;
  - wired `l1_vector_similarity` into both recall injection points
    (`_experience_candidates_for_observation` and `_find_structural_b`'s
    `compute_unified_experience_support` call).

Test:

- `tests/test_phase20_11_l1_online_embedding.py` (6 tests);
- `tests/test_phase20_8e_code_audit_and_unified_candidate.py` guardrail extended with
  `assert "l1_vector_converged" not in serialized`.

## 4. Acceptance

Run from the `APV3.0test` root (running in the upper repo root causes path-level
errors):

- `python -m py_compile` on all 5 implementation files — `BYTE_COMPILE_OK`;
- `node --check apv3test/web/static/phase20_7_workbench.js` — `NODE_CHECK_OK`;
- `python -m pytest -q tests/test_phase20_11_l1_online_embedding.py` — 6 passed;
- regression suite (11 files, 39 tests):
  `tests/test_phase20_7_stage1_text_closed_loop.py`,
  `tests/test_phase20_7_stage3_structural_bccstar.py`,
  `tests/test_phase20_7_stage2_experience_memory_indexes.py`,
  `tests/test_phase20_8e_code_audit_and_unified_candidate.py`,
  `tests/test_phase20_8h_unified_cstar_min_error_integration.py`,
  `tests/test_phase20_8i_cstar_statepool_virtual_feedback.py`,
  `tests/test_phase20_8j_cstar_carryover_next_tick_influence.py`,
  `tests/test_phase20_9i_workbench_learning_lifecycle.py`,
  `tests/test_phase20_10l_workbench_lifecycle_memory_rhythm_timeline_sync.py`,
  `tests/test_phase20_10m_workbench_lifecycle_drilldown.py`,
  `tests/test_phase20_11_l1_online_embedding.py`
  — 39 passed in 17.24s;
- `python scripts/red_line_check_v14.py` — zero hits; the scanner covers all 5
  modified files (recursive `apv3test/**/*.py` glob plus the explicit phase20_7 list
  including `experience_log.py` and `runtime.py`).

## 5. Plain Example

After one teaching turn ("你好啊" -> "你也好"):

- the taught output chars' `text_unit` sa_types now carry non-zero `vector_l1`;
- the `integrate_feedback` tick's `learning_deltas` contains an
  `l1_vector_triplet_update` delta marked `projection_only=True`;
- a later near-text query ("你好呀") gets a positive `l1_vector_similarity` term in
  the recall candidate's `support_terms`, raising structural-B support;
- a far-text query ("你是谁") still requests the teacher with no fake B and no L1
  leak across unrelated text.

## 6. Boundaries

This step can prove:

- L1 online triplet embedding fills the existing `vector_l1` column from the runtime's
  own learning, with no new cognitive entity;
- L1 cosine modulates (not generates) B recall support, bit-identical to 8e when
  unwired;
- the L1 index is rebuildable from the experience log;
- far text still requests the teacher; no completion claims are emitted.

This step cannot yet claim:

- complete L1/L2/L3 online embedding (L2 cross-modal co-occurrence and L3
  action-consequence embeddings are still unimplemented — `vector_l2`/`vector_l3`
  remain unused);
- L1 convergence (no convergence metric or claim is emitted);
- complete six-stage runtime;
- complete paradigm self-learning;
- mathematical column calculation;
- object-centric visual imagination completion;
- Phase21 visual teaching generalization closure.

## 7. Next Step

The natural next runtime-facing boundary is **L2 cross-modal co-occurrence online
embedding** (whitepaper §35.3 / §173.3): fill the existing `vector_l2` column the same
no-new-entity way — triplet/annealed updates driven by cross-modal co-occurrence in
the experience flow, injected as another additive term in
`compute_unified_experience_support`, with a rebuildable `l2_vector_index/v1` and the
same far-text no-leak / no-completion-claim guardrails. L3 action-consequence would
follow the same pattern. Each step stays on the runtime learning boundary rather than
adding display depth.
