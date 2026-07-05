# APV3 Phase 21.0 Final Report: Object-Centric Looking

## Design

Phase 21.0 closes the gap found after Phase 19.8b: the recognizer had foveated visual channels, but `visual_recognize_v1_7` still made one whole-image pass and `_diagnostic_fixation_log` only rendered audit prose. Phase 21.0 changes the task from "label the full image" to "find class-agnostic visual candidates, move focus, inspect each local object, and produce object files."

The implemented loop is:

1. Class-agnostic saliency candidates from color contrast, edge contrast, connected components, NMS, and IOR.
2. Candidate SA injection into `StatePool` with `family="visual_candidate"` and `channel_signature` containing `vision`.
3. Existing `propose_visual_focus_actions` chooses `saccade_to_visual`.
4. `extract_visual_audit_path_v2_object_centric` crops the candidate region and recomputes local V1-V12 channels, especially V7/V10/V11/V12.
5. The existing Phase 19 channel-wise diagnostic confidence path scores the local object view.

## Review

Claude v1a and Codex review issues were absorbed:

- candidate metadata is class-agnostic and does not carry label, concept, or filename semantics;
- V7/V10/V11/V12 are recomputed on local candidate crops rather than full-image masks;
- train and query both use object-centric extraction;
- success gates use multiple dimensions rather than a single 9/12 accuracy claim;
- object count is based on object files after NMS/IOR, not raw candidate count.

## Landing

New files:

- `runtime/cognitive/percept_vector/object_looking.py`
- `tests/test_phase21_object_centric_looking.py`
- `scripts/reports/render_phase21_object_looking_showcase.py`
- `reports/APV3_Phase21_ObjectCentricLooking_Showcase_20260619.html`

Changed files:

- `apv3test/runtime/visual_receptor.py`: added `extract_visual_audit_path_v2_object_centric`.
- `config/apv3_constants.yaml`: added `phase21.object_looking` constants.
- `scripts/red_line_check_v14.py`: added Phase 21.0 deliverables.

## Validation

Targeted tests:

```text
python -m pytest tests/test_phase21_object_centric_looking.py -q
```

Expected gates:

- candidate metadata has no label or filename oracle;
- local V7/V10/V11/V12 differ across candidate regions;
- generated multi-object probes enumerate at least two objects;
- object-centric margin beats whole-image margin on a generated probe;
- runtime source calls `propose_visual_focus_actions` and the object-centric receptor entry;
- showcase is public-readable and boundary-safe;
- `scripts/red_line_check_v14.py --phase 21.0` passes.

## Boundary

Phase 21.0 proves the object-centric looking path is connected on local generated fruit-card materials. It does not prove robust real-world photo recognition, ImageNet-scale recognition, Zvec acceleration, or the full open-dialogue substrate. Those remain future phases.

## Next

Recommended next order:

1. Phase 19.9: add Zvec as a rebuildable recall index, not a source of truth or classifier.
2. Phase 20: connect object files to the open Chinese dialogue substrate and user correction loop.
3. Later: use ImageNet only as non-redistributable internal pressure testing.
