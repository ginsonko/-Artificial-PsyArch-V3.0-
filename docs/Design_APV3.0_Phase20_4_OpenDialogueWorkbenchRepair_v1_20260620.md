# APV3.0 Phase 20.4 Open Dialogue Workbench Repair v1

## 0. Scope

Phase 20.4 repairs the local Web workbench around the already landed Phase 20.2/20.3 AP-native cooccurrence teaching path.

It does not add an independent answer table, image label table, regex route, keyword route, hidden classifier, or student-side LLM. Text teaching and image teaching still enter the same AP path:

```
current text / visual object SA
  -> same-tick teacher evidence
  -> ExpressionPhraseMemory
  -> CooccurrenceAssociationStore
  -> later recall by context / visual SA
```

The repair is mainly a workbench correctness and transparency phase: the page must show what the user actually did, what AP ran, what was taught, what was remembered, and which local memory package can be viewed or uninstalled.

## 1. Problems Found

1. The page exposed two conversation paths. `发送` used the legacy minimalist chat API, while `图文` used Phase 20. Teaching only affected Phase 20, so normal text could appear to ignore teaching.
2. The chat timeline replaced a normal turn with `teaching trace +1 / -0.12`, which made the user lose the conversational record.
3. Current-session user input was displayed as `原文未保存`, although the user needs to see what they just typed. The privacy rule should apply to durable storage, not the live browser transcript.
4. Tick replay only showed persisted low-level rows and had no play/pause/step controls or per-turn workbench sequence.
5. The media path field had no browse/preview affordance, and bubbles did not render image/audio attachments.
6. Memory rows were AP ids such as `style_paradigm::...`, not readable memory contents. Package listing did not make review/uninstall comfortable.

## 2. Design Decisions

### 2.1 Unified Phase20 Send Path

The workbench default send path is Phase 20:

- `发送文字`: `POST /api/phase20/turn` with text only.
- `发送图文`: `POST /api/phase20/turn` with text plus image path or uploaded local image.
- The old `/api/message` path remains as a compatibility endpoint but is no longer used by the main workbench composer.

### 2.2 Live Raw Text, Durable Hash

The browser keeps the current-session raw user text in local JS state and shows it in bubbles.

The backend still persists only hash/length for ordinary user text. The immediate API response may echo the submitted text for live UI rendering, but that echo is not written into SQLite state.

### 2.3 Teaching UI Is Additive

Teaching a better reply appends a small system bubble:

```
纠正回答 "像苹果。" 已学习
```

It must not delete, replace, or reorder the preceding user/AP turn.

### 2.3a Conservative Text-Only Default

When a text-only turn has no teaching cooccurrence hit, the fallback style is conservative uncertainty (`PAR-Q.06`) rather than broad active greeting (`PAR-A.01`). This does not inspect keywords or parse text meaning; it only prevents unrelated text-only turns from randomly looking like they inherited a previous greeting lesson.

### 2.4 Workbench Tick Trace

The page shows a per-turn workbench tick trace derived from runtime events:

1. input ingress
2. optional visual focus/object enumeration
3. minimalist dialogue runtime
4. cooccurrence recall
5. styled response assembly
6. commit
7. configurable idle ticks after commit

Boundary: this is a workbench trace projection over the current Phase 20 runtime events, not a claim that Phase 20.4 has implemented a deeper multi-tick deliberation loop beyond the current backend.

### 2.5 Media Handling

The UI supports:

- file browse button,
- thumbnail/audio preview,
- chat bubble media rendering,
- local upload into a workbench media cache for selected image/audio files.

The runtime recognizes image inputs. Audio is displayed/playable in the workbench, but Phase 20.4 does not claim audio recognition.

### 2.6 Readable Memory View

Memory listing resolves AP ids into readable rows:

- expression phrase -> actual phrase text,
- teacher phrase -> teacher-provided reply,
- style phrase -> style corpus text,
- cooccurrence pair -> readable endpoints and support,
- package registry -> name, status, added/dedup counts, view/uninstall controls.

Deletion and package uninstall still operate on stable memory ids, not display text.

## 3. Red Lines

1. No `phase20_teaching_paradigms` runtime table revival.
2. No `image_label_map`, `label_table`, or independent mapping from image to answer text.
3. No keyword/regex decision route for dialogue replies.
4. No durable persistence of ordinary current-session raw user text.
5. No claim that audio recognition is completed in Phase 20.4.
6. No UI-only fake learning: teaching must create AP-native memory/cooccurrence evidence.

## 4. Acceptance Gates

1. Web main composer calls Phase 20 turn for normal text and image/text input.
2. Current-session bubbles show the raw user text and attached media.
3. Teaching appends `纠正回答 "... " 已学习` without replacing previous chat.
4. A text teaching for `你好` does not contaminate `你是谁?` when the main workbench send path is used.
5. Tick replay has play/pause, prev/next, slider, tick buttons, and configurable max/idle tick settings.
6. Memory list shows readable Chinese/text content for teacher/style memories and cooccurrence pairs.
7. Imported package list can be refreshed, viewed, and uninstalled.
8. Memory auto-refreshes after send, teach, import, uninstall, and delete.
9. Red-line scan for Phase 20.4 passes.
10. Phase 20 adjacent tests and full regression remain green.
