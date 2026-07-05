# APV3 Phase 19 Adversarial Review - Receptor Enrichment, Reconstruction, Confidence

Date: 2026-06-19
Reviewer: Codex
Scope:
- `Design_APV3.0_Phase19_0_VisualSensorEnrichmentAndReconstructionAudit_v1_20260619.md`
- `Design_APV3.0_Phase19_1_AudioSensorEnrichmentAndInnerVoice_v1_20260619.md`
- `Design_APV3.0_Phase19_2_HumanLikeConfidenceFormula_v1_20260619.md`
- `Design_APV3.0_Phase19_3_VisualOnlyProbeRebuilt_v1_20260619.md`
- `Roadmap_APV3.0_Phase19_v1_20260619.md`

## One-Line Verdict

Phase 19 is directionally right and should replace the thin Phase 18.2 visual-only probe, but the current v1 design is not ready for implementation. It needs a v1a errata because reconstruction, confidence calibration, and the 19.3 generalization gate currently overclaim what the mathematics can prove.

## What Is Strong

1. The diagnosis is correct: Phase 18.1 failed because the probe was label-mediated and the sensory channel was too thin.
2. Separating receptor enrichment, reconstruction audit, human-like confidence, and rebuilt visual-only probe is the right decomposition.
3. Keeping filenames and labels evaluator-side only is essential and should be preserved.
4. Treating `inner_picture` / `inner_voice` as audit-rendered products rather than cognitive labels is the right privacy and red-line direction.
5. The psychological direction of the confidence formula is right: humans often rely on a few diagnostic cues plus lack of competitors, not full global similarity.

## BLOCKER B1 - Reconstruction From Summary Features Is Not An Information Sufficiency Proof

Phase 19.0 currently says the 9-channel feature vector should reconstruct a 64x64 image with SSIM >= 0.55 and that failure means the channel set is insufficient.

The problem: V1-V9 are mostly summary statistics. Many different images can share similar RGB/HSV histograms, HOG bins, LBP histograms, radial gradients, and rough shape descriptors. A reconstruction operator can therefore only generate a plausible image, not recover the actual input. If it uses a prototype codebook, it may hallucinate a canonical apple/banana/orange and pass human legibility while still losing the original image information.

This would create a new false positive: "the reconstructed image looks like an orange" may only mean "the renderer guessed an orange prototype", not "the receptor preserved enough visual information".

Required fix:
- Rename the gate from "information-theoretic sufficiency proof" to "sensory bottleneck reconstruction audit".
- Add a non-semantic retinal channel before V1-V9:
  - `V0 Foveated Retinal Pyramid`: low-resolution RGB/Lab tiles, edge tiles, and focus-centered high-resolution patches.
  - It must be label-free and raw-percept-like, not a semantic feature.
  - It is the primary carrier for reconstructability.
- Distinguish two modes:
  - `sensory_reconstruction`: reconstruct from the actual input's receptor traces; used for audit.
  - `prototype_imagination`: render from category/prototype traces; used for inner picture.
- The two modes may share primitive renderers, but audit pass must never use category prototype, filename, evaluator label, or class-conditioned codebook lookup.

## BLOCKER B2 - Feature Dimension Math Is Not Closed

Phase 19.0 estimates `vision_sensor.feature_vector_dim ~= 1800`, but the stated channels exceed that by a large margin.

Region count is up to 1 + 2 + 9 + 25 + 32 = 69.

Approximate dimensions:
- V1 RGB hist: 24 * 69 = 1656
- V2 HSV 8x4x4: 128 * 69 = 8832
- V3 LBP: 30 * 69 = 2070
- V4 HOG-lite: 8 * 69 = 552
- V5 radial: 16
- V6 shape: 5
- V7 parts: at least 4 plus prototype vectors
- V8 layout: several scalars
- V9 fg/bg: multiple KL values

So 1800 cannot be the locked full feature dimension unless there is a defined projection. "PCA to 256 for storage" is not enough, because PCA fitting can introduce transductive leakage if trained on the evaluation set and also makes red-line reproducibility harder.

Required fix:
- Make the unprojected feature schema explicit and compute its exact dimension.
- If projection is needed, use either fixed deterministic pooling or a training-only fitted projection with its own leakage audit.
- Do not lock a magic dimension until the schema is closed by formula.

