# Phase20.8e 代码级审计与统一经验候选落地报告

日期: 2026-06-27

## 一、设计

设计文件:

- `docs/Design_Phase20_8e_CodeAuditAndUnifiedCandidate_20260627.md`

本阶段目标是把 Phase20.8c 的 alignment 候选与 Phase20.8d 的 recent structure flow 候选合流为同一类候选证据对象，并完成代码级红线审计。

核心设计:

```text
ExperienceRecallCandidate
ExperienceFlowCandidate
        -> UnifiedExperienceCandidate
        -> same support formula
        -> B/C/C* attribution and visual imagination audit slots
```

## 二、审查完善

审查重点:

1. 是否仍读最后图片或原始整图资产。
2. 是否仍存在标签表、答案表、hidden solver、学生侧 LLM。
3. 文本触发视觉想象时，是否通过经验流中的 visual patch refs。
4. 近期指代是否进入 C_backward 归因，而不是图片专用 if 分支。
5. 报告是否过度声称六阶段、L1/L2/L3、范式自学习已经完成。

审查发现:

- 统一候选前，alignment 与 recent flow 仍是两个类型，support 公式分散。
- 视觉想象 tick 自身没有显示统一候选来源，UI 回放不够白箱。
- 近期视觉追溯的公开字段从 `recent_visual` 变成 flow recovery kind 后，会破坏旧验收语义。

修正:

- 新增统一候选模块。
- support 计算集中到 `compute_unified_experience_support(...)`。
- `visual_imagination_recall` tick 写出 `unified_experience_candidate` cause slot。
- recent flow 归因同时保留旧 `unified_experience_flow_candidate` 兼容槽和新 `unified_experience_candidate` 槽。
- 公开审计字段继续显示 `recent_visual`，内部保留 `experience_flow_recent_visual_window`。

## 三、通过落地

新增:

- `apv3test/runtime/phase20_7/experience_candidate.py`
- `tests/test_phase20_8e_code_audit_and_unified_candidate.py`

修改:

- `apv3test/runtime/phase20_7/experience_recall.py`
- `apv3test/runtime/phase20_7/experience_flow.py`
- `apv3test/runtime/phase20_7/runtime.py`
- `apv3test/runtime/phase20_7/vision.py`

关键入口:

- `_unified_experience_candidates_for_observation(...)`
- `_unified_experience_candidates_for_input_signature(...)`

## 四、严谨验收测试

专项测试:

```powershell
python -m pytest tests\test_phase20_8e_code_audit_and_unified_candidate.py -q
```

结果:

```text
4 passed in 2.12s
```

相关阶段回归:

```powershell
python -m pytest tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py -q
```

结果:

```text
26 passed in 7.31s
```

Phase20.7/20.8 指定全量回归:

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py -q
```

结果:

```text
59 passed in 27.42s
```

红线扫描:

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|enumerate_objects_in_image" apv3test\runtime\phase20_7 tests\test_phase20_8e_code_audit_and_unified_candidate.py -g "*.py"
```

结果:

```text
无命中
```

## 五、旧问题逐项回答

1. 闲时视觉是否还永远看最后图像?

已有 Phase20.8a/Stage5 测试覆盖“不跟最后图像走”。本阶段没有回退这条路径。

2. 内心画面是否还展示最后输入图像?

本阶段继续验证 `raw_source_asset_used_for_render=False`，视觉想象来自 `borrowed_patch_payload_refs`。

3. 输入“苹果”文本是否能召回曾经共现的苹果视觉 patch?

可以证明局部成立。20.8e 新测试验证 `apple -> experience_alignment -> visual patch refs -> visual_imagination_recall`，且不会被最后香蕉图覆盖。

4. “黄色苹果”是否已经完整拆分苹果轮廓和黄色颜色?

不能这样声称。已有测试只能证明多来源 patch borrowing 的早期桥接，尚不是 object-centric part codebook 级生成。

5. 是否仍使用原始图像资产?

本阶段扫描和测试未发现。视觉想象 tick 明确写出 `raw_source_asset_used_for_render=False`。

6. 文本是否也走 AP 主流程?

比上一阶段更接近。文本触发视觉想象已从统一候选池取候选，但旧 helper 仍存在，尚未全部替换成唯一 B/C/C* 心脏。

7. 泛化能力、范式自学习、跨 tick 自学习是否真正完成?

未完成。当前能证明的是统一候选、近期归因、视觉 patch 桥接，不是完整范式自学习。

8. 六阶段学习协议是否实现?

未贯通。20.8e 新测试确认 runtime 没有伪造 `six_stage_learning_complete`、`online_embedding_converged`、`l1_l2_l3_complete` 等完成标记。

9. 是否存在 AP 主流程外的模拟/硬编码/多余模块?

红线扫描无命中。仍有过渡 helper，但它们现在逐步收束到统一候选入口；后续必须继续收束，而不是扩展成旁路。

## 六、下一步

Phase20.8f 应继续做:

1. 把 `_find_structural_b(...)` 和 `_select_alignment_by_backward_neutralization(...)` 的选择逻辑继续改成统一候选排序。
2. 将 unified candidate 的 support_terms 接入 C* packet，而不只在 cause slots 展示。
3. 设计真正的多维 SSP alignment，减少文本 helper。
4. 开始六阶段学习协议 runtime 状态机，但先只做可验最小闭环，不声称完整泛化。
