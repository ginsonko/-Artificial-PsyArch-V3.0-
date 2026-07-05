# Phase 20.5a2 Workbench Tick Replay Repair Final Report

## Result

PASS.

This repair fixes the Phase 20.5a workbench replay semantics. The prior UI displayed one named pipeline stage per tick, such as input ingress, visual focus, recall, style assembly, and commit. That was misleading: an AP tick should be a complete loop snapshot, not a single pipeline stage.

## What Changed

1. `Phase20MultimodalSession.turn()` now emits per-tick AP loop snapshots through `phase20_5a2_per_tick_workbench_snapshot`.
2. Each replay tick uses `stage = ap_tick_loop` or `idle_tick_loop`, not stage names such as `input_ingress` or `commit_reply`.
3. Each tick carries a `draft_snapshot` / `draft_changes` block with:
   - `draft_action_kind`
   - `typed_token`
   - `draft_buffer`
   - `committed_text`
   - input hash and length
   - visual object labels
   - cooccurrence teaching hit status
4. The web replay panel now foregrounds the draft box, current draft action, recall status, candidate action, energy, and state pool.
5. Layout was adjusted so the chat column is wider, the text input is taller, the per-turn summary sits above the composer, and package controls live behind the right-side memory/package tab instead of consuming the whole bottom row.
6. Chat bubbles no longer inherit template indentation as visible whitespace. Bubble containers use normal flow, while actual message text uses a dedicated `.bubble-text` span for real user newlines.

## Boundaries

- This is still Phase 20.5a-level replay, not full Phase 20.5b action competition.
- Active stop / request teacher competition remains Phase 20.5b.
- Slow-memory persistence remains Phase 20.5b.
- TTS, canvas, recording, and teacher-guided focus remain Phase 20.5c.
- The replay now avoids the fake pipeline-stage tick, but it does not yet claim the final long-horizon open dialogue runtime.

## Validation

- Phase 20.5a + Phase 20.4 targeted tests: `11 passed`.
- Adjacent Phase 20 tests: `22 passed`.
- Phase 20.5a red line gate: PASS.
- Python compile check: PASS.
- JavaScript syntax check: PASS.
- Local API smoke at `http://127.0.0.1:8776/`: PASS.
- Browser UI smoke at `http://127.0.0.1:8776/`: PASS.
- Browser bubble-layout smoke: PASS. A short user/AP exchange rendered as compact bubbles with heights about 64px and 66px, not tall vertical cards.

## Browser Smoke Evidence

The visible tick buttons after sending `你是谁?` were:

```text
1 写 嗯
2 写 ,
3 写 好
4 写 。
5 commit
6 idle_observe
7 idle_observe
```

The replay detail showed the draft box, draft action, input length/hash, visual object status, cooccurrence recall status, candidate action, energy values, state pool, and the boundary `per_tick_ap_loop_snapshot_not_stage_pipeline`.

## Share URL

Local workbench:

```text
http://127.0.0.1:8776/
```
