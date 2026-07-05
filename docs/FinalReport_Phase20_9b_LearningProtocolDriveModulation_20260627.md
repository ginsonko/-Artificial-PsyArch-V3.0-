# Phase20.9b 最终报告：学习协议调制请教与教师退场驱动力

日期：2026-06-27

## 1. 完成内容

本轮完成 Phase20.9b：把 Phase20.9a 的学习协议投影，推进到 AP 主流程的行动竞争层，让它开始调制 `request_teacher`、`maintain_unclosed` 和教师退场压力。

代码改动：

- `apv3test/runtime/phase20_7/runtime.py`
  - 新增 `PHASE20_9B_LEARNING_PROTOCOL_DRIVE_MODULATION_ID`。
  - 在 `_teacher_request_drive_context(...)` 中接入 `_learning_protocol_request_drive_modulation(...)`。
  - 新增 `_recent_selected_action_count(...)` 与 `_recent_event_count(...)`，从真实 tick 事件统计近期请教与教师反馈。
  - 在 `_competition(...)` 中接入 `_apply_learning_protocol_competition_modulation(...)`。
  - 对 `exact_b0`、`structural_bccstar`、`integrate_feedback` 三类状态压低新请教竞争，但不删除请教动作。

新增测试：

- `tests/test_phase20_9b_learning_protocol_drive_modulation.py`

新增设计文档：

- `docs/Design_Phase20_9b_LearningProtocolDriveModulation_20260627.md`

## 2. 可以证明什么

本轮可以证明：

1. AP 第一次遇到未知对象时，`request_teacher` 不会被学习协议冷却，仍能自然请教。
2. 同一个未闭合对象反复没有得到反馈时，`request_teacher / maintain_unclosed` 驱动力会随近期请教次数与未闭合尝试次数下降。
3. exact B0 召回时，action competition 中的请教行会被教师退场压力压低，让已学经验更容易主导行动。
4. feedback integration tick 中，AP 会降低新请教驱动，把当前能量留给整合教师反馈。
5. 这些调制只改变驱动力与行动竞争，不制造答案，不写回复，不新增候选，不绕过 B/C/C* 或 DraftGrid。
6. 调制审计字段包含 `creates_reply_candidate=False`、`writes_answer_directly=False`，可以被 UI、测试和后续审查直接核对。

## 3. 小白可理解的效果

如果 AP 第一次看到一个不懂的东西，它会问。

如果 AP 连续几次都在想同一个不会的问题，但没人教它，它会慢慢少问一点，转向继续观察、回忆和想。

如果它已经根据经验能想起答案，它会少问老师，更多依赖自己的记忆。

如果老师正在纠正它，它会先整合老师的话，而不是同时又追着问下一个问题。

这一步让 AP 更像一个会学习的小孩：不会时会问，问不到会暂时忍住，会了会少问，被教时会先听。

## 4. 验收结果

定向测试：

```powershell
python -m pytest tests\test_phase20_9b_learning_protocol_drive_modulation.py -q
```

结果：`4 passed in 2.57s`

相邻链路：

```powershell
python -m pytest tests\test_phase20_9b_learning_protocol_drive_modulation.py tests\test_phase20_9a_learning_protocol_projection.py tests\test_phase20_8r_current_referent_expression_binding.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8h_unified_cstar_min_error_integration.py tests\test_phase20_8b_every_tick_cognitive_cycle.py -q
```

结果：`23 passed in 8.45s`

Phase20.7 + Phase20.8 + Phase20.9 当前全链路：

```powershell
$tests = @(rg --files tests | rg "test_phase20_(7|8|9)")
python -m pytest @tests -q
```

结果：`114 passed in 48.31s`

红线扫描：

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|student-side LLM|enumerate_objects_in_image|regex|keyword_route|six_stage_complete|six_stage_learning_complete|online_embedding_converged|l1_l2_l3_complete" apv3test\runtime\phase20_7 runtime\cognitive\state_pool tests\test_phase20_9b_learning_protocol_drive_modulation.py -g "*.py"
```

结果：无命中。

Release demo 验证：

```powershell
python scripts\verify_phase20_7_release_demo.py
```

结果：`OK: Phase20.7 release demo package verified`

## 5. 自审

符合 AP 哲学的点：

- 没有新增外部课程脚本，学习阶段只作为当前 tick 认知状态的投影和调制。
- 没有用关键词判断用户想教什么、想问什么。
- 没有把教师退场写成全局成熟结论，只是在当前 action competition 中降低请教竞争。
- 没有为了效果直接生成答案或固定话术。
- 重复请教降温来自短期事件流和未闭合尝试次数，符合“人会暂时忍住，但未闭合感仍在”的拟人过程。

仍需警惕的点：

- 目前的系数是工程默认值，后续需要接入自适应调参器，让它根据“问得太频繁 / 问得太少 / 学习是否成功”自动微调。
- teacher-off 仍是当前 tick 的竞争压力，不是完整六阶段 runtime 的退场验收。
- cold-retest 仍未完成真实跨时间、跨 session 的冷重测闭环。
- L1/L2/L3 在线嵌入还没有接入这层调制。

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

下一步自然进入 Phase20.9c：把 `feedback_only` 与教师退场从“驱动力调制”继续推进到真实学习闭环指标，例如：

- 什么时候只需要反馈，不需要继续示范；
- 什么时候可以短暂 teacher-off；
- 什么时候需要 cold-retest；
- 失败后怎样回退到弱脚手架或强脚手架。

这些仍必须从 AP 主流程信号中长出来，不能变成外部课程脚本。

