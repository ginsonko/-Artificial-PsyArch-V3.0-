# Phase 20.4 Open Dialogue Workbench Repair Final Report

## Result

Phase 20.4 repairs the user-facing local dialogue workbench around the Phase 20 AP-native cooccurrence teaching runtime.

## What Changed

1. The main composer now sends normal text and image/text turns through the Phase 20 endpoint instead of mixing the old `/api/message` path with Phase 20 teaching.
2. Current-session user text is shown in the browser transcript, while durable SQLite state still stores ordinary user input only as hash/length.
3. Teaching no longer replaces the conversation with `teaching trace`; it appends a readable system bubble: `纠正回答 "..." 已学习`.
4. Each Phase 20 turn returns a workbench tick trace with input ingress, visual focus, dialogue runtime, cooccurrence recall, style assembly, commit, and optional idle ticks.
5. The workbench supports image/audio browse, local media cache upload, thumbnail/audio preview, and media rendering in chat bubbles.
6. Local memory and imported package views now resolve ids into readable phrase/cooccurrence content.

## Boundaries

- Teaching still uses `ExpressionPhraseMemory` and `CooccurrenceAssociationStore`; no independent image label table or answer table was added.
- The tick trace is a workbench projection over Phase 20 runtime events, not a claim that a deeper open-ended multi-tick deliberation engine is complete.
- Audio can be uploaded and played in the workbench, but Phase 20.4 does not claim audio recognition.

## Artifacts

- Design: `docs/Design_APV3.0_Phase20_4_OpenDialogueWorkbenchRepair_v1_20260620.md`
- Tests: `tests/test_phase20_4_workbench_repair.py`
- Web files: `apv3test/web/static/index.html`, `apv3test/web/static/app.js`, `apv3test/web/static/styles.css`
- Report page: `reports/APV3_Phase20_4_OpenDialogueWorkbenchRepair_Showcase_20260620.html`

## Validation

PASS.

- Phase 20.4 targeted tests: `6 passed`.
- Adjacent Phase 20/21 workbench tests: `32 passed`.
- Full regression: `609 passed`.
- Phase 20.4 red line gate: PASS.
- Python compile check: PASS for `apv3test/web_chat.py`, `apv3test/runtime/phase20_open_dialogue.py`, and `apv3test/runtime/phase20_memory_packages.py`.
- JavaScript syntax check: PASS for `apv3test/web/static/app.js`.
- Browser smoke test: PASS at `http://127.0.0.1:8774/`.
  - Current-session raw text is visible in the transcript.
  - Teaching appends `纠正回答 "..." 已学习` and does not replace the chat turn.
  - Teaching `你好 -> 你好。` does not contaminate `你是谁?`.
  - Re-entering `你好` recalls the taught response.
  - Tick replay controls advance the workbench trace.
  - Memory view shows readable phrase/cooccurrence content and package controls.
