# Phase 15 Final Report - Web Course Replay

Date: 2026-06-18

## Design

Phase 15 moves from "we have clean curriculum materials" to "we can show AP running a short course trace." It connects the Phase 14 synthetic assets and neutral packs to a local Web course replay workbench.

## Review

The implementation follows the stricter Phase 15 review:

- Runtime generates traces from manifest/package data.
- Frontend renders returned trace fields only.
- Asset endpoint serves manifest ids only.
- Course replay SQLite is isolated from chat state.
- Public page explains results without claiming finished vocabulary mastery.

## Landing

Completed:

- 15.0 CourseReplayRuntime
- 15.1 Course Replay Web API
- 15.2 Course Replay Workbench UI
- 15.3 Public-readable Chinese showcase

Five demos are available:

- 颜色：黄 -> `像是 黄`
- 形状：三角 -> `像是 三角`
- 物体：苹果 -> `像是 苹果`
- 声音：轻声呼唤 -> `像是 轻声呼唤`
- 反馈：对 -> `像是 对`

## Validation

Phase 15 targeted tests:

```powershell
python -m pytest tests/test_phase15_0_course_replay_runtime.py tests/test_phase15_1_course_replay_web_api.py tests/test_phase15_2_course_replay_frontend_contract.py tests/test_phase15_3_public_showcase.py -q
```

Result: `15 passed in 5.52s`.

Deliverable gates:

```powershell
foreach ($p in @('15.0','15.1','15.2','15.3')) { python scripts\red_line_check_v14.py --phase $p }
```

Result: all Phase 15.0-15.3 deliverable gates passed.

Global red line:

```powershell
python scripts\red_line_check_v14.py
```

Result: `OK: All red line checks pass on runtime/cognitive`.

Constant governance:

```powershell
python scripts\check_constant_governance.py
```

Result: `OK: Governance check passed (293 numeric constants)`.

Phase 14+15 nearby regression:

```powershell
python -m pytest tests/test_phase14_0_asset_governance.py tests/test_phase14_1_synthetic_assets.py tests/test_phase14_2_neutral_curriculum_packs.py tests/test_phase14_3_public_showcase.py tests/test_phase15_0_course_replay_runtime.py tests/test_phase15_1_course_replay_web_api.py tests/test_phase15_2_course_replay_frontend_contract.py tests/test_phase15_3_public_showcase.py -q
```

Result: `31 passed in 12.03s`.

Compile check:

```powershell
python -m compileall runtime apv3test scripts tests -q
```

Result: PASS.

Full regression:

```powershell
python -m pytest -q
```

Result: `480 passed in 138.49s`.

## Boundary

Phase 15 proves a local, auditable, public-readable course replay loop over existing Phase 14 materials. It does not claim complete open Chinese dialogue, complete elementary curriculum, real external media ingestion, release/legal readiness, or production-scale user testing.

## Next

Recommended next work:

- use the workbench for longer curriculum runs;
- connect user/Claude-authored quiet-girl expression corpora;
- add optional real-asset ingestion only after license audit tooling;
- prepare Phase 16 release hygiene when the demo loop is stable.
