# Phase 15 Design - Web Course Replay Workbench

Date: 2026-06-18

## Design

Phase 15 turns the Phase 14 clean curriculum assets into a public-readable replay experience. The goal is not to add new vocabulary or claim mastery; it is to let a user see one short AP-native course episode as a trace:

1. course material enters as PERCEIVED course assets;
2. SDPL LearningPacket is formed from content/source/feeling;
3. held-out material probes whether the same concept tendency transfers;
4. contrast material is kept separate;
5. action competition exposes the auditable response candidate;
6. the final AP output is committed from the runtime trace.

## Review

Adversarial review tightened four boundaries before implementation:

- The Web page must render runtime JSON only; no hardcoded answers in frontend code.
- Asset serving must resolve manifest asset ids only; no arbitrary local path reads.
- Course replay persistence must use a separate SQLite file from the chat database.
- Public demos are short six-tick traces, not staged videos or claims of completed vocabulary mastery.

## Landing Plan

- 15.0 CourseReplayRuntime over Phase 14 manifest/packages.
- 15.1 Web API endpoints for demo list, trace run, and manifest-safe asset serving.
- 15.2 Web workbench UI with course selector, tick stepping, material pane, packet pane, mind pane, and summary pane.
- 15.3 Public-readable Chinese showcase with five concrete trace examples.

## Validation Plan

- Phase 15 targeted tests must cover runtime trace generation, Web API, frontend no-hardcode contract, and showcase UTF-8/readability.
- Red-line deliverable gates must pass for 15.0-15.3.
- Constant governance and full regression must remain green.

## Boundary

Phase 15 proves that clean curriculum assets can be replayed through an auditable AP-native trace and rendered in a local Web workbench. It does not prove complete vocabulary mastery, real external dataset ingestion, new style/persona corpus completion, or production release readiness.
