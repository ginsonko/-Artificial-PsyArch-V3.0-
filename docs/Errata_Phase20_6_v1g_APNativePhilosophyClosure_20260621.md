# APV3.0 Phase 20.6 v1g Errata - AP-Native Philosophy Closure

Date: 2026-06-21
Status: Final philosophy/adversarial errata before implementation. This document amends Phase 20.6 v1 + v1b + v1c + v1d + v1e + v1f.
Scope: design/review only. No runtime implementation is claimed here.

---

## 0. Why v1g exists

v1 to v1f already closed the largest fake-runtime risks:

- no projected tick replay;
- no precomputed reply;
- no whole-image label route;
- no Fast whole-reply macro;
- no independent teaching table;
- no empathy keyword route;
- no UI-generated AP decisions.

This v1g performs one final philosophical pass:

> Any feature that can be represented as AP state, AP memory, AP candidate, AP action, AP source tag, or AP actuator must be implemented through that AP-native route. External helpers may only be sensors, actuators, caches, or views. They may not become semantic authority.

---

## 1. AP-native conversion test

Before implementing any Phase 20.6 feature, answer these six questions.

```text
1. Does it enter AP as one or more source-tagged SA packets?
2. Does it leave AP only through an action candidate or actuator after action competition?
3. If it affects words, can the selected write action cite current state / Slow recall / DraftGrid / teacher-source evidence?
4. If it affects confidence, reward, or punishment, does it use source-aware eligibility and support update?
5. Can the complete effect be replayed from RuntimeTickEvent plus memory deltas?
6. If the external artifact is deleted or rebuilt, does AP truth remain in AP memory rather than the helper cache?
```

If any answer is no, the feature is not AP-native yet.

### Redline

`RL-20.6-v1g-Core-01`: A feature may not output semantic text, labels, confidence, or actions unless it has passed through `RecallCandidate -> ActionCandidate -> action_competition -> DraftGrid/actuator`.

`RL-20.6-v1g-Core-02`: External caches, UI views, TTS engines, browsers, package names, filenames, and image/audio metadata cannot be semantic evidence unless first converted into source-tagged AP evidence packets by an explicit teacher/import event.

---

## 2. Allowed outer surfaces

External systems are allowed only in these roles:

| Role | Allowed | Forbidden |
|---|---|---|
| Sensor | image/audio/text/canvas/focus box becomes SA evidence | sensor directly names the answer |
| Actuator | committed reply is spoken by TTS or displayed | actuator decides what to say |
| Cache | Zvec returns vector ids/scores | cache returns label/decision |
| View | UI renders tick events, charts, memory lists | UI changes AP confidence/action |
| Teacher source | user/imported package gives examples/corrections | teacher table hard-overrides answer |
| Safety boundary | system marks crash/timeout/incomplete | safety stop is presented as AP's own decision |

This distinction must be visible in code names and audit traces.

---

## 3. Remaining non-AP-native risks and required conversion

### 3.1 Identity and self-description

Risk: answering "你是谁?" through a fixed identity string.

AP-native route:

- identity/persona facts are seeded as autobiographical/self-profile SA memories;
- "who are you" style questions activate self-referent/query-pressure SAs;
- Slow recall proposes self-profile tokens;
- Fast may help with practiced wording only as action coordination;
- visible text is written into DraftGrid one action at a time.

Gate:

`G-20.6-v1g-Identity-01`: no runtime branch returns a fixed identity answer; self-description reply cites self-profile memory IDs and DraftGrid write actions.

### 3.2 Persona and "小默风格"

Risk: style becomes a template picker.

AP-native route:

- Phase 16 / style corpus examples import as `expression_pattern_sa`, token cooccurrence edges, source tags, and affect/social-context links;
- no full reply template is executable;
- style influences `expression_style_fit` in the single v1d action-drive equation;
- written characters still come from token candidates and DraftGrid actions.

Gate:

`G-20.6-v1g-Style-01`: a style-influenced reply can show which expression-pattern SAs contributed, but no candidate stores a whole reply string.

### 3.3 Empathy, comfort, and social warmth

Risk: empathy becomes `if sad: empathy_template()`.

AP-native route:

- v1f is authoritative: user-observed affect, self-affect memory, relationship context, and response patterns are first-class SAs;
- empathy is co-recall plus action competition, not a module;
- AP may answer the user's concrete task and still choose warmer expression if learned;
- overclaiming the user's state lowers `source_boundary_fit`.

