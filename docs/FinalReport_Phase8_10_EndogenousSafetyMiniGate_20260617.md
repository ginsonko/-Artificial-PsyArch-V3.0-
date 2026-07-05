# Phase 8.10 Final Report - Endogenous Drive + Safety Mini-Gate

## Design

Phase 8.10 implements the minimal stability gate:

- endogenous drive from unfinished pressure, expectation pressure, and residual mass
- Prediction Pi update and absent decay
- habituation through fatigue
- continuous sleep-like tick dilation from global fatigue
- convex attention mixing by endogenous share
- external surprise safety gate

## Review

The implementation does not introduce a sleep/wake state machine. Fatigue only changes continuous timing pressure. External surprise does not erase imagination; it temporarily selects external attention score when external share and pressure are high.

## Landing

Added:

- `runtime/cognitive/endogenous/step.py`
- `runtime/cognitive/attention/safety_gate.py`
- `runtime/cognitive/marker/spawn_novelty.py`
- `tests/test_phase8_10_endogenous_safety_mini_gate.py`

Updated:

- `config/apv3_constants.yaml`
- `config/marker_spawn_rules.yaml`

## Validation

Targeted tests verify:

- three endogenous ledger sources inject attention
- Pi rises with occurrence and decays without zeroing when absent
- habituation lowers attention score and fatigue increases tick dilation
- external surprise safety gate overrides the endogenous mix
- `python scripts/red_line_check_v14.py --phase 8.10` passes

## Boundary

This phase proves the mini-gate and continuous stabilization primitives. It does not yet prove long-run autonomous sleep behavior or full embodied survival dynamics.
