# AP 统一溯源与主观归因竞争冷保存 v0

日期: 2026-06-26

定位: 本文是《AP底层原理白皮书 v0.4》中 C_backward / 追溯认知章节的细化补丁, 也是 Phase20.7 后续实现纠偏的前置设计。它替代“视觉专用追溯补丁”思路, 将“刚刚那张图”“你刚才说的”“继续”“没错”“为什么会这样”“我是不是见过这个”等现象统一为 AP 的来源缺口、主观归因竞争、解释回灌和后天修正过程。

## 0. 结论摘要

上一轮为修复图片教学问题写出的视觉专用逻辑可以作为临时桥, 但不是 AP-native 的最终方案。最终方案不应有“图片指代模块”“文本指代模块”“最近图片恢复函数”等模态专用实体。AP 应当只有统一的状态池、短期结构池、统一经验流、B/C/C*、认知感受与行动竞争。

溯源不是识别图片, 也不是理解某个词。溯源是每个 tick 面对“当前状态无法自足解释”时, 从短期结构池和统一经验流中寻找可能来源的主观解释竞争。候选可以来自任意模态、任意时间距离、任意空间距离和任意内部状态。它像人类一样可以近因归因、远因联想、误归因、合理化、事后解释、梦境式跳跃、创伤回闪、任务恢复、话题回收, 并且可以被后天反馈逐步修正。

## 1. 核心定义

### 1.1 当前认知结构 Q_t

Q_t 是第 t 个 tick 中被注意力调制后进入短期结构池的当前 occurrence 子图。它可以包含文本、视觉、听觉、动作、草稿、情绪、未闭合感、奖励/惩罚、时间感、内源想象等任意 SA occurrence。

Q_t 不是一句话, 不是一张图, 也不是单个对象。它是当前认知流中“正在被当作一件事处理”的局部结构。

### 1.2 来源缺口 Source Gap

来源缺口表示“当前认知结构需要一个来源/对象/原因/上下文才能闭合解释, 但这个来源没有被当前输入直接给出或没有足够把握”。

它不是新实体, 而是由已有信号组合出的认知感受:

```text
G_t =
  residual(Q_t)
+ prediction_mismatch(Q_t)
+ deixis_vacancy(Q_t)
+ unresolved_pressure(Q_t)
+ surprise(Q_t)
+ ambiguity(Q_t)
- self_evidence(Q_t)
- recent_explanation_support(Q_t)
```

解释:

- residual: 当前结构和召回结构之间未拟合的残差。
- prediction_mismatch: 预测未被现实验证。
- deixis_vacancy: 当前结构含“这个/刚刚/继续/没错/为什么/那个感觉”等开放槽, 但槽位没有直接对象。实现时不应靠词表硬判, 而应由结构上“需要外部参照”的空槽产生。早期工程可用少量词触发作为传感器近似, 但必须标为临时近似。
- unresolved_pressure: 未闭合感 U 对当前结构的牵引。
- surprise: 意外输入产生的现实能量突增。
- ambiguity: 多个候选来源竞争且波峰不明显。
- self_evidence: 当前输入自带足够证据时降低来源缺口。
- recent_explanation_support: 刚刚已经形成强解释时降低重复追溯。

来源缺口不是“任务队列”, 不是“指代解析模块”, 也不是“问句分类器”。它是状态池/短期结构池/C* 中自然产生的低闭合、高残差、高不确定感。

### 1.3 候选来源 Source Candidate

候选来源 S_j 是统一经验流或短期结构池中的任意过去 occurrence 子图, 可以是:

- 近期文本输入。
- 近期图片的视觉 patch 流。
- 近期音频片段。
- 上一个 AP 回复的草稿提交。
- 用户刚刚的肯定/否定反馈。
- 一个未闭合任务。
- 一段旧记忆、旧话题、旧关系。
- 一个动作后果。
- 一个内源想象片段。
- 一个情绪/身体感受。
- 一个远距离但结构相似的经验。

候选来源不是按模态建表的分类对象, 而是统一经验流中的 episode/window/occurrence-subgraph。

### 1.4 主观归因 Attribution Hypothesis

归因假设 A_t 是 AP 在当前 tick 暂时选择的解释:

```text
A_t = (Q_t <- S_j, support, grasp, uncertainty, contradiction, source_path)
```

