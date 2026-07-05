# Phase 8.8 Final Report - Visual Composition Generalization

## Design

Phase 8.8 turns the yellow-apple scenario into a structural visual composition test:

- positive contrast: target color + target shape co-occur
- distractors: target color with other shape, and other color with target shape
- candidate promotion: only a joint candidate can pass Delta-P

The test uses opaque SA ids rather than Chinese words or answer labels.

## Review

Implementation review found one important correction:

- Delta-P must not reward a composed vocab candidate for partial component overlap.
- Candidate promotion now requires a governed minimum component count.
- Delta-P is counted only when all candidate components are present in a held-out situation.

This prevents a single high-frequency component from being promoted as if it were a learned composition.

## Landing

Added:

- `runtime/cognitive/composed_vocab/contrast_generalization.py`
- `tests/test_phase8_8_yellow_apple_generalization.py`

Updated:

- `runtime/cognitive/composed_vocab/delta_p_cold_fork.py`
- `config/apv3_constants.yaml`

## Validation

Targeted tests verify:

- target pair co-occurrence separates from distractor pairs
- joint candidate passes Delta-P
- single-slot ablation fails

## Boundary

This phase proves a minimal visual composition gate. It does not yet prove raw image recognition, natural language naming, or full multimodal dialogue grounding.
