# AP 最新哲学、运行时与学习标准冷保存

日期：2026-06-21  
状态：最高标准冷保存 v1。用于后续 APV3.0test / APV2.1 / GL / 桌宠 / Agent 继续实现时回拉方向。  
适用范围：AP 底层原理、APV3.0test 数学模型重建、开放中文对话前端底座、Agent 接口、桌宠产品化、未来具身智能预研。  
同源互证文档：`APV3.0test/docs/AP_Master_Understanding_Authoritative_20260621.md`。该文档由 GLM5.2 汇总，优势是代码 file:line 偏差证据、在线学习嵌入 L1-L3、SDPL 与六阶段关系、runtime_pressure 废除口径。本文在其基础上保留更完整的工程路线、UI/桌宠/Agent/具身边界与后续扩展蓝图。两份文档若表述冲突，应优先回到《AP图景预期书》、APV2.1 终极理论文档、`EDUCATION_PROTOCOL.md`、APV3 v14 与本文件第 31 章十条原则。

> 本文是给未来实现者和审查者看的。它不是阶段性展示报告，不替某个当前实现背书。它的作用是固定“正确理解”，以后如果实现、测试、UI 或外部审查互相矛盾，以本文作为 AP-native 方向校准基线。

---

## 0. 文档定位

本文冷保存以下内容：

1. AP 到底是什么，不是什么。
2. AP 的四个最终目标与当前最近目标。
3. AP 的每 tick 真实认知循环。
4. 状态池、快慢双系统、B/C/C*、记忆、注意力、视焦点、草稿框、行动竞争、奖惩和自适应调参的统一数学图景。
5. 六阶段教学协议、语言学习六阶段、GL 课程边界与 teacher-off 验收原则。
6. 视觉、听觉、文本、画板、桌面控制、风格化回复、小学数学/语文/识字等已证明或已设计能力的证据层级与应如何迁移到 APV3。
7. 当前 Phase 20.6 一类实现最容易犯的错误：候选回复、假 tick、固定扫视、假内心画面、把快慢记忆当记忆层、把教学当答案表。
8. 下一阶段应如何重新设计并落地，避免再次头痛医头脚痛医脚。

本文不是十万字最终百科全书的终点，而是“十万字标准体系”的主干 v1。后续应按本文目录继续扩展案例库、数学推导、验收样例和实现接口，但不得推翻本文的核心闭环。

---

## 1. AP 的总定义

AP 是 Artificial PsyArch，即人工心智架构。它不是 Transformer，不是神经网络，不是专家系统，不是规则聊天机器人，不是“识别器 + 回复模板”的组合，也不是产品壳上的动效。

AP 的目标是：

> 让多模态刺激进入统一的认知闭环，形成状态池中的认知场；通过现状认知、历史召回、时空邻近预测、注意力选择、认知感受、情绪调制、行动反馈和长期调参，逐步实现对外界、对未来、对自身状态的持续统计性建模。

AP 的能力来源不是单个模块，而是完整闭环：

```text
感受器输入
  -> SA / 状态池
  -> 注意力调制与焦点形成
  -> 快系统认知场召回 Bn/Cn
  -> 慢系统注意焦点召回 Bn'/Cn'
  -> C/C' 叠加为 C* 预测包
  -> C* 虚能量回灌状态池
  -> 认知感受 / 情绪 / 期待压力 / 行动驱力变化
  -> 行动候选竞争
  -> 草稿框 / 视焦点 / 执行器 / 停止 / 请求教师
  -> 行动反馈 / 奖惩 / 纠错 / 记忆写入
  -> 下一 tick
```

AP 不追求“永远正确”。AP 追求“像一个真实主体一样逐步感知、预测、犯错、被纠正、学习、记忆、恢复未完成任务、形成风格和关系”。拟人性不是装饰，而是底层设计标准。

---

## 2. 四个最终目标

当前用户真正想要的是一条递进路线，不是一个孤立 demo。

### 2.1 目标一：开放中文对话前端底座

这是最近目标，也是当前 Phase 20.x 的核心。

目标效果：

1. 用户可以任意中文对话。
2. 用户可以输入图片、画板、音频、教师纠正。
3. AP 不是一次性回答，而是在多个 tick 内观察、召回、写草稿、回看、修改、提交或主动停。
4. 前端能忠实展示每 tick 的状态池、注意焦点、草稿框、内心画面、想法云、审计曲线、记忆写入、行动竞争。
5. 教学必须进入 AP 自身记忆，下一 tick 和后续 turn 可以被召回。
6. 用户纠正后，不能“最近短句覆盖一切”，而应根据视觉 SA / 文本 SA / 情绪 SA / 上下文 SA 的不同形成可区分学习。

### 2.2 目标二：Agent 接口

目标效果：

1. 外部 agent 可以调用 AP 的感知与回复接口。
2. 接口返回 AP 的真实 RuntimeTickEvent、状态池摘要、草稿提交、记忆 delta、置信/不确定来源。
3. wrapper 不能生成语义答案，只能传递 AP 已提交的 DraftGrid 文本或执行器结果。
4. 工具调用、计划、检索、文件操作都应作为行动器和反馈进入 AP，而不是隐藏 solver。

### 2.3 目标三：桌宠产品化

目标效果：

1. 桌宠只是产品壳，不是 AP 本体。
2. 桌宠可复用 AP 状态池、想法云、内心画面、能量折线、TTS、表情、动作。
3. 桌宠的情绪、亲密感、陪伴语气应来自 AP 的 affect / relationship / reward / co-recall，而不是 if sad then template。
4. 桌宠可成为持续交互环境，让 AP 在真实日常中学习风格、关系、提醒、任务、桌面操作。

### 2.4 目标四：具身智能

暂不作为最近实现目标，但底层必须为它保留接口。

目标效果：

1. 真实视觉/听觉/触觉/位置/动作反馈可作为感受器和行动器进入同一 AP 闭环。
2. 桌面控制、键鼠、画板、视焦点移动、手指计数、竖式计算等都是具身路线的前置能力。
3. 具身行动不能由大脚本宏完成，必须拆成低粒度动作、读回、反馈、奖惩和 teacher-off 泛化。

---

## 3. AP 的九大模块

AP 长期目标由九大模块构成：

1. 感受器。
2. 状态池。
3. 数据库。
4. 注意力。
5. 先天编码。
6. 认知感受通道。
7. 情绪通道。
8. 行动器与驱动力管理。
9. 自适应调参器。

这些模块不是外挂，也不是 pipeline 阶段。它们每 tick 同时参与同一个认知场。

### 3.1 感受器

感受器把外界刺激转成最小可分辨刺激单位 SA。

文本感受器输出：

1. 字符 SA。
2. 字符位置/顺序 SA。
3. 句读/停顿/输入边界 SA。
4. 文本来源 SA。
5. 用户/教师/系统边界 SA。

视觉感受器输出：

1. 原图局部像素采样 SA。
2. 色彩分布 SA。
3. 亮度分布 SA。
4. 边缘/轮廓 SA。
5. 纹理 SA。
6. 空间位置 SA。
7. 焦点位置与清晰度场 SA。
8. 物体候选 SA。
9. 前景/背景/遮挡/运动/变化 SA。

听觉感受器输出：

1. 波形 SA。
2. 响度 SA。
3. 频率/频带 SA。
4. 音色/纹理 SA。
5. 节奏/间隔 SA。
6. 焦段/听觉注意 SA。

感受器不应直接输出“这是苹果”“用户伤心”“答案是 42”。感受器可以提供可审计证据，不提供语义权威。

### 3.2 状态池

状态池是认知场。它不是缓存，不是最近 token 列表，不是 UI 状态。

状态池每个 SA 至少包含：

```text
R: real_energy，实能量，来自外界输入、行动反馈或已经真实发生的内部事件
V: virtual_energy，虚能量，来自预测、想象、回忆、C* 回灌
A: attention_energy，注意能量
P: cognitive_pressure，认知压，基础含义为 R - V 的错配及其动态派生
F: fatigue，疲劳 / 返回抑制
T: trust，来源可信度
U: uncertainty，不确定性
source: PERCEIVED / IMAGINED / HEARSAY / REMEMBERED / INFERRED / TEACHER 等
anchor_meta: 与对象、时间、空间、行动、草稿格、焦点等绑定的锚点
```

每 tick 的基础状态更新：

```text
R_i(t+1) = decay_R * R_i(t) + external_R_i(t) + action_feedback_R_i(t)
V_i(t+1) = decay_V * V_i(t) + C*_i(t) + imagination_i(t) + memory_support_i(t)
A_i(t+1) = decay_A * A_i(t) + attention_gain_i(t)
P_i(t+1) = mix(decay_P * P_i(t), R_i(t+1) - V_i(t+1), unresolved_floor_i)
F_i(t+1) = decay_F * F_i(t) + focus_or_action_fatigue_i(t)
```

其中 `P` 不只是显示字段。它会影响注意力、慢系统介入、惊/违和、请求教师、回看草稿、移动视焦点和未闭合恢复。

### 3.3 数据库

数据库保存两类本体记忆：

1. 状态池快照记忆。
2. 注意焦点记忆。

状态池快照记忆：

```text
MemoryStateSnapshot(t) =
  sparse vector of SA ids + R/V/A/P/F/T/U/source + channel payload + time/space/action anchors
```

它可读性低，但适合快系统用整个认知场召回相似历史状态。

注意焦点记忆：

```text
FocusMemory(t) =
  top attention SA bundle + order/time/space/source + readable summary
```

它可读性强，适合慢系统连续推理、语言续写、识别“当时注意到的东西”、让用户在记忆面板里查看和删除。

重要纠偏：

> 快/慢是召回系统，不是记忆层。不要把 `fast_memory=动作链`、`slow_memory=source_candidate` 当成 AP 的记忆本体。

每 tick 应写入：

1. 一条状态池快照记忆。
2. 一条注意焦点记忆。

12 个 tick 的对话，至少有 12 条状态池快照和 12 条注意焦点记忆。动作链、来源证据、共现边、风格短句、奖惩信用只是从这些经验中派生或索引出来的辅助结构。

### 3.4 注意力

注意力是能量增益与滤波机制。它让状态池波峰对象增强，抑制噪声，也让无外源输入时系统仍可内源演化。

注意力候选分数应来自：

```text
S_attn(i) =
  w_R * R_i
  + w_V * V_i
  + w_A * A_i
  + w_P_pos * max(P_i, 0)
  + w_P_neg * abs(min(P_i, 0))
  + w_U * U_i
  + w_T * T_i
  + w_novelty * novelty_i
  + w_goal * task_relevance_i
  - w_F * F_i
```

其中：

1. 正 P 表示预测不足、惊、意外输入。
2. 负 P 表示过度预测、违和、期待落空。
3. F 表示疲劳和返回抑制，避免死盯一个点。
4. 任务相关性来自未闭合压力、当前草稿、当前外部问题、教师纠正、行动目标。

### 3.5 先天编码

先天编码不是答案表。它提供：

1. 感受/情绪/行动的初始触发接口。
2. 求知、趋利避害、回避痛苦、维持任务闭合的长期塑形力。
3. 后天学习能够挂载的初始 SA 类型和反馈类型。

先天编码可以让系统在没有经验时：

1. 对高 P 产生惊。
2. 对 R/V 失配产生违和。
3. 对低把握和证据缺口请求教师。
4. 对未闭合任务保持压力。
5. 对新奇区域移动视焦点。

