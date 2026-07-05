# APV3.0 Phase 13 - v3.2c / v3.3b Micro Errata

Date: 2026-06-18
Status: implementation preflight patch. This file does not replace v3/v3.1/v3.2/v3.2a/v3.2b/v3.3a. It only fixes remaining ambiguity before Phase 13.0 implementation.

## Summary

The merged v3.2b/v3.3a Errata correctly fixes the previous blockers. This micro errata adds eight binding implementation constraints so the fixes do not create new shortcut routes, false redline failures, or evaluation leakage.

## R1 - CORRECTION status must not become a hidden marker kind

v3.2b reuses the existing CORRECTION marker and carries `metadata.status = "pending_perceived_revalidation"`.

This is acceptable only under one constraint:

- `marker.metadata.status` is audit/lifecycle annotation, not a cognitive routing feature.
- SDPL packet keys, Q learning, attention selection, and composed-vocab learning must not branch on `marker.metadata.status`.
- The actionable lifecycle state lives in `ConflictResolution.status` or a `CurriculumRevalidationRecord.status`, not in marker metadata.

Required redline:

- Block `marker.metadata.get("status")` and `metadata["status"]` in SDPL, attention, composed vocab, Q table, and action selection paths.
- Allow it only in curriculum revalidation control, audit rendering, and reports.

Required tests:

- Pending revalidation and ordinary system correction both spawn CORRECTION marker kind.
- Their marker kind count remains unchanged.
- SDPL packet key does not include the status string.
- Revalidation control can still wait for PERCEIVED evidence through a lifecycle record.

## R2 - Metadata redline must not ban AP-native context evidence

The project already has AP-native `context_tokens` / `context_tags` used as learned evidence in habit and action-outcome paths. These are not the same as Phase 13 design metadata.

Forbidden:

- `metadata.style_tag`
- `metadata.context_tag`
- `metadata.design_note`
- any style/context design field used as a table key, branch, match case, or action selector

Allowed:

- `context_tokens`
- `context_tags`
- `LearningEpisode.context_tags`
- action outcome evidence tags, when they are produced by runtime evidence and learned statistically

Required tests:

- Redline flags `metadata["style_tag"]` routing.
- Redline flags `table[style_tag]`.
- Redline does not flag existing AP-native `LearningEpisode.context_tags` evidence paths.

## R3 - Pseudonymous identifier canonicalization must reject non-string sequence items

v3.2b canonicalizes str / list / tuple through JSON. The sequence path must not silently coerce arbitrary objects with `str(v)`.

Required rule:

- Accept `str` scalar.
- Accept `Sequence[str]`.
- Reject any sequence containing non-string items.

Recommended storage:

- Store at least 128 bits of HMAC output, preferably 32 hex chars.
- A shorter display prefix may be rendered in UI, but storage identity should not be only 16 hex chars.

Required tests:

- `("a", "b")` and `["a", "b"]` produce the same id.
- `"a"` and `["a"]` differ.
- `[1]`, `[None]`, and `[{"x": "y"}]` raise `TypeError`.
- Stored id length follows the configured storage length.

## R4 - Held-out event id must not enter AP cognition

Opaque event ids prevent semantic leakage, but event ids can still become event-specific memorization handles if they enter AP state.

Required rule:

- `event_id` is an evaluator/store handle only.
- The AP runtime receives raw normalized sensor SA content without `event_id`.
- The evaluator keeps the `event_id -> metadata` map outside AP state.

Required tests:

- `str(ap_state)` does not contain held-out event ids after evaluation.
- Packet keys do not contain held-out event ids.
- Held-out evaluation still works through the external evaluator map.

## R5 - DraftGrid randomization metadata must stay outside AP state

v3.3a correctly randomizes origin / spacing / digit width. These variables must not be handed to AP as symbolic cues.

Required rule:

- `chosen_origin`, `chosen_spacing`, and `digit_width` belong to the curriculum generator/evaluator only.
- AP sees visual pointers, focus movements, cell percepts, and teacher demonstrations as sensor/action traces.
- AP must not receive a symbolic field named `origin`, `spacing`, or `digit_width` during teacher-off validation.

Required tests:

- Teacher-off validation AP state contains no `chosen_origin`, `origin_row`, `origin_col`, `spacing`, or `digit_width` fields.
- Same arithmetic problem passes on unseen origins through relative layout behavior.

## R6 - Math fact SA ids must be opaque

The prose examples use readable labels like `fact::add::3_7 = 10`. That is fine in docs, but runtime SA ids must not encode operands or answers.

Required rule:

- Math fact SA ids are opaque.
- Operands, operators, and result tokens are learned content links, not parsed from ids.
- Runtime code must not parse strings like `fact::add::3_7=10`.

Required tests:

- Label-bijection test renames all fact ids and behavior remains unchanged.
- Redline blocks regex/string parsing of math fact ids.
- Evaluation checks recalled result content, not human-readable fact id text.

## R7 - Substrate in packet_key needs backoff and sparsity monitoring

v3.3a adds PERCEIVED substrate into packet keys to separate external visual and self draft. This is necessary, but it increases Q-table sparsity.

Required rule:

- Exact packet key includes substrate.
- Backoff must still include a content-only or content+non-substrate level so harmless transfer can occur.
- Negative feedback on `SELF_DRAFT_GRID` must not erase `EXTERNAL_VISUAL` learning.

Required tests:

- Same content with different substrate has different exact packet keys.
- Punishing self-draft action does not reduce external-visual Q for the same content.
- With no conflict history, content backoff can still support a related action.
- Q-table key count stays under configured budget in a synthetic grid long run.

## R8 - Phase 13.0 gate count must be textually consistent

v3.2b/v3.3a says Phase 13.0 has 14 must-fix gates, but the action-order section still says 12. The implementation contract is:

- Phase 13.0: all privacy, license, trust, held-out, metadata, and global redline gates from F1-F6 and E1-E5.
- Phase 13.5b.0: DraftGrid substrate proof and math-specific E6-E8 gates.

Reports must list the exact gates executed instead of relying on the number in prose.

## Implementation Order

1. Phase 13.0 implements F1-F6 and E1-E5 plus R1-R4/R8 checks.
2. Phase 13.1 implements curriculum substrate.
3. Phase 13.5b.0 implements DraftGrid substrate proof with E6-E8 plus R5-R7 checks.
4. Only after 13.5b.0 passes should Math-0/1 and later math curriculum packages proceed.

## Boundary

This micro errata does not change the core design. It only prevents implementation from turning status strings into hidden marker kinds, metadata into behavior routes, event ids into memorization handles, grid randomization into symbolic cues, or math fact ids into answer tables.
