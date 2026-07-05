# APV3 Phase 19 v1a Adversarial Review - Final Micro Errata

Date: 2026-06-19
Reviewer: Codex
Scope: `Errata_Phase19_v1a_AnthropomorphicAndEngineeringClosure_20260619.md`

## Verdict

v1a resolves the major philosophical and mathematical issues from the previous review. It correctly moves the standard from "perfect recognizer" to "anthropomorphic perception, imagination, confidence, error, and correction".

I do not see a new architecture-level blocker. The system can proceed after a small v1b micro-errata that closes six implementation-sensitive seams.

## What Is Now Strong

1. The split between `sensory_sketch` and `prototype_imagination` is the right correction. It permits human-like imagination without source confusion.
2. V0/A0 high-bandwidth channels make perception more human-like. The goal is no longer pixel-perfect truth; it is enough spatial/acoustic richness that AP's mistakes are cue-based rather than metadata-based.
3. The dimension math is now closed: visual 7807, audio 20179.
4. The confidence formula fixes the earlier non-human behavior:
   - weak cue saturation is blocked,
   - few strong cues can create a strong prototype pull,
   - top1=top2 no longer gives a half-confident margin,
   - OOD lowers tier rather than forcing no-call.
5. Error taxonomy is aligned with the AP philosophy: human-plausible errors can exist, non-human artifact errors and source confusion are red lines.
6. Source-aware feedback is now explicit, which is essential for "wrong but human" learning.

## Micro Issue M1 - `Conf` Is A Tier Function And A Score At The Same Time

v1a defines:

```text
Conf(c|x) = TierMap(Π·Γ·Q, μ, ν)
```

But `TierMap` returns a decision tier, while later gates need numeric confidence decrease, Recall scoring, and source-specific feedback deltas.

Required v1b patch:

```text
raw_confidence(c|x) = Π(c|x) · Γ(c|x) · Q(x) · μ(c|x)
decision_tier = TierMap(raw_confidence, novelty_tension)
```

Keep both fields:

- `confidence_score`: numeric in `[0,1]`
- `decision_tier`: `firm | soft | ambig | no_call`

This prevents tests from comparing a text tier as if it were a scalar.

## Micro Issue M2 - Source-Aware Feedback Cannot Require An Oracle In Natural Use

v1a says user correction must identify whether the error source was `PERCEIVED`, `IMAGINED`, or `INFERRED`. In real dialogue, the user usually only says "不对,这是橙子", not "your imagined prototype path was wrong".

For tests, source labels can be used as audit annotations. For runtime, source attribution must be inferred from contribution weights.

Required v1b patch:

```text
source_credit(source)
  = contribution_to_decision(source)
    × source_confidence(source)
    × recency(source)

negative_feedback_delta(source)
  ∝ source_credit(source) / sum(source_credit)
```

If an evaluator explicitly marks source, that can override for audit tests, but ordinary user correction should still work without oracle help.

## Micro Issue M3 - Novelty Must Separate Object Novelty From Background Novelty

`ν(x) = 1 - exp(-γ · min d(f_x, p_c))` over the full 7807-dimensional vector risks treating background, lighting, crop, and focus-patch changes as object novelty.

Humans often ignore background if the object cues are clear. If novelty is dominated by V0 raw tiles, a real apple on a tree may be downgraded too much compared with a clean card.

Required v1b patch:

Split novelty:

```text
ν_object = novelty over object mask + diagnostic channels
ν_context = novelty over background/layout channels
ν = max(ν_object, context_weight · ν_context)
```

Use `ν_object` for decision tier. Use `ν_context` mainly to raise curiosity / re-fixation pressure, not to suppress object guess directly.

## Micro Issue M4 - Error Taxonomy Needs A Non-Fudge Operational Rule

The taxonomy is philosophically right, but "human-plausible" can become subjective if not operationalized.

Required v1b patch:

Each error taxonomy row must be assigned by one of two allowed routes:

1. Blind external evaluator:
   - evaluator sees image and AP output,
   - evaluator does not see filename or hidden label,
   - evaluator marks whether the error is human-plausible.
2. Cue-based audit rule:
   - strong misleading cues exist,
   - competitor gap was small or novelty was high,
   - no metadata/label source was accessed.

The implementation must not set `human_plausible_*` merely because the predicted label was wrong.

## Micro Issue M5 - V0/A0 Need Fast Path vs Audit Path

7807 visual dimensions and 20179 audio dimensions are fine for offline audit, but the long-term target has continuous ticks near 0.1s. Full extraction and rendering every tick may be too heavy, especially once Web replay, inner picture, audio, and dialogue all run together.

Required v1b patch:

Define two paths:

- `receptor_fast_path`: per tick, bounded, no rendering by default, updates compact traces.
- `reconstruction_audit_path`: on demand or replay, full V0/A0 extraction and render.

Add latency gates:

- visual fast path p95 under one tick budget on 12-image audit set,
- reconstruction path bounded and queued,
- rendered artifacts never block dialogue tick loop.

## Micro Issue M6 - 19.3a Split Is Too Small Unless It Uses Stratified/Rotating Evaluation

The user set has only 12 images across apple/orange/banana plus difficult variants. A fixed 7 train / 5 held-out split can accidentally starve one class or make nearest-negative diagnosticity unstable.

Required v1b patch:

- Use stratified split with at least 2 train images per core class when available.
- Use rotating leave-one-out / k-fold diagnostic traces instead of a single split when sample count is this small.
- Report results as diagnostic, not stable benchmark.
- Do not fit `h0`, λ, or diagnosticity on the held-out fold.

## Micro Issue M7 - Recall Score Needs Normalization And Leak Boundary

The retrieval formula is useful:

```text
Π + α_part·part_overlap + α_shape·shape_overlap + α_cooccur·learned_cooccurrence - α_conflict·source_conflict
```

But additive scores can exceed a stable range, and `learned_cooccurrence(c,x)` must be guaranteed to come only from AP training evidence, not evaluator labels.

Required v1b patch:

- Normalize recall score to `[0,1]`.
- Clamp or sigmoid after weighted sum.
- Mark `learned_cooccurrence_source = training_sdpl_only`.
- Redline: held-out evaluator sidecar cannot affect `learned_cooccurrence`.

## Final Recommendation

No more large design rewrite is needed.

Ask Claude for a short `v1b Micro Errata` that fixes:

1. numeric confidence vs tier separation,
2. non-oracle source-aware feedback,
3. object novelty vs context novelty,
4. operational taxonomy assignment,
5. fast path vs audit path,
6. stratified/k-fold tiny-set evaluation,
7. normalized no-leak recall score.

After that, Codex can start Phase 19.0 implementation with the usual cycle:

`设计 -> 审查完善 -> 通过落地 -> 严谨验收测试 -> 最终汇总报告`.

The design is now aligned with the AP goal: not an absolutely correct machine, but a system that sees, guesses, imagines, errs, and learns in a human-like, source-aware way.

