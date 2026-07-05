# Phase20.10g Memory Rhythm Structural-B Support

Date: 2026-06-29

Formula:

`apv3_phase20_10g_memory_rhythm_structural_b_support/v1`

## 1. Design

Phase20.10g connects Phase20.10f memory rhythm to structural generalization B support.

The intended AP-native effect:

- when a learning object is repeatedly reviewed, self-tested, and cold-retest-stable, similar structural B candidates receive a small support relief;
- when the same object shows forgetting, review pressure, regression, or reconsolidation need, similar structural B candidates receive a guard penalty;
- the result remains subjective and may be wrong, like human confidence and hesitation.

This is not a new answer path. It only changes B candidate support and acceptance threshold terms.

## 2. No-New-Entity Review

10g does not add:

- new memory table
- new generalization module
- new answer table
- keyword route
- hidden solver
- external review scheduler

It reuses:

- ExperienceFlow alignment candidates
- SSP review/self-test occurrences
- 10d long interval cold retest window
- 10e cold retest confidence tuning
- 10f memory consolidation / forgetting / review rhythm
- existing structural B support and acceptance threshold

The output is a candidate audit slot and support terms inside the existing structural B path.

## 3. Implementation

Runtime:

- `apv3test/runtime/phase20_7/runtime.py`

Added:

- `PHASE20_10G_MEMORY_RHYTHM_B_SUPPORT_ID`
- `_memory_rhythm_structural_b_support_for_alignment(...)`
- `_inactive_memory_rhythm_structural_b_support(...)`

Modified:

- `_find_structural_b(...)`
  - reads 10g projection per structural alignment candidate
  - adds `memory_rhythm_support_boost`
  - adds `memory_rhythm_guard_penalty`
  - exposes `memory_rhythm_structural_b_support` in `candidate_audit_slots`
  - exposes support terms for audit

- `_structural_b_acceptance_threshold(...)`
  - adds `memory_rhythm_relief`
  - adds `memory_rhythm_guard`

Tests:

- `tests/test_phase20_10g_memory_rhythm_structural_b_support.py`

## 4. Acceptance

Passed:

- `pytest -q tests/test_phase20_10g_memory_rhythm_structural_b_support.py -vv`
  - 2 passed
- `pytest -q tests/test_phase20_10*.py -vv`
  - 15 passed
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

and later repeatedly reviews and cold-tests it successfully, then the partial cue:

`你好聪明`

can receive structural B support relief from memory rhythm. AP becomes a little more willing to use the similar memory.

If cold self-test later fails, the same partial cue receives a guard penalty. AP becomes more likely to review, ask, or revise instead of blindly relying on that memory.

This is still AP-native: the support comes from prior experience traces and B competition, not from a hardcoded text rule.

## 6. Boundaries

This step can prove:

- 10f memory rhythm can affect structural B support;
- consolidated memory can relieve structural B acceptance;
- forgetting/reconsolidation pressure can guard structural B generalization;
- all effects are visible in `support_terms` and `candidate_audit_slots`;
- no direct answer path was created.

This step cannot yet claim:

- full L1/L2/L3 online embedding;
- complete paradigm self-learning;
- mathematical column calculation;
- object-centric visual imagination completion;
- final unrestricted open dialogue foundation.

## 7. Next Step

Phase20.10h should connect structural B rhythm confidence into C* and DraftGrid consequence evaluation.

Goal: when a B candidate is rhythm-consolidated, C* should carry higher subjective grasp into draft writing; when it is rhythm-guarded, C* should increase uncertainty, revision, review, or teacher-request pressure. This must remain inside B/C/C*, DraftGrid, and action competition.
