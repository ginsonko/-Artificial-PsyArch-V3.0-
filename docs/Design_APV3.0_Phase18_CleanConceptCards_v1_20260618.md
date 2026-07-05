# Phase 18.0 Design - Clean Concept Cards Before Real-Photo Generalization

Date: 2026-06-18

## Design

Phase 18.0 changes the next curriculum step from "use real photos as first teaching material" to "teach with clean concept cards first, keep real photos for later generalization probes."

The reason is simple: early human teaching usually isolates the concept before adding real-world clutter. A fruit card should help AP attend to "apple / banana / orange" rather than orchard branches, table texture, photographer style, or background color.

## Review

The Phase 17 real-photo pack stays valuable, but its role is adjusted:

- not first-layer teaching material;
- yes later held-out / generalization probe;
- no deletion or mutation of Phase 17 provenance evidence;
- no claim that a clean-card run proves full visual recognition.

Phase 18.0 must satisfy these review constraints:

- card pixels contain no printed label text;
- background, object position, and scale vary across variants;
- train / held-out / contrast refs remain separated;
- package public payload does not contain private answer fields;
- Web course replay renders runtime trace fields, not frontend answer tables;
- existing Phase 15 synthetic demos remain available.

## Landing Plan

1. Generate a deterministic clean-card manifest and package:
   - `config/curriculum/assets/clean_card_manifest.yaml`
   - `config/curriculum/assets/visual/clean_cards/*.png`
   - `config/curriculum/packages/clean/clean_fruit_cards_v1.yaml`
2. Extend `CourseReplayRuntime` to load the clean-card manifest/package in addition to the original synthetic manifest/package.
3. Add three public replay demos:
   - clean card: apple
   - clean card: banana
   - clean card: orange
4. Validate runtime/API/frontend/showcase behavior with Phase 18 tests and redline deliverables.

## Boundary

Phase 18.0 proves a cleaner concept-teaching substrate and course replay integration. It does not prove full pixel-level visual recognition, large-scale object learning, real-world robustness, or complete open dialogue. Those remain later gates.
