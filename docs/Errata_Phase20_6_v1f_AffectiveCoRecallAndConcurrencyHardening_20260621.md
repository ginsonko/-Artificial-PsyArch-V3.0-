# APV3.0 Phase 20.6 v1f Errata - Affective Co-Recall, Empathy Without Shortcuts, and Final Hardening

Date: 2026-06-21
Status: Micro errata. This document amends Phase 20.6 v1 + v1b + v1c + v1d + v1e.
Scope: design/review only. No runtime implementation is claimed here.

---

## 0. Why v1f exists

Claude v1e correctly found five real omissions:

1. StateItem schema compatibility;
2. cognitive pressure formula compatibility;
3. affect/empathy path;
4. sensory canvas lifecycle;
5. multi-session concurrency.

This v1f accepts those omissions as real, but hardens three places where v1e can still drift away from AP philosophy:

1. empathy must not become a separate affect module or emotion keyword route;
2. v1e conflates `U` with unresolved carry, while v1d used `U` as uncertainty;
3. concurrency and canvas lifecycle need profile/source boundaries to avoid cross-session leakage.

---

## 1. Verdict on v1e

| v1e item | Verdict | Required correction |
|---|---|---|
| F1 StateItem compatibility | Correct | Prefer adapter/helper over editing core dataclass with properties |
| F2 P formula conflict | Correct | Do not overwrite legacy `cognitive_pressure`; compute Phase20 runtime pressure separately |
| F3 affect/empathy | Direction correct, mechanism too module-like | Replace `compute_affect_modulator` with AP-native affective co-recall features |
| F4 canvas lifecycle | Correct | Add discourse referent/source boundary: current vs remembered |
| F5 multi-session concurrency | Correct | Add `profile_id`, WAL/busy timeout/process-boundary declaration |

After v1f, no new architecture blocker remains.

---

## 2. F3 correction: empathy is co-recall, not a special module

The user clarified the key principle:

> AP can recognize another person's sadness and recall its own sadness memories because both are active/remembered SA structures around "sadness"; there is no need for a separate empathy mechanism.

Therefore Phase 20.6 must not implement empathy as:

```python
if current_affect in ("sad", "anxious"):
    choose empathy_template()
```

or:

```python
score *= compute_affect_modulator(...)
```

if that function parses affect labels and routes actions.

Correct framing:

> Affect, self-memory, other-observed state, social response, and expression style are all first-class SA evidence. Empathy emerges when current other-affect SA recalls self/other affect memories and learned response patterns through the same Slow/Fast candidate protocol.

---

## 3. Affective SA representation

No new "empathy module" is needed. Add only source-tagged SA families and normalized features.

### 3.1 SA families

```text
affect_observed_other      # evidence about user's apparent state
affect_self_memory         # AP's own past affective episode memory
affect_expression_pattern  # learned response/expression pattern
social_need_pressure       # pressure to respond with care/clarify/help
relationship_context       # source/recency/familiarity, if learned
```

These are ordinary state-pool items:

```text
family: "affect_observed_other"
channel_signature: ("affect", "other_observed")
source: "user_text" | "user_audio" | "teacher_event" | "correction" | "style_corpus_import"
metadata:
  affect_key: opaque id, not parsed as semantic text
  source_confidence: [0,1]
  evidence_refs: packet ids
```

### 3.2 Source boundary

Self and other affect must remain distinct:

```text
OTHER_OBSERVED != SELF_EPISODIC != IMAGINED_PERSPECTIVE
```

AP may recall a self sadness-like memory when it observes the user may be sad, but the trace must show:

```text
recalled_self_memory_source = SELF_EPISODIC
current_user_state_source = OTHER_OBSERVED
```

It must not collapse into "I know exactly how the user feels."

### Gates

`G-20.6-v1f-Affect-01`: current user-affect SA and recalled self-affect memory carry different source tags.

`G-20.6-v1f-Affect-02`: no runtime code parses affect key strings such as `"sad"` or `"anxious"` to choose actions.

---

## 4. Affective co-recall math

Let `O_t` be the set of current other-observed affect SA items.
Let `M` be candidate affect memories from Slow recall.

### 4.1 Other-affect evidence

```text
other_affect_strength(k,t) =
    noisy_or_topm({
        A_i(t) * T_i(t) * evidence_fit(i,k)
        for i in O_t
    }, m)
```

`k` is an opaque affect key. `evidence_fit` comes from learned cooccurrence/markers, not keyword rules.

### 4.2 Empathy resonance

```text
empathy_resonance(m,t) =
    sim_affect(O_t, m)
    * source_trust(m)
    * self_other_boundary(m)
    * memory_clarity(m)
```

Where:

```text
self_other_boundary = 1.0 if source tags remain distinct
                    = 0.0 if the candidate confuses self and other source
```

### 4.3 Care pressure

```text
care_pressure(t) =
    noisy_or_topm({
        empathy_resonance(m,t),
        direct_user_distress_evidence(t),
        unresolved_social_need(t)
    }, m)
    - overclaim_risk(t)
```

