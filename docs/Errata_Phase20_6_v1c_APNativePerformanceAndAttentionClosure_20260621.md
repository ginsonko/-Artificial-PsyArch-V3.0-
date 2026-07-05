# APV3.0 Phase 20.6 v1c Errata - AP-Native Performance, Attention Economy, and Final Adversarial Closure

Date: 2026-06-21
Status: Micro errata. This document amends Phase 20.6 v1 + v1b. It does not replace them.
Scope: design hardening only. No runtime/UI implementation is claimed here.

---

## 0. Why v1c exists

Phase 20.6 v1 fixes the direction: true per-tick AP runtime, DraftGrid, visual focus, Fast/Slow memory, and workbench as a faithful mirror.

v1b closes the most dangerous anti-cheat gaps: no precomputed reply, no whole-image label path, no Fast answer macros, no fake R_sketch, no UI decisions.

This v1c adds the final layer needed before implementation:

1. performance must be treated as an AP-native design problem, not an afterthought;
2. the new vector recall index must be used as a rebuildable C-recall accelerator only, not as recognition quality proof;
3. every expensive operation must be governed by attention, uncertainty, pressure, fatigue, and novelty, which is closer to human cognition than "run all modules every tick";
4. benchmarking gates must be explicit before any claim that Phase 20.6 is usable as a dialogue base.

---

## 1. Final adversarial review of v1 + v1b

### 1.1 No remaining architecture-level blocker

After v1b, the main AP-philosophy blockers are addressed:

- old teaching/image-label/reply-table routes are banned;
- Fast system is scoped to action coordination, not semantic answer authority;
- Slow system remains source-aware semantic/conceptual memory;
- action competition is per tick and cannot be faked by splitting a precomputed answer;
- DraftGrid is the only commit source;
- visual recognition must emerge through focus-local sensory SA + cooccurrence/retrieval;
- UI panels are views over `RuntimeTickEvent`, not decision modules.

### 1.2 Still-dangerous implementation risks

These are not design blockers, but they can still break the implementation if not actively gated.

| Risk | Why dangerous | v1c closure |
|---|---|---|
| Running all heavy modules every tick | True runtime may become too slow and unusable | attention-budgeted stage scheduler |
| Treating Zvec speed as proven | Phase 19.9 proves rebuildable/correct cache, not speed at scale | benchmark gates and fallback metrics |
| Re-rendering full R_sketch every tick | inner-picture panel can dominate turn latency | incremental canvas + audit/render separation |
| Persisting full event blobs every tick synchronously | SQLite writes can become the bottleneck | append-only compact tick event + artifact refs + batched commit |
| Fast system still storing semantic params | action chain can silently become answer macro | slot eligibility and semantic-source audit |
| Slow watchdog too weak | Fast may commit fluent but wrong text | mandatory full Slow before visual/question/correction commit |
| UI chart volume too high | browser becomes the bottleneck | downsample display only, keep raw audit data |
| Too many candidates | action competition becomes quadratic or noisy | bounded candidate budget with audit of dropped candidates |

---

## 2. AP-native performance principle

Performance optimization must follow AP philosophy:

> The system should become faster in the same way a person becomes faster: by attention narrowing, habit, expectation, working-memory limits, fatigue, consolidation, and learned action coordination, not by hidden answer tables or bypassing perception.

Allowed performance mechanisms:

1. focus-local perception instead of full-scene processing every tick;
2. Fast action chains as practiced motor/action priors;
3. Slow watchdog before full Slow recall;
4. novelty/uncertainty-triggered deeper processing;
5. state-pool top-K attention selection;
6. inhibition-of-return for recently inspected focus areas;
7. memory decay/forgetting and consolidation;
8. C-recall index acceleration;
9. incremental sensory canvas and DraftGrid deltas;
10. asynchronous artifact rendering that does not feed back into AP decisions.

Forbidden performance mechanisms:

1. answer tables;
2. label shortcuts;
3. whole-reply macros;
4. precomputed reply then tick playback;
5. frontend-generated semantics;
6. skipping Slow recall when conflict/novelty/question/correction is active;
7. using Zvec hits as labels or confidence decisions;
8. disabling audit fields to hide cost.

---

## 3. Per-tick attention budget

### 3.1 Tick budget is a cognitive resource

Each tick receives a bounded compute budget:

```python
tick_budget_ms = base_budget_ms * pressure_factor * novelty_factor * fatigue_factor
```

Where:

```text
pressure_factor = 1 + clamp(unresolved_pressure + external_reply_pressure, 0, 1)
novelty_factor = 1 + clamp(max(novelty_object, novelty_context), 0, 1)
fatigue_factor = 1 - clamp(fatigue_energy * 0.4, 0, 0.5)
```

Interpretation:

- pressure and novelty allow deeper processing;
- fatigue narrows processing;
- low-risk practiced turns should be short;
- hard visual/teaching/correction turns are allowed to be slower.

### 3.2 Stage scheduler

Every tick should not run every stage at maximum depth. It should run:

1. mandatory micro stages:
   - state-pool decay/update;
   - current input injection;
   - action competition;
   - event emission.
2. conditional stages:
   - focus sample only if image exists and visual attention is active;
   - full Slow-B only if watchdog, novelty, question, correction, or conflict requires it;
   - full R_sketch render only for persisted audit frames or UI-requested frame;
   - package/memory maintenance during idle or post-turn consolidation, not every active tick.

### Gates

`G-20.6-v1c-Budget-01`: every RuntimeTickEvent contains `stage_timings_ms` for state update, fast recall, slow watchdog, full slow, visual sample, action competition, execute, event persist, and render/audit.

`G-20.6-v1c-Budget-02`: at least one easy text-only turn shows full Slow-B skipped on some ticks while watchdog still runs.

`G-20.6-v1c-Budget-03`: at least one image question shows full Slow-B before commit.

`G-20.6-v1c-Budget-04`: no stage may silently exceed its budget without adding `over_budget_marker` to the tick event.

---

## 4. Zvec recall: expected performance and strict limits

### 4.1 What Phase 19.9 already proved

Phase 19.9 proved:

1. the index is rebuildable from truth records;
2. Zvec hits match brute-force filtered topK on fixture data;
3. Zvec returns vector IDs and scores only;
4. labels/private metadata are not returned;
5. fallback brute-force exists.

It did not prove:

1. recognition quality;
2. open-dialogue quality;
3. real-world speedup at large memory sizes;
4. stable latency under per-tick runtime load.

### 4.2 Expected speed effect

Without indexed C-recall:

```text
Slow-C brute force ~= O(N * D) per query
```

where `N` is stored percept vectors and `D` is signature dimension.

With Zvec:

```text
Slow-C candidate retrieval ~= O(index_query + K * D)
```

where `K` is oversampled candidate count. This should be much faster when `N` grows, but only if filtering and truth-score recomputation stay bounded.

### 4.3 Current hidden cost

The current recall-index contract still recomputes truth similarity for candidates and may fall back to scanning more truth vectors if filtered hits are insufficient. That is correct for audit quality, but it means performance must be measured with realistic filters:

- epistemic_source;
- substrate;
- receptor_version;
- source trust;
- package scope;
- deleted/tombstoned memories;
- active modality.

### 4.4 v1c requirement: filter-aware indexing

If Phase 20.6 uses Zvec per tick, it should add or emulate filter-aware partitions:

```text
index_key = epistemic_source + substrate + receptor_version + modality_family
```

Then C-recall queries the correct partition first. Oversampling is still allowed but must be bounded.

### Gates

`G-20.6-v1c-Zvec-01`: benchmark Slow-C with 100, 1k, and 10k synthetic truth vectors if feasible; otherwise mark 10k as skipped with reason.

`G-20.6-v1c-Zvec-02`: report p50/p95 for brute-force fallback and Zvec path separately.

