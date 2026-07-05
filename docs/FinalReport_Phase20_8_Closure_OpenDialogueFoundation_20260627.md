# Phase20.8 闭合报告：开放对话底座认知心脏收束

日期：2026-06-27

## 1. 阶段目标

Phase20.8 的目标不是新增外部功能模块，而是把 Phase20.7 release demo 中仍显分散的路径逐步收束到 AP 白皮书要求的核心流程：

```text
每 tick 输入/闲时状态
-> StatePool / SSP / ExperienceFlow
-> B 当前认知
-> C_forward 预测
-> C_backward 归因
-> C* 最小误差整合
-> StatePool 虚能量回灌
-> SSP 短期结构流延续
-> 行动竞争 / DraftGrid / 表达学习
```

本阶段核心标准：不靠关键词、答案表、直接回复路线、隐藏求解器、视觉标签捷径或 UI 旁路。能用 AP 主流程解释的，都收回 AP 主流程。

## 2. 已完成链路

Phase20.8b：每 tick 认知循环补齐  
让外部输入、闲时 tick、视觉/听觉/文本路径都带上 B/C/C* 审计，不只在最终回复时看结果。

Phase20.8c：统一经验召回  
将 alignment、视觉 patch refs、文本结构召回纳入统一候选审计，开始减少局部 helper 的孤岛感。

Phase20.8d：短期结构流召回  
近期窗口、occurrence、edge、payload refs 进入统一 ExperienceFlow query。

Phase20.8e：统一候选层  
把 ExperienceRecallCandidate 和 ExperienceFlowCandidate 的审计字段拉齐，形成统一候选统计。

Phase20.8f：结构 B 接入统一候选  
`_find_structural_b(...)` 开始由统一候选驱动，不再只是局部文本相似 helper。

Phase20.8g：exact B0 与 weak B/C 接入统一统计  
exact B0 fallback 和默认 weak B/C 都进入候选审计。

Phase20.8h：C* 最小误差整合公式  
让 C* 不只是展示统计，而有统一的最小误差审计公式。

Phase20.8i：C* 回灌 StatePool  
C* 结果开始真实回灌 StatePool 的 V/P/replay，而不是只写 trace。

Phase20.8j：回灌影响后继 tick  
StatePool carryover 能影响后继 tick 的 B/C/C*、注意转移和行动竞争。

Phase20.8k：carryover 落成 SSP 短期结构流  
C* carryover 能写成 short_structure_flow occurrence/edge，连续 tick 可形成 `short_structure_next`。

Phase20.8l：short_structure_next 进入统一 query  
短期结构流不只是写入，而能参与后继 B/C/C* candidate 生成。

Phase20.8m：未闭合 successor 统一化  
闲时未闭合感驱动的叙事续写从统一 ExperienceFlow / UnifiedCandidate 竞争中产生。

Phase20.8n：request_teacher / maintain_unclosed 驱动统一化  
主动请求教学和维持未闭合不再只是固定低把握动作，而由 low_grasp、unclosed、short_structure_flow、C* 共同驱动。

Phase20.8o：表达来自经验流  
“我不懂 / 请教我 / 我还在想”这类表达开始从 targeted expression feedback 和 DraftGrid commit 中选择，不再只靠固定 fallback。

Phase20.8p：表达范式槽位  
表达候选按 AP 内部状态形成槽位，如 `low_grasp_request`、`unclosed_request`、`flow_continuation_request`、`unclosed_maintenance`。

Phase20.8q：DraftGrid 表达片段组合  
AP 能从多条已学表达经验中抽片段组合，形成新表达，但仍只用于 request/maintain 表达，不生成知识答案。

Phase20.8r：当前认知指向绑定表达  
表达经验与当前视觉/文本/未闭合等认知指向绑定，视觉未知和文本未知可按 referent 分流表达；无经验时只 trace，不伪造成熟指称。

## 3. 当前可以证明什么

1. Phase20.8 已把 B/C/C*、StatePool 回灌、SSP 短期结构流、未闭合闲时续写、主动请求教学、表达范式和表达片段组合收束到同一条 AP 信息流中。
2. C* 回灌不是纯展示字段，能影响后继 tick 的候选、注意/行动竞争和短期结构流。
3. 闲时思考可以沿未闭合对象和 short_structure_flow 续写，不再只是重复刷同一句。
4. 主动请求教学的驱动来自 AP 内部低把握、未闭合、短期结构流、C* 压力，不是固定脚本。
5. AP 可以学习“怎么表达自己不懂/还在想”，并能按内部范式槽位和当前 referent 组合表达。
6. 视觉输入、文本输入的未知状态可以通过 `current_referent` 在表达层分流，但这仍不是视觉分类答案路线。

## 4. 验收结果

编译：

```powershell
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_8r_current_referent_expression_binding.py
```

通过。

Phase20.8 全链：

```powershell
python -m pytest tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8p_expression_paradigm_slots.py tests\test_phase20_8q_draftgrid_expression_fragment_composition.py tests\test_phase20_8r_current_referent_expression_binding.py -q
```

结果：`57 passed in 21.13s`

Phase20.7 + Phase20.8 总链：

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8p_expression_paradigm_slots.py tests\test_phase20_8q_draftgrid_expression_fragment_composition.py tests\test_phase20_8r_current_referent_expression_binding.py -q
```

结果：`105 passed in 44.52s`

手动红线扫描：

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|student-side LLM|enumerate_objects_in_image|regex|keyword_route|candidate_text" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_8r_current_referent_expression_binding.py -g "*.py"
```

结果：无命中。

Release demo 脚本：

```powershell
python scripts\verify_phase20_7_release_demo.py
```

结果：`OK: Phase20.7 release demo package verified`

## 5. 红线与边界

本阶段没有引入：

- 关键词路由。
- regex 答案路线。
- answer table。
- taught answer 直接回复。
- hidden solver。
- student-side LLM。
- 视觉 label map。
- 原始图片资产直接渲染为内心画面。
- UI 旁路逻辑。

需要说明：`scripts\red_line_check_v14.py` 还没有登记 Phase20.8b-r，旧的 `20.7-stage8` 检查仍要求历史 token `_inject_cstar_virtuals`，与当前 C* 回灌函数命名不一致。本闭合报告以当前 105 个测试、手动红线扫描、release demo 脚本为验收依据。

## 6. 仍不能声明

Phase20.8 完成后，仍不能声明：

- 完整持久 StatePool 已经实现。
- L1/L2/L3 在线嵌入已完成。
- 六阶段学习协议 runtime 已全量完成。
- 完整范式自学习已完成。
- 数学列竖式和任意简单数学计算已完成。
- object-centric 视觉想象已完成。
- Phase21 视觉教学泛化闭环已完成。
- AP 已达到最终发布版全部能力。

## 7. 下一步

Phase20.8 可以作为“开放对话底座认知心脏收束”的当前闭合点。下一阶段最自然进入：

1. Phase20.9：把表达范式继续推进到更通用的范式自学习与六阶段 runtime 接口。
2. Phase21：视觉教学与泛化闭环，重点解决 object-centric 视觉证据、教师辅助视焦点、画板输入、视觉 patch/空间结构/clarity 与文本教学绑定。
3. 后续数学能力：在完全 AP 主流程下，用 DraftGrid、视焦点/注意焦点移动、后天范式学习和奖惩反馈发展列竖式与简单计算，而不是接 hidden solver。

