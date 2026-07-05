# Phase20.10a 学习阶段 Runtime 推进最终报告

## 1. 目标

Phase20.10a 承接 Phase20.9z。

目标不是新增一个“课程调度器”, 而是把已有 AP 主流程中的学习信号继续压回行动竞争:

- `learning_loop_metric`: 接触 / 模仿 / 纠错 / 复盘 / 自测 / 泛化 / 教师退场 / 冷启动复测的指标投影。
- `idle_learning_review`: 闲时复盘。
- `idle_self_test` 与 `self_test_feedback`: 私有自测及其成功 / 失败反馈。
- `reward_punish_backward_attribution_consolidation`: 奖惩后的主观归因巩固。
- `edit_outcome_learning`: 草稿修改后的成功 / 剩余误差。
- `action_experience_tuner_projection`: 统一行动经验调参。

Phase20.10a 的核心问题:

> 这些阶段不应该只显示在面板里, 而应该真实影响 AP 下一 tick 的行为。

## 2. 设计

新增公式标识:

`apv3_phase20_10a_learning_stage_runtime_progression/v1`

新增的是投影公式, 不是新实体。

它挂在已有 `learning_loop_carryover` 内:

```text
learning_loop_carryover
  -> learning_stage_runtime_progression
      -> stage_scores
      -> stage_action_deltas
      -> merge back to existing action competition deltas
```

它不会:

- 新增 SQLite 表。
- 新增记忆池。
- 直接生成回复。
- 绕过 B/C/C*。
- 绕过 DraftGrid。
- 写答案表或专用技能脚本。

它只改变已有行动候选的 drive:

- `request_teacher`
- `maintain_unclosed`
- `write_cell`
- `commit_reply`
- `idle_think`
- `integrate_feedback`
- `read_draft`
- `edit_cell`
- `stop_generating`

## 3. 小白例子

### 3.1 刚被教

用户教:

```text
phase20.10a feedback cue -> phase20.10a feedback reply
```

AP 内部会更像:

```text
我刚学到这个, 先模仿、记住、复盘一下。
```

实际表现:

- `dominant_runtime_stage = imitation`
- `write_cell_delta > 0`
- `integrate_feedback_delta > 0`
- `idle_think_delta > 0`

### 3.2 已经能召回

再次输入同一 cue。

AP 内部会更像:

```text
我好像会了, 可以自己试着回答, 之后也可以自测一下。
```

实际表现:

- `dominant_runtime_stage in {self_test, generalization, teacher_exit, cold_retest}`
- `write_cell_delta > 0`
- `commit_reply_delta > 0`
- `request_teacher_delta < 0`

### 3.3 自测失败

如果闲时自测发现自己回忆错了。

AP 内部会更像:

```text
我可能记错了, 先回去纠错、回读、修改或请教。
```

实际表现:

- `self_test_feedback.feedback_kind = self_test_failure`
- `correction > teacher_exit`
- `request_teacher_delta > 0`
- `read_draft_delta > 0`
- `edit_cell_delta > 0`

## 4. 落地

修改文件:

- `apv3test/runtime/phase20_7/runtime.py`
- `tests/test_phase20_10a_learning_stage_runtime_progression.py`

主要落地点:

- 增加 `PHASE20_10A_LEARNING_STAGE_RUNTIME_ID`。
- 增加 `_latest_action_experience_tuner_from_events(...)`。
- 增加 `_apply_learning_stage_runtime_progression(...)`。
- 增加 `_learning_stage_runtime_progression(...)`。
- `_learning_loop_carryover_from_events(...)` 接入 10a 投影。
- `_idle_learning_loop_carryover_from_experience_flow(...)` 接入 10a 投影。
- `_learning_loop_carryover(...)` 显式携带 `self_test_feedback`。
- 修正闲时注意力仲裁: 强视觉想象 SA 在无活跃未闭合时可以先赢过学习复盘, 避免 10a 把视觉内心画面回看压掉。

## 5. 对抗性审查

### 5.1 是否新增实体

没有。

10a 没有新增表、池、外部脚本、专用 solver 或专门课程模块。它只是已有 `learning_loop_carryover` 的运行时投影。

### 5.2 是否写答案

没有。

所有 10a trace 均保留:

- `writes_answer_directly = False`
- `creates_reply_candidate = False`

### 5.3 是否破坏视觉闲时

最初回归发现一个问题:

> 视觉想象刚发生后, 10a 把学习复盘 drive 拉高, 导致 idle_think 压过 idle_visual_focus。

修正:

> 当视觉 drive 已经达到强注意阈值, 且没有活跃未闭合对象时, 视觉 SA 可以先进入 idle_visual_focus。学习复盘仍保留在竞争行, 后续 tick 可继续发生。

对应回归已通过。

### 5.4 是否过度硬编码

当前公式仍有人工设定权重, 但它们不是“某个输入 -> 某个答案”的硬编码, 而是 AP 主流程中的能量调制参数。它读取的是学习指标、奖惩归因、自测反馈、行动经验、编辑结果等通用 AP 信号。

后续仍需要把这些权重继续交给更长期的经验调参。

## 6. 验收

新增测试:

```text
tests/test_phase20_10a_learning_stage_runtime_progression.py
```

结果:

```text
3 passed
```

分层回归:

```text
Phase20.7: 48 passed
Phase20.8: 58 passed
Phase20.9: 76 passed
```

红线扫描:

```text
OK: Phase 20.7-stage8 deliverables present
OK: All red line checks pass on runtime/cognitive
```

常量治理:

```text
OK: Governance check passed (507 numeric constants)
(91 warnings: existing @experimental constants pending rationale)
```

语法编译:

```text
python -m py_compile apv3test/runtime/phase20_7/runtime.py
PASS
```

## 7. 当前边界

现在可以证明:

- 六阶段学习不再只是面板指标。
- 阶段推进能真实进入后继 tick 的行动竞争。
- 教学后更偏模仿 / 复盘。
- 召回稳定后更偏自测 / 泛化 / 教师退场。
- 自测失败后更偏纠错 / 请教 / 回读 / 修改。
- 视觉内心画面不会被学习复盘错误压掉。

仍不能声明:

- 完整 L1/L2/L3 在线嵌入完成。
- 完整六阶段 runtime 全量完成。
- 完整范式自学习完成。
- 数学列竖式完成。
- object-centric 视觉想象完成。
- Phase21 视觉教学泛化闭环完成。

## 8. 下一步

下一步建议进入 Phase20.10b:

把 Phase20.10a 的阶段推进继续接到“学习对象粒度”的稳定追踪中。

也就是说, 当前 10a 已经能在 tick 上判断“现在更像模仿 / 自测 / 纠错”, 下一步要让它围绕同一个学习对象形成更稳定的生命周期:

```text
被教 -> 复盘 -> 自测 -> 成功/失败 -> 调整 -> 再测 -> 教师退场 -> 冷启动复测
```

但仍然必须只使用现有 ExperienceFlow / SSP / StatePool / B/C/C* / action competition, 不新增外部课程脚本。
