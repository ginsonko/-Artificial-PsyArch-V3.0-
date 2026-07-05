# Phase20.8p 最终报告：表达范式槽位从经验流中涌现

日期：2026-06-27

## 1. 本阶段目标

Phase20.8p 继续推进 Phase20.8o：8o 已经能让 request_teacher / maintain_unclosed 的表达从 targeted teacher feedback 与 DraftGrid commit 中选择；8p 进一步让表达选择带上“范式槽位”。

这里的范式槽位不是新数据库实体，也不是模板表，而是从 AP 自己当时的认知状态派生出来的可重建审计结构。它来自：

- `intent`
- `low_grasp`
- `unclosed_pull`
- `short_structure_flow_support`
- `cstar_pressure`
- target DraftGrid event 的 `request_expression_selection`

## 2. 设计审查

### 设计原则

- 不新增数据库表。
- 不新增关键词分类器。
- 不新增答案表或回复模板表。
- 不从用户文本中抽关键词决定话术。
- 表达范式只来自 AP 自己曾经的表达行动与教师反馈。
- 带 `expression_role` 的表达经验仍被普通 exact B0 / structural B / visual recall 排除。

### 数学形式

对 targeted expression feedback：

```text
T = target_event.payload.request_expression_selection.teacher_request_drive_context
slot = f(intent, low_grasp, unclosed_pull, short_flow, cstar_pressure)
```

槽位派生：

```text
if intent == maintain_unclosed:
  slot = unclosed_maintenance
else if unclosed_pull >= 0.35:
  slot = unclosed_request
else if short_flow >= 0.50:
  slot = flow_continuation_request
else if low_grasp >= 0.70 and cstar_pressure >= 0.50:
  slot = low_grasp_pressure_request
else if low_grasp >= 0.70:
  slot = low_grasp_request
else:
  slot = general_request
```

候选表达支持：

```text
support = unified_support(...)
        + 0.18 * exact_slot_match
        + 0.06 * family_slot_match
```

这让同样是“请求教学”的表达，也能根据当前 AP 内部状态选择更贴近的经验表达。

## 3. 落地内容

代码：

- `apv3test/runtime/phase20_7/runtime.py`

新增：

- `PHASE20_8P_EXPRESSION_PARADIGM_ID`
- `_expression_paradigm_slot(...)`
- `_expression_paradigm_match(...)`
- `_context_from_expression_trace(...)`
- `_expression_target_trace_for_event(...)`

扩展：

- `_record_teacher_feedback(...)` 在 targeted expression feedback 时写入：
  - `expression_target_trace`
  - `expression_paradigm_slot`
  - `expression_paradigm_formula_id`
- `_select_request_expression(...)` 计算 `current_paradigm_slot`。
- `_teacher_expression_candidates(...)` 与 `_draft_expression_candidates(...)` 使用当前 slot 与候选 slot 做适配加权。
- `request_expression_selection` tick trace 增加：
  - `current_paradigm_slot`
  - `selected_paradigm_slot`
  - `paradigm_formula_id`
  - `paradigm_match`

测试：

- `tests/test_phase20_8p_expression_paradigm_slots.py`

覆盖：

- targeted expression feedback 会保存 `expression_paradigm_slot`。
- 多个 request 表达候选竞争时，当前 slot 匹配的表达胜出。
- maintain_unclosed 使用 `unclosed_maintenance` 槽位。

## 4. 严谨验收

语法检查：

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_8p_expression_paradigm_slots.py
PASS
```

8p 专项：

```text
python -m pytest tests\test_phase20_8p_expression_paradigm_slots.py -q
3 passed
```

相邻链：

```text
python -m pytest tests\test_phase20_8p_expression_paradigm_slots.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_7_stage4_unclosed_idle.py -q
20 passed
```

Phase20.8 全链：

```text
python -m pytest tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8p_expression_paradigm_slots.py -q
51 passed
```

Phase20.7 + Phase20.8 底座链：

```text
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8p_expression_paradigm_slots.py -q
99 passed
```

红线扫描：

```text
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|enumerate_objects_in_image|regex|keyword_route" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_8p_expression_paradigm_slots.py -g "*.py"
No hits
```

## 5. 可以证明什么

- targeted expression feedback 不只是保存一句表达，还会保存该表达对应的 AP 内部范式槽位。
- request_teacher 当前 slot 与候选 slot 匹配时，会提升该表达的竞争力。
- maintain_unclosed 使用独立的 `unclosed_maintenance` 槽位，不和 request_teacher 混用。
- 槽位来自 AP 内部认知流，不来自用户输入关键词。
- 没有新增数据库表；slot 是可重建的 event payload / tick trace 派生结构。
- 表达经验仍不会污染普通答案召回。

## 6. 仍不能声称什么

- 不能声称完整范式自学习已经完成；本阶段完成的是 request/maintain 表达范式槽位。
- 不能声称 AP 已经能自由生成任意表达；当前仍以经验选择与槽位适配为主。
- 不能声称 L1/L2/L3 在线嵌入、六阶段学习 runtime、数学列竖式、object-centric 视觉想象已经完成。
- 不能声称所有主动询问策略都已完备；本阶段只处理低把握/未闭合相关表达范式。

## 7. 下一步建议

Phase20.8q 应继续把表达范式从“选择一句完整表达”推进到 DraftGrid 结构组合：让 AP 能把已学表达拆成可复用片段，例如“我还不确定 / 你可以教我 / 我还在想 / 这个地方”，再由 DraftGrid 按当前认知压力、未闭合对象和短期结构流组合输出。重点仍然是 AP 经验流组合，不是模板表或关键词规则。
