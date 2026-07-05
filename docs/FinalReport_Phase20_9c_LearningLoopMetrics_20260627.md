# Phase20.9c 最终报告：学习闭环指标接入 RuntimeTickEvent

日期：2026-06-27

## 1. 完成内容

本轮完成 Phase20.9c：在每个真实 tick 的学习审计层追加 `learning_loop_metrics`，让 AP 可以看到当前学习闭环更偏向：

- `feedback_only`：老师正在反馈，适合先整合；
- `teacher_off_probe`：已有记忆支持，适合短暂脱离教师；
- `cold_retest_probe`：教师缺席且时间拉开，出现冷重测压力；
- `return_to_scaffold`：把握不足，应回到脚手架。

代码改动：

- `apv3test/runtime/phase20_7/cognitive_cycle.py`
  - 新增 `PHASE20_9C_LEARNING_LOOP_METRICS_ID`。
  - 新增 `_with_learning_loop_metrics(...)`。
  - 新增 `_learning_loop_metrics(...)`。
  - 新增 `_learning_protocol_projection_from(...)`。
  - 新增 `_safe_int(...)`。
  - 在 `complete_every_tick_cognitive_cycle(...)` 中，紧随 20.9a 学习投影后追加闭环指标。

新增测试：

- `tests/test_phase20_9c_learning_loop_metrics.py`

新增设计文档：

- `docs/Design_Phase20_9c_LearningLoopMetrics_20260627.md`

## 2. 可以证明什么

本轮可以证明：

1. AP 首次未知且低把握时，学习闭环指标会主导到 `return_to_scaffold`。
2. 教师反馈整合 tick 中，`feedback_only_readiness` 会上升。
3. exact B0 召回 tick 中，`teacher_off_readiness` 会上升。
4. 教师缺席、时间较晚、仍有记忆证据的 tick 中，`cold_retest_readiness` 会出现。
5. 这些指标只写入审计层，不生成回复，不制造候选，不绕过 B/C/C*。

## 3. 展示效果

用临时 SQLite 跑了三个连续场景，输出如下：

```text
first_unknown
  action= request_teacher stage= weak_scaffold dominant= return_to_scaffold
  feedback= 0.0766 teacher_off= 0.0 cold= 0.0 scaffold= 0.505

teacher_feedback
  action= integrate_feedback stage= strong_scaffold dominant= feedback_only
  feedback= 0.4831 teacher_off= 0.0 cold= 0.0 scaffold= 0.0807

teacher_off_recall
  action= write_cell stage= teacher_off dominant= teacher_off_probe
  feedback= 0.0642 teacher_off= 0.8014 cold= 0.577 scaffold= 0.1133
```

小白解释：

- 第一次不会：脚手架需求最高，所以 AP 倾向问或等待教学。
- 老师反馈：反馈整合最高，所以 AP 倾向先听和记。
- 学过后再问：教师退场最高，所以 AP 倾向靠记忆回答。

## 4. 验收结果

编译：

```powershell
python -m py_compile apv3test\runtime\phase20_7\cognitive_cycle.py tests\test_phase20_9c_learning_loop_metrics.py
```

结果：通过。

定向测试：

```powershell
python -m pytest tests\test_phase20_9c_learning_loop_metrics.py -q
```

结果：`4 passed in 1.59s`

相邻链路：

```powershell
python -m pytest tests\test_phase20_9c_learning_loop_metrics.py tests\test_phase20_9b_learning_protocol_drive_modulation.py tests\test_phase20_9a_learning_protocol_projection.py tests\test_phase20_8r_current_referent_expression_binding.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8b_every_tick_cognitive_cycle.py -q
```

结果：`27 passed in 9.11s`

Phase20.7 + Phase20.8 + Phase20.9 当前全链路：

```powershell
$tests = @(rg --files tests | rg "test_phase20_(7|8|9)")
python -m pytest @tests -q
```

结果：`118 passed in 53.69s`

红线扫描：

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|student-side LLM|enumerate_objects_in_image|regex|keyword_route|six_stage_complete|six_stage_learning_complete|online_embedding_converged|l1_l2_l3_complete" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_9c_learning_loop_metrics.py -g "*.py"
```

结果：无命中。

Release demo 验证：

```powershell
python scripts\verify_phase20_7_release_demo.py
```

结果：`OK: Phase20.7 release demo package verified`

## 5. 自审

符合 AP 哲学的点：

- 闭环指标从 AP tick 的真实信息流中计算，不依赖外部课程脚本。
- 指标是连续倾向，不是硬切状态，因此保留拟人式摇摆和不确定性。
- `teacher_off_readiness` 和 `cold_retest_readiness` 只是压力/倾向，不是“已经会了”的工程断言。
- 没有新增回复路线、答案表、关键词规则或 hidden solver。
- 指标可以直接给 UI 展示，让用户看到 AP 为什么问、为什么听、为什么尝试自己答。

风险与不足：

- `cold_retest_readiness` 目前仍是单 tick 压力，不是完整跨 session 冷重测调度。
- `feedback_only_readiness` 还没有驱动真实“只反馈不示范”的交互策略。
- 指标系数仍是工程默认值，后续需要接入自适应调参器。
- 它仍不是 L1/L2/L3 在线嵌入，也不是完整六阶段 runtime。

## 6. 仍不能声明

仍不能声明：

- 六阶段学习 runtime 全量完成。
- teacher-off / cold-retest 验收系统完成。
- L1/L2/L3 在线嵌入完成。
- 完整范式自学习完成。
- 数学列竖式和任意简单计算完成。
- object-centric 视觉想象完成。
- Phase21 视觉教学与泛化闭环完成。

## 7. 下一步

下一步自然进入 Phase20.9d：让 `learning_loop_metrics` 开始调制“教师退场 / 反馈期 / 冷重测”的后继 tick 行为，但仍必须只通过 AP 主流程信号影响行动竞争，不能新增外部课程脚本。

