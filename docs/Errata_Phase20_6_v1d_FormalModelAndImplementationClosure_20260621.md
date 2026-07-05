# APV3.0 Phase 20.6 v1d Errata - Formal Model, Mathematical Closure, and Implementation Feasibility

Date: 2026-06-21
Status: Final pre-implementation errata. This document amends Phase 20.6 v1 + v1b + v1c.
Scope: design/formal review only. No runtime implementation is claimed here.

---

## 0. Why v1d exists

v1 established the true AP runtime direction.
v1b closed the anti-projection and anti-shortcut loopholes.
v1c closed performance and attention-economy risks.

This v1d closes the final mathematical and implementation gaps:

1. all core scores must be normalized and comparable;
2. state-pool energy dynamics must be bounded and auditable;
3. action competition must have one formal drive equation;
4. Fast/Slow arbitration must be a formal gate, not prose;
5. active vision, DraftGrid commit, stop, teacher request, consolidation, and memory learning must be mathematically closed;
6. implementation difficulty must be stated honestly before coding.

---

## 1. Final adversarial finding

No architecture-level blocker remains, but several v1/v1b/v1c parts were still under-formalized:

| Area | Prior weakness | v1d closure |
|---|---|---|
| State energy | R/A/P/F described but not bounded as a system | bounded state update equations |
| Candidate score | heterogeneous scores mixed by direct addition | one normalized action drive equation |
| Fast score | product of factors can collapse to zero too easily | log-domain geometric scoring with floor |
| Slow skip | prose conditions for when Slow can be reduced | explicit `full_slow_required` predicate |
| Commit/stop | informal positive/negative terms | normalized action-specific drive features |
| Thompson | random noise described but not posterior-like | deterministic-seed stochastic policy over calibrated drives |
| R_sketch | quality gates exist but no state relation | explicit `SensoryCanvas_t` relation to focus samples |
| Learning | cooccurrence and feedback described but not one update | source-aware bounded support update |
| Performance | budgets exist but not tied to candidate math | cost-aware action/candidate features |
| Implementation | current code lacks several methods | feasibility matrix and first-step constraints |

---

## 2. Formal state model

At tick `t`, AP state is:

```text
S_t = (I_t, M_t, D_t, C_t, H_t, E_t)
```

where:

- `I_t`: current external inputs converted into SA packets;
- `M_t`: state pool, a bounded set of state items;
- `D_t`: DraftGrid;
- `C_t`: sensory canvas / auditory canvas;
- `H_t`: fast and slow memory handles;
- `E_t`: runtime event/audit accumulator.

Each state item `i` has:

```text
x_i(t) = (R_i, V_i, A_i, P_i, F_i, T_i, U_i)
```

Meaning:

- `R`: real/current evidence energy;
- `V`: virtual/predicted/imagined energy;
- `A`: attention energy;
- `P`: cognitive/unresolved pressure;
- `F`: fatigue/inhibition;
- `T`: source trust;
- `U`: uncertainty.

All components are normalized:

```text
R,V,A,P,F,T,U in [0,1]
```

### 2.1 Bounded update equations

For each tick:

```text
R_i(t+1) = clip01(rho_R R_i(t) + I_R(i,t) + B_R(i,t))
V_i(t+1) = clip01(rho_V V_i(t) + I_V(i,t) + Pred(i,t))
P_i(t+1) = clip01(rho_P P_i(t) + Mismatch_i(t) + Unclosed_i(t) - Release_i(t))
F_i(t+1) = clip01(rho_F F_i(t) + Cost_i(t) + RepeatInhib_i(t) - Rest_i(t))
A_i(t+1) = clip01(
    rho_A A_i(t)
    + alpha_R R_i(t+1)
    + alpha_P P_i(t+1)
    + alpha_U U_i(t)
    + TopDown_i(t)
    - alpha_F F_i(t+1)
)
U_i(t+1) = clip01(1 - EvidenceClarity_i(t+1))
T_i(t+1) = clip01(T_i(t) + SourceCredit_i(t) - SourcePenalty_i(t))
```

Constraint:

```text
rho_* in [0,1]
alpha_* >= 0
sum(alpha_R, alpha_P, alpha_U, alpha_F) <= 1.5
```

