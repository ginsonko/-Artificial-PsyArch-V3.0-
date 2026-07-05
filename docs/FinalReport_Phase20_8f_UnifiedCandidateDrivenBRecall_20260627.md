# Phase20.8f 统一候选驱动 B 召回落地报告

日期: 2026-06-27

## 一、设计

设计文件:

- `docs/Design_Phase20_8f_UnifiedCandidateDrivenBRecall_20260627.md`

目标:

```text
UnifiedExperienceCandidate
  -> structural B
  -> visual backward neutralization / exact B0
  -> B/C/C* audit trace
```

本阶段不是新增识别模块，而是继续把旧 helper 收束到统一候选池。

## 二、审查完善

审查发现:

1. `_find_structural_b(...)` 仍直接消费 alignment candidate，并自己计算 structural support。
2. `_select_alignment_by_backward_neutralization(...)` 仍直接消费 alignment candidate，并自己计算 visual support。
3. `_tick_event(...)` 的 `b_candidates`、`c_backward`、`cstar_packet` 没有统一展示 structural B / visual B0 的候选来源。

修正原则:

- 候选来源必须来自 `_unified_experience_candidates_for_observation(...)`。
- structural / visual 只是同一候选的不同解释方式。
- B/C/C* 必须写出 `support_formula`、`support_terms`、`unified_experience_candidate`。
- 保留原有行为阈值，避免把统一公式机械套用后压坏已经验证过的近似召回。

## 三、通过落地

修改:

- `apv3test/runtime/phase20_7/runtime.py`

新增:

- `tests/test_phase20_8f_unified_candidate_driven_b_recall.py`

主要落点:

- `_ExactB0` 增加 `candidate_audit_slots`、`support_terms`。
- `_StructuralB` 增加 `candidate_audit_slots`、`support_terms`。
- `_find_structural_b(...)` 改为遍历 `UnifiedExperienceCandidate`。
- `_select_alignment_by_backward_neutralization(...)` 改为遍历 `UnifiedExperienceCandidate`。
- `_tick_event(...)` 将统一候选审计写入:
  - `b_candidates`
  - `c_backward.cause_slots`
  - `cstar_packet`

## 四、严谨验收测试

专项测试:

```powershell
python -m pytest tests\test_phase20_8f_unified_candidate_driven_b_recall.py -q
```

结果:

```text
2 passed in 1.69s
```

相关回归:

```powershell
python -m pytest tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_8e_code_audit_and_unified_candidate.py -q
```

结果:

```text
23 passed in 8.63s
```

Phase20.7/20.8 指定全量回归:

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py -q
```

结果:

```text
61 passed in 34.90s
```

红线扫描:

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|enumerate_objects_in_image" apv3test\runtime\phase20_7 tests\test_phase20_8f_unified_candidate_driven_b_recall.py -g "*.py"
```

结果:

```text
无命中
```

## 五、可以证明什么

本阶段可以证明:

1. structural B 不再直接从旧 alignment helper 单独取候选，而是从统一候选池解释出 structural B。
2. visual exact B0 的反向中和不再直接从旧 alignment helper 单独取候选，而是从统一候选池解释出 visual B0。
3. tick 回放能看到 structural / visual B 的统一候选来源和 support terms。
4. 旧 Stage3 structural B、Stage5 visual patch reconstruction、20.8e 统一候选行为没有回归。

## 六、仍不能声称什么

本阶段仍不能声称:

1. 所有 B/C/C* 消费路径已经完全由唯一心脏驱动。
2. L1/L2/L3 在线嵌入已经接管结构相似。
3. 六阶段学习协议已经贯通 runtime。
4. 任意模态任意距离归因已经完整实现。
5. 数学列竖式、画板动作范式、完整范式自学习已经完成。

## 七、下一步

Phase20.8g 建议继续:

1. 将 `_find_exact_b0(...)` 的 index fallback 也迁移到统一候选解释层。
2. 将 `complete_every_tick_cognitive_cycle(...)` 的默认 weak B/C 补齐逻辑接入 unified candidate statistics。
3. 把 C* packet 从展示候选字段推进为真正的统一最小误差整合层。
4. 开始设计六阶段学习协议 runtime 状态机的最小可验闭环。
