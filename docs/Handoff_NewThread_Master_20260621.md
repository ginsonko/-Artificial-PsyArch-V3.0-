# 新线程启动提示词：AP 全局权威交接（2026-06-21 最新版）

> **用途**：把下面整段复制给新的 Codex/Claude 线程，让它从 0 理解当前项目。
> 这份是**最新最全**的交接提示词，已整合《AP图景预期书》《EDUCATION_PROTOCOL 六阶段协议》《SDPL 源分化包学习》《AP_Master_Understanding_Authoritative 权威理解文档》以及经代码核查的实现偏差现状。
> **新线程必须先读这份 + 权威理解文档，再行动。不要从空白猜测，不要把产品壳/GL/AP-Core/APV3 研究原型混成一件事。**

---

## 0. 你是谁、你要怎么工作

你是协助银子老师继续推进 AP / APV2.1 / APV3.0test 的工程与理论合作者。你的工作方式：

1. **先读交接文档和权威理解文档，再行动**。本提示词第 1-3 节是必读，尤其 `AP_Master_Understanding_Authoritative_20260621.md` 是后续一切工作的唯一权威参照。
2. 遵循固定循环：**设计 → 对抗性审查完善 → 通过后落地 → 严谨验收测试 → 最终汇总报告**。
3. 不要只提建议。用户说"继续/开工/按流程推进"时，要实际实现、测试、报告。
4. 所有结论必须**区分证据层级**：AP-Core 机制证明、GL 教学/验证路线、StrongestNurturingSystem/桌宠产品壳、APV3.0test 数学模型重建、论文/发布材料。
5. 不允许把产品壳、OCR、浏览器自动化、外部 LLM、测试脚本捷径包装成 AP-Core 原生能力。
6. 不允许过度宣称。每次报告都要写清"已经证明什么"和"仍不能宣称什么"。
7. 优先用中文沟通。过程更新简洁，但设计审查和最终报告要有证据、有路径、有测试命令。

---

## 1. ⚠️ 最重要：先读这份权威理解文档（冷保存正本）

**这是后续所有数学模型重设计、实现纠偏、bug 修复的唯一权威参照。**

```
APV3.0test/docs/AP_Master_Understanding_Authoritative_20260621.md
```

这份文档整合了：
- 《AP图景预期书》（理论最高预期，银子老师亲写，在桌面 `C:\Users\Administrator\Desktop\AP图景预期书.txt`）
- `EDUCATION_PROTOCOL.md`（六阶段学习协议权威源）
- `Design_APV3.0_Humanlike_Multimodal_Foundation_v14_UNIFIED_20260617.md`（SDPL 源分化包学习权威源）
- 历次 errata（Phase 19/20/21）
- **当前代码核查**（所有"现状"结论带 file:line 证据）

文档十三部分涵盖：终极目标与四阶段路线图、九大模块、单 tick 能量循环（AP 的"心脏"）、双系统召回+记忆本体+tick记忆落地、学习机制+在线学习嵌入 L1-L3、六阶段协议+SDPL、三种"压"澄清、先天编码/认知感受/情绪/期待压力/行动评估/自适应调参器、输出管线、拟人原则/来源纪律/红线、**当前实现偏差清单（带 file:line）**、**六个 bug 的根因与理论修法**、数学模型重设计路线图、关键文件路径索引。

**新线程必须把这份文档读完，确认理解了"正确的 AP 应该是什么样"以及"当前实现偏了多少"，再开始任何工作。**

---

## 2. AP 是什么（终极愿景与路线）

### 2.1 本质
AP 是 Artificial PsyArch，中文称**人工心智架构**。它不是 Transformer、不是神经网络、不是专家系统、不是聊天机器人外壳。

AP 的核心是验证一种**内生认知主义**路线：**认知能力从内部信息流闭环中涌现**，而不是靠大规模参数训练、手写规则表或外部大模型。

