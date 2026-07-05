# APV3.0 Phase 19.3a Final Report - Visual LOO Probe

Scope: Phase 19.3a only.

## Design

Phase 19.3a runs leave-one-out probes over clean visual teaching cards through the Phase 19.0a receptor and Phase 19.2 confidence formula.

## Review

The probe reports confidence/tier and source cleanliness. It forbids filename-label oracle use.

## Landing

Implemented via `visual_loo_probe` in `runtime/cognitive/percept_vector/phase19_runtime.py`.

## Validation

Covered by `tests/test_phase19_3_visual_probes.py`.

## Boundary

This is a clean-card visual probe, not a claim of broad real-photo recognition.

## Next

Next phase is Phase 19.3b: real-photo stress probe.