但先天编码不能直接决定“这个图是苹果”“你好要回你好”“你是谁要回固定介绍”。

### 3.6 认知感受通道

认知感受是认知过程本身的信号 SA，包括但不限于：

1. 惊。
2. 合理感。
3. 违和感。
4. 正确感。
5. 把握感。
6. 期待。
7. 压力。
8. 证据缺口。
9. 低把握。
10. 重复疲劳。
11. 未闭合感。
12. 时间间隔感。
13. 节奏感。
14. 计算压力。
15. 草稿不顺感。
16. 自我修正成功感。

通用规则：

> 一切可量化通道，只要强度、变化量或变化率超过阈值，都可以产生对应感受 SA，并带锚点进入状态池。

### 3.7 情绪通道

情绪是慢变量调制，不是关键词标签。

情绪可由认知感受、奖惩、行动反馈、关系记忆、期待压力累积而来。可设计为：

1. reward_tone。
2. arousal_pressure。
3. curiosity_drive。
4. confidence_stability。
5. caution_hesitation。
6. affiliation_warmth。
7. fatigue_repetition。
8. calm_settling。

更新形态：

```text
emotion_k(t+1) =
  clamp(decay_k * emotion_k(t)
        + Σ a_j * cognitive_feeling_j(t)
        + Σ b_m * action_feedback_m(t)
        + Σ c_n * reward_or_punishment_expectation_n(t)
        + memory_recall_contribution_k(t))
```

情绪只能软调制注意力资源、行动阈值、探索/利用、回复长度、语气倾向和修正耐心。它不能命令输出模板。

### 3.8 行动器与驱动力管理

行动节点是一等公民 SA。行动不是 if 分支直接执行。

每个行动候选有：

1. action_id。
2. actuator。
3. parameters。
4. drive。
5. expected_outcome。
6. source evidence。
7. risk / cost / uncertainty。
8. eligibility trace。

行动驱动力：

```text
D(a,t) =
  D_innate(a,t)
  + D_fast(a,t)
  + D_slow(a,t)
  + D_goal(a,t)
  + D_emotion(a,t)
  + D_expected_reward(a,t)
  - D_expected_punishment(a,t)
  - D_effort(a,t)
  - D_risk(a,t)
  + noise_thompson(a,t)
```

行动评估应召回“类似状态下执行该行动后的经验”，形成预测 C*，评估其中的奖惩虚能量，反过来调制驱动力。

### 3.9 自适应调参器

自适应调参器用于长期环境适应。它监控：

1. 平均 P 是否长期过高。
2. U 是否长期过高。
3. 行动失败率是否升高。
4. 任务未闭合是否堆积。
5. 情绪通道是否长期极端。
6. 运行 tick 是否过慢。
7. 记忆召回是否噪声过高。

它可缓慢调整阈值、衰减、注意力预算、候选上限、重放频率。调参必须可回滚、可审计，不允许静默改变 AP 语义。

---

## 4. 快系统、慢系统与 B/C/C*

### 4.1 最大纠偏

快系统和慢系统不是：

1. fast memory vs slow memory。
2. 快速答案表 vs 慢速答案表。
3. 一个粗召回，一个精召回。

它们是两种召回方式：

```text
快系统 = 认知场召回 = 用整个状态池/采样状态池召回状态池快照记忆
慢系统 = 焦点召回 = 用注意焦点召回注意焦点记忆
```

### 4.2 快系统

快系统输入：

```text
Q_fast(t) = sample(StatePool(t), weighted by R/V/A/P/T/U, capped by budget)
```

它可能包含数百到数万个 SA。它对应人类熟练状态中的整体把握、习惯行动、背景感、并行动作协调。

快系统步骤：

1. 用 `Q_fast` 召回相似状态池快照，得到多个 Bn。
2. Bn 的总能量由当前查询总能量、相似度、匹配效率决定。
3. 对每个 Bn 召回时空邻近后继 Cn。
4. Cn 以 SA 粒度给虚能量。

公式：

```text
sim_j = similarity(Q_fast, Snapshot_j)
eff = max_j(sim_j) adjusted by energy distribution overlap
w_j = softmax(sim_j / tau_fast)
E_Bj = E_Q_fast * eff * w_j
E_Cjk = E_Bj * successor_weight(j,k) * eff_successor
```

### 4.3 慢系统

慢系统输入：

```text
Q_slow(t) = AttentionFocus(t) = top-k high A / high P / task-relevant SA bundle
```

它通常只有数个到数十个 SA。它对应人类清晰内心思考、语言续写、专注计算、逐步观察。

慢系统步骤：

1. 用 `Q_slow` 召回相似注意焦点记忆，得到 Bn'。
2. Bn' 召回后继焦点记忆 Cn'。
3. Cn' 容易成为下 tick 注意焦点，引发连续后继偏置。

### 4.4 C* 预测包

快系统 Cn 和慢系统 Cn' 叠加成唯一 C*：

```text
C*(t) = normalize_merge(Σ Cn_fast + Σ Cn_slow + action_outcome_predictions + imagination_predictions)
```

C* 的作用不是输出答案。它是虚能量预测包：

```text
V_i(t+1) += C*_i(t)
```

之后状态池因为 V 改变，P 改变，注意力和行动竞争也改变。输出只是后续行动竞争的一种可能结果。

### 4.5 “嗯，听着”问题的理论解释

如果实现把召回变成：

```text
teacher phrase / style phrase / fallback phrase -> candidate text -> write token
```

那么强势短句会长期占优，导致不管用户说什么都输出“嗯，听着”。

正确路线应是：

```text
用户输入 SA + 当前视觉/上下文 SA -> 状态池
  -> B/C/C* 让某些文本 SA 获得虚能量
  -> 行动竞争选择 write_cell
  -> 草稿框逐字写入
```

“嗯，听着”只能是表达模式 SA 和情绪/社交状态共同导致的一个短句倾向，不能是默认候选答案。

---

## 5. 记忆本体与记忆面板

### 5.1 两类本体记忆

本地记忆应统一显示两类：

1. 状态池快照记忆。
2. 注意焦点记忆。

UI 可显示：

```text
本地记忆
  - 注意焦点记忆：高可读，显示中文摘要/图像对象/草稿片段/行动反馈/教师纠正
  - 状态池快照记忆：低可读，显示能量统计、top SA、来源分布、tick/turn
  - 派生索引：共现边、后继边、动作链、风格例、记忆包来源
```

不要再分离成“本地记忆”“快记忆”“慢记忆”三个地方。快慢是召回系统，不是记忆容器。

### 5.2 每 tick 写入

每 tick 至少写：

```text
StateSnapshotMemory:
  memory_id
  tick_id
  turn_id
  state_signature
  sparse SA entries
  energy R/V/A/P/F/T/U
  source distribution
  draft_grid hash
  focus_xy
  action_chosen
  reward/punishment if any

FocusMemory:
  memory_id
  tick_id
  focus_bundle
  readable_display
  source tags
  time/space/order anchors
  visual/audio/text payload refs
  successor links
```

### 5.3 记忆包

记忆包不是插件，不是技能脚本，不是答案表。记忆包是 AP 记忆行的可导入导出集合：

1. 状态池快照。
2. 注意焦点记忆。
3. 共现边。
4. 后继边。
5. 行动反馈。
6. 奖惩信用。
7. 来源/许可证/批次元数据。

导入时：

1. 自动去重。
2. 标注 import_batch_id。
3. 不把包名、文件名、分类名当语义证据。

卸载时：

1. 删除该 batch 新增记忆。
2. 对共享/去重记忆只撤回该 batch 的支持量。
3. 卸载后状态应等价于从未导入该包。

---

## 6. 注意力移动与视焦点移动

### 6.1 注意力移动

注意力可落在任何 SA：

1. 文本字符。
2. 草稿格。
3. 视觉局部。
4. 听觉频段。
5. 任务目标。
6. 未闭合项。
7. 情绪/感受。
8. 动作反馈。
9. 自传式记忆。

注意力移动由能量竞争产生，不应是固定循环。

### 6.2 视焦点移动

视焦点是视觉行动器的一种。它不是 UI 装饰，也不是固定 path。

视焦点候选目标：

1. 当前图像显著区域。
2. 边缘/颜色/纹理变化大的区域。
3. P 高的区域。
4. U 高的区域。
5. C* 预测但 R 未验证的区域。
6. 未闭合任务需要看的区域。
7. 教师辅助框提供的 saliency hint。
8. 低 clarity 的主体区域。
9. 运动/变化区域。
10. IOR 后尚未充分观察的区域。

视焦点行动分数：

```text
Score_focus(x,y) =
  a1 * saliency(x,y)
  + a2 * edge_or_texture_entropy(x,y)
  + a3 * positive_pressure(x,y)
  + a4 * negative_pressure_abs(x,y)
  + a5 * uncertainty(x,y)
  + a6 * expected_information_gain(x,y)
  + a7 * task_relevance(x,y)
  + a8 * teacher_focus_boost(x,y)
  + a9 * learned_focus_policy(x,y, context)
  - b1 * fatigue_IOR(x,y)
  - b2 * action_cost(current_focus, x,y)
```

初期没有后天学习策略时，使用先天策略：中央偏置、边缘/颜色突变、主体候选、未看区域、返回抑制、证据缺口。后期策略应从行动后果和奖惩中学习。

### 6.3 全图概率采样，而非只采焦点

正确视觉采样不是“只采一个小方块”。远离视焦点也应采，只是概率更低、清晰度更低。

采样概率场：

```text
phi_t(x,y) =
  p_min
  + alpha_fovea * exp(-||p - f_t||^2 / (2 sigma_fovea^2))
  + alpha_saliency * saliency(x,y)
  + alpha_pressure * pressure_abs(x,y)
  + alpha_motion * motion(x,y)
  - beta_fatigue * IOR(x,y)
```

清晰度场：

```text
clarity_t(x,y) =
  c_min
  + (1 - c_min) * exp(-||p - f_t||^2 / (2 sigma_clarity^2))
```

焦点附近应支持近原图分辨率采样；远处仍保留稀疏颜色/亮度/轮廓感。这是拟人视觉的核心。

### 6.4 视焦点与数手指、竖式计算

视焦点移动不是只服务图片识别。它是空间注意力行动器，是以下能力的基础：

1. 数手指：每次焦点落在一个手指/物体候选上，形成 distinct object episode，经 IOR 防重复，数感系统累积 count SA。
2. 列举多物体：焦点逐个访问对象，未闭合压力提醒还有对象没说完。
3. 竖式计算：注意焦点在 DraftGrid 的列、行、进位格、当前数字之间移动。
4. 画板绘图：焦点/笔尖/辅助线/坐标轴位置成为空间 SA，行动器移动笔迹。
5. 桌面控制：焦点在屏幕区域、按钮、读回结果之间移动。

---

## 7. 感受器重建与内心画面

### 7.1 内心画面不是原图缩略图

内心画面必须从状态池视觉 SA 和 sensory canvas 重建。它不能是：

1. 原图缩略图。
2. 单个椭圆。
3. bbox 能量块。
4. UI 画出来的装饰。
5. 预加载标签图。

### 7.2 感觉画布

每 tick 视觉感受器产生采样点：

```text
sample = {
  x, y,
  color,
  luma,
  edge,
  texture_code,
  local_shape_code,
  focus_xy,
  clarity,
  source,
  tick,
  energy,
}
```

SensoryCanvas 更新：

