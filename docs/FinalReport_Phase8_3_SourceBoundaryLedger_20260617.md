# Phase 8.3 Final Report: Source Boundary + Attention Gain Ledger

Date: 2026-06-17

## Design

Phase 8.3 implements the v14.1 boundary layer that Phase 8.2 intentionally left open.

Core idea:

- External sensor input first becomes PERCEIVED state evidence.
- Text meaning claims become HEARSAY only after the proposition layer.
- Correction is a feedback-channel event, not a keyword route from user text.
- Attention energy injection is recorded in an AttentionGainLedger.
- Real evidence cap and memory support floor are separated so imagination cannot masquerade as live perception, while cue-relevant memory can still support recall.
- Render payload references are kept render-only and unavailable to cognitive code.

## Review And Boundary

Boundaries preserved:

- No keyword/regex/text-answer route.
- No student-side LLM.
- No direct natural-language punishment parser.
- No SDPL Q table yet; that belongs to Phase 8.4.
- No natural correction loop yet; that belongs to Phase 8.9.
- No vision/audio sensor adapters yet.
- No render payload access in the cognitive path.

Important split:

```text
user utterance perceived -> PERCEIVED marker
utterance meaning proposal -> HEARSAY marker
negative feedback outcome -> CORRECTION marker via reward handler
```

This keeps "the user said something", "the user claimed something", and "the system was corrected" as different packet ingredients.

## Landing

Added or updated:

- `runtime/cognitive/state_pool/attention_gain_ledger.py`
- `runtime/cognitive/state_pool/target_cap.py`
- `runtime/cognitive/state_pool/v_double_control.py`
- `runtime/cognitive/runtime/audit_db_boundary.py`
- `runtime/cognitive/marker/events.py`
- `runtime/cognitive/marker/spawn_perceived.py`
- `runtime/cognitive/marker/spawn_hearsay.py`
- `runtime/cognitive/text_understanding/proposition_emit.py`
- `runtime/cognitive/reward/handler.py`
- `runtime/cognitive/runtime/tick_loop.py`
- `runtime/cognitive/state_pool/state_pool.py`
- `tests/test_phase8_3_source_boundary_ledger.py`

## Validation

Commands run:

```text
pytest -q tests/test_phase8_3_source_boundary_ledger.py
7 passed

python scripts/red_line_check_v14.py --phase 8.3
OK: Phase 8.3 deliverables present
OK: All red line checks pass on runtime/cognitive

python scripts/check_constant_governance.py
OK: Governance check passed (134 numeric constants)

pytest -q tests/test_phase8_2_continuous_tick_sensor_runtime.py tests/test_phase8_3_source_boundary_ledger.py
11 passed

pytest -q tests/test_phase4_0_minimal_dialogue_runtime.py tests/test_phase8_1_real_trial_and_web_chat.py
9 passed

python -m compileall -q apv3test runtime tests
passed

pytest -q
278 passed
```

## Positive Evidence

- Phase 8.3 redline is no longer a missing-deliverables failure.
- PERCEIVED is spawned from text sensor events during the tick loop.
- HEARSAY is spawned from the proposition layer, not raw text chars.
- CORRECTION is spawned through `apply_punishment`, not directly from user text.
- Feedback energy is tracked in the ledger.
- Target cap drops to zero without live external evidence.
- Long-term memory support can still raise V floor through cue alignment.
- Render-only boundary returns references that cognitive code cannot read as payload.

## Boundary

This phase proves the source-boundary and ledger substrate. It still does not prove:

- SDPL packet Q learning with five-layer backoff.
- ComposedVocab cold-fork Delta-P promotion.
- Natural language correction from conversation alone.
- Yellow apple multimodal generalization.
- Vision/audio sensor processing.
- Web visualization of ledger/source packets.

## Next

Phase 8.4 should implement:

- SDPL `LearningPacket` and `packet_key`.
- Five-layer Q backoff.
- Sparse pairwise ComposedVocab store.
- Held-out pool and cold-fork Delta-P gate.
- IMAGINED / REMEMBERED marker spawn paths needed by packet learning.

