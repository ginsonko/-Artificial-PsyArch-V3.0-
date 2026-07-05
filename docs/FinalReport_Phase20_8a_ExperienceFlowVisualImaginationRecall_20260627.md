# Phase20.8a 经验流视觉想象召回与去旁路报告

日期: 2026-06-27

## 目标

本轮针对用户指出的两个核心问题做底层纠偏:

1. 闲时视觉移动和内心画面不能被“最后输入图像”绑架。
2. 文本输入如“苹果”“黄色苹果”应能通过经验流反向召回曾经共现过的视觉 patch, 并由这些视觉 SA / patch payload 重建内心画面, 而不是读取原始图像资产、文件名、标签表或最近图片缓存。

本轮仍遵守 Phase20.7 / APV3 主线边界: 不引入图片标签表、不使用文件名语义、不用原始整图作为内心画面渲染来源、不把 UI 展示当作认知结果。

## 已落地实现

### 1. 删除整图环境帧旁路

文件: `apv3test/runtime/phase20_7/vision.py`

已删除以下运行时能力:

- `visual_environment_frame_payload` 的整图持久化路径。
- `_store_visual_environment_frame`
- `_latest_environment_frame`
- `_environment_frame_by_hash`
- `_environment_rgb`
- `_resample_canvas_from_environment`
- `_replay_environment_focus_history`

现在视觉 idle 和内心画面重建只能读取已经写入经验流的 patch payload, 不能重新读取最后一张原始图像。

### 2. 文本 occurrence 触发视觉想象召回

文件: `apv3test/runtime/phase20_7/runtime.py`

当本轮有文本输入、没有当前图片输入、且历史经验流中存在文本反馈与视觉 evidence 共现时, runtime 会插入 `visual_imagination_recall` tick:

- 从 `experience_alignment` 中召回与当前文本结构片段相似的历史经验。
- 通过 alignment 找到对应的视觉 patch payload refs。
- 调用 `run_visual_imagination_recall_tick(...)`。
- 生成 `visual_inner_picture.source = visual_imagination_recall`。
- 标记 `epistemic_source = IMAGINED_FROM_EXPERIENCE_FLOW`。
- 标记 `raw_source_asset_used_for_render = False`。

这使得“苹果”文本可以反向召回此前“红色苹果”教学经验中的视觉 patch, 并重建内心画面。

### 3. 组合文本可借用多个视觉经验来源

文件: `apv3test/runtime/phase20_7/runtime.py`

`_select_visual_imagination_recall(...)` 不再只选整句最高相似经验, 而是使用当前文本结构片段覆盖:

- “黄色苹果”可以同时命中“红色苹果”中的“苹果”片段和“黄色香蕉”中的“黄色”片段。
- 多个历史视觉 alignment 可同时进入一次 `visual_imagination_recall`。
- 内心画面会记录 `source_alignment_ids` 与 `borrowed_patch_payload_refs`, 便于白箱审计。

这不是完整概念级泛化, 但已经从“单一最近答案/单一最高句子”前进到“多片段经验流混合想象”。

### 4. 闲时视觉跟随最近视觉认知事件

文件: `apv3test/runtime/phase20_7/vision.py`

`idle_visual_focus` 的材料来源由“最近外部视觉采样”改为“最近视觉认知事件”:

- 外部图像采样: `visual_patch_sample`
- 内生视觉想象: `visual_imagination_recall`

因此用户先最后看过香蕉, 再输入“苹果”触发苹果视觉想象后, 下一次闲时视觉会继续围绕刚才的苹果经验流 patch 观察, 不会退回最后上传的香蕉图。

## 新增验收

文件: `tests/test_phase20_7_stage5_visual_patch_reconstruction.py`

新增/强化测试:

1. `test_stage5_text_can_recall_visual_inner_picture_from_experience_flow`
   - 教苹果图与香蕉图。
   - 仅输入“苹果”文本。
   - 验证出现 `visual_imagination_recall` tick。
   - 验证内心画面来自经验流 patch payload, 不使用原始资产。

2. `test_stage5_text_visual_imagination_is_not_the_last_seen_image`
   - 先教苹果, 再教香蕉, 再让最后视觉输入为香蕉。
   - 仅输入“苹果”文本。
   - 验证召回 alignment 来自苹果经验, 不来自香蕉经验。

3. `test_stage5_idle_visual_focus_follows_latest_visual_imagination_not_last_image`
   - 最后外部视觉为香蕉。
   - 输入“苹果”触发苹果视觉想象。
   - 下一次 idle 视觉必须从刚才苹果想象事件借用的 patch refs 继续重建, 不回退到最后香蕉图。

4. `test_stage5_mixed_text_can_borrow_multiple_visual_experience_sources`
   - 教“红色苹果”和“黄色香蕉”。
   - 输入“黄色苹果”。
   - 验证一次视觉想象可借用至少两个经验来源。

## 验收结果

专项测试:

```powershell
python -m pytest tests\test_phase20_7_stage5_visual_patch_reconstruction.py -q
```

结果:

```text
15 passed in 3.02s
```

Phase20.7 全量回归:

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py -q
```

结果:

```text
48 passed in 15.57s
```

红线扫描:

```powershell
rg -n "visual_environment_frame_payload|_store_visual_environment_frame|_latest_environment_frame|_environment_frame_by_hash|_environment_rgb|_resample_canvas_from_environment|_replay_environment_focus_history|environment_frame|environment_payload_ref" apv3test\runtime\phase20_7 tests\test_phase20_7_stage5_visual_patch_reconstruction.py
```

结果:

- 运行时代码无命中。
- 测试文件仅保留 `visual_environment_frame_payload` 数量为 0 的断言。

## 仍然没有完成的部分

本轮可以证明:

- 文本可以通过经验流召回视觉 patch 并生成内心画面。
- 内心画面渲染不依赖原始图像资产。
- idle 视觉不会被最后输入图像强制绑架。
- “黄色苹果”类组合想象可以从多个历史视觉经验来源借用 patch。

本轮还不能证明:

- 完整六阶段学习协议已经实现。
- L1/L2/L3 在线嵌入学习已经真实收敛。
- 任意模态、任意时空距离的归因已经完整泛化。
- 视觉概念已经达到真正 object-centric / part-codebook / 诊断部件级泛化。
- 简单数学列竖式、数手指、范式行动的自学习已经落地到当前 Phase20.7 主循环。

这些仍应进入 Phase20.8 后续阶段, 按 AP 白皮书继续推进。

## 下一步建议

1. 将 C_backward / C_forward 从当前局部 helper 进一步统一到每 tick 的通用 B/C/C* 召回接口, 让文本、视觉、听觉、行动、内心想法都共享同一归因/预测过程。
2. 把 `_semantic_text_overlap_with_units(...)` 继续升级为短期结构池结构对齐, 而不是局部文本 helper。
3. 实现视觉 V0-V12 / part-codebook / source mask 的真实增长, 支撑苹果、香蕉、橙子与变体的部件级区分。
4. 实现六阶段学习协议在主 runtime 的真实状态机与验收 trace。
5. 将 idle thought / idle vision / inner audio 都改成统一的连续认知流演化, UI 只投影 RuntimeTickEvent, 不新增认知旁路。
