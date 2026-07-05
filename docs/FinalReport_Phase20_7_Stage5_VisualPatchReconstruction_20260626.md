# Phase20.7 Stage 5 Visual Patch Reconstruction 验收报告

日期: 2026-06-26  
范围: 视觉 patch payload、焦点采样、clarity map、状态池视觉证据、内心画面重建。

---

## 1. 本阶段目标

Stage 5 的目标是把视觉输入接入 Phase20.7 同一套 RuntimeTickEvent, 但只作为 AP-native 感受器证据:

1. 图片输入不走整图识别。
2. 不使用文件名、OCR、外部模型或标签映射得出物体名。
3. 视觉 tick 由焦点行动 `move_focus / maintain_focus` 驱动。
4. 每个视觉 tick 保存真实 patch payload。
5. SensoryCanvas 逐 tick 融合 patch, 形成 clarity map。
6. `visual_inner_picture` 来自 patch payload 重建, 不是原图贴回。

---

## 2. 已落地内容

### 2.1 payload blob

`experience_log.py` 新增:

1. `insert_payload_blob(...)`

写入:

```text
phase20_7_payload_blobs
payload_kind = visual_patch_payload
media_type = image
bytes = PNG patch bytes
summary_json = focus_xy / patch_box / mean_rgb / patch_native_resolution
```

### 2.2 视觉 runtime

新增 `apv3test/runtime/phase20_7/vision.py`:

1. `run_visual_receptor_ticks(...)`
2. `_focus_sequence(...)`
3. `_store_patch_payload(...)`
4. `_write_visual_occurrences(...)`
5. `_inject_visual_state(...)`
6. `_write_inner_picture(...)`

其中 `_focus_sequence(...)` 基于像素对比度与饱和度形成先天显著性焦点, 不输出任何物体标签。

### 2.3 Runtime 接入

`runtime.py` 新增:

1. `PHASE20_7_STAGE5_SCHEMA_ID`
2. `runtime_stage="stage5"`
3. 图片输入先产生视觉 ticks, 再进入文本/召回/未闭合路径。
4. RuntimeTickEvent 中填充 `visual_inner_picture`。
5. 媒体路径在 trace 中只显示 hash, 不显示原始路径。

---

## 3. 当前可展示效果

本阶段可展示:

```text
输入: 一张本地图片

tick 1: move_focus -> visual_patch_sample -> patch payload -> inner picture
tick 2: move_focus -> visual_patch_sample -> clarity coverage 增长
tick 3: move_focus -> visual_patch_sample -> inner picture 更丰富
```

RuntimeTickEvent 展示:

1. `selected_action.action_type = move_focus`
2. `receptor_outputs.receptor = visual_patch_sensor`
3. `visual_inner_picture.path = .../phase20_7_inner_pictures/inner_*.png`
4. `state_pool_top` 包含 `sensory_canvas` 与 `visual_focus`
5. `phase20_7_payload_blobs` 中有真实 PNG patch bytes

---

## 4. 本阶段能证明什么

Stage 5 可以证明:

1. 视觉输入已经进入 Phase20.7 同一套 RuntimeTickEvent。
2. 视觉证据来自像素 patch payload。
3. 视焦点会移动, 不固定在中心。
4. clarity map 会随 tick 累积。
5. 内心画面是 SensoryCanvas 重建产物。
6. 文件名中的 apple/banana 等文本不会进入认知 trace 或 payload summary。
7. 视觉仍不输出物体名, 不会冒充识别。

---

## 5. 本阶段尚未证明什么

Stage 5 还不证明:

1. 视觉教学后能稳定区分苹果/香蕉。
2. V7 part codebook 的长程泛化。
3. 视觉与文本 alignment 的完整学习闭环。
4. 视觉 C_forward/C_backward 的空间结构推理。
5. 工作台中的高质量可交互可视化。

这些进入后续 Stage。

---

## 6. 验收命令

### 6.1 Stage 0-5 单测

```powershell
python -m pytest .\tests\test_phase20_7_stage0_runtime_boundary.py .\tests\test_phase20_7_stage1_text_closed_loop.py .\tests\test_phase20_7_stage2_experience_memory_indexes.py .\tests\test_phase20_7_stage3_structural_bccstar.py .\tests\test_phase20_7_stage4_unclosed_idle.py .\tests\test_phase20_7_stage5_visual_patch_reconstruction.py -q
```

结果: `25 passed`。

### 6.2 Stage 5 红线扫描

```powershell
python .\scripts\red_line_check_v14.py --phase 20.7-stage5
```

结果: 见最终运行记录。

---

## 7. 下一阶段入口

Stage 6 应实现:

1. audio audit sensor。
2. xiaoyi 本地 TTS actuator。
3. TTS 与 inner voice 明确分离。
4. 录音只作为 audit/basic sensor 进入 RuntimeTickEvent, 不冒充识别标签。

