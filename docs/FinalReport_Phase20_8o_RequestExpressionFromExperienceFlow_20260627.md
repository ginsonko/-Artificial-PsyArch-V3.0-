# Phase20.8o 最终报告：request_teacher 表达从经验流中选择

日期：2026-06-27

## 1. 本阶段目标

Phase20.8o 继续推进 Phase20.8n 的结果：8n 已经让 `request_teacher` / `maintain_unclosed` 的行动驱动来自 low_grasp、unclosed、short_structure_flow、C*/StatePool carryover；8o 则让“具体怎么表达不知道/怎么表达还在想”也从 AP 已有经验流中选择。

本阶段不追求生成更聪明的答案，而是纠正旧实现中固定 `NO_CALL_TEXT` / `MAINTAIN_UNCLOSED_TEXT` 独占表达来源的问题。固定文本现在只作为冷启动最低层先天表达。

## 2. 设计审查

### 核心规则

- 普通知识教学不会变成 request_teacher 表达。
- 只有当 teacher feedback 的 `target_event_id` 指向 AP 自己上一轮 `draft_grid_commit` / `draft_grid_write`，且该事件 `source_intent` 是 `request_teacher` 或 `maintain_unclosed` 时，才沉淀为表达修正经验。
- 表达修正经验带 `expression_role`，并且不会进入 exact B0 问答索引。
- 普通 B0 / structural B / 视觉反向归因 / 视觉想象召回都会跳过带 `expression_role` 的 alignment，防止表达经验污染答案经验。

### 数学形式

表达候选来自：

```text
E_teacher = experience_alignment where payload.expression_role == intent
E_draft = draft_grid_commit where payload.source_intent == intent and visible_chars exists
```

候选支持：

```text
support(E_k) = unified_support(
  structural_similarity = role_match,
  occurrence_energy = expression_energy,
  recency = 1 / (1 + rank),
  modality_match = 1,
  reward = reward_k,
  punish = punish_k
)
```

最终选择：

```text
selected_expression = argmax support(E_k)
if no candidate:
  selected_expression = innate_minimal_expression(intent)
```

`request_teacher` 与 `maintain_unclosed` 不互相借用表达角色，避免“还在想”退化成“我不知道怎么说”。

## 3. 落地内容

代码：

- `apv3test/runtime/phase20_7/runtime.py`

新增/修改：

- `PHASE20_8O_REQUEST_EXPRESSION_ID`
- `_select_request_expression(...)`
- `_teacher_expression_candidates(...)`
- `_draft_expression_candidates(...)`
- `_expression_role_match(...)`
- `_expression_role_for_target_event(...)`
- `_with_request_expression_trace(...)`

事件 payload 扩展：

- `draft_grid_write` 写入 `unit_text` 与 `request_expression_selection`。
- `draft_grid_commit` 写入 `visible_text`、`visible_chars` 与 `request_expression_selection`。
- `teacher_feedback_event` / `experience_alignment` 在 targeted expression feedback 时写入 `expression_role`。

关键防污染：

- 带 `expression_role` 的 alignment 不写 exact B0 index。
- 带 `expression_role` 的 alignment 被 exact fallback、structural B、visual exact、visual imagination 排除。
- 表达修正 feedback 不自动 resolve unclosed item，因为它只教表达，不教答案。

测试：

- `tests/test_phase20_8o_request_expression_from_experience_flow.py`

覆盖：

- 冷启动 request_teacher 使用 innate fallback，且 tick trace 可审计。
- targeted feedback 可以教会 request_teacher 的表达。
- 普通知识教学不会污染 request_teacher 表达。
- targeted feedback 可以教会 maintain_unclosed 的表达。

## 4. 严谨验收

语法检查：

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_8o_request_expression_from_experience_flow.py
PASS
```

8o 专项：

```text
python -m pytest tests\test_phase20_8o_request_expression_from_experience_flow.py -q
4 passed
```

相邻链：

```text
python -m pytest tests\test_phase20_8o_request_expression_from_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_7_stage4_unclosed_idle.py -q
17 passed
```

Phase20.8 全链：

```text
python -m pytest tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8o_request_expression_from_experience_flow.py -q
48 passed
```

Phase20.7 + Phase20.8 底座链：

```text
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8o_request_expression_from_experience_flow.py -q
96 passed
```

红线扫描：

```text
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|enumerate_objects_in_image|regex|keyword_route" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_8o_request_expression_from_experience_flow.py -g "*.py"
No hits
```

## 5. 可以证明什么

- request_teacher 的表达内容现在可以从 targeted teacher feedback expression 中学习。
- maintain_unclosed 的表达内容也可以被 targeted teacher feedback expression 修正。
- AP 会把“教答案”和“教表达”分开：普通“是苹果”不会污染“我不知道时该怎么说”。
- 表达选择痕迹进入 `RuntimeTickEvent.ssp_active_summary.request_expression_selection`，工作台/tick 回放可以真实解释来源。
- 固定 `NO_CALL_TEXT` / `MAINTAIN_UNCLOSED_TEXT` 只剩冷启动 fallback，不再是唯一表达路径。
- 表达经验不会进入普通答案召回路径。

## 6. 仍不能声称什么

- 不能声称完整范式自学习已经完成；本阶段只是 request/maintain 表达选择的经验流化。
- 不能声称主动询问自然语言已经完全由复杂叙事续写生成；目前是从 targeted expression feedback 与 DraftGrid commit 中选择。
- 不能声称 L1/L2/L3 在线嵌入、六阶段学习 runtime、数学列竖式、object-centric 视觉想象已经完成。
- 不能声称所有输出表达都摆脱了固定冷启动本能；没有表达经验时仍会 fallback。

## 7. 下一步建议

Phase20.8p 应继续把“表达候选”下沉到更通用的范式学习：让 AP 不只会复用 targeted expression feedback，而能从多次 teacher feedback / reward / punish / DraftGrid 结构中抽象出“低把握时请求确认”“未闭合时说明还在想”“想学时追问用户”的表达槽位。该阶段仍必须保持：不按关键词分类，不新增答案表，不把表达范式污染为知识答案。
