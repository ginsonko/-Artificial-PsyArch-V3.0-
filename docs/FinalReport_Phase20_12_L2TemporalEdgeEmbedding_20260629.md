# Phase20.12 L2 Temporal/Edge Online Embedding

Date: 2026-06-29

Formula:

`apv3_phase20_12_l2_temporal_edge_embedding_structure_update/v1`

## 1. Design

Phase20.11 landed L1 (receptor-local text similarity, helps B recall). The
Phase20.11 final report mislabeled the next step as "L2 cross-modal co-occurrence".
The Phase20.12 read-only audit corrected this against the whitepaper (§35.2 /
§173.2 / §173.3): **L2 is the temporal/spatial/causal layer; it learns order,
motion, spatial trend, causal candidates; it helps C_forward/C_backward** (not B
recall — that is L1). L2's updated object is the **edge** `e=(a relation b)`,
with `z_edge <- z_edge + lr_L2 * structure_support * (compose(z_a, relation, z_b) - z_edge)`
and **order asymmetry** `z_next(a->b) != z_next(b->a)` (§173.8: "狗咬我/我咬狗
顺序不同").

A user challenge ("SSP already has order/spatial/3D structure edges; why need an
L2 order edge?") forced a whitepaper re-check that **clarified the layering**:
SSP (§10) is the explicit per-tick structure graph (occurrence-level edges with
exact relation_type); L2 (§35.3/§173) is the *learned soft-similarity* layer over
*type-pair* edges, so a new (a->b) whose tokens are similar-but-not-identical to a
historical edge can still recall that successor by cosine. §35.4 red line 1
("online embedding does not replace the explicit channel") is exactly this
SSP/L2 split. The runtime audit confirmed the gap: `_short_structure_next_candidates`
matches edges by exact `edge_type` + `sa_type_id LIKE` prefix with no edge-to-edge
soft similarity — so L2 fills a real gap.

Phase20.12 wires in **L2 order edges only** (`linear_next` on taught output
sequences), C_forward side only, filling the existing `vector_l2` column with no
new cognitive entity. L3, spatial, causal, and C_backward are out of scope.

## 2. No-New-Entity Review (user-signed)

Phase20.12 does not add:

- a new answer table, keyword/regex route, or hidden solver;
- a new cognitive entity — the type-pair edge sa_type
  `text_edge::linear_next::<hash(a)>-><hash(b)>` is only the *key* for the
  existing `vector_l2` column on the existing `sa_types` table, mirroring L1
  filling `vector_l1`. `upsert_sa_type` is a generic interface; no table/column
  added;
- a replication of SSP's occurrence-level explicit edges — L2 only adds a learned
  vector on the type-pair key; SSP occurrence edges stay (§35.4 red line 1);
- an external LLM vector — the L2 edge vector is produced by the runtime's own
  structure update from prediction-error proxy + reward/punish + endpoint L1
  vectors.

Order asymmetry (§173.3) is realized at two levels: the edge sa_type_id key
`(a->b) != (b->a)`, and the `compose()` primitive (first half src-dominated,
second half dst-dominated) so `compose(a,b) != compose(b,a)` at the vector level.
The annealing schedule `lr_t = lr_0/sqrt(1+support_count)` (§173.5) is applied.

User decisions signed: (a) carrier = type-pair key + existing vector_l2 column
(recommended); (b) C_forward-only this step, C_backward deferred.

## 3. Implementation

Files:

- `apv3test/runtime/phase20_7/experience_log.py`
  - constants `L2_VECTOR_DIM = 24`, `L2_VECTOR_INDEX_NAME = "l2_vector_index/v1"`,
    `L2_RELATION_LINEAR_NEXT`, `L2_RELATION_FEEDBACK_LINEAR_NEXT`;
  - `l2_zero_vector`, `l2_relation_code` (deterministic relation encoding),
    `l2_edge_sa_type_id` (type-pair+relation key, order-significant),
    `l2_initial_vector_for` (deterministic content-addressed init vector);
  - `l2_vector_to_bytes` / `bytes_to_l2_vector` (support_count + 24-dim float32
    BLOB);
  - `update_sa_type_vector_l1` / `load_sa_type_vector_l2` (loader always returns
    an entry, initial-vector fallback for NULL/zero/missing);
  - `l2_compose` (order-asymmetric: first half src*0.7+rel*0.3, second half
    dst*0.7+rel*0.3, normalized to magnitude 0.15);
  - `l2_cosine`;
  - `l2_structure_update_vector` (`z_edge += lr*sup*(ctx - z_edge)`, annealed);
  - `rebuild_phase20_7_indexes`: after L1 replay, wipes `vector_l2` for
    `substrate='text_edge'`, replays L2 structure updates from
    `experience_alignment` events in `created_at` order (composing the
    already-rebuilt L1 endpoints), upserts `l2_vector_index/v1` registry row,
    returns the `l2_vector_index` sub-dict.

- `apv3test/runtime/phase20_7/__init__.py`
  - exported the new L2 helpers.

- `apv3test/runtime/phase20_7/runtime.py`
  - `PHASE20_12_L2_STRUCTURE_UPDATE_ID`;
  - `_apply_l2_temporal_edge_update`: for the taught output sequence, forms
    `linear_next` type-pair edges between adjacent chars, upserts the edge
    sa_type, composes the endpoint L1 vectors, runs `l2_structure_update_vector`,
    writes `vector_l2`, returns a delta dict (`delta_kind="l2_temporal_edge_update"`,
    `projection_only=True`, `writes_answer_directly=False`); runs AFTER L1 in the
    same feedback step so endpoint L1 vectors are already learned;
  - `_record_teacher_feedback` now also calls `_apply_l2_temporal_edge_update` and
    returns `(feedback_event_id, alignment_event_id, l1_delta, l2_delta)`;
  - call site: strips ALL trailing dicts first (collecting into
    `trailing_deltas`), then filters remaining to str event ids, classifies by
    `delta_kind` into `l1_triplet_delta` / `l2_edge_delta`, adds both to the
    `integrate_feedback` tick's `learning_deltas`;
  - `_l2_successor_prediction`: takes the observation's last meaningful char as
    source `a'`, `LIKE`-prefix-finds learned `linear_next` edges starting from
    `a'`, ranks by edge support_count, decodes the best edge's dst from
    `canonical_hint`, emits a projection-only C_forward row
    (`kind="l2_temporal_edge_prediction"`);
  - `_l2_dst_sa_type_from_hint`: decodes dst sa_type_id from "src -> dst" hint;
  - wired `_l2_successor_prediction` into the `c_forward_rows` convergence point
    in `_tick_event` (single-point injection, mirroring `_cstar_carryover_c_forward`).

Test:

- `tests/test_phase20_12_l2_temporal_edge_embedding.py` (6 tests);
- `tests/test_phase20_8e_code_audit_and_unified_candidate.py` guardrail extended
  with `assert "l2_vector_converged" not in serialized`.

## 4. Bugs found and fixed during implementation

1. **L2 prediction row not firing (hash-prefix mismatch)**: `l2_edge_sa_type_id`
   encodes the endpoint as `_hash_text(src_sa_type_id)` — the hash of the full
   `"text_unit::<hash>"` string, NOT the raw char hash. The initial prediction
   query used the raw char hash for the `LIKE` prefix, so it matched nothing.
   Fixed: the prefix now uses `_hash_text(src_sa_id)`.

2. **Prediction semantics (cosine=0 between edge and live context)**: the first
   design compared the stored edge vector against `compose(observation's last two
   chars)`, but the edge was trained on `compose(taught a, taught b)` — a
   different context — so cosine was 0. Reframed the prediction to rank candidate
   edges by their learned `support_count` (with the LIKE prefix already pinning the
   source), surfacing the most-reinforced successor edge. This correctly layers
   L1 (endpoint similarity) and L2 (edge reinforcement) and matches the §173.2
   intent (L2 helps C_forward surface a successor).

3. **L1 delta dropped by str-filter in the call site (regression)**: the original
   L1 extraction did `feedback_event_ids = tuple(item for item in
   feedback_event_ids[:-1] if isinstance(item, str))` *inside* the trailing-dict
   strip loop. When two dicts (l1, l2) were returned, stripping l2 ran the str
   filter on `(eid, aid, l1_dict)`, which **discarded l1_dict** as a non-str — so
   L1 delta silently vanished. Fixed: strip all trailing dicts first into
   `trailing_deltas`, then filter the remaining tuple to str ids in one pass;
   classify by `delta_kind`. This restored the L1 delta (L1 test
   `test_phase20_11_teach_fills_vector_l1_and_emits_triplet_delta` had regressed
   and now passes again).

## 5. Acceptance

Run from the `APV3.0test` root (running in the upper repo root causes path-level
errors):

- `python -m py_compile` on `experience_log.py`, `__init__.py`, `runtime.py`,
  test file — `BYTE_COMPILE_OK`;
- `node --check apv3test/web/static/phase20_7_workbench.js` — `NODE_CHECK_OK`;
- `python -m pytest -q tests/test_phase20_12_l2_temporal_edge_embedding.py` —
  6 passed;
- regression suite (12 files, 45 tests): stage1/stage3/stage2, 8e/8h/8i/8j,
  9i, 10l/10m, 11 (L1), 12 (L2) — **45 passed in 15.74s**;
- `python scripts/red_line_check_v14.py` — zero hits; the scanner covers all
  modified files (recursive `apv3test/**/*.py` glob plus the explicit phase20_7
  list including `experience_log.py` and `runtime.py`).

## 6. Plain Example

After one teaching turn ("你好啊" -> "你也好"):

- the taught output's adjacent pairs 你->也, 也->好 each get a non-zero
  `vector_l2` on their `text_edge::linear_next::...` sa_types, with
  support_count >= 1;
- the `integrate_feedback` tick's `learning_deltas` contains an
  `l2_temporal_edge_update` delta marked `projection_only=True` (alongside the
  existing L1 delta, which is preserved);
- a later query ending in a taught edge source (e.g. "你也" ending in 也, which
  is the source of 也->好) produces an `l2_temporal_edge_prediction` C_forward row
  with `predicted_dst_sa_type_id` = the 好 endpoint, `l2_edge_support > 0`,
  `projection_only=True`;
- a far-text query ("你是谁") still requests the teacher with no fake B and no
  L2 prediction leak (谁 was never taught, so no edge starts from it);
- the forward edge 你->也 and its reverse 也->你 yield **different** L2 vectors
  (order asymmetry, §173.3), and `compose()` is order-asymmetric at the primitive
  level too.

## 7. Boundaries

This step can prove:

- L2 temporal-edge embedding fills the existing `vector_l2` column from the
  runtime's own structure learning, with no new cognitive entity;
- order asymmetry holds at both the key and vector level (§173.3 / §173.8);
- L2 layers correctly with SSP (explicit edges stay) and with L1 (endpoint
  similarity), and only adds a learned soft-similarity C_forward row at a single
  convergence point;
- the L2 index is rebuildable from the experience log;
- far text still requests the teacher; the L1 delta is preserved (no regression);
  no completion claims are emitted.

This step cannot yet claim:

- complete L1/L2/L3 online embedding (L3 action-consequence embedding is still
  unimplemented — `vector_l3` remains unused);
- L2 convergence (no convergence metric or claim is emitted);
- L2 C_backward side (order-predecessor attribution) — deferred to a next step
  after C_forward was confirmed;
- L2 spatial/causal edges (visual substrate not yet in this runtime; causal is
  the higher C_backward tier);
- complete six-stage runtime; complete paradigm self-learning; mathematical
  column calculation; object-centric visual imagination completion; Phase21
  visual teaching generalization closure.

## 8. Next Step

The natural next runtime-facing boundary is one of:

- **L2 C_backward side**: add the order-predecessor attribution row at the
  `c_backward_rows` convergence point (mirroring the C_forward cut), so L2 also
  helps "what usually came before this" — same no-new-entity pattern, same
  guardrails; or
- **L3 action-consequence online embedding** (§173.2 "L3 行动后果与奖惩, 帮 action
  competition"): fill the existing `vector_l3` column the same no-new-entity way —
  triplet/annealed updates driven by action outcome (reward/punish) in the
  experience flow, injected as a modulation on `action_competition` drive, with a
  rebuildable `l3_vector_index/v1` and the same far-text no-leak / no-completion
  guardrails.

Each step stays on the runtime learning boundary rather than adding display
depth. The C_backward side is the smaller, lower-risk continuation of the L2
work already in flight; L3 is the next whitepaper-mandated embedding tier
(§173.7 "最后实现 L3, 接 action competition").
