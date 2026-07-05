# Phase20.8i C* 回灌 StatePool 虚能量最终报告

日期: 2026-06-27

## 1. 本阶段目标

Phase20.8h 已经把 C* 做成统一最小误差审计 packet，但它仍主要停留在 tick 回放与审计字段中。Phase20.8i 的目标是让 C* 整合结果真正进入 StatePool：

```text
B/C/C* 整合
  -> 预测/归因方向的 target SA slots
  -> StatePoolItem.V += virtual_energy
  -> StatePoolItem.P = R - V
  -> gain_ledger.replay += delta
  -> state_pool_top / tick trace 可审计
```

本阶段明确不做回复捷径、不新增答案表、不引入关键词/正则路由、不调用 student-side LLM，也不把外部资产伪装成内心画面能力。

## 2. 设计与审查

设计稿:

- `docs/Design_Phase20_8i_CStarStatePoolVirtualFeedback_20260627.md`

核心约束:

1. C* 只能回灌 SA/occurrence 粒度的虚能量，不直接写 `reply_text`。
2. forward prediction 使用已有 `memory_prediction` SA 表达后继预测。
3. backward/current 使用当前 observation 的 text SA 接收解释/归因方向的虚能量。
4. `gain_ledger.replay` 必须记录这次回灌来源。
5. Stage0 仍保持无写入边界。

落地自审发现 structural B 的预测字符如果被机械平均，单个 occurrence 的 `V` 会被摊薄到 `state_pool_top` 之外。已按 AP 的 per-occurrence 能量语义补充设计：有把握的 B/C/C* 匹配应在 leading prediction window 留下可见的虚能量痕迹，而不是只在数学上存在。

## 3. 落地内容

修改文件:

- `apv3test/runtime/phase20_7/runtime.py`
- `runtime/cognitive/state_pool/state_pool.py`
- `tests/test_phase20_8i_cstar_statepool_virtual_feedback.py`
- `docs/Design_Phase20_8i_CStarStatePoolVirtualFeedback_20260627.md`

关键实现:

1. 新增 `PHASE20_8I_CSTAR_STATEPOOL_FEEDBACK_ID`。
2. 新增 `_apply_cstar_statepool_feedback(...)`，统一处理 exact B0、structural B、weak/unknown tick 的 C* 回灌。
3. 新增 `_inject_virtual_energy(...)`，只更新 `V/A/P/gain_ledger.replay/metadata`，不创建回复候选。
4. `_tick_event(...)` 在生成 `state_pool_top` 前调用 C* 回灌，使快照能看到真实影响。
5. `StatePool.snapshot_top(...)` 排序纳入 `V` 和 `abs(P)`，符合状态池由 R/V/A/P 共同影响注意显著性的白皮书要求。
6. forward prediction 的 leading occurrence 使用由 `b_support` 调制的显著性下限，避免预测能量被字符平均摊薄到不可审计。

## 4. 严谨验收

语法检查:

```powershell
python -m py_compile runtime\cognitive\state_pool\state_pool.py apv3test\runtime\phase20_7\runtime.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py
```

结果: PASS

专项 + Stage3 相关回归:

```powershell
python -m pytest tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_7_stage3_structural_bccstar.py -q
```

结果: `8 passed`

Phase20.8 相关回归:

```powershell
python -m pytest tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py -q
```

结果: `16 passed`

Phase20.7/20.8 指定阶段链:

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py -q
```

结果: `72 passed`

红线扫描:

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|enumerate_objects_in_image" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_8i_cstar_statepool_virtual_feedback.py -g "*.py"
```

结果: 无命中。

## 5. 本阶段可以证明什么

1. structural B tick 的 C* forward prediction 会进入 `memory_prediction` SA，并在 `state_pool_top` 中表现出 `V > 0` 与 `gain_ledger.replay > 0`。
2. exact B0 tick 也会产生 `memory_prediction` 的虚能量回灌，但不通过 C* 直接写回复。
3. unknown/weak tick 不制造 fake B，也不制造 reply candidate，只给当前 observation text SA 回灌解释方向的低量 `V`。
4. Stage0 仍没有 C* StatePool 回灌，运行边界保持。
5. C* feedback 审计字段 `cstar_statepool_feedback` 可以解释本 tick 写入了哪些 SA、每个 SA 的 `V/P` 如何变化。

## 6. 仍不能声明什么

1. 不能声明完整持久 StatePool 已跨 turn/session 生效。本阶段仍主要证明本轮 runtime 内的真实回灌。
2. 不能声明 L1/L2/L3 在线嵌入已经实现。
3. 不能声明六阶段学习协议已经成为 runtime 状态机。
4. 不能声明所有 B/C/C* 来源已经完全是唯一心脏。
5. 不能声明视觉 object-centric 想象、数学列竖式、完整范式自学习已经完成。

## 7. 下一步建议

Phase20.8j 应继续把 C* 回灌从“本 tick 可审计”推进到“后继 tick 可用”：

1. 让 StatePool 的 `V/P/A` 回灌结果真实参与下一 tick 的候选竞争与注意转移。
2. 将回灌后的 SA 与 SSP occurrence/edge 的衰减、重复、时空位置统一起来。
3. 继续把残余 helper 收束到统一 ExperienceFlow/SSP query，不新增答案模块。
4. 验收重点从“能看到 V”升级为“V 会改变下一 tick 的 B/C/C* 与行动竞争”。

