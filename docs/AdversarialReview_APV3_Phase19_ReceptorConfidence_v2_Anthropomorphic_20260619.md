# APV3 Phase 19 Adversarial Review v2 - Anthropomorphic Standard

Date: 2026-06-19
Reviewer: Codex
Status: Supersedes the parts of v1 that judged the design by machine-correctness standards rather than anthropomorphic plausibility.

## Corrected Review Principle

The AP target is not an always-correct recognizer. It is an anthropomorphic cognitive system. Therefore a design problem is not "AP might be wrong"; a design problem is:

1. AP makes an error that humans would not plausibly make from the same perceptual evidence.
2. AP is confident for a non-human reason, such as hidden labels, filenames, metadata, or test-set routing.
3. AP cannot later distinguish perception, imagination, hearsay, memory, and correction, so an imagined mistake contaminates perceived reality.
4. AP's error cannot be corrected by normal experience, reward/punishment, surprise, or source-aware learning.
5. AP's confidence does not feel psychologically plausible: it says "firm" where a human would say "looks like", or says "unknown" where a human would naturally make a tentative prototype guess.

Under this standard, human-like mistakes are not only allowed; they are desirable, as long as they are bounded, source-aware, and learnable.

## Revised Verdict

Claude's Phase 19 direction is substantially right. The design should proceed after a v1a anthropomorphic errata, not be blocked by a demand for perfect reconstruction or perfect visual correctness.

The strongest idea is exactly the user's point: AP should be allowed to form schematic, sometimes wrong inner pictures from partial cues, because humans do this. The system should not be a sterile classifier that refuses to imagine.

However, the design still needs correction where its mistakes would be non-human or where its evidence sources would be confused.

## Corrections To My v1 Review

### v1 B1 Was Too Strict

I said reconstruction from summary features is not an information sufficiency proof. That is technically true, but it was the wrong primary criticism.

Human perception and imagination are not pixel-perfect reconstruction. A human can see a few cues, fill in a prototypical apple, and later discover it was wrong. That is not a defect; it is a key part of拟人 cognition.

Corrected stance:
- It is acceptable, even desirable, that reconstruction is schematic and prototype-colored.
- It should be called a "perceptual/imaginal sketch audit", not a proof of objective correctness.
- The real gate is whether the sketch is psychologically plausible from available cues, and whether AP knows whether it is perceived or imagined.

Still required:
- Keep source separation: `sensory_sketch` vs `prototype_imagination`.
- Do not let a prototype imagination count as direct perception.
- Do not use evaluator labels or filenames to build the sketch.

### v1 B4 Was Too Correctness-Biased

I said 19.3 must split real-photo held-out and clean-card transfer before making claims. This is still useful experimentally, but it should not be framed as "otherwise invalid".

Humans often learn from simplified drawings/cards and transfer imperfectly to real photos. That developmental path is plausible. A clean-card-to-real-photo failure may be a meaningful anthropomorphic limitation, not a blocker.

Corrected stance:
- Keep clean-card to real-photo transfer as a valid developmental test.
- Add real-photo train/held-out as a diagnostic companion, not a replacement.
- Report errors as human-like or non-human-like, not merely correct/incorrect.

## BLOCKER B1 - Source Confusion Would Create Non-Human Psychosis, Not Human Imagination

Human imagination is allowed to be wrong, but healthy human cognition usually has some source feeling: "I saw it", "I imagined it", "I remember it", "someone told me".

Phase 19's inner picture design must not blur these.

If AP sees a vague green-orange photo and internally renders a bright orange prototype, that is human-like. If AP then treats that rendered prototype as if it was actually perceived, that becomes source confusion.

Required v1a patch:
- Every visual trace must carry `epistemic_source`:
  - `PERCEIVED_SENSORY_SKETCH`
  - `IMAGINED_PROTOTYPE_SKETCH`
  - `REMEMBERED_SKETCH`
  - `INFERRED_SKETCH`
- The inner picture renderer may use prototypes, but the audit display must show the source.
- Confidence updates must distinguish:
  - "the photo had orange-like cues"
  - "my mind filled in a typical orange"
- Feedback on a prototype hallucination should weaken the imagined-source action path without destroying the perceived-source association.

This matches the earlier SDPL/source-marker philosophy and preserves human-like imagination without letting AP live inside unchecked fantasy.

