# APV3 Phase 20.2/20.3 Final Report: Co-occurrence Teaching + Memory Packages

## Summary

Phase 20.2/20.3 corrects the Phase 20.1 teaching implementation so teaching is no longer an independent response table.

Implemented:

- `teach_latest` now writes teacher phrases into `ExpressionPhraseMemory`.
- Current text context SA and visual object/concept SAs are connected to the phrase via `CooccurrenceAssociationStore`.
- Repeated or matching contexts recall the taught phrase through co-occurrence wave peaks.
- The old `phase20_teaching_paradigms` runtime table is no longer used.
- Styled YAML curriculum imports 1200 entries into AP expression memory and paradigm co-occurrence.
- Memory package manager supports list/search/export/import/dedup/uninstall/delete.
- Web API and UI expose imported package list, package content view, local memory view, selected-memory deletion, export, import, and package uninstall.

## Adversarial Review Result

Accepted correction:

- "Image annotation" must not be a separate label map.
- It is visual object SA and teacher text SA co-occurrence under a teacher-event source.
- Normal questions such as "这是什么" are query source and should not become labels by default.
- The teaching UI is allowed as a source marker, but the learning path must stay AP-native.

Additional user requirements absorbed:

- imported package list is visible in the UI
- package names are preserved
- package content can be viewed
- local complete memory can be searched and selected
- selected local memories can be deleted
- imported packages can be uninstalled precisely
- styled dialogue corpus is imported into AP memory, not just directly sampled from YAML

## Validation

Initial targeted checks:

```text
python -m pytest tests\test_phase20_2_3_cooccurrence_memory.py -k "not redline" -q
4 passed
```

Phase 20.1 compatibility under the new co-occurrence semantics:

```text
python -m pytest tests\test_phase20_1_teaching_paradigm.py -q
6 passed
```

Final aggregate validation is recorded in the chat handoff after the full test run.

Targeted deliverable:

```text
python -m pytest tests\test_phase20_2_3_cooccurrence_memory.py -q
5 passed
```

Red line:

```text
python scripts\red_line_check_v14.py --phase 20.2_20.3
OK: Phase 20.2_20.3 deliverables present
OK: All red line checks pass on runtime/cognitive
```

Adjacent regression:

```text
python -m pytest tests\test_phase20_open_dialogue_foundation.py tests\test_phase20_1_teaching_paradigm.py tests\test_phase20_2_3_cooccurrence_memory.py tests\test_phase21_object_centric_looking.py -q
26 passed
```

Full regression:

```text
python -X utf8 -m pytest -q
603 passed
```

## Boundary

This phase proves AP-native co-occurrence teaching and memory package governance. It does not prove full natural-language understanding, universal real-photo recognition, legal review for community packages, or mature public marketplace operations.
