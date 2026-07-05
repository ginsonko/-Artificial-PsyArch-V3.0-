# Phase20.8l short_structure_next 接入统一 ExperienceFlow Query 最终报告

日期: 2026-06-27

## 1. 本阶段目标

Phase20.8k 已经把 C* carryover 与 idle_think 叙事写入 SSP occurrence/edge，
并形成 `short_structure_next`。Phase20.8l 的目标是让这些短期结构流边不只可回放，
而是被统一 ExperienceFlow query 读到，进入后继 tick 的 B/C/C* candidate 统计。

目标链条：

```text
short_structure_flow occurrence + short_structure_next edge
  -> query_recent_experience_flow_candidates()
  -> ExperienceFlowCandidate(candidate_kind=short_structure_flow_next)
  -> UnifiedExperienceCandidate.audit_slot()
  -> C_backward cause_slots
  -> C* unified_candidate_statistics
```

## 2. 设计与审查

设计稿：

- `docs/Design_Phase20_8l_ShortStructureNextUnifiedQuery_20260627.md`

核心约束：

1. 不新增数据库表。
2. 不让短期结构流直接写 `reply_text`。
3. `short_structure_next` 只表达时序、预测、归因偏置，不是答案路径。
4. query 层只能把已有 occurrence/edge 转成候选证据，不能凭空创建 candidate。
5. unknown weak tick 可以看见 `short_structure_flow_next`，但不能生成 fake B 或 reply candidate。

审查修正：

旧 Phase20.8g/20.8h 的 unknown weak 验收要求 unified statistics 为空。Phase20.8l 后，
这个要求不再符合新理论目标，因为短期结构流已经是合法的非答案候选。已将旧验收升级为：

- `candidate_kinds` 可以为空，也可以只包含 `short_structure_flow_next`。
- `creates_candidate` 必须仍为 `False`。
- `b_candidates` 必须仍为空。
- C* / feedback 仍不能直接写答案。

## 3. 落地内容

修改文件：

- `apv3test/runtime/phase20_7/experience_flow.py`
- `apv3test/runtime/phase20_7/runtime.py`
- `tests/test_phase20_8l_short_structure_next_unified_query.py`
- `tests/test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py`
- `tests/test_phase20_8h_unified_cstar_min_error_integration.py`
- `docs/Design_Phase20_8l_ShortStructureNextUnifiedQuery_20260627.md`

关键实现：

1. `query_recent_experience_flow_candidates(...)` 追加 `_short_structure_next_candidates(...)`。
2. `_short_structure_next_candidates(...)` 从 `phase20_7_structure_edges` 读取
   `edge_type='short_structure_next'` 的边，并回连 src/dst occurrence、event、SA type。
3. 每条 `short_structure_next` 转成 `ExperienceFlowCandidate(candidate_kind='short_structure_flow_next')`。
4. 新增 `_short_structure_flow_query_c_backward(...)`，把统一 query 读到的短期结构流候选放入 C_backward cause slots。
5. C_backward 中同时包含 `unified_experience_flow_candidate` 和
   `UnifiedExperienceCandidate.audit_slot()`，使 C* 的 `unified_candidate_statistics`
   能看见 `short_structure_flow_next`。

## 4. 严谨验收

语法检查：

```powershell
python -m py_compile apv3test\runtime\phase20_7\experience_flow.py apv3test\runtime\phase20_7\runtime.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py
```

结果：PASS

20.8l 专项 + 相邻回归：

```powershell
python -m pytest tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py -q
```

结果：`12 passed`

8g/8h 语义升级回归：

```powershell
python -m pytest tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8l_short_structure_next_unified_query.py -q
```

结果：`11 passed`

完整 Phase20.8 回归：

```powershell
python -m pytest tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py -q
```

结果：`36 passed`

Phase20.7/20.8 指定阶段链：

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py -q
```

结果：`84 passed`

红线扫描：

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|enumerate_objects_in_image" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_8l_short_structure_next_unified_query.py -g "*.py"
```

结果：无命中。

## 5. 本阶段可以证明什么

1. `short_structure_next` 已经能被 `query_recent_experience_flow_candidates(...)` 读到。
2. `short_structure_next` 可以转成 `ExperienceFlowCandidate(candidate_kind='short_structure_flow_next')`。
3. 该候选能通过 `unified_candidate_from_flow(...)` 进入统一候选审计槽。
4. 后继 tick 的 C_backward 会包含 `short_structure_flow_query_recall`。
5. 后继 tick 的 C* `unified_candidate_statistics.candidate_kinds` 能看到 `short_structure_flow_next`。
6. unknown weak tick 可以看到短期结构流候选，但仍不创建 fake B。
7. Stage0 仍无 C_backward/C* completion。

## 6. 仍不能声明什么

1. 不能声明完整持久 StatePool 已跨 turn/session 生效。
2. 不能声明 L1/L2/L3 在线嵌入已经实现。
3. 不能声明六阶段学习协议已经成为 runtime 状态机。
4. 不能声明所有 B/C/C* 来源已经完全收束为唯一心脏。
5. 不能声明短期结构流已经能直接完成复杂范式自学习。
6. 不能声明视觉 object-centric 想象、视觉坐标级注意学习或数学列竖式已经完成。

## 7. 下一步建议

Phase20.8m 建议继续把 idle_think 的 `_successor_for_unclosed(...)` 收束到统一
ExperienceFlow query：

1. 让 unclosed successor 不再只查 alignment/input_signature，而是同等读取
   `short_structure_flow_next`。
2. 让 idle_think 的叙事续写优先沿统一候选的 C_forward successor bias 发展。
3. 保持 private thought 不进入 chat reply。
4. 继续保持红线：不新增答案模块、不做关键词路由、不引入隐藏求解器。

