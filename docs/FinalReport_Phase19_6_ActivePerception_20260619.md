# APV3.0 Phase 19.6 Final Report - Active Perception

Scope: Phase 19.6 only.

## Design

Phase 19.6 chooses the next fixation from low clarity, low confidence, and optional peripheral motion.

## Review

This is an anthropomorphic attention repair: the system looks where it lacks detail or where motion asks for reinspection.

## Landing

Implemented via `choose_next_fixation` and `active_visual_scan`.

## Validation

Covered by `tests/test_phase19_audio_feedback_active.py`.

## Boundary

This proves active fixation mechanics, not full open dialogue.

## Next

Phase 19 can now be summarized with a public-readable showcase.