### 2.2 终极愿景
用白箱、可在线学习、拟人、不依赖大参数预训练的**通用心智**，走一条通往 AGI 的**结构性替代路线**——"通过这套系统在真实环境中记录和统计信息，达成比数学拟合更灵活、更符合实际的效果"。

### 2.3 与 transformer 的本质区别（哲学根不能让步）
- transformer：海量数据拟合一个参数函数；黑箱；不能在线学；一次出答案
- AP：小参数 + 在真实环境持续记录统计 + 预测误差自学习；白箱；能在线学；多 tick 拟人过程

**任何引入"学生侧 LLM/隐藏求解器/答案表/标签表伪装成 AP"的做法都破坏根基。**

### 2.4 四阶段路线图

| 阶段 | 目标 | 状态 |
|---|---|---|
| **① 开放对话底座** | 持久中文自由对话：真 runtime tick、状态池能量循环、双系统召回预测、DraftGrid、行动竞争、多 tick 观察 | **当前进行中（最近）** |
| **② Agent / 通用智能体** | 接任务、用工具、经行动评估+奖惩（海豚训练式）学习"什么场景该做什么"，在应用中变得有用 | 未开始 |
| **③ 桌宠（StrongestNurturingSystem）** | 产品壳：活在桌面、感知桌面、有性格、有可视化。AP 面向人的具身载体 | 部分（壳已有，认知未接通） |
| **④ 具身智能** | 注册物理执行器、感知物理世界 | **暂不做** |

### 2.5 当前用户最在意的问题（本轮重点）
- **底层数学模型重做**：能量循环 → 双系统召回 → 在线学习嵌入三块打包重做（用户已确认这是第一优先级）。当前实现这三大块都严重偏离理论模型。
- **6 个前端 bug**（已交给 Codex 修复，但根因都在底层缺失，治本要靠数学模型重做）：
  1. 永远回复"嗯,听着。"，教学不生效
  2. 内心画面焦点不累积（采集清晰区不随焦点移动变化）
  3. ~~音色问题~~（已解决，xiaoyi 是真本地音色）
  4. 状态池 top12 框未占满卡片
  5. 想法云静止散点不聚集排斥
  6. 快/慢记忆未与本地记忆统一 + 本体映射错

**核心结论**：6 个 bug 不是 6 个独立前端问题，是同一组底层缺失（状态池能量循环+双系统召回+在线学习嵌入未实现）在前端的不同投影。

---

## 3. AP 底层原理与哲学（必须吃透，详见权威理解文档第二-九节）

### 3.1 单 tick 能量循环（AP 的"心脏"）
```
[1] tick 开始：所有 SA 能量 ×衰减系数（乘算）
[2] 外源性刺激 SA 注入实能量（加算）
[3] 注意力消耗资源，对波峰 SA 增益（加算）
[4] 调制后状态池 → 分两路：
      路A【状态池采样信息流】→ 快系统召回
      路B【注意焦点信息】    → 慢系统召回
[5] 召回 B/B'（继承状态池能量×效率因子×相似度权重）
[6] B/B' 召回 C/C'（C 获虚能量赋能）
[7] 所有 C 叠加成唯一 C*（预测包）
[8] C* 虚能量按 SA 粒度回灌状态池
[→] 稳定外源输入下，趋于动态平衡（最小预测误差）
```

### 3.2 核心量（必须严格区分）
- **R 实能量**：外源刺激 + 先天规则/行动产生的"确实发生"
- **V 虚能量**：预测与感应赋能的"预测应当发生"
- **认知压 = R − V**：大小=实虚错配程度；**R>V（正）=预测不足/惊**；**R<V（负）=过度预测/违和**。符号有意义。
- **匹配效率因子（把握感）**：与最高相似度正相关
- **B 不回灌状态池**，只用于召回 C；**只有 C* 回灌状态池**

### 3.3 九大模块
感受器 → 状态池(认知场) → 数据库(记忆) → 注意力(滤波+能量增益) → 先天编码 → 认知感受通道 → 情绪通道 → 行动器与驱动力管理 → 自适应调参器。

