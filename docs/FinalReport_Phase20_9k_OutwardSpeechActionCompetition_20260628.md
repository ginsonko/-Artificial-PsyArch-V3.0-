# Phase20.9k Final Report: Outward Speech Action Competition

Date: 2026-06-28

## Completed

Phase20.9k implements proactive visible speech as an AP-native action candidate.

Implemented:

- Added `PHASE20_9K_OUTWARD_SPEECH_ID`.
- Added `outward_speech` into `_idle_competition(...)`.
- Added `_outward_speech_candidate_from_idle_context(...)`.
- Added no-feedback penalty and repetition fatigue from real event/action history.
- Added `_maybe_commit_outward_speech_from_idle_result(...)` for idle review/self-test paths.
- Added `_commit_outward_speech_from_private_thought(...)` so visible proactive speech goes through DraftGrid and commit trace.
- Added `action_outcome_terms` inside the existing `outward_speech` candidate, so targeted teacher reward/punish and no-feedback history can tune the same action drive.
- Removed the rejected separate outward intent competition experiment; no Phase20.9l entity remains.
- Added tests for silent cold start, learned expression externalization, feedback/fatigue suppression, and rewarded action-outcome tuning.

## Effect

Readable example:

```text
Teach: when AP is still thinking, it may say "still thinking".

User: phase20k open unknown
AP: I do not know yet.

Idle tick:
private thought is created first.
outward_speech competes with idle_think, idle_visual_focus, idle_audio_focus, idle_observe, sleep_lower_frequency.
If its drive wins, AP writes through DraftGrid.

AP: still thinking

Next idle tick without user feedback:
same outward speech is suppressed by repetition_fatigue and no_feedback_penalty.

If the user explicitly rewards that proactive speech, the next similar idle situation raises the same `outward_speech` action's `action_outcome_reward_delta`. The decision still stays in `_idle_competition(...)`; no extra outward-intent module is involved.
```

## Validation

Passed:

```powershell
python -m py_compile apv3test\runtime\phase20_7\runtime.py
python -m pytest tests\test_phase20_9k_outward_speech_action_competition.py -q
python -m pytest tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8q_draftgrid_expression_fragment_composition.py -q
python -m pytest tests\test_phase20_9f_idle_learning_review.py tests\test_phase20_9g_idle_self_test.py tests\test_phase20_9h_self_test_feedback.py tests\test_phase20_9i_workbench_learning_lifecycle.py tests\test_phase20_9j_structural_generalization_value_modulation.py -q
```

Rejected outward-intent experiment string scan: no runtime, test, or doc residue.

## AP Purity Check

No added:

- keyword route,
- regex route,
- answer table,
- hidden solver,
- timer greeting,
- UI-owned cognition,
- fixed proactive template list,
- direct narrative-to-chat shortcut.
- separate outward-intent controller/entity.

The visible text is learned expression material selected through the existing expression flow. The action is visible only after AP has a private thought and an eligible action candidate.

## Boundaries

Can now claim:

- proactive visible speech exists as an AP action candidate,
- private idle thought remains private unless outward speech wins,
- learned expression support and reward expectation can make it speak,
- repetition and lack of feedback suppress repeated proactive messages.
- explicit user/teacher reward can raise later same-action outward speech drive through existing experience flow.

Still cannot claim:

- complete six-stage runtime,
- L1/L2/L3 online embeddings,
- complete paradigm self-learning,
- mathematical vertical calculation,
- object-centric visual imagination,
- mature long-horizon autonomous social behavior.
