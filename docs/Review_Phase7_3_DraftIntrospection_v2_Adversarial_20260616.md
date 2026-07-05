# Phase7.3 Draft Introspection v2 对抗审阅报告

日期: 2026-06-16
对象: `Design_APV3.0_DraftIntrospection_ExpressionLearning_v2_20260616.md`
结论: 方向性通过,但不能无修订直接落地。建议先做 Phase7.3a 设计修订门,修正本文列出的 blocker 后再进入实现。

## 1. 总判

Claude v2 方案抓住了 Phase7.2 的真实问题:当前 `must_reply` 是外部布尔开关,`feeling::undecidable` 是测试/调用方预置标签,而表达学习走的是 `cue=feeling -> reply=expression` 的直接教学,还不是真正的“内部感受涌现 -> 与外部表达共现 -> 后天学会表达范式”。

v2 的核心方向是正确的:从草稿结构抽取模态中立的能量视图,让 draft-introspection feeling 作为一等 SA 进入状态池,再通过带 provenance 的共现学习把 feeling 与外部表达 token 关联起来。这个方向更符合 APV3.0 的拟人原则、全模态平权原则和学生侧无 LLM/无答案表原则。

但 v2 目前仍有几处会在落地时造成严重偏差的问题。它们不是表述瑕疵,而是会直接影响系统是否真的能自发涌现感受和表达的数学/工程边界。

## 2. 已确认优点

1. Phase7.1 的 `undecidable_fragment` 判定可以保留。它基于“前面仍有未填槽,后面却已有共享/固定片段”的结构事实,不读中文内容、不读 case_name、不读答案表,是 AP-native 的结构性不能决。
2. v2 将“不能决”推广为 draft-introspection feeling family,避免为每种心理状态单写一条 if 分支,方向正确。
3. v2 要求 expression 学习来自 feeling SA 与外部表达 token 的共现,比 Phase7.2 的直接 cue/reply 教学更拟人。
4. v2 加入 `origin={perception_other, teacher_reply, self_emission}` 和默认 `gamma_origin[self_emission]=0`,能防止自发声自我强化 support,这符合 v3.1 红线。
5. v2 把 reply pressure 改为从 `state_field_items` 中的真实 SA 能量导出,而不是外部 `must_reply=True`,这是必须的方向。
6. v2 的 label-bijection 验收思路很关键:如果 label 是 opaque key,随机重命名不应改变行为。

## 3. 阻塞问题

### B1. softmax 响应度与“远离所有原型时响应都低”矛盾

设计文档写:

`r_f(phi)` 由 softmax 计算,所有原型响应度之和为 1;同时又写“若 phi 离所有原型都远,所有 r_f 都低,触发新原型孵化”。

这在数学上不成立。普通 softmax 在只有一个原型时永远给 `r=1`,不管距离多远;多个原型时也总会把 1 分配给某些旧原型。结果是新型感受会被错误吸附到旧感受上,共现学习会被污染。

修正要求:

- 先计算白化距离 `d_min = min_f d(phi, mu_f)`。
- 如果 `d_min > spawn_distance_threshold`,先 spawn 新原型,再计算/返回响应。
- 或加入显式 background/null prototype,用未归一化密度与 null 竞争。
- 验收必须覆盖“只有一个旧原型,新 phi 很远时仍能 spawn”,不能只测多原型场景。

### B2. 伪代码使用 `max_distance` 判 spawn 是错误的

v2 伪代码:

```python
max_distance = max(self._distance(phi, p) for p in self.prototypes)
if best_r < floor and max_distance > threshold:
    spawn()
```

这里应该使用 `min_distance`,不是 `max_distance`。只要存在一个很远的无关旧原型,`max_distance` 就会很大,可能导致本应匹配近邻的 phi 被误孵化。这个问题会直接造成 prototype explosion。

修正要求:

```python
min_distance = min(self._distance(phi, p) for p in self.prototypes)
if min_distance > spawn_distance_threshold:
    spawn()
```

`best_r` 可以作为辅助,但不能替代 novelty distance。

### B3. `stable_id(mu_f)` 不能依赖会漂移的 `mu`

