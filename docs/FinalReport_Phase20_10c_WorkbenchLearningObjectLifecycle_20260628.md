# Phase20.10c 工作台学习对象生命周期可视化最终报告

## 1. 目标

Phase20.10c 承接 Phase20.10a / 20.10b。

10a 已经让每 tick 的学习阶段推进进入行动竞争。10b 已经把这些阶段推进收束到同一个学习对象的生命周期投影上。10c 的目标不是继续增加认知功能，而是把这些已经存在于 RuntimeTickEvent / ExperienceFlow / SSP trace 中的证据接到工作台可视化和 tick 回放里，让用户能直接看到一个知识点怎样从：

```text
被教 -> 复盘 -> 自测 -> 成功/失败 -> 教师退场 -> 冷启动复测
```

逐步变化。

本阶段边界：

- 展示层只读已有 trace。
- 不新增 SQLite 表。
- 不新增学习对象实体池。
- 不新增课程脚本或外部调度器。
- 不生成答案、不修改行动竞争、不改变 AP 认知主流程。

## 2. 设计

工作台新增读取路径：

```text
RuntimeTickEvent
  -> action_competition[*]
      -> learning_loop_carryover
          -> learning_stage_runtime_progression
              -> learning_object_lifecycle
```

如果 selected_action 或 feelings 中也携带同一包，则作为 fallback 读取。页面不重新计算生命周期，只选择已有 trace 中最新、最强的投影来展示。

新增前端只读 helper：

- `learningStageRuntime(tick)`
- `learningObjectLifecycle(tick)`
- `learningObjectLifecycleSummaryHtml(lifecycle, tick)`
- `runtimeStageName(value)`
- `lifecycleStageName(value)`
- `shortObjectId(value)`

展示内容：

- tick 回放卡片显示 10a 当前学习阶段。
- tick 回放卡片显示 10b 学习对象短 id 与生命周期阶段。
- 选中 tick 后的解释区显示阶段动作微调和生命周期动作微调。
- 学习生命周期面板显示学习对象摘要、七阶段轨道、复盘/自测/成功/失败计数。
- 审计曲线新增对象稳定、退行、复盘数、自测数。

## 3. 小白例子

可以这样验收：

```text
输入: phase20.10c lifecycle cue
教学纠正: phase20.10c lifecycle reply
发送

再输入: phase20.10c lifecycle cue
发送

之后点几次“闲时 tick”或打开“连续闲时”
```

你应该能在工作台看到：

- 学习生命周期面板出现“学习对象 xxxxxxxx”。
- 阶段从“被教/反馈调整”逐步走向“已复盘/已自测/冷启动复测”。
- 复盘数、自测数逐渐增加。
- 如果自测成功，稳定压力上升，退行压力下降。
- tick 回放里每个相关 tick 都能看到它处在哪个学习阶段。

这更接近“我不是只当场背出来，而是在闲时继续复盘和自测自己有没有学会”。

## 4. 落地

修改文件：

- `apv3test/web/static/phase20_7_workbench.js`
- `apv3test/web/static/phase20_7_workbench.css`
- `tests/test_phase20_10c_workbench_learning_object_lifecycle.py`

没有修改认知主流程：

- `apv3test/runtime/phase20_7/runtime.py` 本阶段未改。
- `apv3test/web_chat.py` 本阶段未改。

这是刻意保持的边界：10c 是只读可视化接线。

## 5. 对抗性审查

### 5.1 是否新增实体

没有。

没有新增学习生命周期表、学习对象池、调度器、课程脚本。`learning_object_lifecycle` 仍然是 10b 从 ExperienceFlow / SSP / 已有 SQLite 事件中重建出来的运行时投影。

### 5.2 是否伪造学习进度

没有。

页面只有在 tick trace 中真实存在 `learning_stage_runtime_progression` 和 `learning_object_lifecycle` 时才显示 10a/10b 信息。没有 trace 时仍回落到旧的学习闭环面板和旧 9i 验收视图。

### 5.3 是否直接写答案或绕过 DraftGrid

没有。

10c 不生成回复候选，不写 DraftGrid，不影响 `commit_reply`。新增测试明确检查：

```text
writes_answer_directly = False
creates_reply_candidate = False
```

### 5.4 是否符合 AP 哲学

符合。

10c 只是把 AP 内部已经发生的阶段投影、生命周期投影、复盘、自测和压力变化呈现出来。它不会把“学会了”当成外部真理标签，而是展示 AP 对同一个学习对象的主观稳定度、退行压力和冷测压力。

### 5.5 仍然可能的不足

这一步只是把 10a/10b 展示清楚，还不是完整六阶段 runtime 的终点。它不能替代后续的 L1/L2/L3 在线嵌入、完整范式自学习、数学列竖式、object-centric 视觉想象和 Phase21 视觉教学泛化闭环。

## 6. 验收

新增测试：

```text
tests/test_phase20_10c_workbench_learning_object_lifecycle.py
```

结果：

```text
2 passed
```

10a + 10b + 10c：

```text
7 passed
```

相邻工作台回归：

```text
tests/test_phase20_9i_workbench_learning_lifecycle.py
tests/test_phase20_9d_workbench_learning_loop_panel.py
5 passed
```

分层回归：

```text
Phase20.7: 48 passed
Phase20.8: 58 passed
Phase20.9: 76 passed
```

红线扫描：

```text
OK: Phase 20.7-stage8 deliverables present
OK: All red line checks pass on runtime/cognitive
```

常量治理：

```text
OK: Governance check passed (507 numeric constants)
(91 warnings: existing @experimental constants pending rationale)
```

语法检查：

```text
node --check apv3test/web/static/phase20_7_workbench.js
PASS

python -m py_compile apv3test/runtime/phase20_7/runtime.py apv3test/web_chat.py
PASS
```

## 7. 当前边界

现在可以证明：

- 工作台可以读出 10a 学习阶段运行投影。
- 工作台可以读出 10b 学习对象生命周期投影。
- 同一个学习对象的复盘数、自测数、稳定度、退行压力能跨 tick 连续展示。
- tick 回放能解释该 tick 为什么更偏向复盘、自测、请教、回复或修改。
- 展示层不新增认知实体，不写答案，不影响 AP 主流程。

仍不能声明：

- 完整 L1/L2/L3 在线嵌入完成。
- 完整范式自学习完成。
- 数学列竖式完成。
- object-centric 视觉想象完成。
- Phase21 视觉教学泛化闭环完成。

## 8. 下一步

下一步建议进入 Phase20.10d：

把“同一个学习对象的生命周期”从展示继续反馈到长期可追踪的冷启动复测验收流程中，但仍然不能新增外部课程脚本。做法应是让已有 ExperienceFlow / SSP / StatePool / B/C/C* / action competition 在跨 session 或更长 idle 间隔后自然重遇同一对象，并把冷测成功/失败继续写成可审计 trace。

更直白一点：现在你能在工作台看到它学一个知识点的短期生命线；下一步要让它过一段时间后还能自己重新碰一下、测一下、忘了就回去复盘，记住了就更敢泛化。
