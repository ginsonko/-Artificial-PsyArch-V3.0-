# Phase20.9d 设计：工作台学习闭环可视化面板

日期：2026-06-27

## 1. 目标

Phase20.9c 已经把 `learning_loop_metrics` 写入每个真实 `RuntimeTickEvent.learning_deltas`。但只在测试输出里看数字，不利于用户理解 AP 为什么会问、为什么会听反馈、为什么会尝试自己回答。

Phase20.9d 的目标是把 20.9a/b/c 的学习状态直接接入 Phase20.7 工作台 HTML：

- 中间列新增“学习闭环”卡片；
- tick 回放显示学习阶段和主导倾向；
- “本 tick 为什么这样做”解释中显示闭环指标；
- 审计曲线新增反馈、退场、冷测、脚手架四条曲线；
- 页面只展示真实 `tick_trace.learning_deltas`，不在 UI 里发明认知结果。

## 2. AP 约束

本阶段只做可视化，不新增认知实体：

- 不新增数据库表。
- 不新增回复路线。
- 不新增前端推理模块。
- 不用关键词、正则、答案表或隐藏求解器。
- 不让 UI 生成学习阶段，只读取 runtime 已写入的 `learning_protocol_projection` 与 `learning_loop_metrics`。

## 3. 信息流

```text
RuntimeTickEvent.learning_deltas
  -> learning_protocol_projection
  -> learning_loop_metrics
  -> phase20_7_workbench.js renderLearningLoop(...)
  -> HTML 展示
```

工作台只读这些字段：

```text
current_protocol_stage
dominant_learning_tendency
feedback_only_readiness
teacher_off_readiness
cold_retest_readiness
scaffold_regression_need
evidence.b_support
evidence.cstar_grasp
evidence.teacher_signal
evidence.request_scaffold_signal
```

## 4. 对抗性审查

保留方案：

- 面板放在中间列，因为它解释当前 tick 的学习状态，和“为什么这样做”相邻。
- 默认展示最近一个非 `reply_tts_audio` 的认知 tick，避免朗读 tick 把学习状态盖住。
- 审计曲线用历史 tick 的真实指标绘制，便于看到连续变化。
- tick 回放上显示阶段标签，便于定位哪个 tick 从“弱脚手架”变成“教师退场”。

拒绝方案：

- 拒绝在前端根据文本判断“用户在教我”。
- 拒绝为了演示写独立 demo 数据。
- 拒绝让 UI 修改 AP 行动竞争或未闭合状态。
- 拒绝把 HTML 展示当成六阶段 runtime 已完成的证据。

## 5. 小白测试方式

打开：

```text
http://127.0.0.1:8776/phase20_7
```

推荐测试：

1. 输入一个新问题，例如 `phase20.9d 小测试 这是什么`，发送。
   - 看“学习闭环”卡片，应偏向“回到脚手架”。
2. 在“教学纠正”里填一个答案，例如 `这是一个测试回答`，发送。
   - 看“学习闭环”卡片，应偏向“先听反馈”。
3. 再输入刚才的问题，发送。
   - 看“学习闭环”卡片，应偏向“尝试自己来”。

这三个变化不是前端写死的，而是 runtime 每个 tick 的 `learning_loop_metrics` 改变后自然显示出来。

## 6. 验收标准

1. 静态 HTML 存在 `learningLoopPanel`。
2. JS 存在 `renderLearningLoop(...)`，且只读取 `learning_loop_metrics`。
3. tick 回放、原因解释、审计曲线都能显示学习闭环信息。
4. API 返回的 `tick_trace.learning_deltas` 中有 `learning_loop_metrics`。
5. 未知输入显示 `return_to_scaffold`。
6. 教学后召回显示 `teacher_off_probe`。
7. 前端语法检查、定向测试、全链路测试、红线扫描、release demo 全部通过。