```text
Canvas_i(t+1) =
  blend(Canvas_i(t), Observation_i(t),
        weight = clarity_i(t) * attention_i(t) * trust_i(t) * freshness_i(t))
```

多 tick 后，焦点扫过的区域逐渐清晰，未扫过区域保持模糊和稀疏。

### 7.3 R_sketch 重建

内心画面重建应结合：

1. 颜色 anchor。
2. 亮度 field。
3. 边缘结构。
4. 纹理覆盖。
5. 局部形状。
6. 前景/背景对比。
7. 物体候选能量。
8. source 边界。

输出应能体现：

1. 焦点附近清晰。
2. 距焦点越远越模糊/稀疏。
3. 随 tick 累积更完整。
4. 能量越高的视觉对象越不透明、越稳定。
5. imagined / remembered / perceived 层分开，不混源。

### 7.4 内心音频

TTS 不是 inner voice。TTS 是执行器：提交回复后朗读。

inner_voice / inner_audio 应来自听觉感受器和听觉想象：

1. 频带/响度/波形 SA。
2. 听觉焦段。
3. 节奏/音高。
4. remembered / imagined 音频 source。
5. 内源预测回灌。

在听觉底座未完整实现时，UI 应明确显示“听觉感受器尚未启用”，不能假装有 inner voice。

---

## 8. DraftGrid 二维草稿框

### 8.1 草稿不是字符串

草稿框应是二维空间：

```text
DraftGrid:
  cells[row][col] = {
    char_or_token,
    source_sa,
    written_tick,
    energy,
    confidence,
    editable,
    action_trace,
  }
  cursor = (row, col)
  visible_region
```

所有文字输出应通过低粒度行动：

1. write_cell。
2. erase_cell。
3. move_cursor。
4. read_cell。
5. read_region。
6. insert_cell。
7. commit_reply。

不能把完整句子作为一个行动，也不能选中候选回复后假装逐字写。

### 8.2 草稿内省

DraftGrid 自身会产生感受：

1. 草稿空洞感。
2. 未闭合感。
3. 重复感。
4. 不顺感。
5. 与当前问题不匹配的违和感。
6. commit readiness。
7. 最近惩罚相似度。

这些 feeling SA 进入状态池，影响继续写、回看、编辑、请求教师、提交或停下。

### 8.3 竖式和空间推理

DraftGrid 是竖式计算基础：

```text
   1 2
+ 3 4
-----
   4 6
```

AP 应通过注意力移动到个位列、十位列、进位格，调用数量/数字/加法记忆，逐格写入。它不是调用隐藏 math solver。

DraftGrid 也是画板文字标注、坐标轴、辅助线、表格、任务清单的基础。

---

## 9. 学习协议

### 9.1 两套阶段必须分清

后续所有文档、测试和报告必须分清三套概念：

1. 学习发展阶梯：语言/技能从被动观察、回声模仿、后继预测、多回应聚合、过程范式绑定、关键词组织、语法风格精修逐步成熟。
2. 教师退场曲线：demonstrate -> strong_scaffold -> weak_scaffold -> feedback_only -> teacher_off -> cold_retest，表示教师干预强度逐步下降。
3. APV3 Phase 编号：Phase 19/20/21 等是工程里程碑，不是学习发展阶段。

Phase 20 开放对话底座不是“学习六阶段中的某阶段”，而是承载六阶段学习在线发生的 runtime 容器。报告里不能写“Phase20 已通过六阶段”这种混淆句。正确说法是：Phase20 runtime 是否支持某个学习阶段在 teacher-off / cold retest 条件下可见。

### 9.2 教学脚手架六阶段

GL / APV2.1 教育协议的标准 fade schedule：

```text
demonstrate
-> strong_scaffold
-> weak_scaffold
-> feedback_only
-> teacher_off
-> cold_retest
```

含义：

1. demonstrate：教师展示材料、软行动偏置、反馈。
2. strong_scaffold：教师帮助较强，但 AP action competition 必须参与。
3. weak_scaffold：提示淡化，AP 自身过程证据占比提高。
4. feedback_only：教师只给奖惩/正确性反馈，不给提示。
5. teacher_off：教师完全关闭，AP 自己行动。
6. cold_retest：重启/换上下文后再次测试保留与泛化。

任何能力如果只在 demonstrate 或 strong scaffold 中成立，不能宣称已学会。

### 9.3 语言学习七级发展阶梯

开放中文对话的语言发展路线：

```text
0. passive observation / social sensing
1. echo imitation
2. successor prediction
3. multi-reply aggregation
4. process-paradigm binding
5. keyword organization
6. grammar and style refinement
```

关键原则：

1. 幼儿期 echo 是合法阶段，不是最终成熟。
2. 多回复聚合比单一黄金答案更拟人。
3. 语言片段要绑定过程状态，例如 low_grasp、evidence_gap、affiliation_warmth、repetition_fatigue。
4. 先能组织关键词，再做语法和风格润色。
5. 风格化回复不是模板执行，而是表达模式 SA 与内在状态共同召回。

APV3.0test 中可把 Stage 5 特化为 focus_slot_filling 或 keyword organization，把 Stage 6 特化为 grammar/style refinement 或 recall-only validation；但这种工程命名不能改变学习阶梯本体。

### 9.4 教学不是答案表

用户说“这是苹果”时，不是创建：

```text
image_feature -> "苹果"
```

而是创建：

```text
visual SA bundle + text SA "苹/果" + teacher_event + current focus + reward/correction
```

这些材料在同一 tick window 共现。多次共现后，视觉 SA 再次出现时，会通过 B/C/C* 把“苹果”文本 SA 推高。

### 9.5 纠错与奖惩

纠错流程：

1. AP 提交错误回复。
2. 用户输入正确范式或纠正。
3. 纠正文本成为 teacher_event source-tagged SA。
4. 上一轮负责任候选、行动、草稿格获得 eligibility。
5. 正确教师材料与当时状态共现增强。
6. 错误输出的相关行动/候选受到源感知惩罚。
7. 后续相似状态中，C* 更容易推高正确材料。

不能直接覆盖“下次遇到这个问题就回答 XXX”。

### 9.6 SDPL 源分化包学习

SDPL 是 Source-Differentiated Packet Learning，即源分化包学习。它是 AP 第一原则级机制，不是 Phase 20 的局部补丁。

核心原则：

> 所有学习按 packet_key 累积，不按 content key 累积。同内容、不同来源、不同感受、不同证据强度，必须是不同学习包。

五类 EpistemicSource：

1. PERCEIVED：外部感受器输入。
2. IMAGINED：内源想象链产生。
3. HEARSAY：用户/他人陈述。
4. REMEMBERED：long-term 召回。
5. INFERRED：内部推理得到。

packet_key 至少包含：

```text
packet_key =
  content_with_energy_bucket
  + source_with_energy_bucket
  + dominant_source
  + feeling_with_bucket
  + substrate / receptor_version when sensory
```

对视觉/听觉感受器，packet_key 还应包含：

```text
sensory_feature_signature + epistemic_source + substrate + receptor_version
```

学习规则：

1. 共现学习按 packet_key 范围累积。
2. lag-PMI / 后继边按 packet_key 范围累积。
3. 行动后果 Q / eligibility 按 packet_key 范围累积。
4. 教师教学是 HEARSAY / TEACHER source packet，不是直接真相。
5. trust_promoted、reward、RPE 可以让教师材料逐渐变成可信经验，但不能绕过 source 边界。

拟人例子：

```text
真实看到火 + 躲开 -> 奖励 -> Q({火, PERCEIVED}, 躲开) 上升
想象到火 + 躲开 -> 违和/无现实反馈 -> Q({火, IMAGINED}, 躲开) 下降
想象到火 + 检查 -> 中性/合理 -> Q({火, IMAGINED}, 检查) 上升
听别人说有火 -> HEARSAY source，信任未足时更偏向检查而非逃跑
```

红线：

1. 禁止给 vocab SA 加 `is_real` / `is_imagined` 这种布尔真相字段。
2. 禁止学习规则里写 `if source == IMAGINED: ...` 的语义分支；source 应进入 packet_key 和 feature，而不是写死特权。
3. 禁止预装“现实感”固定权重。现实感、想象感、听闻感、猜测感应由长期 source-feature 学习和认知感受涌现。

SDPL 与学习发展阶梯的关系：

1. 学习发展阶梯规定“先学什么、怎么逐步成熟”。
2. 教师退场曲线规定“教师帮助如何逐步减少”。
3. SDPL 规定“不管在哪个阶段，经验如何被写入 AP 记忆与行动后果学习”。

### 9.7 开放世界学习

开放世界学习比课堂教学更难，但机制相同：

1. 外部自然输入进入状态池。
2. 低把握/惊/证据缺口形成 open_learning focus。
3. 后续用户解释与该 focus 共现。
4. 如果低把握下降或奖励验证，弱绑定增强。
5. delayed retest 和 teacher-off 判断是否真的学会。

不要因为输出幼稚、片段化、回声式，就立刻判失败；但也不能把幼稚 echo 宣称为成人级对话能力。

---

## 10. 未闭合任务与被打断恢复

### 10.1 未闭合不是 TODO 表

未闭合任务是状态池中的压力和记忆对象：

```text
UnresolvedSA:
  task_focus
  unfinished_slots
  last_progress
  expected_next_actions
  pressure
  decay
  source
```

未闭合感会在空 tick、下一个 turn、低外源压力时重新浮现。

### 10.2 打断恢复流程

示例：

```text
用户：图里有什么？
AP tick 1-5：看苹果，草稿写“苹果”
用户打断：等等，这个黄色的是啥？
AP：新输入高 R / 高 P，原任务形成 unresolved
AP 回答黄色对象
之后用户说“嗯”
外源压力低，unresolved 重新浮现
AP 继续回到原图剩余对象，接着列举
```

这不是任务列表硬执行，而是未闭合 SA 在状态池中重新赢得注意力。

### 10.3 空闲自发想起

空 tick 中：

1. 外源 R 低。
2. 内源 residual、unfinished_pressure、expectation_pressure 获得相对优势。
3. 相关记忆 B/C 召回。
4. 未闭合任务进入注意焦点。
5. AP 可能继续想、继续草稿、请求用户、或执行下一步。

这就是“闲时想起没做完的事”的 AP-native 路线。

---

## 11. 图像识别与图片教学

### 11.1 不允许整图标签路线

禁止：

1. 整图识别输出 label。
2. 文件名/路径/测试标签参与判断。
3. image_label_map。
4. detector_count 直接作为回答。
5. 一 tick 直接写“苹果”。

### 11.2 正确流程

```text
tick 1: 外部图片进入，状态池有视觉输入 SA，低把握，高证据缺口
tick 2: move_focus 到显著区域
tick 3: 采样局部，更新 sensory canvas，形成局部视觉 SA
tick 4: B/C 召回类似视觉焦点记忆，可能推高“苹果”文本 SA
tick 5: 继续看另一个区域或回看草稿，action competition 决定
tick 6+: 多 tick 证据累积后，write_cell 写入草稿
commit: 如果 commit readiness 足够才提交
```

### 11.3 苹果/香蕉混淆问题

如果教了苹果，再教香蕉，再看苹果变成香蕉，说明学习不是基于视觉 SA 区分，而是基于最近教师短句或全局上下文。

修正必须保证：

