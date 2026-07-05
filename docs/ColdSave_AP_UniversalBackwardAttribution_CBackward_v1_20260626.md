# AP 统一溯源与主观归因竞争冷保存 v1

日期: 2026-06-26

定位: 本文是 AP 底层原理白皮书中“追溯认知 C_backward / 合理感 / 任意模态来源归因”的最新冷保存裁定。它继承 v0 的方向, 但进一步把 SourceGap、AttributionCandidate、ExperienceWindow 等名词压回 AP 既有信息流: 它们是审计命名和运行时派生视图, 不是新增心理器官, 不是指代解析模块, 不是视觉专用补丁。

目标: 用尽可能少的核心实体解释“这个指什么”“刚刚那张图是什么”“没错是在肯定哪句话”“为什么音乐停了”“我是不是见过这个”“被打断后为什么还能想起未完成任务”“为什么会误会、迷信、合理化、触景生情、闲时胡思乱想”等人类内心活动。最高准则是拟人性与 AP 哲学: 能由状态池、短期结构池、统一经验流、B/C/C*、认知感受、奖惩、先天规则、注意力和行动竞争解释的, 不新增实体。

## 0. 最终判断

我认为 v0 的方向是对的, 但 v0 还容易被实现者误读成“新增一个溯源模块”。v1 的核心改进是:

1. SourceGap 只是“当前结构闭合不足”的审计量, 来自残差、虚实不匹配、未闭合感、惊讶、低自证据等已有能量关系。
2. ExperienceWindow 只是统一经验流上的查询窗口, 不是新的记忆库。
3. AttributionCandidate 只是 C_backward 竞争过程中的候选 trace, 不是按模态建立的候选表。
4. SelectedAttribution 只是 AP 当前 tick 的主观解释倾向, 不是真理标签。
5. 视觉、文本、听觉、动作、草稿、情绪、未闭合任务、内部想象都必须以同等 occurrence 身份进入同一套短期结构池和统一经验流。

因此, 当前更 AP-native 的设计不是“最近图片恢复”, 而是:

```text
当前认知结构 Q_t
  -> 残差/缺口/未闭合/意外形成归因压力
  -> 在短期结构池和统一经验流中召回任意经验窗口
  -> C_backward 对候选来源进行主观竞争
  -> C* 保留预测 slot 与解释 slot
  -> 认知感受与行动竞争决定观察、询问、回答、继续想、放下或休眠
  -> 行动/反馈/奖惩写回经验流
```

这套方案有机会复现大量人类内心活动, 但要成功, 工程上必须把“候选生成、得分、把握感、反例修正、闲时续写、教学反馈绑定”写成可审计的统一 RuntimeTickEvent 字段, 不能再散落成视觉专用或文本专用函数。

## 1. AP 核心实体边界

AP 底层只承认以下核心实体:

1. 感受器: 把文本、视觉、听觉、动作反馈、内部想象、身体/情绪信号等转成 SA occurrence。
2. 状态池 StatePool: 当前认知场, 聚合 type-level 能量和可注意性, 但不吞掉 occurrence 的时空关系。
3. 短期结构池 SSP: 当前认知流, 保存达到阈值的 occurrence 及其线性、空间、时空、图、行动、奖惩、焦点关系。
4. 统一经验流 ExperienceFlow: append-only 的长期真相源, 保存结构增量、感受、行动、反馈、教学和学习更新。
5. B: 由当前短期结构池 query 召回的历史相似结构波。
6. C_forward: 从 B 和当前结构向后传播得到的预测波。
7. C_backward: 从 B、当前缺口和经验窗口向前/向源传播得到的解释波。
8. C*: 预测 slot、解释 slot、行动后果 slot、感受触发 slot 的结构化整合包。
9. 认知感受: 惊讶、违和、合理、正确、把握、期待、压力、闭合/未闭合、好奇、熟悉、陌生等由能量关系产生的感受。
10. 行动竞争: 观察、移动焦点、写草稿、提交、询问教师、继续想、放下、休眠、身体/工具动作等互相竞争。
11. 奖惩和先天规则: 为行动后果和学习提供价值偏置, 但不预置答案表。

