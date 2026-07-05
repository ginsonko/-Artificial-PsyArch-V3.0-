# Phase20.9e 设计: 学习闭环指标回灌后继 tick 行动竞争

日期: 2026-06-27

## 1. 目标

Phase20.9c 已经把 `learning_loop_metrics` 写入每个真实 `RuntimeTickEvent.learning_deltas`。Phase20.9d 已经让工作台可以显示这些指标。

Phase20.9e 的目标是继续推进一步: 让这些闭环指标开始影响后继 tick 的行动竞争。它不是课程脚本, 不是回复捷径, 也不是新的学习状态机。它只是把上一 tick 已经形成的 AP-native 学习倾向, 作为下一 tick 行动竞争里的轻量能量调制。

小白解释:

- 第一次不会时, AP 会更容易请教或维持未闭合。
- 刚收到教学反馈时, AP 会更容易先写入和整合, 不急着继续乱问。
- 已经有可靠召回时, AP 会更容易尝试自己写, 即教师退场倾向上升。

## 2. AP 约束

本阶段必须遵守:

1. 不新增数据库表。
2. 不新增外部课程脚本。
3. 不新增回答候选。
4. 不根据用户文本关键字判断学习状态。
5. 不写死某个回复。
6. 不把 `teacher_off_readiness` 当成已经学会。
7. 不把 `cold_retest_readiness` 当成冷重测已经通过。
8. 所有影响都必须进入既有行动竞争, 而不是绕过 B/C/C* 或 DraftGrid。

## 3. 信息流

Phase20.9e 的位置:

```text
RuntimeTickEvent
  -> complete_every_tick_cognitive_cycle(...)
  -> learning_loop_metrics
  -> next tick learning_loop_carryover
  -> action competition row drive modulation
  -> selected action
```

关键点:

- `learning_loop_metrics` 仍然来自真实 tick。
- `_append_runtime_tick(...)` 在 tick 生成时立刻补全 B/C/C* 与学习指标, 让后继 tick 能读到它。
- `_learning_loop_carryover_from_events(...)` 从当前 turn 已完成 tick 中取最近一条闭环指标。
- `_apply_learning_loop_carryover_to_competition(...)` 只调制行动竞争 drive。

## 4. 数学形式

输入:

```text
F = feedback_only_readiness
T = teacher_off_readiness
C = cold_retest_readiness
S = scaffold_regression_need
```

主导倾向:

```text
dominant = argmax(F, T, C, S)
```

行动增益:

```text
request_teacher_delta    = 0.12 * S
maintain_unclosed_delta  = 0.10 * S + 0.04 * C
write_cell_delta         = 0.10 * F + 0.085 * T
commit_reply_delta       = 0.06 * T
idle_think_delta         = 0.08 * C + 0.04 * S
integrate_feedback_delta = 0.11 * F
```

行动竞争行:

```text
drive_after = clamp01(drive_before + delta(action_type))
```

边界字段:

```text
writes_answer_directly = false
creates_reply_candidate = false
```

这保证学习闭环只改变行动倾向, 不直接写答案。

## 5. 对抗性审查

保留方案:

- 把 carryover 放在行动竞争层, 因为白皮书里的学习不是外部课程状态, 而是把握感、未闭合感、反馈和经验流共同调制行动。
- `teacher_request_drive_context` 保留 `learning_loop_carryover` 作为审计来源, 但不在 context 内重复加权。
- 真正的 drive 改变只在 `_apply_learning_loop_carryover_to_competition(...)` 发生一次, 避免同一压力被算两次。

拒绝方案:

- 拒绝根据 `dominant_learning_tendency` 直接选择动作。
- 拒绝把 feedback-only 写成固定确认回复。
- 拒绝把 teacher-off 写成固定不请教。
- 拒绝把 cold-retest 写成外部定时任务。

## 6. 验收标准

1. 未知输入后, 后继 `request_teacher` 行动竞争行包含 `learning_loop_carryover`, 且 `request_teacher_delta > 0`。
2. 教师反馈后, 后继 `write_cell` 行动竞争行包含 `feedback_only` carryover, 且写入 drive 上升。
3. 已学 cue 再次召回后, 后继 `write_cell` 行动竞争行包含 `teacher_off_probe` carryover, 且写入 drive 上升。
4. 20.8n 的请教驱动仍然成立, 且分层关系为:

```text
drive_before_cstar_carryover
  = context.request_drive or context.maintain_drive
  + learning_loop_carryover_delta
```

5. 全链路 Phase20.7/20.8/20.9 回归通过。
6. 红线扫描无命中。
7. release demo 验证通过。