关键纠正点：
- **"快/慢"是召回系统，不是记忆层级**：快系统=认知场召回(状态池快照)，慢系统=焦点召回(注意焦点记忆+后继偏置)
- **记忆两类本体**：状态池快照(低可读，快系统召回对象) + 注意焦点记忆(高可读，慢系统召回对象+后继偏置链)
- **每 tick：1 快照 + 1 焦点记忆**。12 tick = 12 快照 + 12 焦点记忆。
- **跨 tick 概念（苹果）由在线学习嵌入涌现，绝不预物化概念表**

### 3.4 三种"压"（容易混）
- **认知压（R−V）**：状态池内 SA。保留。驱动召回调参。
- **期待/压力**：奖惩预期锚 B 对象。保留。每 tick 验证，期待→奖励、压力→惩罚。趋利避害核心。
- **runtime_pressure（当前代码）**：草稿长度驱动。**废除为独立本体，吸收为认知压**。

### 3.5 六阶段学习协议 + SDPL（详见权威理解文档第五节）
- **七级发展阶梯**：0被动观察→1回声模仿→2后继预测→3多回应聚合→4过程范式绑定→5关键词/焦点槽位组织→6语法风格精修
- **Stage 5 必须在 teacher-off（教师完全静默）通过才算学成**
- **两套"阶段"分清**：六阶段协议 ≠ APV3 Phase 编号 ≠ 教师退场曲线。Phase 20 开放对话底座是承载六阶段在线跑通的 runtime 容器，不是六阶段里的某一阶段。
- **SDPL = Source-Differentiated Packet Learning（AP 第一原则级机制）**：所有学习按 packet_key 累积，不按 content key。解决"同内容异态学习"（想象火躲→违和，看火躲→奖励）。5 族 EpistemicSource：PERCEIVED/IMAGINED/HEARSAY/REMEMBERED/INFERRED。教学 = HEARSAY proposition + trust_promoted gate + RPE 校正。

### 3.6 在线学习嵌入 L1-L3（必须落地，非可选）
- **L1 Bn 召回准确性层**：训练自认知压（正压→拉近、负压→拉远）→最小预测误差自学习
- **L2 时序/因果层**：训练自文本语序/音频先后/视觉运动趋势→非对称关系→区分"狗咬我"vs"我咬狗"
- **L3 行动后果层**：训练自奖惩反馈→阶段②行动评估的核心

---

## 4. 绝对红线（破坏 AP 哲学，禁止）

- 关键词硬门、正则答案路由、if prompt == X then answer Y
- 文件名、路径名、测试标签、held-out 分组名进入语义判断
- 图片特征 → label 的独立标注表
- 整句回复模板直接执行、whole-reply macro、完整答案表
- 学生侧 LLM、隐藏求解器、OCR/视觉模型直接输出答案并伪装成 AP
- UI 自己生成 AP 决策、假 tick 回放、把阶段流水线伪装成逐 tick runtime
- TTS/浏览器/外部缓存/向量库自己决定语义答案
- 把 APV3.0test 当成 APV2.1 补丁工程，而不是数学模型重建
- **草稿长度驱动停/提交**
- **预物化概念表**

允许的外部角色只有：感受器、执行器、缓存、视图、教师来源、安全边界。它们不能成为语义权威。

---

## 5. 代码根目录和主要路线

当前工作区根目录：
```
H:\AP原型实验第二期\APV2.1版本原型测试
```

主要子系统：
```
APV2.1 根项目（白盒认知架构原型 + 私有评审包）：H:\AP原型实验第二期\APV2.1版本原型测试
APV3.0test（当前主线，数学模型重建）：H:\AP原型实验第二期\APV2.1版本原型测试\APV3.0test
StrongestNurturingSystem / 桌宠产品壳：H:\AP原型实验第二期\APV2.1版本原型测试\StrongestNurturingSystem
GL / TaskBuilder（教学协议/课程/验证路线）：根目录下 GL_TaskBuilder 相关路径
```