本文中出现的 SourceGap、ExperienceWindow、AttributionCandidate、SelectedAttribution 都只是这些核心实体的审计视图。它们可以出现在日志、RuntimeTickEvent、UI trace 和测试断言里, 但不能成为绕过 AP 主循环的独立模块。

## 2. 当前认知结构 Q_t

Q_t 是第 t 个 tick 中, 被注意力调制后进入短期结构池的当前 occurrence 子图。它不是一句话, 不是一张图, 不是一个对象名, 而是 AP 正在处理的局部认知结构。

Q_t 可以包含:

1. 文本 occurrence: 字符、词块、句块、教师纠正、AP 草稿、上一轮回复。
2. 视觉 occurrence: 像素 patch、颜色/亮度/边缘/纹理/形状通道、视焦点、清晰度场、空间位置。
3. 听觉 occurrence: 音频片段、频谱/节奏/音高/能量、听觉焦点。
4. 动作 occurrence: 鼠标、键盘、TTS、画板笔画、视焦点移动、草稿写入。
5. 内部 occurrence: 想象片段、未闭合任务、情绪残响、预测 slot、解释 slot。
6. 奖惩 occurrence: 教师肯定、纠正、行动成功、行动失败、舒适/痛苦、奖励/惩罚信号。

Q_t 的关键是结构, 不是模态。文本“刚刚那个”、当前图片 patch、上一轮 AP 草稿、一次 TTS 失败、一个未闭合问题都可以共同构成 Q_t 的一部分。实现上必须允许 Q_t 是多模态、多位置、多时间尺度的局部图。

## 3. 来源缺口 SourceGap

SourceGap 表示当前 Q_t 对自己不够自足, 需要某个来源、对象、上下文、原因或前置经验才能更好闭合。它是状态池和短期结构池能量关系产生的认知感受, 不是新增模块。

形式:

```text
G_t =
  a_r * residual(Q_t, B_t)
+ a_m * prediction_mismatch(Q_t, C_forward)
+ a_u * unresolved_pressure(Q_t)
+ a_s * surprise_energy(Q_t)
+ a_a * ambiguity_entropy(Q_t)
+ a_o * open_slot_energy(Q_t)
- a_e * self_evidence(Q_t)
- a_x * recent_explanation_support(Q_t)
```

其中:

1. residual: 当前结构与召回结构无法拟合的部分。
2. prediction_mismatch: 预测没有被现实验证, 或现实出现未预测内容。
3. unresolved_pressure: 未闭合感对当前结构的牵引。
4. surprise_energy: 意外输入造成的现实能量突增。
5. ambiguity_entropy: 多个候选来源分数接近导致的模糊。
6. open_slot_energy: 当前结构中存在“需要外部参照才能闭合”的槽位。
7. self_evidence: 当前输入自己已经提供了足够对象和解释时, 来源缺口下降。
8. recent_explanation_support: 刚刚已经形成高把握解释时, 避免同一缺口每 tick 重复拉扯。

注意: open_slot_energy 不能靠关键词硬判定。早期工程可以把“这、那、刚刚、继续、没错、为什么”等作为文本感受器产生的弱 evidence, 但它只进入 G_t, 不能直接决定来源或答案。更 AP-native 的长期做法是让结构残差、低自证据和经验中的共同注意模式自己产生 open slot。

## 4. 经验窗口 ExperienceWindow

ExperienceWindow 是从统一经验流中切出的候选子图窗口。它不是新记忆库, 而是查询结果。

形式:

```text
W_j = {
  event_ids,
  occurrence_ids,
  modality_mix,
  time_span,
  spatial_span,
  structure_edges,
  state_energy_summary,
  affect_summary,
  reward_punish_summary,
  action_outcome_summary,
  source_refs
}
```

候选窗口可以来自:

1. 短期结构池中仍有能量的近期窗口。
2. 高未闭合 U 的任务、问题、期待或压力片段。
3. 统一经验流中与 Q_t 结构相似的片段。
4. 高情绪、高奖惩、高痛苦、高舒适、高熟悉/陌生的片段。
5. 自身刚刚的行动后果, 例如刚说过的话、刚写的草稿、刚播放失败的 TTS。
6. 内源想象和闲时思考留下的结构片段。
7. 很远但结构、情绪或奖惩高度相关的旧经验。

