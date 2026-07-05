# APV3 Phase 20.1 Design: Web Demo Polish + Context-Bound Teaching Paradigm

## Goal

Phase 20.1 turns the Phase 20.0 connected substrate into a shareable local web demo and adds a direct teaching path for unsatisfactory replies.

The new teaching path is intentionally narrow:

- It targets the latest Phase20 turn context, not arbitrary global dialogue.
- It stores a teacher-authored response candidate with explicit source `teacher_reply_paradigm`.
- It rewards the taught response and records a light penalty against the previous reply hash.
- It does not inject the taught sentence into `incoming_external_query`.
- It does not change visual labels, Zvec labels, object files, or image recognition scores.

## Failure Being Fixed

Observed failure:

1. User says `你好`; AP can reply `你好`.
2. User asks `这是什么` with an image; AP replies a previous greeting-like pattern.
3. Teacher feedback causes later `你好` to recall the image-question phrase.

Root cause:

- Ordinary dialogue, multimodal question answering, and teaching correction were not separated by a structural response context.
- Display assembly joined style tokens directly, causing non-human text such as `嗯在` even when the styled corpus contained natural `response_text`.

## Phase 20.1 Mechanism

Every ordinary Phase20 turn emits:

```json
{
  "schema_id": "apv3_phase20_1_context_signature/v1",
  "user_text_hash": "...",
  "has_image": true,
  "situation": "object_no_call",
  "object_count_bucket": 1,
  "top_concept_uuid": "...",
  "top_decision_tier": "no_call",
  "styled_paradigm_id": "PAR-Q.06"
}
```

The canonical JSON is hashed into `phase20ctx::<sha16>`. This is the only target used by the teaching paradigm.

Teaching stores:

```json
{
  "schema_id": "apv3_phase20_1_teaching_paradigm/v1",
  "context_signature": "phase20ctx::...",
  "response_text": "像苹果。",
  "response_tokens": ["像苹果。"],
  "source": "teacher_reply_paradigm",
  "reward_support": 1.0
}
```

The previous displayed reply is punished only by hash:

```json
{
  "schema_id": "apv3_phase20_1_previous_reply_penalty/v1",
  "context_signature": "phase20ctx::...",
  "reply_text_hash": "...",
  "punish_support": 0.12
}
```

## Red Lines

- No keyword route: selection is keyed by a structural hash, not text matching.
- No filename/label leakage: context uses object trace, not image path or filename.
- No user-text persistence: ordinary user text remains hash + length only.
- No hidden solver: the taught response is explicitly teacher-authored and source-marked.
- No recognition overclaim: teaching a reply does not prove visual confidence improvement.

## Web Demo Additions

- Local image path still works.
- Clean-card demo buttons fill known local paths for apple/banana/orange.
- A separate teaching textarea posts to `/api/phase20/teach`.
- The Phase20 panel shows reply, context signature, image hash, ObjectFiles, styled source, teaching application, feedback trace, and teaching trace.

## Acceptance Gates

- Greeting teaching and image-question teaching do not contaminate each other.
- Teaching reward and previous-reply penalty are persisted and auditable.
- Taught response does not enter `incoming_external_query`.
- Styled display no longer collapses `["嗯", "在"]` into `嗯在`.
- Web API returns teaching trace and later applies the taught response only in the matching context.