它表示“我现在主观上把当前这件事归因到过去那个来源”。它可能正确, 也可能错误。错误归因不是 bug, 而是拟人性的一部分。后天反馈、反例、重复经验、预测验证会改变归因倾向。

### 1.5 C_backward 与归因的关系

旧表述中 C_backward 是从 B 命中历史片段向前传播得到的追溯认知。新补丁将其扩展为:

```text
C_backward(t) = AttributionCompetition(Q_t, StatePool_t, SSP_t, ExperienceFlow)
```

它包括两条路径:

1. B 命中后沿历史结构向前传播, 找“什么过去条件导致这个历史结果”。
2. 当前 Q_t 有来源缺口时, 在短期结构池和统一经验流里反向寻找“什么过去对象可以解释当前缺口”。

两者不是两个模块, 而是同一套候选生成和评分的两个入口。

## 2. 信息流

### 2.1 单 tick 中的位置

统一溯源发生在每个 tick 的常规 AP 循环内:

```text
感受器 -> 状态池 -> 注意调制 -> 短期结构池 Q_t
     -> B 当前相似召回
     -> C_forward 后继预测
     -> C_backward 来源追溯/主观归因
     -> C* 预测解释整合
     -> 认知感受
     -> 行动竞争
     -> 草稿/视焦点/听觉焦点/询问/停止/动作
     -> 经验流写入
```

不允许 UI 或独立模块额外决定“这句话指的是图片”。UI 只能展示 RuntimeTickEvent 中的 attribution candidates、selected attribution、grasp、source gap、rejected candidates。

### 2.2 候选生成

候选来源集合来自四层, 但四层只是检索范围, 不是四个心智模块:

```text
S = S_recent + S_unclosed + S_similar + S_emotional
```

- S_recent: 短期结构池中仍有能量的近期 occurrence window。
- S_unclosed: 未闭合压力仍未衰减的任务/问题/期待/痛点。
- S_similar: 统一经验流中与 Q_t 局部结构相似的历史片段。
- S_emotional: 高奖惩、高痛苦、高舒适、高依恋、高惊讶的高权重记忆。

候选可以跨模态。文本“刚刚那个”可以候选到视觉 patch; 声音“砰”可以候选到刚才动作; “没错”可以候选到 AP 上一轮草稿; 闲时无输入可以候选到几小时前未闭合的哲学问题。

### 2.3 评分函数

候选 S_j 对 Q_t 的归因得分:

```text
score_j =
  w_struct * Sim_struct(Q_t, S_j)
+ w_bridge * Bridge(Q_t, S_j)
+ w_pred * DeltaPredictionGain(Q_t | S_j)
+ w_gap * GapReduction(Q_t | S_j)
+ w_energy * ActiveEnergy(S_j)
+ w_u * UnclosedMatch(Q_t, S_j)
+ w_affect * AffectiveWeight(S_j)
+ w_reward * RewardPunishBias(S_j)
+ w_path * PathSupport(S_j -> Q_t)
- w_time * TimeDistanceDecay(S_j, Q_t)
- w_space * SpaceDistanceDecay(S_j, Q_t)
- w_boundary * BoundaryPenalty(S_j, Q_t)
- w_contra * ContradictionPressure(S_j, Q_t)
+ noise_t
```

关键约束:

- TimeDistanceDecay 不能硬截断远距离记忆, 只能衰减。强情绪、强未闭合、强结构相似可以跨越时间距离。
- BoundaryPenalty 不能阻止跨 episode 联想, 只能降低随意串场概率。
- noise_t 保留拟人的随机联想和误归因。
- ContradictionPressure 不应让 AP 天生不会错, 只是把已经学到的反例作为压力。

### 2.4 把握感

```text
grasp(A_t) =
  peak(score) - second_peak(score)
+ absolute_support(peak)
- conflict_entropy
- unresolved_residual
```

把握高: AP 会自然地把来源假设回灌 C*, 用于继续写草稿、行动、闭合未闭合项。

把握低: AP 会犹豫、继续观察、请求教学、保持未闭合、或在闲时继续想。

### 2.5 主观性与错误

AP 的归因不是概率真理, 而是主体当下的解释倾向。允许出现:

- 近因偏差: 最近发生的事被过度归因。
- 可得性偏差: 高能量记忆更容易被当作原因。
- 情绪归因: 不舒服时把无关事件当成原因。
- 事后合理化: 行动后给自己找解释。
- 迷信/伪因果: 两件事连续出现就建立因果感。
- 纠正后修正: 后天反馈逐步降低错误归因。