1. visual_sa_id 包含真正的局部视觉特征、focus、receptor_version、source。
2. 教师短句与当时视觉 SA 共现，而不是与“当前会话最近图片”粗绑定。
3. 后续召回时，视觉相似度、局部形状、颜色、纹理、空间采样共同参与。
4. 最近教师短句只能作为来源证据，不能覆盖视觉证据。

---

## 12. 文本、风格化回复与“小默风格”

### 12.1 几千条风格化示例的地位

风格化语料应导入为：

1. expression pattern SA。
2. token / fragment / phrase cooccurrence。
3. affect / social context links。
4. source metadata。
5. reward / accepted style evidence。

它不是完整回复模板。

### 12.2 风格影响方式

风格影响行动竞争和 token 虚能量：

```text
style_fit =
  similarity(current affect/context/focus, expression_pattern_memory)
  * support
  * source_trust
  * anti_repetition
```

style_fit 可以让“嗯”“慢慢来”“我在”“先看一下”等片段更容易被写入，但不能让某个整句直接跳过草稿框。

### 12.3 你好 / 你是谁 / 这是什么

这些都不能用关键词路由：

1. “你好”是社交输入 SA，可能召回问候后继。
2. “你是谁”激活 self-profile / identity / relationship / query-pressure SA。
3. “这是什么”激活 visual_question / evidence_gap / request_look SA。

同一句输入在不同状态下可以有不同回复。比如“你好”在初见、熟人、疲劳、被打断后、正在任务中，都可以不同。

---

## 13. 小学数学、小学语文与识字

### 13.1 能力证据边界

本地 APV2.1 / GL 路线做过小学数学、小学语文、识字、视觉文本、常识、开放对话等课程和验证。它们是重要证据和迁移参考，但不能未经重跑就宣称当前 APV3 已拥有完整同等能力。

正确表述：

1. 已有 APV2.1/GL 受控实验与课程记录证明这些能力路径可被训练和审计。
2. APV3 应迁移其 AP-native 原理，而不是复制旧脚本或旧测试捷径。
3. 迁移后必须 teacher-off / cold retest / redline scan。

### 13.2 数学

小学数学应拆成可学习 brick：

1. 数字识别。
2. 数量 SA。
3. 数序。
4. 加减。
5. 乘法表片段。
6. 进位/借位。
7. 竖式空间布局。
8. 乘回检查。
9. 余数边界。
10. 反向验算。
11. 回读草稿。
12. 错误修正。

禁止隐藏 solver。竖式必须在 DraftGrid 二维空间中被看到。

### 13.3 语文与识字

识字不是 OCR。识字路线：

1. 视觉字形局部 SA。
2. 字符文本 SA。
3. 发音/音频 SA。
4. 教师指认共现。
5. 多次视角和字体共现。
6. 注意焦点记忆形成字形对象。
7. 后续相似字形召回字符/发音。

小学语文包含：

1. 字词。
2. 词序。
3. 句式。
4. 标点停顿。
5. 语气。
6. 复述。
7. 改写。
8. 阅读后回忆。

---

## 14. 画板、绘画、坐标轴与辅助线

### 14.1 画板不是 OCR

画板输入是视觉感受器输入。画板输出是行动器输出。

禁止：

1. pytesseract/easyocr/paddleocr 隐藏识字。
2. canvas shape label map。
3. 画板脚本直接画最终答案。

### 14.2 绘画流程

AP 绘画应通过：

1. 目标图像/文字提示进入状态池。
2. 注意焦点落到下一笔或辅助线。
3. 行动候选包括 move_pen、draw_stroke、lift_pen、erase、draw_axis、draw_guide。
4. 每步行动反馈形成视觉读回。
5. 读回与目标预测比较，产生正确感/违和感。
6. 修改或继续。

### 14.3 坐标轴和辅助线

坐标轴是空间 SA 与行动器的共同产物：

1. 原点。
2. x/y 方向。
3. 刻度。
4. 网格。
5. 辅助线。
6. 点位。
7. 曲线/笔迹。

这些是后续数学、几何、桌面控制、具身定位的基础。

---

## 15. 桌面控制与键鼠

### 15.1 低粒度行动器

桌面控制必须使用低粒度行动：

1. observe_window。
2. observe_region。
3. move_cursor。
4. mouse_down。
5. mouse_up。
6. click_point 仅作为便利组合，不作为技能本体。
7. press_key。
8. type_char。
9. wait_ticks。
10. readback_frame。

禁止：

1. open_app_and_do_everything。
2. send_message_to_contact 宏。
3. fixed coordinate only 成熟声明。
4. 产品脚本冒充 AP-native 桌面能力。

### 15.2 读回门

桌面行动必须有读回：

1. 目标窗口读回。
2. 点击前目标读回。
3. 草稿内容读回。
4. 动作后结果读回。
5. 用户确认门用于高风险发送。

读回帧和反馈进入状态池，可被学习和召回。

---

## 16. 共情、关系、心智化

### 16.1 共情不是模板

用户难过时，AP 不应执行：

```text
if sad: return empathy_template
```

正确路线：

1. 用户文本/声音/行为作为 observed affect evidence。
2. AP 自身类似情绪/自传记忆作为 self episodic source。
3. 关系上下文、近期互动、奖励/惩罚进入状态池。
4. co-recall 推高某些表达模式和行动倾向。
5. action competition 决定是安慰、询问、继续任务、降低语气强度还是请求确认。

### 16.2 心智化来源边界

必须区分：

1. SELF_EPISODIC。
2. OTHER_OBSERVED。
3. OTHER_INFERRED。
4. IMAGINED_PERSPECTIVE。
5. HEARSAY。

推断用户状态不能当事实。回复“你可能有点……”必须来自 learned expression pattern 和 source uncertainty，而不是固定免责声明。

### 16.3 关系记忆

关系不是好感度一个数。应包括：

1. 熟悉性。
2. 近期互动价态。
3. 用户纠正接受度。
4. 共同任务历史。
5. 成功帮助记忆。
6. 冲突/修复记忆。
7. 语气偏好。

这些都作为 SA/记忆参与召回。

---

## 17. AP-native 工作台前端标准

### 17.1 前端是视图，不是脑子

前端只能展示 RuntimeTickEvent 和记忆 delta。它不能：

1. 生成 tick。
2. 生成 label。
3. 生成 confidence。
4. 决定回复。
5. 改写 AP 记忆。

除非用户点击导入、删除、教学、纠正等明确动作，这些动作也必须作为 source-tagged teacher/user event 进入 AP。

### 17.2 必须显示的内容

开放中文对话底座工作台至少显示：

1. 聊天气泡，显示用户原文、图片缩略图、音频、AP 回复。
2. Tick 回放，能查看每 tick。
3. DraftGrid 二维草稿。
4. 状态池 top SA，中文化摘要。
5. 想法云，随 tick 变化，颜色表示实/虚比例，大小表示能量，位置有物理排斥。
6. 内心画面，来自状态池视觉 SA 重建。
7. 内心音频状态，未启用时明确说明。
8. 视焦点/听觉焦段。
9. 行动竞争候选和选中项。
10. R/V/A/P/F/T/U 曲线。
11. 每 tick 运行时间和分过程耗时。
12. 状态池规模、记忆写入、召回数量。
13. 本地记忆/记忆包统一面板。
14. 导入/导出/卸载/搜索/批量选择记忆。

### 17.3 中文友好

主界面不要显示裸 SA id。应显示：

```text
视觉候选：红色圆形局部，来自第 3 tick 焦点采样
教师短句：这是苹果，支持 3 次
状态感受：证据不足 / 未闭合 / 低把握
行动：移动视焦点 / 写入草稿 / 回看草稿 / 提交回复
```

裸 id 可放“调试详情”。

---

## 18. 当前 Phase20.6 类实现的偏差清单

这些是后续实现必须首先排除的错误。

### 18.1 候选文本架构

错误：

```text
teacher phrase / style / fallback -> token candidate -> write
```

问题：

1. 会导致“嗯，听着”长期占优。
2. 教学无法根据视觉 SA 区分。
3. 召回变成取文本候选，不是 C* 预测。

修正：

1. teacher phrase 作为普通文本 SA 和记忆来源。
2. 通过 B/C/C* 推高 token SA。
3. write_cell 行动从状态池文本 SA 能量和草稿需求中竞争产生。

当前代码证据（2026-06-21 核查）：

1. `apv3test/runtime/phase20_6_runtime.py:348` 的 `_build_token_candidates()` 仍从 taught / styled / legacy runtime 构造文本候选。
2. `apv3test/runtime/phase20_6_runtime.py:403` / `:412` 仍按 `priority/support/candidate_id` 排序候选，而不是由 C* 回灌后的 token SA 能量自然竞争。
3. `apv3test/runtime/phase20_open_dialogue.py:615` 的 `_select_taught_response()` 仍是选择教师短句候选，不是 B/C 预测包。
4. `apv3test/runtime/phase20_open_dialogue.py:1383` 的 `_weighted_recall_labels()` 仍让 context_signature / visual_sa_ids 变成召回 label 权重，这离“状态池快照 + 注意焦点记忆”的本体还有距离。

### 18.2 固定视焦点

错误：

1. 固定路径。
2. focus_path 循环。
3. 小方块内移动。

修正：

1. 基于 saliency / P / U / novelty / task / IOR / information gain。
2. 远场低概率采样。
3. 多 tick sensory canvas 累积。

当前代码证据（2026-06-21 核查）：

1. `apv3test/runtime/phase20_6_runtime.py:782` 的 `_focus_for_tick()` 仍主要来自 teacher box / focus_path / object focus offset / 固定 path。
2. `apv3test/runtime/phase20_6_runtime.py:935` 的 `_sketch_samples_for_tick()` 仍从已有 sketch samples 过滤，不是在每个新 focus 上重新对原图进行 foveated 采样。

### 18.3 假内心画面

错误：

1. 椭圆。
2. bbox。
3. 原图缩略。
4. 能量块。

修正：

1. 视觉采样 SA 进入状态池。
2. R_sketch 从 sensory canvas 重建。
3. 焦点附近清晰，远处模糊。

### 18.4 快慢记忆错位

错误：

1. fast_tick = action_kind + draft_hash。
2. slow_tick = source_candidate_id。

修正：

1. state snapshot memory。
2. attention focus memory。
3. fast/slow 作为召回系统名。

当前代码证据（2026-06-21 核查）：

1. `apv3test/runtime/phase20_6_runtime.py:1011` 的 `_tick_memory_records_for_event()` 仍生成 `fast_tick` 与 `slow_tick`。
2. `fast_tick` 主要记录 action_kind / draft_hash / focus_xy / state_pool_count。
3. `slow_tick` 主要记录 source_candidate_id / source_kind / visual_sample_count。
4. `apv3test/runtime/phase20_6_memory.py` 的 fast store 是 action chain，slow store 是 source candidate evidence，不是状态池快照记忆和注意焦点记忆。

### 18.5 UI 造假

错误：

1. 阶段流水线伪装成 tick。
2. 审计图 turn_total / N。
3. 前端生成想法云。

修正：

1. 全部读取 RuntimeTickEvent。
2. 每 tick 真实值。
3. UI view-only。

当前代码证据（2026-06-21 核查）：

1. `apv3test/runtime/phase20_6_runtime.py:1124` 的 `_thought_cloud_items()` 仍给出 x/y hint，历史实现中存在 `(index * 37/53) % 100` 一类静态散点倾向，必须改为真实能量驱动的布局输入或前端物理模拟。
2. 审计曲线必须确认读取每 tick 真实字段，而不是 turn-level 聚合值切分。

