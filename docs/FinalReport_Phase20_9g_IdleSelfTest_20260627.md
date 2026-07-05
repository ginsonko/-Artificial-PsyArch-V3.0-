# Phase20.9g 最终报告: teacher-off / cold-retest 闲时自测事件

日期: 2026-06-27

## 1. 完成内容

本轮完成 Phase20.9g: 闲时复盘不再只是倾向展示。AP 可以在后继闲时 tick 中读取上一条 `learning_review` 短期结构流 occurrence, 并在 teacher-off / cold-retest 压力足够时生成私有自测事件。

改动文件:

- `apv3test/runtime/phase20_7/runtime.py`
  - 新增 `PHASE20_9G_IDLE_SELF_TEST_ID`。
  - 新增 `_idle_learning_self_test_from_short_structure_flow(...)`。
  - 新增 `_run_idle_learning_self_test_tick(...)`。
  - 新增 `short_structure_flow::self_test::*` 写入路径。
  - 自测 tick 写入 `c_forward` 的私有召回与 `c_backward` 的来源追踪。

- `tests/test_phase20_9g_idle_self_test.py`
  - 验证第一个 idle 先复盘。
  - 验证第二个 idle 才自测。
  - 验证 feedback-only 不强行自测。

- `docs/Showcase_Phase20_9g_IdleSelfTest_20260627.html`
  - 新增可打开展示页。

## 2. 可以证明什么

本轮可以证明:

1. teacher-off / cold-retest 不再只是单 tick 倾向, 已经可以形成跨 tick 私有自测事件。
2. 自测来源是短期结构流中的上一条学习复盘, 不是外部课程脚本。
3. 自测不进入聊天框, 只进入私有 tick 与短期结构流。
4. 自测有 forward recall 和 backward source trace, 可以审计“想起了什么”和“从哪里来的”。
5. feedback-only 阶段不会被强行推进成考试。

## 3. 可见效果

真实追踪结果:

```text
REVIEW
  tick=37
  action=idle_think
  review=True
  self_test=False
  tendency=teacher_off_probe
  narrative=phase20.9g showcase cue -> phase20.9g showcase reply -> 试着自己想起来

SELF_TEST
  tick=38
  action=idle_think
  kind=cold_retest_self_test
  grasp=0.8864
  match=1.0
  expected=phase20.9g showcase reply
  recalled=phase20.9g showcase reply
  narrative=phase20.9g showcase cue -> phase20.9g showcase reply -> cold self-test grasp 0.89

FEEDBACK_ONLY_SECOND_IDLE
  action=idle_think
  self_test=False
  review_tendency=feedback_only
  reply=
```

小白解释:

- 第一次闲时: 它先复盘刚才学过或刚想起来的联系。
- 第二次闲时: 如果它已经有把握或过了一段认知距离, 它会私下测一下自己还能不能想起来。
- 刚被教完: 它仍然先整理, 不会马上考试。

## 4. 如何在底座里测试

工作台:

```text
http://127.0.0.1:8776/phase20_7
```

建议步骤:

1. 输入 `phase20.9g 测试问题`, 在“教学纠正”里填 `phase20.9g 测试答案`, 发送。
2. 再输入同一个问题, 让 AP 自己召回。
3. 点一次“闲时 tick”: 应该看到 `learning_review`, 类似“试着自己想起来”。
4. 再点一次“闲时 tick”: 应该看到 `idle_self_test`, 包含 expected/recalled/grasp/source trace。
5. 如果只教学不让它自己召回, 再点闲时 tick, 应该仍偏 feedback-only 整理, 不强行自测。

## 5. 验收结果

语法检查:

```powershell
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_9g_idle_self_test.py
```

结果: 通过。

20.9g 定向测试:

```powershell
python -m pytest tests\test_phase20_9g_idle_self_test.py -q
```

结果: `3 passed in 1.91s`

相邻链路:

```powershell
python -m pytest tests\test_phase20_9g_idle_self_test.py tests\test_phase20_9f_idle_learning_review.py tests\test_phase20_9e_learning_loop_carryover.py tests\test_phase20_9d_workbench_learning_loop_panel.py tests\test_phase20_9c_learning_loop_metrics.py tests\test_phase20_9b_learning_protocol_drive_modulation.py tests\test_phase20_9a_learning_protocol_projection.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py -q
```

结果: `33 passed in 17.52s`

Phase20.7 + Phase20.8 + Phase20.9 全链路:

```powershell
$tests = @(rg --files tests | rg "test_phase20_(7|8|9)")
python -m pytest @tests -q
```

结果: `130 passed in 65.71s`

红线扫描:

```powershell
使用既有 Phase20 红线扫描表达式覆盖 runtime 与 20.9g 测试文件。
```

结果: 无命中。

Release demo:

```powershell
python scripts\verify_phase20_7_release_demo.py
```

结果: `OK: Phase20.7 release demo package verified`

## 6. 自审

符合 AP 哲学的点:

- 自测来自上一条短期结构流复盘, 是跨 tick 的。
- 自测仍然是私有 `idle_think`, 不进入聊天框。
- 自测有主观性和可能错误标记, 保留拟人式不确定性。
- 自测结果继续写入短期结构流, 后继 tick 可以沿它发展。

仍不能声明:

- 不能声明完整六阶段 runtime 已完成。
- 不能声明 L1/L2/L3 在线嵌入已完成。
- 不能声明完整范式自学习已完成。
- 不能声明数学列竖式已完成。
- 不能声明 object-centric 视觉想象已完成。
- 不能声明 Phase21 视觉教学泛化闭环已完成。

## 7. 下一步

下一步建议进入 Phase20.9h: 把自测事件的成功/失败反过来轻量调制后继学习倾向。比如自测把握高时, teacher-off 权重更稳; 自测把握低或矛盾时, scaffold / request_teacher 压力回升。仍然必须通过 AP 主流程, 不能变成外部成绩表。

