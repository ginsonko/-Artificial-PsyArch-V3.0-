# Phase20.8j C* Carryover 影响后继 tick 最终报告

日期: 2026-06-27

## 1. 本阶段目标

Phase20.8i 已经让 C* 最小误差整合结果真实回灌到 StatePool 的
`V/P/A/gain_ledger.replay`。Phase20.8j 继续推进：让上一 tick 的 C* 回灌不只在
本 tick 审计中可见，而是能在后继 tick 里参与认知循环。

目标链条：

```text
tick t: C* -> StatePool.V/P/replay
tick t+1:
  StatePool carryover
  -> B support bias
  -> C_forward / C_backward carryover rows
  -> C* min-error integration
  -> action competition drive modulation
```

## 2. 设计与审查

设计稿：

- `docs/Design_Phase20_8j_CStarCarryoverNextTickInfluence_20260627.md`

核心约束：

1. carryover 只读 StatePool 中已有的 C* 回灌痕迹。
2. carryover 不生成答案、不写 `reply_text`、不创建 fake B。
3. carryover 可以调制已有经验候选的支持度，但不能凭空生成候选。
4. carryover 只作为 C_forward/C_backward 和 action competition 的场效应增补。
5. every-tick 默认预测/归因循环必须保留，carryover 不能覆盖基础循环。

自审修正：

初次落地后，宽回归发现 weak tick 中 carryover 的 C_backward 会让 Phase20.8g 默认
`unified_candidate_statistics` cause slot 被覆盖。已修正 `complete_every_tick_cognitive_cycle(...)`：
默认 forward/backward 行始终补齐，carryover 只增补，不替代 AP 的每 tick 基础循环。

## 3. 落地内容

修改文件：

- `apv3test/runtime/phase20_7/runtime.py`
- `apv3test/runtime/phase20_7/cognitive_cycle.py`
- `tests/test_phase20_8j_cstar_carryover_next_tick_influence.py`
- `docs/Design_Phase20_8j_CStarCarryoverNextTickInfluence_20260627.md`

关键实现：

1. 新增 `PHASE20_8J_CSTAR_CARRYOVER_ID`。
2. `_inject_virtual_energy(...)` 写入 `cstar_feedback_tick`、`cstar_feedback_slot_kind`、
   `cstar_feedback_virtual_energy_delta`，让后继 tick 能区分来源。
3. 新增 `_cstar_statepool_carryover(...)`，只读取 `cstar_feedback_tick < current_tick`
   的 StatePool SA，避免同 tick 自我放大。
4. 新增 `_statepool_observation_support_bias(...)`，让观察 tick 后留下的 V/P/replay
   小幅调制 exact/structural B 的 support。
5. 新增 `_cstar_carryover_c_forward(...)` 与 `_cstar_carryover_c_backward(...)`，
   将上一 tick 的预测/压力痕迹接入当前 tick 的 C 过程。
6. 新增 `_apply_cstar_carryover_to_competition(...)`，让 carryover 调制行动竞争 drive。
7. `complete_every_tick_cognitive_cycle(...)` 改为默认 B/C/C* 行始终补齐，carryover 只增补。

## 4. 严谨验收

语法检查：

```powershell
python -m py_compile apv3test\runtime\phase20_7\runtime.py apv3test\runtime\phase20_7\cognitive_cycle.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py
```

结果：PASS

20.8j 专项 + 相邻回归：

```powershell
python -m pytest tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8h_unified_cstar_min_error_integration.py -q
```

结果：`12 passed`

8g 覆盖问题修复回归：

```powershell
python -m pytest tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py -q
```

结果：`7 passed`

完整 Phase20.8 回归：

```powershell
python -m pytest tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py -q
```

结果：`28 passed`

Phase20.7/20.8 指定阶段链：

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py -q
```

结果：`76 passed`

红线扫描：

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|enumerate_objects_in_image" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_8j_cstar_carryover_next_tick_influence.py -g "*.py"
```

结果：无命中。

## 5. 本阶段可以证明什么

1. C* 回灌到 StatePool 的 `V/P/replay` 后，后继 tick 能读到这份 carryover。
2. observation tick 留下的 V/P/replay 会以 `statepool_cstar_observation_bias`
   进入 exact/structural B 的 support terms。
3. 预测 SA 的 carryover 会在后继 tick 形成
   `statepool_virtual_prediction_carryover` C_forward 行。
4. 未中和压力和预测残留会在后继 tick 形成
   `statepool_virtual_pressure_carryover` C_backward 行。
5. 后继 tick 的 action competition 会出现可审计的
   `cstar_carryover_drive_delta`。
6. unknown weak tick 仍不创建 fake B，不创建 reply candidate。
7. Stage0 仍保持无 C* completion/carryover 的边界。

## 6. 仍不能声明什么

1. 不能声明 StatePool 已完整跨 turn/session 持久化。
2. 不能声明 L1/L2/L3 在线嵌入已经实现。
3. 不能声明六阶段学习协议已经成为 runtime 状态机。
4. 不能声明所有 B/C/C* 来源已经完全收束为唯一心脏。
5. 不能声明视觉 object-centric 想象、数学列竖式、完整范式自学习已经完成。

## 7. 下一步建议

Phase20.8k 建议继续把 carryover 从“runtime 内后继 tick 调制”推进到“SSP occurrence/edge
层面的短期结构流演化”：

1. 将 StatePool carryover 与 SSP occurrence/edge 的时序、空间、重复关系统一。
2. 让 carryover 不只调制 support，还能影响注意焦点的下一步移动。
3. 将 idle_think 的叙事续写进一步收束到同一套 C_forward successor bias，而不是单独 helper。
4. 继续保持红线：不新增答案模块、不做关键词路由、不引入隐藏求解器。