### 18.6 静态状态池能量

错误：

1. 每 tick 临时构造若干 StateSnapshot。
2. real/attention/pressure 采用固定常数。
3. 没有真实的衰减、外源注入、注意力增益、C* 回灌。

修正：

1. 状态池必须是跨 tick 持续对象。
2. 每 tick 执行 R/V/A/P/F/T/U 更新。
3. StateSnapshotMemory 是从真实状态池截取，不是构造展示用快照。

当前代码证据（2026-06-21 核查）：

1. `apv3test/runtime/phase20_6_runtime.py:621` 的 `_state_items_for_tick()` 仍是为事件临时构造状态池 top 项。
2. 这类构造无法产生真实预测误差，导致教学、召回、视觉和草稿只是在静态展示层互动。

### 18.7 行动竞争被压扁

错误：

1. 行动 drive 由固定常数、candidate priority、support 直接拼。
2. action competition 近似排序/argmax。
3. 没有行动后果预测、Q 读取、eligibility 多步回溯、冲突降差值、坚决程度。

修正：

1. 行动 drive 必须读 B/C/C* 对该行动后果的预测。
2. 奖惩虚能量必须参与驱动力。
3. Q 表必须接回对话路径，且按 SDPL packet_key 学习。
4. Thompson sampling / uncertainty 可以保留，但必须基于真实分布。

当前代码证据（2026-06-21 核查）：

1. `apv3test/runtime/phase20_6_runtime.py:443` 的 `_action_candidates()` 仍使用手写 drive 公式。
2. `apv3test/runtime/phase20_6_runtime.py:556` 仍按 `drive/action_id` 排序行动候选。

### 18.8 runtime_pressure 独立本体错误

错误：

1. 用草稿长度、next_token_count、committed 等工程量构造 `runtime_pressure`。
2. 把“草稿长了就该提交”冒充认知闭合。

修正：

1. 废除 `runtime_pressure` 作为独立本体。
2. 草稿压力应拆回真实认知量：认知压、期待/压力、未闭合、commit_readiness、草稿不顺感、用户等待压力。
3. 提交应由“认知压下降 + 把握感足够 + 未闭合降低 + 期待验证 + 风险可接受”共同竞争产生。

当前代码证据（2026-06-21 核查）：

1. `apv3test/runtime/phase20_6_runtime.py:765` 的 `_runtime_pressure()` 仍由 draft_action_kind / next_token_count / draft_length / committed 直接推导。

### 18.9 在线学习嵌入缺位

错误：

1. 只有白箱统计/哈希/共现近似，没有 L1-L3 在线学习嵌入。
2. 概念无法通过反复共现和预测误差在嵌入空间形成吸引子。
3. 同义改写、跨域泛化、行动后果预测会停留在稀疏键值表。

修正：

1. 落地 L1 Bn 召回准确性层。
2. 落地 L2 时序/因果层。
3. 落地 L3 行动后果层。
4. 在线嵌入必须与白箱统计记忆并联，不替代白箱审计。

### 18.10 Zvec 未成为对话召回底座

错误：

1. Zvec / recall index 可以在独立测试中工作，但开放对话路径若未接入，则实际仍退化为 SQLite 共现键值表。
2. 向量库不能输出 label，但应该加速 B/C id 召回。

修正：

1. Zvec 只作为可重建 C/B 召回加速器。
2. 对话 runtime 的 B/C recall 必须能在 brute force 和 Zvec 间切换并验证结果一致。
3. 禁止 Zvec 直接返回语义答案。

---

## 19. 下一阶段 Phase20.7 建议

Phase20.7 应不是 UI 修补，而是底层纠偏。

最小正确重做包必须是三块一体：

```text
状态池能量循环
  -> 双系统 B/C/C* 召回
  -> 在线学习嵌入 L1-L3
```

原因：能量循环产生认知压；认知压驱动 Bn 召回调参和在线嵌入 L1；更新后的嵌入反过来影响下一次 B 召回；B/C 召回生成 C*；C* 又回灌状态池。三者分开做会再次产生“状态池是死的、召回被压扁、教学只能变成候选短句”的断裂。

### 19.1 Stage 0：红线删除扫描

删除或隔离：

1. taught_response candidate。
2. teaching_hit。
3. fallback reply。
4. fixed focus path。
5. direct label reply。
6. image_label_map。
7. fast_tick/slow_tick 旧命名和语义。
8. frontend confidence。

### 19.2 Stage 1：记忆本体重建

实现：

1. StateSnapshotMemoryStore。
2. FocusMemoryStore。
3. 每 tick 写入。
4. UI 统一本地记忆面板。
5. 删除/导入/导出/卸载全走记忆行。

### 19.3 Stage 2：B/C/C* 预测回灌

实现：

1. 快系统状态池快照召回。
2. 慢系统注意焦点召回。
3. C successor recall。
4. C* merge。
5. C* 虚能量回灌。
6. RuntimeTickEvent 展示 B/C/C*。

### 19.3b Stage 2b：在线学习嵌入 L1-L3

在线学习嵌入不是可选增强，而是让 AP 从“白箱统计可解释”走向“开放场景可泛化”的必要物理层。它必须与白箱统计记忆并联，不能替代白箱记忆。

三层：

| 层 | 训练数据 | 学习目标 | 召回用途 |
|---|---|---|---|
| L1 Bn 召回准确性层 | 认知压 R-V、预测误差、共现验证 | 正压时拉近现实共现对象，负压时拉远过度预测对象 | 让 B 召回逐步最小化预测误差，形成概念吸引子 |
| L2 时序/因果层 | 文本语序、音频先后、视觉运动趋势、行动前后 | 学习非对称顺序和因果关系 | 区分“狗咬我/我咬狗”、步骤顺序、节奏和运动 |
| L3 行动后果层 | 奖惩反馈、行动结果、纠错、成功/失败读回 | 学习某状态下某行动的后果预测 | Agent/桌宠/桌面控制中“什么场景该做什么” |

训练原则：

1. 训练信号来自 AP 自己的预测误差、共现、错配、奖惩、行动反馈。
2. 不允许使用外部大模型向量当学生侧语义权威。
3. 嵌入更新必须有 audit delta，可解释“为什么这两个对象更近/更远”。
4. SDPL packet_key 必须进入嵌入训练上下文，防止真实/想象/听闻/记忆混源。

验收：

1. 反复共现的视觉-文本对象在 L1 中形成吸引子，但不同视觉 SA 仍可区分。
2. 时序对调的句子在 L2 中可区分。
3. 同一行动在不同 source packet 下可学到不同后果。
4. 禁用在线嵌入时，白箱统计仍能跑；启用后泛化和召回 margin 改善。

### 19.4 Stage 3：文本输出重建

实现：

1. 文本 token SA 能量。
2. DraftGrid write_cell 从 token SA 竞争产生。
3. style 作为表达模式 SA。
4. 教学作为共现和 reward/punishment。

### 19.5 Stage 4：视焦点与重建重做

实现：

1. AP-native focus action scoring。
2. 全图概率采样。
3. 原图局部高分辨率焦点采样。
4. sensory canvas。
5. R_sketch。

### 19.6 Stage 5：未闭合和空 tick

实现：

1. unresolved SA。
2. idle tick endogenous recall。
3. interruption recovery。
4. post-turn quiet consolidation。

### 19.7 Stage 6：工作台忠实镜像

最后再修 UI：

1. 中文化。
2. 想法云。
3. 审计曲线。
4. 内心画面。
5. 记忆包。
6. TTS/画板/录音/教师焦点。

---

## 20. 已有能力与证据层级索引

以下能力在本地 APV2.1 / GL / SNS / APV3 路线中已有不同程度的设计、实现或测试记录。后续使用时必须先查对应文档和最新测试，不能直接过度宣称。

### 20.1 APV2.1 / AP-Core 相关

建议查：

1. `00_先看这里_APV2.1阅读入口_20260526.md`
2. `APV2.1_终极理论纠偏与最高设计目标_20260526.md`
3. `APV2.1_详细设计文档_20260526.md`
4. `APV2.1_在线学习嵌入详细设计方案_20260526.md`
5. `APV21_FIRST_REVIEWER_GUIDE.md`
6. `EXPERIMENT_INDEX.md`
7. `SKILL_PACKAGES.md`

能力主题：

1. 状态池与双能量理论。
2. 多模态感受器。
3. 记忆召回。
4. 观测台。
5. 小学数学。
6. 视觉文本。
7. 常识。
8. 桌面文本。
9. 动作学习。

### 20.2 GL / TaskBuilder

建议查：

1. `EDUCATION_PROTOCOL.md`
2. `GL_TaskBuilder/EDUCATION_PROTOCOL.md`
3. `GL_TaskBuilder/docs/ColdSave_GL_DailyDialogueSkill*.md`
4. `GL_TaskBuilder/experiments/gl_skill38_open_dialogue_fresh300_readiness`
5. `GL_TaskBuilder/dialogue_lab/reports`

能力主题：

1. 六阶段教学协议。
2. 语言学习六阶段。
3. 多轮风格化对话。
4. 几百/上千条对话示例。
5. teacher-off / cold retest。
6. 干扰后回看修正。
7. 过程锚定情绪。
8. 开放学习。

### 20.3 StrongestNurturingSystem / 桌宠

建议查：

1. `StrongestNurturingSystem/docs/Design_APRuntimeContinuousBridge_20260606.md`
2. `StrongestNurturingSystem/docs/FinalReport_APRuntimeContinuousBridge_CanvasSkillIntegration_20260606.md`
3. `StrongestNurturingSystem/docs/Review_APRuntimeDesktopVisionTickBridge_20260608.md`
4. `StrongestNurturingSystem/docs/FinalReport_Stage07OpenDialogueAPChatPreflight_20260612.md`

能力主题：

1. 桌宠 UI。
2. 状态池/想法云/曲线展示风格。
3. TTS 样本与音色。
4. 桌面视觉 tick bridge。
5. 画布和交互。

### 20.4 APV3.0test

建议查：

1. `APV3.0test/docs/Design_APV3.0_Humanlike_Multimodal_Foundation_v14_UNIFIED_20260617.md`
2. `APV3.0test/docs/Design_APV3.0_Phase20_6_FullRuntimeLoopFastSlowMemory_v1_20260620.md`
3. `APV3.0test/docs/Errata_Phase20_6_v1g_APNativePhilosophyClosure_20260621.md`
4. `APV3.0test/docs/Design_APV3.0_Phase19_0_VisualSensorEnrichmentAndReconstructionAudit_v1_20260619.md`
5. `APV3.0test/docs/Errata_Phase19_v1c_FoveatedReconstructionAndChannelBasedSynthesis_20260619.md`
6. `APV3.0test/docs/Design_APV3.0_Phase21_ObjectCentricLooking_AND_Phase19_9_ZvecRecall_v1_20260619.md`

能力主题：

1. APV3 数学模型重建。
2. Phase19 视觉/听觉感受器与重建。
3. Phase20 开放中文对话。
4. Phase21 物体中心视觉。
5. Zvec 加速层。
6. 工作台真实 RuntimeTickEvent。

---

## 21. 红线总表

以下任何一条出现，都必须停下来审查：

