# Phase20.10m Learning Lifecycle Drilldown

Date: 2026-06-29

Formula:

`apv3_phase20_10m_learning_lifecycle_drilldown/v1`

## 1. Design

Phase20.10m extends the synchronized learning lifecycle card into a deeper drilldown.

The goal is to keep the same memory-rhythm timeline from 10l, but let the card expose more of the already-existing trace:

- reward and punish pressure;
- stability, regression, and cold-retest pressure;
- recent review ticks and recent self-test ticks;
- lifecycle action deltas across existing actions.

This is still presentation over existing trace. It does not add a new cognitive entity, scheduler, or route.

## 2. No-New-Entity Review

10m does not add:

- a new memory table
- a new lifecycle engine
- a new action selector
- a new answer route
- a new hidden solver

It only reads existing `learning_object_lifecycle` fields already exposed by the runtime.

## 3. Implementation

Files:

- `apv3test/web/static/phase20_7_workbench.js`
- `apv3test/web/static/phase20_7_workbench.css`

Added a lifecycle drilldown block inside the lifecycle card:

- a compact metric grid for reward / punish / stability / regression / cold-retest / teacher feedback;
- chips for recent review ticks and recent self-test ticks;
- a small action-delta grid over the existing lifecycle actions.

Test:

- `tests/test_phase20_10m_workbench_lifecycle_drilldown.py`

## 4. Acceptance

To verify:

- `node --check apv3test/web/static/phase20_7_workbench.js`
- `pytest -q tests/test_phase20_10m_workbench_lifecycle_drilldown.py tests/test_phase20_10l_workbench_lifecycle_memory_rhythm_timeline_sync.py tests/test_phase20_10i_workbench_memory_rhythm_display.py tests/test_phase20_10j_workbench_tick_memory_rhythm_explanation.py tests/test_phase20_10c_workbench_learning_object_lifecycle.py tests/test_phase20_9d_workbench_learning_loop_panel.py`

## 5. Plain Example

The card now answers questions like:

- what is the current lifecycle pressure balance?
- what recent review/self-test ticks are still “hot”?
- which action tendencies are being pushed up or down by this object?

This is still the same lifecycle, just shown one layer deeper.

## 6. Boundaries

This step can prove:

- the lifecycle card has a deeper readout over existing trace;
- the memory rhythm timeline remains synchronized with the replay view;
- no new cognitive entity was introduced.

This step cannot yet claim:

- complete L1/L2/L3 online embedding;
- complete six-stage runtime;
- complete paradigm self-learning;
- mathematical column calculation;
- object-centric visual imagination completion;
- Phase21 visual teaching generalization closure.

## 7. Next Step

Phase20.10n should only continue if this drilldown needs one more level of compression or emphasis in the same card; otherwise the next meaningful work should move back to a runtime-facing learning boundary rather than adding more display depth.
