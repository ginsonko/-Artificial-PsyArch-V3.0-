# APV3.0 Phase 19.7 Adversarial Review - Diagnostic-First Recognition

Date: 2026-06-19

## Verdict

Claude's core diagnosis is partially correct:

- Correct: the old effect probe used full-vector cosine and direct argmax, which makes fruit photos saturate and produces tiny margins.
- Correct: a formal recognizer should expose C recall, B recall, channel-wise diagnostic evidence, and channel ablation audit.
- Not yet proven: replacing full-vector cosine with channel noisy-OR solves real-photo generalization.

## Implementation Probe

An experimental `visual_recognize_v1_7` was added in `runtime/cognitive/percept_vector/phase19_runtime.py` and the public effect page was regenerated through the Phase 19.7 path.

Result on the same 12 user real-photo probes:

- Old Phase 19 effect probe: 9/12 top-1, mostly `ambig`, average margin still tiny.
- First channel-only 19.7 probe: 4/12 top-1.
- 19.7 with V0 sensory-sketch channel included: 6/12 top-1.

This means the structural path is better audited, but the recognition quality is worse than the old full-vector baseline.

## Root Cause

The deeper blocker is not only the scoring formula. The current clean-card concept prototypes do not contain enough diagnostic diversity for real photos:

- V6 shape geometry is almost identical for clean apple, banana, and orange in current generated cards.
- V7 part coverage is too weak and does not encode human-salient fruit parts reliably.
- V2/V3/V4 channels remain highly similar across fruits after clean-card-to-real-photo domain shift.
- Adding V0 helps, but still does not create a stable diagnostic margin.

## Design Corrections

Phase 19.7 should not be accepted as complete with the current formula. A v1g/micro-errata should require:

- better concept prototypes from multiple clean card variants plus curated real teaching examples,
- subject descriptor quality gates before using subject-weighted evidence,
- channel baselines calibrated on train-only domain diversity, not held-out probes,
- a report that compares old cosine, channel-only, and hybrid channel evidence without overclaiming,
- no hard promise of 10/12 or 11/12 until the prototype data becomes sufficiently diagnostic.

## Current Boundary

The current 19.7 experimental implementation proves auditability, not improved recognition quality. It should not be used as proof that the real-photo generalization issue is solved.

## Validation

Commands run after the experimental landing:

- `python scripts/reports/render_phase19_generalization_effect_probe.py` -> generated updated effect page through `visual_recognize_v1_7`
- `python scripts/red_line_check_v14.py --phase 19.all` -> PASS
- `python -m pytest tests/test_phase19_3_visual_probes.py tests/test_phase19_0a_foveated_visual_repair.py tests/test_phase19_0b1_vector_population.py -q` -> 17 passed