这符合拟人哲学。AP 不应被设计成先天完全理性机器。

## 3. 与心理学/认知科学的对应

### 3.1 指代与共同注意

人类听到“这个”“那个”“刚刚”时, 不只是语义解析, 而是把当前语言结构与共同注意场、短期记忆、对方眼神/手势/上下文一起绑定。AP 中对应:

- 当前文本 SA 产生开放槽。
- 近期视觉/听觉/动作/对话 occurrence 作为候选来源。
- 注意能量和时空距离决定哪个候选获胜。

这不是语言模块, 而是多模态共同注意的归因竞争。

### 3.2 情景记忆与线索依赖回忆

人类回忆高度依赖线索。一个气味、一句话、一个位置会突然召回旧事。AP 中对应:

- Q_t 的局部结构作为 cue。
- 统一经验流中相似子图被召回。
- 情绪和未闭合压力可放大远距离候选。

因此 AP 可以支持“任意时空距离”的回忆, 但不会保证总是准确。

### 3.3 预测加工与解释

预测加工理论认为大脑持续用内部模型解释感官输入, 预测误差推动更新。AP 中对应:

- C_forward 给出后继预测。
- 现实输入未拟合产生 prediction_mismatch。
- C_backward 寻找来源解释以降低误差。
- 解释成功产生合理感, 惊讶下降。

音乐突然停了、图像不符合预期、用户突然说“没错”, 都是预测误差和解释竞争的例子。

### 3.4 归因理论

社会心理学中的归因理论区分内因、外因、稳定性、可控性等。AP 不应把这些分类写成底层实体, 但可以让它们从信息流中涌现:

- 内因/外因来自 source candidate 是自身行动、内部状态还是外界输入。
- 稳定性来自跨 episode 重复验证。
- 可控性来自行动后果和 affordance 经验。
- 责任感来自自身行动候选与后果之间的高 PathSupport。

### 3.5 工作记忆与注意恢复

人类被打断后能回到原任务, 因为未闭合压力和工作记忆痕迹持续存在。AP 中对应:

- 未闭合项是高 U 的候选来源。
- idle tick 或低外部输入时, U 候选得分上升。
- C_backward 把注意拉回未完成任务。
- 若当前 affordance 不足, 只会计划/想象, 不一定执行。

### 3.6 默认模式网络与闲时思考

人类无事时会回忆、计划、幻想、整理自我叙事。AP 中对应:

- 外部输入低时, S_unclosed、S_emotional、S_similar 占比上升。
- C_forward 续写想法。
- C_backward 找来源和解释。
- C* 形成叙事化内源结构。

这不需要新增“默认模式模块”, 只需要调节候选来源权重和行动竞争频率。

### 3.7 创伤回闪与执念

高痛苦、高未闭合、高惊讶的记忆会被远距离反复召回。AP 中对应:

- AffectiveWeight 和 UnclosedMatch 长半衰期。
- 时间衰减被强情绪抵消。
- 候选反复获胜, 形成 intrusive recall。
- 后天安全经验和反例可逐步中和。

### 3.8 迷信、偏方与伪因果

人类会把连续出现的事件误认为因果。AP 中对应:

- 近邻 temporal edge + reward/punish coincidence 形成初始 PathSupport。
- 若缺少反例, C_backward 会把它当作原因。
- 反复验证失败后, ContradictionPressure 才逐步上升。

这比“内置反伪因果门”更拟人。

## 4. 当前实现偏差

Phase20.7 当前局部修复中存在以下不够 AP-native 的痕迹:

1. 视觉专用恢复函数 `_recover_recent_visual_observation`。
2. 视觉专用触发 `_text_can_refer_to_recent_visual`。
3. 内部固定锚 `VISUAL_ONLY_ANCHOR_TEXT`。
4. `visual_reference_family` 显式标签。
5. `_find_visual_exact_b0` 对视觉召回做特殊路径。

这些能修复“图片教学”眼前体验, 但会阻碍任意模态、任意距离的统一归因。后续实现应逐步替换为通用 AttributionCandidate / SourceGap / C_backward competition。

## 5. AP-native 工程设计

### 5.1 统一事件窗口

从统一经验流构造候选窗口:

```text
ExperienceWindow {
  window_id
  event_ids
  occurrence_ids
  modality_mix
  time_span
  spatial_span
  source_refs
  state_energy_summary
  structure_edges
  affect_summary
  reward_punish_summary
}
```

它不是新心智实体, 而是经验流查询结果。

### 5.2 SourceGap 审计字段

RuntimeTickEvent 应新增或扩展:

```text
source_gap: {
  value
  residual
  ambiguity
  prediction_mismatch
  unresolved_pressure
  self_evidence
}
```

### 5.3 AttributionCandidate 审计字段

```text
attribution_candidates: [
  {
    source_window_id
    event_ids
    modality_mix
    score
    structural_sim
    bridge_support
    prediction_gain
    gap_reduction
    time_distance
    boundary_penalty
    affect_weight
    contradiction_pressure
    grasp_if_selected
  }
]
```

### 5.4 Selected Attribution

```text
selected_attribution: {
  source_window_id
  subjective: true
  grasp
  uncertainty
  source_path
  may_be_wrong: true
}
```

这让 UI 能展示“AP 为什么把这句话和那张图/那句话/那个任务联系起来”, 而不是展示硬编码流程。

### 5.5 教学与反馈

教学不应写“图片标签”。教学应强化:

```text
Q_t <- selected_attribution <- teacher_feedback
```

如果用户纠正“不是刚才那个, 是更早那个”, 则当前选中 attribution 被惩罚, 另一个候选被强化。

### 5.6 替换当前视觉补丁的顺序

1. 先保留当前视觉补丁作为兼容路径, 防止工作台体验倒退。
2. 新增通用 SourceGap / AttributionCandidate 数据结构。
3. 把文本、视觉、音频、草稿、未闭合项统一转为 ExperienceWindow。
4. 用 AttributionCompetition 生成 C_backward。
5. UI 只展示 attribution trace。
6. 旧视觉专用函数改为通用候选生成的一个早期特例, 再逐步删除。

## 6. 能涌现的人类内心活动覆盖表

| 人类现象 | 当前统一归因方案是否可覆盖 | 所需信号 |
|---|---|---|
| 指代理解 | 可覆盖 | source gap + 近期候选 + 共同注意 |
| 话题回收 | 可覆盖 | 短期结构池 + episode boundary 衰减 |
| 被打断后恢复任务 | 可覆盖 | 未闭合 U + idle attribution |
| 闲时自言自语 | 可覆盖 | 低外部输入 + C_forward/C_backward 叙事循环 |
| 回忆旧事 | 可覆盖 | 结构相似 + 情绪权重 + 时间衰减非硬截断 |
| 触景生情 | 可覆盖 | 感官 cue + affective weight |
| 误会别人意思 | 可覆盖 | 低 grasp attribution 被行动使用 |
| 事后合理化 | 可覆盖 | 行动后果作为 Q_t, C_backward 找自身/外界来源 |
| 迷信/伪因果 | 可覆盖 | 近邻时序边 + 奖惩巧合 + 缺少反例 |
| 创伤回闪 | 可覆盖 | 高痛苦/高惊讶/高未闭合长半衰 |
| 做梦式跳跃联想 | 部分可覆盖 | 低外部输入、低温度控制、噪声、弱 boundary |
| 自我叙事 | 可覆盖 | 自身行动/记忆作为候选来源 |
| 责任感/愧疚 | 可覆盖 | 自身行动 -> 后果 PathSupport + 惩罚/社交反馈 |
| 理解因果 | 可覆盖但需后天验证 | C_backward + 预测验证/反例 |
| 抑郁式反刍 | 可覆盖但需安全调节 | 负性 affect + 未闭合循环 |

## 7. 对抗性评估

### 7.1 最大风险: 候选爆炸

若任意模态、任意时空距离都可作为候选, 候选数量会爆炸。解决方式不能是硬截断, 而应是 AP-native 的多级能量门:

1. 短期结构池活动候选优先。
2. 未闭合/高情绪/高奖励候选可跨越时间。
3. 低能量远距离候选只在闲时或高 source gap 时进入。
4. ANN/Zvec/rolling hash 只作为索引, 不作为真相来源。

### 7.2 最大哲学风险: 把心理学分类写成实体

不能把“共同注意模块”“责任模块”“迷信模块”“默认模式网络模块”写进 AP 底层。它们应从同一套归因竞争中涌现。文档中的心理学术语只能作为解释和验收场景, 不能成为运行时硬分类。

