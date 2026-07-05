# Phase 8.15 Final Report - Long-Term Cold/Active Dual Layer

## Design

Phase 8.15 adds explicit short-to-long flow:

- short-term SA can be admitted into a cold index
- cue match rehydrates cold SA into active pool
- active pool is capped
- rehydration emits REMEMBERED markers

## Review

The design avoids making long-term memory permanently active. It is recalled by cue, then bounded by active pool capacity.

## Landing

Added:

- `runtime/cognitive/long_term/layers.py`
- `tests/test_phase8_15_long_term_dual_layer.py`

## Validation

Targeted tests verify:

- cold admission and rehydration
- REMEMBERED marker emission
- active pool cap with cold fallback

## Boundary

This phase proves the dual-layer memory mechanics, not rich autobiographical organization.
