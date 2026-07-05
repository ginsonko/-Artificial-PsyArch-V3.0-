# Phase 15.0 Final Report - Course Replay Runtime

Date: 2026-06-18

## Design

CourseReplayRuntime reads the Phase 14 asset manifest and neutral curriculum packages, then emits a six-tick trace for a selected demo course. The trace includes material refs, PERCEIVED source marker, SDPL packet keys, Q score, and AP output.

## Review

The runtime was checked against the main risk: fake scripted traces. The implementation builds packets with `LearningPacket`, `MarkerEvent`, `StateItem`, and `QTableWithBackoff`, and every asset ref is resolved from the manifest.

## Landing

Implemented `apv3test/runtime/course_replay.py` with five first demos:

- color_yellow
- shape_triangle
- noun_apple
- audio_soft_call
- feedback_correct

Also optimized `load_constant` with a read-only cache. This keeps YAML governance as the source of truth while removing repeated full-file reads during Q-table queries.

## Validation

Targeted test:

```powershell
python -m pytest tests/test_phase15_0_course_replay_runtime.py -q
```

Result in combined Phase 15 targeted run: PASS.

Core assertions:

- 5 demos are listed.
- Each demo emits 6 ticks.
- Asset refs all exist in the manifest.
- Held-out q score is above contrast q score.
- Course replay SQLite writes only to the explicit test DB.

## Boundary

This phase proves short replay trace generation over existing Phase 14 assets. It does not claim full curriculum training, complete vocabulary mastery, or real external dataset ingestion.

## Next

Expose the runtime through Web APIs and render it in the local workbench.
