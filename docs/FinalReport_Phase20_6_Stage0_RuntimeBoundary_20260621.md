# APV3 Phase 20.6 Stage0 Runtime Boundary Final Report

Date: 2026-06-21

## Scope

Phase 20.6 Stage0 is the redline cleanup, runtime-boundary landing, and first
shareable true-runtime workbench. It exists to prevent the workbench from
presenting projected or staged front-end stories as AP runtime.

This report covers only the main Phase20 dialogue path.

## Implemented

1. Added `apv3test/runtime/phase20_6_runtime.py`.
2. Routed `Phase20MultimodalSession.turn()` through `run_phase20_6_runtime()`
   before the old Phase20.5 unreachable code.
3. Removed the Phase20 dialogue dependency on whole-image
   `enumerate_objects_in_image`; Phase20 now uses class-agnostic
   `extract_candidate_targets()` and exposes only `visual_candidate` objects.
4. Removed the old monkeypatch-style runtime replacement path.
5. Moved visible reply commitment behind `DraftGrid`.
6. Tightened Stage0 into a per-tick candidate loop:
   - each tick rebuilds next-token candidates from the current draft prefix;
   - each tick proposes AP actions (`move_focus`, `write_cell`, `commit_reply`,
     `idle_observe`, or system boundary);
   - `commit_reply` reads `DraftGrid.visible_text()`;
   - write actions do not carry a full `candidate_text` / `reply_text` payload.
7. Added per-tick `recall_candidates`, `action_competition`,
   `draft_grid_snapshot`, and `thought_cloud_items` fields so the future UI can
   mirror runtime data instead of inventing panel state.
8. Added `apv3test/runtime/phase20_6_memory.py`:
   - Fast memory stores action-chain tendencies only, not surface replies;
   - Slow memory stores source-candidate evidence only, not labels or answers;
   - later turns can read Fast/Slow hints back into action competition/state
     pool without creating a separate answer route.
9. Added real SQLite projection tables:
   - `phase20_6_fast_action_chains`;
   - `phase20_6_slow_memory`.
10. Added active stop:
   - `commit_reply` and `stop_generating` are separate RuntimeTickEvent actions;
   - active stop never commits an empty reply.
11. Added cross-turn unresolved carry:
   - system-boundary unfinished draft/context is saved as unresolved carry;
   - next turn re-enters it as `unresolved_carry` state-pool evidence.
12. Added affect co-recall substrate:
   - text affect receptor emits uncertain `affect_evidence` SA;
   - affect can modulate styled expression selection;
   - affect evidence has `direct_reply_authority = false`.
13. Updated the web/API payload so `workbench_tick_trace` exposes true
   `recall_candidates`, `action_competition`, `draft_grid_snapshot`, and
   `thought_cloud_items` from RuntimeTickEvent.
14. Updated the active web replay renderer to display those true runtime
   fields in the tick detail panel.
15. Added `tests/test_phase20_6_stage0_runtime_boundary.py`.
16. Added `--phase 20.6-stage0` deliverable/redline support to
   `scripts/red_line_check_v14.py`.
17. Removed the unreachable Phase20.5 projected tick block from
    `apv3test/runtime/phase20_open_dialogue.py`.
18. Removed the old staged workbench trace block from `apv3test/web_chat.py`.
19. Added a dedicated shareable workbench page:
    - `apv3test/web/static/phase20_6_workbench.html`;
    - `apv3test/web/static/phase20_6_workbench.css`;
    - `apv3test/web/static/phase20_6_workbench.js`.
20. The new page bypasses the legacy `app.js` stack and renders only fields
    returned by `/api/phase20/turn`:
    - `workbench_tick_trace`;
    - `recall_candidates`;
    - `action_competition`;
    - `draft_grid_snapshot`;
    - `thought_cloud_items`;
    - `state_pool_top12`;
    - `inner_picture_state`;
    - `phase20_6_memory`.
21. Teaching UI now appends a normal chat-row note
    `纠正回答「...」 已学习` instead of replacing the chat with a trace panel.
22. Added `tests/test_phase20_6_true_runtime_workbench_page.py`.
23. Added AP-native `sensor_actuator_context` into the Phase20.6 runtime:
    - teacher-guided focus boxes enter as saliency evidence only;
    - canvas images enter as visual sensor input;
    - recordings enter as `audio_audit_only` sensor evidence;
    - reply TTS enters as a local actuator request.
24. Extended each RuntimeTickEvent with:
    - `sensor_actuator_context`;
    - `inner_audio_state`;
    - `reply_tts_request`.
25. Extended the shareable workbench with:
    - teacher focus-box controls;
    - HTML canvas input;
    - MediaRecorder upload path for audio;
    - local browser TTS playback triggered only by a `reply_tts_audio` action;
    - searchable local memory view;
    - memory package export/import/uninstall/delete controls.
26. Added tests proving these controls do not create semantic shortcuts:
    - teacher focus does not bind labels;
    - audio recording does not produce recognition labels;
    - TTS is local actuator output, not inner voice;
    - the page contains no OCR route.

## Redlines Enforced

The Stage0 scan checks the main runtime/web paths for:

- no `enumerate_objects_in_image` in Phase20 dialogue;
- no direct `reply_text = taught.response_text`;
- no old `_phase20_5a2` / `_build_phase20_5a2_workbench_ticks`;
- no `Phase20MultimodalSession.turn =` monkeypatch;
- no visible "teaching hit" wording;
- no `teaching_hit`, `taught_answer`, `direct_label_reply`, or `image_label_map`;
- no `_select_visible_token_source`, `writable_count`, or `candidate_text`
  reply schedule artifacts.