设计写 `label = feeling::draft::proto_ + stable_id(mu_f)`。如果 stable_id 由 `mu_f` 内容算出,而 `mu_f` 会随经验更新,标签就会变,共现记忆和持久化引用会断裂。

修正要求:

- 原型 ID 必须在 spawn 时一次性分配,持久化保存,之后不随 `mu/tau` 漂移改变。
- `mu/tau/activation_ema` 可更新,`prototype_id` 不可更新。
- warm-load 后继续 spawn 时要从持久化 ID 推断 next_id,避免重号。

### B4. 当前代码库没有 v2 假定的 OnlineEmbeddingStore 接口

v2 依赖:

- `observe_positive_pair(f.label, e.token, weight)`
- `learned_similarity(...)`
- `nearest_by_label(...)` 或 `nearest_paradigm_cues_by_labels(...)`

但当前 APV3.0test 只有 `state["online_embedding"]["tokens"]` 与 promoted centroid 相似度,没有完整的 pair-association / nearest-by-label store。`learning_writer.py` 只写 token vector/support/transition/paradigm,没有共现对表。

修正要求:

- Phase7.3 必须先实现最小 `CooccurrenceAssociationStore` 或扩展 `online_embedding` schema,不能用直接 `LearningEpisode(paradigms cue=feeling reply=expr)` 伪装共现学习。
- 该 store 必须持久化到 SQLite,并通过 warm-load parity 验收。
- `nearest_by_label` 需要读 association index,不能线性扫所有 paradigm 后靠测试小样本过关。

### B5. label-bijection 测试的作用域必须精确定义

label-bijection 是好验收,但 v2 目前没有说清要重写哪些引用。如果只改 `state_field_items` 里的 label,而不改 association store、paradigm cue、trace、prototype store 等引用,测试会误报失败;如果只改一部分又刚好没覆盖 runtime 路径,会误报通过。

修正要求:

- bijection 只作用于 opaque internal feeling labels,不作用于外部表达 token。
- 必须一致重写: prototype store label/id 引用、state_field_items、cooccurrence pair keys、expression paradigm cue keys、recall index、persistence projection、trace 中用于计算的 key。
- 表达 token 如 `expr::uncertain` 不能被当作内部 label 重命名;它是外部学来的表达符号,可读性不等于学生侧硬编码。

## 4. 严重但可控风险

### S1. reply_pressure 权重可能退化为新策略表

`pressure_type_weights` 是 tuner-owned,但 `external_query:+1.0/recent_commit:-1.2` 仍是先验。如果后续每种表达风格都要补新 pressure 类型或新权重,它会变成“什么时候说什么”的手写策略表。

约束:

- pressure 只能决定“是否有回复压力”,不能决定“说哪种表达”。
- 表达选择必须只来自 feeling-expression association。
- 所有 pressure SA 必须有 tick 衰减,尤其 `external_query/silence/recent_commit`,否则 stale pressure 会让系统长期误以为必须回复。

### S2. DraftSAEnergyView 适配器可能藏模态/内容捷径

Protocol 是正确边界,但真正风险在 adapter。比如 text adapter 若读取 token 字面、中文词类、case_name 或固定字段,就会把“模态中立”变成壳。

约束:

- `extract_facts` 只能读 protocol 字段。
- adapter 不能出现 if text content / if vision content 的特权分支。
- 当前只能声明 within-text 内容无关,不能宣称已完成跨模态平权;第二模态 adapter 落地后再验。

### S3. 共现学习容易把干扰 token 一起学进去

同一 tick 中可能有教师表达、环境噪声、上下文 token 同时出现。若所有 external token 都按同样权重与 feeling 关联,会学出错误表达。

约束:

- external expression token 必须有 attention/window/segment 权重。
- 验收必须包含 distractor:目标表达相似度增长要显著高于干扰 token,而不是两者一起涨。
- teacher_reply 可以有更高 provenance weight,但这属于来源可信度,不能变成答案表。

### S4. rebind 与 one-token-per-tick 的时序需要更保守

