# Phase20.8q 设计：DraftGrid 表达片段组合

日期：2026-06-27

## 1. 目标

Phase20.8p 已经让 request_teacher / maintain_unclosed 的表达带上 AP 内部范式槽位。Phase20.8q 继续推进：让 AP 不只选择一句完整表达，而能从已有表达经验中提取片段，再按当前范式槽位组合输出。

本阶段仍不新增数据库表、不新增模板表、不按用户输入关键词触发话术。片段来自已有 expression alignment / DraftGrid commit，是经验流的派生视图。

## 2. AP 约束

1. 片段只能来自 AP 已经写过或教师已针对 AP 表达反馈过的表达。
2. 片段组合只服务 request_teacher / maintain_unclosed 的表达，不产生知识答案。
3. 普通知识教学不进入表达片段池。
4. 带 `expression_role` 的 alignment 仍被普通答案召回排除。
5. 组合结果必须进入 DraftGrid 逐字符写入，并在 tick trace 中可审计。

## 3. 数学形式

对当前表达状态：

```text
current_slot = f(intent, low_grasp, unclosed_pull, short_flow, cstar_pressure)
```

候选表达 `E_k` 已有支持度 `support_k`。从候选文本切出片段：

```text
fragments(E_k) = split_by_observed_expression_boundary(E_k.text)
```

片段评分：

```text
fragment_score = support_k
               + 0.18 * exact_slot_match
               + 0.06 * family_slot_match
               + reward_bias
               - duplicate_penalty
```

组合：

```text
selected_fragments = top diverse fragments from compatible candidates
output = join(selected_fragments)
```

若只有一个可用片段，回退到 8p 的整句选择；若没有候选，回退到先天最低层表达。

## 4. 审查要点

- 不把片段持久化成新表。
- 不从用户输入文本中抽关键词。
- 不把组合结果写入 exact B0 答案索引。
- `request_expression_selection` 必须记录 `composition_kind`、fragment 来源、source event ids、formula id。
- maintain_unclosed 与 request_teacher 不跨 intent 混用。

## 5. 验收标准

1. 两条同槽位 targeted expression feedback 可被组合成新表达。
2. 组合 trace 记录多个 source event 与 fragment 列表。
3. 单候选时仍保持 8p 的整句选择。
4. maintain_unclosed 可组合自己的片段。
5. 全链与红线扫描通过。