Extra gate:

`G-20.6-v1g-Empathy-01`: empathy tests must include a concrete-task-plus-distress case where AP does not blindly suppress task answering.

### 3.4 Theory of mind / perspective taking

Risk: adding a "user mental state classifier".

AP-native route:

- use `other_observed`, `other_inferred`, `self_episodic`, and `imagined_perspective` source tags;
- inferred user state is uncertain SA evidence, not truth;
- perspective-taking candidates must carry uncertainty and overclaim risk;
- responses such as "你可能..." must be learned expression patterns, not hardcoded disclaimers.

Gate:

`G-20.6-v1g-ToM-01`: no runtime code treats inferred user state as direct fact; selected action evidence shows source boundary and uncertainty.

### 3.5 Image annotation

Risk: "图片标注" becomes an `image_feature -> label` table.

AP-native route:

- teacher text and focus-local visual SAs co-activate in the same tick window;
- repeated cooccurrence creates support peaks through `sparse_pairwise` / Slow memory;
- next visual encounter recalls associated token candidates through C/B recall;
- no object label enters DraftGrid unless learned through these cooccurrence edges.

Gate:

`G-20.6-v1g-ImageTeach-01`: an image-teaching test must show visual SA ids, text token SA ids, cooccurrence edge updates, and later token recall without using filename/object metadata.

### 3.6 Multi-object recognition and counting

Risk: detector count or whole-image object list becomes the answer.

AP-native route:

- each focus-local object candidate becomes a distinct object episode SA;
- inhibition-of-return reduces repeated focus on the same object;
- "count" emerges from distinct remembered object episodes in the current visual context;
- number words are written through learned count-expression/token candidates, not detector outputs.

Gate:

`G-20.6-v1g-Count-01`: count reply evidence must cite focus-local object episodes and IOR/distinct-object trace, not a detector count field.

### 3.7 Teacher corrections and rewards

Risk: correction directly rewrites the future answer.

AP-native route:

- correction creates source-tagged teacher event packets;
- candidate/action eligibility traces determine credit and punishment;
- rewarded alternatives are learned by cooccurrence and support deltas;
- prior bad outputs are punished source-aware, not globally deleted unless user explicitly deletes memory.

Gate:

`G-20.6-v1g-Correct-01`: after correction, memory deltas show positive support for teacher evidence and negative support for responsible prior candidates; no direct answer override table exists.

### 3.8 Memory package ecosystem

Risk: packages become plugins/skills that install answers.

AP-native route:

- a package is only a bundle of AP memory rows: Slow edges/prototypes, Fast action chains, source tags, evidence summaries, optional examples;
- import is an evidence event with `source_batch_id`, trust, support, dedup key, and profile scope;
- uninstall reverses only that batch's contribution;
- package name, filename, and category are UI metadata, not recall evidence.

Gate:

`G-20.6-v1g-Package-01`: imported memory affects recall only through ordinary Fast/Slow candidates with source tags; package metadata is absent from semantic score components.

### 3.9 Local memory browser and deletion

Risk: UI search/filter becomes a hidden memory selector for AP.

AP-native route:

- search/filter is a view-only query over persisted memory rows;
- manual deletion produces tombstones/source deltas that future recall respects;
- historical tick traces remain unchanged;
- UI selection can submit a teacher/user action, but then it enters as a normal source-tagged event.

Gate:

`G-20.6-v1g-MemUI-01`: filtering the memory browser without pressing a teacher/delete/import action does not change any future runtime candidate distribution.

### 3.10 TTS and voice

Risk: TTS is confused with inner voice or semantic generation.

AP-native route:

- TTS is an actuator that reads `DraftGrid.to_string()` only after `commit_reply`;
- generated audio may optionally re-enter as `SELF_ACTUATED_AUDIO` if the system listens to itself, but not in the same pre-commit decision;
- `inner_voice_sketch` remains auditory imagery from AP auditory substrate and may be unavailable.

Gate:

`G-20.6-v1g-TTS-01`: TTS has no path into `write_cell`, `commit_reply`, or semantic recall before the reply is committed.

### 3.11 Audio input and recording

Risk: ASR or audio classifier secretly supplies text/labels.

AP-native route:

