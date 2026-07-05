# Phase20.8b 每 tick 通用 B/C/C* 认知循环落地报告

日期: 2026-06-27

## 一、设计

本阶段按“设计 -> 审查完善 -> 通过落地 -> 严谨验收测试 -> 最终汇总报告”推进。

设计文件:

- `docs/Design_Phase20_8b_EveryTickCognitiveCycle_20260627.md`

核心目标:

- 将文本、视觉、听觉、草稿、闲时思考、TTS 等 tick 统一补齐 B/C/C* 审计包。
- 每个认知 tick 都能看见预测与归因。
- 不让各模态 helper 各自发明独立解释路径。
- 不改变答案生成, 不读取原始视觉资产, 不引入标签表、答案表、hidden solver 或 LLM。

## 二、审查完善

审查中发现一个关键语义风险:

- 不能把弱证据 B 直接写进 `b_candidates`, 因为旧语义中 `b_candidates` 表示真实记忆召回命中。

修正:

- `b_candidates` 只保留真实 exact/structural recall。
- 每 tick 的弱证据 B 写入 `cstar_packet.tick_evidence_b`。
- 这样既满足每 tick 闭环, 又不污染“是否召回成功”的验收语义。

## 三、通过落地

新增文件:

- `apv3test/runtime/phase20_7/cognitive_cycle.py`

新增核心函数:

- `complete_turn_cognitive_cycle(result)`
- `complete_every_tick_cognitive_cycle(event)`

接入点:

- `apv3test/runtime/phase20_7/runtime.py`
- Stage1-Stage6 的 `run_phase20_7_turn(...)` 返回前统一调用 `complete_turn_cognitive_cycle(...)`。
- Stage0 boundary tick 保持原样, 不被重分类为认知 tick。

完成后每个认知 tick 至少补齐:

- `c_forward`
- `c_backward`
- `cstar_packet.kind = every_tick_min_error_cycle`, 或保留已有更具体 C*。
- `feelings.every_tick_cycle_completed = True`

## 四、严谨验收测试

新增测试文件:

- `tests/test_phase20_8b_every_tick_cognitive_cycle.py`

覆盖内容:

1. 未知文本输入也有每 tick C_forward / C_backward / C*, 但不会产生假 `b_candidates`。
2. 视觉、TTS、idle tick 均共享统一认知循环。
3. Stage0 boundary 不被误判为认知 tick。

专项测试:

```powershell
python -m pytest tests\test_phase20_8b_every_tick_cognitive_cycle.py -q
```

结果:

```text
3 passed in 1.02s
```

全量回归:

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py -q
```

结果:

```text
51 passed in 25.54s
```

红线扫描:

```powershell
rg -n "enumerate_objects_in_image|image_label_map|label_map|teaching_hit|taught_answer|direct_reply|reply_text\s*=\s*taught|raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|hidden_solver|student_side_llm|answer_table|regex" apv3test\runtime\phase20_7 tests\test_phase20_8b_every_tick_cognitive_cycle.py
```

结果:

- 无命中。

## 五、本阶段可以证明什么

本阶段可以证明:

- Stage1-Stage6 的认知 tick 均经过统一 B/C/C* 补齐。
- 未知输入不会被伪造为记忆召回命中。
- 视觉、听觉、TTS、idle、文本、草稿 tick 都能通过统一 RuntimeTickEvent 字段审计预测与归因。
- 新增循环不改 reply_text, 不参与答案生成, 不读原始资产。

## 六、仍待完成

本阶段还不能证明:

- B/C 候选已经完全来自统一 SSP 结构对齐与在线嵌入。
- 六阶段学习协议已经贯通 runtime。
- 任意模态、任意时空距离的长程归因已经完整实现。
- 数学列竖式、数手指、画板、范式行动已经以 AP-native 方式落地。

下一步应继续把当前 `_select_visual_imagination_recall(...)`、`_select_backward_attribution(...)`、`_find_structural_b(...)` 等局部 helper 收束到统一 ExperienceFlow / SSP 结构召回接口中, 让 B/C/C* 不只是事件补齐, 而是真正成为 runtime 的唯一召回与归因心脏。
