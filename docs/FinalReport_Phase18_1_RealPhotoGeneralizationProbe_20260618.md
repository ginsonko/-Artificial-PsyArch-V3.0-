# Phase 18.1 Final Report - Real Photo Generalization Probe Audit Correction

Date: 2026-06-18, corrected 2026-06-19

## Audit Correction

Phase 18.1 is reclassified after user review.

It is not a valid visual generalization proof. The trace proves cross-asset replay plumbing, but the apparent `held-out > contrast` result is label-mediated and confounded by `intended_use` energy buckets.

Current runtime marks these demos with:

- `visual_generalization_valid: false`
- `audit_status: plumbing_only_label_mediated_probe`
- `rejection_reason: probe_packet_contains_curriculum_label_and_energy_bucket_confound`
- final output: `还不能确认`

## Design

Phase 18.1 takes the Phase 18.0 clean concept-card curriculum and routes Phase 17 real photos into the same replay trace. After audit, this is treated as a plumbing probe, not a visual recognition result.

## Review

Key review decisions:

- Do not use noisy real photos as first-layer teaching material.
- Do use real photos as probe assets after clean-card concept tendency exists.
- Do not let curriculum metadata such as `teaching_intent` split the concept content key.
- Do not claim arbitrary real-world visual recognition.
- Do not claim the current trace distinguishes real photo pixels, because `neutral_label` remains in packet content.
- Keep the Phase 15 Web workbench rendering returned runtime trace fields only.

## Landing

Completed:

- `apv3test/runtime/course_replay.py` supports cross-package probe demos.
- Three new demos:
  - `demo_generalize_clean_to_real_apple`
  - `demo_generalize_clean_to_real_banana`
  - `demo_generalize_clean_to_real_orange`
- `scripts/reports/render_phase18_1_showcase.py`
- `tests/test_phase18_1_real_photo_generalization_probe.py`
- `reports/APV3_Phase18_1_RealPhotoGeneralizationProbe_Showcase_20260618.html`

Runtime behavior:

- tick 1-2: clean-card teaching material enters and updates SDPL Q.
- tick 3: Phase 17 real held-out photo enters the trace, but the packet still contains label-mediated content.
- tick 4: Phase 17 real contrast photo remains lower, but this is confounded by the contrast energy bucket.
- tick 5-6: the runtime now refuses to present the result as visual recognition and outputs `还不能确认`.

## Validation

Targeted test:

```powershell
python -m pytest tests/test_phase18_1_real_photo_generalization_probe.py -q
```

Result: `7 passed in 5.80s`.

Phase 15/17/18 compatibility:

```powershell
python -m pytest tests/test_phase15_0_course_replay_runtime.py tests/test_phase15_1_course_replay_web_api.py tests/test_phase15_2_course_replay_frontend_contract.py tests/test_phase15_3_public_showcase.py tests/test_phase17_0_real_visual_assets.py tests/test_phase18_0_clean_concept_cards.py tests/test_phase18_1_real_photo_generalization_probe.py -q
```

Result: `37 passed in 19.62s`.

Deliverable gate:

```powershell
python scripts\red_line_check_v14.py --phase 18.1
```

Result: Phase 18.1 deliverables present and global red line passed.

Global red line:

```powershell
python scripts\red_line_check_v14.py
```

Result: `OK: All red line checks pass on runtime/cognitive`.

Constant governance:

```powershell
python scripts\check_constant_governance.py
```

Result: `OK: Governance check passed (316 numeric constants)`.

Phase 14-18 nearby regression:

```powershell
python -m pytest tests/test_phase14_0_asset_governance.py tests/test_phase14_1_synthetic_assets.py tests/test_phase14_2_neutral_curriculum_packs.py tests/test_phase14_3_public_showcase.py tests/test_phase15_0_course_replay_runtime.py tests/test_phase15_1_course_replay_web_api.py tests/test_phase15_2_course_replay_frontend_contract.py tests/test_phase15_3_public_showcase.py tests/test_phase16_0_styled_expression_corpus.py tests/test_phase17_0_real_visual_assets.py tests/test_phase18_0_clean_concept_cards.py tests/test_phase18_1_real_photo_generalization_probe.py -q
```

Result: `68 passed in 359.66s`.

Compile check:

```powershell
python -m compileall runtime apv3test scripts tests -q
```

Result: PASS.

Full regression:

```powershell
python -m pytest -q
```

Result: `517 passed in 545.80s`.

## Boundary

Phase 18.1 proves an auditable clean-card-to-real-photo replay path in the course replay workbench. It does not prove visual generalization, live camera perception, large-scale object recognition, arbitrary real-scene visual understanding, or complete open dialogue.

## Next

The next stable step is Phase 18.2: implement a visual-only probe gate. The student-side packet must not contain `neutral_label`, `entry_id`, target class, or intended-use shortcut evidence. Held-out real photos must beat contrast only through AP-native visual features or percept prototypes, with an external evaluator keeping the answer outside the AP packet.
