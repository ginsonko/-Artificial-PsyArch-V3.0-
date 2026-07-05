# Phase20.8n 最终报告：request_teacher / maintain_unclosed 统一驱动

日期：2026-06-27

## 1. 本阶段目标

Phase20.8n 的目标是把 `request_teacher` 与 `maintain_unclosed` 从固定低把握动作，继续收束到 AP 白皮书主流程：

- 低把握感：当前输入没有形成高支持的 B 召回。
- 未闭合感：同一经验签名仍有 active unclosed item。
- 短期结构流：近期 `short_structure_flow_next` 仍在推动当前 tick。
- C*/StatePool carryover：前序 tick 的预测/压力虚能量继续影响行动竞争。

本阶段只统一行动驱动与审计来源，不新增答案表、不新增关键词路由、不新增独立主动询问模块，也不把 request_teacher 变成直接回复候选。

## 2. 设计审查

采用公式：

```text
low_grasp = 1 - max(exact_b0.support, structural_b.support, 0)
unclosed_pull = active_unclosed.u_value
short_flow = max_support(short_structure_flow_next)
cstar_pressure = max(carryover.pressure_support, carryover.max_carry, carryover.observation_support_bias)

request_drive = clamp(
  0.20
  + 0.30 * low_grasp
  + 0.18 * unclosed_pull
  + 0.14 * short_flow
  + 0.12 * cstar_pressure,
  0.05,
  0.95
)

maintain_drive = clamp(
  0.18
  + 0.16 * low_grasp
  + 0.36 * unclosed_pull
  + 0.12 * short_flow
  + 0.10 * cstar_pressure,
  0.05,
  0.95
)
```

审查结论：

- 这些输入信号全部来自已有 AP 主流程：B/structural B、unclosed item、SSP/ExperienceFlow、C*/StatePool carryover。
- 没有新增“社交期待/任务承诺/主动询问模块”等额外实体。
- request_teacher 只表达“需要教学/确认”的行动倾向，不承载具体答案。
- 8j 已有 C* carryover 会在 `_tick_event` 中继续追加 drive delta，因此 8n 的基础公式 drive 与最终 competition drive 允许不同；审计字段保留 `drive_before_cstar_carryover`。

## 3. 落地内容

代码：

- `apv3test/runtime/phase20_7/runtime.py`

新增/接入：

- `PHASE20_8N_REQUEST_TEACHER_DRIVE_ID`
- `_teacher_request_drive_context(...)`
- `_latest_short_structure_flow_support(...)`
- `_competition(..., teacher_request_context=...)`
- `_drive_for_output(..., teacher_request_context=...)`
- `_feelings_for_output(..., teacher_request_context=...)`

关键接入点：

- `action_record.drive`：request/maintain 使用统一公式 drive。
- `action_record.eligibility`：记录 `teacher_request_drive_context`。
- `action_competition`：request/maintain 行记录同一 context。
- `unclosed_item.reason`：记录同一 context，grasp 来自 low_grasp。
- `feelings`：source 改为 `unified_teacher_request_drive` / `unified_unclosed_request_drive`。
- `commit_reply` 与 post-commit idle tick 的审计也保留同一 context，便于 tick 回放解释。

测试：

- `tests/test_phase20_8n_request_teacher_unified_drive.py`

覆盖：

- 未知输入触发 request_teacher，并携带统一 drive context。
- 重复未知触发 maintain_unclosed，并由同一 context 解释。
- `short_structure_flow_next` 能进入 request drive。
- Stage0 不产生 teacher request drive context。

## 4. 严谨验收

语法检查：

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_8n_request_teacher_unified_drive.py
PASS
```

8n 专项测试：

```text
python -m pytest tests\test_phase20_8n_request_teacher_unified_drive.py -q
4 passed
```

相邻链测试：

```text
python -m pytest tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_7_stage4_unclosed_idle.py -q
13 passed
```

Phase20.8 全链：

```text
python -m pytest tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py -q
44 passed
```

Phase20.7 + Phase20.8 底座链：

```text
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8i_cstar_statepool_virtual_feedback.py tests\test_phase20_8j_cstar_carryover_next_tick_influence.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py tests\test_phase20_8l_short_structure_next_unified_query.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8n_request_teacher_unified_drive.py -q
92 passed
```

红线扫描：

```text
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|enumerate_objects_in_image" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_8n_request_teacher_unified_drive.py -g "*.py"
No hits
```

## 5. 可以证明什么

- `request_teacher` 不再只是固定 0.75 的低把握动作；它的基础 drive 来自 low_grasp、unclosed、short_structure_flow、C*/StatePool carryover 的统一公式。
- `maintain_unclosed` 与 `request_teacher` 使用同一份 context，只是权重更偏向未闭合感。
- 同一份 `teacher_request_drive_context` 贯穿 action record、competition、feelings、unclosed reason 和 tick 回放。
- C* carryover 仍然能作为后继压力在最终 competition 中追加 drive delta，保持 20.8j 的连续 tick 影响。
- Stage0 边界保持干净，不写入该 drive context。
- 未知/弱召回路径仍然不造 B，不把 request_teacher 写成直接回复或答案候选。

## 6. 仍不能声称什么

- 不能声称完整持久 StatePool 已完成。
- 不能声称 L1/L2/L3 在线嵌入已完成。
- 不能声称六阶段学习协议已经 runtime 化。
- 不能声称完整范式自学习、数学列竖式、object-centric 视觉想象已经完成。
- 不能声称主动询问的自然语言表达已经完全由范式自学习生成；本阶段统一的是 drive 与审计，不是表达生成机制。

## 7. 下一步建议

下一步应进入 Phase20.8o：把 request_teacher 的表达内容继续从固定 `NO_CALL_TEXT` 向 DraftGrid/已学表达范式/短期结构流续写收束。重点仍然不是让它“回答得更多”，而是让“我不懂、我想确认、你能教我吗”这类表达从 AP 的经验流、未闭合感和行动竞争中自然长出来，同时保持不造答案、不走关键词模板。
