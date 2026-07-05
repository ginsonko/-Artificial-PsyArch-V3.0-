# Phase20.8g Exact B0 索引回读与默认 weak B/C 统一候选统计设计

日期: 2026-06-27

## 1. 设计目标

Phase20.8f 已将 structural B 与 visual B0 收束到 `UnifiedExperienceCandidate`。本阶段继续处理两个残留路径:

1. `_find_exact_b0(...)` 的 `phase20_7_exact_b0_index` 命中后仍可直接返回 `_ExactB0`。
2. `complete_every_tick_cognitive_cycle(...)` 的默认 weak B/C 只基于当前 tick 的状态池、执行器和内心图像补证据，尚未统计已有 unified candidate 审计槽。

Phase20.8g 的目标:

```text
exact_b0_index hit
  -> alignment event
  -> UnifiedExperienceCandidate
  -> ExactB0

RuntimeTickEvent weak B/C fallback
  -> existing b_candidates/c_backward/visual/audio/state evidence
  -> unified_candidate_statistics
  -> C* audit
```

## 2. 白皮书约束

1. 索引是加速层，不是真相来源。
2. 如果索引命中但无法回到经验流 alignment event，不允许直接返回答案。
3. 默认 weak B/C 不能创造新的候选实体，只能统计本 tick 已有审计槽和状态池证据。
4. 不新增 keyword/regex/answer table/hidden solver/student-side LLM。
5. 本阶段仍不能声称六阶段学习、L1/L2/L3 在线嵌入、完整范式自学习已经完成。

## 3. 数学与审计形式

Exact B0 索引回读:

```text
index(input_signature)
  -> alignment_event_id
  -> unified_candidate(alignment_event_id)
  -> ExactB0(
       support=max(index_support, unified_support),
       support_terms=unified_terms + exact_b0_index_support
     )
```

weak B/C 统一统计:

```text
unified_candidate_statistics =
  count(unified_experience_candidate slots)
  max_support
  candidate_kinds
  support_formulas
```

这些统计进入:

- `tick_evidence_b.unified_candidate_statistics`
- default `c_backward.cause_slots`
- default `cstar_packet.unified_candidate_statistics`

## 4. 验收标准

1. exact B0 索引命中后，`b_candidates[0]` 仍为 `exact_b0`，但包含 `support_formula`、`support_terms`、`unified_experience_candidate`。
2. unknown/default weak B tick 的 `cstar_packet.tick_evidence_b` 包含 `unified_candidate_statistics`。
3. Stage0 不被补成认知 tick。
4. Phase20.7/20.8 指定全量回归通过。
5. 红线扫描无命中。
