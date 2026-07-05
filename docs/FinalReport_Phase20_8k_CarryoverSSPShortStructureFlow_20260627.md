# Phase20.8k Carryover 下沉 SSP 短期结构流最终报告

日期: 2026-06-27

## 1. 本阶段目标

Phase20.8j 已证明 C* 回灌到 StatePool 的 `V/P/replay` 可以影响后继 tick 的
B/C/C* 与 action competition。Phase20.8k 继续把这条后继效应下沉到 SSP /
ExperienceFlow 的 occurrence/edge 层，让它成为可回放、可追溯、可被 idle_think
沿边继续的短期结构流。

目标链条：

```text
tick t: C* -> StatePool.V/P/replay
tick t+1: carryover -> B/C/C*/action modulation
tick t+1: carryover -> cognitive occurrence + short_structure_next edge
tick t+2: idle_think / later tick can see prior short_structure_flow
```

## 2. 设计与审查

设计稿：

- `docs/Design_Phase20_8k_CarryoverSSPShortStructureFlow_20260627.md`

核心约束：

1. 不新增数据库表，不新增答案表，不新增关键词/正则路由。
2. 不让 SSP flow 直接决定回复内容。
3. occurrence/edge 是已有 AP 基础实体，可以承载短期结构池的线性、时序、预测、归因关系。
4. carryover flow 的能量来自 StatePool 的 `V/P/replay`，不伪装成外部实能量。
5. idle_think 的叙事化想法必须写入短期结构流，而不是只写 UI 文本或 payload。

落地自审结论：

- `cstar_carryover_flow` 只在已有 carryover active 时写入。
- unknown weak tick 可以写短期结构流，但仍不能产生 fake B。
- idle_think 的叙事 flow 是 private thought，不进入 `reply_text`。
- 注意焦点影响本阶段先体现为 idle 阶段 action competition 的 visual/think drive bias；还不是完整视觉坐标级 object-centric 注意轨迹学习。

## 3. 落地内容

修改文件：

- `apv3test/runtime/phase20_7/runtime.py`
- `tests/test_phase20_8k_carryover_ssp_short_structure_flow.py`
- `docs/Design_Phase20_8k_CarryoverSSPShortStructureFlow_20260627.md`

关键实现：

1. 新增 `PHASE20_8K_CARRYOVER_SSP_FLOW_ID`。
2. 新增 `_write_cstar_carryover_structure_flow(...)`，把 carryover top slots 写为 cognitive occurrence，并用 `cstar_carryover_to_short_flow` edge 连到 flow occurrence。
3. 新增 `_write_short_structure_flow_occurrence(...)`，统一写 `short_structure_flow::*` occurrence，并与上一条 flow 写 `short_structure_next` edge。
4. 新增 `_latest_short_structure_flow_occurrence(...)`，让后继 tick 可以追溯最近短期结构流。
5. 新增 `_short_structure_flow_attention_bias(...)`，用最近 flow 调制 idle 阶段 visual/think drive。
6. `_tick_event(...)` 接收 `conn` 后，在同一事务中写入 `cstar_carryover_flow`，并投影到 `ssp_active_summary`。
7. idle_think 叙事写入 `short_structure_flow::idle::*` occurrence，不再只是 feelings/payload。

## 4. 严谨验收

语法检查：

```powershell
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py
```

结果：PASS

20.8k 专项 + 相邻回归：

```powershell
python -m pytest tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py -q
```

结果：`11 passed`

完整 Phase20.8 回归：

```powershell
python -m pytest tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py -q
```

结果：`32 passed`

Phase20.7/20.8 指定阶段链：

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py -q
```

结果：`80 passed`

红线扫描：

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|enumerate_objects_in_image" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_8k_carryover_ssp_short_structure_flow.py -g "*.py"
```

结果：无命中。

## 5. 本阶段可以证明什么

1. C* carryover 可以写入 SSP/ExperienceFlow 的 cognitive occurrence。
2. carryover source occurrence 会通过 `cstar_carryover_to_short_flow` edge 连到短期结构流 occurrence。
3. 连续后继 tick 会形成 `short_structure_next` edge。
4. idle_think 的叙事想法会写入 `short_structure_flow::idle::*` occurrence。
5. 重复 idle_think 会沿上一条 idle flow 形成新的 `short_structure_next`。
6. 最近短期结构流可以通过 `short_structure_flow_attention_bias` 调制 idle 阶段的 visual/think drive。
7. unknown weak tick 仍不创建 fake B，不创建 reply candidate。
8. Stage0 仍没有 carryover SSP flow。

## 6. 仍不能声明什么

1. 不能声明完整持久 StatePool 已跨 turn/session 生效。
2. 不能声明 L1/L2/L3 在线嵌入已经实现。
3. 不能声明六阶段学习协议已经成为 runtime 状态机。
4. 不能声明所有 B/C/C* 来源已经完全收束为唯一心脏。
5. 不能声明视觉 object-centric 想象或视觉坐标级注意学习已经完成。
6. 不能声明数学列竖式或完整范式自学习已经完成。

## 7. 下一步建议

Phase20.8l 建议继续把短期结构流接入统一 ExperienceFlow query：

1. 让 `short_structure_next` 不只是写入，而是真正参与后继 B/C/C* candidate 生成。
2. 将 idle_think 当前的 `_successor_for_unclosed(...)` helper 收束到统一 ExperienceFlow query。
3. 将 visual idle focus 的 drive bias 继续细化为视觉坐标级的 attention/fixation 选择影响。
4. 保持红线：不新增答案模块、不做关键词路由、不引入隐藏求解器。

