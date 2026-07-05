# APV3 Phase 19.7h Final Report: Local Diagnostic Channels

## Design

Phase 19.7h reviews Claude's v1h errata: real natural fruit photos expose that global statistics can be anti-diagnostic. The intended repair is to keep global channels for audit/reconstruction, but shift recognition pressure toward local diagnostic evidence.

Implemented visual channels:

- V6 upgraded from 5 coarse shape scalars to 40 shape descriptors.
- V7 upgraded from 4 hue-like top parts to 64 local part codes plus quadrant distribution.
- V10 added per-part color/texture profile.
- V11 added part relational graph.
- V12 added color cluster spatial map.

## Adversarial Review

Accepted:

- The v1h diagnosis is directionally correct: global RGB/HSV/LBP/HOG style statistics are weak or anti-diagnostic on the user's natural fruit photos.
- Recognition should not rely on full-vector cosine or global histogram similarity.
- Sparse local features must not be averaged over inactive rows, because shared absence is not humanlike evidence.

Corrected:

- Do not permanently delete V1/V2/V3/V4/V8/V9. They remain in the sensory trace for reconstruction, audit, memory, and future tasks.
- Default Phase 19.7h recognition weight for those global channels is `0.0`, so they are audit-only in this fruit recognition stress path.
- Fast path cannot call full `solve_subject_mask()` every tick; it now uses a no-mean-threshold lightweight percentile mask, while audit path uses the full mask solver.

Rejected / not yet proven:

- The claim that V7+V10/V11/V12 will immediately produce 10/12 or high-confidence real-photo recognition is not supported by current implementation evidence.
- The claim that more data can never fix global channels is too strong. More data plus object-centric masks/local features can help; more data with only global statistics can reinforce the wrong bias.

## Landing

Files changed:

- `config/apv3_constants.yaml`
- `apv3test/runtime/visual_receptor.py`
- `runtime/cognitive/percept_vector/phase19_runtime.py`
- `scripts/reports/render_phase19_0_showcase.py`
- `scripts/reports/render_phase19_complete_showcase.py`
- `scripts/reports/render_phase19_generalization_effect_probe.py`
- `tests/test_phase19_0_visual_receptor.py`
- `tests/test_phase19_0a_foveated_visual_repair.py`
- `tests/test_phase19_7_mask_recovery.py`
- `tests/test_phase19_7h_local_diagnostic_channels.py`

## Validation

Targeted checks:

```text
python -m pytest tests/test_phase19_0_visual_receptor.py tests/test_phase19_0a_foveated_visual_repair.py tests/test_phase19_7_mask_recovery.py -q
python -m pytest tests/test_phase19_7_mask_recovery.py tests/test_phase19_0a_foveated_visual_repair.py -q
python scripts/reports/render_phase19_generalization_effect_probe.py
```

Observed results:

- Visual vector dimension is closed at `8654` for Phase 19.0 audit path.
- Foveated visual vector dimension is closed at `28686` for Phase 19.0a/19.7h path.
- Local channels are present: V10, V11, V12.
- Global channels are still computed but recognition weights are audit-only.
- Real-photo stress page regenerated.

Real-photo stress result after v1h:

- `clean_cards_only`: `7/12`, all `no_call`.
- `diagnostic_library`: `7/12`, all `no_call`.

The result does not reach the desired target. The system is more structurally honest, but not yet humanlike-confident.

## Boundary

Phase 19.7h proves:

- the visual receptor can carry local diagnostic channels without filename/label oracle;
- global anti-diagnostic channels can be demoted without deleting sensory evidence;
- sparse local similarity no longer rewards shared absence;
- current failure remains uncertainty-honest.

Phase 19.7h does not prove:

- robust real-photo object recognition;
- humanlike high confidence on unfamiliar fruit photos;
- sufficient object-centric active perception;
- mature part-code learning.

## Next

The next repair should move from handcrafted local statistics to active object-centric learning:

1. Multi-fixation scoring must actually merge features from multiple subject fixations, not only log fixations.
2. Part codes should be learned as true medoids from a stratified train set with held-out separation.
3. Subject segmentation should expose object masks and uncertain subregions to the attention loop.
4. Recognition should report "what local cue made me think apple/banana/orange" in the showcase.

Do not claim the desired real-photo generalization effect until the stress page shows both higher top-1 and non-trivial soft/firm decisions without filename leakage.