## BLOCKER B3 - Human-Like Confidence Formula Will Saturate Or Suppress The Wrong Cases

The intended psychological effect is right, but the current formula has three mathematical problems.

Problem 1: Noisy-OR saturation.
With 9 channels, even weak per-channel hits can push `D` high. For example, if each `delta*h = 0.2`, then `D = 1 - 0.8^9 = 0.866`, even though every cue is weak. This contradicts the design claim that "all channels half-believing stays medium".

Problem 2: The consistency term penalizes "few diagnostic cues".
For K=9, if only two genuinely diagnostic cues are strong and the rest are irrelevant, the stated Cauchy-Schwarz ratio is about 2/9 before remapping. That is low, exactly when the user wants AP to be human-like and say "a few strong cues, no competitors, likely X".

Problem 3: The diagnosticity term ignores within-class variance and nearest competitor.
`delta_k` uses mean distance to all other classes over std among other-class distances. A channel can look diagnostic because it separates from many irrelevant classes while still confusing the nearest competitor. For AP decisions, the nearest competitor matters most.

Required fix:
- Compute diagnosticity using nearest-negative separation relative to within-class scatter:
  - `delta_k(c) = sigmoid(beta * (d_nearest_negative - r_positive) / (r_positive + eps))`
  - or a held-out Delta-P / mutual-information estimate.
- Replace raw Noisy-OR with thresholded or top-m evidence:
  - `e_k = max(0, delta_k * (h_k - h0_k))`
  - `D = 1 - prod_{k in top_m}(1 - e_k)`
  - top_m should be fixed by constant governance.
- Compute consistency only over active diagnostic cues, not all channels:
  - active set `A = {k | delta_k >= delta_min and h_k >= h_min}`
  - if `|A| < min_active`, consistency stays low.
  - if 2-4 active cues agree, consistency can be high.
- Change margin suppression to a shifted gate:
  - current `sigmoid(0)=0.5` still permits confidence when top-1 and top-2 tie.
  - use `M = sigmoid(kappa * (relative_margin - margin_midpoint))` or a direct relative-margin clamp.

## BLOCKER B4 - Phase 19.3 Still Confuses Two Different Claims

Phase 19.3 says prototypes come from Phase 18.0 clean cards, then probes 12 real photos. That is clean-card-to-real-photo transfer. It is a much harder claim than real-photo train-to-heldout generalization.

If it fails, we will not know whether:
- the receptor is still insufficient,
- the confidence formula is poorly calibrated,
- or clean synthetic cards are too far from real photos.

If it passes, with only 12 images, the result is still a small internal probe, not robust visual generalization.

Required fix:
- Split 19.3 into two gates:
  - `19.3a user-real train/held-out visual-only probe`: train on user real-photo train split, evaluate held-out/hard variants. This tests visual-only no-leak learning on real images.
  - `19.3b clean-card to real-photo transfer`: train on clean cards, evaluate real photos. This is the harder cross-domain transfer gate.
- Do not call either "visual generalization valid" globally. Use "small-probe visual-only success" unless more concepts and more held-out assets pass.
- Gate must require correct prediction for firm and soft. Current "no firm + wrong" is too weak; "soft + wrong" should also fail calibration.

## SERIOUS S1 - Foreground Segmentation Is A Hidden Load-Bearing Assumption

V6, V8, and V9 all depend on `M_obj`. The design says GrabCut-lite from V1+V4 with pure numpy, but does not define the algorithm or failure handling.

If segmentation fails, shape, layout, foreground/background contrast, quality gate, and confidence all become unreliable.

Required fix:
- Define deterministic segmentation:
  - saliency from color contrast + edge closure + center prior, with no class label.
  - multi-hypothesis masks, not one mask.
  - segmentation confidence becomes part of Q.
- Add ablation gates:
  - busy background photo should lower Q, not produce confident wrong output.
  - centered clean card should reconstruct and segment easily.

## SERIOUS S2 - Audio Reconstruction Metrics Are Misapplied

STOI is mainly a speech intelligibility metric. It is not a general measure for rain, bird sounds, piano, bells, wind, or water.

