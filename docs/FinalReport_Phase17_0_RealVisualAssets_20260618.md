# Phase 17.0 Final Report - Real Visual Asset Seed

Date: 2026-06-18

## Design

Phase 17.0 adds a separate real-photo asset seed while preserving the Phase 14 synthetic-first manifest. The first seed uses Wikimedia Commons allowlisted material and records license/provenance per asset.

## Review

The first generated attempt was rejected during review because some candidates were paintings, fruit cards, or person-context images. The final implementation tightened the contract: smaller first seed, cleaner title filters, no CC-BY-SA, and no generated-local assets.

## Landing

Completed:

- `scripts/curriculum/download_real_visual_assets.py`
- `config/curriculum/assets/real_manifest.yaml`
- `config/curriculum/assets/visual/real/` with 15 PNG files
- `config/curriculum/assets/visual/real/_sources.json`
- `config/curriculum/packages/real/real_fruit_photos_v1.yaml`

Asset counts:

- 15 real visual assets
- 3 concepts: apple, banana, orange
- 9 train, 3 held-out, 3 contrast
- 0 audio

License counts:

- PDM-1.0: 6
- CC0-1.0: 1
- CC-BY-2.0: 2
- CC-BY-3.0: 1
- CC-BY-4.0: 5

## Validation

Targeted test:

```powershell
python -m pytest tests/test_phase17_0_real_visual_assets.py -q
```

Result: `8 passed in 3.34s`.

Deliverable gate:

```powershell
python scripts\red_line_check_v14.py --phase 17.0
```

Result: Phase 17.0 deliverables present and global red line passed.

Global red line:

```powershell
python scripts\red_line_check_v14.py
```

Result: `OK: All red line checks pass on runtime/cognitive`.

Constant governance:

```powershell
python scripts\check_constant_governance.py
```

Result: `OK: Governance check passed (309 numeric constants)`.

Phase 14-17 nearby regression:

```powershell
python -m pytest tests/test_phase14_0_asset_governance.py tests/test_phase14_1_synthetic_assets.py tests/test_phase14_2_neutral_curriculum_packs.py tests/test_phase14_3_public_showcase.py tests/test_phase15_0_course_replay_runtime.py tests/test_phase15_1_course_replay_web_api.py tests/test_phase15_2_course_replay_frontend_contract.py tests/test_phase15_3_public_showcase.py tests/test_phase16_0_styled_expression_corpus.py tests/test_phase17_0_real_visual_assets.py -q
```

Result: `54 passed in 300.76s`.

Full regression:

```powershell
python -m pytest -q
```

Result: `503 passed in 500.04s`.

## Boundary

Phase 17.0 proves a clean first real-photo seed with provenance and license audit. It does not prove a full-scale dataset, automatic pixel-level semantic mastery, full external license pipeline, or production legal release.

## Next

Recommended next work:

- expand real photo seed gradually after the same filters hold;
- add image-quality scoring and duplicate-source analysis;
- connect real-photo packs to longer course replay once visual perception learning is ready;
- keep style corpus integration and real asset expansion as separate evidence routes.
