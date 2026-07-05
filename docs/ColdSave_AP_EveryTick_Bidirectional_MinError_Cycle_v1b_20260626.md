# AP 每 tick 双向最小误差循环冷保存 v1b

日期: 2026-06-26

定位: 本文是对《AP 统一溯源与主观归因竞争冷保存 v1》的关键纠偏。v1 中“当前来源缺口 -> 归因竞争”的表述方向成立, 但还不够 AP-native。更准确的底层模型应是: AP 每个 tick 都同时进行后继预测与前因归因, 二者是同一 B 召回结构在时间方向上的对称传播, 并共同追求状态池与短期结构池中的实虚能量最小误差闭合。

## 0. 核心裁定

归因不是“有指代词/有缺口/有图片教学时才启动”的特殊过程。归因和预测一样, 是每个 tick 的基础过程。

每个 tick 都应有:

```text
当前短期结构 Q_t
  -> 召回历史相似现状 B_t
  -> 沿历史后继传播 C_forward
  -> 沿历史前因传播 C_backward
  -> C_forward 与未来/下一步期待做实虚误差闭合
  -> C_backward 与当前短期结构池中已经发生的线索做实虚误差闭合
  -> C* 形成预测/解释/行动后果/感受触发的结构化回灌
  -> 行动竞争选择观察、继续想、回答、询问、行动、放下或休眠
  -> 新实能量和行动后果写回经验流
```

因此, AP 的完整数学模型不是单向预测模型, 也不是特殊指代解析模型, 而是:

```text
每 tick 双向最小误差:
min E_total(t) = E_forward(t) + E_backward(t) + E_action(t) + E_value(t)
```

其中:

1. E_forward: “接下来会怎样”的后继预测误差。
2. E_backward: “为什么现在会这样”的前因归因误差。
3. E_action: “我做什么能让闭环更好”的行动后果误差。
4. E_value: 奖惩、先天规则、情绪和未闭合压力带来的价值误差。

## 1. 对 v1 的纠偏

v1 说:

```text
当前认知结构 Q_t
  -> 残差/缺口/未闭合/意外形成归因压力
  -> 在短期结构池和统一经验流中召回任意经验窗口
  -> C_backward 对候选来源进行主观竞争
```

这可以作为审计描述, 但不应作为底层实现主路径。它的问题是容易被写成“缺口触发检索器”。

v1b 裁定:

```text
Q_t 先召回历史相似现状 B_t;
C_forward 是 B_t 沿后继方向传播;
C_backward 是 B_t 沿前因方向传播;
当前短期结构池中已经发生的线索, 与 C_backward 前因虚能量中和;
中和程度最高、把握最高、被注意力选中的线索, 形成主观原因感。
```

也就是说, SourceGap 不是 C_backward 的主入口, 而是放大 C_backward 竞争强度的认知压力。即使没有明显缺口, AP 每 tick 也会有弱归因; 只是高熟悉、高闭合、低残差时, 归因波很快被中和, 不会进入显性注意。

## 2. 后继预测与前因归因的对称性

设当前短期结构为:

```text
Q_t = SSP_t[focused_subgraph]
```

召回历史相似现状:

```text
B_t = RecallSimilar(Q_t, ExperienceFlow)
```

每个历史命中片段 H_k 包含:

```text
H_k^- : 历史前因窗口
H_k^0 : 历史相似现状
H_k^+ : 历史后继窗口
```

则:

```text
C_forward(t)  = propagate(H_k^0 -> H_k^+)
C_backward(t) = propagate(H_k^0 -> H_k^-)
```

两者完全对称:

1. C_forward 问: 历史上这种现状之后通常发生什么?
2. C_backward 问: 历史上这种现状之前通常有什么条件?
3. C_forward 给未来 slot 注入虚能量。
4. C_backward 给前因/来源 slot 注入虚能量。
5. 现实输入、短期结构池线索和行动后果提供实能量。
6. 实虚中和形成闭合感、合理感、正确感和把握感。

## 3. C_backward 的实虚中和

