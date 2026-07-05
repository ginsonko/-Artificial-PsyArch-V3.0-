# APV3 验收与对抗性审核 — 新线程交接提示词

> **用途**: 把本文件完整喂给一个全新无上下文的 codex/AI 线程，让它先彻底理解 AP 是什么、再了解 APV3 现状、再对最新成果与整个 APV3 底座做验收和对抗性审核。
> **生成日期**: 2026-06-30
> **生成者**: 上一个工作线程（完成 Phase20.13b/13c/14 及既存失败清理）

---

## 〇、你的任务定位

你是一个**全新的独立审核线程**。你的任务不是继续开发，而是**验收和对抗性审核**上一个工作线程的成果，并检查整个 APV3 开放对话底座是否符合白皮书、是否有硬编码或隐患、是否可更泛化优雅、是否更符合 AP 哲学。

你必须做到：
1. **先彻底理解 AP 是什么**（读白皮书，不要只信本提示词的总结）。
2. **再了解 APV3 现状**（读代码、测试、报告，实跑验证）。
3. **再对最新成果做验收和对抗性审核**（Phase20.13b/13c/14 + 既存失败清理）。
4. **也要对整个 APV3 底座做检查**（看是否有不符合白皮书、不合适、可优化、可提升泛化性的地方）。
5. **每一步都要实际检查效果，不要口头假设**。实跑、实读、实查。

你不是"快速过一遍"，而是**最高等级质量**的严谨审核。发现问题要明确指出文件:行号、违反了哪条白皮书、建议怎么改。不要含糊。

---

## 第一部分：理解 AP 是什么

### 1.1 AP 的核心定义

AP（Artificial PsyArch，人工心智架构）是一个**白箱认知闭环 runtime**，研究学派是**内生认知主义（Endogenous Cognitivism）**。核心论点：认知能力可从内部信息流结构涌现，而非只依赖神经网络参数训练或手写符号规则。

AP **不是**：Transformer、纯神经网络、纯符号专家系统、LLM 包装、纯 if-else 规则引擎、已完成的 AGI。
AP **是**：围绕状态池、注意力、记忆、认知感受、行动选择、奖惩反馈的白箱认知 runtime。每个 tick（最小认知节拍）走统一的认知闭环：感知输入 → 状态池匹配 → 经验流召回 → 草稿格提案 → 动作竞争选择 → 提交回复 → 老师反馈 → 更新向量。

九大模块：感受器、状态池、数据库、注意力、先天编码、认知感受通道、情绪通道、行动器与驱动力管理、自适应调参器。

### 1.2 白皮书阅读顺序（已核实路径，请按此读）

仓库根目录：`H:\AP原型实验第二期\APV2.1版本原型测试`（APV3.0test 的上一级）。白皮书分布在此根目录与根的 `docs/` 下。**请实际打开读，不要只看本提示词的摘要。**

**第一优先（理解项目身份，英文）**：
1. `README.md`（根，最完整主入口）
2. `APV21_FIRST_REVIEWER_GUIDE.md`（根，首次评审 15 分钟路径，含大量证据 HTML 链接）
3. `APV21_FULL_PROJECT_GUIDE_FOR_AI.md`（根，写给 AI 评审者的深度解释）

**第二优先（理解理论最高基线，中文，APV2.1 重建口径）**：
4. `00_先看这里_APV2.1阅读入口_20260526.md`（根，阅读入口，给出推荐顺序）
5. `APV2.1_终极理论纠偏与最高设计目标_20260526.md`（根，**最高哲学基线**，任何冲突时回拉方向用此）
6. `APV2.1_详细设计文档_20260526.md`（根，工程蓝图）
7. `APV2.1_在线学习嵌入详细设计方案_20260526.md`（根，在线学习嵌入专项，含"能量驱动优先"修订口径）

**第三优先（设计哲学源头）**：
8. `AP图景预期书.txt`（根，**非 md 但极重要**，AP 设计的"初心"文档，状态池实能量/虚能量/认知压等图景的最早成文源头）

