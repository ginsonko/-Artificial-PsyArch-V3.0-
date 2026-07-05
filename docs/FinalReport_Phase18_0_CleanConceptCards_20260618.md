# Phase 18.0 Final Report - Clean Concept Cards

Date: 2026-06-18

## Design

Phase 18.0 changes the immediate visual-curriculum direction after reviewing the Phase 17 real-photo pack. Real photos are valuable, but they are noisy first-layer teaching material. The new design teaches fruit concepts first with clean, no-text cards, then keeps real photos for later generalization probes.

## Review

The review outcome was:

- Phase 17 real photos are preserved and not mutated.
- Clean concept cards should reduce background/scene shortcut risk.
- Cards must contain no printed label text.
- Existing Phase 15 synthetic demos must remain available.
- Course replay must still render runtime traces, not frontend answer tables.

## Landing

Completed:

- `scripts/curriculum/generate_clean_concept_cards.py`
- `config/curriculum/assets/clean_card_manifest.yaml`
- `config/curriculum/assets/visual/clean_cards/` with 15 PNG files
- `config/curriculum/packages/clean/clean_fruit_cards_v1.yaml`
- `apv3test/runtime/course_replay.py` multi-manifest / multi-package replay support
- `tests/test_phase18_0_clean_concept_cards.py`
- `reports/APV3_Phase18_CleanConceptCards_Showcase_20260618.html`

Asset counts:

- 15 clean card visual assets
- 3 concepts: apple, banana, orange
- 9 train, 3 held-out, 3 contrast
- 0 text in generated card pixels by generator contract

Course replay:

- Added 3 clean-card demos:
  - `demo_clean_card_apple` -> `像是 苹果`
  - `demo_clean_card_banana` -> `像是 香蕉`
  - `demo_clean_card_orange` -> `像是 橙子`
- Existing 5 Phase 15 synthetic demos remain available.

## Validation

Targeted test:

```powershell
python -m pytest tests/test_phase18_0_clean_concept_cards.py -q
```

Result: `7 passed in 3.78s`.

Phase 15 replay compatibility:

```powershell
python -m pytest tests/test_phase15_0_course_replay_runtime.py tests/test_phase15_1_course_replay_web_api.py tests/test_phase15_2_course_replay_frontend_contract.py tests/test_phase15_3_public_showcase.py -q
```

Result: `15 passed in 7.04s`.

Phase 17 real-photo preservation:

```powershell
python -m pytest tests/test_phase17_0_real_visual_assets.py -q
```

Result: `8 passed in 2.88s`.

Deliverable gate:

```powershell
python scripts\red_line_check_v14.py --phase 18.0
```

Result: Phase 18.0 deliverables present and global red line passed.

Global red line:

```powershell
python scripts\red_line_check_v14.py
```

Result: `OK: All red line checks pass on runtime/cognitive`.

Constant governance:

```powershell
python scripts\check_constant_governance.py
```

Result: `OK: Governance check passed (316 numeric constants)`.

Phase 14-18 nearby regression:

```powershell
python -m pytest tests/test_phase14_0_asset_governance.py tests/test_phase14_1_synthetic_assets.py tests/test_phase14_2_neutral_curriculum_packs.py tests/test_phase14_3_public_showcase.py tests/test_phase15_0_course_replay_runtime.py tests/test_phase15_1_course_replay_web_api.py tests/test_phase15_2_course_replay_frontend_contract.py tests/test_phase15_3_public_showcase.py tests/test_phase16_0_styled_expression_corpus.py tests/test_phase17_0_real_visual_assets.py tests/test_phase18_0_clean_concept_cards.py -q
```

Result: `61 passed in 310.58s`.

Compile check:

```powershell
python -m compileall runtime apv3test scripts tests -q
```

Result: PASS.

Full regression:

```powershell
python -m pytest -q
```

Result: `510 passed in 474.01s`.

## Boundary

Phase 18.0 proves clean concept-card curriculum assets and replay integration. It does not prove full real-world visual recognition, broad object mastery, or open-ended multimodal dialogue. Real photos are now positioned as the next generalization probe, not as the first teaching substrate.

## Next

The next stable step is Phase 18.1: use clean-card learning as the teaching side and Phase 17 real photos as a held-out generalization probe inside the course replay workbench, with boundaries that prevent overclaiming pixel-level mastery.
