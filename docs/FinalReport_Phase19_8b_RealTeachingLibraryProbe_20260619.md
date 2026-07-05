# APV3 Phase 19.8b Final Report: Curated Real Teaching Probe

## Design

Phase 19.8b tests Claude's data-first hypothesis: if clean cards are too far from real photos, a human-curated real-photo teaching library should improve real-photo recognition through the existing AP-native receptor/vector path.

## Landing

Inputs:

- Downloaded candidate images from Openverse with explicit sidecar metadata.
- Wikimedia Commons bulk use was stopped after HTTP 429 robot-policy response.
- User curated `curation.json` manually.
- Ingest copied kept candidates into `config/curriculum/assets/visual/real_teaching`.
- Train/held-out split used deterministic sha256 ordering.
- Train split populated Layer-1/2/3 through `populate_visual_vectors`.

Curated ingest result:

- Curated accepted records: 87
- Train: 59
- Held-out: 28
- Formal concepts meeting the minimum 8 kept images: apple, banana, bird, cake, dog, orange, strawberry
- Skipped below minimum: book, bread, cat, chair, computer, cup, egg, fish, grape, phone

## Validation

Command:

```text
python scripts/curriculum/ingest_real_teaching_photos.py --candidate-root config/curriculum/assets/visual/real_teaching_candidates --curation-json config/curriculum/assets/visual/real_teaching_candidates/curation.json --curated-dir config/curriculum/assets/visual/real_teaching --vector-root data/phase19_8_real_teaching_vectors --manifest config/curriculum/assets/visual/real_teaching_manifest.json
python scripts/reports/render_phase19_generalization_effect_probe.py
```

Real-photo probe result on the original 12 user images:

- Clean cards only: 7/12, all no_call
- Old diagnostic library: 7/12, all no_call
- Human-curated real teaching library: 6/12, all no_call

This fails the Phase 19.8b target:

- Expected top-1 target: at least 10/12
- Expected soft/firm target: at least 6/12
- Actual curated result: 6/12 and 0/12 soft/firm

## Diagnosis

The data-first hypothesis was only partially right. Real photos are needed, but this downloaded/curated batch did not solve the distribution problem.

Observed issues:

- Public image candidates were noisy; many concepts had too few usable images.
- Several concepts had only 1-2 usable images after curation.
- Fruit train data was imbalanced: apple had many more train examples than banana/orange.
- For a banana test image, nearest-negative evidence from orange/apple beat banana across V7/V10/V11/V12, so the AP correctly stayed in no_call rather than forcing a confident wrong answer.

The current failure is therefore not a hidden classifier bug. It is a data/course quality and representation alignment failure.

## Boundary

Phase 19.8b proves:

- candidate download, curation, curated-only ingest, deterministic split, and vector population work;
- low-quality public image pools do not automatically fix real-photo generalization;
- the confidence gate remains uncertainty-honest.

Phase 19.8b does not prove:

- robust real-photo object recognition;
- that the 20-concept teaching library is complete;
- that public web image scraping is enough for AP-native visual teaching;
- that Phase 19's visual representation is finished.

## Next

The next step should be smaller and stricter:

1. Build a fruit-only, high-quality teaching set: apple / banana / orange only.
2. Require balanced counts and visual diversity: 10-12 usable images per fruit after curation.
3. Prefer user-supplied or manually selected clean real photos over broad web search.
4. Add a pre-ingest diagnostic page that shows V7/V10/V11 nearest-neighbor clusters before teaching.
5. Only rerun 20 concepts after the fruit-only gate passes.

The current 19.8b result is useful, but it is not a pass for the final expected real-photo generalization target.