**第四优先（论文/白皮书形态）**：
9. `docs/APV21_Paper_CombinedMainDraft_v0_7_20260606.md`（docs，论文合订主稿 v0.7，~167KB，最接近完整白皮书的 md 形态）
10. `docs/APV21_Paper_ReproductionGuide_20260605.md`（docs，复现指南）

**第五优先（教育/学习边界，审核 Phase20.13c/14 必读）**：
11. `EDUCATION_PROTOCOL.md`（根，英文正式版，**语言学习阶梯 6 阶段、scaffold 褪除、场景学成要求、禁止捷径**）
12. `docs/education_protocol_guide_zh_20260610.md`（docs，中文导读）
13. `docs/APV21_GL_Learning_Protocol_Formal_zh_20260610.md`（docs，正式中文协议）

**第六优先（工程实现与文档地图）**：
14. `docs/TECHNICAL_IMPLEMENTATION_GUIDE.md`（docs，目录结构与模块职责）
15. `docs/INDEX.md`（docs，**含 phase 0-7 实施顺序**）
16. `docs/APV2.1_现状缺口与实施总规划_20260526.md`（docs，分阶段路线图）

**第七优先（可直接用的 LLM 启动提示词，可作为本提示词的补充）**：
17. `APV2.1_新仓库启动用LLM总提示词_20260526.md`（根，注意拼写是"新仓库启动用"不是"新仓启动运用"）

**应排除（与 AP 无关，同一作者的另一物理理论项目）**：
- `ABC_recent_month_review_20260627.md`、`ABC_theory_review_20260626.md`（FCWFT 物理理论，不是 AP）

### 1.3 关键提示
- "人工心智架构：一种面向拟人持续认知闭环…"是 **PDF**（根目录，7.46MB），不是 md。md 世界里最接近的是 `docs/APV21_Paper_CombinedMainDraft_v0_7`。
- 白皮书里有大量 §编号条款（如 §35.4、§132、§173.3、§173.5、§1742、§33.1、§19.3b 等）。**请在白皮书原文里核实这些编号的出处与语义**，不要只信本提示词转述。本提示词第二部分会列出已知约束的语义，但**以白皮书原文为准**。

---

## 第二部分：APV3 现状与工作环境

### 2.1 工作目录（绝对红线）

**你的工作目录固定为**：`H:\AP原型实验第二期\APV2.1版本原型测试\APV3.0test`

- **所有 APV3 测试必须在此目录下跑**（`cd` 到此处再 `python -m pytest`）。在上一层仓库根跑会导致路径层级错误、import 失败。
- APV3.0test 是一个**并行试验场**，不是把整个 APV2 仓库复制一遍。APV3 专属实现在 `apv3test/` 包里；顶层 `runtime/` 是**共享认知底座**（state_pool 等在此），APV3 通过 `from runtime.cognitive.state_pool.state_pool import ...` 跨包引用。

### 2.2 代码结构（已核实）

```
APV3.0test/
├── apv3test/                      # APV3 专属包（核心实现）
│   ├── chat.py                    # CLI 会话入口
│   ├── web_chat.py                # Web 工作台入口（http.server）
│   ├── runtime/                   # APV3 专属运行时（~60 模块）
│   │   ├── phase20_7/             # 主运行时子包（runtime.py / experience_log.py / models.py 等 11 模块）
│   │   ├── phase20_open_dialogue.py   # 开放对话底座核心编排
│   │   ├── sqlite_runtime_store.py    # 运行库本体投影
│   │   ├── sqlite_audit_store.py      # 审计库（与运行库分离）
│   │   ├── draft_grid.py              # 草稿格
│   │   └── ... (action_competition/cooccurrence/curriculum 等)
│   └── web/static/                # phase20_6_workbench.{html,css,js} / phase20_7_workbench.* / app.js
├── runtime/                       # 顶层共享认知底座（state_pool 在这里！不在 apv3test/runtime/）
│   └── cognitive/state_pool/      # StatePool / attention_gain_ledger / target_cap / v_double_control
├── tests/                         # ~165 个测试（扁平，按 phase 命名）
├── docs/                          # 83 个 FinalReport_Phase20_*.md + 本交接提示词
├── config/ scripts/ data/ state/ reports/
└── README.md
```