这就允许任意模态、任意时空距离参与归因。文本可以归因到图片, 图片可以归因到教师纠正, 声音可以归因到动作, 情绪可以归因到旧任务, 闲时想法可以归因到几小时前未完成的问题。

## 5. C_backward 作为主观归因竞争

v1 裁定:

```text
C_backward(t) = AttributionCompetition(Q_t, G_t, B_t, SSP_t, ExperienceFlow)
```

它有两个入口:

1. 历史相似结构入口: B 命中某些历史片段后, 沿这些片段的前驱边、证据边、行动后果边向前传播, 得到“当时为什么会这样”的解释波。
2. 当前来源缺口入口: Q_t 出现高 G_t 时, 从短期结构池和统一经验流中找“什么过去窗口可以让当前结构更闭合”。

两个入口共享候选生成和评分。它们不是两个模块。

归因假设:

```text
A_{t,j} = Q_t <- W_j
```

含义是: AP 在当前 tick 主观上把当前结构的一部分解释为来自窗口 W_j。这个解释可以正确, 可以错误, 可以只对一部分结构有效, 也可以随后被反馈推翻。

## 6. 归因评分

候选 W_j 对当前 Q_t 的主观归因分数:

```text
score(A_{t,j}) =
  w_struct * Sim_struct(Q_t, W_j)
+ w_edge   * EdgeAlign(Q_t, W_j)
+ w_bridge * CrossModalBridge(Q_t, W_j)
+ w_pred   * PredictionGain(Q_t | W_j)
+ w_gap    * GapReduction(G_t | W_j)
+ w_energy * ActiveEnergy(W_j)
+ w_u      * UnclosedMatch(Q_t, W_j)
+ w_affect * AffectiveWeight(W_j)
+ w_value  * RewardPunishBias(W_j)
+ w_path   * PathSupport(W_j -> Q_t)
+ w_trust  * LearnedSourceTrust(W_j)
+ w_recent * SoftRecency(W_j)
- w_time   * TimeDistanceDecay(W_j, Q_t)
- w_space  * SpaceDistanceDecay(W_j, Q_t)
- w_bound  * BoundaryPenalty(W_j, Q_t)
- w_contra * ContradictionPressure(W_j, Q_t)
- w_cost   * CognitiveCost(W_j)
+ noise_t
```

解释:

1. Sim_struct: 节点类型、能量模式、局部结构、文本/视觉/听觉/动作等结构的相似度。
2. EdgeAlign: 顺序、空间、时空、行动后果、奖惩、教师反馈等边的对齐。
3. CrossModalBridge: 不同模态之间的桥, 来自同 tick 共现、共同注意、教师纠正、行动后果和历史多模态绑定。
4. PredictionGain: 选中该窗口后, 当前结构的后继预测是否更顺。
5. GapReduction: 选中该窗口后, 当前来源缺口是否下降。
6. ActiveEnergy: 该窗口在当前状态池/短期结构池中的残余能量。
7. UnclosedMatch: 是否与未闭合任务、期待或压力相关。
8. AffectiveWeight: 情绪、痛苦、舒适、惊讶、熟悉感等权重。
9. RewardPunishBias: 奖励/惩罚历史对归因的偏置。
10. PathSupport: 历史中 W_j 到类似 Q_t 的路径支持。
11. LearnedSourceTrust: 来源可靠性是后天统计, 不是先天权威。
12. SoftRecency: 人类确实有近因偏差, 近期窗口会更容易赢, 但不能硬排除远因。
13. TimeDistanceDecay 和 SpaceDistanceDecay 只衰减, 不硬截断。
14. BoundaryPenalty 只降低跨 episode 串场, 不禁止触景生情或远距离联想。
15. ContradictionPressure 来自反例和反馈, 不能把 AP 设计成天生不会伪因果。
16. noise_t 保留拟人的随机联想、跳跃、误会和创造性。