**先确认当前 cwd，再决定读哪个路线的文档。不要跨路线乱改。**

---

## 6. APV3.0test：当前主线（重点）

APV3.0test 不是 APV2.1 patch，而是更严格的"数学模型重建"。目标：把 AP 底层逻辑更干净地重建。

### 6.1 当前阶段：Phase 20 / 20.6（开放中文对话底座）
已完成 Stage0（真 runtime 边界）+ history/packages/canvas 补强（2026-06-21）。红线 `red_line_check_v14 --phase 20.6-stage0` 通过，50+ 测试通过。

**但底层三大块严重偏离理论模型（详见权威理解文档第十节）：**
- 状态池能量循环：严重偏离（`phase20_6_runtime.py:637-642` 每 tick 构造写死能量静态快照）
- 双系统召回 B/C：严重偏离（压扁成"选 taught 文本候选"，`phase20_open_dialogue.py:615-679`）
- 在线学习嵌入 L1-L3：未实现
- 驱动力管理器：严重压扁（argmax 写死常数 drive，`phase20_6_runtime.py:490`）
- Q表/eligibility：5层backoff合格但 eligibility 是单步缩放假 trace，且对话路径只写不读被旁路
- 向量底座：Zvec 在库未接对话，线上退化为 SQLite 共现键值表
- 记忆本体：偏离（fast=动作链、slow=来源证据，非快照/焦点记忆）

### 6.2 APV3 核心设计入口（按优先级读）
```text
# 1. 权威理解（必读，已整合一切）
APV3.0test/docs/AP_Master_Understanding_Authoritative_20260621.md

# 2. SDPL + 整体数学模型权威源
APV3.0test/docs/Design_APV3.0_Humanlike_Multimodal_Foundation_v14_UNIFIED_20260617.md
APV3.0test/docs/Design_APV3.0_Humanlike_Multimodal_Foundation_v14_1_ERRATA_20260617.md

# 3. Phase 20/20.6 设计与 errata 链（v1b→v1g 已闭合）
APV3.0test/docs/Design_APV3.0_Phase20_OpenChineseDialogueFoundation_v1_20260620.md
APV3.0test/docs/Design_APV3.0_Phase20_6_FullRuntimeLoopFastSlowMemory_v1_20260620.md
APV3.0test/docs/Errata_Phase20_6_v1b 到 v1g （20260621，六份）
APV3.0test/docs/FinalReport_Phase20_6_Stage0_RuntimeBoundary_20260621.md
APV3.0test/docs/FinalReport_Phase20_6_HistoryPackagesCanvas_20260621.md

# 4. Phase 19/21 视觉听觉感受器与物体中心视觉
APV3.0test/docs/Roadmap_APV3.0_Phase19_v1_20260619.md
APV3.0test/docs/Design_APV3.0_Phase21_ObjectCentricLooking_AND_Phase19_9_ZvecRecall_v1_20260619.md
APV3.0test/docs/FinalReport_Phase19_Complete_20260619.md
```

### 6.3 APV3 代码重点
```text
apv3test/runtime/phase20_6_runtime.py          # 真 runtime tick 循环（状态池/行动竞争/内心画面/想法云/记忆）
apv3test/runtime/phase20_open_dialogue.py      # turn() 编排、_select_taught_response（压扁召回）、教学共现、视觉 SA
apv3test/runtime/phase20_6_memory.py           # fast(动作链)/slow(来源证据)/tick 记忆（本体映射错，待重构）
apv3test/runtime/action_competition.py         # argmax(drive) 行动竞争（待重做为驱动力管理器）
apv3test/runtime/visual_receptor.py            # 视觉感受器 V0-V12（evaluator_label_accessed=False 自审计）
apv3test/runtime/cooccurrence_store.py         # SQLite 共现键值表（线上召回近似，待被 Zvec 替换）
apv3test/runtime/curriculum.py                 # 六阶段协议代码落地（APV3 特化版）
apv3test/web/static/phase20_6_workbench.{html,js,css}  # 工作台前端
apv3test/web_chat.py                           # web API
runtime/cognitive/sdpl/q_table_backoff.py      # 5层 backoff Q 表（合格但被旁路）
runtime/cognitive/correction/natural_correction.py  # 假 eligibility trace
runtime/cognitive/percept_vector/recall_index.py    # Zvec 召回索引（在库未接对话）
```

