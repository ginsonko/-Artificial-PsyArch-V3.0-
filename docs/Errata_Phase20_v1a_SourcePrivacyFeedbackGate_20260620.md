# APV3.0 Phase 20 v1a Errata — Source, Privacy, and Feedback Gate Closure

Date: 2026-06-20
Status: Landing errata, must be read with `Design_APV3.0_Phase20_OpenChineseDialogueFoundation_v1_20260620.md`.

## 0. Summary

Codex adversarial review accepts the Phase 20 direction, but v1 has three serious implementation risks. They are fixed here before landing.

## 1. F1 — Visual Evidence Must Not Become User Text

v1 shows a `visual_context_hint` being appended to `incoming_external_query`. That would make AP's own visual hypothesis look like a user utterance, creating source confusion.

Correction:

- `incoming_external_query` contains only user-authored text.
- visual evidence lives only in `object_files`, `phase20_trace`, and final reply assembly.
- if dialogue context needs a cue, use an opaque context token such as `vision_objects_present`, never a visible label like `apple`.

Gate:

- Runtime trace `incoming_query_total_length` must equal the user's text length, not text plus visual labels.
- No object label may appear in `incoming_external_query`.

## 2. F2 — User Images Are Private Inputs

v1 says Step 8 persists image trace and commits to Zvec. That is acceptable only for derived signatures, not raw images.

Correction:

- raw uploaded image bytes are never stored in SQLite.
- state stores `image_sha16`, `object_files`, and audit metrics only.
- any temporary upload file must live in an explicit temp/session directory and may be deleted after processing.
- Zvec may receive only UUID/signature candidates through Phase 19.9 rules, not image bytes, filenames, source URLs, or user text.

Gate:

- `chat_session_trace` and `minimalist_dialogue_trace` must not contain image path, image bytes, source URL, or user raw text.
- only `image_sha16` may appear in persisted state.

## 3. F3 — Feedback Trace Is Not Yet Recognition Improvement Proof

v1 expects a single correction to raise visual `raw_confidence` by at least 0.10. Existing Phase 19.5 `apply_natural_correction_credit` updates SDPL Q values; it does not automatically rewrite Phase 21 channel/concept recognition weights.

Correction for Phase 20:

- Phase 20 proves feedback routing: user feedback attaches to the last turn, emits source-aware correction trace, and does not directly overwrite Layer-3 weights.
- Phase 20 may record a tentative teaching signal for later Phase 22 concept promotion.
- Any claim that raw visual recognition confidence improves after feedback requires a later dedicated learning phase.

Gate:

- `G-20-Anth-07` becomes: same-session feedback produces a non-empty correction trace with nonzero total outcome and preserves the one-turn target boundary.
- No Phase 20 report may claim robust recognition improvement from feedback alone.

## 4. Landing Rule

Implementation must follow this corrected contract:

1. text source stays user-only;
2. image source stays visual-only;
3. feedback source stays correction-only;
4. styled output may use visible object labels only after recognition, during reply assembly, not by injecting them into user input.
