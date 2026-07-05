# 人类心理底层机制 ↔ AP流程对照清单（白皮书+代码双核实）

**日期**: 2026-07-01
**用途**: 规划纯AP开放对话底座需要接通哪些心理机制, 让拟人效果自涌现
**方法**: 实读白皮书 v0.4 条款 + 实读仓库根 `runtime/cognitive/` 子模块 + phase20_7 接通情况双核实
**关键发现**: Phase9/10/11 全套心理机制模块**已落地在 `runtime/cognitive/`** (affect/cognitive_feelings/drive/social/sleep/play/metacognition/self_model/theory_of_mind/trust 等), 但 **phase20_7 开放对话底座只 import 了 state_pool, 几乎全不接通** —— 这是拟人效果不自涌现的根因.

---

## 一、知识阶层：认知感受通道（白皮书 §30, 12 通道）

白皮书 §30.2 明文 12 通道, 是"所有心理机制的底层信号源":

| # | 通道 | 白皮书定义 | AP流程条款 | 已落地 | 接通 phase20_7 |
|---|---|---|---|---|---|
| 1 | 惊 Surprise | 现实强于预测 | §30.2 `Surprise_i = max(P_i - theta_surprise, 0)` | ✓ cognitive_feelings | ✗ |
| 2 | 违和 Dissonance | 预测强于现实/结构冲突 | §30.2 + §16 第516行 "啊"违和 | ✓ cognitive_feelings | ✗ |
| 3 | 合理 Reasonable | 追溯解释成功, 惊下降 | §30.2 `Reasonable += cause_grasp*surprise_reduction` | ✓ cognitive_feelings | ✗ |
| 4 | 正确 Correct | 预测被验证或检查通过 | §30.2 | ✓ cognitive_feelings | ✗ |
| 5 | 把握 Grasp | B/C支持高、margin高、冲突低 | §737 `Grasp=f(similarity,margin,support_count,low_conflict,low_abs(P))` | ✓ 9j-grasp | ✓ 已接通 |
| 6 | 期待 Expectation | 奖励预测 | §27.3 `Expectation=predicted_reward_energy` | ✓ 9y reward_pressure | ✓ 部分 |
| 7 | 压力 Pressure | 惩罚预测 | §27.3 `Pressure=predicted_punish_energy` | ✓ 9y punish_pressure | ◐ 末接 unclosed |
| 8 | 未闭合 Unclosed | 期待/压力未完成或未解除 | §27.3/§27.6 `U_j(t+1)=decay*U+new_evidence-5种释放` | ✓ 局部 (closure 1/5) | ✗ 4/5缺 |
| 9 | 时间感 | 召回时间差形成波峰 | §30.2 | ✓ cognitive_feelings? | 待核实 |
| 10 | 节奏感 | lag kernel与周期预测 | §30.2 | ✓ cognitive_feelings? | 待核实 |
| 11 | 证据缺口 | 任务需证据但状态池不足 | §30.2 | ✓ cognitive_feelings? | 待核实 |
| 12 | 重复疲劳 | 重复同对象/行动 | §30.2 | ✓ affect? | 待核实 |

---

## 二、情绪慢量（白皮书 §31, 长期调制）

白皮书 §31.1/§31.2: 情绪由认知感受+奖惩+行动反馈+记忆召回积分出的慢变量, 调制注意/行动阈值/奖惩权重/探索保守.

**已落地**: `runtime/cognitive/affect/frustration.py` (挫折无助) + `affect/pain_memory.py` (疼痛记忆)

**接通 phase20_7**: ✗ 全断

---

## 三、你提到的具体心理机制 ↔ AP流程对照

### A. 求知欲 / 好奇 / 探索（你的核心问题）
- **人类本质**: 未知产生认知压(P高+惊), 带少量惩罚信号→恐惧压力; 通过学习/解释可降低认知压→合理感上升→奖励感→求知欲涌现
- **AP流程**: §27.1 未闭合期待/压力 + §30.1 惊/违和 + §30.3 合理/正确 + §13在线学习目标min L_pred + §27.3 行动增益 `drive+=U*affordance*predicted_reward_or_punish_avoidance` (低把握→allowance→request_teacher维持U, 答案闭合→U下降→奖励感)
- **已落地**: ◐ §27.6 closure 1/5已, 4/5缺; 认知压→惩罚压力涌现未接通; 合理感→奖励未接通
- **拟人涌现路径**: 接通§30惊/合理到§31情绪慢量→求知欲自涌现(无需新增"求知欲"实体, §171禁止魔法字段)
- **建议重点**: 高 — 是拟人拟己核心