**关键纠正（容易看错）**：`state_pool` **不在** `apv3test/runtime/` 下，而在顶层 `runtime/cognitive/state_pool/`。看到"apv3test/runtime/state_pool"的描述是错的。

### 2.3 持久化双库分离原则

- 运行库 `sqlite_runtime_store.py`（runtime essentials：状态、本体投影、向量）
- 审计库 `sqlite_audit_store.py`（audit 事件，可与运行库独立删除）
- 契约测试：`tests/test_sqlite_store_contract.py`
- 验收要点：运行库不依赖审计库存在。

### 2.4 当前进度（已完成的阶段）

**phase 1-19**：AP 各项能力建设（感受器/范式/对话/课程/视觉/听觉/记忆/认知感受/情绪/元认知/叙事等），详见 `tests/test_phase{1..19}_*.py` 与 `docs/FinalReport_Phase20_*` 早期报告。

**phase 20（开放对话底座重建，当前主线，已完成的子阶段）**：
| 子阶段 | 内容 | 状态 |
|---|---|---|
| 20.0 | 开放对话基础 | ✓ |
| 20.1 | web 教学范式 | ✓ |
| 20.2_3 | 共现教学 + 记忆包 | ✓ |
| 20.4 | 工作台修复 | ✓ |
| 20.5a | 运行时工作台 | ✓ |
| 20.6 | 历史包画布 + stage0 边界 | ✓ |
| 20.7 | stage0-8（9 个 stage：边界/文本闭环/经验记忆索引/结构BCC*/未闭环idle/视觉重建/音频TTS/API工作台/发布demo）| ✓ |
| 20.8 | 闭合 + 8a-8r（18 个：经验流/统一召回/结构流/草稿格/动作竞争等）| ✓ |
| 20.9 | 9a-9z（25 个：六阶段学习协议投影/学习环carryover/idle review/self-test/动作竞争/经验调谐器等）| ✓ |
| 20.10a-10m | 学习阶段运行时进展 / 学习对象生命周期 / 长间隔冷重测 / 冷重测泛化置信 / 记忆巩固遗忘复习节奏 等 | ✓ |
| 20.11 | L1 在线嵌入 | ✓ |
| 20.12/12b/12c | L2 时间边嵌入 / L2-C 反向 / 文本输入不借视觉签名 | ✓ |
| 20.13a | 支持退火（有报告 `docs/FinalReport_Phase20_13a_SupportAnnealing`，**无对应测试**——请审核这是否是缺口）| ✓(?) |
| **20.13b** | **L3 动作-后果在线嵌入**（本会话前完成，本会话做 SQL 参数化修复）| ✓ |
| **20.13c** | **语言学习阶梯 6 阶投影**（本会话前完成）| ✓ |
| **20.14** | **场景学成判据纯派生投影**（本会话完成）| ✓ |
| **PreexistFailures** | **4 既存失败独立清理**（本会话完成）| ✓ |
| 20.21 | object_centric_looking（已有测试）| ? 请核实 |

**全量回归当前状态**：`890 passed / 0 failed`（2026-06-30 实跑，单进程 ~25min，exit 0）。底座全绿。

**未做 / 下一步候选（上一个工作线程预告，尚未授权启动）**：
1. 课程编排读取 `scene_learned_projection`（据 confidence + dominant_blocking_stage 决定加 scaffold 还是准备冷重测）
2. 更多拟人化语言效果（teacher_off + cold_retest 条件下"我学会了"的连贯语言风格，仍走 AP 主流）

### 2.5 总规划与"哪些没做"

