# APV3.0test 对抗性评估与细粒度规划

日期: 2026-06-16
对象:
- `GL_TaskBuilder/docs/Design_持久化中文对话底座_范式通道重构_v2_20260615.md`
- `GL_TaskBuilder/docs/Design_APV3.0能量本体数学模型_20260615.md`
- `APV3.0test/`

## 0. 总判断

当前 v2.1 + v3.0-reviewed 的理论主线是可继续落地的, 不建议推翻。

但实现必须以设计稿后半段的 §12/§13 修正为准, 不能照抄前文旧公式。前文还保留了若干历史表达, 例如:
- `λ_fast = g * habit * (1 - demand_slow)` 的乘积门。
- `τ -> ∞` 等价现有 top-k 的错误端点。
- `L` 而不是 `L′` 的目标函数说法。
- 内源链靠 `V/P/A` 维持的旧表述。

这些都已经在 §12/§13 被纠正。实现标准应是:
- `L′ = Σ w_i^innate * loss(P_i) - β * Σ EV_i`
- 注意力是降 `L′` 的执行器, 不是 `L′` 的内部项。
- `λ_fast` 用加性 logit, 先 observe-only。
- `τ_focus` 惊时收紧, 歧义时扩展召回广度。
- 内源持续主要靠 A-loop, 不是靠负 P。
- Hebbian 学习只是 `-∂L′` 的有界代理, 需要 observable 证伪。

## 1. 找茬式逻辑评估

### 1.1 目标函数是否会退化成沉默或逃避注意力

旧 `L = Σ m_i * loss(P_i)` 有两个退化:
- 系统可以通过不关注高 P 对象来降低 `m_i`, 形成 defocus 逃避。
- 全部能量衰减到 0 时 `L=0`, 沉默会成为最优。

v3.0-reviewed 用 `L′` 修正:
- `w_i^innate` 不含系统自控的注意力项, 不能靠移开焦点篡改显著性。
- `EV_i` 代表未解决认知债, 沉默但认知债未偿时并非最优。

结论: 数学上可自洽, 但 `β` 必须先观测标定。`β` 过高会让系统躁动追逐残差, 过低会退回趋静。

### 1.2 想象是否会冒充外部输入

当前旧代码仍有硬地板:
- `core/state_pool/state_pool.py:196`
- `core/state_pool/state_pool.py:206`
- `core/state_pool/state_pool.py:740`
- `core/state_pool/state_pool.py:826`

这会让 baseline 不自然衰减, 内源 V 有机会长期维持。v3.0 的修正方向正确:
- baseline 初值为 0。
- begin_tick 中随 `real_decay` 衰减。
- 外部输入时按对象更新 ruler。
- live 外部对象可让 `V` 达到 `R`, 纯内源对象不能。

结论: 这是 Phase 1.5 前必须单独验证的 blocker。否则“想象不越界”只是文档成立。

### 1.3 注意力是否会和惊/解释机制互相矛盾

旧文中有“惊时 broaden”的表达, 但 `softmax(s/τ)` 的真实数学是:
- `τ -> 0`: 更接近 argmax/top-k。
- `τ -> ∞`: 趋向均匀喷洒。

因此惊本身应收紧焦点, 把注意力铆在高 P 对象上; 同时解释阶段可以扩大候选召回广度。这是两个旋钮:
- `τ_focus`: 焦点温度。
- `recall_breadth`: 解释候选广度。

结论: 逻辑可行, 但实现时禁止把 `resource_multiplier` 当作“每 SA 温度”。它最多是总注意力预算 `B_attn` 的标量。

### 1.4 快慢系统仲裁是否会压死快系统

乘积门 `g * habit * (1 - demand_slow)` 会结构性偏低, 单个强熟悉信号无法独立承载快反应。

修正为:

```text
lambda_fast = sigmoid(w_g*g + w_h*habit - w_d*demand_slow - b)
```

并且先 observe-only, 只记录 `lambda_fast` 与后续 `ΔL′` 的相关性, 暂不改变路由。

