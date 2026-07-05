# Phase20.9f 最终报告: 闲时学习复盘接入 AP 主流程

日期: 2026-06-27

## 1. 完成内容

本轮完成 Phase20.9f: 当用户没有输入时, AP 可以从已有经验流中重建最近学习倾向, 让 `idle_think` 私有复盘刚学过或刚能召回的内容。

改动文件:

- `apv3test/runtime/phase20_7/runtime.py`
  - 新增 `PHASE20_9F_IDLE_LEARNING_REVIEW_ID`。
  - 新增 `_idle_learning_loop_carryover_from_experience_flow(...)`。
  - 新增 `_idle_learning_review_metric(...)`。
  - 新增 `_run_idle_learning_review_tick(...)`。
  - `_idle_competition(...)` 支持 `learning_loop_carryover`。
  - 闲时视觉/听觉选择会和学习复盘压力竞争, 避免永远只看最后画面。
  - 复盘 tick 写入 `short_structure_flow::learning_review::*`, 且 `private_thought=True`。

- `tests/test_phase20_9f_idle_learning_review.py`
  - 验证反馈后闲时私有复盘。
  - 验证 teacher-off 召回后闲时自测复盘。
  - 验证空白 session 不伪造复盘。

- `docs/Showcase_Phase20_9f_IdleLearningReview_20260627.html`
  - 提供可打开的展示页, 用小白能懂的方式说明效果和工作台测试步骤。

## 2. 可以证明什么

本轮可以证明:

1. 闲时 tick 已经能读取既有经验流, 重建学习闭环倾向。
2. 刚被教过后, AP 会产生私有复盘, 倾向为 `feedback_only`。
3. 已经 teacher-off 召回后, AP 会产生私有自测复盘, 倾向为 `teacher_off_probe`。
4. 复盘进入短期结构流, 可以被后继 tick 继续利用。
5. 复盘不写聊天回复, 不新增答案候选, 不绕过 AP 主流程。

## 3. 可见效果

真实追踪结果:

```text
FEEDBACK_IDLE
  tick=10
  action=idle_think
  tendency=feedback_only
  learning_loop_delta=0.0371
  drive=0.2871
  narrative=phase20.9f showcase cue -> phase20.9f showcase reply -> 先整理刚学到的联系

TEACHER_OFF_IDLE
  tick=42
  action=idle_think
  tendency=teacher_off_probe
  learning_loop_delta=0.0993
  drive=0.3493
  narrative=phase20.9f showcase exact cue -> phase20.9f showcase exact reply -> 试着自己想起来

EMPTY_IDLE
  tick=1
  action=idle_observe
  has_review=False
  reply=
```

小白解释:

- 刚被教: 它不在聊天框刷屏, 但内部会把“问题 -> 教学答案”的联系整理一遍。
- 已经会: 它在闲时更像自己默念和自测, 看看能不能想起来。
- 什么经验都没有: 它不会假装有想法。

## 4. 如何在底座里测试

工作台:

```text
http://127.0.0.1:8776/phase20_7
```

建议步骤:

1. 输入 `phase20.9f 测试问题`, 并在“教学纠正”里填 `phase20.9f 测试答案`, 发送。
2. 不输入任何内容, 点“闲时 tick”。
3. 看“闲时观察/想法流/tick 回放”, 应该出现私有复盘: `问题 -> 答案 -> 先整理刚学到的联系`。
4. 再输入同一个问题, 让 AP 自己召回。
5. 再点“闲时 tick”, 应该更偏向 `teacher_off_probe`, 叙事接近“试着自己想起来”。

## 5. 验收结果

语法检查:

```powershell
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_9f_idle_learning_review.py
```

结果: 通过。

20.9f 定向测试:

```powershell
python -m pytest tests\test_phase20_9f_idle_learning_review.py -q
```

结果: `3 passed in 1.88s`

相邻链路:

```powershell
python -m pytest tests\test_phase20_9f_idle_learning_review.py tests\test_phase20_9e_learning_loop_carryover.py tests\test_phase20_9d_workbench_learning_loop_panel.py tests\test_phase20_9c_learning_loop_metrics.py tests\test_phase20_9b_learning_protocol_drive_modulation.py tests\test_phase20_9a_learning_protocol_projection.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py -q
```

结果: `30 passed in 20.16s`

Phase20.7 + Phase20.8 + Phase20.9 全链路:

```powershell
$tests = @(rg --files tests | rg "test_phase20_(7|8|9)")
python -m pytest @tests -q
```

结果: `127 passed in 67.26s`

红线扫描:

```powershell
使用既有 Phase20 红线扫描表达式覆盖 runtime 与 20.9f 测试文件。
```

结果: 无命中。

Release demo:

```powershell
python scripts\verify_phase20_7_release_demo.py
```

结果: `OK: Phase20.7 release demo package verified`

## 6. 自审

符合 AP 哲学的点:

- 闲时复盘来自经验流, 不是 UI 或脚本。
- 复盘通过行动竞争选择 `idle_think`, 而不是强行执行。
- 复盘写入短期结构流, 可以参与后继 tick 的统一召回。
- 复盘是私有思考, 不进入聊天框, 避免“主动刷屏”。
- 空白 session 不产生复盘, 防止假拟人。

仍不能声明:

- 不能声明完整六阶段 runtime 已完成。
- 不能声明 L1/L2/L3 在线嵌入已完成。
- 不能声明完整范式自学习已完成。
- 不能声明数学列竖式已完成。
- 不能声明 object-centric 视觉想象已完成。
- 不能声明 Phase21 视觉教学泛化闭环已完成。

## 7. 下一步

下一步建议进入 Phase20.9g: 把 teacher-off / cold-retest 从“闲时倾向和复盘”推进成更明确的跨 tick 验收事件。也就是让 AP 在闲时不仅复盘, 还能形成可审计的“隔一会儿自己测一下是否还记得”的运行证据, 但仍然不能变成外部定时课程脚本。

