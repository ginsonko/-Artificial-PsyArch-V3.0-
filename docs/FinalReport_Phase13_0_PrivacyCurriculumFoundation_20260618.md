# Phase 13.0 Final Report - Privacy And Curriculum Foundation

Date: 2026-06-18

## Design

Phase 13.0 implements the foundation gates required before cognitive curriculum content can safely enter APV3:

- Default user text privacy: runtime may use input text transiently during the current turn, but persisted state and Web snapshots store only HMAC pseudonymous ids, lengths, and counts unless explicit opt-in is set.
- Pseudonymous identifiers: canonical JSON input plus per-install salt and HMAC-SHA256, avoiding raw sha256 dictionary reversal for short Chinese phrases.
- Held-out evaluation boundary: evaluator metadata and private handles stay outside AP cognition; public held-out events contain only raw sensor-facing content and PERCEIVED source markers.
- Trust promotion gate: trust can only adjust p-value threshold and minimum held-out observations. It cannot soften the hard effect-size floor.
- CORRECTION lifecycle reuse: pending perceived revalidation reuses the existing CORRECTION marker with string status metadata, without adding a new marker kind or bool lifecycle field.
- SDPL content key hardening: packet content identity now prefers `metadata["cognitive_content"]`, so opaque SA ids do not become the learned content.
- Phase 13 redlines: metadata/context hard routing and status leakage in learning paths are blocked by AST checks.

## Review And Corrections

The implementation follows the merged v3.2/v3.2a/v3.2b/v3.2c/v3.3d contract:

- F1/F2: all default persisted traces remove raw user text; HMAC ids use canonical JSON and local salt.
- F3: promotion evidence must declare `effect_source="held_out_cold_fork"`.
- F4/E2/E3/R1: pending revalidation is `CORRECTION + metadata.status`, but status stays out of packet keys and learning path redlines.
- E4/D5/R4: held-out private handle never enters AP state, and evaluator metadata is not recovered by content equality.
- F5/E5/R2/D4: redline forbids style/context metadata routing while allowing AP-native `context_tokens` statistical evidence.
- D1 guard: SDPL packet content identity no longer depends on opaque SA id when cognitive content is present.

One redline false positive was found and corrected: comparing a learned row field named `context_tokens` to the runtime context tuple is AP-native evidence, not a literal semantic branch. The scanner now permits field-name literals while still blocking `"math_context" in episode.context_tokens`.

## Landing

Implemented files:

- `apv3test/util/pseudonymous_id.py`
- `apv3test/chat.py`
- `apv3test/runtime/minimalist_dialogue_flow.py`
- `apv3test/web_chat.py`
- `apv3test/web/static/app.js`
- `runtime/cognitive/curriculum/held_out_private_pool.py`
- `runtime/cognitive/curriculum/trust_gate.py`
- `runtime/cognitive/curriculum/conflict_resolution.py`
- `runtime/cognitive/sdpl/packet.py`
- `scripts/red_line_check_v14.py`
- `tests/test_phase13_0_privacy_curriculum_foundation.py`
- `config/apv3_constants.yaml`

CLI additions:

- `python -m apv3test.chat --privacy-status`
- `python -m apv3test.chat --export-my-data <path>`
- `python -m apv3test.chat --delete-my-data`

## Validation

Executed:

```powershell
python -m pytest tests/test_phase13_0_privacy_curriculum_foundation.py -k "not redline_deliverables" -q
```

Result: `9 passed, 1 deselected`.

```powershell
python scripts\red_line_check_v14.py
```

Result: `OK: All red line checks pass on runtime/cognitive`.

```powershell
python -m pytest tests/test_phase8_0a_runtime_profile.py tests/test_phase8_0b_minimal_cli_entry.py tests/test_phase8_1_real_trial_and_web_chat.py tests/test_phase8_4_sdpl_composed_vocab.py tests/test_phase12_1_demo_audit_view.py -q
```

Result: `21 passed`.

The final deliverable gate and full regression are run after this report and showcase are present.

Final executed gates:

```powershell
python -m pytest tests/test_phase13_0_privacy_curriculum_foundation.py -q
```

Result: `10 passed`.

```powershell
python scripts\red_line_check_v14.py --phase 13.0
```

Result: `OK: Phase 13.0 deliverables present` and global redline pass.

```powershell
python scripts\check_constant_governance.py
```

Result: `OK: Governance check passed (255 numeric constants)`.

```powershell
python -m pytest -q
```

Result: `419 passed in 247.49s`.

## Boundary

Phase 13.0 proves only the privacy/curriculum foundation gates. It does not yet implement Phase 13.1 substrate loading, Phase 13.5b DraftGrid/char-focus math proof, visual/audio dataset ingestion, expression paradigm packs, or real curriculum content.

## Next

The next safe step is Phase 13.1: substrate/course package loading with the same gates active. Phase 13.5b.0 should only start after substrate loading is clean, because DraftGrid and math curriculum need the held-out/trust/privacy boundaries established here.