`G-20.6-v1c-Zvec-03`: report `fallback_rate`, `oversample_count`, and `filtered_hit_count` per visual turn.

`G-20.6-v1c-Zvec-04`: Zvec hit metadata still has `label_returned=False`.

`G-20.6-v1c-Zvec-05`: deleting and rebuilding the index preserves results and does not change memory truth records.

`G-20.6-v1c-Zvec-06`: if Zvec is unavailable, Phase 20.6 remains correct but may mark performance as degraded; it must not disable AP behavior.

---

## 5. Candidate-budget discipline

Human-like cognition does not consider infinite candidates every tick. It narrows candidates through attention and salience.

### 5.1 Required candidate caps

Default caps:

```text
state_pool_active_top_k = 32
fast_C_top_k = 12
fast_B_top_k = 6
slow_watchdog_top_k = 16
slow_C_top_k = 24
slow_B_top_k = 8
action_candidate_top_k = 16
thought_cloud_display_top_k = 32
```

These are starting constants, not magic truth. They must live in constants config and appear in audit.

### 5.2 Dropped-candidate audit

Dropping candidates for budget is allowed only if the tick event records:

```text
candidate_kind
count_before
count_after
drop_reason
max_dropped_score
```

### Gates

`G-20.6-v1c-Cand-01`: no unbounded loop over all slow memories runs during ordinary active ticks except explicit benchmark/audit mode.

`G-20.6-v1c-Cand-02`: candidate caps are constants, not inline numeric literals.

`G-20.6-v1c-Cand-03`: dropped-candidate audit exists for Fast, Slow, action, and UI thought-cloud display.

---

## 6. Incremental visual and inner-picture performance

### 6.1 Split sensory update from display render

Each visual tick should update the sensory canvas incrementally:

```text
focus patch -> V0..V12 local features -> sensory_canvas delta
```

The UI image artifact may be rendered:

1. every N ticks;
2. when focus changes significantly;
3. when user scrubs to that tick;
4. at commit.

The runtime event should store a stable reference to the canvas state and optional rendered artifact. AP decisions read sensory state, not the rendered PNG.

### 6.2 R_sketch cannot block action competition

`R_sketch` render is an audit/view artifact. It must not sit in the critical path unless the action itself needs introspective visual review. The normal path uses the sensory canvas state directly.

### Gates

`G-20.6-v1c-VisualPerf-01`: visual sample stage timing and R_sketch render timing are recorded separately.

`G-20.6-v1c-VisualPerf-02`: a visual turn can emit tick events even if PNG rendering is delayed; delayed render fills artifact refs later without changing AP decisions.

`G-20.6-v1c-VisualPerf-03`: UI never uses original image URL to fake inner picture.

`G-20.6-v1c-VisualPerf-04`: focus-local extraction operates on bounded patch size unless an explicit audit mode requests full-frame recomputation.

---

## 7. Persistence performance

### 7.1 Compact events, external artifacts

`RuntimeTickEvent` should persist compact structured data. Large artifacts should be stored by reference:

```text
inner_picture_png_hash
inner_picture_png_path
inner_audio_wav_hash
state_pool_summary_ref
draft_grid_delta_ref
```

Do not store raw PNG bytes or huge vector arrays inline in every tick event row.

### 7.2 Batched writes

Active tick writes may append to an in-memory event buffer and flush:

1. every `flush_every_n_ticks`;
2. on commit/stop/error;
3. before UI reply returns.

This is acceptable if crash recovery marks the turn as incomplete and does not pretend the missing ticks existed.

### Gates

`G-20.6-v1c-Persist-01`: per-turn persisted tick stream can be replayed after process restart.

`G-20.6-v1c-Persist-02`: large artifacts are stored out-of-row and referenced by hash/path.

`G-20.6-v1c-Persist-03`: SQLite write timing is included in stage timings.

`G-20.6-v1c-Persist-04`: interrupted/crashed turn is marked incomplete, not silently converted into a valid completed trace.