结论: 加性 logit 可行。落地顺序必须保守, 否则会在自由对话里造成新一轮行为漂移。

### 1.5 范式通道是否会自证循环

最大风险不是 DP 或熵公式, 而是写入边界。

必须保持:
- observe / recall / score 阶段只读 `OnlineEmbeddingStore`。
- slot anchor 写入只发生在统一学习/反馈阶段。
- self-emission 不增加 `support`。
- 自生成草稿不提高 `conf`。

结论: 设计已补, 但实现时要把这个做成入口约束和测试, 不能只靠注释。

### 1.6 successor_virtuals 是否会变成新 policy

它作为 Cn′ 的虚能量物化是合理的, 但有滑坡风险。

必须保留三条硬约束:
- 来源可追溯: 显式 transition / FocusSuccessorBias / active ParadigmSA slot_type 近邻。
- 数量有界: top-k, 随疲劳和未降压失败衰减。
- 强直接后继已成立时, successor_virtuals 只能陪跑, 不能改写赢家。

结论: 可保留, 但它必须走单一 scorer 和行动竞争。

### 1.7 持久化是否会破坏内存态等价性

核心要求不是“把 JSON 换 SQLite”, 而是:
- AP-native 运行本体能等价重载。
- 白箱审计可删, 不影响 runtime。
- sqlite 只保存运行必需本体和小型可重建索引。
- 10G 上限只应优先回收审计和低价值可重建材料, 不能误删范式、奖惩、基础技能。

旧 `sqlite_store.py` 已有 10G budget / forgetting / runtime projection 的雏形, 但其 docstring 仍混有“white-box snapshots and derived audit payloads”的历史语义。APV3.0test 中必须显式拆成:
- runtime ontology db
- audit trace db

结论: sqlite 继续可用, 但要在 APV3.0test 内加 wrapper/contract, 不直接把旧库语义原样继承。

### 1.8 数学硬编码残留是否会污染 APV3.0

当前实现中仍有已知残留:
- `memory/store/memory_store.py:93` 的 `learned_vector_candidate_weight=4.5`
- `memory/store/memory_store.py:128` 的 `_label_overlap_rank_decay=0.72`
- `memory/store/memory_store.py:3208` 的 forked exact scorer
- `core/action/text_actuator.py:1248` 的 `_branch_alignment`
- `core/action/planner.py:3494` 的 `math_process_tokens`
- `core/action/planner.py:3699` / `3701` 的字面答案串加权

结论: 这些不能直接搬进 APV3.0test 的“新核心”。可以暂时作为 legacy baseline 被 golden-lock, 但不能作为最终 APV3.0 策略。

## 2. 是否能实现目标

理论上可以实现用户目标, 条件是逐阶段证明以下链路:

1. 当前输入形成 SA, 进入 R/V/P/A/F 状态池。
2. Bn 只负责“当前场像过去哪些经验”。
3. Cn 只沿显式后继边读“这个 B 之后通常发生什么”。
4. ParadigmSA 作为普通 SA 进入竞争, 不直接输出答案。
5. 行动器逐 token 执行赢家, 不走整句宏。
6. 奖惩只改后续竞争倾向, 不直接删词/写规则。
7. 持久化重载后 Bn/Cn/ParadigmSA/OnlineEmbeddingStore/ActionOutcomeMemory 等价。
8. 实时学习在当前持久化环境下能形成新 support / transition / outcome bias。

如果任意一条失败, 自由中文对话底座会退化成:
- 关键词规则系统。
- 自回环草稿系统。
- 热窗短记忆系统。
- 或者只会跑 harness 的伪能力系统。

因此实现顺序不能从 Fresh300 开始, 必须从最小可证伪门开始。

## 3. APV3.0test 细粒度落地规划

### Phase 0.0: 冻结边界与目录

产物:
- `APV3.0test/docs/interface_contracts.md`
- `APV3.0test/config/apv3_config.py`
- `APV3.0test/runtime/bootstrap.py`

