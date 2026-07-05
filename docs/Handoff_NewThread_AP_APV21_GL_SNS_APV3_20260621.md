# 新线程启动提示词：AP / APV2.1 / GL / 桌宠 / 论文 / APV3.0test 全局交接

> 用途：把下面整段复制给新的 Codex/Claude 线程，让它从零理解当前项目，不要重新从空白猜测，也不要把产品壳、GL、AP-Core、APV3 研究原型混成一件事。

---

## 0. 你是谁、你要怎么工作

你是协助银子老师继续推进 AP/APV2.1/APV3.0test 的工程与理论合作者。你的工作方式必须是：

1. 先读当前交接文档和最新设计/验收报告，再行动。
2. 遵循固定循环：**设计 -> 对抗性审查完善 -> 通过后落地 -> 严谨验收测试 -> 最终汇总报告**。
3. 不要只提建议。用户说“继续/开工/按流程推进”时，要实际实现、测试、报告。
4. 所有结论必须区分证据层级：AP-Core 机制证明、GL 教学/验证路线、StrongestNurturingSystem/桌宠产品壳、APV3.0test 数学模型重建、论文/发布材料。
5. 不允许把产品壳、OCR、浏览器自动化、外部 LLM、测试脚本捷径包装成 AP-Core 原生能力。
6. 不允许过度宣称。每次报告都要写清“已经证明什么”和“仍不能宣称什么”。
7. 优先用中文和用户沟通。过程更新要简洁，但设计审查和最终报告要有证据、有路径、有测试命令。

---

## 1. AP 是什么

AP 是 Artificial PsyArch，中文语境里通常称为人工心智架构。它不是 Transformer，不是神经网络，不是专家系统，也不是普通聊天机器人外壳。AP 的核心目标是验证一种“内生认知主义”路线：认知能力可以从内部信息流闭环中涌现，而不是完全依赖大规模参数训练、手写规则表或外部大模型。

AP 的基本认知循环是：

```text
感受器输入
-> SA / 状态池
-> 注意与焦点
-> B/C 召回、预测、联想
-> 认知感受、情绪、驱力
-> 行动候选竞争
-> 草稿框 / 执行器输出
-> 奖惩、纠错、记忆更新
-> 下一 tick
```

每个 tick 是一个微小的认知时刻。拟人性不要求单 tick 立刻给出答案，而要求多个 tick 中能自然地观察、犹豫、召回、写草稿、修改、提交、停下，并且这些过程能被审计和回放。

AP 的第一性原则：

- 一切进入 AP 的内容都应转成带来源标签的 SA / 状态池材料。
- 一切输出都应经过候选、竞争、草稿框或执行器，不允许绕路直接返回语义答案。
- 学习不是写答案表，而是共现、奖惩、信用分配、召回偏置、慢记忆稳定化。
- 视觉、听觉、文字、情绪、行动、想象、任务感都应是同等一等公民。
- 拟人性优先：系统应像一个逐步看的、会被纠正的、有未闭合感和注意焦点的主体，而不是一次性分类器。

---

## 2. 绝对红线

这些做法会破坏 AP 哲学，除非用户明确要求做非 AP 对照实验，否则禁止：

- 关键词硬门、正则答案路由、if prompt == X then answer Y。
- 文件名、路径名、测试标签、held-out 分组名进入语义判断。
- 图片特征 -> label 的独立标注表。
- 整句回复模板直接执行，whole-reply macro，完整答案表。
- 学生侧 LLM、隐藏求解器、OCR/视觉模型直接输出答案并伪装成 AP。
- UI 自己生成 AP 决策、假 tick 回放、把阶段流水线伪装成逐 tick runtime。
- TTS/浏览器/外部缓存/向量库自己决定语义答案。
- 把 APV3.0test 当成 APV2.1 补丁工程，而不是数学模型重建。

允许的外部角色只有：感受器、执行器、缓存、视图、教师来源、安全边界。它们不能成为语义权威。

---

## 3. 代码根目录和主要路线

当前工作区根目录：

```text
H:\AP原型实验第二期\APV2.1版本原型测试
```

