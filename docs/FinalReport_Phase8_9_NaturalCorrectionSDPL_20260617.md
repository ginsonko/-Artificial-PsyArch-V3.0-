# Phase 8.9 Final Report - Natural Correction + SDPL Credit

## Design

Phase 8.9 connects correction to packet-level action learning:

- A CORRECTION marker carries negative feedback evidence.
- The action Q table updates by the original SDPL packet, not by content alone.
- Two-stage credit uses immediate penalty plus a delayed eligibility-weighted penalty.

## Review

This keeps the anthropomorphic distinction intact: an imagined packet can learn that an action was punished while the same content under a perceived packet remains valuable.

## Landing

Added:

- `runtime/cognitive/correction/natural_correction.py`
- `tests/test_phase8_9_natural_correction_sdpl.py`

## Validation

Targeted tests verify:

- correction penalizes the imagined packet without erasing the perceived packet
- delayed credit is weaker than near credit

## Boundary

This phase proves packet-level correction credit. It does not yet implement a full natural language correction parser or UI feedback loop.