## 7. 把握感与行动倾向

归因把握感:

```text
grasp(A_t) =
  b_margin * (score_top1 - score_top2)
+ b_abs    * score_top1
+ b_repeat * repeated_support(A_t)
+ b_value  * value_consistency(A_t)
- b_entropy * conflict_entropy(candidates)
- b_resid   * unresolved_residual(Q_t | A_t)
- b_fatigue * recent_failed_attribution(A_t)
```

把握高时:

1. C* 把解释 slot 回灌状态池。
2. 行动竞争更容易选择回答、继续草稿、提交、执行动作或闭合任务。
3. UI 可以显示“AP 当前较有把握地把这句话/这个输入联系到某个经验窗口”。

把握低时:

1. AP 更容易继续观察、移动视觉/听觉焦点、询问教师、保持未闭合、闲时继续想。
2. AP 可以说“我还不太确定”“这个像是刚才那个, 但我不太有把握”。
3. 教师反馈会强化或惩罚本次 attribution, 而不是写死标签。

把握不是正确性。人类经常很有把握地错, 也会低把握地猜对。AP 应保留这种拟人结构。

## 8. 教学如何进入归因

教学不是写“图片标签表”或“文本答案表”。教学反馈应绑定到当前 C* 中 AP 主观选中的解释路径。

形式:

```text
teacher_feedback_t -> reinforce_or_punish(
  Q_t,
  selected_attribution A_t,
  competing_attributions,
  action_output,
  reward_punish_signal
)
```

例子:

1. 用户先发一张图片, AP 不知道。
2. 过几秒用户说“这是苹果”。
3. 当前文本 Q_t 自身没有完整来源, 产生 SourceGap。
4. C_backward 从短期结构池找到近期视觉窗口 W_img。
5. A_t = “这是苹果” <- W_img 得分较高。
6. 教师反馈强化“视觉窗口 W_img 与文本/奖惩/教师纠正共同出现”的结构边。
7. 下次类似视觉结构出现时, 通过 B/C/C* 召回“是苹果”的行动候选, 不是读图片文件名, 不是最近标签覆盖。

如果用户过了一段时间才教, 只要 W_img 仍有能量、未闭合感或结构索引, 仍可被候选召回。若过很久才教, 得分会下降, 但不会被硬阻断。AP 可能归因错, 用户可以纠正“不是刚才那张, 是更早那张”, 于是另一个窗口被强化, 当前窗口被惩罚。

## 9. 闲时思考与连续叙事

用户不输入时, AP 不是停止认知, 而是外部输入能量下降, 内源候选占比上升。

闲时 Q_t 主要来自:

1. 未闭合 U 高的任务或问题。
2. 高情绪、高奖惩、高陌生感的经验窗口。
3. 刚刚 C_forward 预测出的后继想法。
4. 刚刚 C_backward 找到的解释路径。
5. 最近行动后果和自我叙事。

闲时不应重复同一句“未闭合感把短期结构流拉回某问题”。重复 bug 的根因通常是只把 U 当成静态标题, 没有让 C_forward 沿后继结构继续发展, 也没有 recent_thought_fatigue。

AP-native 的闲时发展:

```text
idle_Q_t = select_by_energy(U, affect, novelty, recent_Cstar)
B_t = recall(idle_Q_t)
C_forward = continue_narrative(B_t, idle_Q_t)
C_backward = seek_explanation(idle_Q_t)
C*_t = merge(prediction_slots, explanation_slots)
next_internal_occurrence = action_competition(continue_thought / ask / observe / sleep)
```

这样才会出现:

1. 想起未完成问题。
2. 沿着后继偏置继续想。
3. 发现低把握, 形成“下次问用户”的倾向。
4. 被新输入打断后, 还能通过 U 和结构残响回到原问题。
5. 想累了或没有进展时降低频率/休眠。

## 10. 心理学与认知科学对照

本节不是把心理学术语写成模块, 而是检查 AP 信息流是否能涌现相应现象。

### 10.1 指代理解与共同注意

人听到“这个”“刚才那个”“没错”时, 会把当前语言、共同注意场、手势、视线、上一句话、上一张图、刚发生的动作放在一起竞争。AP 中对应为:

1. 当前文本 occurrence 产生开放槽。
2. 近期视觉/听觉/动作/草稿/回复窗口作为候选。
3. 注意力、时空距离、结构边和奖惩反馈决定候选得分。
4. 选中的 attribution 回灌 C*, 行动竞争决定回答或询问。

覆盖度: 可以覆盖。

### 10.2 情景记忆与线索回忆

气味、声音、画面、位置会突然召回旧事。AP 中对应为:

1. Q_t 的局部结构作为 cue。
2. 统一经验流中相似窗口通过结构索引召回。
3. 情绪权重和未闭合压力可跨越时间衰减。
4. C_backward 形成“这让我想起某事”的解释感。

覆盖度: 可以覆盖。

### 10.3 预测加工与合理感

人面对意外输入会先找解释, 找到解释后惊讶下降。AP 中对应为:

1. C_forward 预测失败产生 residual 和 prediction_mismatch。
2. G_t 上升。
3. C_backward 找到可解释来源。
4. GapReduction 下降惊讶, 合理感上升。

覆盖度: 可以覆盖。

### 10.4 归因偏差、迷信与伪因果

人会把连续出现的事误认为因果, 也会用偏方、迷信、近因偏差解释世界。AP 中对应为:

1. 近邻时序边和奖惩巧合给 PathSupport 初始能量。
2. 缺少反例时 ContradictionPressure 低。
3. noise 和近因偏差让错误归因可被选中。
4. 后天反例、行动失败、教师纠正逐渐改变权重。

覆盖度: 可以覆盖, 且应保留。过度反伪因果会让 AP 不像人。

### 10.5 被打断后的任务恢复

人被打断后仍会想起“刚才还没做完”。AP 中对应为:

1. 未闭合 U 长半衰期保留。
2. 任务窗口在 S_unclosed 中得分较高。
3. 空闲或低外部输入时, C_backward 把注意力拉回任务来源。
4. 若当前 affordance 不足, 只计划/想象, 不强行动。

覆盖度: 可以覆盖。

### 10.6 闲时心流、默认模式与自我叙事

人无聊时会回忆、计划、幻想、整理自我故事。AP 中对应为:

1. 外部输入低时, 内源 occurrence 获得相对优势。
2. C_forward 续写想法。
3. C_backward 找来源和解释。
4. 奖惩和未闭合感决定哪些想法反复出现。
5. 行动竞争可选择继续想、询问用户、记录草稿、休眠。

覆盖度: 可以覆盖, 但工程上需要 idle tick 真实运行和防重复疲劳。

### 10.7 共情与社会认知

共情不应作为“共情模块”硬写。AP 中可以由以下信息流涌现:

1. 他人作为经验流中的外部主体 occurrence。
2. 他人的表情、语言、行动后果与奖惩信号共同出现。
3. AP 对“如果我这样说, 对方可能如何反应”的 C_forward 预测。
4. C_backward 对对方当前状态寻找来源。
5. 奖惩和先天规则让痛苦/安慰/陪伴相关路径被强化。

覆盖度: 可以覆盖基础共情雏形。要接近人类, 还需要更丰富的社交经验、身体/情绪感受器和长期人格连续性。

### 10.8 梦、幻想与创造性联想

梦和幻想可以看作低外部输入、弱边界惩罚、高噪声、内源预测占优时的 C_forward/C_backward 自循环。AP 中对应为:

1. 外部输入低。
2. BoundaryPenalty 降低。
3. noise_t 和情绪权重上升。
4. 远距离窗口更容易进入候选。
5. 行动竞争不提交外部动作, 而在内部结构流中续写。

覆盖度: 可以部分覆盖。若要更像梦, 需要睡眠态/低频态的调参策略, 但它仍是同一主循环的参数状态, 不是梦模块。

### 10.9 后悔、羞耻、责任感

这些不应作为硬分类底层实体。AP 中可以由:

1. 自身行动 occurrence。
2. 后果 reward/punish。
3. C_backward 归因到自身行动路径。
4. 未闭合压力和未来规避预测。
5. 他人反馈与社交奖惩经验。

