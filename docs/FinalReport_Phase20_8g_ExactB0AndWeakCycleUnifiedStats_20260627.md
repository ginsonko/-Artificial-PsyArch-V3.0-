# Phase20.8g Exact B0 索引回读与 weak B/C 统一候选统计落地报告

日期: 2026-06-27

## 一、设计

设计文件:

- `docs/Design_Phase20_8g_ExactB0AndWeakCycleUnifiedStats_20260627.md`

本阶段继续把 Phase20.8e/20.8f 已经建立的 `UnifiedExperienceCandidate` 推进到两个残留路径:

```text
exact_b0_index
  -> alignment_event_id
  -> UnifiedExperienceCandidate
  -> ExactB0 audit

default weak B/C
  -> existing runtime tick audit slots
  -> unified_candidate_statistics
  -> tick_evidence_b / c_backward / C*
```

核心原则:

1. 索引只做加速层，不做真相源。
2. 索引命中后必须能回到 experience alignment event，并被包装成统一候选，才允许形成 ExactB0。
3. weak B/C 只统计本 tick 已有审计槽，不创造新的 B 候选。
4. 不新增 keyword/regex/answer table/hidden solver/student-side LLM。

## 二、审查完善

审查发现:

1. `_find_exact_b0(...)` 已经开始调用 `_unified_candidate_for_alignment_id(...)`，但 helper 尚未定义，代码处于半落地状态。
2. `_find_exact_b0(...)` fallback 曾用 support terms 中的 `reward` 重新拼接 support；但这里的 `reward` 已是统一公式中的加权贡献，不应再当原始奖赏解释。
3. `complete_every_tick_cognitive_cycle(...)` 的 default weak B/C 会补齐每 tick 的 B/C/C*，但没有把已有 `unified_experience_candidate` 审计槽汇总到统一统计字段。

修正:

1. 补 `_unified_candidate_for_alignment_id(...)`:
   - 从 `_unified_experience_candidates_for_observation(...)` 回读候选。
   - 只接受 `candidate_kind == "experience_alignment"`。
   - 要求 `alignment_event_id` 与 `input_signature` 都匹配当前 observation。
   - 回读失败时跳过该 index row，不直接返回答案。
2. `_find_exact_b0(...)` fallback support 改为直接使用 unified candidate support 的保守下限，不再二次解释 reward term。
3. `cognitive_cycle.py` 新增统一候选统计:
   - 从 `b_candidates[*].candidate_audit_slots` 统计。
   - 从 `c_backward[*].cause_slots` 统计。
   - 去重后生成 `candidate_count`、`max_support`、`candidate_kinds`、`support_formulas`、`candidate_ids`。
   - 明确写出 `creates_candidate=False`。

## 三、通过落地

修改:

- `apv3test/runtime/phase20_7/runtime.py`
- `apv3test/runtime/phase20_7/cognitive_cycle.py`

新增:

- `tests/test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py`

主要落点:

- `_find_exact_b0(...)` 的 index hit 路径不再相信 index payload 本身，必须回到统一候选。
- `_find_exact_b0(...)` 的 alignment fallback 继续写回 index，但 ExactB0 审计来自统一候选。
- `tick_evidence_b.unified_candidate_statistics` 写入默认 weak B 证据。
- default `c_backward.cause_slots` 写入 `slot_kind=unified_candidate_statistics`。
- default `cstar_packet.unified_candidate_statistics` 写入同一统计。
- 已有 C* packet 也会补入该统计字段，但不改写既有 packet 语义。

## 四、严谨验收测试

编译:

```powershell
python -m py_compile apv3test\runtime\phase20_7\runtime.py apv3test\runtime\phase20_7\cognitive_cycle.py
```

结果:

```text
通过
```

专项测试:

```powershell
python -m pytest tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py -q
```

结果:

```text
3 passed in 2.46s
```

相关回归:

```powershell
python -m pytest tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py -q
```

结果:

```text
17 passed in 7.83s
```

Phase20.7/20.8 指定回归链:

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py -q
```

结果:

```text
64 passed in 53.06s
```

红线扫描:

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|enumerate_objects_in_image" apv3test\runtime\phase20_7 tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py -g "*.py"
```

结果:

```text
无命中
```

补充说明:

```powershell
python -m pytest -q
```

结果:

```text
240 秒超时，未得到完成摘要；不作为通过证据。
```

确认超时后仅有的 Python 进程为 `apv3test.web_chat` 工作台服务，不是 pytest 残留。

## 五、可以证明什么

本阶段可以证明:

1. exact B0 的 index 命中路径已经不再直接把 index 当答案源。
2. index row 必须回读成 `UnifiedExperienceCandidate`，并带 `support_formula`、`support_terms`、`unified_experience_candidate` 审计槽，才能形成 ExactB0。
3. default weak B/C 的每 tick 补齐已经纳入统一候选统计；没有候选时显示 `candidate_count=0`，而不是伪造 B 候选。
4. Stage0 边界仍保持不写经验事件、不补认知 tick。
5. Phase20.7/20.8 当前指定回归链没有被破坏。

## 六、仍不能声称什么

本阶段仍不能声称:

1. 所有 B/C/C* 都已经完全由唯一心脏驱动。
2. C* 已经是真正的统一最小误差整合层。
3. 六阶段学习协议已经贯穿 runtime。
4. L1/L2/L3 在线嵌入已经完成。
5. 完整范式自学习、数学列竖式、画板行动范式、任意模态任意距离归因已经完成。
6. 全仓库 `pytest -q` 已经通过；本轮全量 pytest 超时，只能声明指定回归链通过。

## 七、下一步

Phase20.8h 建议继续:

1. 将 C* packet 从“展示统一候选统计”推进为真正的统一最小误差整合层。
2. 把 `c_forward`、`c_backward`、`C*` 的 support reconciliation 写成同一套可审计公式。
3. 开始六阶段学习协议 runtime 状态机的最小可验闭环，但只做 AP 主流程内的状态推进，不新增学习旁路。
4. 继续收束剩余 helper，使文本、视觉、音频、行动都通过 SSP/ExperienceFlow 的统一结构召回与预测归因循环。
