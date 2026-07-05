# Phase 18.1 Errata - Real Photo Probe Was Label-Mediated

Date: 2026-06-19

## Correction

Phase 18.1 is reclassified.

It proves:

- the course replay workbench can connect clean-card teaching assets and real-photo probe assets in one auditable trace;
- both manifests appear in the trace;
- Web/API/SQLite plumbing works.

It does not prove:

- true visual generalization from clean concept cards to real photos;
- pixel-driven recognition of apple / banana / orange;
- robust real-scene visual understanding.

## Cause

The probe packet still contained curriculum semantic fields such as `neutral_label` and `entry_id`. Therefore the Q score could be produced by the package label and energy bucket rather than by visual evidence extracted from the image.

The `held-out > contrast` result was also confounded by the different `intended_use` energy buckets. This means the result is not a valid visual discrimination proof.

## Runtime Patch

`real_photo_generalization` traces now return:

- `visual_generalization_valid: false`
- `audit_status: plumbing_only_label_mediated_probe`
- `rejection_reason: probe_packet_contains_curriculum_label_and_energy_bucket_confound`
- final output: `还不能确认`

## Next

Phase 18.2 must implement a visual-only probe gate:

- student-side probe packet must not contain label / entry id / target class;
- visual evidence must come from image-derived percept prototypes or comparable AP-native visual features;
- external evaluator may know the answer, but AP packet content must not;
- held-out real photo must beat contrast without using `intended_use` energy as the deciding evidence.
