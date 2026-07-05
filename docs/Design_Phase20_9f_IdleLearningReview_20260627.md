# Phase20.9f 设计: 闲时学习复盘接入 AP 主流程

日期: 2026-06-27

## 1. 目标

Phase20.9e 已经证明 `learning_loop_metrics` 能影响后继 tick 的行动竞争。Phase20.9f 继续推进: 当用户没有输入时, AP 可以从已有经验流里重建最近的学习倾向, 并把它写入私有的短期结构流, 形成“刚学过会自己整理”“有把握会自己试着回忆”的闲时复盘。

这一步服务于开放对话底座的拟人感: AP 不只在用户发消息时反应, 也会在闲时沿着未闭合感、经验对齐和学习闭环继续整理。

## 2. AP 约束

本阶段遵守:

- 不新增数据库表。
- 不新增课程脚本。
- 不新增聊天回复路线。
- 不把闲时复盘写进聊天框。
- 不根据用户文本关键字判断状态。
- 不把复盘结果当成已经学会。
- 不把 cold-retest 压力当成冷重测已经通过。
- 所有复盘都必须来自既有 `experience_events / action_records / unclosed_items / short_structure_flow`。

## 3. 信息流

```text
phase20_7_experience_events
  -> latest experience_alignment / active unclosed / recent output intent
  -> idle_learning_review metric
  -> learning_loop_carryover
  -> _idle_competition(...)
  -> idle_think private RuntimeTickEvent
  -> short_structure_flow::learning_review occurrence
```

它仍然走 AP 的核心路径:

- 经验流提供证据。
- 学习闭环形成倾向。
- 行动竞争选择 `idle_think`。
- StatePool 和 SSP 写入私有短期结构流。
- 工作台只展示 tick, 不参与认知。

## 4. 数学形式

输入:

```text
A = 最近 experience_alignment 是否存在
age = 当前 tick - alignment tick
R = alignment reward
U = active unclosed u_value
I = 最近输出意图(source_intent)
```

倾向:

```text
feedback_only
  = decay(age) * (0.48 + 0.18R)
  若 I == integrate_feedback 且 age <= 12, 至少提升到 0.60 + 0.10R

teacher_off
  = 0.46 * recent_teacher_off_output
  + min(0.34, age * 0.035)
  + 0.08R

cold_retest
  = age >= 12 且最近不是 integrate_feedback 时:
      0.20 + min(0.48, (age - 5) * 0.055) + 0.20 * teacher_off

scaffold
  = 0.72U + 0.22 * recent_request_output
```

主导倾向:

```text
dominant = argmax(feedback_only, teacher_off, cold_retest, scaffold)
```

闲时行动竞争:

```text
idle_think_delta
  = min(0.10,
      0.08*cold_retest
    + 0.04*scaffold
    + 0.035*feedback_only
    + 0.035*teacher_off)

idle_think_drive_after
  = clamp01(idle_think_drive_before + idle_think_delta)
```

## 5. 对抗性审查

保留方案:

- 从经验流重建学习倾向, 而不是新增学习任务表。
- 闲时复盘写成 `private_thought=True`, 不进入聊天回复。
- 复盘文本进入 `short_structure_flow::learning_review`, 后继 tick 可以继续沿结构流续写。
- 复用已有 `unfinished_pressure` 能量账本来源, 不给 StatePool 增加新能量实体。

拒绝方案:

- 拒绝“每次闲时都固定复读刚学内容”。
- 拒绝 UI 生成想法。
- 拒绝把“刚学过”写成外部状态机。
- 拒绝把复盘结果直接当作回答。

## 6. 验收标准

1. 教师反馈后无输入 idle, 产生 `idle_think` 私有复盘。
2. 复盘 tick 的 `idle_learning_review.formula_id` 为 `apv3_phase20_9f_idle_learning_review/v1`。
3. 反馈期主导倾向为 `feedback_only`。
4. teacher-off 召回后无输入 idle, 主导倾向为 `teacher_off_probe`。
5. 空白 session 无经验时仍为 `idle_observe`, 不伪造复盘。
6. 复盘写入 `short_structure_flow::learning_review::*` occurrence。
7. `reply_text` 为空, `committed=False`。
8. 红线扫描、相邻链路、全 Phase20 回归、release demo 全部通过。