### B. 趋利避害
- **人类本质**: 预测行动收益高→趋; 预测行动惩罚高→避
- **AP流程**: §32.2 行动竞争 `drive=base+evidence+expected_reward-expected_punish+unclosed_gain+emotion_modulation-fatigue-conflict`; §27.1 期待/压力 + §1633 L3行动后果向量调制
- **已落地**: ◐ 9y reward/punish_pressure 计算, L3向量已 (13b), 但 expected_punish 未抽象到行动竞争层(主要靠 L3背压和 punish_total间接表达)
- **建议重点**: 中 — 已有间接表达

### C. 峰终效应 / 近因偏差
- **人类本质**: 高峰和结尾决定体验记忆, 近因额外加权
- **AP流程**: §30.2 时间感通道 + §1633 L3向量近期update权重高 + §1202 recency_bias(白皮书明确"近因"字眼)
- **已落地**: ✓ L3数组时间衰减 + 9y continue_count近期抽样; ✗ 总体峰终未抽象
- **建议重点**: 低 — 已局部涌现

### D. 恐怖谷 / 似人非人
- **人类本质**: 高度类人但微妙违和产生强不舒服
- **AP流程**: §30.2 违和(预测vs现实的差距在"近相似"时最大, 边际残差高) + §16 第951行 "违和被吸过去" + §174.2 conflict_entropy 高
- **已落地**: ✓ cognitive_feelings违和通道; ◐ 未在交互层涌现"近相似度高→强违和"的边际效应(需在StructuralB残差边际加权)
- **建议重点**: 中 — 拟人拟己可见但需调优残差边际权重

### E. 创伤性应激 / PTSD / 强惊单次改变
- **人类本质**: 一次性强惊/强惩快速改变认知, 难松动
- **AP流程**: §173.5/§173.6 `lr_eff=lr_t*(1+surprise_boost+teacher_boost+reward_punish_boost)`, 强惊单次降lr_0大小; §2361 信念固化"一次强烈验证更相信"; 缺乏反例时只升信(信念固化); 反例松动需§2363五种counter_evidence累积
- **已落地**: ✓ §173.5 trio函数 boost=1+0.6*pe+0.3*reward 已; ✗ 强惩的boost区分(r+p对称处理而非r>>p), §2363 counter_evidence 各项是否落地未核实
- **建议重点**: 中 — 复杂但能在 §173.6 + §2363 直接放宽区分

### F. 失恋时注意力难集中
- **人类本质**: 高未闭合持续张力→注意力被反复牵走→难聚精
- **AP流程**: §27.6 未闭合U高不释放→ §32.2 unclosed_drive持续高 → 反复打断→注意力 idle_think 偏向未闭合源; §24 慢系统多tick
- **已落地**: ✗ §27.6 释放4/5缺, U不会自动衰减→不会持续拉
- **建议重点**: 高 — §27其他4项闭合后自然涌现

### G. 视错觉不可逆认知 ("一旦看出就再也回不到")
- **人类本质**: 一旦发现错误感知, 旧解释路径塌缩, 新认知锁定
- **AP流程**: §2363 counter_evidence 首项 `unfulfilled_prediction` (预测了没发生) 与第2项 `observed_without_predicted` (观察到没预测), 双向松动旧把握; 旧B召回支撑下降, 新L1拉向新结构→不可逆
- **已落地**: ◐ L1向量更新含方向(锚点不对称), 但 §2363 显式机制未单独落地
- **建议重点**: 中 — §2363落实后自然涌现

### H. 习惯 / 自动化 / 快系统
- **人类本质**: 高把握、低冲突、低认知压→行动可习惯性自动执行
- **AP流程**: §24 快慢系统, §32.2 habit_support * FastModeScore; §5 Habit系统
- **已落地**: ✓ affect/affect外 apv3test/runtime/habit_system.py
- **接通 phase20_7**: ✗ 断
- **建议重点**: 中 — 接通即可