- no `fast_direct_reply` or `answer_text` shortcut in the Phase20.6 main path.
- no `workbench_projection_over_phase20_runtime_events` legacy UI boundary.
- no old visible staged tick titles such as `输入进入`, `视觉聚焦`,
  `文本运行时`, `风格组装`, or `提交回复` in the Phase20.6 runtime/web paths.
- no OCR imports (`pytesseract`, `easyocr`, `paddleocr`).
- no cloud TTS route (`OpenAI TTS`, `Google TTS`, `Edge TTS`).
- no audio recognition label route in Phase20.6.

## Validation

Commands run:

```powershell
python -m py_compile .\apv3test\runtime\phase20_open_dialogue.py .\apv3test\runtime\phase20_6_runtime.py .\apv3test\web_chat.py
```

Result: PASS

```powershell
node --check .\apv3test\web\static\app.js
```

Result: PASS

```powershell
python -m py_compile .\apv3test\runtime\phase20_6_runtime.py .\tests\test_phase20_6_stage0_runtime_boundary.py
```

Result: PASS

```powershell
python -m pytest .\tests\test_phase20_6_stage0_runtime_boundary.py -q
```

Result: `10 passed`

```powershell
python -m pytest .\tests\test_phase20_5a_runtime_workbench.py .\tests\test_phase20_6_stage0_runtime_boundary.py -q
```

Result: `17 passed`

```powershell
python -m pytest .\tests\test_phase20_6_true_runtime_workbench_page.py .\tests\test_phase20_6_stage0_runtime_boundary.py -q
```

Result: `17 passed`

```powershell
python -m pytest .\tests\test_phase20_open_dialogue_foundation.py .\tests\test_phase20_1_teaching_paradigm.py .\tests\test_phase20_2_3_cooccurrence_memory.py .\tests\test_phase20_4_workbench_repair.py .\tests\test_phase20_5a_runtime_workbench.py .\tests\test_phase20_6_stage0_runtime_boundary.py .\tests\test_phase20_6_true_runtime_workbench_page.py -q
```

Result: `47 passed`

```powershell
python -m pytest .\tests\test_phase21_object_centric_looking.py .\tests\test_phase19_9_zvec_recall_index.py -q
```

Result: `15 passed`

```powershell
python scripts\red_line_check_v14.py --phase 20.0
python scripts\red_line_check_v14.py --phase 20.1
python scripts\red_line_check_v14.py --phase 20.4
python scripts\red_line_check_v14.py --phase 20.6-stage0
```

Result: all four phase gates reported deliverables present and redlines pass.

Browser smoke:

```text
http://127.0.0.1:8786/phase20_6_workbench.html
```

Result: PASS

- The page opened with title `APV3 Phase20.6 真实运行工作台`.
- Visible page text did not contain the old projected flow titles.
- Sending `你好，你现在在想什么？` showed the original user text in the chat
  bubble and produced a RuntimeTickEvent-backed AP bubble.
- The tick replay showed `RecallCandidate`, `ActionCompetition`, `DraftGrid`,
  `state_pool_top12`, and `thought_cloud_items`.
- Switching tick changed the DraftGrid from `嗯` to `嗯。`, proving the panel
  was following different tick events instead of a fixed final reply.
- Teaching `我正在整理自己的草稿。` appended
  `纠正回答「我正在整理自己的草稿。」 已学习` without replacing the chat, and
  the page refreshed Fast/Slow memory counts.
- The enhanced workbench opened with teacher-focus, canvas, recording, TTS,
  and memory package controls visible.
- A turn with teacher focus box `(x=20,y=30,w=40,h=20)` and an image produced a
  `move_focus` action with `teacher_guided_focus / no_label`, and the state
  pool included `teacher_guided_focus`.
- The same turn exposed `reply_tts_actuator_intent` and a RuntimeTickEvent TTS
  request; local speech playback is triggered only from that event.
- The local memory panel rendered readable Chinese entries such as style
  snippets, teacher snippets, user utterances, and cooccurrence edges.

Full historical test suite note: a full `python -m pytest .\tests -q` run was
attempted once and timed out at 10 minutes without failure output. Per the
current implementation policy, Phase 20.6 validation is scoped to the latest
runtime-boundary and adjacent substrate tests above rather than obsolete older
tests.

## Boundaries

Stage0 does not claim that Phase 20.6 is complete.

Still not claimed:

- mature Fast/Slow arbitration quality beyond the current source-tagged hints;
- mature humanlike active-stop policy beyond the current separate
  `stop_generating` action event;
- complete affect/empathy co-recall loop;
- full theory-of-mind / perspective-taking substrate;
- full state-pool evolution over AP-native SA objects;
- true Phase19 R_sketch image reconstruction;
- Phase19.1 auditory inner-voice substrate;
- full production workbench package management UI.
- recording is currently `audio_audit_only`; it is not audio recognition.
- browser TTS is local reply playback; it is not `inner_voice_sketch`.
- canvas input is visual sensor input; it is not OCR or text recognition.
- teacher focus boxes are saliency hints; they are not label authority.
- full production workbench package management polish.

The next implementation stage must keep the same boundary: every new panel or
tool must be a view over AP-native runtime state or an AP-native sensor/actuator
input, not an independent semantic answer route.
