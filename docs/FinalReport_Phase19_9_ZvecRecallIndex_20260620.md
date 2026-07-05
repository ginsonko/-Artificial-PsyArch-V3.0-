# APV3 Phase 19.9 Final Report: Zvec Recall Index

## Design

Phase 19.9 adds a rebuildable Layer-1 vector recall index. The authoritative source remains `Layer1PerceptVectorStore`: JSON records, `.npy` full vectors, packet identity, epistemic source, substrate, receptor version, and audit metadata. Zvec is only a derived search backend.

The strict contract is:

- Zvec may return only vector UUIDs and similarity scores.
- Zvec must not return labels, source URLs, user text, or concept decisions.
- `c_recall` filters by `epistemic_source`, `substrate`, and `receptor_version`.
- If Zvec import or query fails, brute-force recall remains available.
- Deleting the Zvec index must be recoverable by rebuilding from truth records.

## Review

The implementation follows the Phase 21 and Phase 19.9 design notes:

- `runtime/cognitive/percept_vector/recall_index.py` owns Zvec access.
- `visual_recognize_v1_7` and `enumerate_objects_in_image` do not call Zvec directly.
- `RecallHit` metadata states `label_returned=False`.
- The index is a cache, not a classifier and not a source of truth.

## Landing

New files:

- `runtime/cognitive/percept_vector/recall_index.py`
- `tests/test_phase19_9_zvec_recall_index.py`
- `scripts/reports/render_phase19_9_recall_showcase.py`
- `reports/APV3_Phase19_9_ZvecRecallIndex_Showcase_20260620.html`

Changed files:

- `config/apv3_constants.yaml`: added `phase19_9.recall`.
- `scripts/red_line_check_v14.py`: added Phase 19.9 deliverables.

## Validation

Commands run:

```text
python -m pytest tests/test_phase19_9_zvec_recall_index.py -q
python scripts/red_line_check_v14.py --phase 19.9
python -m pytest tests/test_phase19_0b0_vector_schema.py tests/test_phase19_0b1_vector_population.py tests/test_phase21_object_centric_looking.py tests/test_phase19_9_zvec_recall_index.py -q
python -X utf8 -m pytest -q
```

Observed results:

- Phase 19.9 targeted: 6 passed.
- Phase 19.9 deliverable/redline gate: PASS.
- Adjacent Phase 19/21 regression: 26 passed.
- Full regression: 584 passed.

Gates:

- rebuildable index returns the same filtered topK as brute force on the fixture set;
- source/substrate/receptor filters prevent cross-path recall;
- hits do not return labels or private metadata;
- deleting and rebuilding the derived index preserves results;
- recognizers do not call Zvec directly;
- `scripts/red_line_check_v14.py --phase 19.9` passes.

## Boundary

Phase 19.9 does not improve recognition quality by itself. It does not prove real-photo generalization, object recognition, or open dialogue. It only proves that AP's vector memory has a rebuildable, source-disciplined recall acceleration layer.

## Next

The next phase can connect Phase 21 ObjectFiles to the Phase 20 open Chinese dialogue substrate and user correction loop.
