# Phase 8.17 Final Report - Autobiographical Recall

## Design

Phase 8.17 adds autobiographical memory:

- episodes have cue SA ids
- episodes have entity anchors
- recall requires cue and entity match
- recalled episode emits REMEMBERED marker

## Review

The implementation keeps entity anchors structural. It does not parse names or rely on dialogue text.

## Landing

Added:

- `runtime/cognitive/long_term/autobiographical.py`
- `tests/test_phase8_17_autobiographical_recall.py`

## Validation

Targeted tests verify:

- cue + entity recall emits REMEMBERED marker
- different entity anchor does not recall the episode

## Boundary

This phase proves a minimal autobiographical recall substrate, not full narrative memory.