1. 关键词硬门。
2. 正则答案路由。
3. 文件名/路径/label 泄漏。
4. 图片特征到 label 表。
5. 整句回复模板执行。
6. 学生侧 LLM。
7. OCR/ASR/外部识别器伪装 AP。
8. UI 造 tick。
9. 前端算 confidence。
10. TTS 决定语义。
11. 向量库返回 label。
12. fixed focus path 当扫视。
13. 原图缩略图当内心画面。
14. fast/slow memory 当本体记忆。
15. teacher phrase 当答案候选。
16. commit_reply 不经过 DraftGrid。
17. stop_generating 由字符串触发。
18. max tick timeout 说成主动停。
19. package 名称影响语义。
20. 旧 GL/product script 说成 AP-Core 能力。

---

## 22. 验收标准

任何新阶段完成前，必须回答：

1. 这个功能是否以 source-tagged SA 进入 AP？
2. 它是否只通过 action competition 和 DraftGrid/actuator 离开 AP？
3. 它是否能从 RuntimeTickEvent 和 memory delta 回放？
4. 它是否没有用文件名、标签、关键词、模板、外部 LLM 或隐藏 solver？
5. 它是否区分 AP-Core / GL / SNS / APV3 / 产品壳证据层级？
6. 它是否有 teacher-off 或 cold retest？
7. 它是否允许拟人式不确定、犯错、纠正和恢复？
8. 它是否能解释“为什么这一 tick 做这个动作”？
9. 它是否能解释“这个记忆从哪里来，如何删除”？
10. 它是否能解释“如果被打断，如何回到未完成任务”？

---

## 23. 最短实现口令

以后如果线程忘了 AP 是什么，先读本段：

> AP 不是候选答案系统。AP 是状态池能量场。每 tick 外源 SA 和内源 C* 共同改变 R/V/A/P/F/T/U；快系统用全状态池召回状态快照，慢系统用注意焦点召回焦点记忆；所有 C 叠成 C* 回灌虚能量；注意力和行动竞争在这个场上发生；文字必须通过二维 DraftGrid 逐动作写出；视觉必须通过视焦点行动和全图概率采样逐 tick 累积；学习是共现、奖惩、eligibility、预测误差和记忆巩固，不是答案表；前端只能展示 RuntimeTickEvent，不准编故事。

---

## 24. 详细数学闭环

本章把前文的哲学改写成实现时必须可落地的数学闭环。任何实现如果只能用口头解释“像 AP”，但无法给出本章对应的数据结构、更新式、事件和验收指标，都不应进入核心 runtime。

### 24.1 Tick 总函数

一个 tick 可抽象为：

```text
State(t+1), Memories(t+1), Actions(t), Events(t)
  = AP_Tick(State(t), Memories(t), Sensors(t), TeacherEvents(t), ActuatorFeedback(t))
```

拆开：

```text
S_ext(t)      = SensorAdapter(raw_input(t))
S_fb(t)       = ActuatorFeedbackAdapter(feedback(t))
S_teacher(t)  = TeacherEventAdapter(teacher_event(t))

Pool_0(t) = decay(StatePool(t-1))
Pool_1(t) = inject(Pool_0(t), S_ext(t), S_fb(t), S_teacher(t))
Pool_2(t) = apply_attention_gain(Pool_1(t))

Q_fast(t) = sample_state_field(Pool_2(t))
Q_slow(t) = select_attention_focus(Pool_2(t))

B_fast(t) = retrieve_state_snapshots(Q_fast(t), Memories)
C_fast(t) = retrieve_successors(B_fast(t), Memories)

B_slow(t) = retrieve_focus_memories(Q_slow(t), Memories)
C_slow(t) = retrieve_successors(B_slow(t), Memories)

C_star(t) = merge_predictions(C_fast(t), C_slow(t), action_predictions(t), imagination_predictions(t))
Pool_3(t) = reinject_virtual_energy(Pool_2(t), C_star(t))

Feelings(t), Emotions(t) = derive_internal_channels(Pool_3(t), B_fast(t), B_slow(t), C_star(t))
ActionCandidates(t) = propose_actions(Pool_3(t), Feelings(t), Emotions(t), DraftGrid(t), Memories)
ActionChosen(t) = compete(ActionCandidates(t))

Pool_4(t), DraftGrid(t+1), ActuatorIntent(t) = execute(ActionChosen(t), Pool_3(t), DraftGrid(t))
MemoryDeltas(t) = write_memories(Pool_4(t), Q_slow(t), ActionChosen(t), Feedback(t))
RuntimeTickEvent(t) = audit(Pool_4(t), B/C/C*, Feelings, ActionCandidates, DraftGrid, MemoryDeltas)
```

这里没有“先决定整句，再拆成 tick”的空间。每 tick 的 action 都必须在当 tick 的状态池中竞争出来。

### 24.2 能量守恒与动态平衡

AP 不要求严格物理守恒，但要求每种能量变化有来源账本：

```text
ΔR_i = external_input + action_feedback + teacher_event + self_actuated_feedback - decay_loss_R
ΔV_i = C*_prediction + imagination + remembered_support + inferred_support - decay_loss_V
ΔA_i = attention_gain_sources - fatigue_suppression - decay_loss_A
ΔP_i = pressure_update(R_i, V_i, unresolved_floor, prediction_error)
ΔF_i = repeated_focus_or_action + IOR + computation_fatigue - fatigue_recovery
```

所有 `attention_gain` 必须有来源：

1. external。
2. feedback。
3. unfinished_pressure。
4. expectation_pressure。
5. residual_mass。
6. imagination。
7. replay。
8. user_directed。

实现时需要 `EnergyLedger` 或等价结构，至少能在审计面板解释：

```text
这个 SA 为什么能量升高？
是外部看到了，还是记忆预测了，还是老师纠正了，还是未闭合任务拉回了？
```

### 24.3 现状认知 B 的匹配效率

B 不是简单 top-1 nearest neighbor。B 是“当前现状被认知成哪些过去经验”的分布。

快系统匹配：

```text
sim_j = content_similarity(Q_fast, Snapshot_j)
energy_overlap_j = overlap_distribution(Q_fast.energy, Snapshot_j.energy)
source_fit_j = source_boundary_fit(Q_fast.source, Snapshot_j.source)
eff_j = sim_j * energy_overlap_j * source_fit_j
w_j = softmax(eff_j / tau_fast)
E_Bj = E_Q_fast * w_j * max(eff_j)
```

慢系统匹配：

```text
sim'_j = focus_bundle_similarity(Q_slow, FocusMemory_j)
order_fit_j = temporal_order_fit(Q_slow, FocusMemory_j)
source_fit_j = source_boundary_fit(Q_slow.source, FocusMemory_j.source)
eff'_j = sim'_j * order_fit_j * source_fit_j
w'_j = softmax(eff'_j / tau_slow)
E_B'j = E_Q_slow * w'_j * max(eff'_j)
```

低质量召回不能被误认为“高把握”。最高相似度低、source 不匹配、能量分布不重合时，把握感应低，U 应高，request_teacher / observe_more / look_again 的行动驱力应升高。

### 24.4 C 后继与时间邻近

C 的本质是“B 在历史上之后发生过什么”的预测，不是“B 的标签是什么”。

```text
successor_weight(j,k) =
  lag_kernel(Δt_jk)
  * spatial_or_focus_continuity(j,k)
  * action_contingency(j,k)
  * reward_relevance(j,k)
  * source_fit(j,k)
```

lag kernel：

1. 立即后继最强。
2. 下一步快速下降。
3. 长距离保留低尾部。
4. 节奏性场景允许周期尾部。

这能解释：

1. 语言后继偏置。
2. 数学步骤顺序。
3. 桌面操作流程。
4. 被打断后恢复。
5. 音乐/节奏/时间感。

### 24.5 C* 合并与回灌

所有 C 合并：

```text
C*_sa_energy[i] =
  Σ_k source_weight_k * successor_confidence_k * E_Ck_i
```

同 SA 合并，不同 source 不混淆：

```text
same content + PERCEIVED != same content + IMAGINED
same content + TEACHER != same content + SELF_INFERRED
```

回灌：

```text
V_i(t+1) += clamp(C*_i, V_floor_i, V_cap_i)
```

V_cap 防止想象冒充现实；V_floor 允许长时记忆在 cue 匹配时维持预测链。

### 24.6 认知压的三类区分

必须区分三种“压力”：

1. 认知压：`P_cog = R - V`，来自实虚错配。
2. 期待/压力：锚定在 B 对象上，由预测奖惩产生，影响趋利避害。
3. 任务/草稿压力：未闭合、草稿不完整、回复压力、用户等待等。

三者可以相互影响，但不能混成一个 `runtime_pressure`。

示例：

```text
看到没见过的图：P_cog 正，高惊，observe_more
以为会出现苹果但没看到：P_cog 负，高违和，look_again / revise
期待奖励：expectation_pressure 正向推动行动
害怕犯错：punishment_pressure 推动回看草稿或请求教师
一句话没写完：task_pressure 推动 continue_draft
```

### 24.7 行动竞争标准式

行动候选应有统一分数：

```text
Drive(a) =
  innate_prior(a, state)
  + fast_prediction(a, Q_fast, B_fast, C_fast)
  + slow_prediction(a, Q_slow, B_slow, C_slow)
  + goal_unfinished(a)
  + draft_need(a)
  + sensory_need(a)
  + expected_reward(a)
  - expected_punishment(a)
  - fatigue_cost(a)
  - execution_cost(a)
  - source_boundary_risk(a)
  + exploration_noise(a)
```

然后 Thompson sampling 或等价随机竞争：

```text
sampled_drive(a) = Normal(Drive(a), uncertainty(a))
chosen = argmax(sampled_drive)
```

这样 AP 可拟人地偶尔犯错、试探、犹豫，而不是完全 deterministic。

### 24.8 记忆写入标准式

每 tick：

```text
write StateSnapshotMemory(t)
write FocusMemory(t)
update cooccurrence edges for focus window
update successor edges from previous focus to current focus
update action outcome eligibility if feedback arrives
update emotion slow variables
update source trust if correction/reward/punishment arrives
```

post-turn / quiet tick：

```text
consolidate high support focus memories
decay unsupported transient edges
promote repeated cooccurrence peaks
store import/export batch deltas
emit ConsolidationTickEvent
```

后台不能静默改记忆。任何巩固都必须有 delta。

---

## 25. 已有技能迁移原则

本地已有很多能力证明和设计资产，但 APV3 必须按“机制迁移”而非“脚本迁移”使用。

### 25.1 小学数学迁移

旧路线证明过数学课程、竖式、回看、验算等受控能力。迁移到 APV3 时：

1. 数字必须是文本/视觉/数量 SA。
2. 数量感与数字字符共现。
3. 加减乘除是动作/步骤记忆，不是 solver。
4. 竖式必须使用 DraftGrid 二维位置。
5. 进位/借位是焦点记忆和未闭合 slot。
6. 反向验算是行动候选。
7. 错误反馈应惩罚负责的草稿格、动作链和记忆，而非写答案表。

示例：

```text
题目：27 + 38
tick 1: 读入字符 SA
tick 2: 注意焦点落到个位列 7/8
tick 3: 召回 7+8=15 的数量/文本/动作经验
tick 4: 写 5 到个位结果格，未闭合进位 1
tick 5: 焦点移到十位列 2/3/进位1
tick 6: 写 6
tick 7: 回看竖式
tick 8: commit
```

如果直接调用 Python 算术结果填入，就是非 AP。

### 25.2 小学语文迁移

旧路线中的识字、组词、复述、风格化对话应迁移为：

