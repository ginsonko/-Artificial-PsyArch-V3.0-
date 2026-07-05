# Phase20.10f Memory Consolidation / Forgetting / Review Rhythm

Date: 2026-06-29

Formula:

`apv3_phase20_10f_memory_consolidation_forgetting_review_rhythm/v1`

## 1. Design

Phase20.10f extends 20.10d/20.10e from cold retest confidence into a slower memory rhythm:

- `memory_consolidation`
- `forgetting_pressure`
- `review_rhythm_pressure`
- `reconsolidation_need`

The rhythm is not a new scheduler. It is a projection inside the existing `learning_object_lifecycle`, computed from existing AP traces:

- ExperienceFlow alignment event
- SSP idle learning review occurrences
- SSP private self-test occurrences
- long-interval cold retest window
- cold retest success/failure generalization tuning
- reward / punish
- stability / regression
- learning stage scores

The output only merges into existing action competition deltas:

- `commit_reply`
- `write_cell`
- `request_teacher`
- `maintain_unclosed`
- `idle_think`
- `read_draft`
- `edit_cell`
- `integrate_feedback`
- `stop_generating`

It does not create a reply candidate and does not write an answer.

## 2. No-New-Entity Review

10f does not add:

- memory consolidation table
- review schedule table
- external curriculum script
- timer-based review daemon
- answer route
- keyword route
- hidden solver

It reuses `learning_object_lifecycle` as the projection surface, and reads only existing runtime evidence. This follows the AP rule that long-term memory rhythm should emerge from repeated experience, reward/punish, recall, self-test, and forgetting pressure.

## 3. Implementation

Runtime:

- `apv3test/runtime/phase20_7/runtime.py`

Added:

- `PHASE20_10F_MEMORY_RHYTHM_ID`
- `_memory_consolidation_forgetting_review_rhythm(...)`
- `memory_consolidation_forgetting_rhythm` inside `learning_object_lifecycle`
- `merged_with_memory_rhythm_formula_id`
- merged 10f `action_deltas` into `lifecycle_action_deltas`

Workbench:

- `apv3test/web/static/phase20_7_workbench.js`

Added display-only trace:

- tick explanation for 10f memory rhythm
- lifecycle object bars for consolidation / forgetting / review rhythm / reconsolidation
- audit curves:
  - `对象:记忆巩固`
  - `对象:遗忘压力`
  - `对象:复习节律`
  - `对象:再巩固`

Tests:

- `tests/test_phase20_10f_memory_consolidation_forgetting_review_rhythm.py`

## 4. Acceptance

Passed:

- `pytest -q tests/test_phase20_10f_memory_consolidation_forgetting_review_rhythm.py -vv`
  - 2 passed
- `pytest -q tests/test_phase20_10*.py -vv`
  - 13 passed
- `pytest -q tests/test_phase20_9*.py -vv`
  - 76 passed
- `pytest -q tests/test_phase20_8*.py -vv`
  - 58 passed
- `pytest -q tests/test_phase20_7*.py -vv`
  - 48 passed
- `python -m py_compile apv3test/runtime/phase20_7/runtime.py apv3test/web_chat.py`
  - PASS
- `node --check apv3test/web/static/phase20_7_workbench.js`
  - PASS
- `python scripts/red_line_check_v14.py --phase 20.7-stage8`
  - PASS
- `python scripts/check_constant_governance.py`
  - PASS, with existing 91 experimental constant warnings

## 5. Plain Example

If AP learned:

`没错,你好聪明 -> 谢谢`

Then repeated private review and cold self-test can make `memory_consolidation` rise. That gently raises write/commit tendency and lowers unnecessary teacher request.

If later a cold self-test fails, `forgetting_pressure`, `review_rhythm_pressure`, and `reconsolidation_need` rise. AP becomes more likely to think privately, reread draft, ask, or revise, instead of blindly answering.

This is AP-native: the behavior comes from past traces and action competition, not from a hardcoded answer rule.

## 6. Boundaries

This step can prove:

- long-cycle memory rhythm is visible in the runtime trace
- cold success can consolidate memory tendency
- cold failure can raise forgetting/review/reconsolidation pressure
- the rhythm affects later action competition
- no direct answer path is created

This step cannot yet claim:

- complete L1/L2/L3 online embedding
- complete six-stage learning runtime
- full paradigm self-learning
- object-centric visual imagination completion
- mathematical column calculation completion
- a publish-final unrestricted open dialogue foundation

## 7. Next Step

Phase20.10g should connect this memory rhythm into structural generalization support itself.

Goal: when memory is consolidated, similar B candidates can receive a small AP-native support relief; when forgetting/regression is high, similar candidates should become more cautious and favor review/request/revision. This should reuse the same `ExperienceFlow / SSP / StatePool / B/C/C* / action competition` path and must not add a new answer module.