`B_R` is bottom-up reinforcement from current perception or text.
`Pred` is prediction/imagery activation.
`Mismatch` comes from conflict markers.
`Unclosed` comes from unfinished tasks / incomplete DraftGrid / unanswered external query.
`Release` comes from commit, correction resolution, or successful action.

### 2.2 Aggregate energy must not be raw sum

Raw sum grows with state-pool size and is not comparable across ticks. Aggregate chart values must use bounded pooling:

```text
Agg_R(t) = noisy_or_topk({R_i(t)}, k_R)
Agg_A(t) = mean_topk({A_i(t)}, k_A)
Agg_P(t) = noisy_or_topk({P_i(t)}, k_P)
Agg_F(t) = mean_topk({F_i(t)}, k_F)
```

Where:

```text
noisy_or_topk(v_1..v_k) = 1 - product_j(1 - clip01(v_j))
```

Gate:

`G-20.6-v1d-State-01`: state components and aggregate chart values are always in `[0,1]`.

`G-20.6-v1d-State-02`: adding many low-energy irrelevant items cannot by itself force commit, stop, or high confidence.

---

## 3. Candidate normalization

Every candidate, from any origin, must expose normalized features:

```text
phi(c,t) = {
  evidence,
  source_trust,
  context_match,
  semantic_fit,
  motor_fit,
  successor_gain,
  uncertainty,
  novelty_object,
  novelty_context,
  conflict,
  fatigue_cost,
  time_cost,
  unresolved_relevance,
  draft_fit,
  visual_fit,
  teacher_pressure
}
```

Each feature is in `[0,1]`.

Missing feature rule:

```text
missing positive feature -> neutral 0.5 only if not required by action kind
missing required positive feature -> eligibility = 0
missing negative feature -> 0
```

Gate:

`G-20.6-v1d-Candidate-01`: every `ActionCandidate.score_components` contains only normalized `[0,1]` values plus raw audit values stored separately.

---

## 4. One formal action drive equation

For candidate action `a` at tick `t`:

```text
elig(a,t) in {0,1} or [0,1]
raw_drive(a,t) =
    b_kind(a)
    + sum_m w_kind(a),m * z(phi_m(a,t))
    + w_succ * z(successor_gain)
    + w_pressure * z(unresolved_relevance)
    - w_conflict * z(conflict)
    - w_fatigue * z(fatigue_cost)
    - w_cost * z(time_cost)

drive(a,t) = elig(a,t) * sigmoid(raw_drive(a,t))
```

Where:

```text
z(x) = 2 * clip01(x) - 1
sigmoid(y) = 1 / (1 + exp(-y))
```

Constraints:

```text
abs(w_*) <= 3
sum(abs(w_kind(a),m)) <= W_kind_max
drive(a,t) in [0,1]
```

Why this is needed:

- direct addition like `confidence + succession_bonus` can exceed 1 and become incomparable;
- direct subtraction like `task_completion - unresolved_pressure` can go negative without calibration;
- this equation gives every action one comparable drive scale while preserving action-specific features.

### 4.1 Required eligibility examples

```text
elig(write_cell) = 0 if no semantic binding for visible char
elig(commit_reply) = 0 if DraftGrid empty and external_reply_pressure high
elig(commit_reply) = 0 if unresolved_required_slot_count > 0 and no teacher_request_pressure
elig(stop_generating) = 0 if external_reply_pressure high and DraftGrid has uncommitted stable answer
elig(request_teacher) = 0 if teacher_request_pressure low and no uncertainty/conflict
elig(move_focus) = 0 if no visual input
```

Gate:

`G-20.6-v1d-Action-01`: implementation has one scoring function for action drive; action-specific behavior is represented by features/weights/eligibility, not separate hidden routes.

`G-20.6-v1d-Action-02`: selected action event records `eligibility`, `raw_drive`, `drive`, and feature vector.

---

## 5. Thompson / stochastic action choice

AP may be variable when uncertain, but high-certainty behavior must be stable.

Use calibrated drive as a posterior mean:

```text
mu_a = drive(a,t)
kappa_a = kappa_base / (epsilon + uncertainty_a + novelty_context_a + conflict_a)
alpha_a = 1 + kappa_a * mu_a
beta_a  = 1 + kappa_a * (1 - mu_a)
sample_a ~ Beta(alpha_a, beta_a)
```

Then choose the highest sampled action. With deterministic seed, samples are reproducible.

If `uncertainty + novelty + conflict` is below a low threshold, deterministic argmax is allowed:

```text
if max_uncertainty < u_low and max_conflict < c_low:
    choose argmax drive
else:
    choose argmax sample
```

Gate:

`G-20.6-v1d-Sampling-01`: fixed seed reproduces action sequence excluding wall-clock timings.

`G-20.6-v1d-Sampling-02`: high-certainty action selection is stable; ambiguous action selection can vary but remains inside redlines.

---

## 6. Fast system formalization

A Fast chain `h` is:

```text
h = (schema, slots, stage, support, reward, penalty, last_used, source_tags)
```

Fast score:

```text
fast_score(h,t) = exp(
    mean_j log(floor + f_j(h,t))
) * recency(h,t) * source_trust(h)
```

Where `f_j` includes:

- context match;
- motor schema match;
- stage maturity;
- successor match;
- slot eligibility;
- reward support;
- low penalty.

Use `floor` (for example 0.05) to avoid a single weak but non-critical factor collapsing the chain to zero.

### 6.1 Semantic slot rule

Fast can propose:

```text
write_cell(slot=current_next_char)
```

but `current_next_char` must be bound by:

```text
semantic_binding_source in {
  current_text_state,
  current_visual_slow_candidate,
  current_draft_readback,
  source_tagged_teacher_event_slot
}
```

Fast cannot bind semantic content by itself.

Gate:

`G-20.6-v1d-Fast-01`: Fast candidate contains `schema_score`, `slot_eligibility`, `semantic_binding_source`, and `stage_maturity`.

`G-20.6-v1d-Fast-02`: if `semantic_binding_source` is absent, Fast-origin `write_cell` has `elig=0`.

---

## 7. Slow system and full-slow requirement

Slow recall has two stages:

```text
Slow-C: candidate retrieval through sparse_pairwise / Layer index / Zvec
Slow-B: source-aware diagnostic scoring and binding
```

### 7.1 Formal full-slow predicate

Full Slow is required before commit if:

```text
full_slow_required(t) =
    image_input_active
    OR teacher_correction_active
    OR external_question_pressure > q_threshold
    OR max(conflict_i) > conflict_threshold
    OR novelty_object > novelty_object_threshold
    OR novelty_context > novelty_context_threshold
    OR unresolved_pressure > unresolved_threshold
    OR draft_stability < draft_stability_threshold
    OR Fast proposes semantic write without current Slow binding
```

Fast can reduce full Slow only when `full_slow_required(t) == False`, while Slow watchdog still runs.

Gate:

`G-20.6-v1d-Slow-01`: every commit event records whether `full_slow_required` was true and whether full Slow ran after the latest relevant input/focus change.

`G-20.6-v1d-Slow-02`: if `full_slow_required == True` and full Slow did not run, commit eligibility is zero.

---

## 8. DraftGrid formal closure

DraftGrid state:

```text
D_t = (cells, cursor, focus, revision_id)
```

Each tick may apply at most one DraftGrid mutation:

```text
delta_D(t) in {write, edit, delete, insert, move_cursor, none}
D_{t+1} = apply(D_t, delta_D(t))
```

Commit:

```text
final_reply = render_visible(D_t_commit)
```

There is no valid `final_reply` before the commit action.

Draft stability:

```text
draft_stability(t) =
    1
    - normalized_recent_edit_rate(t)
    - unresolved_slot_ratio(t)
    - conflict_marker_ratio(t)
```

clipped to `[0,1]`.

Implementation note:

Current `apv3test/runtime/draft_grid.py` has `write_at` and visible text methods, but not the complete edit/delete/insert/revision API required by v1b/v1d. Implementation must extend it before claiming DraftGrid lifecycle complete.

Gate:

`G-20.6-v1d-Draft-01`: DraftGrid supports write/edit/delete/insert/move/read/revision in code and tests.

`G-20.6-v1d-Draft-02`: `final_reply` is absent or `None` before commit; hashes may exist only for DraftGrid snapshots.

---

## 9. Commit / stop / request-teacher closure

Use the general action drive equation, with these action-specific feature sets.

### 9.1 Commit

Required features:

```text
draft_fit
draft_stability
external_reply_pressure
semantic_completion
conflict
unresolved_relevance
full_slow_ready
```

Eligibility:

```text
elig(commit) = 1 only if DraftGrid has visible content
               and full_slow_ready when full_slow_required
               and conflict below hard ceiling
```

### 9.2 Stop

Stop is waiting/ending generation, not submitting an empty answer.

Required features:

```text
low_external_reply_pressure
fatigue_cost
no_viable_action_pressure
unresolved_relevance
teacher_request_pressure
```

Eligibility:

```text
elig(stop) = 0 if external_reply_pressure high and there is a viable commit or request_teacher action
```

### 9.3 Request teacher

Request teacher creates pressure and then must be expressed through DraftGrid.

Required features:

```text
uncertainty
conflict
novelty
source_trust_gap
teacher_availability
```

Eligibility:

```text
elig(request_teacher) = 1 if uncertainty/conflict high and no safe answer candidate dominates
```

Gate:

`G-20.6-v1d-End-01`: commit, stop, and request_teacher use different eligibility rules and are distinguishable in trace.

`G-20.6-v1d-End-02`: request_teacher cannot return a hardcoded phrase; it must create state pressure plus DraftGrid write actions.

---

## 10. Visual focus and SensoryCanvas closure

Let a focus sample at tick `t` be:

```text
f_t = (x_t, y_t, radius_t, source, confidence)
```

Local receptor extraction:

```text
v_t = V_local(image, f_t)
```

Sensory canvas update:

```text
C_{t+1}(p) =
    blend(C_t(p), image_patch(p), w = clarity(f_t, p) * confidence_t)
```

Where:

```text
clarity(f_t,p) = phi_min + (1 - phi_min) * exp(-dist(p, f_t)^2 / (2*sigma_t^2))
```

Coverage:

```text
coverage(t) = mean_p [C_t.confidence(p) > coverage_threshold]
```

Active vision score:

```text
EIG(f,t) =
    w_u * expected_uncertainty_reduction(f)
    + w_b * boundary_gain(f)
    + w_s * unresolved_slot_relevance(f)
    + w_g * teacher_guidance(f)
    - w_r * return_inhibition(f)
    - w_f * fatigue_cost(f)
```

`move_focus` candidates use `EIG` as a feature, not as a hidden recognizer.

Gate:

`G-20.6-v1d-Vision-01`: repeated focus has a traceable reason in one of the EIG terms.

`G-20.6-v1d-Vision-02`: coverage is non-decreasing within the same image unless the canvas is explicitly reset.

`G-20.6-v1d-Vision-03`: `R_sketch` input is `C_t`, not the original full image path.

---

## 11. Cooccurrence and memory update closure

For two active SA items `i,j` in the same packet/window:

```text
edge_strength_ij(t+1) =
    clip01(rho_edge * edge_strength_ij(t)
           + eta * active_i(t) * active_j(t) * source_trust(packet_source))
```

Diagnostic delta:

```text
delta_p(i,j) = P(j | i, source_scope) - P(j | not_i, source_scope)
```

Promotion:

```text
promote if edge_strength >= support_min
          and delta_p >= delta_p_min
          and source_trust >= trust_min
```

Feedback update:

```text
edge_strength <- clip01(edge_strength + reward_delta * contribution)
edge_strength <- clip01(edge_strength - punish_delta * contribution)
source_trust  <- clip01(source_trust + trust_reward - trust_penalty)
```

Import/uninstall:

```text
effective_strength = local_strength + sum(package_contribution_batch)
```

Uninstall removes only the target batch contribution; local strength remains.

Gate:

`G-20.6-v1d-Memory-01`: memory rows store local strength and package-batch contributions separately.

`G-20.6-v1d-Memory-02`: uninstall restores effective candidate distribution to pre-import snapshot within declared tolerance.

