# Phase20.8n request_teacher 统一驱动设计

日期: 2026-06-27

## 1. 目标

Phase20.8m 已经把未闭合 idle_think successor 收束到统一 ExperienceFlow /
UnifiedCandidate 竞争。Phase20.8n 的目标是继续收束 `request_teacher`：
它不再是固定 0.75 的低把握动作，而是由低把握、未闭合压力、短期结构流、
StatePool/C* carryover 共同驱动。

## 2. 白皮书约束

1. 不新增数据库表，不新增答案表，不新增关键词/正则路由。
2. request_teacher 只能表达“需要教学/确认”的行动倾向，不能决定具体答案。
3. 主动询问内容仍通过 DraftGrid/已学表达承载，本阶段只先统一 drive 和审计。
4. low grasp、unclosed、short_structure_flow、C* carryover 都是已有 AP 流程信号。
5. unknown / weak 路径可以提高 request drive，但不能 fake B。

## 3. 数学形式

```text
low_grasp = 1 - max(exact_b0.support, structural_b.support, 0)
unclosed_pull = active_unclosed.u_value
short_flow = max_support(short_structure_flow_next)
cstar_pressure = max(carryover.pressure_support, carryover.max_carry)

request_drive = clamp(
  0.20
  + 0.30 * low_grasp
  + 0.18 * unclosed_pull
  + 0.14 * short_flow
  + 0.12 * cstar_pressure,
  0.05,
  0.95
)
```

`maintain_unclosed` 使用同一上下文，但更偏向 `unclosed_pull`。

## 4. 审查要点

1. context 只调制 action competition / action record / feelings / unclosed reason。
2. context 不写 reply，不创建 output candidate。
3. Stage0 不参与。
4. 旧 Stage4 request_teacher 行为保留，但审计来源从固定常数变为统一公式。

## 5. 验收标准

1. unknown request_teacher tick 的 action competition 含 `teacher_request_drive_context`。
2. request_teacher selected drive 来自公式，不是固定裸 0.75。
3. unclosed reason 记录同一 drive context。
4. maintain_unclosed 也带统一 drive context。
5. no fake B / no direct reply / 红线无命中。