phase 0-7 实施顺序见 `docs/INDEX.md`。phase 20 是开放对话底座的完整重建。**你需要审核的是：phase 20 整体是否符合白皮书、是否有遗漏或越界。** 特别关注：
- 13a 有报告无测试，是否是质量缺口？
- phase 1-19 中是否有已被 phase 20 取代但未清理的陈旧结构？
- 顶层散落大量 `tmp_*.sqlite` 探针文件和 `tmp_phase20_8*_debug/` 目录（调试残留，非正式结构）——是否应清理？

---

## 第三部分：必须遵守的红线与哲学

### 3.1 勿增实体（Occam / 最高原则）

**不得新增任何认知实体、答题模块、隐藏求解器、外部课程脚本、硬编码答案表、正则答案路由、关键词路由、学生侧 LLM、UI 自有决策逻辑。** 只能用既有结构：RuntimeTickEvent / ExperienceFlow / SSP / StatePool / B / C / C* / DraftGrid / 动作竞争 —— 来投影、注入、调制、解释。

如果要做的事白皮书没覆盖，**回到 AP 主流找解法**；主流也没有，**停在边界报告**，不要自创实体。

### 3.2 关键白皮书约束（语义摘录，编号请回白皮书核实）

| 约束 | 语义 | 审核要点 |
|---|---|---|
| §35.4 红线1 | 在线嵌入**不替代**显式通道（SSP/L2 分层）| 嵌入向量只做软调制，不能绕过显式 Bn/Cn |
| §132 | 向量/索引是派生的、可重建的，**不是真值源** | 索引可从原始记录重建，不能成黑箱隐藏状态 |
| §19.3b | 学生侧**无外部 LLM** 作语义权威 | 不能用外部 LLM 做答案/语义判定 |
| §1742 | 有界非零 [0.7,1.3]，无候选可独大或全抑 | 调制乘子必须落在界内 |
| §173.3 | L3 公式 `z += lr * 结果值 * 朝成功/失败方向` | L3 向量更新方向 |
| §173.5 | 退火 `lr = lr_min + (lr_max-lr_min)*exp(-support_count/tau)`，boost `1+0.6*abs(outcome)` | 学习率随支持数衰减 |
| §1726 | 动作失败降低同状态同动作 drive | L3 drive 调制 |
| §1727/§37.3 | 源区分，不把内部 tick 混入后果 | 奖惩源与内生源不混 |
| §33.1 | 三元组非对称：异常对象更新，上下文是参考，不共更新 | 锚是参考不被共更新 |
| support_count=0 中性 | 未见过边**不调制**（乘子=1.0）| 不能对从未经历的组合装懂 |

### 3.3 禁用串（over-claim 防线）

**代码与报告中不得出现**：
`l1_l2_l3_complete`、`six_stage_learning_complete`、`online_embedding_converged`、`l1_vector_converged`、`l2_vector_converged`、`l3_vector_converged`、`ladder_complete`、`ladder_converged`、`keyword_organization_converged`、`scene_learned_complete`、`scene_learned_converged`。

AP 的学成判定是**软判据 may_be_wrong**，不声称收敛/完成/通过。检查这些串是否出现在任何 runtime 输出或报告里。

### 3.4 投影护栏模式（所有 10× 投影共用）

每个纯派生投影必须带：
`projection_only=True / subjective=True / may_be_wrong=True / writes_answer_directly=False / creates_reply_candidate=False / uses_existing_ap_flow=True`

审核：13c 阶梯、14 场景学成、10a/10b 等投影是否都带这些护栏？有没有投影偷偷写了答案或产了候选？

### 3.5 工具函数约定

- `_unit(value)`：钳到 [0,1]
- `_bounded_multiplier(value, low, high)`：钳调制乘子到界内
- `FORMULA_ID`：`__init__.py` 不导出 FORMULA_ID，测试通过 `from apv3test.runtime.phase20_7 import runtime as _rtm; _rtm.PHASE20_..._ID` 访问

### 3.6 语言学习阶梯（EDUCATION_PROTOCOL 2026-06-09 Addendum，审核 13c/14 必读）

