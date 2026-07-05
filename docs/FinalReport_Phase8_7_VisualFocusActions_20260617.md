# Phase 8.7 Final Report - Visual Focus Actions

## Design

Phase 8.7 adds visual focus as action competition:

- `saccade_to_visual`
- `fixate_visual`
- `release_visual`

The proposals are scored from normalized visual SA energy fields. They do not decode object labels or route by keywords.

## Review

Focus actions update attention through the same state item and ledger trace used elsewhere. The overlay is render-only trace data for the workbench.

## Landing

Added:

- `runtime/cognitive/attention/visual_focus.py`
- `tests/test_phase8_7_visual_focus.py`

Updated:

- `config/apv3_constants.yaml`

## Validation

Targeted tests verify:

- Three visual focus action types are produced.
- Applying a focus action updates attention and ledger.
- Overlay output is a small renderable trace.

## Boundary

This phase proves visual attention action proposals. It does not yet prove yellow-apple generalization, natural correction, or cross-session memory.