当前短期结构池中不只有当前焦点, 还保留刚刚发生过的 occurrence:

```text
SSP_t = {o_1, o_2, ..., o_n}
```

C_backward 从历史相似现状传播出前因虚能量:

```text
V_cause = {v_1, v_2, ..., v_m}
```

对每个当前线索 o_i, 计算它对历史前因虚能量的中和程度:

```text
neutralize(o_i, V_cause) =
  align(o_i, v_j)
* energy_match(o_i.R, v_j.V)
* structure_edge_match(o_i, v_j)
* temporal_spatial_plausibility(o_i, Q_t)
* learned_bridge(o_i, v_j)
```

主观原因感:

```text
cause_grasp(o_i) =
  neutralize(o_i, V_cause)
+ active_energy(o_i)
+ recency_bias(o_i)
+ unclosed_or_affect_gain(o_i)
+ reward_punish_path_support(o_i)
- contradiction_pressure(o_i)
- conflict_entropy(o_i)
```

注意:

1. recency_bias 是拟人的近因偏差, 不是硬规则。
2. contradiction_pressure 来自后天反例, 不是先天禁止伪因果。
3. learned_bridge 可跨模态, 例如文字教学与图片 patch、声音与动作、情绪与话题。
4. 如果多个 o_i 都能部分中和, AP 可以形成多因解释或低把握解释。

## 4. 未中和时的归因

如果当前 SSP 中没有线索能很好中和 C_backward, AP 仍然可以形成主观归因, 但把握较低。

低中和归因来源包括:

1. 历史共现频繁。
2. 近期天然权重较高。
3. 情绪或奖惩权重高。
4. 未闭合感牵引强。
5. 结构相似但证据不足。
6. 噪声和联想导致跳跃。

这对应人类的:

1. 猜测。
2. 误会。
3. 迷信。
4. 触景生情。
5. 事后合理化。
6. “我不知道为什么, 但感觉和那个有关”。

因此, AP 不应要求每次归因都能完美中和。完美中和产生高把握合理感; 部分中和产生猜测; 无法中和但被情绪/近因/未闭合牵引时, 产生低把握联想。

## 5. 长距离归因如何自然发生

长距离归因不需要专门的“远距离搜索模块”。

过程:

```text
tick t:
  某个当前线索 o_i 与 C_backward 前因虚能量部分中和
  o_i 获得主观原因感和注意力

tick t+1:
  o_i 成为新的 Q_{t+1} 或 Q_{t+1} 的高权重组成
  再次召回与 o_i 相似的历史结构 B_{t+1}
  继续沿前因传播

tick t+k:
  多次跳转后到达很久以前的经验窗口
```

这更像人类回忆: 不是一下子全库搜索到十年前的事, 而是一个线索拉出另一个线索, 注意力一步步沿经验结构移动。高情绪、高奖惩、高未闭合可以让步长更大, 但仍是同一 tick 循环。

## 6. 每个过程都有预测和归因

AP 的任何过程都不是纯输入输出。每个过程都至少包含:

```text
感受器过程:
  预测: 当前采样后接下来应出现什么感受?
  归因: 当前感受来自哪个空间/时间/动作/内部来源?

注意过程:
  预测: 注意这个对象后能降低什么误差?
  归因: 当前违和/好奇/压力由哪些线索造成?

召回过程:
  预测: 召回片段的后继能解释下一步吗?
  归因: 召回片段的前因能解释当前吗?

行动过程:
  预测: 做这个动作会有什么后果?
  归因: 上一个后果是不是由我的动作造成?

学习过程:
  预测: 新经验会如何改变下次召回?
  归因: 奖惩/纠正应归到哪个线索、动作或解释路径?

闲时思考:
  预测: 这个想法继续下去会到哪里?
  归因: 我为什么又想起这件事?
```

这就是“每个过程都有归因和预测”。它不是额外功能, 而是 AP 最小误差闭环的基本形式。

## 7. 总误差形式

一个可实现的总误差草案:

```text
E_total(t) =
  lambda_f * E_forward(t)
+ lambda_b * E_backward(t)
+ lambda_a * E_action(t)
+ lambda_u * E_unclosed(t)
+ lambda_v * E_value(t)
+ lambda_c * E_conflict(t)
+ lambda_cost * E_cognitive_cost(t)
```

其中:

```text
E_forward(t) = distance(realized_successors, C_forward.prediction_slots)
E_backward(t) = min_alignment_error(SSP_recent_occurrences, C_backward.cause_slots)
E_action(t) = distance(action_outcome_real, action_outcome_predicted)
E_unclosed(t) = remaining_unclosed_energy_after_update
E_value(t) = reward_punish_prediction_error
E_conflict(t) = entropy_or_contradiction_among_active_slots
E_cognitive_cost(t) = energy_cost_of_attention_recall_action
```

行动竞争不是简单选择最大 reward, 而是选择在当前约束下最可能降低 E_total 的行动。人类很多时候会选择继续看、继续想、询问、放下、睡觉, 都可以从这里解释。

## 8. 对拟人性的影响

这个模型比 v1 更像人, 因为:

1. 人类确实每时每刻都在预测“接下来会怎样”, 也在隐性解释“为什么现在这样”。
2. 大多数熟悉场景中, 预测和归因误差很快中和, 所以不会显性意识到。
3. 意外、违和、压力、未闭合、痛苦、奖惩会让误差上升, 于是归因和预测进入注意。
4. 归因不是总正确, 而是主观中和最顺的解释先胜出。
5. 长距离回忆是注意力沿线索逐步跳转, 不是硬搜数据库。
6. 闲时思考是低外部输入下, 预测和归因围绕未闭合/情绪/自我叙事持续运行。

因此, 它更能解释:

1. “我刚才想说什么来着?”
2. “我为什么突然想到这个?”
3. “这个声音是不是刚才那个东西发出来的?”
4. “他刚刚那句话是不是在说我?”
5. “我感觉这件事和小时候某个经历有关。”
6. “我知道不一定对, 但总觉得是因为那个。”
7. “想了一会儿, 我又从一个线索想起另一个线索。”

## 9. 工程实现裁定

后续实现时:

1. 不应实现一个独立 attribution resolver。
2. 不应按图片/文本/音频分别写 recent recovery。
3. 不应由关键词直接决定归因对象。
4. 应在每 tick 的 B/C/C* 中同时生成 C_forward 和 C_backward。
5. 应在 RuntimeTickEvent 中展示:
   - B 命中的历史相似现状。
   - C_forward 后继预测 slots。
   - C_backward 前因归因 slots。
   - 当前 SSP 中哪些 occurrence 中和了哪些前因虚能量。
   - cause_grasp / prediction_grasp / unresolved_error。
   - 被注意力选中的归因线索。
6. 教师反馈应强化或惩罚“当前线索 o_i 与 C_backward cause slot 的中和关系”, 而不是写标签表。

## 10. 与白皮书的统一表述

建议白皮书最终写法:

> AP 每个 tick 都进行双向最小误差闭环。B 召回给出历史相似现状; C_forward 沿历史后继传播, 形成对未来的虚能量预测; C_backward 沿历史前因传播, 形成对来源和原因的虚能量解释。当前短期结构池中已经发生的线索与 C_backward 的前因虚能量中和, 产生主观原因感和合理感。预测与归因并不是两个模块, 而是同一经验结构在时间正向和反向上的对称传播。高闭合时它们隐性运行, 高误差时它们进入注意, 并通过行动、反馈、奖惩和学习不断降低总误差。

## 11. 最终裁定

v1b 覆盖 v1 的实现口径。v1 中 SourceGap / ExperienceWindow / AttributionCandidate 仍可作为审计字段保留, 但底层实现必须以“B 相似现状召回后的双向传播 + 当前 SSP 实虚中和 + 每 tick 最小误差”为主。

这比“当前缺口触发归因检索”更不硬, 泛化能力更强, 也更符合 AP 拟人哲学。
