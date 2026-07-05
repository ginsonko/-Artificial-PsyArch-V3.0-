# Phase20.9i 设计: 工作台学习生命周期验收视图

日期: 2026-06-27

## 1. 目标

Phase20.9e-h 已经让 `learning_loop_metrics`、闲时复盘、私有自测和自测反馈稳定进入 AP 主流程。Phase20.9i 不新增认知能力, 只把这条链路做进工作台, 让用户能直接看见:

```text
教学/反馈 -> 闲时复盘 -> 私有自测 -> 自测反馈稳定
```

拟人对应:

- 刚被教过: “我听到了老师怎么说。”
- 闲时复盘: “我把刚才学的东西在心里整理一遍。”
- 私有自测: “我不看老师, 自己想一下能不能想起来。”
- 反馈稳定: “想起来了就更敢自己说, 想错了就回到脚手架。”

## 2. AP 约束

本阶段遵守:

- 不改 runtime 认知决策。
- 不新增数据库表。
- 不新增课程脚本或成绩表。
- 不让 UI 生成学习状态。
- 不让 UI 判断成功/失败。
- 不把自测内容写进聊天框。
- 只读取真实 `RuntimeTickEvent` / `tick_trace` 字段。

## 3. 信息流

```text
RuntimeTickEvent.learning_deltas.experience_alignment_written
RuntimeTickEvent.feelings.idle_learning_review
RuntimeTickEvent.feelings.idle_self_test
RuntimeTickEvent.feelings.idle_learning_review.self_test_feedback
  -> workbench learningLifecyclePanel
  -> audit chart: 自测把握 / 反馈稳定
```

工作台只做投影:

```text
tick history -> renderLearningLifecycle(...)
```

不做:

```text
UI state -> AP learning state
```

## 4. 数学/字段形式

生命周期四段:

```text
F = latest tick with experience_alignment_written or integrate_feedback
R = latest tick with idle_learning_review
S = latest tick with idle_self_test
B = latest tick with self_test_feedback
```

显示量:

```text
source_text = R.source_text or S.source_text
target_text = R.target_text or S.expected_text
self_test_grasp = S.self_test_grasp or B.self_test_grasp
stable_value = 1 if B.feedback_kind == self_test_success else max(0.18, B.mismatch_pressure)
```

空缺规则:

```text
if phase tick missing:
  show "等待真实 RuntimeTickEvent"
```

这保证前端不会补编不存在的学习链路。

## 5. 对抗性审查

保留方案:

- 用工作台展示跨 tick 学习链, 解决用户看不懂“它到底怎么学”的问题。
- 只读已有 tick 字段, 不影响 AP 内部状态。
- 自测成功/失败仍由 runtime 产生, UI 只显示。
- 审计曲线新增 `自测把握` 和 `反馈稳定`, 便于连续观察。

拒绝方案:

- 拒绝在前端维护“知识点状态机”。
- 拒绝用 UI 本地变量判断 AP 是否学会。
- 拒绝把 expected/recalled 写成答案表。
- 拒绝为了展示效果伪造复盘或自测。

## 6. 验收标准

1. 工作台存在 `learningLifecyclePanel`。
2. JS 存在 `renderLearningLifecycle(...)`。
3. 面板读取 `experience_alignment_written`、`idle_learning_review`、`idle_self_test`、`self_test_feedback`。
4. 审计曲线显示 `自测把握` 和 `反馈稳定`。
5. 真实 API 能跑出完整四段链路。
6. 前端语法检查通过。
7. Phase20.7/20.8/20.9 回归通过。
8. 红线扫描无命中。

