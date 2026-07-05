# Phase20.9h 最终报告: 自测结果反向调制后继学习倾向

日期: 2026-06-27

## 1. 完成内容

本轮完成 Phase20.9h: `idle_self_test` 的成功/失败结果已经可以被后继 `idle_learning_review_metric` 读取, 并反向调制 teacher-off、cold-retest、scaffold、feedback-only 四类学习倾向。

改动文件:

- `apv3test/runtime/phase20_7/runtime.py`
  - 新增 `PHASE20_9H_SELF_TEST_FEEDBACK_ID`。
  - 新增 `_latest_idle_self_test_feedback(...)`。
  - `_idle_learning_review_metric(...)` 读取自测反馈并调制学习倾向。
  - `_idle_learning_self_test_from_short_structure_flow(...)` 增加防重复门, 避免同一条复盘连续自测。

- `tests/test_phase20_9h_self_test_feedback.py`
  - 验证成功自测稳住 teacher-off。
  - 验证失败自测抬高 scaffold。
  - 验证无 self-test 时不出现反馈包。

- `docs/Showcase_Phase20_9h_SelfTestFeedback_20260627.html`
  - 新增可打开展示页。

## 2. 可以证明什么

本轮可以证明:

1. 自测结果已经不是一次性展示字段, 而能影响后继学习倾向。
2. 成功自测会让 teacher-off 更稳。
3. 失败自测会让 scaffold/request 压力回升。
4. 反馈只来自短期结构流中的 self-test occurrence。
5. 反馈不写聊天回复, 不新增答案候选。

## 3. 可见效果

真实追踪结果:

```text
BEFORE_FEEDBACK
  teacher_off=0.88
  cold=0.856
  scaffold=0.0
  feedback={}

SELF_TEST
  kind=cold_retest_self_test
  grasp=0.8864
  match=1.0

AFTER_FEEDBACK
  teacher_off=0.9864
  cold=0.7551
  scaffold=0.0
  feedback_kind=self_test_success
  feedback_formula=apv3_phase20_9h_self_test_feedback/v1
```

小白解释:

- 自测前: 它觉得自己大概能想起来, 但还有冷重测压力。
- 自测成功: 它更确定自己能想起来, teacher-off 更稳。
- 如果自测失败: 它会更愿意回到脚手架, 而不是假装自己会了。

## 4. 如何在底座里测试

工作台:

```text
http://127.0.0.1:8776/phase20_7
```

建议步骤:

1. 教 AP 一个问题。
2. 再问同一个问题, 让 AP 自己召回。
3. 点第一次“闲时 tick”: 出现 learning_review。
4. 点第二次“闲时 tick”: 出现 idle_self_test。
5. 点第三次“闲时 tick”: 出现带 `self_test_feedback` 的 learning_review。

## 5. 验收结果

语法检查:

```powershell
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_9h_self_test_feedback.py
```

结果: 通过。

20.9h 定向测试:

```powershell
python -m pytest tests\test_phase20_9h_self_test_feedback.py -q
```

结果: `3 passed in 1.72s`

相邻链路:

```powershell
python -m pytest tests\test_phase20_9h_self_test_feedback.py tests\test_phase20_9g_idle_self_test.py tests\test_phase20_9f_idle_learning_review.py tests\test_phase20_9e_learning_loop_carryover.py tests\test_phase20_9d_workbench_learning_loop_panel.py tests\test_phase20_9c_learning_loop_metrics.py tests\test_phase20_9b_learning_protocol_drive_modulation.py tests\test_phase20_9a_learning_protocol_projection.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py -q
```

结果: `36 passed in 14.55s`

Phase20.7 + Phase20.8 + Phase20.9 全链路:

```powershell
$tests = @(rg --files tests | rg "test_phase20_(7|8|9)")
python -m pytest @tests -q
```

结果: `133 passed in 47.84s`

红线扫描:

```powershell
使用既有 Phase20 红线扫描表达式覆盖 runtime 与 20.9h 测试文件。
```

结果: 无命中。

Release demo:

```powershell
python scripts\verify_phase20_7_release_demo.py
```

结果: `OK: Phase20.7 release demo package verified`

## 6. 自审

符合 AP 哲学的点:

- 自测反馈来自短期结构流, 不是外部成绩表。
- 成功/失败只调制学习倾向, 不直接写答案。
- 自测失败会重新提高脚手架需求, 更拟人。
- 自测成功不会被宣称为完整学会, 只是 teacher-off 更稳。

仍不能声明:

- 不能声明完整六阶段 runtime 已完成。
- 不能声明 L1/L2/L3 在线嵌入已完成。
- 不能声明完整范式自学习已完成。
- 不能声明数学列竖式已完成。
- 不能声明 object-centric 视觉想象已完成。
- 不能声明 Phase21 视觉教学泛化闭环已完成。

## 7. 下一步

下一步建议进入 Phase20.9i: 把这套学习闭环从 idle 私有复盘继续接入真实多轮教学阶段的“教师退场/冷重测验收视图”, 让工作台能清楚展示一个知识点从被教、复盘、自测、反馈稳定到可退场的全过程。

