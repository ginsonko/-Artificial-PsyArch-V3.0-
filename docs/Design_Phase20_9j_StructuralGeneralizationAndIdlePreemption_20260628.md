# Phase20.9j 结构泛化价值调制与闲时输入抢占设计稿

日期: 2026-06-28

## 1. 问题定义

用户验收发现两个当前体验问题:

1. 教过「没错,你好聪明 -> 谢谢」后, 再输入「你好聪明」仍低把握并请求教学。
2. 连续闲时运行时, 用户输入中文文本并发送, 可能被正在进行的 idle 请求吞掉。

第一个问题不是缺少记忆, 而是 `_find_structural_b(...)` 在进入 B/C/C* 前用结构阈值提前筛掉了候选。这样 C*、学习阶段、奖惩调制都没有机会参与竞争, 不符合白皮书中“低把握也应进入预测场/行动竞争, 再由奖惩塑形”的原则。

## 2. AP-native 设计

本阶段不新增回答模块、不新增答案表、不新增主动聊天模板。只修正现有主流程:

```text
当前短期结构 Q
  -> 统一经验流候选
  -> 结构序列对齐: 位置 / bigram / 前缀 / 后缀 / 最长连续片段 / 子序列
  -> reward/punish 对支持度调制
  -> structural B
  -> C_forward / C_backward / C*
  -> StatePool 回灌与行动竞争
```

### 2.1 子序列/片段对齐

人类听到「你好聪明」时, 可以把它贴到过去听过的「没错,你好聪明」中的一段上。这个过程不是关键词路由, 而是短期序列池上的局部结构中和。

本阶段把 `_structural_similarity(...)` 从只看同位置/prefix/bigram, 扩展为:

- positional score
- bigram score
- prefix score
- suffix score
- longest common contiguous span
- longest common subsequence

其中「你好聪明」对「没错,你好聪明」会得到高 span query coverage; 「你是谁」对「你好啊」只有弱共享, 不会形成 structural B。

### 2.2 奖惩调制泛化倾向

低把握泛化不是固定性格, 也不是固定阈值人格。经验中的 reward/punish 进入支持度:

```text
support_raw = max(sequence_fit + visual_boost,
                  unified_formula_support,
                  min(unified_candidate_support, sequence_fit + 0.12))

support = clamp(support_raw
                + statepool_observation_bias
                + reward_boost
                - punish_penalty
                - residual_conflict_penalty)
```

奖励让相似经验更容易进入 B/C/C*, 惩罚让相似经验退回 request_teacher/maintain_unclosed。这样 AP 可以像人一样“猜对后更敢猜, 猜错后更谨慎”。

同时, 局部眼熟不等于现状相同。若当前输入只共享一小段公共前缀, 而大量残差无法中和, `residual_conflict_penalty` 会压低支持度。例如 `phase20o knowledge question` 与 `phase20o unrelated unknown` 只共享测试前缀, 残差过大, 不应因为历史 reward 就回复 `red apple`。

### 2.3 闲时输入抢占

工作台原先在 `requestInFlight` 时直接 `return`, 导致用户在连续闲时请求未结束时发送输入被丢掉。现在改为:

1. 若 in-flight 是 idle, 用户发送真实输入时, 保存 `pendingUserTurn`。
2. 暂停连续闲时。
3. 当前请求结束后立即发送排队的用户 turn。
4. idle tick 自身仍不会排队空请求。

这只是 UI 调度修复, 不参与 AP 认知核心。

## 3. 对抗性审查

### 3.1 是否变成关键词路由?

否。实现没有检查具体词面含义, 也没有给「你好聪明」特殊规则。它只比较当前 SA 序列与历史 SA 序列的结构重合。

### 3.2 是否把教学变成答案表?

否。教学仍写入 `experience_alignment`, 召回时作为 unified experience candidate 进入 structural B, 后续经过 C_forward/C_backward/C* 与行动竞争。审计字段保留:

- `structural_sequence_fit`
- `structural_query_coverage`
- `value_reward_boost`
- `value_punish_penalty`
- `low_grasp_generalization_uncertainty`
- `writes_answer_directly: false`

### 3.3 是否过度泛化?

风险存在, 但本阶段有四道 AP-native 抑制:

1. 远文本共享不足时不达 structural B。
2. 共享片段后还有大量残差时, `residual_conflict_penalty` 降低支持度。
3. punish 会降低支持度。
4. 低支持无法绕过 request_teacher/maintain_unclosed 的行动竞争。

后续仍需要用更多中文自然表达做 held-out 泛化/反例课程。

### 3.4 主动发消息为什么本阶段不实现?

用户希望连续闲时时 AP 能主动决定是否给用户发消息。这应从已有闭环长出来:

```text
idle private thought
  -> 未闭合 / C* / reward expectation / social feedback trace
  -> outward_speech action candidate
  -> repetition fatigue + no-feedback punish projection
  -> DraftGrid 外显发言
```

不能新增一个定时模板模块, 例如“每隔 N 秒说一句”。这会违反白皮书的行动竞争和奖惩塑形原则。因此本阶段只修复 idle 输入抢占, 主动外显发言留给后续 Phase20.9k/Phase21 作为 AP-native action competition 扩展。

## 4. 验收标准

1. 奖励教学「没错,你好聪明 -> 谢谢」后, teacher-off 输入「你好聪明」回复「谢谢」。
2. 该回复出现 structural B, 支持项包含 Phase20.9j 结构泛化字段。
3. 输入「你是谁」不串到该经验, 仍请求教学。
4. 惩罚版本的相同经验不进入 structural B, 回到低把握/请教。
5. 工作台 JS 在 `requestInFlight` 时不会丢弃真实用户输入。