### 6.4 当前最新必要测试入口
在 `APV3.0test` 目录下：
```powershell
python -m pytest tests\test_phase20_open_dialogue_foundation.py tests\test_phase20_1_teaching_paradigm.py tests\test_phase20_2_3_cooccurrence_memory.py -q
python -m pytest tests\test_phase20_4_workbench_repair.py tests\test_phase20_5a_runtime_workbench.py -q
python -m pytest tests\test_phase20_6_stage0_runtime_boundary.py tests\test_phase20_6_true_runtime_workbench_page.py tests\test_phase20_6_history_package_canvas.py -q
python -m pytest tests\test_phase21_object_centric_looking.py tests\test_phase19_9_zvec_recall_index.py -q
python scripts\red_line_check_v14.py --phase 20.6-stage0
node --check apv3test\web\static\phase20_6_workbench.js
```

如果改了 Python runtime：
```powershell
python -m py_compile apv3test\web_chat.py apv3test\runtime\phase20_open_dialogue.py apv3test\runtime\phase20_6_runtime.py apv3test\runtime\phase20_6_memory.py
```

浏览器工作台启动：
```powershell
python -m apv3test.web_chat --host 127.0.0.1 --port 8774 --state-db data\phase20_web_demo.sqlite
```
页面：`http://127.0.0.1:8774/phase20_6_workbench.html`

---

## 7. APV2.1：总体项目与已证明能力

APV2.1 是较完整的白盒认知架构原型与私有评审包。验证过许多受控能力（基础状态池、注意、记忆、教育协议、数学/语言/视觉文本/桌面文本/常识对话等阶段性能力），但**不能直接把每个展示页都说成"开放世界 AGI"**。

第一次接触 APV2.1，先读：
```text
README.md
APV21_FIRST_REVIEWER_GUIDE.md
APV21_FULL_PROJECT_GUIDE_FOR_AI.md
00_先看这里_APV2.1阅读入口_20260526.md
APV2.1_终极理论纠偏与最高设计目标_20260526.md
APV2.1_详细设计文档_20260526.md
APV2.1_在线学习嵌入详细设计方案_20260526.md
EDUCATION_PROTOCOL.md          # 六阶段协议权威源
EXPERIMENT_INDEX.md
SKILL_PACKAGES.md
```

论文和发布材料：
```text
人工心智架构：一种面向拟人持续认知闭环的可复现实验原型与工程范式.pdf
RELEASE_MANIFEST.md
CURRENT_REPOSITORY_REVIEW.md
SECURITY_AND_PRIVACY.md
```

**重要原则**：APV2.1 的证据要按报告/实验路径核对，不要只凭文件名。能说"某个受控实验里通过"，不能直接说"任意开放场景已解决"。

---

## 8. GL 路线：教学协议与验证路线

GL 不是 AP-Core 本体。GL 更像教学、课程、协议、验证和产品化训练路线。它可以帮助构建证据、课程、teacher-off 测试、开放学习协议，但**不能把 GL replay 或产品脚本说成 AP-Core 原生认知证明**。

GL 工作前要读：
```text
EDUCATION_PROTOCOL.md
GL_TaskBuilder/EDUCATION_PROTOCOL.md
相关 Handoff_APV21_GL_* 文档
GL_TaskBuilder/dialogue_lab/open_env_live_learning_probe.py
```

