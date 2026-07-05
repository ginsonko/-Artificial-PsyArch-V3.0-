# Phase 13.6 Final Report - Expression Paradigm Curriculum

## Design

Expression candidates follow the quiet, terse persona direction: short token sequences, no full-sentence macro style.

## Review

`audit_style_tag` is kept as audit metadata only. Selection must still go through existing AP-native phrase/cooccurrence/Q paths.

## Landing

Implemented `expression_paradigm.py`.

## Validation

`tests/test_phase13_6_expression_paradigm_curriculum.py` verifies a 20-item short corpus passes and a long macro sentence is rejected.

## Boundary

This is a first alpha expression corpus gate, not the final 200-300 paradigm library.

## Next

Phase 13.7 adds action prototype curriculum.

