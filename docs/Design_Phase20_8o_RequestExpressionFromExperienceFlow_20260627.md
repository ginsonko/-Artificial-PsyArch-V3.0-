# Phase20.8o 设计：request_teacher 表达从经验流中选择

日期：2026-06-27

## 1. 目标

Phase20.8n 已经把 `request_teacher` / `maintain_unclosed` 的行动驱动接入 low_grasp、unclosed、short_structure_flow、C*/StatePool carryover。Phase20.8o 继续收束表达内容：

- 不再把固定 `NO_CALL_TEXT` / `MAINTAIN_UNCLOSED_TEXT` 当成唯一表达来源。
- 优先从已有 ExperienceEvent / DraftGrid / teacher feedback expression correction 中选择表达。
- 固定文本只作为冷启动最低层先天表达，不作为长期唯一模板。

## 2. 白皮书约束

1. 不新增答案表、关键词路由、正则路由、隐藏求解器或学生侧 LLM。
2. 不把普通知识教学误当成 request_teacher 表达范式。
3. 表达候选必须来自 AP 已有主流程：DraftGrid 输出、teacher feedback、ExperienceEvent、action competition、SSP/ExperienceFlow。
4. 选择表达只决定“怎么请求教学/怎么表示还在想”，不决定具体问题答案。
5. 若没有表达经验，允许使用先天最低层表达作为冷启动本能。

## 3. 关键纠偏

普通教学：

```text
用户: 这是什么? + 图片
AP: 我还不太知道怎么说。
教师: 是苹果
```

这里的“是苹果”是知识对齐，不是 request_teacher 表达。它不能污染以后未知时的表达。

表达教学：

```text
AP 上一轮 DraftGrid commit: 我还不太知道怎么说。
教师反馈 target_event_id = 该 commit_event_id
教师: 你可以问我怎么说
```

这里的反馈明确指向 AP 自己的表达行动，因此可以沉淀为表达修正经验。

## 4. 数学形式

表达候选 `E_k` 来自两类已有经验：

```text
E_teacher = experience_alignment where payload.expression_role in compatible(intent)
E_draft = draft_grid_commit where payload.source_intent == intent and visible_chars exists
```

候选支持度：

```text
support(E_k) = unified_support(
  structural_similarity = role_match,
  occurrence_energy = expression_energy,
  recency = 1 / (1 + rank),
  modality_match = 1,
  reward = reward_k,
  punish = punish_k
)
```

最终选择：

```text
selected_expression = argmax_k support(E_k)
if no candidate:
  selected_expression = innate_minimal_expression(intent)
```

其中 `innate_minimal_expression` 是 AP 冷启动本能，不是答案知识。

## 5. 审查点

- expression correction 必须由 `target_event_id` 指向 `draft_grid_commit` / `draft_grid_write` 且该事件 `source_intent` 是 request/maintain。
- 普通知识教学没有 `expression_role`，不会进入表达候选。
- draft commit 只存 AP 自己已经写过的表达，不存用户答案表。
- tick trace 必须暴露 `request_expression_selection`，说明表达从哪里来。
- Stage0 不参与。

## 6. 验收标准

1. 冷启动未知输入仍可最低限度请求教学，但 trace 标注 innate fallback。
2. 对 AP 上一轮 request_teacher commit 做 targeted teacher feedback 后，后续未知输入会使用该表达。
3. 普通知识教学不会污染 request_teacher 表达。
4. maintain_unclosed 也能被 targeted expression feedback 修正。
5. 全链测试与红线扫描通过。