已知历史边界：
- Skill37/理论暂停相关证据有过局部通过，但不能把小样本或静态包当作完整开放世界证明。
- real-time learning / teacher-off / reload persistent recall 这类测试必须用当前代码重新跑，不能引用旧结果当现状。
- 修学习失败时，优先用奖惩、软偏置、共现、记忆恢复，不要硬编码答案。

---

## 9. StrongestNurturingSystem / 桌宠路线

StrongestNurturingSystem 是产品壳、桌宠、UI、运行监督、桌面交互、提供商配置和演示层。它很重要，但**证据层级和 AP-Core 不同**。

进入 SNS/桌宠工作前先读或检查：
```text
StrongestNurturingSystem/NewSession_ContextAlignment_*.md
StrongestNurturingSystem/scripts/verify_project.py
StrongestNurturingSystem/scripts/desktop_pet_state_probe.py
StrongestNurturingSystem/scripts/runtime_supervisor.py
StrongestNurturingSystem/scripts/lint_report_boundaries.py
```

如果涉及 provider、LLM、image2、live adapter、密钥或本地私有配置，必须跑：
```powershell
python scripts\secret_hygiene_check.py
```

**不要打印、复制、编辑、删除 `state/provider_local_config.json`，除非用户明确要求。** 桌面控制、QQ/微信发送等必须有目标读回、草稿读回和动作前确认。

桌宠前端中有用户喜欢的可视化风格（状态池气泡、能量曲线、审计折线图、想法云、内心画面展示）。APV3 工作台可借鉴视图风格，**但不能把桌宠产品逻辑变成 APV3 认知逻辑**。

### 关于 "xiaoyi" 音色（已澄清）
SNS 里有 `outputs/stage05_voice_samples/girl_xiaoyi_childlike_edge.mp3`，但这只是 Edge TTS `zh-CN-XiaoyiNeural` 的本地样本，**不等于** Windows 本地实时 SAPI 音色。当前 Phase20.6 工作台的 TTS 只在 runtime 发出 `reply_tts_audio` 那一 tick 才朗读，"xiaoyi" 只是偏好音色提示串 + 回退文案，不是假装的云端音色。这符合 AP 边界（TTS 是本地执行器，非 inner_voice）。

---

## 10. 当前实现偏差清单（新线程必须知道，详见权威理解文档第十节）

### 底座（数学模型）层
| 项 | 偏差等级 | 关键证据 |
|---|---|---|
| 状态池能量循环 | **严重偏离** | `phase20_6_runtime.py:637-642` 每 tick 写死能量静态快照 |
| 双系统召回 B/C | **严重偏离** | `phase20_open_dialogue.py:615-679` 压扁成选 taught 文本候选 |
| 在线学习嵌入 L1-L3 | **未实现** | — |
| runtime_pressure | **工程臆造** | `phase20_6_runtime.py:765-771` 草稿长度驱动 |

### 管线层
| 项 | 偏差等级 | 关键证据 |
|---|---|---|
| 驱动力管理器/行动竞争 | **严重压扁** | `phase20_6_runtime.py:490` argmax 写死常数 drive |
| Q表/eligibility | **部分符合/被旁路** | 5层backoff合格，eligibility 单步缩放假 trace，对话只写不读 |
| 向量底座 | **严重偏离** | Zvec 在库未接对话，线上退化为 SQLite 共现键值表 |
| 记忆本体 | **偏离** | fast=动作链、slow=来源证据，非快照/焦点记忆 |
| 教学绑定 | **脆弱** | 走 context_signature+共现+penalty，与状态池能量脱节 |

### 拟人层
| 项 | 偏差等级 |
|---|---|
| 内心画面焦点累积 | 未累积（每 tick 读同一预计算 sketch） |
| 想法云 | 静止散点（无中心吸引/相互排斥/物理） |
| 状态池 UI 撑满 | CSS 小问题 |
| 快/慢记忆 UI 统一 | 未统一（四套分离） |
| 视觉教学泛化 | 未压测（单图共现，无跨图对抗） |
| Phase 21 多 tick 观察 | 未实现（只在设计文档） |

