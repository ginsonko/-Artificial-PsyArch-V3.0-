# APV3.0test Phase20.9q 奖惩调制溯源巩固与 DraftGrid 回读回流设计稿

日期: 2026-06-28

## 1. 设计

Phase20.9q 的目标是把两个理论点接成同一条 AP 主流程:

```text
每 tick C_backward 溯源
+ 奖惩信号
+ eligibility trace
+ DraftGrid SELF_DRAFT_GRID 回读
-> SSP/ExperienceFlow 可召回结构
-> 后继 B/C/C*、行动竞争和学习倾向变化
```

这一步不新增“信念模块”“迷信模块”“强迫模块”“编辑模块”或“外显意图模块”。所有现象都必须由现有 AP 信息流产生:

```text
sensor/receptor
-> StatePool
-> SSP occurrence/edge
-> ExperienceFlow
-> B/C_forward/C_backward/C*
-> cognitive feeling
-> action competition
-> DraftGrid/actuator
-> reward/punish feedback
```

## 2. 理论合并点

### 2.1 奖惩调制 C_backward 归因

奖励或惩罚出现时, AP 应读取同 tick 或近邻 tick 的 C_backward cause_slot、SSP occurrence/edge、注意焦点和行动记录, 对当前最像“因”的对象进行可动摇巩固:

```text
AttributionConsolidation(o_i, result_t)
  = CauseFeeling(o_i -> result_t)
  * attention_i
  * eligibility_trace_i
  * result_intensity(reward_t, punish_t)
  * source_context_weight_i
```

奖励提高期待、注意偏置和主观因果把握。惩罚提高压力、抑制和替代搜索倾向。它们都是权重变化, 不是绝对真理。

### 2.2 DraftGrid 回读回流

`read_draft` 不是 UI 展示, 而是 AP 对自己草稿的感受器输入。它必须:

1. 写入 `phase20_7_experience_events`.
2. 写入 `phase20_7_occurrences`, substrate 为 `SELF_DRAFT_GRID`.
3. 建立与前序 `draft_grid_write`、后续 `draft_grid_commit`、教师反馈事件的 SSP edge.
4. 进入统一 ExperienceFlow query.
5. 参与后继 C_backward 的“我为什么这样写/哪里不顺”归因.
6. 参与后继 C_forward 的“继续写/修改/停下/提交”后果预测.

## 3. 当前底座符合性审查

### 3.1 已符合

1. `read_draft` 已经是真实行动记录, 不是前端假展示.
2. `draft_grid_read` 已写入 `phase20_7_experience_events`.
3. `continue_writing/read_draft/edit_cell/stop_generating` 已进入同一行动竞争 trace.
4. `commit_reply` 固定高 drive 已下沉到 DraftGrid、B/C/C*、压力、疲劳和学习闭环信号.
5. 当前代码保留 `writes_answer_directly=false`、`creates_reply_candidate=false` 这类红线审计字段.

### 3.2 仍不够 AP-native 的点

1. `draft_grid_read` 目前主要是 event, 还没有充分写成 SSP occurrence/edge. 这会导致回读不够像“AP 看见自己写的东西”, 更像“历史日志里有一条记录”.
2. 奖惩目前影响 candidate support 和反馈整合 drive, 但还没有统一读取 C_backward cause_slot 来巩固“当时被溯源为因的对象”.
3. 惩罚后的替代搜索、冻结、回避、求助、检查等倾向还没有充分从同一归因巩固中长出来.
4. `edit_cell` 仍是候选审计, 因为缺少从回读冲突和 C* 产生替代单元的路径. 这一步不能用隐藏编辑规则补.
5. 低把握泛化的奖励/惩罚经验还需要更直接影响后续 “回复/请教/继续想/不说” 行动竞争.

## 4. Phase20.9q 落地方案

### 4.1 DraftGrid readback occurrence

在 `read_draft` 真实执行后, 追加:

```text
sa_type_id = SELF_DRAFT_GRID:readback:<visible_text_hash 或 cell signature>
substrate = SELF_DRAFT_GRID
modality = text/draft_grid
occurrence R = draft_visible_energy
occurrence V = expected_readback_value
occurrence A = read_draft action drive
occurrence P = conflict_or_unclosed_pressure
payload_ref = draft_grid_read payload ref or event_id
```

并建立 edge:

```text
draft_grid_write -> draft_grid_read
draft_grid_read -> draft_grid_commit
draft_grid_read -> teacher_feedback_event
draft_grid_read -> edit_cell candidate
```

这些 edge 只是 SSP 结构关系, 不写答案.

### 4.2 奖惩调制归因巩固 trace

在教师反馈、用户确认/否定、自测成功/失败、行动结果反馈处, 生成一个派生学习 delta:

```text
reward_punish_backward_attribution_consolidation:
  result_event_id
  reward
  punish
  cause_slots_from_c_backward
  eligible_occurrences
  eligible_edges
  attribution_consolidation_score
  expected_reward_delta
  expected_punish_delta
  attention_bias_delta
  inhibition_delta
  alternative_search_delta
  subjective = true
  may_be_wrong = true
  writes_answer_directly = false
```

这可以先作为 `learning_deltas` 和 SSP/ExperienceFlow 可查证据, 后续再用于 L3 在线嵌入.