动作:
- 列出允许复用的公共接口:
  - `read_r_state`
  - `learned_similarity`
  - `learned_transition`
  - `pair_evidence`
  - `export_state/import_state`
  - `CognitiveFeelingChannel.derive`
  - `RhythmChannel.derive`
  - `TextActionActuator.step`
  - `ActionOutcomeMemory.snapshot/record`
- 列出禁止继承的 legacy 逻辑:
  - 关键词 if-else
  - 答案表
  - 整句宏
  - planner 字面数学答案加权
  - text_actuator `_branch_alignment`
  - scorer fork

验收:
- 文档列清楚“能搬 / 不能搬 / 暂时只作 legacy baseline”的清单。

### Phase 0.1: 配置收口, 不改行为

产物:
- `APV3.0test/config/energy_config.py`
- `APV3.0test/config/recall_config.py`

动作:
- 把现有魔数搬到具名 config。
- 初值等于现值。
- 不改变任何 score / output。

验收:
- 同一输入下旧实现与 config 化实现 score breakdown 完全一致或 round4 一致。

### Phase 0.2: 单一 scorer golden-lock

产物:
- `APV3.0test/tests/test_scorer_golden_lock.py`
- `APV3.0test/data/golden/scorer_cases.jsonl`

动作:
- 从当前 runtime scorer 和 audit exact scorer 抽取 per-candidate breakdown。
- 建单一 scorer 纯函数。
- runtime/audit 差异只通过 preset 表达。

验收:
- runtime preset 复现旧 runtime。
- audit preset 复现旧 audit。
- 不允许 `posting=0` 这类伪 preset 魔数。

### Phase 0.3: sqlite 分层契约

产物:
- `APV3.0test/runtime/sqlite_runtime_store.py`
- `APV3.0test/runtime/sqlite_audit_store.py`
- `APV3.0test/docs/persistence_contract.md`

动作:
- runtime db 存:
  - OnlineEmbeddingStore state
  - state snapshots / transitions
  - ParadigmSA
  - PerceptPrototype
  - ActionOutcomeMemory
  - necessary indexes
- audit db 存:
  - score breakdown
  - DP intermediate states
  - explanation pass trace
  - recent white-box ticks
- 默认 10G 上限。
- audit 先淘汰。
- runtime 只淘汰可重建、低权重、非范式核心材料。

验收:
- 删除 audit db 后 runtime 仍能启动。
- 达到预算时不会删除范式核心、基础数学表、奖惩核心。

### Phase 1.0: 内存态 vs 持久化态 parity

产物:
- `APV3.0test/tests/test_memory_persistence_parity.py`

动作:
- 同一批输入跑内存态。
- 导出 sqlite。
- 重启恢复。
- 比较:
  - Bn top-k
  - Cn 后继
  - learned vectors
  - transitions
  - action outcome memory
  - draft token
  - commit 清空

验收:
- top-k 允许近似一致, 但后继证据链必须一致。
- 对旧训练句, 输出行为等价。

### Phase 1.5: APV3.0 能量 observe-only

产物:
- `APV3.0test/runtime/energy_observer.py`
- `APV3.0test/tests/test_energy_observer.py`

动作:
- 计算 `L′`, 不进控制路径。
- 记录:
  - `P`
  - `EV`
  - `target_cap`
  - `lambda_fast`
  - `tau_focus`
  - `recall_breadth`
  - Hebbian step 与 `-∂L′` 有限差分 cosine

验收:
- 稳定教学输入下 `L′` 趋势下降。
- 意外输入下 `L′` 尖峰后可回落。
- 自发空 tick 下 `target_cap` 衰减趋近 0。
- Hebbian 对齐 cosine 长期非负; 若长期为负, 不能把 MPE 当已证。

### Phase 1.6: baseline/ruler 修正

产物:
- `APV3.0test/tests/test_prediction_ruler_decay.py`

动作:
- 去掉硬地板和 `or 1.0` 语义。
- baseline 随 real_decay 衰减。
- live 外部对象使用对象级 ruler。

