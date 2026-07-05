# APV3 Phase 21 v1b Final Report: Truly Local Object Channels

## Design

Phase 21 v1b closes the audit gap found after Phase 21.0: the previous object-centric test only proved that at least one of V7/V10/V11/V12 changed across candidate regions. It did not prove that V10, V11, and V12 each changed under local object crops.

The current runtime already routes `extract_visual_audit_path_v2_object_centric` through a cropped `local_rgb` and then runs the normal V0-V12 extractor on that crop. So the fix is a hard validation closure rather than a formula rewrite.

## Review

Adversarial review found one correction to the Claude v1b diagnosis:

- The code is not literally passing the full-image mask to V10/V11/V12 in the object-centric path.
- The real gap is weaker validation: the old test used `max(diffs)` across channels, allowing V7 or V12 alone to satisfy the gate.

## Landing

Changed files:

- `tests/test_phase21_object_centric_looking.py`
- `scripts/red_line_check_v14.py`

Existing design errata:

- `docs/Errata_Phase21_v1b_TrulyLocalMasksForV10V11V12_20260620.md`

## Validation

The new test builds a three-region synthetic probe and extracts three local candidate crops from the same parent image. It verifies:

- all traces share one parent `source_image_hash`;
- each trace has a different `local_source_image_hash`;
- V10, V11, and V12 each exceed the configured local-difference floor under pairwise mean absolute distance;
- V7 exceeds the same floor under L1 distance, because its sparse normalized codebook makes mean absolute distance artificially small.

Command:

```text
python -m pytest tests/test_phase21_object_centric_looking.py -q
python scripts/red_line_check_v14.py --phase 21.v1b
python -m pytest tests/test_phase19_9_zvec_recall_index.py tests/test_phase20_open_dialogue_foundation.py tests/test_phase21_object_centric_looking.py -q
python -X utf8 -m pytest -q
```

Observed:

- Phase 21 targeted after v1b: 9 passed.
- Phase 21.v1b redline: PASS.
- Adjacent Phase 19.9/20/21 regression: 21 passed.
- Full regression: 592 passed.

## Boundary

Phase 21 v1b does not claim better real-photo top-1 accuracy. It only proves that object-centric visual extraction is locally re-computed and that the previously weak channel-locality gate is closed.
