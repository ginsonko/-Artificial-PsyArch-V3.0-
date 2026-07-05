# Phase 18.2 Design - User Real Image Visual-Only Probe

## Design

Phase 18.2 is a correction phase after the Phase 18.1 audit.

The user supplied a small real-image probe set whose filenames describe the intended concept. Those filenames are useful for an external evaluator, but they must not enter the AP student-side cognitive packet. The goal is to test whether a visual-only feature/prototype path can produce a guarded concept tendency without using `neutral_label`, `entry_id`, filename semantics, target class fields, or intended-use energy shortcuts.

This phase uses two separate layers:

- Public/AP layer: opaque image ids, image bytes, image-derived feature vectors, source marker metadata, and no answer labels.
- Evaluator layer: filename-derived labels and split roles, stored in a sidecar that the AP packet builder never reads while constructing probe payloads.

## Review

The main failure mode is a repeat of Phase 18.1: a probe that looks like visual generalization but actually gets the answer through labels, package entry ids, or energy buckets. Phase 18.2 therefore treats leakage prevention as a first-class gate.

The second risk is overclaiming. With only a dozen web-search images, some difficult held-out cases may be visually ambiguous. If the visual-only classifier is not confident, the correct AP-facing output is `还不能确认`, not a polished label.

The third risk is licensing. These images are user-supplied public-search assets for internal testing. They are not release-ready or redistributable open-source assets.

## Landing Plan

1. Ingest user images into an opaque internal asset manifest.
2. Store evaluator-only labels in a separate sidecar.
3. Extract visual features from image pixels only.
4. Train class prototypes from teacher-labeled training images.
5. Probe held-out images with labels hidden from the student payload.
6. Render a public-readable report showing what AP saw, what the evaluator knew, and whether the result passed.

## Validation

Required gates:

- Public manifest contains no Chinese concept labels, no original filenames, and no target labels.
- Student probe payload contains no `neutral_label`, `entry_id`, target class, filename, or Chinese answer label.
- Evaluator sidecar may contain labels, but is not used to build student-side visual payloads.
- Any label output requires both correct prediction and confidence/margin gates.
- If confidence fails, the output is `还不能确认`.

## Boundary

Phase 18.2 does not prove full visual recognition, live camera perception, arbitrary real-scene understanding, or clean-card-to-real-photo transfer. It proves whether this small user-provided real-image set can pass a stricter visual-only probe gate, and if it cannot, it records the failure honestly.