---

## 8. UI performance and truthfulness

### 8.1 Virtualized rendering

The browser must not render thousands of nodes/ticks at once. It may virtualize:

1. tick list;
2. memory rows;
3. session history;
4. thought cloud labels;
5. audit chart points.

Virtualization is a display transform only. Raw event data remains available for export/audit.

### 8.2 Downsampling rule

Chart downsampling is allowed for display, but:

1. raw per-tick metrics remain persisted;
2. tooltip can reveal exact tick values;
3. export uses raw data;
4. final report states whether chart was downsampled.

### Gates

`G-20.6-v1c-UIPerf-01`: 200-tick session remains responsive in Playwright interaction test.

`G-20.6-v1c-UIPerf-02`: chart downsampling does not change raw exported audit values.

`G-20.6-v1c-UIPerf-03`: UI screenshot shows no overlapping thought-cloud labels in the default top-K view.

---

## 9. More AP-philosophical optimization: active perception

Phase 20.6 should not just "process image if image exists." It should choose where to look and when to stop looking.

### 9.1 Inhibition of return

Recently sampled regions should receive temporary suppression unless:

1. uncertainty remains high;
2. user/teacher points there;
3. conflict markers require reinspection;
4. DraftGrid contains a visual claim that needs verification.

This prevents repeated center-looking and makes scan behavior more human-like.

### 9.2 Expected information gain

Focus candidates should include an expected information gain estimate:

```text
EIG = uncertainty_reduction_expected
    + object_boundary_gain
    + unresolved_slot_relevance
    + teacher_guidance_boost
    - return_inhibition
    - fatigue_cost
```

This is not a hidden detector. It is a salience/action score for where to sample next.

### 9.3 Looking and writing compete

`move_focus`, `sample_focus`, `look_again_draft`, `write_cell`, and `commit_reply` must compete in the same action space. AP may write with partial evidence, then look again if conflict rises.

### Gates

`G-20.6-v1c-ActiveVision-01`: multi-object image trace shows at least two different focus regions before confident multi-object answer.

`G-20.6-v1c-ActiveVision-02`: repeated focus on same region must have an audit reason: high uncertainty, teacher guidance, conflict, or draft verification.

`G-20.6-v1c-ActiveVision-03`: visual answer can be interrupted by draft-review or teacher-request action when uncertainty/conflict is high.

---

## 10. More AP-philosophical optimization: consolidation during quiet ticks

People do not consolidate every association at maximum depth during active response. They often consolidate after action, during pauses, or through repeated rehearsal.

Phase 20.6 should add a post-turn consolidation window:

```text
after commit/stop:
  for up to consolidation_tick_budget:
      decay temporary SA
      promote high-attention evidence
      update Fast action chain support
      update Slow cooccurrence support
      write package/memory deltas
      emit consolidation tick events
```

These ticks are still real runtime events, but they are marked:

```text
phase = "post_commit_consolidation"
visible_reply_already_committed = True
```

### Gates

`G-20.6-v1c-Consol-01`: teaching effects are not required to be instantly fully consolidated before the next millisecond, but must be available by the next turn after consolidation completes.

`G-20.6-v1c-Consol-02`: consolidation ticks can be replayed and show memory deltas.

`G-20.6-v1c-Consol-03`: no visible reply text is changed after commit by consolidation.

---

## 11. More AP-philosophical optimization: metacognitive self-monitoring

The workbench should expose AP's self-monitoring, not just hidden scores.

Add these AP-native state items:

1. `draft_stability_sa`;
2. `conflict_pressure_sa`;
3. `teacher_request_pressure_sa`;
4. `visual_uncertainty_sa`;
5. `memory_source_trust_sa`;
6. `fatigue_sa`;
7. `unfinished_task_sa`.

They are not modules that decide answers. They are state-pool items participating in action competition.

### Gates

`G-20.6-v1c-Meta-01`: commit/stop/request_teacher score components cite metacognitive SA energies.

