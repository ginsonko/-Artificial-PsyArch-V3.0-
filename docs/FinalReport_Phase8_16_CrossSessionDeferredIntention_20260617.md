# Phase 8.16 Final Report - Cross-Session Deferred Intention

## Design

Phase 8.16 implements cross-session deferred intention:

- an action id is associated with cue SA ids
- the association is persisted
- a later session recalls the action from matching cue SA

## Review

The test does not depend on sleep. It uses a temporary SQLite file and action ids, not natural language labels.

## Landing

Added:

- `runtime/cognitive/long_term/deferred_intention.py`
- `tests/test_phase8_16_cross_session_deferred_intention.py`

## Validation

Targeted tests verify:

- save in one session, load in another, recall by cue
- unrelated cue does not emit the action

## Boundary

This phase proves deferred intention persistence mechanics, not full planning.
