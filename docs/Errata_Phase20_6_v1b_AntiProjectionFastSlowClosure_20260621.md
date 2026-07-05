# APV3.0 Phase 20.6 v1b Errata - Anti-Projection, Fast/Slow Closure, and Runtime-Workbench Hardening

Date: 2026-06-21
Status: Micro errata. This document amends `Design_APV3.0_Phase20_6_FullRuntimeLoopFastSlowMemory_v1_20260620.md`; it does not replace it.
Scope: only design / review hardening. Do not treat this file as implementation evidence.
Intent: close the remaining loopholes that could let Phase 20.6 become another projected demo instead of a true AP-native runtime workbench.

---

## 0. Why v1b exists

Phase 20.6 v1 correctly changes direction: remove projected tick replay, remove whole-image dialogue shortcuts, restore per-tick action competition, connect DraftGrid, and represent fast/slow memory as real AP mechanisms.

However, v1 still has several implementation-sensitive gaps. If they are not closed before coding, an implementation could pass page-level tests while still violating the AP philosophy:

1. Fast memory could become a whole-reply macro store.
2. "Fast first, Slow later" could become "Fast bypasses Slow whenever it is confident".
3. "Unified recall" could be misunderstood as one physical store, or as one teacher-specific path.
4. Thompson sampling could make tests flaky or hide instability behind randomness.
5. `enumerate_objects_in_image` could be banned too broadly in tests, but still leak labels into runtime through another field.
6. `R_sketch` could be called but still render energy dots, original thumbnails, or empty canvases.
7. DraftGrid could become a write-only animation rather than a read/edit/recover substrate.
8. `stop_generating` could become an output token or empty commit shortcut.
9. UI panels could contain rendering logic, which is fine, but accidentally become AP decision logic.
10. Memory package import/export could miss rollback, dedup, and local-memory deletion semantics.

This errata locks those seams before implementation.

---

## 1. Terminology correction: one learning path does not mean one memory system

### 1.1 Correct distinction

| Dimension | Must be unified? | Must remain distinct? | Meaning |
|---|---:|---:|---|
| Teaching vs natural dialogue | Yes | No | Teacher events and natural dialogue are both evidence packets in the same cooccurrence / source-aware learning path. |
| Fast vs Slow system | No | Yes | They have different stores, contents, latency, consolidation, and recall objectives. |
| Candidate interface | Yes | No | Fast and Slow both emit `RecallCandidate` / `ActionCandidate` into the same competition surface. |
| Physical storage | No | Yes | Fast chains, slow semantic memories, state pool, sessions, and package registry must be separately auditable. |

### 1.2 Replacement wording

Avoid saying:

> only one recall path

Use:

> one AP-native candidate protocol, with distinct Fast and Slow stores. Teacher/natural evidence differs only by source tags, not by a separate reply or label route.

### 1.3 Redline

`RL-20.6-v1b-Term-01`: No code or UI may name a path `teaching_reply`, `teaching_hit`, `image_label_map`, `direct_label_reply`, or `taught_answer`.

`RL-20.6-v1b-Term-02`: Fast and Slow stores must expose different table prefixes and different audit views; they may not be collapsed into one SQLite table for convenience.

---

## 2. Unified candidate protocol

All recall systems must output candidates through one typed protocol before action competition.

```python
@dataclass(frozen=True)
class RecallCandidate:
    candidate_id: str
    system_origin: Literal["fast", "slow", "state_pool", "innate_drive"]
    candidate_kind: Literal[
        "action_schema",
        "next_motor_step",
        "token_sa",
        "concept_sa",
        "focus_target",
        "draft_read",
        "draft_edit",
        "commit_intent",
        "stop_intent",
        "teacher_request_intent",
    ]
    source_tags: tuple[str, ...]          # teacher_event, natural_dialogue, imported_package, self_practice, etc.
    evidence_refs: tuple[str, ...]        # packet ids / edge ids / chain ids / vector ids
    confidence: float                     # calibrated 0..1 score before action competition
    successor_gain: float                 # fast/slow continuation pressure
    novelty_object: float
    novelty_context: float
    semantic_bindings: dict[str, str]     # slots filled by current state or slow evidence
    conflict_markers: tuple[str, ...]
    audit: dict[str, Any]
```