`G-20.6-v1c-Meta-02`: thought cloud can display these metacognitive SAs in Chinese labels.

`G-20.6-v1c-Meta-03`: correction feedback changes source trust or conflict pressure through source-aware credit, not hard deletion unless user explicitly deletes memory.

---

## 12. Performance claim levels

Final reports must use these claim levels.

| Level | Allowed claim | Required evidence |
|---|---|---|
| P0 | correct but slow | gates pass, no latency claim |
| P1 | usable local demo | p95 turn latency acceptable on 5-turn demo, UI responsive |
| P2 | scalable recall substrate | benchmark 1k/10k memory, Zvec p95 better than brute-force |
| P3 | long-running local workbench | 200-tick sessions replay, memory browser responsive, DB size tracked |

Phase 20.6 should target P1. P2 is nice if Zvec benchmark passes, but must not be required for the first true runtime landing.

### Gates

`G-20.6-v1c-PerfClaim-01`: final report states P-level explicitly.

`G-20.6-v1c-PerfClaim-02`: if P2 is not proven, report says Zvec is integrated as rebuildable accelerator but large-scale speed remains unproven.

---

## 13. Revised implementation order

The safest implementation order is:

1. Redline deletion scan: old reply projection, old whole-image runtime label, old teaching hit, old `taught.response_text`.
2. True RuntimeTickEvent schema with stage timing and compact persistence.
3. DraftGrid real write/read/edit/commit, no precomputed reply.
4. Candidate protocol and action competition.
5. Fast action chain store with anti-macro gates.
6. Slow watchdog + Slow C/B recall with Zvec/brute fallback instrumentation.
7. Attention-budget scheduler and candidate caps.
8. Visual focus sampling + active perception + sensory canvas deltas.
9. R_sketch artifact rendering and quantitative gates.
10. Teaching/cooccurrence + style corpus import + memory browser.
11. Package import/export/uninstall and delete/tombstone.
12. Workbench UI panels, charts, thought cloud, history replay.
13. TTS/canvas/recording/focus hint.
14. Agent API parity.
15. Full tests, Playwright screenshots, benchmark report, final showcase.

Do not build the full UI before steps 1-9 pass. Otherwise the UI will again tempt the implementation into projection.

---

## 14. Final v1c redlines

`RL-20.6-v1c-Perf-01`: performance optimization cannot introduce answer/label/reply shortcuts.

`RL-20.6-v1c-Perf-02`: no unbounded all-memory scan in ordinary active tick path unless explicitly marked fallback/audit.

`RL-20.6-v1c-Perf-03`: no direct full-image R_sketch render in the action-critical path unless an action explicitly requests introspective visual review.

`RL-20.6-v1c-Perf-04`: no large binary artifacts inline in tick event rows.

`RL-20.6-v1c-Zvec-01`: Zvec returns IDs/scores only and cannot output labels or final decisions.

`RL-20.6-v1c-UI-01`: frontend downsampling/virtualization cannot change AP decisions or raw audit data.

`RL-20.6-v1c-Claim-01`: Phase 20.6 cannot claim P2/P3 performance unless benchmark gates pass.

---

## 15. Go / no-go after v1c

Go to implementation if all are accepted:

1. v1 + v1b + v1c are the active Phase 20.6 design set.
2. implementation begins with deletion/redline scan, not UI polish.
3. performance is AP-native attention economy, not hidden shortcuts.
4. Zvec is a C-recall accelerator/cache, not a recognizer or answer source.
5. P1 is the target for Phase 20.6; P2/P3 are explicit stretch claims.
6. final report must state which performance level is actually proven.

No-go if any of these are rejected:

1. Fast cannot be prevented from storing semantic whole replies;
2. whole-image label path remains in Phase 20 turn runtime;
3. UI is allowed to fabricate tick data;
4. no per-stage timing and benchmark gates are accepted;
5. memory deletion/import/uninstall cannot affect real recall.

