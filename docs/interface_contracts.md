# APV3.0test 接口契约

日期: 2026-06-16

## 目标

APV3.0test 是平行试验场。它复用 APV2.1 中已经稳定的公共接口, 但不继承旧实现里的策略性硬编码。

本文件冻结第一批可复用接口、禁止继承清单、以及 APV3.0 新增桥接层的写入边界。

## 允许复用的公共接口

这些接口可以作为 APV3.0test 的共享底座, 但调用方必须保持语义不变。

| 接口 | 语义 | APV3.0 使用方式 |
|---|---|---|
| `DualEnergyStatePool.read_r_state` | 从状态池生成有界 R-state 读出 | Bn 输入, 不全池扫描 |
| `OnlineEmbeddingStore.learned_similarity` | 学到的语义邻近 | 候选评分特征, 不直接决定行动 |
| `OnlineEmbeddingStore.learned_transition` | 学到的有向后继 | Cn / successor evidence |
| `OnlineEmbeddingStore.pair_evidence` | 白箱证据 | audit trace, 不当策略 |
| `OnlineEmbeddingStore.export_state/import_state` | 在线嵌入持久化 | runtime ontology db 必存 |
| `CognitiveFeelingChannel.derive` | 认知感受生成 | 只消费 trace, 不走关键词门 |
| `RhythmChannel.derive` | 节奏/边界感受 | 范式聚类软先验 |
| `TextActionActuator.step` | 逐 token 执行动作 | 只保留执行面, 选择逻辑外移 |
| `ActionOutcomeMemory.record/snapshot/estimate` | 奖惩-行动后果学习 | 唯一行动后果写入器 |

## APV3.0 新增接口

| 接口 | 阶段 | 写入权限 |
|---|---|---|
| `EnergyObserver.observe` | Phase 1.5 | 只读, 不改行为 |
| `PredictionRuler` | Phase 1.6 | 可替换旧 baseline 逻辑 |
| `ParadigmChannel.observe/recall` | Phase 2 | observe/recall/score 只读 embedding |
| `ParadigmActionBinding` | Phase 3 | 只读聚合, 不写奖惩 |
| `ExplanationConverger` | Phase 4 | 只偏置当 tick 注意力, 不改学习权重 |
| `PerceptPrototypeStore` | Phase 5 | 写稳定 percept token, 不写类别答案 |

## 禁止继承清单

这些旧逻辑可以作为 golden baseline 被观测, 不能作为 APV3.0 新核心。

- 关键词 if-else。
- 答案表。
- 整句动作宏。
- 学生侧 LLM。
- planner 中的数学 token / 字面答案串加权。
- text_actuator 中的 `_branch_alignment` 分支倍率。
- forked exact scorer。
- learned-vector 隐式强权重。
- 自生成草稿增加正向 support。
- 审计库参与 runtime 召回。

## 写入边界

### OnlineEmbeddingStore

- 范式通道的 observe / recall / score 阶段只读。
- slot anchor 写入只能发生在统一学习/反馈阶段。
- self-emission 不增加 `support`。

### ActionOutcomeMemory

- 行动后果奖惩只能写这里。
- `ParadigmActionBinding` 只能读和聚合, 不能新增 `record/update`。

### Persistence

- runtime ontology db 是唯一运行依赖。
- audit db 可删, runtime 不得 import audit db。

## 第一阶段验收

- APV3.0test 包可以独立 import。
- 接口契约对应的测试可以只跑 APV3.0test, 不污染主线。
- 新增观测量默认 observe-only, 不影响旧行为。
