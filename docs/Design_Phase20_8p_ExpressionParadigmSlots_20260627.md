# Phase20.8p 设计：表达范式槽位从经验流中涌现

日期：2026-06-27

## 1. 目标

Phase20.8o 已经证明 request_teacher / maintain_unclosed 的表达可以从 targeted expression feedback 与 DraftGrid commit 中选择。Phase20.8p 继续推进：让表达不只是“复用某一句反馈”，而是能根据当时 AP 自己的认知状态形成可审计的表达范式槽位。

本阶段仍不新增数据库表、不新增模板表、不新增关键词分类器。范式槽位是从已有 ExperienceEvent payload 与 teacher_request_drive_context 中派生出来的审计结构。

## 2. AP 约束

1. 表达范式只能来自 AP 自己曾经的表达行动与教师反馈。
2. 槽位由 AP 内部信号派生：low_grasp、unclosed_pull、short_structure_flow_support、cstar_pressure、intent。
3. 不从用户输入文字中抽关键词决定话术。
4. 不把表达范式写入普通 exact B0 / structural B / visual recall 答案通道。
5. 没有范式经验时仍允许先天最低层 fallback。

## 3. 数学形式

对一次 targeted expression feedback，其 target_event 是 AP 的 DraftGrid commit/write：

```text
T = target_event.payload.request_expression_selection.teacher_request_drive_context
```

派生范式槽位：

```text
slot = f(intent, low_grasp, unclosed_pull, short_flow, cstar_pressure)
```

默认规则：

```text
if intent == maintain_unclosed:
  slot = unclosed_maintenance
else if unclosed_pull >= 0.35:
  slot = unclosed_request
else if short_flow >= 0.50:
  slot = flow_continuation_request
else if low_grasp >= 0.70 and cstar_pressure >= 0.50:
  slot = low_grasp_pressure_request
else if low_grasp >= 0.70:
  slot = low_grasp_request
else:
  slot = general_request
```

选择时，对当前 tick 的 context 也派生同样 slot。候选支持度：

```text
support = unified_support(...)
        + 0.18 * exact_slot_match
        + 0.06 * family_slot_match
```

这不是答案生成，而是表达经验与当前认知状态之间的适配。

## 4. 审查要点

- `expression_paradigm_slot` 只写入 expression feedback alignment payload。
- 普通知识教学没有 `expression_role` / `expression_paradigm_slot`。
- 普通答案召回继续排除带 `expression_role` 的 alignment。
- tick trace 暴露 `selected_paradigm_slot` 与当前 slot。
- request_teacher 与 maintain_unclosed 不跨 intent 混用。

## 5. 验收标准

1. targeted expression feedback 会保存 `expression_paradigm_slot`。
2. 当前 request context 会产生 `current_paradigm_slot`。
3. 多个 request 表达候选竞争时，slot 匹配的候选优先。
4. maintain_unclosed 使用自己的 `unclosed_maintenance` 槽位。
5. 普通知识教学不产生表达槽位、不污染普通答案召回。
