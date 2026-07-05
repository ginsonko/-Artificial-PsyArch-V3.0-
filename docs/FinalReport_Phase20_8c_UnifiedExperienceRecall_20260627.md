# Phase20.8c 统一 ExperienceFlow / SSP 结构召回接口落地报告

日期: 2026-06-27

## 一、设计

设计文件:

- `docs/Design_Phase20_8c_UnifiedExperienceRecall_20260627.md`

本阶段目标是把多个局部 helper 对 `experience_alignment` 的重复扫描收束到统一候选层, 为后续 B/C/C* 真正成为唯一召回与归因心脏做准备。

## 二、审查完善

审查原则:

1. 统一召回接口只生成经验候选, 不直接生成回答。
2. 不改变 reply_text。
3. 不读取原始图像资产、不读取文件名、不使用标签表。
4. 不把弱证据伪装成真实 recall candidate。
5. 近期窗口归因仍保留, 因为它对应拟人的“刚刚那个/这张图/刚才说的”短期追溯能力。

审查后选择的落地方式:

- 先抽 `ExperienceRecallCandidate` 和 `query_experience_alignment_candidates(...)`。
- 保留各用途门槛与返回 dataclass。
- 将结构 B、视觉 exact、视觉想象、exact fallback、idle successor 都迁移到统一候选层。

## 三、通过落地

新增文件:

- `apv3test/runtime/phase20_7/experience_recall.py`

新增结构:

- `ExperienceRecallQuery`
- `ExperienceRecallCandidate`
- `query_experience_alignment_candidates(...)`

Runtime 接入:

- `apv3test/runtime/phase20_7/runtime.py`
- 新增 `_experience_candidates_for_observation(...)`
- 新增 `_experience_candidates_for_input_signature(...)`

已迁移消费路径:

- `_select_visual_imagination_recall(...)`
- `_select_alignment_by_backward_neutralization(...)`
- `_find_structural_b(...)`
- `_find_exact_b0(...)` 的 experience alignment fallback
- `_successor_for_unclosed(...)`

现在主 runtime 中经验 alignment 的候选扫描入口集中到 `experience_recall.py`。

## 四、严谨验收测试

新增测试:

- `tests/test_phase20_8c_unified_experience_recall.py`

覆盖:

1. 统一候选层能读取 alignment, 生成文本/视觉可用候选。
2. 结构文本召回仍可用。
3. 视觉 exact 仍可用。
4. “黄色苹果”视觉想象仍可借用多个经验来源。

专项测试:

```powershell
python -m pytest tests\test_phase20_8c_unified_experience_recall.py -q
```

结果:

```text
2 passed in 1.81s
```

全量回归:

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py -q
```

结果:

```text
53 passed in 30.01s
```

红线扫描:

```powershell
rg -n "enumerate_objects_in_image|image_label_map|label_map|teaching_hit|taught_answer|direct_reply|reply_text\s*=\s*taught|raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|hidden_solver|student_side_llm|answer_table|regex" apv3test\runtime\phase20_7 tests\test_phase20_8c_unified_experience_recall.py
```

结果:

- 无命中。

经验流扫描收束检查:

```powershell
rg -n "WHERE event_kind='experience_alignment'|SELECT event_id, payload_json, reward, punish" apv3test\runtime\phase20_7
```

结果:

- `experience_recall.py` 中保留统一召回入口。
- `experience_log.py` 中保留记忆包/索引相关查询, 非主 runtime helper 召回路径。

## 五、本阶段可以证明什么

本阶段可以证明:

- 主 runtime 的多个局部召回 helper 已开始共享统一 ExperienceFlow candidate layer。
- 结构文本、视觉 exact、视觉想象和 idle successor 在行为不漂移的前提下完成迁移。
- 统一召回层不参与直接回答, 不引入标签表或 hidden solver。

## 六、仍待完成

本阶段还不能证明:

- B/C/C* 的全部数学评分已经完全统一。
- 短期结构池的图/空间/时空结构对齐已完全进入候选层。
- 在线嵌入 L1/L2/L3 已作为候选召回主信号。
- 六阶段学习协议、列竖式数学、画板动作范式已贯通统一召回。

下一步建议:

Phase20.8d 应继续把 `_recent_experience_windows(...)` 的短期窗口追溯、视觉 patch refs、文本结构片段、unclosed successor 全部表达为同一类 SSP occurrence/edge query, 让 `ExperienceRecallCandidate` 从“alignment 候选层”升级为真正的“统一短期结构流 + 经验流召回层”。