### 4.3 行动竞争读取同一结果

不新增行动实体, 只让现有行动候选读取该巩固结果:

```text
commit_reply:
  + expected_reward_delta
  - expected_punish_delta
  - conflict_pressure

request_teacher:
  + expected_punish_delta
  + unresolved_pressure
  + low_grasp
  - recent_request_fatigue

continue_writing:
  + successor_pressure
  + readback_unclosed
  - overrun_fatigue

read_draft:
  + draft_uncertainty
  + recent_write_without_read
  + expected_error_pressure

edit_cell:
  + readback_conflict
  + available_alternative_unit_from_Cstar
  - no_alternative_unit_gate

stop_generating:
  + pressure_released
  + repetition_fatigue
  - unresolved_pressure
```

### 4.4 低把握泛化学习

用户提到的 “没错, 你好聪明” -> “你好聪明” 应走同一机制:

1. “你好聪明”部分匹配召回历史 B 对象.
2. C_backward 发现它来自被奖励的肯定/夸奖语境.
3. 若过去低把握使用相似召回后得到奖励, `expected_reward_delta` 提高.
4. 行动竞争更敢 commit 或给出低把握但合理回应.
5. 若被纠正或惩罚, 后续同类低把握泛化更倾向 request_teacher 或 maintain_unclosed.

这不是调一个固定 grasp 阈值, 而是让阈值被奖惩和归因经验塑形.

## 5. 严谨验收标准

### 5.1 DraftGrid 回读

1. 一次回复必须产生 `draft_grid_write -> draft_grid_read -> draft_grid_commit`.
2. `draft_grid_read` 必须有对应 `SELF_DRAFT_GRID` occurrence.
3. 后继 tick 的 C_backward cause_slots 能看到 readback occurrence.
4. `read_draft` 后的 commit/read/edit/stop drive 与 readback trace 有可审计关系.

### 5.2 奖励归因

场景:

```text
用户: 没错,你好聪明
教学/奖励: 嗯
用户: 你好聪明
```

验收:

1. “你好聪明”能部分召回 “没错,你好聪明”.
2. tick 回放显示 shared/residual 结构.
3. C_backward 显示奖励语境 cause_slot.
4. 行动竞争显示 `expected_reward_delta` 或同等学习 delta.
5. 回复倾向高于未奖励前, 但仍保留低把握/可能错的主观标记.

### 5.3 惩罚归因

场景:

```text
AP 低把握泛化回复
用户纠正/惩罚
相似输入再次出现
```

验收:

1. 相似召回仍存在, 不硬删.
2. C_backward 能显示曾经失败/纠正的 cause_slot.
3. request_teacher、maintain_unclosed、read_draft 或 edit_cell drive 上升.
4. commit_reply drive 相对下降.
5. 学习 delta 标记 `may_be_wrong=true`, 不变成全局禁用.

### 5.4 拟人伪因果

场景:

```text
AP 做某个动作/想法 A 后偶然获得奖励
下一次相似期待出现
```

验收:

1. A 的注意偏置或行动倾向上升.
2. 多次无奖励或反例后, A 的因果把握下降.
3. 代码中没有 A 专属规则、关键词规则或迷信表.

## 6. 红线

1. 不新增 belief/superstition/compulsion 专属实体.
2. 不新增基于文本内容的关键词判断.
3. 不新增答案表、完整回复表、隐藏求解器或 LLM.
4. 不让 UI 生成认知结论.
5. 不让 DraftGrid edit 依赖隐藏字符串替换规则.
6. 不把伪因果天生过滤掉.

## 7. 对抗性审查

### 7.1 可能的问题

1. 如果奖惩巩固太强, AP 会过度迷信和重复动作.
2. 如果惩罚抑制太强, AP 会过度不敢说、不敢试.
3. 如果 readback occurrence 只写入不参与 query, 仍然是日志装饰.
4. 如果 edit_cell 没有 alternative unit 就执行, 会变成隐藏编辑器.
5. 如果为了展示“像人”而让 idle 或 UI 编造内心活动, 会破坏 AP 纯度.

### 7.2 修正原则

1. 所有巩固都必须是可动摇权重, 不是绝对规则.
2. 强化和抑制都必须有衰减、疲劳、反例和 source context.
3. readback 必须进入 SSP/ExperienceFlow 并影响后继 tick, 才能算完成.
4. edit_cell 必须等待 C* 产生替代单元.
5. 小白展示页只能展示 RuntimeTickEvent 和 memory delta, 不能自己生成解释.

## 8. 下一步实施顺序

1. 给 `draft_grid_read` 补 `SELF_DRAFT_GRID` occurrence 和 write/read/commit/feedback edges.
2. 让 ExperienceFlow query 把 `draft_grid_read` candidate 纳入统一候选.
3. 在 C_backward 中暴露 readback cause_slot 与 neutralized occurrences.
4. 加入 reward/punish backward attribution consolidation learning delta.
5. 让行动竞争读取该 delta, 优先影响 commit/request/read/edit/stop.
6. 新增 Phase20.9q 测试和小白 HTML 展示页.
7. 跑 Phase20.9、Phase20.8、Phase20.7 回归与红线扫描.

