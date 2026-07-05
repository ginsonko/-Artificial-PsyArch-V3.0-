# Phase 8.4 Final Report - SDPL + ComposedVocab

## Design

Phase 8.4 implements the first source-aware learning substrate:

- `LearningPacket` separates content SA, epistemic source markers, feeling SA, and slot context.
- `QTableWithBackoff` uses five layers: exact, content+source, source+feeling, content-only, and action-global.
- `SparsePairwiseGraph` records sparse pairwise co-occurrence under packet keys.
- `HeldOutPool` and `evaluate_delta_p_incremental` gate composed vocab candidates by held-out pressure reduction.
- IMAGINED and REMEMBERED markers enter the same marker substrate as PERCEIVED, HEARSAY, and CORRECTION.

## Review

The implementation review found one concrete contract gap:

- `composed_vocab.delta_p.positive_ratio_min` was read by the Delta-P evaluator but was missing from the governed constants file. It is now in `config/apv3_constants.yaml`.

The targeted tests separate same content under PERCEIVED and IMAGINED packets, so imagination can participate in learning without overwriting real-world evidence.

## Landing

Added runtime files:

- `runtime/cognitive/sdpl/packet.py`
- `runtime/cognitive/sdpl/q_table_backoff.py`
- `runtime/cognitive/composed_vocab/sparse_pairwise.py`
- `runtime/cognitive/composed_vocab/held_out_pool.py`
- `runtime/cognitive/composed_vocab/delta_p_cold_fork.py`
- `runtime/cognitive/endogenous/imagined_marker_spawn.py`
- `runtime/cognitive/long_term/rehydration.py`

Added tests:

- `tests/test_phase8_4_sdpl_composed_vocab.py`

## Validation

Planned validation:

- Phase 8.4 pytest.
- `python scripts/red_line_check_v14.py --phase 8.4`
- `python scripts/check_constant_governance.py`
- Regression with Phase 8.2/8.3 tests.

## Boundary

This phase proves source-aware learning packets, sparse composed vocab evidence, and held-out Delta-P gating exist. It does not yet prove visual grounding, natural correction learning, sleep/endogenous convergence, audio, long-term autobiographical recall, or full open Chinese dialogue.
