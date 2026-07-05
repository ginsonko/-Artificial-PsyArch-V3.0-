# APV3.0 Phase 19.0 Final Report — Visual Receptor Sketch

Date: 2026-06-19
Status: PASS
Scope: Phase 19.0 only
Design basis: `Design_APV3.0_Phase19_0_VisualSensorEnrichmentAndReconstructionAudit_v1_20260619.md` + `Errata_Phase19_v1a_AnthropomorphicAndEngineeringClosure_20260619.md` + `Errata_Phase19_v1b_ImplementationSensitiveClosure_20260619.md`

## Design

Phase 19.0 repairs the visual foundation exposed by the Phase 18.1 audit correction. The goal is not to prove object recognition. The goal is to give AP a richer, source-separated visual sensory trace:

- V0 foveated retinal pyramid plus V1..V9 channels, with closed `feature_vector_dim = 7807`.
- `receptor_fast_path` for per-tick prepared frames, bounded by p95 < 5 ms.
- `reconstruction_audit_path` for full V0..V9 extraction and renderable audit traces.
- `R_sketch` / `R_proto` split: `sensory_sketch` means input-derived perceptual sketch; `prototype_imagination` means imagined/prototype sketch.
- Mandatory metadata: `render_mode`, `input_trace_hash`, `prototype_trace_hash`, `evaluator_label_accessed`, `epistemic_source`, `source_confidence`, `confidence_score`, `decision_tier`, `confidence_decomposition`.

## Review

Claude v1b was treated as an engineering contract, not a prophecy. The pre-landing review found no architecture-level blocker, but kept these boundaries:

- Phase 19.0 can complete visual dimensions, fast/audit split, source-separated rendering, cooccurrence source lock, alpha startup assertion, and p95 fast-path gate.
- Phase 19.0 does not complete `nu_object/nu_context`, contribution-based feedback, stratified LOO, or visual-only real-photo generalization. Those are Phase 19.2 / 19.3 / 19.5.
- AP is anthropomorphic, so plausible perceptual mistakes remain allowed. The red line is source confusion or non-human artifacts, not ordinary uncertainty.

## Landing

Implemented files:

- `apv3test/runtime/visual_receptor.py`
- `tests/test_phase19_0_visual_receptor.py`
- `scripts/reports/render_phase19_0_showcase.py`
- `reports/APV3_Phase19_0_VisualReceptorSketch_Showcase_20260619.html`
- `config/apv3_constants.yaml`
- `scripts/red_line_check_v14.py`

Key implementation details:

- Audit trace channel lengths are exactly `V0=4544, V1=288, V2=1536, V3=1110, V4=296, V5=16, V6=5, V7=4, V8=5, V9=3`.
- Fast path operates on a prepared 32x32 visual frame. File IO and offline image decoding are not counted as cognitive tick time.
- Rendering writes PNG plus JSON metadata. SA ids use hashes and do not include labels or filenames.
- `CooccurrenceMatrix.update()` rejects any write whose `source_tag` is not `training_sdpl_only`.
- `assert_retrieval_alpha_weights()` enforces `alpha_part + alpha_shape + alpha_cooccur <= 1` and `alpha_conflict in [0, 0.5]`.

## Validation

Targeted tests:

```powershell
python -m pytest tests/test_phase19_0_visual_receptor.py -q
```

Result: `8 passed in 3.11s`.

Red line:

```powershell
python scripts\red_line_check_v14.py --phase 19.0
```

Result: `OK: Phase 19.0 deliverables present`; `OK: All red line checks pass on runtime/cognitive`.

Governance:

```powershell
python scripts\check_constant_governance.py
```

Result: `OK: Governance check passed (346 numeric constants)`. The script reported 91 existing warnings for experimental constants pending longer rationale; no blocker.

Nearby regression:

```powershell
python -m pytest tests/test_phase18_0_clean_concept_cards.py tests/test_phase18_1_real_photo_generalization_probe.py tests/test_phase19_0_visual_receptor.py -q
```

Result: `22 passed in 10.34s`.

Full regression:

```powershell
python -m pytest -q
```

Result: `525 passed in 440.78s (0:07:20)`.

Compile check:

```powershell
python -m compileall apv3test runtime scripts tests
```

Result: PASS.

## Boundary

Phase 19.0 proves only that AP now has a richer visual receptor substrate and a source-separated internal sketch/prototype rendering path.

It does not prove:

- AP can identify arbitrary real photos.
- Clean concept cards generalize to real photographs.
- Human-like confidence formula is active.
- Visual-only LOO evaluation has passed.
- Audio receptor enrichment is complete.
- Source-aware feedback is active in runtime.

## Next

Proceed in the locked order:

1. Phase 19.2 — human-like confidence formula with `raw_confidence`, `decision_tier`, `nu_object`, and `nu_context`.
2. Phase 19.3a — stratified LOO real-photo visual-only probe.
3. Phase 19.3b — clean-card to real-photo transfer, with failure treated as a developmental limitation rather than automatic design failure.
4. Phase 19.1 / 19.4 / 19.5 — audio receptor symmetry and source-aware feedback.