覆盖度: 可以覆盖功能雏形。需要更完整的自我连续性和社交反馈经验。

### 10.10 执念、反刍与创伤回闪

AP 中对应为:

1. 高痛苦/高惊讶/高未闭合的窗口长半衰期。
2. 时间衰减被情绪和未闭合抵消。
3. C_backward 反复把注意力拉回。
4. 反例、安全经验、教师安抚和成功行动逐渐中和。

覆盖度: 可以覆盖, 但产品实现要有安全调节和休眠/降频机制。

## 11. 对抗性评估

### 11.1 风险: 变成新模块堆叠

问题: SourceGap、AttributionCandidate、ExperienceWindow 看起来像新实体。

修正: 文档和代码必须规定它们是 RuntimeTickEvent trace / 查询视图 / 审计字段。它们不能有独立记忆、独立策略或独立答案输出。所有更新必须回到状态池、短期结构池、经验流、C* 和行动竞争。

### 11.2 风险: 关键词指代解析偷偷回归

问题: “刚刚”“这个”“没错”容易被写成关键词路由。

修正: 这些词只允许作为文本感受器产生的弱 open_slot evidence。真正候选必须由统一经验流窗口竞争产生。测试必须覆盖无关键词场景, 例如用户只发“嗯”“对”“继续”“那个呢”, 或只发图片/音频, 仍能由结构缺口触发归因。

### 11.3 风险: 视觉专用补丁长期残留

问题: 当前代码里视觉专用恢复能修眼前 bug, 但会把 AP 拉回模态特权。

修正: 允许短期兼容, 但必须在 trace 中标记为 legacy bridge。最终所有 recent_visual、recent_text、recent_audio、recent_draft 都要合并为 recent ExperienceWindow 查询。

### 11.4 风险: 候选爆炸与性能压力

问题: 任意模态、任意距离都可候选, 全库遍历不可行。

修正: 用 AP-native 能量门和派生索引:

1. 近期短期结构池候选优先。
2. 高 U、高情绪、高奖惩候选可跨越时间。
3. 结构索引、ANN、Zvec、rolling hash 只负责加速召回, 不作为真相源。
4. 每 tick 有候选预算, 但不能按模态硬排除。
5. idle tick 可扩大远距离候选预算, 活跃对话 tick 预算更紧。

### 11.5 风险: 串场和过度归因

问题: 远距离归因可能把无关旧事拉进当前对话。

修正: 不用硬关远距离。用 BoundaryPenalty、ContradictionPressure、recent_failed_attribution、teacher correction、source trust 和 grasp 控制。低把握时应表现为“像是...但不确定”或询问, 不是强答。

### 11.6 风险: 过度理性, 失去拟人错误

问题: 如果强行反伪因果、强行追求正确, AP 会像冷冰冰的推理器。

修正: 保留 noise、近因偏差、情绪权重、低把握猜测、事后合理化。纠错依赖后天反馈和反例, 不是先天禁止错误。

### 11.7 风险: 闲时想法重复

问题: 当前 demo 中闲时会重复同一个未闭合标题。

修正: 闲时必须把上一 tick 的内部 occurrence 写入 SSP, 由 C_forward 产生后继偏置, 同时给刚重复过的 thought occurrence recent_fatigue。这样短期结构流会发展, 而不是静态刷屏。

### 11.8 风险: UI 生成认知

问题: 想法云、叙事卡、审计曲线容易自己生成解释文字。

修正: UI 只能展示 RuntimeTickEvent 中真实字段: Q_t 摘要、source_gap、candidate windows、selected attribution、C* slots、action competition、SSP deltas、thought occurrences。UI 可以翻译成小白中文, 但不能凭 UI 自己决定 AP 在想什么。

### 11.9 风险: “复现几乎一切人类内心活动”目标过大

判断: 当前方案能给出统一信息流框架, 但要接近“几乎一切”还需要把以下输入也纳入同一 SA/occurrence 体系:

1. 身体/内感受: 饥饿、疼痛、疲劳、困倦、舒适、紧张。
2. 自我连续性: 我的名字、承诺、偏好、过去行动、身份叙事。
3. 他人模型: 用户、老师、朋友、陌生人作为可预测的外部主体。
4. 行动 affordance: 当前能不能看、说、打字、移动、画图、打开工具。
5. 长期价值塑形: 奖惩、先天规则和后天反馈塑造稳定偏好。

这些不是新核心实体。它们都是新的感受器/行动器输入和经验类型, 仍走同一状态池、短期结构池、经验流、B/C/C* 闭环。

## 12. 与“几乎一切人类内心活动”的关系

从心理学和认知科学角度看, 人类内心活动的许多表面分类都可以压回几类底层过程:

1. 感觉输入与内源预测的冲突和拟合。
2. 工作记忆中的结构保持和衰减。
3. 情景记忆的线索召回。
4. 对未来的预测和对过去的解释。
5. 奖惩、身体状态和社会反馈对注意/行动的调制。
6. 行动后果写回, 形成学习。
7. 闲时由未闭合、情绪和自我叙事驱动的内源循环。

AP 的状态池、短期结构池、统一经验流、B/C_forward/C_backward/C*、认知感受和行动竞争正好对应这些底层过程。因此, 逻辑上它有机会涌现:

1. 记忆、联想、误会、理解、解释、合理感。
2. 好奇、困惑、惊讶、熟悉、陌生、把握和犹豫。
3. 闲聊、学习、主动询问、举一反三和过度泛化。
4. 未完成任务恢复、计划、放下和休眠。
5. 伪因果、迷信、事后合理化和后天纠错。
6. 基础共情、责任感、后悔、羞耻、安慰和社交期待的功能雏形。
7. 想象、梦样联想、创意组合和自我叙事。

它不能靠当前空泛设计自动实现这些。必须有真实的感受器、真实 SSP、真实经验流、真实 C_backward 候选竞争、真实行动反馈和足够多的经验积累。白皮书给哲学闭环, 工程要给可运行闭环。

## 13. AP 主流程纳入裁定

统一后的单 tick AP 流程应写成:

```text
1. 感受器采样:
   外部文本/视觉/听觉/动作反馈 + 内源想象/情绪/身体信号 -> SA occurrence

2. 状态池更新:
   occurrence 注入 R/V/A/P/affect/value 等能量, type-level 场强形成

3. 注意调制与短期结构池:
   达阈值 occurrence 进入 SSP, 保留线性/空间/图/时空/行动关系

4. 当前结构 Q_t:
   从 SSP 中形成当前被处理的局部结构

5. B 召回:
   用 Q_t 召回历史相似结构波

6. C_forward:
   沿历史后继、行动后果、奖惩路径产生预测

7. C_backward:
   根据 Q_t 的来源缺口、B 前驱和经验窗口产生主观归因竞争

8. C*:
   结构化整合 prediction_slots、explanation_slots、action_outcome_slots、feeling_slots

9. 认知感受:
   产生合理/违和/惊讶/把握/未闭合/闭合/好奇/疲劳等

10. 行动竞争:
   观察、移动焦点、继续想、询问、写草稿、提交、放下、休眠等竞争

11. 反馈写回:
   行动后果、奖惩、教师纠正、内部想法 delta 写入统一经验流
```

这就是后续白皮书和 Phase20.8/20.9 实现应采用的统一口径。

## 14. 工程硬化清单

在实现前, 需要把以下数学与接口硬化:

1. SourceGap 各项权重和默认范围。
2. ExperienceWindow 的构造半径、候选预算和索引策略。
3. Sim_struct 的统一函数: 文本、视觉、听觉、动作如何在结构层比较。
4. CrossModalBridge 的来源: 同 tick 共现、共同注意、教师反馈、行动后果、奖惩绑定。
5. Attribution score 的温度、噪声、疲劳、情绪调节。
6. grasp 的行动门限: 何时回答, 何时观察, 何时询问, 何时只在心里想。
7. 教师反馈如何强化/惩罚 selected attribution 和 competing attribution。
8. 反例如何形成 ContradictionPressure, 且不把伪因果先天禁止。
9. idle tick 如何把 C_forward 后继写入 SSP, 避免重复刷屏。
10. RuntimeTickEvent v3 字段: source_gap、experience_windows、attribution_candidates、selected_attribution、cstar_slots、ssp_delta、thought_occurrences。
11. UI 展示规则: 只翻译 trace, 不生成认知。
12. 红线扫描: 禁止 visual-only recovery、keyword route、label table、answer table、filename/path semantics、UI-owned cognition。