v2 要求 `paradigm_fill_draft` 产 token,`paradigm_rebind_slots` 只改槽。这个方向对,但当前 runtime 仍是一次 run_turn 可能处理多个 draft candidate 的骨架。直接改成每 tick 单外显 token 可能影响 Phase7.0/7.1 既有验收。

建议:

- Phase7.3b 先做 observer-only:只产生 feeling SA 和 cooccurrence trace,不改变发声。
- Phase7.3e 再接入 expression recall/rebind。
- 每一步都保留 teacher-off echo/successor/multi-reply 回归。

### S5. prototype decay / max_prototypes 不能只是“未决问题”

内省 feeling 是高频机制,如果每个小波动都 spawn 原型,状态池会膨胀,共现学习会被稀释。

约束:

- `max_prototypes`、activation half-life、eviction floor、aggressive decay 必须进入 Phase7.3 首批实现。
- 验收包括平滑漂移不频繁换 ID、长期不用会衰减、衰减后重新出现可重新孵化。

### S6. teacher/natural 等价要落在 evidence 层,不能落在教师语义层

用户补充过:自然教育和 LLM 标准教学可以并存,但学到的内容在 AP-native evidence 层应等价。v2 中 `teacher_reply` origin 是允许的,但它不能让学生侧获得自然观察无法产生的特殊字段。

约束:

- `teacher_reply` 只能作为 external expression token 的 provenance,影响可信/学习权重。
- 学生侧 association store 中不能出现 “LLM said so” 路由字段。
- 同一个 feeling-expression 共现,自然旁人表达与 LLM 教师表达写入同构 pair evidence。

## 5. 推荐修订后的 Phase7.3 路线

### Phase7.3a: 设计修订门

先修订 v2 设计文档:

- 把 softmax spawn 改成 `min_distance/null prototype` 方案。
- 明确 prototype id 一次性分配并持久化。
- 明确 cooccurrence store schema 与 SQLite parity。
- 明确 label-bijection 的重写域。
- 明确 reply pressure 衰减与“只管压力不管表达”的边界。

### Phase7.3b: 内省原型 observer-only

实现 `draft_introspection.py`,只产生 feeling SA,不改变发声。

验收:

- 无教学也能产生 feeling SA。
- 同结构不同文本内容得到同一/近邻原型。
- 远离旧原型能 spawn。
- prototype id 稳定,mu 漂移不改 id。
- 长期不用会衰减。

### Phase7.3c: 共现关联 store

实现 `cooccurrence_learning.py` 与最小 association index。

验收:

- feeling 与外部表达共现后相似度相对增加。
- distractor 增长显著更低。
- self_emission 默认不增长。
- SQLite warm-load 后 association 行为等价。

### Phase7.3d: reply_pressure SA

实现从 `state_field_items` 派生 reply_pressure,不再读 `must_reply` bool。

验收:

- 只能通过 ingest/已有模块铸造 external_query/silence/recent_commit 等 SA。
- pressure 随 tick 衰减。
- 无 expression association 时,有压力也不凭空表达。

### Phase7.3e: expression recall/rebind

把 feeling-expression association 接入 expression paradigm recall,替换 Phase7.2 的 `undecidable_feeling_tokens` 参数。

验收:

- 学过类似表达时,不能决 + 高 reply_pressure 能召回表达范式。
- 未学过时,只保留不能决 draft,不发明“我不确定”。
- teacher-off echo/successor/multi-reply 全部回归。

### Phase7.3f: 红线与不变量

新增三层红线:

- AST 扫 exact prototype label / label compare / case_name route。
- label-bijection 行为不变。
- tests 不许内联 prototype id,只能从 store 运行结果取得。

## 6. 最终结论

v2 的战略方向应当采用:它把 Phase7.2 的临时桥改造成更符合 APV3.0 的“结构内省感受 -> 状态池 SA -> 共现学习表达 -> 压力触发表达倾向”链路。

但 v2 不能直接开工实现。必须先修正 softmax spawn、prototype id 稳定性、cooccurrence store 缺失、label-bijection 作用域和 reply pressure 衰减边界。修正后,Phase7.3 可以作为 APV3.0test 下一条主线,而且它比继续堆教师协议更接近“开放中文自由对话底座”的核心目标。