clipped to `[0,1]`.

### 4.4 Candidate feature integration

Do not multiply final score by a separate affect modulator. Instead add normalized v1d action-drive features:

```text
phi_affect(c,t) = {
  affective_fit,
  care_pressure,
  overclaim_risk,
  task_relevance,
  source_boundary_fit,
  expression_style_fit
}
```

Then v1d's single action drive equation decides:

```text
drive(a,t) = elig(a,t) * sigmoid(raw_drive(a,t))
```

### Gates

`G-20.6-v1f-Affect-03`: affect changes action candidates only through normalized `score_components`, not by a separate final multiplier.

`G-20.6-v1f-Affect-04`: empathy-related features are auditable in selected/rejected action candidates.

---

## 5. Affect buckets are opaque evidence, not semantic labels

Phase 16 `affect_bucket` can be used as a source-tagged grouping key for expression evidence, but runtime must not parse its text.

Allowed:

```text
expression_pattern_sa --cooccurred_with--> affect_key_7f3a
current affect evidence recalls affect_key_7f3a
write_cell candidates from expression_pattern_sa gain expression_style_fit
```

Forbidden:

```python
if affect_bucket == "warm": ...
if current_affect == "sad": ...
if user_text contains "难过": ...
```

`warm`, `calm`, `curious`, etc. may be UI/debug labels, not runtime decision labels.

### Gates

`G-20.6-v1f-Affect-05`: grep/redline test bans runtime branches on affect bucket literal strings.

`G-20.6-v1f-Affect-06`: affect-bucket labels may appear in fixtures/docs/UI audit, but selected action evidence must cite opaque affect SA ids and cooccurrence edges.

---

## 6. Empathy behavior tests

### 6.1 Positive co-recall test

Teaching:

```text
Turn A: user expresses a distress-like state through phrase P1.
Teacher response demonstrates a gentle response pattern R1.
```

Probe:

```text
User later expresses different phrase P2 that recalls the same affect SA through cooccurrence, not exact words.
```

Expected:

1. AP recalls affect-related response pattern candidates;
2. AP does not require exact keyword match;
3. DraftGrid writes response through normal action competition;
4. trace shows other-affect evidence + recalled expression pattern.

### 6.2 Negative keyword trap

Input contains a word previously associated with distress but in a non-distress context, for example as an object name, quote, or discussion topic.

Expected:

1. affect evidence remains low or uncertain;
2. AP may ask/clarify if uncertain;
3. no automatic empathy response.

### 6.3 Image plus distress test

User says a distress-like sentence and also asks a concrete image question.

Expected:

1. AP must not blindly suppress visual answer candidates;
2. action competition may choose a blended pattern: brief care acknowledgement + answer, if learned;
3. if uncertainty is high, AP asks a clarifying/teacher-request style response through DraftGrid.

This corrects v1e's hard "distress -> demote counting/object explanation" rule. Humans often still answer the requested task, just with warmer framing.

### 6.4 Self-other boundary test

AP recalls a self-affect memory while responding to user distress.

Expected:

1. trace shows self memory as `SELF_EPISODIC`;
2. response does not claim the user's exact internal state;
3. overclaiming responses receive lower `source_boundary_fit`.

---

## 7. F1/F2 correction: use Phase20 state view adapter

v1e says "do not add StateItem dataclass fields", but its code snippet adds properties into `StateItem`. That is safer than adding dataclass fields, but still edits a core class.

Safer implementation:

```python
@dataclass(frozen=True)
class Phase20StateFeatureView:
    item: StateItem

    @property
    def trust(self) -> float:
        return clip01(float(self.item.metadata.get("phase20_6_trust_value", 0.5)))

    @property
    def uncertainty(self) -> float:
        return clip01(float(self.item.metadata.get("phase20_6_uncertainty_value", 0.5)))

    @property
    def unresolved_carry(self) -> float:
        return clip01(float(self.item.metadata.get("phase20_6_unresolved_carry", 0.0)))
```

Important correction:

```text
T = trust
U = uncertainty
unresolved_carry is separate
```

v1e accidentally maps `U` to unresolved carry. v1d used `U` as uncertainty. Implementation must not conflate them.

### Runtime pressure

Do not overwrite legacy `item.cognitive_pressure = R - V`.

Compute Phase20 pressure separately:

```text
runtime_pressure_i(t+1) =
    clip01(max(
        legacy_pressure_i(t+1),
        unresolved_floor_i(t),
        rho_P * runtime_pressure_i(t)
        + mismatch_i(t)
        + unclosed_i(t)
        - release_i(t)
    ))
```

Store this as a Phase20 event/adapter value:

```text
score_components["runtime_pressure"]
RuntimeTickEvent.state_pool_top12[].runtime_pressure
metadata["phase20_6_runtime_pressure"]
```

### Gates

`G-20.6-v1f-State-01`: `StateItem` dataclass source is unchanged except if a narrowly reviewed helper import is unavoidable.