Also, reconstructing waveform from MFCC/chroma/spectral summaries with Griffin-Lim will not preserve words or detailed timbre. It can make a plausible sound texture, but not prove that the auditory receptor preserved all information needed for recognition.

Required fix:
- Add `A0 Cochlear Spectrogram Tiles`: gammatone or mel magnitude tiles over time as the auditory analog of V0 retinal pyramid.
- Use metrics by sound family:
  - speech: STOI or envelope/phonetic intelligibility proxy
  - non-speech: mel-spectrogram correlation, spectral convergence, onset F1, pitch contour correlation, envelope correlation
  - human ear score remains blind and separate.
- Inner voice should not claim real TTS. Without a learned vocal motor pathway, it is "inner sound sketch" or "auditory imagery", not arbitrary speech synthesis.

## SERIOUS S3 - Inner Picture And Audit Reconstruction Need Source Discipline

Reusing one renderer is elegant, but the source must stay explicit. Otherwise an imagined prototype render can accidentally be counted as sensory reconstruction.

Required fix:
- Every rendered artifact must include:
  - `render_mode`: `sensory_reconstruction` or `prototype_imagination`
  - `input_trace_hash`
  - `prototype_trace_hash` only for imagination mode
  - `evaluator_label_accessed: false`
- Audit pass only accepts `render_mode=sensory_reconstruction`.
- Inner picture display may show prototype imagination, but it must be labelled as imagination in audit metadata.

## SERIOUS S4 - Similar Object Recall Is Not Proved By Reconstruction

The user asked whether the channels can mathematically recall similar other objects. Reconstruction alone does not prove retrieval.

Required fix:
- Add a percept-retrieval gate:
  - Train AP-native percept prototypes from label-hidden observations.
  - Align prototypes to vocab through SDPL packets only when teacher evidence is present.
  - On held-out image, require positive prototype rank above contrast by a margin.
  - Report Recall@1, Recall@3, margin, and high-confidence wrong count.
- Student-side packet must contain only receptor traces / percept prototype tokens / source markers, not evaluator labels.

## SERIOUS S5 - The 12-Image Acceptance Gate Is Too Small For The Claim

The 12 user images are useful as a diagnostic set. They are not enough to prove robust object recognition.

Required fix:
- Treat 12 images as Phase 19 diagnostic gate only.
- Add later Phase 20/21 expansion target:
  - at least 10 concepts,
  - at least 20 held-out images per concept,
  - backgrounds and lighting stratified,
  - class-balanced contrast set,
  - calibration metrics such as Brier score / ECE.

## Recommended v1a Patch

1. Add `V0 Foveated Retinal Pyramid` and `A0 Cochlear/Spectrogram Tiles`.
2. Rename reconstruction proof to bottleneck audit; remove "information-theoretic proof" wording.
3. Split reconstruction modes: sensory reconstruction vs prototype imagination.
4. Close feature dimensions exactly; no approximate 1800 until schema is computed.
5. Rewrite confidence formula:
   - nearest-negative diagnosticity,
   - thresholded top-m Noisy-OR,
   - active-cue consistency,
   - shifted relative-margin suppression,
   - class-radius OOD penalty.
6. Split 19.3 into real-photo held-out probe and clean-card transfer probe.
7. Require no high-confidence wrong output for both firm and soft.
8. Add percept-retrieval metrics, not just reconstruction metrics.
9. Treat 12 images as a diagnostic audit set, not a global visual-generalization proof.

## Final Assessment

The final goal is logically reachable, but not through the current v1 formulas unchanged.

The correct path is:

1. Build high-bandwidth foveated visual/audio receptor traces.
2. Use reconstruction as a bottleneck audit, not as a proof by itself.
3. Feed those traces into AP-native percept prototypes and SDPL alignment.
4. Use a calibrated human-like confidence layer that respects diagnostic cues, competitor absence, image quality, and OOD uncertainty.
5. Prove recall on label-hidden held-out assets with honest confidence calibration.

If v1a makes those changes, Phase 19 becomes a strong and elegant foundation for the open dialogue substrate. If it does not, the project risks replacing one false positive with another: label-mediated generalization becomes prototype-renderer-mediated generalization.

