# APV3 Phase 20.2/20.3 Design: Co-occurrence Teaching + Memory Package Ecosystem

## Correction

Phase 20.1 provided a useful web teaching workflow, but its first implementation used an independent teaching table. That is not AP-native enough. Phase 20.2 replaces the internal mechanism with co-occurrence learning:

- teacher text becomes an expression phrase memory item
- current text context SA and visual object/concept SAs become source SAs
- `CooccurrenceAssociationStore` stores source-SA to phrase co-occurrence
- repeated teacher events strengthen the same co-occurrence edge
- recall selects the phrase wave peak from AP memory

The UI can still say "教学", but runtime semantics are now `teacher_event_cooccurrence`.

## Visual-Text Teaching

When a user teaches after a visual turn, Phase 20.2 binds the taught phrase to:

- `phase20ctx::<hash>` for the current structural text/context event
- `visual_object::<candidate_id>` for the current object candidate
- `visual_concept::<top_concept_uuid>` for the current visual concept tendency

This keeps image teaching compatible with object-centric looking and moving visual focus. It does not create an image label map and does not read filenames or paths as labels.

## Text Teaching

Text-only teaching is also co-occurrence:

- `phase20ctx::<hash>` is the source SA
- the taught short expression is a phrase memory item
- the source phrase association is stored in `CooccurrenceAssociationStore`

This preserves the behavior users expect from "teach it how to reply here" without hard override.

## Styled Corpus Import

The styled curriculum YAML files are now imported into AP memory on Phase20 session startup:

- at least 1000 styled examples are written into `ExpressionPhraseMemory`
- corresponding `style_paradigm::<id>` co-occurrence edges are written into `CooccurrenceAssociationStore`
- the source is recorded as `curriculum_styled_yaml`

The import is capped for runtime state size, but it is no longer merely a direct YAML selector.

## Phase 20.3 Memory Package Ecosystem

Memory packages are co-occurrence subgraphs and expression memories, not external answer tables.

Supported operations:

- list local memories
- search memories
- view imported packages
- view package contents
- export selected memories
- import package with automatic dedup
- uninstall a package by removing only newly added memory ids
- manually delete selected local memory ids

Package registry records:

- package name
- package id
- import batch id
- active/uninstalled status
- added memory ids
- dedup memory ids

Uninstalling a package never deletes memories that pre-existed before import.

## Red Lines

- no `phase20_teaching_paradigms` runtime table
- no image label map
- no filename/path semantic label extraction
- no raw ordinary user text persistence
- no package uninstall by fuzzy content match
- no package import without dedup accounting

## Acceptance Gates

- style corpus imports at least 1000 examples into AP memory
- visual teaching creates co-occurrence edges from visual SA to teacher phrase
- greeting and image-question teaching do not cross-contaminate
- memory package import dedups, lists package, shows contents, uninstalls exactly added ids
- local memory deletion removes selected ids only
- web API exposes list/export/import/uninstall/delete