- before Phase 19.1/19.4 recognition is implemented, recording is audit-only or waveform SA evidence;
- no external ASR/OCR model is used for AP-native claims;
- future audio recognition must follow the same auditory SA -> cooccurrence -> recall -> action route.

Gate:

`G-20.6-v1g-Audio-01`: audio demo reports its mode: `audit_only`, `basic_auditory_sa`, or `recognition`; no ASR-derived text enters runtime under AP-native mode.

### 3.12 Canvas and handwriting

Risk: drawing canvas becomes OCR.

AP-native route:

- canvas output is just an image sensor input;
- user text around the drawing teaches cooccurrence;
- no hidden OCR/shape-label shortcut is allowed.

Gate:

`G-20.6-v1g-Canvas-01`: canvas tests verify no OCR imports and no label is produced unless learned through visual/text cooccurrence.

### 3.13 Teacher-guided focus

Risk: focus rectangle becomes label supervision.

AP-native route:

- teacher rectangle creates `teacher_guided_focus_candidate` and boosts saliency only;
- any words supplied by the teacher are separate text SAs;
- visual/text binding still depends on coactivation and later recall.

Gate:

`G-20.6-v1g-Focus-01`: a focus box with no teacher text cannot create a semantic token candidate; it can only affect focus/action candidates.

### 3.14 Agent/tool API

Risk: an external agent calls `ap_perceive_and_reply` and receives a synthesized answer from wrapper logic.

AP-native route:

- API returns `RuntimeTurnResult` generated by the same Phase 20.6 runtime;
- wrapper may format fields, never generate reply text;
- external LLM/teacher responses are source-tagged teacher events, not student-side solvers.

Gate:

`G-20.6-v1g-Agent-01`: API final reply equals committed DraftGrid text and includes the commit tick ID.

### 3.15 Zvec and vector database

Risk: vector DB becomes recognizer.

AP-native route:

- Zvec is only a rebuildable Slow-C accelerator returning ids/scores;
- Slow-B and action competition still decide;
- deleting/rebuilding Zvec does not change truth memory rows.

Gate:

`G-20.6-v1g-Zvec-01`: disabling Zvec changes latency/fallback metrics but not the top semantic result on fixture queries within tolerance.

### 3.16 Active stop and max tick limits

Risk: safety timeout is reported as AP deciding to stop.

AP-native route:

- `stop_generating` is an ordinary action candidate selected by action competition;
- hard `max_tick` / crash / server timeout is a system boundary, not AP intention;
- UI must mark safety stops as `system_stop`, not `action_chosen=stop_generating`.

Gate:

`G-20.6-v1g-Stop-01`: forced max-tick termination cannot be counted as AP active stop in reports or charts.

### 3.17 Private thought / inner speech

Risk: hidden chain-of-thought generator outside AP.

AP-native route:

- inner speech, if implemented, uses the same DraftGrid-like substrate with `visibility=private`;
- private draft actions are still action candidates and can be replayed;
- public reply can read from private draft only through explicit `look_again_private_draft` / `copy_or_rewrite` candidates.

Gate:

`G-20.6-v1g-InnerSpeech-01`: no hidden text generator exists; private thought tokens, if any, are RuntimeTickEvent-visible under local audit mode.

### 3.18 Metacognition and confidence

Risk: confidence is a post-hoc display score.

AP-native route:

- confidence-like behavior emerges from evidence clarity, conflict, novelty, source trust, and draft stability SAs;
- these features enter the v1d action-drive equation;
- UI confidence chips are views of score components, not new calculations.

Gate:

`G-20.6-v1g-Meta-01`: any displayed confidence can be traced to candidate score components recorded at the selected tick.

### 3.19 Quiet consolidation

Risk: background job silently changes AP memory.

AP-native route:

- consolidation runs as post-turn / quiet-tick events;
- each consolidation emits memory deltas and source refs;
- UI can replay consolidation separately from active response ticks;
- consolidation may improve future recall but cannot rewrite past replies.

Gate:

`G-20.6-v1g-Consol-01`: every memory support change after commit is represented by a `ConsolidationTickEvent` or equivalent persisted delta.

### 3.20 Error handling and fallback

Risk: runtime error returns a canned AP reply.

AP-native route:

- if AP state is still valid, uncertainty/failure SAs may trigger `request_teacher` or a learned repair expression through DraftGrid;
- if runtime state is invalid, backend returns system error, not an AP reply;
- incomplete traces are marked incomplete.