`G-20.6-v1f-State-02`: `trust`, `uncertainty`, and `unresolved_carry` are three separate values.

`G-20.6-v1f-State-03`: legacy `cognitive_pressure` behavior remains `R - V`; Phase20 runtime pressure is separate and auditable.

---

## 8. F4 correction: canvas lifecycle needs discourse source boundary

v1e's ring buffer is right, but remembered canvas must never leak into perceived current-image evidence.

### 8.1 Visual context fields

Every visual tick must carry:

```text
visual_context_id
current_image_hash
canvas_source: PERCEIVED_CURRENT | REMEMBERED_PREVIOUS | EMPTY
referent_status: current_image | previous_image | no_image
```

### 8.2 Rules

1. New image turn: only `PERCEIVED_CURRENT` participates in current visual perception.
2. Same image follow-up: previous canvas may remain `PERCEIVED_CURRENT` if image hash matches.
3. No image turn: stale canvas may be recalled only as `REMEMBERED_PREVIOUS`.
4. User reference like "刚才那张" can raise remembered visual relevance.
5. User asks "这张图" without current image: AP should treat reference as uncertain or ask clarification.

### Gates

`G-20.6-v1f-Canvas-01`: stale canvas never has source `PERCEIVED_CURRENT`.

`G-20.6-v1f-Canvas-02`: no-image turn using remembered overlay records `REMEMBERED_PREVIOUS` in RuntimeTickEvent.

`G-20.6-v1f-Canvas-03`: new image turn cannot cite old canvas as visual evidence for current image answer.

---

## 9. F5 correction: concurrency is profile-scoped

v1e says all sessions share Fast/Slow store because they are the same AP. That is correct only inside the same AP profile.

Add:

```text
profile_id
session_id
turn_id
```

Rules:

1. sessions under the same `profile_id` share long-term Fast/Slow memory;
2. sessions under different `profile_id` do not share memory;
3. test sandboxes should use isolated `profile_id` to avoid contaminating the main AP;
4. imported packages are installed per profile unless explicitly global.

### 9.1 SQLite concurrency

Thread locks are not enough if the server later becomes multi-process.

Minimum requirements:

```text
PRAGMA journal_mode=WAL
PRAGMA busy_timeout = 5000
write transactions use BEGIN IMMEDIATE
single-writer lock per DB path inside process
documented fallback: multi-process deployment requires file/process lock or one runtime worker
```

### Gates

`G-20.6-v1f-Concurrency-01`: memory rows include `profile_id`.

`G-20.6-v1f-Concurrency-02`: same-profile sessions can share learned memory; different-profile sessions cannot.

`G-20.6-v1f-Concurrency-03`: SQLite connection setup proves WAL and busy_timeout are enabled.

`G-20.6-v1f-Concurrency-04`: if multi-process locking is not implemented, final report explicitly says Phase20.6 supports single-process local workbench only.

---

## 10. Affect memory privacy and package export

Affective/relationship memories are more sensitive than ordinary object cooccurrence.

Default package export must exclude:

1. raw user affect text;
2. relationship-context rows;
3. self/other affect episodes;
4. audio clips that may reveal emotion;
5. private session transcripts.

User may explicitly include selected affect memories, but the package preview must show them clearly.

### Gates

`G-20.6-v1f-Privacy-01`: affect/relationship memory export default is off.

`G-20.6-v1f-Privacy-02`: package preview displays affect-memory count and requires explicit include.

---

## 11. Updated no-go conditions

Do not implement Phase 20.6 if any of these are still allowed:

1. runtime branches on affect literal strings such as `"sad"`, `"anxious"`, `"warm"`;
2. empathy is implemented as a separate response module or template table;
3. Fast/Slow candidates bypass v1d action-drive features for affect;
4. `U` is used for unresolved carry instead of uncertainty;
5. legacy `StateItem.cognitive_pressure` is overwritten by Phase20 runtime pressure;
6. stale canvas can masquerade as current perception;
7. sessions from different profiles share memory without explicit import/export;
8. multi-process concurrency is implied but not implemented/tested.

---

## 12. Final implementation order addition

Insert before v1e Stage 2:

```text
Stage 1.5:
  - Phase20StateFeatureView adapter
  - runtime_pressure separate from legacy cognitive_pressure
  - affective SA co-recall feature extraction
  - profile_id/session_id/turn_id boundary
  - canvas source tags
```

Then Stage 2 can implement Fast/Slow/action scoring with affective co-recall as ordinary normalized features.

---

## 13. Final verdict after v1f

v1e's five omissions are real. v1f corrects the only risky part: affect/empathy must emerge through AP-native co-recall rather than a special affect route.

With v1 + v1b + v1c + v1d + v1e + v1f read together:

- no known architecture-level blocker remains;
- implementation should begin with a new `phase20_6_runtime.py` boundary;
- old projected Phase20 paths must be quarantined before UI work;
- empathy tests must prove co-recall, not keyword response.

