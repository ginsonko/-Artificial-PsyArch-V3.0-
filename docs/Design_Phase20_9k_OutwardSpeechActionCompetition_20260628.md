# Phase20.9k Design: Outward Speech As AP Action Competition

Date: 2026-06-28

## Goal

Phase20.9k turns proactive visible speech into an AP-native action candidate, not a timer, greeting script, UI event, or reply shortcut.

The action is named `outward_speech`. It can only become visible after an idle private thought, learning review, or self-test has already been written into the short structure flow. The visible text must come from learned expression experience or DraftGrid expression fragments. If AP has not learned how to express the current state, the thought remains private.

## Whitepaper Mapping

AP whitepaper requires:

- Sensor / state pool / SSP / B-C-C* / feelings / action competition / actuator / feedback.
- Idle thought is private unless an action wins.
- Learned language expression should be bound to process states such as low grasp, unclosed pressure, fatigue, and feedback.
- Repetition fatigue and no-feedback pressure should suppress annoying repeated behavior.

Phase20.9k follows that path:

1. `idle_think`, `idle_learning_review`, or `idle_self_test` creates private narrative content.
2. The same private event writes a short-structure-flow occurrence.
3. `_outward_speech_candidate_from_idle_context(...)` computes a drive from:
   - private thought pressure,
   - unclosed value,
   - successor / learning pressure,
   - expression reward expectation,
   - repetition fatigue,
   - no-feedback penalty,
   - action outcome terms from prior `outward_speech` events.
4. `outward_speech` enters `_idle_competition(...)`.
5. If eligible and selected, DraftGrid writes characters through `outward_speech` then normal `write_cell` ticks.
6. `commit_reply` commits an `outward_speech` experience event.

The 2026-06-28 review rejected a separate outward intent layer. Experience tuning remains inside the existing action candidate as `action_outcome_terms`: prior `outward_speech` events, targeted teacher reward/punish, and lack of later external feedback change the next drive directly. This is treated as ordinary action consequence learning, not a new cognition entity.

## Formula

```text
private_thought_pressure =
    0.22
  + 0.34 * unclosed_value
  + 0.20 * successor_support
  + 0.22 * learning_pressure
  + 0.10 * short_structure_flow_support

reward_expectation =
    0.52 * learned_expression_support
  + 0.16 * referent_match

repetition_fatigue =
    min(0.42, 0.10 * recent_outward_count + 0.18 * recent_same_text_count)

drive =
    0.12
  + 0.42 * private_thought_pressure
  + 0.32 * reward_expectation
  + successor_bonus
  + action_outcome_reward_delta
  - repetition_fatigue
  - no_feedback_penalty
  - action_outcome_punish_delta
  - action_outcome_no_feedback_delta
  + feedback_relief
```

Eligibility:

```text
eligible = drive >= 0.50
```

The candidate is blocked when expression source is `innate_minimal_expression`. This keeps cold-start idle thought private until the user teaches AP how to externalize that kind of state.

## Review

Accepted:

- Uses existing private idle thoughts and short structure flow.
- Uses existing expression learning and fragment composition.
- Writes through DraftGrid and action records.
- Adds no answer table, regex route, hidden solver, timer template, or UI-owned cognition.
- Repetition/no-feedback suppression comes from experience events and action records.
- Rewarded or punished proactive speech changes later `outward_speech` drive as an action outcome term.

Rejected:

- Fixed interval proactive messages.
- Directly sending `narrative_text` to chat.
- New proactive-chat template list.
- Separate outward intent competition helper/entity.
- Treating successor prediction as an answer.

## Landing

Runtime file:

- `apv3test/runtime/phase20_7/runtime.py`

Tests:

- `tests/test_phase20_9k_outward_speech_action_competition.py`

Formula id:

- `apv3_phase20_9k_outward_speech_action_competition/v1`

## Human Example

User first teaches AP a way to say it is still thinking:

```text
User: phase20k maintain seed
AP: I don't know how to say this yet.
User teaches target AP expression: still thinking
```

Later:

```text
User: phase20k open unknown
AP: I don't know how to say this yet.

[idle tick]
private thought: the unclosed item is still pulling the short structure flow
action competition: outward_speech drive wins
AP: still thinking
```

If the user gives no feedback after this proactive speech, the next idle tick suppresses the same visible speech through no-feedback penalty and repetition fatigue.

## Workbench Test

1. Open the Phase20.7 workbench.
2. Send an unknown sentence twice so AP produces a maintain-unclosed expression.
3. Teach that AP expression, for example `我还在想这个`.
4. Send another unknown sentence.
5. Enable / click idle tick.
6. Expected: thought panel first shows private narrative; chat only receives a proactive message if `outward_speech` wins.
7. Click idle again without replying.
8. Expected: repeated proactive message is suppressed.

## Boundaries

This phase proves proactive visible speech can enter AP action competition from private thought. It still does not prove:

- full six-stage learning runtime,
- L1/L2/L3 online embeddings,
- complete paradigm self-learning,
- vertical arithmetic,
- object-centric visual imagination,
- mature long-horizon social initiative.