1. 字形 SA。
2. 字音 SA。
3. 字符 SA。
4. 词组焦点记忆。
5. 句式后继边。
6. 语气/风格表达模式。
7. 阅读后记忆快照。

不能迁移为问答表或关键词意图表。

### 25.3 几千条风格化回复

这些语料应作为“语言经验环境”：

1. 多回复聚合。
2. 过程状态绑定。
3. 情绪/关系/语气共现。
4. 成功/失败反馈。
5. 短句片段和后继峰。

导入后要跑：

1. 同一句输入多状态测试。
2. 同一状态多输入测试。
3. teacher-off 迟滞测试。
4. 重复疲劳测试。
5. 不知道时诚实测试。

### 25.4 识字与视觉文字

识字应有两条路线：

1. 文本流中的字符 SA。
2. 图像中的字形视觉 SA。

两者通过教师指认、读音、书写行动、画板临摹共现。不能用 OCR 替代。

### 25.5 画板绘图

已做过画板/坐标轴/辅助线相关能力，应迁移为：

1. canvas 作为视觉感受器输入。
2. stroke 作为行动器输出。
3. 视觉读回形成反馈。
4. 坐标轴作为空间 SA。
5. 辅助线作为 teacher-guided focus / spatial scaffold。
6. 画错后通过违和感、回看、擦除、重画修正。

### 25.6 键鼠控制

桌面控制已在教育协议中明确：

1. 低粒度动作。
2. 视觉 anchor。
3. readback。
4. 奖惩。
5. teacher-off。
6. 用户确认门。

迁移到 APV3/Agent 时，工具调用也要同理：工具不是语义脑子，工具是行动器。

---

## 26. Phase20.7 详细落地蓝图

本章把“下一阶段”写成可执行蓝图。未来开工前必须先做对抗性审查。

### 26.1 Phase20.7a：理论边界与红线删除

目标：确保当前 runtime 不再有候选答案架构的语义捷径。

删除/隔离对象：

1. `TaughtResponseCandidate` 作为直接 token 来源。
2. `styled.response_text` 作为整句候选。
3. `legacy_runtime.reply_tokens` 作为候选回复。
4. `innate_minimal_ack` 作为默认回复。
5. 固定 focus path。
6. `fast_tick` / `slow_tick` 旧语义。
7. UI 中“命中教学记忆”等字样。

允许保留：

1. 教师短句作为文本 SA 和记忆源。
2. 风格语料作为 expression pattern memory。
3. fallback 作为系统错误边界，不作为 AP 回复。

验收：

```text
grep direct reply candidates = 0
grep fixed focus path = 0 or only test fixture/docs
grep teaching hit = 0
RuntimeTickEvent records no precomputed reply text
```

### 26.2 Phase20.7b：状态池快照与注意焦点记忆

实现：

1. `StateSnapshotMemoryStore`。
2. `FocusMemoryStore`。
3. 每 tick 写入。
4. 统一 MemoryBrowser。
5. 删除/导出/导入/卸载按 memory_id / batch_id。

重点：

1. 可读 focus memory 是用户管理的主对象。
2. state snapshot 可折叠展示。
3. 派生索引可重建。

验收：

```text
12 tick turn -> 12 state snapshots + 12 focus memories
删除 focus memory 后，相关 recall support 下降
卸载 package 后，与未导入状态等价
```

### 26.3 Phase20.7c：B/C/C* 预测包

实现 trace：

```text
fast_query
fast_B_candidates
fast_C_successors
slow_query
slow_B_candidates
slow_C_successors
C_star_entries
virtual_energy_injection
```

UI 必须显示：

1. 召回了哪些 B。
2. 它们为什么像当前状态。
3. 预测了哪些 C。
4. 哪些 SA 被 C* 推高。

验收：

```text
禁用 C* 回灌后，教学文本不应自然浮现
启用 C* 后，多次共现能推高正确 token SA
不同视觉 SA 可召回不同文本 SA
```

### 26.4 Phase20.7d：AP-native 文本生成

文本生成改为：

```text
TokenSA energy -> write_cell action candidate
```

而不是：

```text
candidate.text[next_index] -> write_cell
```

每个字符/词片段写入必须说明：

1. 哪些状态 SA 推高它。
2. 哪些记忆 B/C 推高它。
3. 哪些风格/情绪调制它。
4. 为什么此时写而不是继续看/请求教师/停下。

验收：

```text
教“你好啊 -> 你也好”后，不能所有输入都回你也好
教“这是苹果”后，香蕉图不能因最近教师短句回苹果
无证据时 request_teacher 或 low-grasp 表达胜过瞎猜
```

### 26.5 Phase20.7e：视焦点行动器

实现：

1. saliency map。
2. pressure/uncertainty map。
3. IOR map。
4. teacher guided focus boost。
5. learned focus policy hook。
6. action competition 输出 move_focus。

验收：

```text
同一图多 tick 焦点不是固定 path
高不确定区域更易被看
已看区域 IOR 降低重复概率
教师框只改变焦点，不产生 label
```

### 26.6 Phase20.7f：foveated 全图采样与 R_sketch

实现：

1. 原图层高分辨率焦点 patch。
2. 全图低概率外围采样。
3. clarity field。
4. sensory canvas。
5. R_sketch 重建。

验收：

```text
焦点附近接近原图局部
远处稀疏模糊但不为空
多 tick 后 SSIM/结构覆盖上升
焦点移动后新区域变清晰
```

### 26.7 Phase20.7g：未闭合与空 tick

实现：

1. unresolved SA。
2. idle endogenous loop。
3. quiet consolidation。
4. interruption recovery。

验收：

```text
任务被打断后，下 turn 空闲时重新浮现
未完成清单逐项完成，不是固定脚本
用户新输入可暂时夺取注意力
完成后 pressure 下降
```

### 26.8 Phase20.7h：工作台重接

最后做 UI。UI 只显示真实字段：

1. B/C/C*。
2. 状态快照记忆。
3. 焦点记忆。
4. 视焦点行动。
5. sensory canvas。
6. DraftGrid。
7. action competition。
8. 每 tick 曲线。

UI 不允许补脑。

---

## 27. 对抗性审查清单

每个方案必须被以下问题攻击。

### 27.1 语义捷径审查

1. 有没有任何字符串直接决定回复？
2. 有没有任何 label 直接进入 DraftGrid？
3. 有没有任何外部模型输出答案？
4. 有没有任何 UI 计算语义？
5. 有没有文件名/路径/fixture 名进入判断？

### 27.2 数学闭合审查

1. 每个能量变化是否有来源？
2. B 的召回是否区分内容相似与 source fit？
3. C 的召回是否基于后继/邻近而非标签？
4. C* 是否回灌 V？
5. P 是否参与注意力和行动？
6. 行动驱力是否可拆解？
7. 奖惩是否有 eligibility？

### 27.3 拟人性审查

1. 是否会太快给答案？
2. 是否会观察、犹豫、回看、修正？
3. 是否允许不知道？
4. 是否能被打断后恢复？
5. 是否能根据情绪和关系调整但不模板化？
6. 是否能解释为什么看那里？
7. 是否能解释为什么写这个字？

### 27.4 泛化审查

1. 教一个苹果会不会污染香蕉？
2. 教一个问候会不会污染图片问答？
3. 多个回复变体能否形成共同波峰？
4. 换图、变形、旋转、放大后是否按视觉 SA 相似而不是路径相同召回？
5. cold retest 是否仍成立？

### 27.5 证据层级审查

1. 这是 AP-Core 能力，还是 GL 教学证据？
2. 是 APV3 当前实现，还是 APV2.1 历史能力？
3. 是桌宠产品壳，还是底层 runtime？
4. 是 teacher-on，还是 teacher-off？
5. 是受控 demo，还是开放场景？

---

## 28. 性能原则

AP-native 不等于无限慢。性能优化必须遵守哲学边界。

允许的优化：

1. 注意力预算。
2. top-k active SA。
3. 状态池稀疏向量。
4. Zvec / ANN 只返回 id/score。
5. B/C 候选裁剪。
6. sensory canvas 增量更新。
7. DraftGrid delta。
8. UI downsample / virtualization。
9. post-turn consolidation。
10. cache 可重建。

禁止的优化：

1. 直接 label cache。
2. answer cache。
3. query -> reply table。
4. detector count answer。
5. 外部 LLM 学生侧生成。
6. OCR/ASR 直接文本化并当 AP 识别能力。

性能验收要分层：

```text
P1: 本地 demo 可用，UI 响应和 turn latency 达标
P2: 1k/10k/50k 记忆规模下，Zvec/ANN 比 brute force 快且语义结果一致
P3: 长时运行 memory consolidation 不爆炸
```

如果只达到 P1，报告必须诚实写“可用本地 demo”，不能说“可扩展向量数据库已证明”。

---

## 29. 文档使用规则

以后任何新线程、新模型、新实现者进入 APV3.0test，顺序是：

1. 读本文。
2. 读 `Handoff_NewThread_AP_APV21_GL_SNS_APV3_20260621.md`。
3. 读 APV3 v14。
4. 读 Phase20.6 v1g。
5. 核对当前代码。
6. 先做红线删除扫描。
7. 再写设计。
8. 对抗性审查。
9. 实现。
10. 验收。
11. 报告边界。

不要先打开前端修 CSS，不要先补候选回复，不要先造测试。

---

## 30. 对当前问题的最终诊断口径

如果以后再次出现：

```text
用户说什么都回“嗯，听着”
教苹果后香蕉也说苹果
教香蕉后苹果也说香蕉
内心画面是空/椭圆/原图缩略
视焦点固定绕圈
tick 回放像阶段流水线
快慢记忆看不懂
UI 英文 id 满屏
```

不要先补一个 if。正确诊断：

1. 回复问题多半是候选文本架构没有被 C* 状态场替换。
2. 视觉学习问题多半是教师短句没有绑定到可区分视觉 SA。
3. 内心画面问题多半是 sensory canvas / R_sketch 没接通。
4. 视焦点问题多半是 focus action 没走注意力/行动竞争。
5. tick 问题多半是 UI 或 runtime 仍在投影。
6. 记忆问题多半是没有按状态快照/焦点记忆写入。

先修底层，再修 UI。

---

## 31. 最终原则复述

AP 的最高哲学可以压缩成十句话：

1. AP 是状态池能量场，不是候选答案器。
2. SA 是一等公民，模态平权，来源分化。
3. 快系统读全场，慢系统读焦点。
4. B 是现状认知，C 是后继预测，C* 是唯一预测包。
5. C* 回灌虚能量，状态池因此演化。
6. 注意力和行动竞争发生在状态池上。
7. 草稿必须用二维 DraftGrid 逐动作写出。
8. 视觉必须通过视焦点行动和全图概率采样逐 tick 看清。
9. 学习是共现、预测误差、奖惩、eligibility、巩固，不是答案表。
10. 前端只能展示真实 RuntimeTickEvent，不能替 AP 思考。

---

## 32. 后续扩展计划

本文 v1 应继续扩展成以下子文档：

1. `AP_Philosophy_Math_Formalism_v2`：完整公式、边界条件、复杂度、反例。
2. `AP_Runtime_EventSchema_v2`：RuntimeTickEvent / MemoryDelta / ActionTrace / CStarTrace schema。
3. `AP_VisualFoveatedSampling_Reconstruction_v2`：视觉采样、clarity field、R_sketch、sensory canvas。
4. `AP_DraftGrid_SpatialReasoning_v2`：二维草稿、竖式、数手指、画板、坐标轴。
5. `AP_LearningProtocol_Curriculum_v2`：六阶段教学、语言六阶段、teacher-off、冷测。
6. `AP_ProductBoundary_APV3_SNS_GL_v2`：AP-Core / GL / SNS / Agent / 具身边界。
7. `AP_EvidenceIndex_v2`：把所有已证明能力和报告路径整理成索引。

