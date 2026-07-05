# APV3.0 Phase 19.2 Final Report - Humanlike Confidence

Scope: Phase 19.2 only.

## Design

Phase 19.2 implements raw confidence and decision tier as separate values: thresholded top-m cue pooling, active-cue diagnosticity, source reliability, shifted nearest-negative margin, and novelty downgrade.

## Review

The formula is anthropomorphic rather than maximum-correctness oriented: a few strong cues can produce a soft or firm call, equal top candidates do not get fake margin confidence, and context novelty asks for reinspection rather than forced no-call.

## Landing

Implemented in `runtime/cognitive/percept_vector/phase19_runtime.py`.

## Validation

Covered by `tests/test_phase19_2_humanlike_confidence.py`.

## Boundary

This proves confidence math behavior. It does not prove real category accuracy.

## Next

Next phases are 19.3a/19.3b visual probes.