---

## 12. Cost-aware scheduler

Each optional stage `s` has expected value and cost:

```text
utility_s(t) = expected_information_gain_s(t)
               + expected_conflict_reduction_s(t)
               + unresolved_relevance_s(t)
               - fatigue_cost_s(t)

run stage s if utility_s(t) / estimated_cost_s(t) >= stage_threshold_s
```

Mandatory stages are not skipped:

- state update;
- minimal Slow watchdog;
- action candidate build;
- action competition;
- execution;
- compact event emission.

Gate:

`G-20.6-v1d-Scheduler-01`: skipped optional stages record `estimated_cost`, `utility`, and `skip_reason`.

`G-20.6-v1d-Scheduler-02`: a skipped stage cannot be required by the selected action's eligibility.

---

## 13. Formal invariants

These invariants must hold in unit tests.

1. **No precommit reply**: `final_reply is None` until `commit_reply`.
2. **Draft source**: committed text equals `DraftGrid.render_visible()` at commit tick.
3. **Bounded state**: all normalized state values are in `[0,1]`.
4. **Source boundary**: filename/path/evaluator labels never appear as semantic evidence.
5. **Fast boundary**: Fast cannot provide semantic binding alone.
6. **Slow gate**: if `full_slow_required`, commit eligibility is zero until full Slow runs.
7. **Canvas source**: perceived `R_sketch` derives from sensory canvas, not original thumbnail.
8. **Package rollback**: uninstall removes only batch contribution.
9. **UI mirror**: UI panels render persisted tick events; they do not alter action/candidate decisions.
10. **Performance truth**: stage timing is real measured time, not total time divided by tick count.

---

## 14. Implementation feasibility matrix

| Component | Current feasibility | Risk | Required first implementation move |
|---|---|---|---|
| StatePool | existing but additive/unbounded | medium | add bounded normalized wrapper or Phase20-specific state adapter |
| ActionCompetition | existing deterministic drive sorter | medium | extend to `ActionCandidate` score components and optional seeded sampling |
| DraftGrid | existing write/read basics | medium-high | add edit/delete/insert/revision/snapshot deltas |
| Phase20 runtime | old projected/whole-reply path remains | high | quarantine old path and create new `phase20_6_runtime.py` |
| Visual focus | local receptor primitives exist | medium | build focus-only adapter; forbid whole-image label path |
| R_sketch | design exists, quality uncertain | high | implement minimal sensory-canvas sketch first; gate honestly |
| Zvec recall | Phase19.9 exists | medium | integrate only as Slow-C accelerator with fallback metrics |
| Memory packages | existing package work | medium | add per-batch contribution ledger and tombstones |
| UI | current workbench partly fake | high | rebuild panels from persisted RuntimeTickEvent after backend passes |
| TTS/recording/canvas | peripheral | low-medium | defer until core runtime gates pass |

### 14.1 Important implementation correction

Do not mutate the old `Phase20MultimodalSession.turn` path in-place until the new runtime passes substrate tests. Safer approach:

1. create a new runtime entry, e.g. `phase20_6_runtime.py`;
2. make old workbench able to call it under a new flag or route;
3. once substrate gates pass, switch `/api/phase20/turn` to the new runtime;
4. remove/quarantine old projection paths and add grep redlines.

This avoids half-editing old projected code into a hybrid that is hard to audit.

---

## 15. Final go/no-go

Go if:

1. v1 + v1b + v1c + v1d are accepted as the active design set;
2. the first landing target is substrate tests, not UI polish;
3. implementation may add formal wrappers/adapters before replacing the old runtime;
4. performance target for first landing is P1, not unproven P2/P3;
5. R_sketch quality is gated honestly, with no visual overclaim.

No-go if:

1. any whole-reply, whole-image-label, or teacher-hit route is allowed to remain in the new Phase20.6 runtime;
2. Fast is allowed to bind semantic text without current-state/Slow evidence;
3. UI is allowed to synthesize tick traces;
4. action scores remain unnormalized and action-specific shortcuts decide commit/stop;
5. current code is patched in-place without a clean new runtime boundary.

