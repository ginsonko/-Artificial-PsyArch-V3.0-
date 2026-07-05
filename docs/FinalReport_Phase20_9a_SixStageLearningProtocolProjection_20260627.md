# Phase20.9a 最终报告：六阶段学习协议 Runtime 投影

日期：2026-06-27

## 1. 完成内容

本轮完成 Phase20.9a：在 `complete_every_tick_cognitive_cycle(...)` 中为每个非 stage0 的真实 tick 追加 `learning_protocol_projection`。

代码改动：

- `apv3test/runtime/phase20_7/cognitive_cycle.py`
  - 新增 `PHASE20_9A_LEARNING_PROTOCOL_PROJECTION_ID`。
  - 新增 `LEARNING_PROTOCOL_PHASES`。
  - 新增 `_with_learning_protocol_projection(...)`。
  - 新增 `_learning_protocol_projection(...)`。
  - 新增 `_teacher_signal(...)`、`_request_scaffold_signal(...)`、`_feedback_only_hint(...)`、`_cold_retest_hint(...)`。
  - 在 `complete_every_tick_cognitive_cycle(...)` 末尾追加投影到 `learning_deltas`。

新增测试：

- `tests/test_phase20_9a_learning_protocol_projection.py`

新增设计文档：

- `docs/Design_Phase20_9a_SixStageLearningProtocolProjection_20260627.md`

## 2. 可以证明什么

本轮可以证明：

1. 每个非 stage0 的核心 RuntimeTickEvent 都能获得 AP-native 学习协议投影。
2. 未知输入触发 `request_teacher` 时，学习态投影为 `weak_scaffold`，因为低把握/请求脚手架信号占优。
3. 教师反馈整合 tick 投影为 `strong_scaffold`，因为 teacher feedback / experience alignment 信号占优。
4. exact B0 在无当前教师输入下召回时投影为 `teacher_off`，但这只表示本 tick teacher absent + learned recall active，不等于全局能力成熟。
5. 视觉感受器观察 tick 投影为 `demonstrate`，因为 receptor / sensory action 信号占优。
6. stage0 仍保持边界，不被误补学习协议投影。
7. 投影字段明确 `projection_only=True`、`creates_reply_candidate=False`、`writes_answer_directly=False`。

## 3. 验收结果

编译与定向测试：

```powershell
python -m py_compile apv3test\runtime\phase20_7\cognitive_cycle.py tests\test_phase20_9a_learning_protocol_projection.py
python -m pytest tests\test_phase20_9a_learning_protocol_projection.py -q
```

结果：`5 passed in 1.95s`

相邻链：

```powershell
python -m pytest tests\test_phase20_9a_learning_protocol_projection.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8r_current_referent_expression_binding.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8b_every_tick_cognitive_cycle.py -q
```

结果：`23 passed in 7.65s`

Phase20.8 + 20.9a：

```powershell
python -m pytest tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8p_expression_paradigm_slots.py tests\test_phase20_8q_draftgrid_expression_fragment_composition.py tests\test_phase20_8r_current_referent_expression_binding.py tests\test_phase20_9a_learning_protocol_projection.py -q
```

结果：`62 passed in 20.57s`

Phase20.7 + Phase20.8 + Phase20.9a：

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8p_expression_paradigm_slots.py tests\test_phase20_8q_draftgrid_expression_fragment_composition.py tests\test_phase20_8r_current_referent_expression_binding.py tests\test_phase20_9a_learning_protocol_projection.py -q
```

结果：`110 passed in 43.79s`

手动红线扫描：

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|student-side LLM|enumerate_objects_in_image|regex|keyword_route|six_stage_complete|six_stage_learning_complete|online_embedding_converged|l1_l2_l3_complete" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_9a_learning_protocol_projection.py -g "*.py"
```

结果：无命中。

Release demo 验证：

```powershell
python scripts\verify_phase20_7_release_demo.py
```

结果：`OK: Phase20.7 release demo package verified`

## 4. 自审

符合 AP 哲学的点：

- 学习阶段不是外部课程状态机，而是由当前 tick 的 B/C/C*、感受器、行动竞争、教师反馈和未闭合信号投影出来。
- 不新增数据库表，不新增答案候选，不修改回复路线。
- 不用关键词或 regex 判断阶段。
- stage0 保持纯边界。
- 保留“投影”和“完成”的差异，不让工程字段误导为六阶段能力已完成。

需要注意的风险：

- `cold_retest` 当前只保留低强度 hint，尚未接入真实跨时距/跨 session 冷测窗口统计。
- `feedback_only` 只能从当前 feedback trace 中弱推断，尚未实现完整 no-answer feedback 课程。
- 当前投影不会驱动 teacher fade 或在线嵌入更新；它只是后续 20.9b/20.9c 的公共审计坐标。

## 5. 仍不能声明

仍不能声明：

- 六阶段学习协议 runtime 全量完成。
- teacher-off/cold-retest 验收系统完成。
- L1/L2/L3 在线嵌入完成。
- 完整范式自学习完成。
- 数学列竖式和任意简单计算完成。
- object-centric 视觉想象和 Phase21 视觉教学泛化闭环完成。

## 6. 下一步

Phase20.9b 最自然继续做：让 `learning_protocol_projection` 参与“教师退场 / request_teacher 频率 / feedback_only 判断”的 AP-native 调制，但仍然不能成为外部课程脚本。更后面再接 L1 在线嵌入更新和 Phase21 视觉教学泛化闭环。