Action candidates are built from recall candidates, not directly from strings.

```python
@dataclass(frozen=True)
class ActionCandidate:
    action_id: str
    kind: Literal[
        "move_focus",
        "sample_focus",
        "look_again_draft",
        "write_cell",
        "edit_cell",
        "delete_cell",
        "commit_reply",
        "stop_generating",
        "request_teacher",
        "idle",
    ]
    params: dict[str, Any]
    score_components: dict[str, float]
    source_candidate_ids: tuple[str, ...]
    eligibility: float
    final_score: float
```

### Gates

`G-20.6-v1b-Candidate-01`: every selected action references one or more `source_candidate_ids`, except pure low-level `idle`.

`G-20.6-v1b-Candidate-02`: UI top-K action display is generated from `ActionCandidate`, not from hand-written frontend labels.

`G-20.6-v1b-Candidate-03`: candidate audit can answer: "what evidence made this action possible?" and "what source tags would be credited or punished?"

---

## 3. Fast system anti-macro constraints

The Fast system is AP-native and necessary. It must model practiced action coordination, successor priors, motor chunks, imitation, abstraction, and generalization. But it must not become a hidden answer table.

### 3.1 What Fast may store

Fast may store:

1. action chain schemas, e.g. `look_again_draft -> write_cell -> commit_reply`;
2. motor chunks, e.g. practiced character-cell placement patterns;
3. successor priors, e.g. "after writing a comma, continue same row";
4. context-action associations, e.g. "external query pressure + stable draft -> commit";
5. teacher-demonstrated action traces, stored as action episodes, not as semantic answers.

### 3.2 What Fast must not store

Fast must not store:

1. a whole reply selected from user text;
2. an image label bound to an object feature;
3. a fixed answer for a query string;
4. a chain that writes multiple semantic tokens without per-tick recompetition;
5. a chain that commits without checking current DraftGrid, conflict markers, and unresolved pressure.

### 3.3 One tick, one executable step

A Fast chain may propose a next step, but it must not execute the whole chain.

Required behavior:

```text
tick t:
  Fast recalls chain candidate
  action_competition may select only the next action
  action executes
  tick t+1 recomputes state, recall, and competition from scratch
```

### 3.4 Semantic binding rule

If a Fast candidate proposes writing a visible character or word fragment, the semantic content must come from one of:

1. current sensory/text state;
2. current DraftGrid readback;
3. Slow recall candidate;
4. teacher demonstration slot that is source-tagged and still passes current-context eligibility.

Fast chain content may provide motor continuity, not semantic authority.

### Gates

`G-20.6-v1b-Fast-01`: no Fast table has a column named `reply_text`, `answer_text`, `image_label`, or `full_sentence`.

`G-20.6-v1b-Fast-02`: a selected Fast chain cannot produce more than one executable action in one tick.

`G-20.6-v1b-Fast-03`: if a Fast-origin `write_cell` action writes visible text, the event must show which current-state or Slow candidate supplied the semantic binding.

`G-20.6-v1b-Fast-04`: a Fast-origin `commit_reply` must include `draft_stability`, `conflict_marker_count`, `unresolved_pressure`, and `external_reply_pressure` in score components.

`G-20.6-v1b-Fast-05`: the old bug transcript must fail without this gate and pass with it: after teaching image-question behavior, a later plain "你好" must not recall "这是什么" as a semantic answer.

---

## 4. Fast/Slow arbitration, not hard bypass

v1 says "Slow recall runs only if Fast gives up" in some places. That is too risky.

Human-like fast action is supervised by slower conflict and context checks. Therefore:

1. Fast may run first for latency.
2. Slow may run in parallel, be budgeted, or run as a minimal probe.
3. Fast may reduce Slow depth only under strict low-risk conditions.
4. Slow must run fully when there is novelty, external question pressure, image input, teacher correction, source conflict, unresolved task pressure, or low draft stability.

### 4.1 Minimum slow watchdog

Every tick must run at least a cheap Slow watchdog:

```python
slow_watchdog = slow_recall_min_probe(
    state_pool_top=top_k_state_items,
    draft_snapshot=draft_grid.peek(),
    conflict_markers=state_pool.conflict_markers(),
)
```

Fast can skip full Slow-B only if:

```text
fast_top_score >= fast_confident_threshold
and slow_watchdog.conflict_count == 0
and novelty_object < novelty_low
and novelty_context < novelty_low
and external_reply_pressure < query_pressure_low
and teacher_correction_active == False
and image_focus_changed_recently == False
and unresolved_pressure < unresolved_low
```

### 4.2 Gate

`G-20.6-v1b-Arb-01`: on image turns, teacher-correction turns, and external question turns, full Slow recall must run at least once before `commit_reply`.

`G-20.6-v1b-Arb-02`: if Fast proposes a write that Slow watchdog marks as conflict, action competition must either choose a lower-risk action or record why conflict was overridden.

`G-20.6-v1b-Arb-03`: there is no code path named `fast_direct_reply`, `fast_commit_answer`, or `fast_skip_all_slow`.

---

## 5. Thompson sampling and reproducibility

v1 gate `same input twice should differ because Thompson sampling is random` is wrong. It rewards instability and makes tests flaky.

### 5.1 Correct behavior

1. With fixed seed and same state, the trace must be reproducible.
2. Without fixed seed, low-certainty situations may vary.
3. High-certainty situations should remain stable even with randomness.
4. Exploration temperature must be a function of uncertainty, not a global randomizer.

```python
temperature = clamp(
    base_temperature
    * uncertainty_pressure
    * (1.0 - draft_stability)
    * (1.0 + novelty_context),
    min_temp,
    max_temp,
)
```

### Gates

`G-20.6-v1b-Rand-01`: fixed seed produces byte-identical `RuntimeTickEvent` action sequence, excluding wall-clock timing fields.

`G-20.6-v1b-Rand-02`: high-confidence practiced greeting has >= 95% same first two selected actions across 100 non-fixed runs.

`G-20.6-v1b-Rand-03`: ambiguous visual query has measurable exploration but still never bypasses source/conflict gates.

`G-20.6-v1b-Rand-04`: remove v1 `G-20.6-Loop-03` wording that requires different answers for the same input.

---

## 6. Vision boundary: no whole-image label route, but allow low-level visual primitives

The ban is not "never call any visual helper." The ban is:

> Phase 20 dialogue runtime must not obtain a semantic object label from a whole-image recognizer and feed it to reply generation.

Allowed:

1. local focus sampling;
2. local object-centric feature extraction;
3. segmentation masks;
4. foveated sensory canvas updates;
5. offline audit scripts;
6. legacy tests outside the Phase 20 turn path.

Forbidden in Phase 20 turn path:

1. whole-image `enumerate_objects_in_image`;
2. any `ObjectFile.label` or `object.name` directly entering DraftGrid;
3. filename/path-derived labels;
4. UI label clicks that create semantic answers instead of focus guidance;
5. "Phase20 hit teaching memory" display or logic.

### 6.1 ObjectFile boundary

ObjectFile may exist as a low-level percept container. Its label field, if present for audit, is evaluator metadata. It must not be used as a semantic candidate unless the token was learned through cooccurrence and carries source-tagged AP evidence.

### Gates

`G-20.6-v1b-Vision-01`: instrument the Phase 20 turn runtime. During a visual dialogue turn, calls to `enumerate_objects_in_image` must be zero.

`G-20.6-v1b-Vision-02`: no selected `write_cell` action may cite `ObjectFile.label`, filename, path, or curation metadata as evidence.

`G-20.6-v1b-Vision-03`: visual reply tokens must cite active local visual SA plus Slow cooccurrence/retrieval candidates.

`G-20.6-v1b-Vision-04`: teacher-guided focus rectangles only increase saliency/focus priority; they do not bind labels.

---

## 7. R_sketch and inner-picture gates

Calling `R_sketch()` is not enough. The inner picture must be an audit view of the perceived sensory canvas, not a raw thumbnail and not an energy scatterplot.

### 7.1 Required substrates

`inner_picture` for the perceived stream must use:

1. foveated sensory canvas accumulated from local focus samples;
2. per-tick focus trajectory;
3. local V0..V12 features available at that tick;
4. clarity field from sampled focus points;
5. epistemic source `PERCEIVED`.

It must not use:

1. original full image resized directly as the output;
2. image filename or label;
3. state-pool energy circles as a substitute;
4. `R_proto` when the panel says perceived sketch.

### 7.2 Quantitative gates

For a turn with an image and at least 5 focus samples:

`G-20.6-v1b-Sketch-01`: sampled focus regions have higher local similarity to the source image than never-sampled regions.

`G-20.6-v1b-Sketch-02`: edge overlap inside the latest focus patch increases after that focus is sampled.

`G-20.6-v1b-Sketch-03`: multi-tick sensory-canvas coverage is non-decreasing.

`G-20.6-v1b-Sketch-04`: output hash is not equal to a direct thumbnail hash of the source image.

`G-20.6-v1b-Sketch-05`: a blank/near-empty canvas fails unless the image truly has no usable visual input.

`G-20.6-v1b-Sketch-06`: inner-picture data is rendered from `RuntimeTickEvent.inner_picture_canvas_png_hash` or a persisted tick artifact referenced by it; frontend may not reconstruct it from original image URL.

### 7.3 Recognition boundary

The inner picture is a mirror of AP state. It may be inspected by humans. It must not be used as a hidden recognition input that gives the runtime a second chance to label the image.

`RL-20.6-v1b-Sketch-01`: no runtime recognition code may parse the inner-picture PNG to produce labels.

---

## 8. DraftGrid lifecycle

DraftGrid is not an animation buffer. It is the current externalized draft substrate AP reads, edits, and commits.

### 8.1 Required operations

Each operation must be a real action candidate:

1. `look_again_draft(row, col | region)`;
2. `write_cell(row, col, char)`;
3. `edit_cell(row, col, new_char)`;
4. `delete_cell(row, col)`;
5. `insert_cell(row, col, char)`;
6. `move_cursor(row, col)`;
7. `commit_reply()`.

### 8.2 Read-before-commit

Before `commit_reply`, action competition must have access to:

1. draft text readback;
2. grid occupancy;
3. unresolved slots;
4. recent edit rate;
5. conflict markers;
6. completion pressure.

### 8.3 Interruption recovery

If a turn is interrupted before commit:

1. remaining unresolved DraftGrid state is stored as unresolved SA;
2. next turn can recall it through normal state/Slow recall;
3. recovery competes with the new user request rather than forcing a fixed order.

### Gates

`G-20.6-v1b-Draft-01`: there is no `reply_text` before the first `commit_reply` event.

`G-20.6-v1b-Draft-02`: `final_reply` equals `DraftGrid.to_string()` at commit tick.

`G-20.6-v1b-Draft-03`: a test turn includes an edit/delete action and proves final reply changed because of that edit.

`G-20.6-v1b-Draft-04`: interruption test proves unfinished grid state changes the next turn's candidate distribution.

---

## 9. Active stop, commit, and teacher request

`stop_generating` is not a token and not a blank reply.

### 9.1 Distinct actions

| Action | Meaning | Output bubble? | Ends turn? |
|---|---|---:|---:|
| `commit_reply` | submit current DraftGrid text | Yes | Yes |
| `stop_generating` | stop internal generation / wait | No, unless a prior commit exists | Yes |
| `request_teacher` | create teacher-request pressure and write a learned request through DraftGrid | Yes only after DraftGrid commit | Usually yes |
| `idle` | do nothing this tick | No | No |

### 9.2 Stop score components

`stop_generating` and `commit_reply` must be scored separately:

```python
commit_score = (
    semantic_completion
    + draft_stability
    + external_reply_pressure
    - unresolved_pressure
    - conflict_pressure
    - recent_edit_pressure
)

stop_score = (
    low_external_reply_pressure
    + fatigue_pressure
    + no_viable_action_pressure
    - unresolved_pressure
    - teacher_request_pressure
)
```

### 9.3 Teacher request is not a hardcoded phrase

`request_teacher` creates a teacher-request SA. The visible question is then written through the same DraftGrid/action competition path using learned expression evidence. No `_styled_question_from_corpus()` shortcut is allowed in the runtime path.

