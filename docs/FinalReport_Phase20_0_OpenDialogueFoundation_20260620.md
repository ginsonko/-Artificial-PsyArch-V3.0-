# APV3 Phase 20.0 Final Report: Open Chinese Dialogue Foundation

## Design

Phase 20.0 connects the current user-facing dialogue shell to multimodal perception:

- text: existing `APV3MinimalistChatSession` and `MinimalistDialogueFlowRuntime`;
- image: Phase 21 `enumerate_objects_in_image`;
- style: Phase 16 styled corpus YAML packs;
- feedback: Phase 19.5 natural correction credit trace;
- agent/web substrate: Python wrapper plus `/api/phase20/turn` and `/api/phase20/agent`.

The design is governed by `Errata_Phase20_v1a_SourcePrivacyFeedbackGate_20260620.md`.

## Review

Codex adversarial review found and closed three risks before landing:

- visual labels must not be appended to user text;
- raw user images must not be persisted;
- feedback trace must not be overclaimed as immediate recognition improvement.

## Landing

New files:

- `apv3test/runtime/phase20_open_dialogue.py`
- `tests/test_phase20_open_dialogue_foundation.py`
- `scripts/reports/render_phase20_showcase.py`
- `docs/Errata_Phase20_v1a_SourcePrivacyFeedbackGate_20260620.md`
- `reports/APV3_Phase20_OpenDialogueFoundation_Showcase_20260620.html`

Changed files:

- `apv3test/web_chat.py`
- `apv3test/web/static/index.html`
- `apv3test/web/static/app.js`
- `apv3test/web/static/styles.css`
- `scripts/red_line_check_v14.py`

## Validation

Targeted gates cover:

- text and image source boundaries;
- image privacy: state stores hash, not raw image or path;
- styled response is loaded from YAML;
- feedback attaches only to the previous turn and emits nonzero credit;
- agent wrapper and web API schema;
- Phase 20 deliverable redline.

Commands:

```text
python -m pytest tests/test_phase20_open_dialogue_foundation.py -q
python scripts/red_line_check_v14.py --phase 20.0
python -m pytest tests/test_phase19_9_zvec_recall_index.py tests/test_phase20_open_dialogue_foundation.py tests/test_phase21_object_centric_looking.py -q
python -X utf8 -m pytest -q
```

Observed:

- Phase 20 targeted: 6 passed.
- Phase 20 redline: PASS.
- Adjacent Phase 19.9/20/21 regression: 21 passed.
- Full regression: 592 passed.
- Local web API smoke: `POST /api/phase20/turn` returned 200 with one object and `image_sha16` only.

## Boundary

Phase 20.0 proves the open-dialogue substrate is connected. It does not prove full Chinese NLU, production web upload UX, robust real-photo recognition, immediate feedback-driven visual confidence improvement, desktop-pet polish, or embodied intelligence.

The correct claim is: APV3 can now process one local turn containing user Chinese text, optional local image path, optional feedback, Phase 21 object enumeration, Phase 16 styled response, and Phase 19.5 correction trace under one auditable session.