6 阶段：`echo_imitation → successor_prediction → multi_reply_aggregation → process_paradigm_binding → keyword_organization → grammar_refinement`

场景学成要求（630 行）：`keyword_organization_stage_passed=true` before claiming a scene learned；红线 `student_side_llm=false` / `full_sentence_action=false` / `answer_table_lookup=false`。

scaffold 褪除顺序（148-149 行）：`teacher_off → cold_retest`（双褪除，单教师退场不算学成）。

**注意区分三个不同概念**：
- 语言学习阶梯（6 阶，13c）：语言习得阶段
- scaffold 阶段（demonstrate→strong→weak→feedback_only→teacher_off→cold_retest）：教师褪除时间表
- learning_stage_runtime_progression（8 阶，10a）：教学褪除投影
- learning_object_lifecycle（7 阶，10b）：教学褪除/冷重测就绪

不要把它们混为一谈。

---

## 第四部分：本次要验收的成果（最新工作）

上一个工作线程完成了 4 项，你要逐一验收 + 对抗性审核：

### 4.1 Phase20.13b — L3 动作-后果在线嵌入
**文件**：
- `apv3test/runtime/phase20_7/runtime.py`（L3 live trigger + SQL 参数化）
- `apv3test/runtime/phase20_7/experience_log.py`（L3 向量助手 + rebuild + SQL 参数化）
- `tests/test_phase20_13b_l3_action_consequence_embedding.py`
- `docs/FinalReport_Phase20_13b_L3ActionConsequenceEmbedding_20260630.md`

**验收点**：
- L3 公式是否符合 §173.3（`z += lr * outcome * (ctx - z)` 方向）
- 退火是否符合 §173.5
- support_count=0 时是否中性（乘子=1.0，不调制未见过边）
- §1742 有界 [0.7,1.3]
- §132 索引可重建（rebuild_phase20_7_indexes 能从原始记录恢复 L3 向量）
- §35.4 L3 不替代显式通道（只软调制，不绕过 Bn/Cn）
- §19.3b 无学生侧 LLM
- SQL 是否参数化（无注入面）——上一线程称已修两处 `% ",".join("'"...)` 为 `?` 占位
- 不声称收敛/完成
- **实跑** `python -m pytest tests/test_phase20_13b_l3_action_consequence_embedding.py -v` 确认全过

### 4.2 Phase20.13c — 语言学习阶梯 6 阶投影
**文件**：
- `apv3test/runtime/phase20_7/runtime.py`（`_language_learning_ladder_projection` / `_inactive_language_learning_ladder` / 挂载 / `PHASE20_13C_LANGUAGE_LEARNING_LADDER_ID`）
- `tests/test_phase20_13c_language_learning_ladder.py`
- `docs/FinalReport_Phase20_13c_LanguageLearningLadder_20260630.md`

**验收点**：
- 6 阶分数是否纯派生（从 lifecycle/progression/carryover/tuner 既有键，非硬编码）
- dominant = max(scores) 是否派生一致
- 护栏是否同型（projection_only/不写答案/不产候选/may_be_wrong）
- grammar_refinement 信号：上一线程称初版误用 `boldness_multiplier-1.0`（胆壮度≠语法打磨），已改为 `edit_count+read_count → refinement_pressure`。**核实这个改动是否正确**：白皮书 grammar=refine grammar/particles/politeness/tone/continuity，反复读稿/编辑微调是否比胆壮度更贴切？
- 不声称阶梯收敛/完成
- **实跑** 7 个测试

### 4.3 既存失败清理（PreexistFailures）
**文件**：
- `apv3test/runtime/phase20_open_dialogue.py:663`（**源码改动**：删 `phrase_kind` 冗余路由层，留 `phrase_id.startswith("teacher_phrase::")` 命名空间判据）
- `tests/test_phase8_11_web_workbench_audit.py`（断言 `Phase8`→`Phase20.6`）
- `tests/test_phase8_1_real_trial_and_web_chat.py`（断言 `APV3 本地对话工作台`→`Phase20.6`）
- `tests/test_sqlite_store_contract.py`（counts 加 `phase20_6_fast_action_chains:0`/`phase20_6_slow_memory:0`）
- `docs/FinalReport_Phase20_PreexistFailures_Cleanup_20260630.md`

