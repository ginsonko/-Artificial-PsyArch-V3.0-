# Phase20.8m 未闭合 successor 收束统一 ExperienceFlow Query 最终报告

日期: 2026-06-27

## 1. 本阶段目标

Phase20.8l 已经让 `short_structure_next` 接入统一 ExperienceFlow query，并进入后继
C_backward / C* candidate statistics。Phase20.8m 继续收束 idle_think：
`_successor_for_unclosed(...)` 不再只看 alignment/input_signature，而是从统一
ExperienceFlow / UnifiedCandidate 中竞争出 successor，使未闭合感驱动的叙事续写
从同一套 AP 信息流中长出来。

## 2. 设计与审查

设计稿：

- `docs/Design_Phase20_8m_UnclosedSuccessorUnifiedExperienceFlow_20260627.md`

核心约束：

1. 不新增数据库表，不新增答案表，不新增关键词/正则路由。
2. idle successor 只影响 private thought 的叙事续写，不直接写 `reply_text`。
3. alignment、recent flow、short_structure_flow_next 都只是候选证据，不能绕过 AP 主流程。
4. 未闭合感可以沿经验后继继续想，也可以沿短期结构流继续想；二者用 support 竞争。
5. unknown / weak 路径不能 fake B。

落地自审修正：

初次试跑发现，如果 idle successor 无限制读取所有 `short_structure_next`，会把普通
C* carryover 的内部 SA 标签拿来当叙事文本。已修正为：idle successor 只沿
`private_thought` / idle narrative 类短期结构流续写。普通 carryover 仍可进入 B/C/C*
候选统计，但不直接变成叙事内容。

## 3. 落地内容

修改文件：

- `apv3test/runtime/phase20_7/runtime.py`
- `tests/test_phase20_8m_unclosed_successor_unified_experience_flow.py`
- `docs/Design_Phase20_8m_UnclosedSuccessorUnifiedExperienceFlow_20260627.md`

关键实现：

1. `_successor_for_unclosed(...)` 同时收集：
   - alignment/input_signature 产生的 `UnifiedExperienceCandidate`
   - recent ExperienceFlow 中可驱动 idle successor 的 flow candidate
2. 新增 `_flow_candidate_can_drive_idle_successor(...)`，过滤非 private thought 的普通 carryover。
3. 新增 `_successor_text_from_flow_candidate(...)`，从统一 flow candidate 中读取 target/narrative/text。
4. `idle_successor_continuation` C_forward 增加 `source_candidate_id`、`source_kind`、
   `support_formula`、`cause_slots`、`writes_answer_directly=False`。
5. alignment successor 保留，保证已有教学路径不被破坏；flow successor 进入同一竞争。

## 4. 严谨验收

语法检查：

```powershell
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py
```

结果：PASS

20.8m 专项 + 相邻回归：

```powershell
python -m pytest tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_7_stage4_unclosed_idle.py -q
```

结果：`17 passed`

完整 Phase20.8 回归：

```powershell
python -m pytest tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py -q
```

结果：`40 passed`

Phase20.7/20.8 指定阶段链：

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py -q
```

结果：`88 passed`

红线扫描：

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|enumerate_objects_in_image" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py -g "*.py"
```

结果：无命中。

## 5. 本阶段可以证明什么

1. `_successor_for_unclosed(...)` 已经不再只依赖 alignment/input_signature。
2. idle successor 可以由 `short_structure_flow_next` 统一 flow candidate 驱动。
3. alignment successor 仍可通过统一候选竞争驱动 idle 续写。
4. idle C_forward 的 `idle_successor_continuation` 能审计 successor 来源、support、cause slots。
5. idle successor 只驱动 private thought，不写 `reply_text`。
6. unknown / weak 路径不创建 fake B。
7. Stage0 仍无 idle successor query。

## 6. 仍不能声明什么

1. 不能声明完整持久 StatePool 已跨 turn/session 生效。
2. 不能声明 L1/L2/L3 在线嵌入已经实现。
3. 不能声明六阶段学习协议已经成为 runtime 状态机。
4. 不能声明所有 B/C/C* 来源已经完全收束为唯一心脏。
5. 不能声明完整范式自学习、数学列竖式、视觉 object-centric 想象已经完成。

## 7. 下一步建议

Phase20.8n 建议继续把“统一 ExperienceFlow successor”推进到主动询问和 teacher request：

1. request_teacher 不再只是固定低把握动作，而是由 C*/unclosed/short_structure_flow 的未闭合压力驱动。
2. 主动询问内容仍不能模板化成答案路径，应由 DraftGrid + learned expression/paradigm 逐步承载。
3. 继续把 response generation 从硬编码文本向已学表达范式迁移。
4. 保持红线：不新增答案表、不做关键词路由、不引入隐藏求解器。

