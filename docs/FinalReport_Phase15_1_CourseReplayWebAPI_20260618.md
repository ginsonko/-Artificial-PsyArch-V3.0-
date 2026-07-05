# Phase 15.1 Final Report - Course Replay Web API

Date: 2026-06-18

## Design

Phase 15.1 adds render-only Web endpoints for the course replay runtime:

- `GET /api/course/demos`
- `POST /api/course/run`
- `GET /api/course/assets/<asset_id>`

## Review

The key review point was asset safety. The asset endpoint accepts a manifest asset id, never a filesystem path. Runtime resolution rejects missing ids, absolute paths, and parent traversal inside manifest records.

## Landing

Updated `apv3test/web_chat.py` to host CourseReplayRuntime alongside the existing chat app. When chat uses `web.sqlite`, course replay persists to `web_course_replay.sqlite`.

## Validation

Targeted test:

```powershell
python -m pytest tests/test_phase15_1_course_replay_web_api.py -q
```

Result in combined Phase 15 targeted run: PASS.

Core assertions:

- `/course.html` is served.
- Demo list returns 5 demos.
- Course run returns a runtime-generated 6 tick trace.
- Asset endpoint serves real PNG bytes for a manifest asset.
- Non-manifest/path-like asset ids return 404.
- Course replay table does not pollute the chat DB.

## Boundary

This phase exposes course replay locally. It is not a hosted service, public release, or privacy/legal release package.

## Next

Add the browser-facing course workbench page.
