# APV3 Phase 19.8a Final Report: Real Teaching Library Pipeline

## Design

Phase 19.8a responds to the Phase 19.7h finding: local channels V7/V10/V11 can be diagnostic, but clean concept cards are too far from real photos. The AP-native repair is not to add a hidden classifier. It is to create a curated real-photo teaching library that can be processed by the same receptor/vector path.

This phase implements the data pipeline only:

- candidate download with explicit license sidecars;
- human curation page;
- curated-only ingest;
- deterministic train/held-out split;
- Layer-1/2/3 vector population for train images.

## Review

Accepted from Claude:

- The cross-domain gap between clean cards and real photos is a serious bottleneck.
- A small curated set of real photos is a plausible AP-native next step.
- Human screening is appropriate because public image search returns noisy and ambiguous material.

Corrected before landing:

- Pexels/Pixabay/Unsplash are not treated as CC0-equivalent in this phase.
- Phase 19.8a only allows sources that can provide explicit CC0 / CC-BY / PDM style license metadata.
- The phase does not claim the expected `10/12` recognition target before the user actually curates images.
- Candidate images are not considered training evidence until human curation keeps them.

## Landing

Implemented:

- `scripts/curriculum/download_real_teaching_photos.py`
- `scripts/curriculum/render_real_curation_page.py`
- `scripts/curriculum/ingest_real_teaching_photos.py`
- `scripts/reports/render_phase19_8_showcase.py`
- `tests/test_phase19_8_real_teaching_library.py`
- Phase deliverable gate `19.8a`.

The downloader supports:

- Wikimedia Commons;
- Openverse;
- local fixture mode for deterministic tests.

The curation page exports `apv3_real_teaching_curation/v1`. The ingest script only reads records marked `keep`.

## Validation

Commands run:

```text
python -m pytest tests/test_phase19_8_real_teaching_library.py::test_phase19_8_fixture_download_sidecars_and_curation_page tests/test_phase19_8_real_teaching_library.py::test_phase19_8_ingest_keeps_held_out_out_of_training_vectors -q
python scripts/reports/render_phase19_8_showcase.py
```

Results:

- Fixture curation and ingest tests: `2 passed`.
- Showcase generated: `reports/APV3_Phase19_8_RealTeachingLibrary_Showcase_20260619.html`.

## Boundary

Phase 19.8a proves the pipeline can be executed and audited. It does not prove:

- enough real photos have been downloaded;
- the user has curated the images;
- real-photo recognition improved;
- soft/firm confidence targets are met.

Those belong to Phase 19.8b after curation.

## Next

1. Run the downloader for the approved concept list.
2. Open `reports/APV3_Phase19_8_RealTeachingCuration.html`.
3. The user keeps/deletes candidates and saves `curation.json`.
4. Run ingest.
5. Re-run the real-photo generalization probe and only then evaluate the `10/12` and `6/12 soft/firm` targets.
