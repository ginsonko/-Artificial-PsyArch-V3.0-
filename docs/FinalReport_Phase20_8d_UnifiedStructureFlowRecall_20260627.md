# Phase20.8d 统一短期结构流 + 经验流候选层落地报告

日期: 2026-06-27

## 一、设计

设计文件:

- `docs/Design_Phase20_8d_UnifiedStructureFlowRecall_20260627.md`

本阶段目标是把 Phase20.8c 的 alignment 候选层继续推进为更接近 AP 白皮书的统一候选层:

```text
近期事件 + occurrence + structure edge + visual patch payload + alignment
  -> ExperienceFlowCandidate
  -> B/C/C* 归因、预测、视觉想象、idle successor
```

## 二、审查完善

审查原则:

1. 不新增答案模块。
2. 不改变 reply_text。
3. 不读取原始整图、不读取文件名、不引入 label map。
4. 近期窗口追溯必须保留, 因为它对应人类“刚刚那个”的短期归因。
5. visual patch payload 可以进入候选, 但只能作为已采样视觉 SA 的 payload, 不能退回整图缓存。

实施策略:

- 新增 `ExperienceFlowCandidate`。
- 保留原有归因门槛和评分, 先替换数据来源。
- 在 C_backward cause slots 中记录 unified flow candidate, 让 tick 回放能看见真实来源。

## 三、通过落地

新增文件:

- `apv3test/runtime/phase20_7/experience_flow.py`

新增核心结构与函数:

- `ExperienceFlowCandidate`
- `query_recent_experience_flow_candidates(...)`

Runtime 接入:

- `_recent_experience_windows(...)` 改为消费 `ExperienceFlowCandidate`。
- `_patch_payload_refs_for_alignment(...)` 的 fallback 改为通过 recent visual flow candidates 取 patch payload refs。
- C_backward 的 `cause_slots` 增加 `unified_experience_flow_candidate` 审计槽。

## 四、严谨验收测试

新增测试:

- `tests/test_phase20_8d_unified_structure_flow.py`

覆盖内容:

1. “刚刚图片是啥”这类近期追溯会在 C_backward 中出现 `unified_experience_flow_candidate`。
2. flow candidates 同时携带 occurrence ids、edge ids、visual payload refs。

专项测试:

```powershell
python -m pytest tests\test_phase20_8d_unified_structure_flow.py -q
```

结果:

```text
2 passed in 1.32s
```

全量回归:

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py -q
```

结果:

```text
55 passed in 33.13s
```

红线扫描:

```powershell
rg -n "enumerate_objects_in_image|image_label_map|label_map|teaching_hit|taught_answer|direct_reply|reply_text\s*=\s*taught|raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|hidden_solver|student_side_llm|answer_table|regex" apv3test\runtime\phase20_7 tests\test_phase20_8d_unified_structure_flow.py
```

结果:

- 无命中。

结构流收束扫描:

```powershell
rg -n "text_receptor_observation', 'visual_patch_sample|WHERE e\.event_kind='visual_patch_sample'|SELECT e\.payload_json|recent_experience_windows|query_recent_experience_flow_candidates|ExperienceFlowCandidate" apv3test\runtime\phase20_7\runtime.py apv3test\runtime\phase20_7\experience_flow.py
```

结果:

- `_recent_experience_windows(...)` 保留为兼容函数名, 但底层已消费 `query_recent_experience_flow_candidates(...)`。
- recent visual patch fallback 已通过 `ExperienceFlowCandidate` 获取 payload refs。

## 五、本阶段可以证明什么

本阶段可以证明:

- 近期窗口追溯不再是独立扫描逻辑, 已进入统一 flow candidate。
- flow candidate 能携带 occurrence、edge、payload refs。
- “刚刚图片是啥”这类拟人短期归因能在 C_backward 中显示统一候选来源。
- 视觉 patch fallback 不再直接扫描 visual_patch_sample, 而是从 recent visual flow candidates 取 payload refs。

## 六、仍待完成

本阶段还不能证明:

- 全部 B/C/C* scoring 已完全统一为同一个数学模型。
- 在线嵌入 L1/L2/L3 已进入 flow candidate support。
- 图/空间/时空结构对齐已经完全替代文本 helper。
- 六阶段学习、数学列竖式、画板范式行动已贯通。

下一步 Phase20.8e 应继续把 `ExperienceRecallCandidate` 与 `ExperienceFlowCandidate` 合流, 让 alignment、recent window、occurrence/edge、visual/audio payload 都成为同一个候选类型, 并把 B/C/C* 的 support 统一到一个可审计公式里。