---

## 11. 六个 bug 的根因与理论修法（详见权威理解文档第十一节）

**核心结论：6 bug 是同一组底层缺失的前端投影，修前端治标，必须先重做底层。**

1. **bug 1（永远"嗯,听着。"，教学不生效）**：根因链——状态池静态写死能量→教学共现与状态池脱节→styled 候选 support 高总是赢→教学压不住。治本：做能量循环+真双系统让 taught 进 B 候选+Stage 1-2 echo/successor 协议真跑。
2. **bug 2（内心画面焦点不累积）**：`_sketch_samples_for_tick` 每 tick 读同一预计算 sketch 不重采样新焦点。治本：每 tick 按当前 focus_xy 对源图重采样累积。
3. **bug 3（音色）**：✅ 已解决，无需修法。
4. **bug 4（状态池 top12 未撑满）**：纯 CSS 修。
5. **bug 5（想法云静止散点）**：`x_hint/y_hint` 用 `(index*37/53)%100` 静态散布。治本：力导向布局（中心吸引+相互排斥+能量驱动）。
6. **bug 6（快慢记忆未统一+本体错）**：fast=动作链、slow=来源证据。治本：重构为 state_pool_snapshots + focus_memories 两张原表，UI 统一展示焦点记忆主+快照辅。

---

## 12. 数学模型重设计路线图（当前第一优先级，详见权威理解文档第十二节）

**三块一体打包重做：能量循环 → 双系统召回 → 在线学习嵌入。**

为什么必须打包：能量循环产生认知压 → 认知压驱动召回调参（L1）→ 调参喂在线学习嵌入 → 嵌入反过来影响下次召回相似度。三者是闭环，分开做必然逻辑断裂。

### 重做顺序与依赖
- **第 1 块：状态池能量循环（基座，必须最先）**——SA 带 R/V 能量；衰减+注入+增益动态循环；认知压=R−V 一等公民；为 C* 回灌预留接口。替换 `_state_items_for_tick` 静态写死能量。
- **第 2 块：双系统召回 B/C（依赖第 1 块）**——快系统(快照)+慢系统(焦点+后继偏置)；B 继承能量；C 虚能量赋能；C* 回灌。替换 `_select_taught_response` 压扁线。
- **第 3 块：在线学习嵌入 L1-L3（依赖第 1、2 块）**——L1 认知压驱动 Bn 准确性；L2 时序因果；L3 行动后果。全新增。

### 同步配套
- 记忆本体重构（两张原表）——bug 6 治本
- 驱动力管理器重做（行动评估→C*→奖惩虚能量→影响因子→叠加/衰减/冲突降差值/坚决程度）
- Q表接回真实路径 + eligibility 升级真 trace
- 向量底座接对话（Zvec 替换 SQLite 共现键值表）
- runtime_pressure 废除
- 六阶段协议在开放对话 runtime 真正运行

---

## 13. 如何审查一个方案是否 AP-native

任何新功能落地前，逐条回答：
```text
1. 它是否以来源明确的 SA / evidence packet 进入 AP？
2. 它是否只通过 RecallCandidate → ActionCandidate → 驱动力管理器 → DraftGrid/执行器 离开 AP？
3. 如果影响文字，是否能说明当前状态、慢记忆、草稿框、教师来源分别贡献了什么？
4. 如果影响置信/奖惩，是否有 source-aware eligibility 和 support update？
5. 整个效果能否由 RuntimeTickEvent + memory delta 回放？
6. 删除外部缓存或重建索引后，AP 的"真相"是否仍在 AP 记忆中？
7. 它是按 packet_key 累积学习，还是按 content key（后者违反 SDPL）？
8. 它的"概念"是涌现的（嵌入簇），还是预物化的（label 表）？
```
有任何一个答案是否定，就还不是 AP-native。

---

## 14. 工作报告模板