验收:
- 喂一次外部输入后跑 N 个空 tick, target_cap 单调趋近 0。
- 当前 live 外部对象可让 `V` 接近 `R`, 不产生永久 P 地板。

### Phase 2.0: 范式通道最小三阶

产物:
- `APV3.0test/runtime/paradigm_channel.py`
- `APV3.0test/tests/test_paradigm_three_stage.py`

动作:
- echo imitation。
- successor prediction。
- multi-reply aggregation。

验收:
- teacher-off。
- 输出 token 来源可回溯。
- 无目标串喂字。
- 无关键词路由。
- self-emission 不抬 support。

### Phase 2.1: Rhythm signature IO 无关性

产物:
- `APV3.0test/tests/test_rhythm_signature_io_invariance.py`

动作:
- 同 episode 用逐字、逐句、整段输入三种切块跑。
- 比较 `signature_for`。

验收:
- signature 稳定。
- 不读内容字符串 / turn flag / chunk 边界。

### Phase 2.2: 桶索引剪枝

产物:
- `APV3.0test/tests/test_paradigm_bucket_pruning.py`

动作:
- rhythm_signature 只作一级桶。
- quantum_prior / head_anchor / relation skeleton 只作候选检索索引。
- DP 只对 top-K 小候选池做。

验收:
- 不发生全桶 pairwise DP。
- 重复字/长句/多义结构不爆炸。

### Phase 3.0: action outcome 接入范式视图

产物:
- `APV3.0test/runtime/paradigm_action_view.py`
- `APV3.0test/tests/test_action_outcome_single_writer.py`

动作:
- `ActionOutcomeMemory` 是唯一写入学习器。
- `ParadigmActionBinding` 只读聚合。

验收:
- grep 不存在第二套 record/update 策略写入。
- 奖惩改变 drive_bias, 不直接改文本。

### Phase 4.0: explanation convergence

产物:
- `APV3.0test/runtime/explanation_converger.py`
- `APV3.0test/tests/test_surprise_explanation.py`

动作:
- latch `residual_P = R - V_pre`。
- 收束 pass 只影响当 tick 注意力偏置。
- 学习权重读收束前 P。

验收:
- 意外输入先升 P, 后因解释下降。
- 无解释时保留 strange/residual, 驱动 evidence-seeking。
- 不污染学习权重。

### Phase 5.0: percept prototype 冷启动

产物:
- `APV3.0test/runtime/percept_prototype_store.py`
- `APV3.0test/tests/test_percept_prototype_bootstrap.py`

动作:
- 非文本 SA 通过 numeric_features 形成稳定 percept token。
- previous_object_anchor_id 参与连续性。
- spawn 由压力驱动, 阈值 tuner-owned。

验收:
- 同一物体多位置稳定归一。
- 不同对象不过度合并。
- 原型数有界。
- 未过四子门前不宣称跨模态泛化。

### Phase 6.0: 自由中文底座小样本

产物:
- `APV3.0test/tests/test_open_chinese_dialogue_smoke.py`

动作:
- 只在前面所有门过后跑。
- 用小样本测试:
  - 你好
  - 你是谁
  - 简单纠错教学
  - 重复尾部修订
  - 简单数学
  - 多轮保留

验收:
- 不出现 `你好你` 自固化。
- 草稿能提交并清空。
- 新教学能进入持久化。
- 重启后仍会。

## 4. 第一批实际执行建议

下一步不要直接写范式 DP, 也不要直接跑 Fresh300。

第一批最小实现应是:

1. 写 `interface_contracts.md`。
2. 写 `persistence_contract.md`。
3. 写 `energy_observer` 的数据结构草案。
4. 写 `test_prediction_ruler_decay.py` 的失败测试。
5. 写 `test_memory_persistence_parity.py` 的最小骨架。

原因:
- 这五项能最快暴露旧代码和新理论的真实裂缝。
- 它们不需要先重写完整 runtime。
- 它们能保证之后每一步都按 APV3.0 主线前进, 不会又回到补丁式硬编码。

