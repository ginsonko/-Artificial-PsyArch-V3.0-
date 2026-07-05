# Phase 15.2 Final Report - Course Replay Workbench

Date: 2026-06-18

## Design

The workbench shows a short course replay as three panes:

- material pane: question, current assets, playback controls;
- tick pane: six tick timeline and detailed current tick;
- audit pane: packet keys, mind/source/marker/feeling, and summary.

## Review

The frontend must remain render-only. It may request demos and traces, display assets, and step through returned ticks. It must not contain answer tables or final outputs.

## Landing

Added:

- `apv3test/web/static/course.html`
- `apv3test/web/static/course.js`
- course-specific styles in `apv3test/web/static/styles.css`

The page is available at `/course.html` on the local web server.

## Validation

Targeted test:

```powershell
python -m pytest tests/test_phase15_2_course_replay_frontend_contract.py -q
```

Result in combined Phase 15 targeted run: PASS.

Core assertions:

- Dedicated renderer is loaded.
- Tick controls and packet/mind/summary tabs exist.
- Frontend fetches `/api/course/demos` and `/api/course/run`.
- Frontend renders `tick.ap_output`, packet keys, and summary from runtime JSON.
- Concrete final outputs such as `像是 黄` do not appear in frontend JS.

## Boundary

This is a local workbench UI. It does not add new cognitive learning mechanisms or style/persona content.

## Next

Write the public-readable Chinese showcase using real runtime traces.