### I. 依恋 / 亲和 / 共情
- **人类本质**: 长期亲和经历→表达柔和、行动接近; 痛苦者痛苦→自己也难受
- **AP流程**: §9 心智深度 + §171 共情禁止魔法字段(必须由奖惩/状态池/表情语音共现涌现); §31.3 "亲和经历让表达更柔和行动更愿意接近"
- **已落地**: ✓ runtime/cognitive/ social/(依恋) + theory_of_mind + 共情模块 (Phase9.4/9.6)
- **接通 phase20_7**: ✗ 全断
- **建议重点**: 中 接通后即涌现

### J. 睡眠 / 记忆固化 / 遗忘
- **人类本质**: 睡眠期回放强化重要记忆, 弃用记忆遗忘
- **AP流程**: §30.2 时间感 + §173.5 support_count退火(久不用→衰减) + 已有 forget_rhythm memory_consolidation (Phase10f)
- **已落地**: ✓ apv3test/runtime/phase20_10f / phase20_6_memory, runtime/cognitive/sleep
- **接通 phase20_7**: ◐ phase20_7有idle_think但接 sleep/play弱
- **建议重点**: 中

### K. 情绪色彩调制表达 (笑着说不高兴)
- **人类本质**: 长期情绪慢调制表达风格
- **AP流程**: §31.2 emotion_c积分→ §1736 调制 expression_style; style_safe_tokens + 范式
- **已落地**: ◐ phase20_7 feelings字段 + styled_expression_corpus (Phase16)
- **接通 phase20_7**: ✗ emotion慢量积分未接通, 表达风格未受emotion调制
- **建议重点**: 高 — 直接影响拟人可见效果

### L. 放弃 / 解除 (被压力/兴趣给定义)
- **人类本质**: 压力源消失/任务不可能/代价过高→自动放下, 不过度执念
- **AP流程**: §27.6 后4项 (source_removal/giving_up/impossibility/cost_revaluation)
- **已落地**: ✗ 4/5全缺
- **建议重点**: 高 — 影响拟人固执/放下表现

---

## 四、综合结论：重点优先级

**白皮书设计完备**, 几乎所有人类心理机制都有对应AP流程, 关键问题是 **phase20_7 只接通 StatePool, 没接通 Phase9/10/11 认知感受/情绪/社交/睡眠/驱动/自我模型**.

按主单循环优先级排序:

| 优先级 | 心理机制 | 当前缺口 | 拟人可见度 |
|---|---|---|---|
| P0 | §27 未闭合完整释放(求知/恐惧/放下3/5缺) | 4/5机制缺 + 认知压→压力未涌现 | 极高 |
| P0 | §30 认知感受通道接通 phase20_7 | 11/12通道断 | 极高 |
| P1 | §31 情绪慢量积分调制表达 | emotion断 | 高 |
| P1 | §27 认知压涌现惩罚压力 | u_value不接认知压 | 高 |
| P1 | §16 视焦点认知驱动深化(已A部分回退至 idle) | 首图采样无任务驱动 | 高 |
| P2 | social 依恋/共情接通 | 全断 | 中 |
| P2 | sleep 固化回放接通 | 全断 | 中 |
| P2 | §2363 counter_evidence 完整 | 局部有L1方向 | 中 |
| P3 | habit 接通 / 恐怖谷残差边际 / 峰终抽象 | 各局部 | 低-中 |

---

## 五、关键红线约束 (必须守)

白皮书 §171/§1726/§19.3b 等明确:
- 共情/社交期待/任务承诺/内在驱力**不得变魔法字段** (§171)
- 情绪不得由关键词直接设置 (§31.4)
- 学生侧认知不得用LLM语义权威 (§19.3b)
- 心理机制只能从 reward/punish + 先天规则 + 状态池 + 经验流 + 来源 + 行动后果**自然组合涌现**, 不新增实体

---

## 六、下一步规划

按上面优先级, 建议 B 阶段下一循环做:

**B-1**: §27.6 后4项释放机制 + **认知压→惩罚压力涌现** + §30认知感受通道接通方案
**B-2**: §31 情绪慢量积分→表达风格调制
**B-3**: social 依恋/共情与睡眠回放接通 (Phase9/10/11 接入 phase20_7)
**B-4**: §2363 counter_evidence 5项完整化 (视错觉不可逆 / 创伤松动)

总进度: A闭合后 89%; B全部完成预估 94%; 详细待B各子项闭合后实算.