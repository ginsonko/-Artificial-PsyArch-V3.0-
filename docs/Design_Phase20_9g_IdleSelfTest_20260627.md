# Phase20.9g 设计: teacher-off / cold-retest 闲时自测事件

日期: 2026-06-27

## 1. 目标

Phase20.9f 已经让 AP 在闲时把最近学习内容写入私有短期结构流。Phase20.9g 继续推进: 当后继闲时 tick 再次看到同一条学习复盘, 且 teacher-off 或 cold-retest 压力足够时, AP 生成一个私有自测事件。

这不是外部课程脚本, 也不是聊天回复。它只是 AP 沿着已有经验流和短期结构流做一次“我还能不能想起来”的内部验证。

## 2. AP 约束

本阶段遵守:

- 不新增数据库表。
- 不新增外部任务队列。
- 不新增聊天回复路线。
- 不根据用户文本关键字触发自测。
- 不把自测写进聊天框。
- 不把自测通过等同于完整学会。
- 自测必须从 `short_structure_flow::learning_review::*` 和既有经验对齐中长出来。

## 3. 信息流

```text
idle learning review occurrence
  -> latest experience alignment
  -> learning_loop_carryover
  -> self_test pressure gate
  -> idle_think private self-test tick
  -> short_structure_flow::self_test occurrence
```

关键原则:

- 第一个闲时 tick 先复盘, 不直接考试。
- 后继闲时 tick 才允许自测。
- feedback-only 仍以整理为主, 不强行自测。
- teacher-off / cold-retest 压力足够时, 自测成为私有 `idle_think`。

## 4. 数学形式

输入:

```text
R_prev = 最近 learning_review occurrence
M = 当前 idle_learning_review metric
T = M.teacher_off_readiness
C = M.cold_retest_readiness
F = M.feedback_only_readiness
target = M.target_text
```

门控:

```text
self_test_allowed =
  R_prev exists
  and target not empty
  and max(T, C) >= 0.34
  and F < max(T, C) + 0.18
```

自测类型:

```text
if C >= 0.72:
  self_test_kind = cold_retest_self_test
else:
  self_test_kind = teacher_off_self_test
```

自测把握:

```text
match_score = overlap(recalled_text, expected_text)
self_test_grasp =
  0.62 * match_score
  + 0.28 * max(T, C)
  + min(0.10, review_age_ticks * 0.02)
```

当前实现中, `recalled_text` 来自已有经验对齐的私有召回, 不写入聊天。

## 5. 对抗性审查

保留方案:

- 自测只在已有 `learning_review` 之后发生, 保证跨 tick。
- 自测仍然是 `idle_think`, 不是新的外部动作类型。
- 自测写入 `short_structure_flow::self_test::*`, 让后继 tick 可继续沿结构流召回。
- 自测结果包含 `subjective=True` 与 `may_be_wrong=True`, 保留拟人式不确定性。

拒绝方案:

- 拒绝刚教学完就立即考试。
- 拒绝把自测结果直接回复给用户。
- 拒绝把 expected/recalled 当外部标准答案表。
- 拒绝给系统增加课程调度器。

## 6. 验收标准

1. 教师退场召回后, 第一个 idle 是 `idle_learning_review`。
2. 第二个 idle 才生成 `idle_self_test`。
3. `idle_self_test.formula_id` 为 `apv3_phase20_9g_idle_self_test/v1`。
4. 自测 tick 的 `reply_text` 为空, `committed=False`。
5. 自测 tick 写入 `short_structure_flow::self_test::*` occurrence。
6. 自测 tick 有 forward recall 和 backward source trace。
7. feedback-only 阶段不会强行生成 self-test。
8. 全 Phase20 回归、红线扫描和 release demo 通过。