## 15. 验收场景

### 15.1 图片延迟教学

用户先发图片, 过几秒说“这是苹果”。AP 应通过 C_backward 把教学文本归因到近期视觉窗口。随后再见类似视觉结构, 通过视觉 SA 与经验结构召回回答。

### 15.2 文本肯定归因

AP 回答“我是小 AP”。用户说“没错”。AP 应把肯定归因到上一轮自身回复, 强化该回答路径, 而不是把“没错”当成一个需要固定回复的输入。

### 15.3 音频来源归因

用户播放一段声音, 过几秒说“这个声音是什么”。AP 应候选到近期听觉窗口, 而不是只看文本。

### 15.4 打断后恢复任务

AP 正在思考“还有什么动物”, 用户插入无关问候。处理完问候后, idle tick 应能通过未闭合感和 SSP 残响回到“动物”话题, 但若用户继续新话题, AP 也能放下或降权。

### 15.5 允许误归因并可纠正

用户说“不是刚才那张, 是更早那张”。AP 应惩罚当前 selected attribution, 强化另一个 candidate, 并在 RuntimeTickEvent 里留下 trace。

### 15.6 闲时连续发展

空闲 10 个 tick, AP 的 thought occurrences 应从“想起未闭合问题”发展到“召回相关经验”“形成低把握解释”“准备下次询问”, 而不是 10 次重复同一句。

## 16. 白皮书补充位置

建议将本文内容补入:

1. 第 22 章 C_backward: 用本文的 AttributionCompetition 重写追溯定义。
2. 第 27 章 期待/压力/未闭合: 增加未闭合如何参与任意距离归因。
3. 第 50 章 短期结构池: 增加 occurrence window 是归因候选基本单位。
4. 第 56 章 B/C/C*: 增加 C* 的 prediction/explanation/action/feeling slots。
5. 视觉章节: 明确视觉只是统一归因候选的一种, 删除视觉专用追溯倾向。
6. RuntimeTickEvent 章节: 增加 attribution trace 字段。
7. 红线章节: 增加禁止模态专用恢复、关键词路由、UI 认知生成。

## 17. 实施顺序

1. 保留当前视觉修复作为短期兼容桥, 但在文档和代码注释中标为 legacy bridge。
2. 新增统一 ExperienceWindow 查询层, 覆盖文本、视觉、听觉、动作、草稿、反馈、未闭合项。
3. 新增 SourceGap 和 AttributionCandidate trace, 先只审计不改变行为。
4. 将教学反馈绑定到 selected attribution。
5. 让回答、询问、观察、闲时继续想都读取 C* 中的 attribution 结果。
6. 通过验收场景确认稳定后, 删除视觉专用恢复函数。
7. 更新白皮书和 Phase20.8/20.9 工程数学设计。

## 18. 最终裁定

这套 v1 方案比视觉专用补丁更符合 AP 拟人哲学。它不是新增“溯源模块”, 而是把 C_backward 从“历史结构的前驱传播”完善为“当前认知缺口驱动的主观归因竞争”。它允许正确理解, 也允许误会、伪因果、近因偏差、触景生情和事后合理化; 它把纠错交给后天经验、奖惩、教师反馈和反例, 而不是让 AP 天生像机器一样不会错。

若后续实现严格遵守本文, AP 在逻辑上有机会复现大量人类内心活动的功能形态。要走向“几乎一切”, 还需要把身体内感受、长期自我连续性、他人模型、行动 affordance 和社会反馈都作为同等 SA occurrence 接入同一闭环, 而不是新增独立心理模块。

本文件应作为后续白皮书补丁和 Phase20.8/20.9 实施前的冷保存标准。
