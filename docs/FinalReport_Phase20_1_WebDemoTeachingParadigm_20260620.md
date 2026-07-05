# APV3 Phase 20.1 Final Report: Web Demo Polish + Context-Bound Teaching Paradigm

## Summary

Phase 20.1 upgrades the Phase 20.0 open dialogue substrate with a shareable web-demo teaching loop.

Implemented:

- Natural display text now uses styled corpus `response_text`, so token pairs such as `["嗯", "在"]` no longer render as `嗯在`.
- Every Phase20 turn emits a structural `context_signature`.
- `/api/phase20/teach` stores a teacher-authored response candidate for the latest context.
- Teaching rewards the taught response and records a light penalty against the previous reply hash.
- Taught responses compete only inside the matching context signature.
- The web panel now shows context, ObjectFiles, styled source, feedback trace, and teaching trace.
- The showcase page demonstrates greeting and image-question teaching without cross-context contamination.

## Design / Review

The reviewed risk was context confusion:

- `你好` should not learn the image-question response.
- `这是什么` with image should not recall a pure greeting.
- Teaching text must not be treated as the latest user query.
- Explicitly taught reply text may be persisted as teacher content, but ordinary user text remains hidden.

The accepted design uses a canonical JSON context signature:

- user text hash
- image presence
- situation
- object count bucket
- top object UUID
- top decision tier
- styled paradigm id

This is not a keyword route and does not read filenames or image paths.

## Landing

Touched runtime/API/UI:

- `apv3test/runtime/phase20_open_dialogue.py`
- `apv3test/web_chat.py`
- `apv3test/web/static/index.html`
- `apv3test/web/static/app.js`
- `apv3test/web/static/styles.css`

New validation/report artifacts:

- `tests/test_phase20_1_teaching_paradigm.py`
- `scripts/reports/render_phase20_1_showcase.py`
- `reports/APV3_Phase20_1_WebDemoTeachingParadigm_Showcase_20260620.html`

## Validation

Targeted behavior test:

```text
python -m pytest tests\test_phase20_1_teaching_paradigm.py -k "not redline" -q
5 passed, 1 deselected
```

Targeted deliverable test:

```text
python -m pytest tests\test_phase20_1_teaching_paradigm.py -q
6 passed
```

Adjacent regression:

```text
python -m pytest tests\test_phase20_open_dialogue_foundation.py tests\test_phase20_1_teaching_paradigm.py tests\test_phase21_object_centric_looking.py -q
21 passed
```

Red line:

```text
python scripts\red_line_check_v14.py --phase 20.1
OK: Phase 20.1 deliverables present
OK: All red line checks pass on runtime/cognitive
```

Full regression:

```text
python -X utf8 -m pytest -q
598 passed
```

## Boundary

Phase 20.1 proves a context-bound teaching response substrate for the web demo. It still does not prove full Chinese NLU, robust real-photo recognition, visual-confidence learning after correction, production desktop-pet UI, or embodied intelligence.
