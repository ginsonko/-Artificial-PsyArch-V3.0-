# Phase20.8r 设计：当前认知指向绑定到表达范式

日期：2026-06-27

## 1. 目标

Phase20.8q 已经让 `request_teacher / maintain_unclosed` 的表达能够从已学表达经验中抽取片段并组合。Phase20.8r 继续把这些表达和当前 AP 内部真正正在指向的认知对象绑定起来，让 AP 在不知道、困惑、未闭合时，不只是学会“我不懂”这一类表达，还能逐步学会围绕“这张图 / 当前文字 / 未闭合对象 / 刚才声音”这类当前认知指向组织表达。

本阶段仍然不新增答案通道、不新增模态专用回复路线、不从用户输入关键字触发模板。当前指向只作为 AP 内部状态的一个可审计摘要，来源于已有 observation、unclosed、短期结构流和 C* carryover。

## 2. AP 约束

1. `current_referent` 只能从现有 AP 流程产生：`_ObservationLike`、`active_unclosed`、`short_structure_flow_support`、`cstar_pressure`。
2. `current_referent` 只调制表达经验的竞争，不生成知识答案。
3. 教师针对 AP 表达的反馈会保存当时的 `expression_referent`；普通知识教学不会进入表达池。
4. 带 `expression_role` 的 alignment 继续被 exact/structural/visual recall 排除，避免把“怎么表达不懂”误当成“问题答案”。
5. 没有已学 referent 表达时，只保留 trace，不伪造“这张图/这个地方”等成熟表达。

## 3. 数学形式

当前表达驱动力仍由 20.8n 给出：

```text
D_request = f(low_grasp, unclosed_pull, short_flow_support, cstar_pressure)
```

20.8r 在同一上下文中派生当前认知指向：

```text
R_now = g(observation, intent, unclosed, short_flow, C*)
```

其中：

```text
referent_kind =
  unclosed_current | visual_focus | audio_focus | multimodal_focus | text_focus | structure_focus | none
```

表达候选 `E_k` 由 20.8o/p/q 给出，若候选来自 targeted expression feedback，则携带当时的：

```text
R_k = expression_referent(E_k)
```

当前指向与候选指向的匹配：

```text
referent_match =
  0.45 * same_kind
+ 0.28 * modality_overlap
+ 0.18 * same_visual
+ 0.12 * same_text
+ 0.16 * unclosed_match
```

表达候选支持度更新为：

```text
support'_k = clamp(support_k + paradigm_term + min(0.16, referent_match * 0.16))
```

候选排序：

```text
sort_key = (support', referent_match, paradigm_match, recency)
```

片段组合时，如果当前 referent active，优先从同槽位且 referent_match > 0 的候选中抽片段；不足两条时回退到 20.8q 的同槽位组合。

## 4. 与人类过程的对应

人类不会只有一句抽象的“我不知道”。人在看图时会更容易说“这个我没看懂”，在听到声音后会说“刚才那个声音是什么”，在心里有未完成任务时会说“我还没弄完那个”。这种表达不是一个单独的模板系统，而是当前注意对象、未闭合感、把握感、语言经验共同竞争后的结果。

20.8r 对应的是：先有内部指向，再学习如何把这个指向说出来。冷启动时 AP 只知道自己低把握，随着教师针对 AP 表达进行纠正，表达经验会携带当时的认知指向，下次相似指向出现时自然更容易被召回。

## 5. 审查结论

设计审查后保留的方案：

- 保存 `current_referent` 为 trace 和 expression alignment payload，不新建数据库表。
- 用 referent 匹配调制表达候选，不直接写入答案。
- 视觉焦点的“这张图片”锚点不算文本模态，而归入 `visual_focus`，避免视觉表达和文本表达错误混用。
- 支持同 referent 的表达片段组合，但没有足够经验时不假装会指称。

放弃的方案：

- 不硬编码输出“这张图/刚才声音/这个地方”。
- 不新增 `visual_request_expression`、`audio_request_expression` 之类分支。
- 不把用户文本里的指代词作为主触发器。

## 6. 验收标准

1. 视觉未知输入形成 `current_referent.referent_kind = visual_focus`，且模态为 `vision`。
2. 文本未知输入形成 `current_referent.referent_kind = text_focus`，且模态为 `text`。
3. 视觉表达经验和文本表达经验同时存在时，当前 referent 能调制候选竞争。
4. 同视觉 referent 下至少两条表达经验可被 20.8q 片段组合复用。
5. 无表达经验时只保留 trace，不创建答案候选。
6. Phase20.8 全链、Phase20.7+20.8 总链、红线扫描通过。