## BLOCKER B2 - Thin Summary Channels Can Produce Non-Human Errors

The issue is not that thin features are "not correct enough". The issue is that they may produce errors humans would not make.

Example: two images with the same color histogram but completely different spatial layout may look identical to a summary-feature AP, while a human would instantly distinguish them. That is not a human-like mistake; it is a sensor bottleneck artifact.

Required v1a patch:
- Add a foveated spatial trace, but justify it anthropomorphically:
  - humans have high-bandwidth spatial perception at attention focus,
  - lower fidelity in periphery,
  - active re-fixation over multiple ticks.
- It does not need pixel-perfect storage.
- It does need enough local spatial structure that AP's mistakes are cue-based rather than histogram-based.

Recommended channel:
- `V0 Foveated Spatial Sketch`
  - low-resolution color/luminance grid,
  - edge grid,
  - focus-centered high-resolution patch,
  - no labels,
  - decayable short-term sensory memory.

This makes AP more human-like, not merely more accurate.

## BLOCKER B3 - Current Confidence Formula Is Not Yet Human-Like Enough

The formula's goal is right, but some details can produce psychologically unnatural confidence.

### Problem 1: Noisy-OR over many weak cues can create false firmness

Humans can make guesses from partial cues, but many weak, non-diagnostic cues should usually create "looks like" or "maybe", not firm certainty.

Patch:
- Use `active diagnostic cues`, not all channels.
- Weak cues can raise familiarity, but should not directly create firm confidence.
- Add a separate `prototype_pull` term for human-like "it reminds me of X".

### Problem 2: Consistency should not punish few strong cues

Humans often need only two or three strong cues: long curved yellow form -> banana; round orange surface -> orange.

Patch:
- Compute consistency over active cues only.
- If there are 2-4 strong cues and no strong competitor, consistency can be high.
- If there is only one strong cue, allow soft but not firm unless prior familiarity is very high.

### Problem 3: OOD should not always force no-call

Humans often say "像是 X" for unfamiliar variants. A green orange should not necessarily become "unknown"; it should often become "像是橙子,但不太确定".

Patch:
- OOD should mostly lower tier: firm -> soft -> ambig.
- Only extreme OOD with no coherent prototype pull should become no_call.
- OOD should also trigger teacher-seeking or exploratory attention, not only suppress output.

Suggested anthropomorphic formula:

```text
prototype_pull(c|x)
  = noisy_or over active diagnostic cue matches

coherence(c|x)
  = agreement among active cues + cross-scale stability

competitor_gap(c|x)
  = how much stronger c feels than nearest rival

source_quality(x)
  = focus clarity, occlusion, segmentation confidence, sensory freshness

novelty_tension(x)
  = unfamiliarity signal that lowers tier but can coexist with prototype pull

subjective_confidence
  = tier_map(
      prototype_pull * coherence * source_quality,
      competitor_gap,
      novelty_tension
    )
```

This allows human-like outputs:
- strong cues + no rival -> firm or soft,
- atypical color + strong shape -> soft,
- rival close -> ambig,
- no coherent cues -> no_call,
- misleading strong cues -> possible wrong soft/firm, but correction should adjust future source-aware weights.

## SERIOUS S1 - Wrong Answers Should Be Classified By Human Plausibility, Not Only Accuracy

The gate "no firm + wrong" from v1 was too machine-like. Humans can be firmly wrong under strong misleading cues. The better gate is error taxonomy.

Add audit categories:

- `human_plausible_soft_error`: AP says "像是 X"; wrong, but cues justify the guess.
- `human_plausible_illusion_error`: AP says firm X; wrong, but image has strong misleading cues that would plausibly fool a person.
- `nonhuman_artifact_error`: AP's answer is caused by filename/label/metadata, or ignores obvious visual cues.
- `source_confusion_error`: AP confuses imagined prototype with perceived image.
- `uncertainty_underreach`: AP says no_call where most humans would make a natural tentative guess.

Acceptance should allow some human-plausible errors and block nonhuman artifact/source-confusion errors.