**验收点（这是唯一动了源码的清理，重点审）**：
- 删 `phrase_kind` 路由是否符合 phase7_9 红线（禁 kind 脚本路由）？
- 删后教师候选过滤是否**真等价**？核实：`teacher_phrase::` 前缀是否由 `_phrase_id_for_teacher_text` 唯一产出？`style::`/`user_utterance::`/`teacher_phrase::` 三命名空间是否互斥？若有人给非教师短语也用 `teacher_phrase::` 前缀会不会误通过？
- 3 个测试改断言是否**掩盖真回归**？API 契约断言是否仍守数据正确性？
- sqlite counts 加 0 键是否掩盖投影漏写？（漏建表应抛 KeyError 非 0）
- **实跑** 4 个测试 + 4 个受影响文件全文 + 邻批

### 4.4 Phase20.14 — 场景学成判据纯派生投影（最新）
**文件**：
- `apv3test/runtime/phase20_7/runtime.py`（`PHASE20_14_SCENE_LEARNED_ID` / `_scene_learned_projection` / `_inactive_scene_learned` / 合流点挂载 / reason 补全 / 索引派生优雅化）
- `tests/test_phase20_14_scene_learned_projection.py`（10 测试）
- `docs/FinalReport_Phase20_14_SceneLearnedProjection_20260630.md`

**验收点（重点对抗性审核）**：
- 是否纯派生（只读 13c ladder_scores / 10b current_stage+lifecycle_stages / carryover readiness，不采集新信号不新增存储）
- **是否不产布尔 `passed=true`**（白皮书 630 用 `passed=true`，但 13c 确立软判据不声称通过；14 是否一致用连续 `scene_learned_confidence ∈ [0,1]` + `may_be_wrong`？这个"软判据化"是否合规，还是应该严格按白皮书产布尔？**请对照白皮书判定**）
- 双褪除就绪 `min(teacher_off, cold_retest)` 是否符合 148-149 顺序褪除
- keyword_organization 阶走完判据（dominant 到 keyword_organization/grammar_refinement）是否符合 630
- 三因子乘法合成是否合理（任一拖后腿则低，软判据 may_be_wrong）
- `lifecycle_readiness` 索引派生：上一线程称初版硬编码 4/2，已改为从 `lifecycle_stages` 派生 `teacher_exit_idx`/`cold_retest_idx`。**核实这个优雅化是否正确、是否真泛化**
- `dominant_blocking_stage` 是否派生一致（三因子最低者）
- 禁用串：无 `scene_learned_complete`/`converged`/`passed`
- 护栏同型
- **实跑** 10 个测试 + 邻批（13c/10b/10a/teaching/cooccurrence）

---

## 第五部分：整个 APV3 底座的检查

除了最新 4 项，你还要检查整个 APV3 底座：

### 5.1 红线全扫
- 扫 `apv3test/runtime/*.py` 是否有 `phrase_kind ==` / `if record.phrase_kind`（phase7_9 红线，上一线程称只剩 0 处，核实）
- 扫 `apv3test/` 是否有 `answer_table` / `student_side_llm` / `must_reply` / `case_name ==` / `incoming_external_query ==`（禁用路由）
- 扫所有 runtime 输出是否有禁用 over-claim 串（见 3.3）
- 扫是否有外部 LLM 调用作学生侧语义权威（§19.3b）

### 5.2 投影一致性
- 所有 10× 投影（9a/10a/10b/10f/10g/11/12/12b/13c/14 等）是否都带完整护栏？
- 有没有投影偷偷改了 selected / 写了答案 / 产了候选？
- 向量索引是否都可重建（§132）？有没有变成不可追溯黑箱的？