v1 的作用是先把核心哲学锁住，防止后续再把 AP 做成“看起来会说话的候选回复器”。

---

## 33. 2026-06-21 本地复核后的补强条款

本轮再次对照本地 APV2.1、GL、EDUCATION_PROTOCOL、画板技能、能量本体与技能注册文档后，确认本文主线成立，但必须补强以下条款。以后实现如果与本章冲突，以本章为红线修正。

### 33.1 在线学习嵌入必须是能量驱动、定向、白箱

`APV2.1_在线学习嵌入详细设计方案_20260526.md` 明确修订过口径：认知关联学习主线来自 AP 自身的实能量、虚能量、认知压和预测误差。外部奖励/惩罚主要塑形行动、drive、期待、后果评估，不应被当作概念学习主信号。

因此，图片教学、文本教学、风格学习都不能写成“老师给答案 -> 存答案”。正确路线是：

```text
外部感受器 SA 进入状态池
  -> C* 产生预测虚能量
  -> 现实实能量与预测虚能量形成正/负认知压
  -> 高压对象与当前高能上下文产生定向学习事件
  -> L1/L2/L3 在线嵌入有界更新
  -> 下一次 B/C 召回排序与行动后果预测发生改变
```

关键约束：

1. 正认知压表示现实比预测更强出现，可形成正证据。
2. 负认知压表示预测未被现实验证，可形成负证据。
3. 认知压学习不能对称写入；异常对象是被更新对象，上下文是参照，不可互相同权拉近。
4. 普通共现、多模态连续性可以作为弱对称 evidence，但不能替代认知压定向学习。
5. L1 负责 B 召回准确性，L2 负责时序/因果，L3 负责行动后果。
6. 在线嵌入与白箱显式记忆并联，不能覆盖白箱轨，也不能变成黑箱学生侧模型。
7. 每次向量移动必须可审计：来源、pressure、正/负方向、参与对象、预算、更新幅度、对 B/C 排名贡献都要能回放。

### 33.2 语言学习不是一句话覆盖，而是发展阶梯

`EDUCATION_PROTOCOL.md` 的语言学习阶梯要纳入开放对话底座。教学不是“用户说 X，AP 以后固定回 Y”。它至少应经历：

1. 回声模仿：能复述、能把输入输出当作同 tick / 邻近 tick 事件。
2. 后继预测：从 “A 后面常跟 B” 学到非对称 successor。
3. 多回复聚合：同一输入有多个后继时形成支持峰、竞争、共享片段和不确定感。
4. 过程范式绑定：学习“提问/回答/纠错/确认/请求教师”等过程结构。
5. 关键词组织：词汇成为组织线索，但不是硬门。
6. 语法与风格修 refine：句式、语气、关系感、情绪调制逐渐进入范式。

所以“你好 -> 你也好”不能一次教学后覆盖“你是谁”“这是什么”。正确结果应是：在相似文本状态、相似关系状态、相似情绪状态、相似历史上下文下，那个回复候选的 C* 支持提高；在图片问答或身份询问状态下，由于状态场不同，它不应压过视觉/身份相关后继。

### 33.3 干扰不是敌人，错误提交才是敌人

本地教育协议明确修正过：干扰本身不是坏事。人类学习和 AP 学习都需要在干扰后练习回看、重读、修订和恢复任务。错误不是“被打断”，而是被打断后不回看、不恢复、不检查草稿，直接提交不相关候选。

AP-native 流程：

```text
当前任务形成未闭合 SA / 草稿 SA / 期待 SA
外部惊或违和输入进入状态池
注意力被高 P 外部对象暂时夺走
外部对象被解释或处理后，外源压力下降
未闭合 SA 的 unfinished_pressure 在空 tick / 低外源场景重新进入竞争
注意力回到原任务
DraftGrid 回读当前草稿
继续写、修改或提交
```

禁止路线：

1. 脚本化 `mark_unfinished` 的强度和时刻。
2. 脚本强制选择某个未完成任务。
3. 把恢复任务写成 TODO 表。
4. 在 UI 里伪造“已恢复”而 RuntimeTickEvent 没有能量竞争证据。

### 33.4 范式通道必须消费焦点流，不得消费答案串

`Design_持久化中文对话底座_范式通道重构_v2_20260615.md` 的关键思想是：范式通道坐在 `OnlineEmbeddingStore + RhythmChannel + RelativeRelationStore + FocusBuffer` 上，是薄对齐与方差消费层，不是模板库。

必须落实：

1. `FocusBuffer.all_recent()` 是二维焦点流：外层是跨 tick 顺序，内层是同 tick bundle。
2. 边界来自节奏相位、数量闭合、step_closure、压力释放和连续性掉落，不来自关键词。
3. 草稿面就是游标。DraftGrid 上已经写出的 token/格子决定下一列，而不是另起 successor cursor。
4. 范式 recall 只能提出候选虚能量，行动器每 tick 只能执行竞争赢出的一个动作。
5. 自生成草稿不能抬 support。只有外部观测或带反馈的行动结果能增加范式支持。
6. slot/shared_fragment 要通过跨样本对齐、按列方差、关系邻域重叠自然涌现，不能用“如果低置信就回复某固定句”。

### 33.5 能量本体必须防 dark-room / 沉默退化

`Design_APV3.0能量本体数学模型_20260615.md` 的对抗审计已经指出：如果目标函数只是简单降低压力，系统会学会 defocus、沉默、能量衰减，从而让表面损失变低。这是 dark-room 退化，不符合 AP。

因此 Phase20.7 不能只写“最小化预测误差 L”。应采用修正口径：

```text
L' = 预测错配代价 + 认知债/未闭合代价 - epistemic value
```

含义：

1. 高惊对象不能通过移开注意力来“降低损失”。
2. 沉默不是全局最优，因为未闭合、用户等待、证据缺口和 epistemic value 会继续产生行动压力。
3. 注意力不是 L' 里的可操纵权重，而是降低未来 L' 的执行器。
4. 聚焦、回看、请求教师、观察、写草稿、提交都应按预期未来 `-ΔL'` 获得行动信用。
5. `L'` 初期先做 observe-only 监控，确认它与真实行为改善相关，再让它直接调控大权重。

### 33.6 惊、解释、想象、打断恢复必须是一套能量动力学

不能给“惊”“解释”“想象”“恢复任务”各写一套独立模块。它们应是同一状态池动力学在不同场景下的表现：

1. 惊：外源 `R` 高、预测 `V` 低，正 `P` 抬高。
2. 解释：从意外对象反向召回能预测它的线索，使未来 `V` 更贴近 `R`。
3. 想象：无外源时由 `C*` 和注意力惯性维持虚能量，但 source 必须是 IMAGINED，且不能冒充 PERCEIVED。
4. 打断：外部惊暂时赢注意力竞争。
5. 恢复：惊退去后，未闭合压力重新赢竞争。

这也是“闲时想起没做完的事”“被打断后继续之前任务”“思考中弱外扰不一定打断，强外扰会打断”的统一解释。

### 33.7 画板、坐标轴、几何辅助线是 DraftGrid 与行动器证据，不是装饰

本地 GL 画板技能证明过的方向是：观察图形关系、规划笔画、画辅助标记、再观察、发现错位后局部修订。迁移到 APV3 时应作为 DraftGrid / 视觉行动器 / 画板行动器的一体化证据。

应保留的能力形态：

1. 画板输入作为视觉感受器输入。
2. 笔尖、线段、坐标轴、辅助线、标注位置都作为空间 SA。
3. 作图不是一次生成最终图，而是多 tick 行动序列。
4. 画后再看，错位后局部修订。
5. 几何符号、等长刻痕、平行箭头、角标等是过程标记，帮助后续推理。

不可把画板能力写成 OCR、图像生成、canvas 脚本模板或前端装饰。

### 33.8 技能注册只能复用已证明过程，不能证明自身

`AP_LearnedSkillRegistry_Design_20260603.md` 明确：已验证 AP-learned skill 可以注册为 `action::skill.*`，供高层任务复用；但不能在证明该技能自身时调用它。

因此：

1. 高层应用题可以调用已验证的竖式加减乘除技能。
2. 证明“AP 能学竖式加法”时不能调用竖式加法技能。
3. 技能必须有证据包、适用范围、依赖列表、abstain 条件、trace 展开能力。
4. 技能调用仍是行动候选，必须进入行动竞争，不是后台求解器。
5. 技能结果必须能回灌状态池，形成可观察反馈。

### 33.9 性能优化要服务 AP-native，而不是替代 AP-native

新召回方法有机会显著提升性能，但边界要写清：

1. Zvec / ANN / HNSW / IVF 只能加速 B/C 召回候选 id 检索。
2. 它们不能输出 label、回复、对象名或行动。
3. 召回结果必须回到 AP 的 scoring、source discipline、C* 合并和行动竞争。
4. 在线嵌入应固定预算：每 tick 更新事件数、每事件对象数、晋升 learnable token 数、向量表大小、淘汰策略。
5. 全局 `L'` 不能每 tick 扫全库，只在 active/high-energy/focus/top-k 子集上计算。
6. 视觉 sensory canvas 可增量更新，UI 可降采样，但 RuntimeTickEvent 内的采样和重建证据不能伪造。

如果这些边界守住，新召回方法能把“全库 brute-force 相似度”变成“AP-native 候选检索加速层”，性能会提升；如果边界失守，它会退化成标签数据库或答案缓存。

### 33.10 逻辑可达性判断

从本地文档交叉审查后，AP 设计在逻辑上有机会通向用户想要的图景，但前提是实现真正落到以下闭环：

```text
统一 SA
  -> 双能量状态池
  -> B/C/C* 预测回灌
  -> 认知感受与 L' 压力
  -> 注意力/视焦点/草稿/工具行动竞争
  -> 行动反馈与源分化记忆
  -> 在线嵌入 L1/L2/L3
  -> 下一 tick 更好的召回和行动
```

逻辑理由：

1. 视觉、听觉、文本、行动、情绪、任务、关系都进入同一状态池，具备多模态绑定的共同坐标。
2. B/C/C* 提供从“现在像什么”到“接下来可能怎样”的经验复用机制。
3. 认知压和 `L'` 提供学习信号，使系统能从错配中调整召回、注意力和行动后果预测。
4. DraftGrid 与画板/键鼠行动器让“想法”能变成可检查的空间行为，而不是只说一句话。
5. 未闭合压力、空 tick 和注意力竞争提供持续主体感：不是问一句答一句，而是有正在做、没做完、被打断、恢复的过程。
6. source discipline 防止想象、听说、记忆、现实混淆，保留拟人认知边界。
7. 技能注册让已证明的底层技能能像人类熟练技能一样被高层复用，同时不破坏从零证明边界。

但这不是说当前 Phase20.6 已经做到。当前实现如果仍存在候选回复、固定视焦点、假 tick、假内心画面、教学短句覆盖等问题，就只能说明它还没实现上述闭环。正确下一步不是补 UI，而是 Phase20.7 按能量循环、B/C/C*、在线嵌入、DraftGrid、视焦点和 R_sketch 的顺序重做底座。

---

End of cold-save v1.