### Gates

`G-20.6-v1b-Stop-01`: `stop_generating` never calls `commit("")`.

`G-20.6-v1b-Stop-02`: no `if token == "完了": stop()` or equivalent token trigger exists.

`G-20.6-v1b-Stop-03`: `request_teacher` does not return a hardcoded question string; it produces state pressure and DraftGrid actions.

`G-20.6-v1b-Stop-04`: commit and stop can be distinguished in tick replay and audit charts.

---

## 10. Memory lifecycle and package ecology

The workbench must show, edit, import, export, and unload AP memories without inventing a non-AP teaching store.

### 10.1 Local memory views

The local memory browser must include:

1. Slow cooccurrence edges;
2. Slow vector/prototype memories;
3. Fast action chains;
4. imported package registry;
5. session/turn/tick trace index;
6. source tags and evidence references;
7. human-readable summaries where available;
8. raw audit IDs in an advanced view only.

### 10.2 Deletion and rollback semantics

Every memory row must carry:

```text
memory_id
memory_kind
source_tags
source_batch_id
created_turn_id
created_tick
support_count
ref_count
dedup_key
```

Import uninstall rule:

1. imported rows with `ref_count == 1` and `source_batch_id == target` are deleted;
2. deduplicated shared rows decrement only that batch's contribution;
3. local rows created before import are not deleted;
4. after uninstall, candidate distribution must match pre-import snapshot within tolerance.

Manual deletion rule:

1. deleting a memory affects future recall;
2. deletion is source-aware and auditable;
3. deleted IDs are tombstoned to prevent package re-import from silently restoring them unless user explicitly allows restore.

### 10.3 Package export

Package export may include:

1. selected Slow edges/prototypes;
2. selected Fast action chains;
3. selected source tags;
4. time ranges;
5. keyword/search matches;
6. manual include/exclude list;
7. support / delta_p thresholds;
8. optional example transcripts.

Package export must default to excluding raw user text and original media unless the user explicitly includes them. The local workbench session itself may display and store raw transcript for replay because this is a local user training environment; export defaults remain conservative.

### Gates

`G-20.6-v1b-Mem-01`: after teaching, new cooccurrence/fast-chain evidence appears in the local memory browser without page refresh.

`G-20.6-v1b-Mem-02`: deleting a displayed memory changes later recall candidates.

`G-20.6-v1b-Mem-03`: import, dedup, uninstall round-trip leaves state equal to pre-import snapshot for non-shared rows.

`G-20.6-v1b-Mem-04`: imported package list displays package name, batch id, counts, source, install time, and uninstall button.

`G-20.6-v1b-Mem-05`: user can inspect package contents before import and before export.

---

## 11. Session persistence and history replay

No hidden "privacy bar" in the workbench UI. The history panel is a functional session replay list.

### 11.1 Persisted artifacts

Each session must persist:

1. session metadata and title;
2. user text as local transcript for the workbench profile;
3. media references or copied local media blobs;
4. turns;
5. `RuntimeTickEvent` stream;
6. DraftGrid snapshots or reconstructable deltas;
7. focus trajectory;
8. state-pool summaries;
9. memory deltas;
10. audit metrics;
11. final reply.

### 11.2 Replay rule

Clicking a historical session loads the persisted tick stream. It must not rerun the current runtime and produce a new trace, unless the user explicitly chooses "rerun".

### Gates

`G-20.6-v1b-Hist-01`: history list click loads the same tick count, same action sequence, and same final reply recorded at original run.

`G-20.6-v1b-Hist-02`: the UI contains no "输入已隐藏", "原文未保存", or "历史隐私" text in the local workbench profile.

`G-20.6-v1b-Hist-03`: raw transcript display is local-session only; memory package export still requires explicit raw-text inclusion.

---

## 12. UI boundary: view transforms are allowed, AP decisions are not

The frontend may:

1. lay out panels;
2. render charts;
3. smooth graph animation;
4. run force-directed layout for thought cloud display;
5. show thumbnails/audio controls;
6. filter or search displayed memories;
7. submit user actions to the backend.

The frontend must not:

