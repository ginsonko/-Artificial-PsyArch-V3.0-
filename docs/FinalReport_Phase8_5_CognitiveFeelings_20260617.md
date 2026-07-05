# Phase 8.5 Final Report - Cognitive Feelings

## Design

Phase 8.5 implements the CFS feeling layer required by v14/v14.1:

- Core CFS channels: fluency, boredom, fulfillment, satisfaction.
- Epistemic source feelings: reality_sense, imagination_sense, hearsay_sense, guess_sense, incongruity.
- Marker evidence is converted with continuous sigmoid-style energy signals, not binary feature routing.

## Review

The implementation keeps feelings as trace values and SDPL packet features. It does not use marker kind to select answers or actions.

The important v14.1 invariant is preserved: absent source evidence has a governed zero floor, while present marker energy is mapped continuously.

## Landing

Added:

- `runtime/cognitive/cognitive_feelings/factory.py`
- `runtime/cognitive/cognitive_feelings/epistemic_source_feelings.py`
- `tests/test_phase8_5_cognitive_feelings.py`

Updated:

- `config/apv3_constants.yaml`

## Validation

Targeted tests verify:

- PERCEIVED and IMAGINED evidence produce different source feelings.
- HEARSAY, guess, and incongruity are numeric trace values.
- Feelings can be exported into SDPL packet `FeelingValue` objects.
- `python scripts/red_line_check_v14.py --phase 8.5` passes.

## Boundary

This phase proves the feeling factory exists and is source-aware. It does not yet prove visual grounding, natural correction learning, or long-term autobiographical behavior.