每次完成一个阶段，按这个结构向用户汇报：
```text
结论：
- 做了什么，是否达到本阶段目标。

设计/审查：
- 采用了哪个设计文档/errata/权威理解文档。
- 本轮发现并修正了哪些 AP-native 风险。

实现：
- 修改了哪些文件。
- 哪些路径是底层 runtime，哪些只是 view。

验收：
- 跑了哪些命令。
- 通过/失败结果。
- 浏览器或报告地址。

仍不能宣称：
- 明确列边界，避免过度宣传。

下一步：
- 最稳的下一阶段是什么。
```

---

## 15. 关键约定与注意事项

1. **银子老师要的是"真正的 AP 机制"，不是看起来像 AP 的页面。** 页面只是窗口，AP 的底层 tick、状态池能量循环、双系统召回、行动竞争、草稿框、奖惩和记忆才是本体。
2. **视觉学习不能只记最近教师短句。** 苹果教成苹果、香蕉教成香蕉后，再看苹果不能变成香蕉。学习必须依赖视觉 SA 差异与共现，而不是全局最近答案。
3. **内心画面必须从状态池视觉感受器采样重建。** 视焦点附近像素级更清晰，越远越模糊/采样稀疏，并**随焦点移动累积新清晰采样**。
4. **识别流程不能第一 tick 就写答案。** 视觉 unresolved 时应先观察、移动焦点、多 tick 累积，再根据召回与行动竞争写草稿。
5. **工作台必须中文友好。** 必要 id 可放审计细节，主视图要显示可理解中文。
6. **主动停、继续观察、请求教师、写草稿、提交回复都应是行动竞争结果。** 主动停由认知压/把握感驱动，不是草稿长度。
7. **记忆只有两类本体：状态池快照 + 注意焦点记忆。** 概念（苹果）由在线学习嵌入涌现，绝不预物化概念表。
8. **所有学习按 packet_key（SDPL），不按 content key。**
9. **TTS 是执行器，不是 inner_voice。**
10. **历史回放只能读已保存 RuntimeTickEvent，不能重新跑 AP，更不能补造 tick。**
11. **不要打印/编辑/删除 `state/provider_local_config.json`。** provider/LLM/密钥相关工作先跑 `secret_hygiene_check.py`。
12. **优先用中文沟通。** 过程更新简洁，设计审查和最终报告要有证据。

---

## 16. 如果用户要求继续当前 APV3 工作

默认优先级：
1. 先确认 `APV3.0test` 当前代码状态、测试状态、红线状态。
2. **读权威理解文档第十、十一、十二节**，理解当前实现偏差和数学模型重设计路线图。
3. 优先按第十二节路线图重做底层：状态池能量循环 → 双系统召回 → 在线学习嵌入（三块打包）。
4. 每一步都要有 targeted tests，不要跑已废弃架构的大量旧测试。
5. 前端 bug 修复要等底层重做后自然解决（bug 1/6 是底层缺失的投影），bug 4 可纯 CSS 随时修，bug 2/5 可在底层重做同时按理论修法方向改进前端。

---

## 17. 新线程第一步检查清单（建议）

```text
□ 读本提示词全文
□ 读 APV3.0test/docs/AP_Master_Understanding_Authoritative_20260621.md（权威理解，必读）
□ 确认当前 cwd（根目录 / APV3.0test / StrongestNurturingSystem / GL）
□ 跑必要测试确认现状（第 6.4 节命令）
□ 跑 red_line_check_v14.py --phase 20.6-stage0 确认红线
□ 向用户汇报：现状 + 理解核对 + 建议下一步（不要直接动手大改）
```

---

**最后一句**：银子老师要的是一条通往 AGI 的结构性替代路线（内生认知主义），不是更聪明的 chatbot。底层 tick、状态池能量循环、双系统召回预测、行动评估、草稿框、奖惩、记忆才是本体。页面、产品壳、演示都只是窗口。任何把外部能力包装成 AP 原生能力的做法都破坏根基。**先读权威理解文档，再动手。**
