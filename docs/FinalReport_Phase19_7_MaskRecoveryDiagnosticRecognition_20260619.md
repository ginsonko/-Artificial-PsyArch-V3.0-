# APV3 Phase 19.7 Final Report: Mask Recovery + Diagnostic Recognition

## Design

Phase 19.7 responds to the real-photo generalization stress test after Phase 19.0-19.6. The goal is not to claim full open-world vision, but to close the specific implementation gap exposed by the user's apple/banana/orange photos:

- the old stress probe used broad vector similarity too directly;
- the subject mask was flattening elongated objects;
- the recognition score lacked channel-level audit;
- confidence needed to depend on competition against nearest negative evidence.

The intended path is:

`PERCEIVED real image -> receptor channels -> subject mask -> C recall -> B episodic recall -> channel diagnostic evidence -> nearest-negative margin -> humanlike tier`.

## Review

Claude's v1g diagnosis was substantially correct: the legacy quick mask used a mean-threshold saliency rule that can keep a broad square-ish region and erase the banana's elongated subject geometry. This is not only a correctness issue; it produces non-human evidence because shape channels V6/V7/V8/V9 appear to vote while their input subject is degraded.

The review also found two additional implementation risks:

- A channel-validity hard gate that is too strict can punish real teaching diversity and disable useful channels.
- Nearest-negative evidence must be cross-concept, not an intra-concept spread approximation.

## Landing

Implemented changes:

- `_quick_mask()` now delegates to `solve_subject_mask()` instead of the old mean-threshold formula.
- Phase 19.7 recognition now records a channel validity map from training examples.
- Channel evidence now compares each candidate against the nearest cross-concept negative example.
- Positive evidence is margin-gated, so a channel only strongly votes when it beats its closest competitor.
- The generalization report now shows two modes separately:
  - `clean_cards_only`: only Phase 18 clean cards used for teaching.
  - `diagnostic_library`: clean cards plus existing real training assets.
- Added `tests/test_phase19_7_mask_recovery.py`.
- Added Phase 19.7 deliverable gate to `scripts/red_line_check_v14.py`.

## Validation

Commands run:

```text
python -m pytest tests/test_phase19_7_mask_recovery.py -q
python -m pytest tests/test_phase19_3_visual_probes.py tests/test_phase19_0a_foveated_visual_repair.py tests/test_phase19_0b1_vector_population.py -q
python scripts/reports/render_phase19_generalization_effect_probe.py
python scripts/red_line_check_v14.py --phase 19.all
python scripts/check_constant_governance.py
```

Results:

- Phase 19.7 targeted tests: `4 passed`.
- Related Phase 19 regression tests: `17 passed`.
- Red line: `PASS`.
- Constant governance: `PASS`, 459 numeric constants.
- Report regenerated: `reports/APV3_Phase19_GeneralizationEffectProbe_20260619.html`.

Observed real-photo stress result:

- `clean_cards_only`: top tendency is `8/12`, but all decisions are `no_call` after the stricter nearest-negative margin gate.
- `diagnostic_library`: top tendency is `4/12`, also all `no_call`.

This means the mask bug was real and the pipeline is now more honest, but the desired humanlike real-photo generalization is not solved yet.

## Boundary

Phase 19.7 proves:

- the legacy subject-mask failure is removed from the fast path;
- the diagnostic path no longer rewards full-vector saturation as confidence;
- wrong or weak calls do not become firm;
- channel evidence is auditable.

Phase 19.7 does not prove:

- robust real-photo apple/banana/orange recognition;
- high-confidence humanlike object recognition from clean cards alone;
- sufficient local part/texture representation for natural images;
- true multi-fixation accumulation inside the recognition score.

## Next

The next necessary repair should not change the philosophical target. It should make the visual experience more humanlike:

1. Use real multi-fixation features in scoring, not only an audit fixation log.
2. Build a real diagnostic teaching library with train/held-out separation instead of mixing a small existing real asset set.
3. Add local part and contour channels that can represent stems, curved banana bodies, peel highlights, fruit boundary, and surface texture without relying on filename labels.
4. Keep the current no-call behavior until nearest-negative margins become large enough.

Only after those gates improve should the project claim that Phase 19 has solved the original real-photo generalization problem.
