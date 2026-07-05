# Phase20.12b L2 C_backward 顺序前驱归因

Date: 2026-06-29

Formula:

`apv3_phase20_12_l2_temporal_edge_embedding_structure_update/v1` (same model id as
Phase20.12; 12b reuses the already-learned edge vectors, only adding the backward
read side — no new update formula).

## 1. Design

Phase20.12 landed L2 temporal-edge embedding on the **C_forward side**: taught
output sequences form `linear_next` type-pair edges that fill the existing
`vector_l2` column, and a projection-only `l2_temporal_edge_prediction` row is
appended at the `c_forward_rows` convergence point. The Phase20.12 design doc
§2.3 explicitly deferred the C_backward side ("先只做 C_forward 一侧……C_backward
侧留到确认 C_forward 注入无误后再加").

Phase20.12b is that deferred **C_backward mirror cut**. It does NOT add any new
edge-vector update — it only adds a backward read of the already-learned
`linear_next` edges, surfacing the historical predecessor ("what usually came
before this") per whitepaper §1160 C_backward definition and §173.2 "L2 帮
C_forward/C_backward". This closes the L2 tier before moving to L3.

The order-asymmetry (§173.3 `z_next(a->b) != z_next(b->a)`) is realized here as
**opposite query direction** on the same learned edges:
- C_forward (12): take the current last char as **source** `a'`, LIKE-prefix
  `text_edge::linear_next::<hash(a'_sa_id)>->%` finds edges **starting at** `a'`
  → predict successor dst.
- C_backward (12b): take the current last char as **dst** `b'`, LIKE-suffix
  `text_edge::linear_next::%-><hash(b'_sa_id)>` finds edges **ending at** `b'`
  → attribute predecessor src.

Same learned edge vectors, opposite query direction — the §173.8
"狗咬我/我咬狗" asymmetry landed on the C_backward side.

## 2. No-New-Entity Review (user-signed)

Phase20.12b does not add:

- a new table, column, or substrate — it only READS the `vector_l2` that
  Phase20.12 already filled;
- a new cognitive entity — `_l2_predecessor_attribution` is the mirror of
  `_l2_successor_prediction`, peer to `_cstar_carryover_c_backward` and
  `_short_structure_flow_query_c_backward`, all appendable rows at the same
  convergence point;
- a replication of SSP's occurrence-level explicit edges — it queries only the
  learned `linear_next` type-pair edges;
- an external LLM vector — the predecessor sa_type_id is decoded from the edge's
  `canonical_hint` ("src -> dst") by the runtime itself (§24/§132 derived
  quantity).

User decision signed: C_backward mirror cut, reusing Phase20.12's learned edges,
no new update formula.

## 3. Implementation

Files:

- `apv3test/runtime/phase20_7/runtime.py`
  - `_l2_src_sa_type_from_hint(hint)`: mirror of `_l2_dst_sa_type_from_hint`;
    decodes the src endpoint sa_type_id from "src -> dst" (the predecessor).
    Docstring cites §1160 "历史上这种现状之前通常有什么条件".
  - `_l2_predecessor_attribution(conn, *, observation)`: the backward mirror of
    `_l2_successor_prediction`. Takes the observation's last meaningful char as
    dst `b'`, LIKE-suffix-finds learned `linear_next` edges ENDING at `b'`
    (suffix `%->{dst_edge_hash}` where `dst_edge_hash = _hash_text(dst_sa_id)`,
    same encoding rule as the C_forward prefix), ranks by edge support_count
    (score = min(1.0, 0.4 + 0.12*support_count), same scoring as C_forward so
    the two directions are comparable), decodes the best edge's src via
    `_l2_src_sa_type_from_hint`, emits a projection-only C_backward row
    (`kind="l2_temporal_edge_predecessor"`, `attributed_cause_sa_type_id`,
    `current_dst_sa_type_id`, `cause_grasp`, `e_backward`, `cause_slots`,
    `may_be_wrong=True`, `projection_only=True`, `writes_answer_directly=False`).
  - wired `_l2_predecessor_attribution` into the `c_backward_rows` convergence
    point in `_tick_event` (single-point injection, alongside
    `_cstar_carryover_c_backward` and `_short_structure_flow_query_c_backward`,
    mirroring the C_forward cut that appends `_l2_successor_prediction`).

No changes to `experience_log.py` or `__init__.py` — 12b reuses the Phase20.12
helpers (`bytes_to_l2_vector`, `L2_RELATION_LINEAR_NEXT`,
`PHASE20_12_L2_STRUCTURE_UPDATE_ID`) already exported there.

Test:

- `tests/test_phase20_12b_l2_c_backward.py` (6 tests);
- `tests/test_phase20_8e_code_audit_and_unified_candidate.py` guardrail
  (the `l2_vector_converged` ban added in Phase20.12 covers 12b too).

## 4. Bugs found and fixed during implementation

None new in 12b. The two encoding/scoring consistency rules that Phase20.12
discovered the hard way were applied from the start here:

1. **LIKE-suffix encoding**: `l2_edge_sa_type_id` encodes the endpoint as
   `_hash_text(<full sa_type_id>)` (hash of the full `"text_unit::<hash>"`
   string), so the LIKE suffix must embed `_hash_text(dst_sa_id)`, NOT the raw
   char hash. The C_forward cut hit this as a bug (prefix mismatched, matched
   nothing); 12b applied the corrected rule directly to the suffix.
2. **Scoring by support_count, not live-context cosine**: the edge was trained
   on `compose(taught a, taught b)`; comparing it against `compose(observation's
   last two chars)` is a different context and yields cosine 0. 12b ranks
   candidate edges by their learned `support_count` (with the LIKE suffix
   already pinning the dst exactly), mirroring the C_forward fix.

## 5. Acceptance

Run from the `APV3.0test` root (running in the upper repo root causes path-level
errors):

- `python -m py_compile` on `runtime.py`, test file — `BYTE_COMPILE_OK`;
- `node --check apv3test/web/static/phase20_7_workbench.js` — `NODE_CHECK_OK`;
- `python -m pytest -q tests/test_phase20_12b_l2_c_backward.py` — 6 passed;
- regression suite (13 files, 51 tests): stage1/stage3/stage2, 8e/8h/8i/8j,
  9i, 10l/10m, 11 (L1), 12 (L2 C_forward), 12b (L2 C_backward) —
  **51 passed in 17.21s**;
- `python scripts/red_line_check_v14.py` — zero hits.

## 6. Plain Example

After one teaching turn ("你好啊" -> "你也好"), the taught output's adjacent
pairs 你->也, 也->好 each have a learned `linear_next` type-pair edge with
non-zero `vector_l2` and support_count >= 1 (from Phase20.12).

- a later query ending in 好 (e.g. "也好") produces an
  `l2_temporal_edge_predecessor` C_backward row with
  `attributed_cause_sa_type_id` = the 也 endpoint (也->好 edge), `l2_edge_support > 0`,
  `projection_only=True`;
- a query ending in 也 (e.g. "你也") attributes 你 as the predecessor (你->也 edge)
  — different dst attributes a different predecessor;
- the C_forward side predicts 也's successor is 好 (也->好 edge); the C_backward
  side attributes 好's predecessor is 也 (also 也->好 edge) — **same edge, opposite
  query direction**, the §173.3 asymmetry self-consistent;
- a far-text query ("你是谁") still requests the teacher with no fake B and no
  L2 predecessor leak (谁 was never taught, so no edge ends at it);
- the predecessor attribution survives `rebuild_phase20_7_indexes` (edge vectors
  rebuildable from the experience log).

## 7. Boundaries

This step can prove:

- L2 C_backward predecessor attribution reads the already-learned `linear_next`
  type-pair edges and surfaces the historical predecessor at the
  `c_backward_rows` convergence point, with no new cognitive entity and no new
  edge-vector update;
- order asymmetry is self-consistent between C_forward and C_backward (same
  learned edges, opposite query direction, §173.3/§173.8);
- L2 C_backward layers correctly with the existing `_cstar_carryover_c_backward`
  and `_short_structure_flow_query_c_backward` rows (single-point append, no
  override);
- the predecessor attribution survives an index rebuild; far text still requests
  the teacher; no completion claims are emitted.

This step cannot yet claim:

- complete L1/L2/L3 online embedding (L3 action-consequence embedding is still
  unimplemented — `vector_l3` remains unused);
- L2 convergence (no convergence metric or claim is emitted);
- L2 spatial/causal edges (visual substrate not yet in this runtime; causal is
  the higher C_backward tier);
- complete six-stage runtime; complete paradigm self-learning; mathematical
  column calculation; object-centric visual imagination completion; Phase21
  visual teaching generalization closure.

## 8. Next Step

With L2's C_forward (Phase20.12) and C_backward (Phase20.12b) both closed, the
next whitepaper-mandated embedding tier is **L3 action-consequence online
embedding** (§173.2 "L3 行动后果与奖惩, 帮 action competition"; §173.7 "最后实现
L3, 接 action competition"): fill the existing `vector_l3` column the same
no-new-entity way — triplet/annealed updates driven by action outcome
(reward/punish) in the experience flow, injected as a modulation on
`action_competition` drive, with a rebuildable `l3_vector_index/v1` and the same
far-text no-leak / no-completion guardrails.

The L2 tier (C_forward + C_backward) is now complete; the runtime learning
boundary moves to L3.