### 7.3 最大拟人风险: 过度理性

如果 score 设计过于反伪因果、过度追求正确, AP 会不像人。应允许低把握归因被使用, 允许 noise, 允许近因偏差。纠错依赖后天经验和反馈。

### 7.4 最大工程风险: 早期实现仍会偷偷变成关键词规则

“这个/刚刚/继续/没错”等早期 cue 可作为文本感受器的临时近似, 但必须在 trace 中标注为 receptor-derived source-gap evidence, 不能成为行为路由。更好的方向是让文本结构残差、无对象槽、低自证据自然产生 source gap。

### 7.5 最大长期风险: 远距离归因导致串场

人类也会串场, 但 AP 需要可调节。应使用:

- episode boundary 衰减。
- contradiction pressure。
- source trust。
- recent explanation suppression。
- teacher correction feedback。

这些不是防错硬门, 而是后天调节项。

### 7.6 当前方案是否足够

作为白皮书补丁和 Phase20.8/20.9 实现方向, 这套方案比视觉专用补丁更符合 AP 哲学。它仍需要数学硬化:

1. SourceGap 各项默认权重。
2. ExperienceWindow 的构造半径和性能预算。
3. 结构相似 Sim_struct 的统一实现。
4. 跨模态 Bridge 的来源: 同 tick 共现、时空邻接、教师反馈、动作后果。
5. 归因候选的温度和噪声如何受注意力/疲劳/情绪调节。
6. 反例如何产生 contradiction pressure。

在这些硬化完成前, 不应把当前实现宣称为完整人类级溯源能力。但这条路线有机会覆盖目标图景。

## 8. 更进一步的改进裁定

最 AP-native 的最终表述应是:

> AP 没有“指代解析模块”或“因果推理模块”。AP 只有当前认知结构、过去经验结构、预测误差、未闭合压力、情绪权重、奖惩后果和行动竞争。所谓理解“这个指什么”、知道“为什么发生”、想起“刚才没做完的事”、误会、迷信、合理化、触景生情, 都是同一套 C_backward 主观归因竞争在不同能量图景下的表现。

因此后续实现应把所有“最近文本恢复”“最近视觉恢复”“最近音频恢复”“最近草稿恢复”合并为统一候选生成:

```text
recent_windows = query_recent_experience_windows(session/global, modalities=all)
unclosed_windows = query_unclosed_windows()
similar_windows = query_structural_index(Q_t)
emotion_windows = query_high_affect_windows()
candidates = score_all_windows(Q_t, windows)
```

然后由 C* 和行动竞争决定是否:

- 继续观察。
- 回答。
- 请求教学。
- 闲时继续想。
- 放弃/降低压力。
- 形成新的经验边。

## 9. 进入白皮书的建议

建议补入白皮书以下位置:

1. 第 22 章“追溯认知 C_backward”: 增加 SourceGap、AttributionCompetition、主观归因假设。
2. 第 27 章“期待/压力/未闭合”: 增加未闭合如何成为远距离归因候选。
3. 第 50 章“短期结构池”: 增加 occurrence window 是归因候选的基本单位。
4. 第 56 或工程章节: 增加 RuntimeTickEvent attribution trace 字段。
5. 视觉章节: 删除“视觉专用追溯”的倾向, 说明视觉只是统一归因候选的一种。

## 10. 实施前红线

1. 不许用文件名/路径/标签作为视觉归因证据。
2. 不许用关键词直接决定来源或答案。
3. 不许建立图片标签表、文本答案表、音频标签表。
4. 不许 UI 自己生成归因解释。
5. 不许把心理学分类写成硬模块。
6. 不许把远距离归因硬关掉。
7. 不许让 AP 天生不会伪因果。

## 11. 最终判断

这套统一溯源与主观归因竞争方案比当前代码补丁更符合 AP 哲学, 也更有机会复现广泛的人类内心活动。它的关键不是新增实体, 而是把已有 AP 信息流中的 C_backward 从“结构相似后的向前传播”扩展为“当前来源缺口驱动的任意经验窗口归因竞争”。

建议将本文作为冷保存标准, 先补入白皮书与 Phase20.8/20.9 工程数学稿, 再进行实现。实现时应先加 trace 和候选评分, 再删除视觉专用补丁, 避免工作台体验倒退。