Gate:

`G-20.6-v1g-Error-01`: no exception path returns a user-visible AP semantic reply unless it went through action competition and DraftGrid.

### 3.21 Correctness vs human-plausibility

Risk: gates judge only correct answers, encouraging hidden solvers.

AP-native route:

- tests must inspect process plausibility: focus trace, evidence refs, uncertainty, conflict, correction response, and source boundary;
- human-plausible mistakes are allowed and audited;
- nonhuman artifacts such as filename leakage, instant label tables, or impossible confidence remain redline failures.

Gate:

`G-20.6-v1g-Plausibility-01`: each showcase includes at least one "allowed uncertainty/mistake" case and one redline nonhuman-artifact negative test.

---

## 4. Unified implementation rule

All Phase 20.6 runtime-visible behaviors must be expressible as:

```text
Input/Sensor/Event
  -> source-tagged SA packets
  -> state-pool update
  -> Fast/Slow/State/Innate RecallCandidate
  -> ActionCandidate with normalized score components
  -> action_competition
  -> execute one action
  -> RuntimeTickEvent
  -> memory deltas / DraftGrid / actuator / UI view
```

No other semantic route is allowed.

---

## 5. Performance after AP-native conversion

AP-native does not mean "do everything slowly." Performance must improve in human-like ways:

1. attention budget and focus-local perception;
2. Fast action chains for practiced coordination;
3. cheap Slow watchdog plus mandatory full Slow only under risk;
4. Zvec / vector index as rebuildable C-recall accelerator;
5. bounded candidate caps with dropped-candidate audit;
6. incremental sensory canvas and DraftGrid deltas;
7. post-turn consolidation instead of full maintenance each active tick;
8. UI virtualization/downsampling as view-only optimization.

Expected claim level remains:

```text
P1: usable local demo if p95 turn latency and UI responsiveness pass.
P2: scalable memory substrate only if 1k/10k Zvec benchmarks beat brute-force and fallback correctness matches.
```

If P2 fails, the report must say "Zvec integrated as rebuildable accelerator; large-scale speed not yet proven." It must not add shortcuts.

---

## 6. Added redline scan targets

Implementation must scan runtime code and UI-visible text for:

```text
fixed_identity_reply
persona_template
empathy_template
affect_modulator
image_label_map
direct_label_reply
teaching_hit
taught_answer
object_count_answer
detector_count
asr_text
ocr_text
frontend_confidence
frontend_label
system_stop_as_ap_stop
fallback_reply
package_skill_execute
reply_from_wrapper
```

Allowed fixture/docs occurrences must be explicitly whitelisted by path.

---

## 7. Added deliverable gates

| Gate | Meaning |
|---|---|
| G-20.6-v1g-Core-01 | Every visible semantic output has a `RuntimeTickEvent` action chain and DraftGrid commit source |
| G-20.6-v1g-Core-02 | Every non-text feature enters as SA packet, action candidate, actuator, cache, or view with source boundary |
| G-20.6-v1g-Core-03 | No UI-only interaction changes AP state unless it submits a typed user/teacher action |
| G-20.6-v1g-Core-04 | Safety timeout and runtime crash are not counted as AP stop or AP reply |
| G-20.6-v1g-Core-05 | Package import/export/uninstall changes future recall through memory rows only |
| G-20.6-v1g-Core-06 | Identity, style, empathy, image teaching, and count demos all pass without fixed answer routes |
| G-20.6-v1g-Core-07 | Performance report separates AP-native speedups from cache/UI speedups and states P1/P2 level honestly |

---

## 8. Final go / no-go after v1g

Implementation may begin only if the team accepts:

1. no feature is "just UI" if it changes AP behavior;
2. no feature is "just a helper" if it supplies semantic labels, answers, or confidence;
3. identity/persona/empathy/style are memories and co-recall patterns, not hardcoded branches;
4. image/audio/canvas/teacher focus are sensors or saliency guidance, not label routes;
5. TTS, charts, thought cloud, and memory browser are views/actuators, not AP decision makers;
6. forced timeouts and errors are system boundaries, not AP mental actions;
7. performance work must remain attention economy/cache acceleration, not hidden shortcuts.

With v1 + v1b + v1c + v1d + v1e + v1f + v1g read together, the Phase 20.6 design is ready for implementation from the redline deletion scan and true runtime boundary.

