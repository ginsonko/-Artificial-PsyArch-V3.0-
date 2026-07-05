# Phase20.8r 最终报告：当前认知指向绑定到表达范式

日期：2026-06-27

## 1. 完成内容

本轮完成 Phase20.8r：把 `request_teacher / maintain_unclosed` 的表达选择与 AP 当前内部认知指向绑定。

代码改动集中在 `apv3test/runtime/phase20_7/runtime.py`：

- 新增 `PHASE20_8R_CURRENT_REFERENT_BINDING_ID`。
- `_teacher_request_drive_context(...)` 生成 `current_referent`，来源于 observation、unclosed、short_structure_flow、C* carryover。
- `_record_teacher_feedback(...)` 在 targeted expression feedback 的 alignment payload 中保存 `expression_referent`。
- `_select_request_expression(...)` 将 `current_referent` 传入 teacher/draft expression candidates、片段组合和 trace。
- `_teacher_expression_candidates(...)` / `_draft_expression_candidates(...)` 用 referent match 调制表达候选支持度。
- `_compose_expression_fragments(...)` 在有 active referent 且候选足够时优先组合同 referent 表达片段。
- 新增 `_current_referent_summary(...)`、`_expression_referent_match(...)` 等辅助函数，但没有新增数据库表和回复捷径。

新增测试：

- `tests/test_phase20_8r_current_referent_expression_binding.py`

新增设计文档：

- `docs/Design_Phase20_8r_CurrentReferentExpressionBinding_20260627.md`

## 2. 可以证明什么

本轮可以证明：

1. 视觉未知输入会形成 `current_referent.referent_kind = visual_focus`，且模态为 `vision`。
2. 文本未知输入会形成 `current_referent.referent_kind = text_focus`，且模态为 `text`。
3. 当视觉表达经验和文本表达经验同时存在时，当前 referent 会参与表达候选竞争，视觉输入选择视觉指向下学到的表达，文本输入选择文本指向下学到的表达。
4. 同视觉 referent 下至少两条 targeted expression feedback 可被 DraftGrid 片段组合复用。
5. 没有表达经验时，系统只保留 referent trace，仍使用先天最小表达，不伪造“这张图/这个地方”等成熟表达。
6. 表达经验仍不进入普通答案 B0；`request_expression_selection` 明确标记 `creates_answer_candidate = False` 和 `writes_answer_directly = False`。

## 3. 验收结果

命令与结果：

```powershell
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_8r_current_referent_expression_binding.py
```

通过。

```powershell
python -m pytest tests\test_phase20_8r_current_referent_expression_binding.py -q
```

结果：`3 passed in 2.02s`

```powershell
python -m pytest tests\test_phase20_8r_current_referent_expression_binding.py tests\test_phase20_8q_draftgrid_expression_fragment_composition.py tests\test_phase20_8p_expression_paradigm_slots.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_7_stage4_unclosed_idle.py -q
```

结果：`26 passed in 9.95s`

```powershell
python -m pytest tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8p_expression_paradigm_slots.py tests\test_phase20_8q_draftgrid_expression_fragment_composition.py tests\test_phase20_8r_current_referent_expression_binding.py -q
```

结果：`57 passed in 21.13s`

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8p_expression_paradigm_slots.py tests\test_phase20_8q_draftgrid_expression_fragment_composition.py tests\test_phase20_8r_current_referent_expression_binding.py -q
```

结果：`105 passed in 44.52s`

手动红线扫描：

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|student-side LLM|enumerate_objects_in_image|regex|keyword_route|candidate_text" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_8r_current_referent_expression_binding.py -g "*.py"
```

结果：无命中。

脚本级 release demo：

```powershell
python scripts\verify_phase20_7_release_demo.py
```

结果：`OK: Phase20.7 release demo package verified`

说明：`scripts\red_line_check_v14.py --phase 20.8r` 尚未登记 20.8r phase 名；`--phase 20.7-stage8` 的旧 deliverable 规则仍要求历史 token `_inject_cstar_virtuals`，与当前 20.8 的 C* 回灌函数命名不一致。本轮没有为了脚本旧 token 新增假函数。

## 4. 自审

符合 AP 哲学的点：

- 当前指向不是新模块，而是 observation / unclosed / short_structure_flow / C* 的摘要。
- referent 只调制表达，不生成答案。
- 视觉锚点“这张图片”不再被当成文本模态，以免视觉表达和文本表达错误互相污染。
- 保留冷启动不成熟：没有表达经验时只 trace，不装作会精准指代。

风险与边界：

- 当前实现已经支持 visual/text referent；audio referent 的 trace 入口保留，但专门的音频表达回归测试还没有补。
- `current_referent` 仍是摘要级，不是完整 persistent StatePool 对象。
- 这不等于完整范式自学习，也不等于 L1/L2/L3 在线嵌入或六阶段 runtime 已完成。

## 5. 仍不能声明

仍不能声明：

- 完整 L1/L2/L3 在线嵌入已经完成。
- 六阶段学习协议已经在 runtime 全量落地。
- 完整范式自学习已经完成。
- 数学列竖式能力已经完成。
- object-centric 视觉想象已经完成。
- Phase21 视觉教学泛化闭环已经完成。