Suggested Phase 19.3 gate:
- `nonhuman_artifact_error = 0`
- `source_confusion_error = 0`
- strong typical images: mostly firm/soft
- atypical variants: soft/ambig preferred
- human-plausible wrong soft allowed and reported
- firm wrong allowed only if tagged `illusion_like` and capped
- after correction feedback, repeated same image should reduce wrong confidence

## SERIOUS S2 - Reconstruction Should Evaluate Human-Readable Inner Experience, Not Objective Truth

For AP's "inner picture", the right question is not "does it match the original photo exactly?" The right question is:

1. Can a human observer understand what AP seems to be imagining?
2. Does the sketch correspond to the AP's current cue evidence?
3. Is it source-marked as perception, memory, inference, or imagination?
4. Does feedback change future sketches in a plausible way?

Therefore SSIM is secondary. A low-SSIM sketch can still be cognitively valid if it reveals AP's inner prototype. A high-SSIM sketch can be invalid if it secretly uses the original image or a label-conditioned template.

Patch:
- Keep SSIM/feature metrics for engineering diagnostics.
- Add `inner_picture_legibility` and `cue_fidelity`:
  - legibility: can a person tell what AP is imagining?
  - cue_fidelity: do visible cue elements correspond to actual observed cues?
- Show both sensory sketch and prototype imagination when possible.

## SERIOUS S3 - Similar Object Recall Should Be Cue-Based And Allow Family Resemblance

The user asked whether channels can really recall similar other objects. Under the anthropomorphic standard, similar-object recall is not exact classification. It is family resemblance.

Mathematically, AP should be able to retrieve:
- same concept prototype,
- nearest sibling concepts,
- partial shared features,
- and uncertainty when the rival is close.

Patch:
- Use active cue overlap to retrieve candidates:

```text
recall_score(c)
  = prototype_pull(c)
  + shared_part_overlap(c)
  + shared_shape_overlap(c)
  + learned_cooccurrence_support(c)
  - source_conflict_penalty(c)
```

- Report top-k, not only top-1.
- For green orange, a human-like AP may retrieve orange, apple, and "round fruit" together.
- The output should be able to say "像是橙子" or "可能是橙子,也可能是苹果/别的圆水果" depending on cue gap.

This is closer to human cognition than a single hard label.

## SERIOUS S4 - Audio Inner Voice Should Be Schematic, Not A Fake TTS Promise

Human inner speech is often schematic. It is not necessarily a high-fidelity external voice.

So Phase 19.1 should not be judged by whether it reconstructs perfect speech. But it should be judged by whether it produces a human-interpretable auditory image:
- rhythm,
- rough pitch contour,
- intensity,
- timbre family,
- speech-like vs noise-like feeling,
- narrative sequence timing.

Patch:
- Rename early output to `inner_voice_sketch`.
- Keep STOI only for speech-like samples.
- For non-speech, use perceptual family metrics and human ear legibility.
- Do not require full TTS before there is a learned vocal/action pathway.

## Revised Phase 19 v1a Recommendations

1. Keep Claude's Phase 19 sequence: 19.0 -> 19.2 -> 19.3 -> 19.1 is reasonable.
2. Add V0 foveated spatial sketch for human-like perception, not machine-perfect correctness.
3. Make reconstruction a dual-use sketch renderer:
   - sensory sketch,
   - prototype imagination.
4. Source-mark every rendered inner picture/voice.
5. Rewrite confidence around active diagnostic cues, prototype pull, competitor gap, quality, and novelty tension.
6. Let OOD lower confidence tier instead of forcing no_call.
7. Replace pure accuracy gates with human-plausibility error taxonomy.
8. Keep label/filename leakage at zero; this is still an absolute red line because humans do not see hidden metadata.
9. Add feedback tests: after AP makes a plausible but wrong guess and receives correction, future confidence changes source-specifically.

## Final Assessment Under Anthropomorphic Standard

The final picture is logically achievable.

Claude's design is not wrong because it allows prototype hallucination; that is actually one of the most human-like parts. The real requirement is that AP must know, or gradually learn to feel, whether the content came from perception or imagination, and must let feedback tune those pathways separately.

So the next design errata should not make AP more like a perfect recognizer. It should make AP's perception, imagination, confidence, and mistakes more human:

- richer foveated perception,
- schematic but readable inner imagery,
- tentative prototype guesses,
- plausible illusions,
- source-aware correction,
- and no hidden metadata shortcuts.