1. choose AP actions;
2. generate reply text;
3. infer labels from images;
4. decide memory support or confidence;
5. decide commit/stop;
6. translate SA ids into semantic labels unless the backend provided human-readable text;
7. patch tick traces.

### 12.1 Thought cloud display

Thought cloud items must come from `RuntimeTickEvent.thought_cloud_items`.

Frontend force layout is a display transform only:

```text
node size = backend energy magnitude
node hue = backend real/virtual energy balance
node saturation = backend energy dominance
node label = backend human_readable_label
```

If `human_readable_label` is missing, display "未命名记忆 xxxx", not raw SA id.

### 12.2 Audit charts

Required per-tick chart groups:

1. total tick time and stage timings;
2. state pool size by family;
3. R/A/P/F aggregate energies in one chart;
4. cognitive/unresolved pressure;
5. Fast vs Slow recall attempts and top scores;
6. action top-K score comparison;
7. DraftGrid occupancy and edit rate;
8. focus movement distance and visual coverage;
9. memory promote/delete/import deltas;
10. commit/readiness/stability curves.

Each chart must be built from per-tick metrics. Turn-total divided by N is forbidden.

### Gates

`G-20.6-v1b-UI-01`: visible UI text scan has no raw SA id unless advanced audit mode is enabled.

`G-20.6-v1b-UI-02`: charts include at least one multi-line chart and at least ten per-tick metric series overall.

`G-20.6-v1b-UI-03`: thought cloud nodes do not overlap after force layout settles in Playwright screenshot.

`G-20.6-v1b-UI-04`: UI cannot display tick panels unless each tick event has `is_projection == False`.

---

## 13. TTS, audio, canvas, and teacher-guided focus

### 13.1 TTS

TTS is output narration only:

```text
reply_tts_audio != inner_voice_sketch
```

Implementation must use local file output. Do not assume pyttsx3 can return bytes directly.

Gates:

`G-20.6-v1b-TTS-01`: pyttsx3 output is written to a local WAV/MP3 file and referenced by path/hash.

`G-20.6-v1b-TTS-02`: if pyttsx3 is unavailable, UI shows local TTS unavailable; it must not call cloud TTS.

### 13.2 Recording

Recording has three modes:

1. `audio_audit_only`: store waveform and display it;
2. `phase19_1_basic`: if enabled, feed auditory receptor primitives;
3. `phase19_4_recognition`: future recognition.

Default is `audio_audit_only`. It must not pretend speech recognition exists.

### 13.3 Canvas

Canvas creates an image input. It must go through the visual focus/runtime path, not OCR.

`RL-20.6-v1b-Canvas-01`: no `pytesseract`, `easyocr`, `paddleocr`, or OCR route in Phase 20.6 canvas path.

### 13.4 Teacher-guided focus

Teacher rectangles are focus hints:

```text
teacher_guided_focus_candidates -> saliency boost -> action competition
```

They are not labels and not answers.

---

## 14. Style corpus import

The existing style dialogue examples must be learned into AP-native memory, not used as a hidden template table.

### 14.1 Required representation

Each style example becomes evidence packets:

1. user/context token SA;
2. reply expression token/paradigm SA;
3. feeling/expression cooccurrence if available;
4. source tag `style_corpus_import`;
5. package/batch id.

It can bias expression style through cooccurrence and action competition. It must not map input strings to complete replies.

### Gates

`G-20.6-v1b-Style-01`: style corpus import count is reported and visible in memory browser.

`G-20.6-v1b-Style-02`: disabling/removing the style import changes expression candidates but does not remove core visual/text understanding.

`G-20.6-v1b-Style-03`: no exact input-to-full-reply table is created from style corpus.

---

## 15. Agent tool boundary

The shareable agent API must call the same runtime as the web workbench.

Forbidden:

1. web uses Phase 20.6 runtime, API uses old `minimalist_dialogue_flow`;
2. API precomputes reply and emits synthetic ticks;
3. API omits memory deltas or source trace.

Required output:

```python
class APDialogueResult:
    session_id: str
    turn_id: str
    final_reply: str
    end_reason: Literal["commit", "stop", "max_tick", "error"]
    tick_count: int
    tick_event_refs: tuple[str, ...]
    memory_delta_refs: tuple[str, ...]
    source_trace: dict[str, Any]
```

