# APV3.0test Phase5 设计门: 增量式范式发现与教学等价性

日期: 2026-06-16

## 1. 设计目标

Phase5 的目标不是继续增加离线探针, 而是把 APV3.0test 从“能在一批观察后发现范式”的最小骨架, 推进到“能在 tick 流中持续学习、持续修正、持续召回”的在线底座。

最终目标仍然是 APV3.0 中文开放自由对话底座:

- 能像儿童一样通过自然对话、模仿、奖惩和后继预测学习。
- 能通过 LLM 标准教学协议加速学习, 但 LLM 只在教师侧组织经验, 不在学生侧运行时替它回答。
- 文本、视觉、听觉、动作、情绪、认知感受、反馈、percept token 都是一等 SA。
- 范式不是答案模板, 而是从重复经验中形成的槽位结构、关系结构和过程结构。
- 快系统能在高把握、好后果、低慢系统需求的场景下快速复刻习惯行动或想法。
- 慢系统能在不确定、冲突、惊/违和、任务未闭合时接管竞争和解释。
- SQLite 持久化只保存 AP 运行所需本体和索引, 白箱审计可独立限额清理。

## 2. 审查问题

### 2.1 批处理倾向

当前 Phase2 范式链路大致是:

```text
收集一批观察 -> anchor-relative DP 对齐 -> relation coherence -> Viterbi role decode -> paradigm
```

这对最小证明是可接受的, 但长期风险是把 APV3.0test 做成“批处理范式发现器 + 在线动作系统”的拼接物。AP 哲学要求:

```text
每个 tick 的新 SA / 感受 / 行动 / 反馈 -> 更新状态池与统计池 -> 影响下一 tick 的召回、注意力、范式和行动竞争
```

因此 Phase5 必须转为增量式。

### 2.2 transition 弱平滑的来源

当前 Viterbi transition 使用固定 config 表达相邻角色偏好。这不是当前阶段的严重错误, 但不能成为永久先验。

Phase5 要求:

- transition 权重初始可以有弱默认值。
- 默认值必须被观察到的角色转移统计逐步覆盖。
- 角色转移统计来自已提交、已奖励或至少未惩罚的范式使用经验。
- 未提交草稿、自回环草稿、失败行动不能提高 transition support。
- 惩罚信号应降低对应 transition 在相似上下文中的后果预测驱动力。

### 2.3 教学等价性

自然教学和 LLM 教学必须在结果上等价。区别只在教师侧如何组织输入, 不在学生侧如何运行。

等价合同:

```text
自然教学 episode
    -> SA 流 / 感受 / 行动 / feedback / commit
    -> AP-native evidence
    -> runtime recall and action

LLM 标准教学 episode
    -> 同构 SA 流 / 感受 / 行动 / feedback / commit
    -> 同一 schema 的 AP-native evidence
    -> 同一 runtime recall and action
```

禁止:

- LLM 直接给 runtime policy。
- LLM 直接填最终答案作为学生侧动作。
- LLM 生成关键词路由、答案表、正则分支、隐藏 solver。
- LLM 教出来的技能有自然教学无法产生的特殊字段。

允许:

- LLM 作为教师侧生成多阶段教学材料。
- LLM 标注奖励/惩罚/纠错/解释信号。
- LLM 把长课程拆成 echo imitation、successor prediction、multi-reply aggregation、process-paradigm binding、keyword organization、grammar/style refinement 等阶段。
- LLM 帮助安排对比样例和负例, 但最终都必须落成 AP-native 经验。

## 3. Phase5 实现标准

### 3.1 增量式范式统计池

新增或改造的统计池必须支持:

- append-only observation ingest。
- dirty bucket 标记。
- 每次新观察只更新相关 anchor、slot、relation、role transition 统计。
- 空闲时可做后台压缩或重算, 但 tick 主链不能依赖全量重算。
- SQLite 恢复后统计池与内存态等价。

最小数据:

- observation_id
- tick_id
- modality
- token sequence
- boundary feelings
- focus context
- reward/punishment
- commit state
- relation signatures
- successor edges
- action outcome links

### 3.2 增量式对齐

Phase2.1 的 DP 对齐可以保留为局部更新算法的基准, 但 Phase5 不能每次全量对齐全部样本。

要求:

- 新观察只与候选 paradigm 的 anchor-relative skeleton 对齐。
- 若对齐失败, 产生新 paradigm embryo 或等待更多证据。
- 若对齐成功, 更新对应列的 occupancy、token distribution、relation signature、boundary evidence。
- 高冲突样本不能强塞进旧 paradigm, 应形成竞争胚胎。

### 3.3 role transition 后天学习

新增 RoleTransitionStats:

```text
(prev_role, role, context_signature) -> support, reward, punishment, recency, confidence
```

Viterbi transition 由两部分组成:

```text
transition_score = weak_prior + learned_transition_bias
```

其中:

- `weak_prior` 只能是极弱默认值, 且可以被学习覆盖。
- `learned_transition_bias` 来自已提交和奖惩后的角色转移经验。
- 负反馈可以在相似 context 中压低对应转移。
- 近因经验贡献更强, 但有上限趋近函数, 不能无限累加。

### 3.4 范式暴露门

范式候选进入 runtime 前必须满足:

- support 足够。
- coherence 足够。
- 最近没有强惩罚。
- 至少有一个可解释的 anchor、relation 或 successor 证据来源。
- 对全槽结构, 必须有外部 relation 或 successor support, 不能靠冷启动地板暴露。

### 3.5 快系统习惯兼容

增量式范式发现必须服务快系统, 不能只服务慢系统解释。

快系统候选来自:

- 高 grasp。
- 高 habit support。
- 当前慢系统需求低。
- 历史行动后果奖励高。
- 当前 context 与过往成功 context 相似。

但快系统不能绕过:

- actuator 同 tick 互斥。
- commit boundary。
- 惩罚回退。
- 惊/违和/不确定时慢系统接管。

### 3.6 持久化约束

SQLite 只保存 AP-native 运行证据和必要索引:

- state snapshots
- state field items
- learned vectors
- explicit successor transitions
- paradigm observations
- paradigm statistics
- role transition statistics
- action outcomes
- percept prototypes
- reward/punishment traces

白箱审计:

- 单独库或单独目录。
- 默认 10G 上限。
- 可自动删除最旧材料。
- 删除审计材料不影响 runtime recall。

## 4. 验收门

Phase5 最小验收必须覆盖:

1. 在线增量学习:
   - 逐条输入观察。
   - 每条观察后统计池局部更新。
   - 不全量重算仍能形成同一 paradigm。
2. 持久化等价:
   - 学习到一半保存恢复。
   - 继续学习。
   - 最终范式与纯内存连续学习等价或近似等价。
3. transition 学习:
   - 重复奖励某类角色转移后, 该转移 bias 上升。
   - 惩罚后, 相似 context 下 bias 下降。
4. 教学等价:
   - 自然教学 episode 和 LLM 标准教学 episode 写入同 schema 证据。
   - runtime 行为一致。
   - 不存在 LLM-only 字段。
5. 快系统兼容:
   - 熟练问候能走 fast habit。
   - 不确定或冲突问候进入慢系统。
   - 同 actuator 同 tick 仍只有一个行动赢家。
6. 跨模态平权:
   - percept token、text token、action token 能进入同一范式统计接口。
   - 不出现 `if vision`、`if text` 类模态特权分支。

## 5. 通过标准

Phase5 通过后才允许宣称:

- 范式发现开始具备在线增量学习形态。
- LLM 教学和自然教学在 AP-native evidence 层有等价路径。
- Viterbi transition 不再只是固定人工平滑, 已经有后天学习入口。

Phase5 通过前仍不能宣称:

- 完整 APV3.0 中文开放自由对话底座完成。
- 完整儿童式自学习已经实现。
- 完整跨模态泛化已经实现。
- Fresh300 可以代表最终能力。

## 6. 下一步落地顺序

1. 建立 `ParadigmObservationStore` 和 `IncrementalParadigmStats`。
2. 将 Phase2 的批处理 discovery 包成基准器, 用于对照, 不进入 tick 主链。
3. 实现增量 ingest:
   - observation -> candidate paradigm match
   - local alignment update
   - relation/coherence update
   - role distribution update
4. 实现 `RoleTransitionStats`。
5. 修改 `RoleViterbiDecoder`:
   - 保留弱 prior。
   - 叠加 learned transition bias。
   - 记录 bias 来源。
6. 实现自然教学与 LLM 教学等价 probe。
7. 做内存态 vs SQLite 恢复态 parity。
8. 通过后再回到更大规模旧技能复训和自由中文对话底座测试。
