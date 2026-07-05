# Phase 18.1 Design - Clean Card To Real Photo Generalization Probe

Date: 2026-06-18

## Design

Phase 18.1 connects the cleaner Phase 18.0 card curriculum to the Phase 17 real-photo seed as a replay-level generalization probe.

The intended sequence is:

1. teach a concept from clean, no-text cards;
2. form an SDPL packet over the concept content;
3. probe with a held-out real photo from Phase 17;
4. compare against a real-photo contrast asset;
5. show the result in the Phase 15 course replay workbench.

## Review

The main risk is overclaiming. Phase 18.1 does not prove full pixel-level recognition. It proves that the workbench can run a cross-substrate curriculum trace where clean-card teaching and real-photo probe material remain auditable and separated.

Review decisions:

- keep Phase 17 real photos as probe material, not first-layer teaching material;
- keep Phase 18.0 clean cards as the teaching substrate;
- filter curriculum metadata such as `teaching_intent` out of SDPL concept content, because it is not the concept itself;
- require the trace to show both manifest ids: clean-card train and real-photo probe;
- require held-out real-photo tendency to beat real-photo contrast tendency;
- keep frontend rendering from runtime trace only.

## Landing Plan

1. Extend course replay demo specs with optional probe package / entry ids.
2. Add three demos:
   - clean cards -> real apple photo
   - clean cards -> real banana photo
   - clean cards -> real orange photo
3. Add Phase 18.1 tests for runtime trace, Web API, content-key metadata filtering, and public showcase.
4. Generate a public-readable showcase page from runtime traces.

## Boundary

Phase 18.1 proves a replay-level, auditable generalization probe path. It does not yet prove live camera perception, robust object recognition in arbitrary scenes, or open-ended multimodal dialogue.