`G-20.6-v1b-Agent-01`: web `/api/phase20/turn` and agent tool import the same runtime function.

---

## 16. Anti-cheat regression suite

These tests are mandatory before claiming Phase 20.6 complete.

### 16.1 No precomputed reply

Input: ordinary text.

Expected:

1. no `reply_text` exists before `commit_reply`;
2. DraftGrid evolves per tick;
3. final reply equals grid at commit.

### 16.2 No whole-image label answer

Input: image with filename containing the correct concept.

Expected:

1. runtime does not call whole-image enumeration;
2. filename token never appears as evidence;
3. reply token must cite cooccurrence/visual SA evidence or remain uncertain.

### 16.3 Teaching does not hard overwrite

Transcript:

1. user: "你好"
2. AP replies through normal runtime
3. user with image asks: "这是什么?"
4. teacher correction teaches image/text cooccurrence
5. user: "你好"

Expected:

1. later "你好" does not output "这是什么";
2. image teaching changes visual-token recall, not plain greeting semantics;
3. memory browser shows source-tagged evidence.

### 16.4 Interruption changes plan

Start a multi-object visual answer, interrupt mid-turn, then continue.

Expected:

1. interrupted task creates unresolved SA;
2. next turn candidate distribution includes recovery pressure;
3. recovery competes with new query rather than fixed forced order.

### 16.5 Memory delete affects recall

Teach one association, verify recall rises, delete the memory row, verify recall candidate disappears or drops below threshold.

### 16.6 Package import/uninstall identity

Snapshot memory, import package, verify candidates change, uninstall package, verify memory/candidate state returns to snapshot except allowed timestamps/audit counters.

### 16.7 UI projection scan

Playwright checks:

1. no "投影" warning;
2. no "输入已隐藏";
3. no "命中教学";
4. no raw SA ids in default mode;
5. tick slider changes DraftGrid, inner picture, thought cloud, and charts together.

---

## 17. Delivery discipline

v1 says 10-day full landing. That is acceptable only if it does not become a black-box implementation sprint with no internal proof.

Use this discipline:

1. Keep the user-facing completion claim until all gates pass.
2. Still create daily internal artifacts: design delta, redline scan, targeted tests, screenshots.
3. Do not ask for acceptance of partial 20.6 as if it were the final workbench.
4. If a foundational gate fails, stop feature stacking and fix the substrate first.
5. Final report must list every still-fake or still-disabled item. "Not implemented" is acceptable; pretending is not.

### Implementation order lock

1. Deletion/redline scan: old projected trace, old teaching hit, whole-image runtime calls.
2. Runtime skeleton: true `RuntimeTickEvent`, no precomputed reply, DraftGrid commit.
3. Fast/Slow candidate protocol and arbitration.
4. Visual focus sampling and R_sketch.
5. Teaching/cooccurrence and memory lifecycle.
6. UI panels wired to persisted tick events.
7. TTS/canvas/recording/focus hints.
8. Agent API parity.
9. Full gates, showcase, final report.

---

## 18. Go / no-go checklist before coding

Do not start implementation until each item is checked:

1. v1 and v1b are both treated as active requirements.
2. `FastActionChainStore` is scoped as action coordination, not answer memory.
3. Slow watchdog/full Slow recall conditions are accepted.
4. fixed-seed replay requirement replaces random-different requirement.
5. Phase 20 visual runtime ban is label-route-specific, not a global ban on visual primitives.
6. `R_sketch` quantitative gates are accepted.
7. DraftGrid read/edit/recover operations are in scope.
8. stop/commit/request_teacher action semantics are separated.
9. local workbench history stores and displays raw transcript; exports default conservative.
10. memory browser includes fast, slow, imported package, session, delete, and uninstall views.
11. UI rendering transforms are allowed; UI AP decisions are forbidden.
12. style corpus import goes through AP-native evidence packets.
13. agent tool must share web runtime.
14. anti-cheat suite is required before any completion claim.

If all 14 are accepted, Phase 20.6 can move from design/review to implementation.