### 5.3 调制有界性
- 所有调制乘子是否都过 `_bounded_multiplier` 或等价钳制（§1742 [0.7,1.3]）？
- support_count=0 时是否都中性？

### 5.4 陈旧结构
- phase 1-19 中是否有被 phase 20 取代但未清理的陈旧代码/测试？
- 13a 有报告无测试，是否是缺口？
- 顶层 `tmp_*.sqlite` 探针残留是否应清理？

### 5.5 可优化/泛化点
- 有没有硬编码系数可改为结构派生？（如 14 的 lifecycle_readiness 已改，其他投影有没有类似机会）
- 有没有冗余判据可收敛？（如 phrase_kind 已收敛，其他有没有）
- 有没有更符合 AP 哲学的写法？（用既有结构而非新标签）

---

## 第六部分：验收与审核方法

### 6.1 实跑验证（不要口头假设）
- **工作目录**：`cd "H:/AP原型实验第二期/APV2.1版本原型测试/APV3.0test"` 再跑 pytest。**不要在仓库根跑**。
- 单独跑：`python -m pytest tests/test_phase20_13b_*.py tests/test_phase20_13c_*.py tests/test_phase20_14_*.py -v`
- 全量回归：`python -m pytest tests/ -q`（约 25 分钟，后台跑，exit 0 应得 890 passed / 0 failed）
- 邻批：跑受影响文件全文 + 相邻 phase 测试

### 6.2 实读核实
- 每个声称都要打开源码核实行号。上一线程自述"降智版 codex 会路径调用不对"，所以**不要信它的自述，自己读**。
- 白皮书条款编号要回原文核实语义。

### 6.3 对抗性审核
对每个成果问：
1. **硬编码**？有没有硬编码答案/路由/魔数？
2. **隐患**？有没有误通过/边界漏洞/不可重建？
3. **白皮书不符**？有没有违反红线或越界？
4. **可更泛化/优雅**？有没有可从结构派生却硬编码的？有没有冗余判据可收敛？
5. **更符合 AP 哲学**？有没有用新标签而非既有结构的？

### 6.4 报告要求
你的审核报告应包含：
- 每项成果的验收结论（通过/不通过/有保留）
- 发现的问题（文件:行号 + 违反条款 + 建议）
- 整个底座的检查结论
- 可优化/泛化建议
- **实际跑过的测试结果**（不要口头声称，要贴输出）

---

## 第七部分：注意事项

1. **质量 > 速度**。不要求快，要求最高等级质量。
2. **每一步观察自检**。做完一步检查效果再往下。
3. **对抗性分析在前后都做**。读代码前预判风险，读完后二次自检。
4. **实际检查效果**。不要口头说"应该没问题"，要实跑实读。
5. **发现问题明确指出**，不要含糊。文件:行号 + 违反条款 + 建议。
6. **不要新增实体**。你是审核者，不是开发者。如果发现问题，指出并建议，不要直接改（除非用户让你改）。
7. **白皮书是最高权威**。本提示词的转述若有出入，以白皮书原文为准。

---

## 附：上一个工作线程的自述（供你参考但要独立核实）

上一个工作线程自称：
- 13b：L3 实现干净，6/6 测试过（注：摘要里有 6/7 与 6/6 两种说法，**请实跑确认到底几个测试几个过**），SQL 参数化，全量 869/4。
- 13c：7/7 测试过，对抗审阅修了 grammar_refinement 信号（boldness→edit_count+read_count），全量 876/4。
- PreexistFailures：4 失败转绿，源码删 phrase_kind 冗余层，全量 880/0。
- 14：10/10 测试过，对抗审阅修了 lifecycle_readiness 索引硬编码（4/2→结构派生），全量 890/0。

**这些数字都需要你实跑核实。** 特别是 13b 的 6/7 vs 6/6 矛盾，必须查清。

祝你审核严谨。AP 的质量取决于你这一关。
