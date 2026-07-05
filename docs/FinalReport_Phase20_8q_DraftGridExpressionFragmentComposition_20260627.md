# Phase20.8q 最终报告：DraftGrid 表达片段组合

日期：2026-06-27

## 1. 本阶段目标

Phase20.8q 在 Phase20.8p 的表达范式槽位基础上继续推进：AP 不再只能在 request_teacher / maintain_unclosed 时选择一句完整表达，而可以从已学表达经验中提取片段，并通过 DraftGrid 逐字符组合输出。

本阶段仍遵守 AP 白皮书边界：

- 不新增数据库表。
- 不新增模板表。
- 不新增关键词/正则路由。
- 不从用户输入文本抽关键词决定表达。
- 不把表达组合写入普通答案索引。
- 表达片段只来自已有 targeted expression feedback / DraftGrid 表达经验。

## 2. 设计审查

### 片段来源

片段来源于已有表达候选：

```text
teacher_feedback_expression
draft_grid_expression_memory
```

本阶段为了防止冷启动表达和普通 DraftGrid fallback 污染组合，真实组合只在至少两条同 intent、同范式槽位的 `teacher_feedback_expression` 存在时触发。

### 数学形式

当前范式槽位仍由 Phase20.8p 派生：

```text
current_slot = f(intent, low_grasp, unclosed_pull, short_flow, cstar_pressure)
```

片段来自表达文本本身的可观察边界：

```text
fragments(E_k) = split_by_observed_expression_boundary(E_k.text)
```

片段组合条件：

```text
source_kind == teacher_feedback_expression
candidate.paradigm_slot == current_slot
candidate.support >= 0.50
distinct_source_event_count >= 2
```

组合支持：

```text
support = avg(fragment.source_support) + 0.08
```

输出：

```text
output = join(selected_fragments)
```

组合结果仍进入 DraftGrid 逐字符写入；因为 DraftGrid 是二维草稿栏，UI 文本可能出现换行，这是草稿空间投影，不是直接字符串拼接器。

## 3. 落地内容

代码：

- `apv3test/runtime/phase20_7/runtime.py`

新增：

- `PHASE20_8Q_EXPRESSION_FRAGMENT_COMPOSITION_ID`
- `_compose_expression_fragments(...)`
- `_expression_fragments_from_text(...)`
- `_join_expression_fragments(...)`

扩展：

- `_select_request_expression(...)` 在整句选择前尝试片段组合。
- composition trace 写入 `request_expression_selection`：
  - `composition_formula_id`
  - `composition_kind`
  - `fragment_count`
  - `fragments`
  - `source_event_ids`
  - `selected_text`
  - `support_terms`

测试：

- `tests/test_phase20_8q_draftgrid_expression_fragment_composition.py`

覆盖：

- 两条同槽位 request_teacher 表达经验可组合成新表达。
- 只有一条表达候选时仍保持整句选择。
- maintain_unclosed 可组合自己的表达片段。

## 4. 严谨验收

语法检查：

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_8q_draftgrid_expression_fragment_composition.py
PASS
```

8q 专项：

```text
python -m pytest tests\test_phase20_8q_draftgrid_expression_fragment_composition.py -q
3 passed
```

相邻链：

```text
python -m pytest tests\test_phase20_8q_draftgrid_expression_fragment_composition.py tests\test_phase20_8p_expression_paradigm_slots.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_7_stage4_unclosed_idle.py -q
23 passed
```

Phase20.8 全链：

```text
python -m pytest tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8p_expression_paradigm_slots.py tests\test_phase20_8q_draftgrid_expression_fragment_composition.py -q
54 passed
```

Phase20.7 + Phase20.8 底座链：

```text
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8p_expression_paradigm_slots.py tests\test_phase20_8q_draftgrid_expression_fragment_composition.py -q
102 passed
```

红线扫描：

```text
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|enumerate_objects_in_image|regex|keyword_route" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_8q_draftgrid_expression_fragment_composition.py -g "*.py"
No hits
```

## 5. 可以证明什么

- request_teacher 可以从两条同槽位表达经验中组合片段，而不是只复用单句。
- maintain_unclosed 也可以组合自己的表达片段。
- 组合 trace 能显示片段、来源 event、source support、composition formula。
- 组合结果通过 DraftGrid 逐字符写入，不是直接回复捷径。
- 片段组合不会进入普通答案召回路径。
- 没有新增表、模板表、关键词路由或隐藏求解器。

## 6. 仍不能声称什么

- 不能声称完整范式自学习已经完成；本阶段只完成 request/maintain 表达的片段组合。
- 不能声称 AP 已能自由生成任意语言；当前仍依赖已学表达片段。
- 不能声称 L1/L2/L3 在线嵌入、六阶段学习 runtime、数学列竖式、object-centric 视觉想象已经完成。
- 不能声称所有 DraftGrid 组合都已达到自然语言流畅度；二维草稿栏换行仍会影响 UI 投影。

## 7. 下一步建议

Phase20.8r 应继续推进“表达片段组合”与“短期结构流 / 未闭合对象”的绑定：让片段不仅来自表达经验，还能引用当前未闭合对象、当前感觉来源、当前视觉/听觉/文本焦点的可审计摘要，例如“这个地方 / 这张图 / 刚才那个声音 / 我还没弄懂”。仍然必须从 RuntimeTickEvent / SSP / StatePool 中取证，不从用户输入关键词硬编码。