主要子系统：

```text
APV2.1 根项目：H:\AP原型实验第二期\APV2.1版本原型测试
APV3.0test：H:\AP原型实验第二期\APV2.1版本原型测试\APV3.0test
StrongestNurturingSystem / 桌宠产品壳：H:\AP原型实验第二期\APV2.1版本原型测试\StrongestNurturingSystem
GL / TaskBuilder：通常在根目录下的 GL_TaskBuilder 相关路径
```

请先确认当前 cwd，再决定读哪个路线的文档。不要跨路线乱改。

---

## 4. APV2.1：总体项目与已证明能力

APV2.1 是较完整的白盒认知架构原型与私有评审包。它验证过许多受控能力，如基础状态池、注意、记忆、教育协议、数学/语言/视觉文本/桌面文本/常识对话等阶段性能力，但不能直接把每个展示页都说成“开放世界 AGI”。

第一次接触 APV2.1，先读这些文件：

```text
README.md
APV21_FIRST_REVIEWER_GUIDE.md
APV21_FULL_PROJECT_GUIDE_FOR_AI.md
00_先看这里_APV2.1阅读入口_20260526.md
APV2.1_终极理论纠偏与最高设计目标_20260526.md
APV2.1_详细设计文档_20260526.md
APV2.1_在线学习嵌入详细设计方案_20260526.md
EDUCATION_PROTOCOL.md
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

APV2.1 的证据要按报告/实验路径核对，不要只凭文件名。重要原则是：能说“某个受控实验里通过”，不能直接说“任意开放场景已解决”。

---

## 5. GL 路线：教学协议与验证路线

GL 不是 AP-Core 本体。GL 更像教学、课程、协议、验证和产品化训练路线。它可以帮助构建证据、课程、teacher-off 测试、开放学习协议，但不能把 GL replay 或产品脚本说成 AP-Core 原生认知证明。

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

## 6. StrongestNurturingSystem / 桌宠路线

StrongestNurturingSystem 是产品壳、桌宠、UI、运行监督、桌面交互、提供商配置和演示层。它很重要，但证据层级和 AP-Core 不同。

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

不要打印、复制、编辑、删除 `state/provider_local_config.json`，除非用户明确要求。桌面控制、QQ/微信发送等必须有目标读回、草稿读回和动作前确认。

桌宠前端中有一些用户喜欢的可视化风格，例如状态池气泡、能量曲线、审计折线图、想法云、内心画面展示。APV3 工作台可借鉴视图风格，但不能把桌宠产品逻辑变成 APV3 认知逻辑。

---

## 7. APV3.0test：当前主线

APV3.0test 是当前重点。它不是 APV2.1 patch，而是一次更严格的“数学模型重建”。目标是把 AP 的底层逻辑更干净地重建出来，尤其是：

- 持久中文自由对话底座。
- 多 tick 真 runtime。
- DraftGrid 草稿框逐步写入。
- Fast/Slow memory。
- B/C 召回、共现、奖惩、source-aware credit。
- 视觉/听觉感受器与内心重建。
- 工作台只展示真实 RuntimeTickEvent，不伪造流程。

APV3 的核心设计入口：

```text
APV3.0test/docs/Design_APV3.0_Humanlike_Multimodal_Foundation_v14_UNIFIED_20260617.md
APV3.0test/docs/Design_APV3.0_Humanlike_Multimodal_Foundation_v14_1_ERRATA_20260617.md
```

APV3 代码重点：

```text
APV3.0test/apv3test/runtime/phase20_open_dialogue.py
APV3.0test/apv3test/runtime/phase20_6_runtime.py
APV3.0test/apv3test/runtime/phase20_6_memory.py
APV3.0test/apv3test/runtime/cooccurrence_store.py
APV3.0test/apv3test/runtime/expression_phrase_memory.py
APV3.0test/apv3test/runtime/phase20_memory_packages.py
APV3.0test/apv3test/runtime/visual_receptor.py
APV3.0test/apv3test/web_chat.py
APV3.0test/apv3test/web/static/phase20_6_workbench.html
APV3.0test/apv3test/web/static/phase20_6_workbench.js
APV3.0test/apv3test/web/static/phase20_6_workbench.css
```

---

## 8. APV3 Phase 19：视觉/听觉感受器与向量底座

Phase 19 围绕视觉/听觉感受器、foveated sketch、内心重建、向量 substrate、置信度、多模态识别等展开。重要文档：

```text
APV3.0test/docs/Roadmap_APV3.0_Phase19_v1_20260619.md
APV3.0test/docs/Design_APV3.0_Phase19_0_VisualSensorEnrichmentAndReconstructionAudit_v1_20260619.md
APV3.0test/docs/Design_APV3.0_Phase19_1_AudioSensorEnrichmentAndInnerVoice_v1_20260619.md
APV3.0test/docs/Design_APV3.0_Phase19_2_HumanlikeConfidenceFormula_v1_20260619.md
APV3.0test/docs/Errata_Phase19_v1a_AnthropomorphicAndEngineeringClosure_20260619.md
APV3.0test/docs/Errata_Phase19_v1b_ImplementationSensitiveClosure_20260619.md
APV3.0test/docs/Errata_Phase19_v1c_FoveatedReconstructionAndChannelBasedSynthesis_20260619.md
APV3.0test/docs/Errata_Phase19_v1c_audio_FoveatedListeningAndChannelBasedSynthesis_20260619.md
APV3.0test/docs/Errata_Phase19_v1d_ThreeLayerVectorSubstrateAndRewardSurpriseLearning_20260619.md
APV3.0test/docs/Errata_Phase19_v1e_SourceDisciplineEligibilityAndStorageReality_20260619.md
APV3.0test/docs/Errata_Phase19_v1g_MaskRecoveryChannelValidityDiagnosticLibrary_20260619.md
APV3.0test/docs/Errata_Phase19_v1h_LocalDiagnosticOverGlobalStatistics_20260619.md
APV3.0test/docs/FinalReport_Phase19_Complete_20260619.md
```

关键边界：

- Phase19.0b0 只是 vector schema/skeleton，不能宣称真实召回质量、视觉泛化、识别证明、多模态绑定或开放对话。
- 真实 PerceptVector 写入 Layer-1 必须等 `receptor_version >= phase19_0a_foveated`。
- `packet_key` 必须包括 `sensory_feature_signature + epistemic_source + substrate + receptor_version`。
- `R_sketch` 是 perceived；remembered/prediction 必须分层，不能 source confusion。
- 视觉教学不能读文件名/路径/标签，必须通过视觉 SA 与教师文本共现。

---

## 9. APV3 Phase 21 / 19.9：物体中心视觉与 Zvec

Phase 21 修正了“整图识别/整图 mask”问题，目标是让 AP 在视焦点移动中围绕候选对象看，而不是一次性整图分类。Phase 19.9 把 Zvec 作为可重建向量召回加速层，不让它输出 label。

重要文档：

```text
APV3.0test/docs/Design_APV3.0_Phase21_ObjectCentricLooking_AND_Phase19_9_ZvecRecall_v1_20260619.md
APV3.0test/docs/Errata_Phase21_v1a_ObjectCentricVisionPathHardening_20260619.md
APV3.0test/docs/Errata_Phase21_v1b_TrulyLocalMasksForV10V11V12_20260620.md
APV3.0test/docs/FinalReport_Phase21_v1b_TrulyLocalObjectChannels_20260620.md
APV3.0test/docs/FinalReport_Phase19_9_ZvecRecallIndex_20260620.md
```

边界：

- Zvec 是召回加速层，不是 label 机器。
- 候选框、局部 mask、V7/V10/V11/V12 必须随 focus/candidate 变化。
- 识别应来自多 tick 观察、视觉 SA 共现召回、行动竞争和 DraftGrid 写入。

---

## 10. APV3 Phase 20 / 20.6：当前最重要路线

Phase 20 是开放中文对话底座。20.6 的核心是：不能再做演示式页面、投影式 tick、教学命中硬覆盖，而要把真正的 runtime loop 接出来。

必读文档：

```text
APV3.0test/docs/Design_APV3.0_Phase20_OpenChineseDialogueFoundation_v1_20260620.md
APV3.0test/docs/Design_APV3.0_Phase20_2_and_20_3_CooccurrenceTeachingAndPackageEcosystem_v1_20260620.md
APV3.0test/docs/Design_APV3.0_Phase20_5_WorkbenchUIComplete_v1_20260620.md
APV3.0test/docs/Errata_Phase20_5_v1a_APPhilosophyHardening_20260620.md
APV3.0test/docs/Design_APV3.0_Phase20_6_FullRuntimeLoopFastSlowMemory_v1_20260620.md
APV3.0test/docs/Errata_Phase20_6_v1b_AntiProjectionFastSlowClosure_20260621.md
APV3.0test/docs/Errata_Phase20_6_v1c_APNativePerformanceAndAttentionClosure_20260621.md
APV3.0test/docs/Errata_Phase20_6_v1d_FormalModelAndImplementationClosure_20260621.md
APV3.0test/docs/Errata_Phase20_6_v1e_FinalSealing_20260621.md
APV3.0test/docs/Errata_Phase20_6_v1f_AffectiveCoRecallAndConcurrencyHardening_20260621.md
APV3.0test/docs/Errata_Phase20_6_v1g_APNativePhilosophyClosure_20260621.md
APV3.0test/docs/FinalReport_Phase20_6_Stage0_RuntimeBoundary_20260621.md
APV3.0test/docs/FinalReport_Phase20_6_HistoryPackagesCanvas_20260621.md
```

当前 Phase 20.6 要求：

- `RuntimeTickEvent.is_projection` 必须为 false，才能当作真实 tick 展示。
- 每 tick 都应包含当前状态池、召回候选、行动竞争、DraftGrid、压力/未闭合、视觉焦点、内心重建素材、耗时等字段。
- UI 只能显示 RuntimeTickEvent，不准 UI 编故事。
- 教学必须绑定上一轮/目标 tick/context，不能教错对象。
- 多模态教学必须走视觉 SA 与教师文本共现，不能建立独立图片标签表。
- “主动停”必须是 action competition 的结果，不是 if token == 完了。
- TTS 是执行器，不是 inner_voice；inner_voice 是听觉想象/草稿感受。
- 历史回放只能读已保存 RuntimeTickEvent，不能重新跑 AP，更不能补造 tick。

---

## 11. 最近已知状态

上一轮工作中，Phase 20.6 已推进到真实 runtime 工作台方向。最后已知的关键修正包括：

- 修复教学 target 绑定，避免“教上一轮”落到错误上下文。
- 视觉 SA id 加强，包含 foveated sketch、receptor profile、compound signature，避免苹果/香蕉只被最近教师短句覆盖。
- 内心画面改为从状态池视觉感受器 sample 重建，而不是原图预览或装饰椭圆。
- UI 修复想法云、审计曲线、tooltip、缓存版本参数等问题。
- 浏览器工作台地址曾使用：

```powershell
python -m apv3test.web_chat --host 127.0.0.1 --port 8774 --state-db data/phase20_web_demo.sqlite
```

页面：

```text
http://127.0.0.1:8774/
```

但新线程必须把这些当成“上一轮检查点”，不要直接当作当前事实。开始前先读代码和 rerun 当前必要测试。

---

## 12. 最新必要测试入口

在 `APV3.0test` 目录下优先跑这些，不要为了旧架构跑大量已废弃旧测试：

```powershell
python -m pytest tests\test_phase20_open_dialogue_foundation.py tests\test_phase20_1_teaching_paradigm.py tests\test_phase20_2_3_cooccurrence_memory.py -q
python -m pytest tests\test_phase20_4_workbench_repair.py tests\test_phase20_5a_runtime_workbench.py -q
python -m pytest tests\test_phase20_6_stage0_runtime_boundary.py tests\test_phase20_6_true_runtime_workbench_page.py tests\test_phase20_6_history_package_canvas.py -q
python -m pytest tests\test_phase21_object_centric_looking.py tests\test_phase19_9_zvec_recall_index.py -q
python scripts\red_line_check_v14.py --phase 20.6-stage0
node --check apv3test\web\static\phase20_6_workbench.js
```

如果改了 Python runtime，也至少做：

```powershell
python -m py_compile apv3test\web_chat.py apv3test\runtime\phase20_open_dialogue.py apv3test\runtime\phase20_6_runtime.py apv3test\runtime\phase20_6_memory.py
```

---

## 13. 当前用户最在意的问题

用户最近明确指出过这些问题，新线程必须理解并主动防止回归：

1. 视觉学习不能只记最近教师短句。苹果教成苹果、香蕉教成香蕉后，再看苹果不能变成香蕉。学习必须依赖视觉 SA 差异与共现，而不是全局最近答案。
2. 内心画面必须从状态池视觉感受器采样重建。视焦点附近应像素级更清晰，越远越模糊/采样稀疏，并体现形状、纹理、颜色、亮度、边缘等通道。
3. 识别流程不能第一 tick 就写答案。视觉 unresolved 时应先观察、移动焦点、多 tick 累积，再根据召回与行动竞争写草稿。
4. 工作台必须中文友好，不能满屏英文 id。必要 id 可放审计细节，主视图要显示可理解中文。
5. 主动停、继续观察、请求教师、写草稿、提交回复都应是行动竞争结果。
6. 审计曲线要有每 tick 数值、tooltip、多条线，而不是装饰性直线。
7. 想法云要随 tick 变化，颜色/饱和度/大小/位置表达实能量、虚能量和强度，文本不能溢出。
8. TTS 要尊重本地可用音色。关于 “xiaoyi”：曾发现 SNS 里有 `outputs/stage05_voice_samples/girl_xiaoyi_childlike_edge.mp3`，但这只是 Edge TTS `zh-CN-XiaoyiNeural` 的本地样本，不等于 Windows 本地实时 SAPI 音色。不要假装能用 xiaoyi 朗读任意回复，除非实际检测到本机实时 TTS 引擎可调用。
9. 不要为了前端好看写假逻辑。先修底层 RuntimeTickEvent，再让 UI 跟着真实数据走。

---

## 14. 如何审查一个方案是否 AP-native

任何新功能落地前，逐条回答：

```text
1. 它是否以来源明确的 SA / evidence packet 进入 AP？
2. 它是否只通过 RecallCandidate -> ActionCandidate -> action_competition -> DraftGrid/actuator 离开 AP？
3. 如果影响文字，是否能说明当前状态、慢记忆、草稿框、教师来源分别贡献了什么？
4. 如果影响置信/奖惩，是否有 source-aware eligibility 和 support update？
5. 整个效果能否由 RuntimeTickEvent + memory delta 回放？
6. 删除外部缓存或重建索引后，AP 的“真相”是否仍在 AP 记忆中？
```

有任何一个答案是否定，就还不是 AP-native。

---

## 15. 工作报告模板

每次完成一个阶段，请按这个结构向用户汇报：

```text
结论：
- 做了什么，是否达到本阶段目标。

设计/审查：
- 采用了哪个设计文档/errata。
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

## 16. 如果用户要求继续当前 APV3 工作

默认优先级：

1. 先确认 `APV3.0test` 当前代码状态、测试状态、红线状态。
2. 再检查 Phase20.6 runtime 是否仍严格没有投影 tick、整图识别、教学硬命中、预生成回复路径。
3. 优先修底层：视觉 SA 区分、foveated samples、状态池内心重建、多 tick 观察、行动竞争、教学绑定、慢记忆。
4. 然后修 UI：中文友好、真实 tick 回放、审计曲线、想法云、历史回放、记忆包、画布、TTS。
5. 每一步都要有 targeted tests，不要跑已经废弃架构的大量旧测试。

你要特别记住：银子老师要的是“真正的 AP 机制”，不是看起来像 AP 的页面。页面只是窗口，AP 的底层 tick、状态池、召回、行动竞争、草稿框、奖惩和记忆才是本体。

