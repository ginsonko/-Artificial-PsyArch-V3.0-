# Phase20.10b 学习对象生命周期投影最终报告

## 1. 目标

Phase20.10b 承接 Phase20.10a。

10a 已经让每 tick 的学习阶段推进能影响行动竞争。10b 的目标是进一步把这些 tick 级阶段收束到“同一个学习对象”的生命周期上:

```text
被教 -> 复盘 -> 自测 -> 成功/失败 -> 调整 -> 再测 -> 教师退场 -> 冷启动复测
```

重要边界:

这不是新增一个外部课程表, 也不是新建“学习对象实体”。它只是从已有 ExperienceFlow / SSP / StatePool / B/C/C* / action competition 里, 对同一 `experience_alignment` 的历史证据做运行时投影。

## 2. 设计

新增公式:

```text
apv3_phase20_10b_learning_object_lifecycle_projection/v1
```

生命周期身份来自已有经验流:

- `alignment_event_id`
- `source_event_id`
- `source_text`
- `target_text`

生命周期证据来自已有表和事件:

- `phase20_7_experience_events`
  - `experience_alignment`
  - `teacher_feedback_event`
- `phase20_7_occurrences`
  - `short_structure_flow::learning_review::*`
  - `short_structure_flow::self_test::*`
- 既有 `learning_loop_carryover`
- 既有 `learning_stage_runtime_progression`

输出挂在:

```text
learning_loop_carryover
  -> learning_stage_runtime_progression
      -> learning_object_lifecycle
```

它会轻量调制 10a 的 `stage_action_deltas`, 但不会直接控制回复。

## 3. 小白例子

### 3.1 同一个知识点逐步稳定

先教:

```text
cue -> reply
```

再问一次, AP 能回忆。

随后闲时:

```text
第一次闲时: 复盘这个 cue -> reply
第二次闲时: 私下自测自己还记不记得
第三次闲时: 看到自测成功, 更接近教师退场 / 冷复测
```

10b 会保持同一个 `learning_object_id`, 并看到:

- `review_count` 增加。
- `self_test_count` 增加。
- `self_test_success_count` 增加。
- 生命周期进入 `retested / teacher_exit_ready / cold_retest_ready`。
- `commit_reply` 倾向上升。
- `request_teacher` 倾向下降。

### 3.2 自测失败后回到调整

如果闲时自测错了:

```text
我以为自己会了, 但回忆错了。
```

10b 会看到:

- `self_test_failure_count` 增加。
- `regression > stability`。
- 生命周期回压到 `adjusted_after_feedback / reviewed / self_tested`。
- `request_teacher / read_draft / edit_cell` 倾向上升。

这更像真实人类学习: 不是线性升级, 而是会因为失败回到纠错和复盘。

## 4. 落地

修改文件:

- `apv3test/runtime/phase20_7/runtime.py`
- `tests/test_phase20_10b_learning_object_lifecycle.py`

关键实现:

- `PHASE20_10B_LEARNING_OBJECT_LIFECYCLE_ID`
- `_learning_object_lifecycle_projection(...)`
- `_learning_object_identity_from_carryover(...)`
- `_learning_object_lifecycle_events(...)`
- `_learning_review_occurrences_for_alignment(...)`
- `_self_test_occurrences_for_alignment(...)`
- `_learning_object_lifecycle_from_events(...)`
- `_merge_learning_stage_with_object_lifecycle(...)`

并在 `_idle_learning_loop_carryover_from_experience_flow(...)` 中把 SQLite 上下文传入 10a/10b 投影, 使闲时复盘和自测能围绕同一学习对象重建生命周期。

## 5. 对抗性审查

### 5.1 是否新增实体

没有。

没有新增 SQLite 表, 没有新增学习对象池, 没有新增课程调度器。所谓生命周期只是每次从已有事件流重建的投影。

### 5.2 是否伪造流程

没有。

10b 只在有真实 `experience_alignment` 和真实 SSP occurrence 证据时 active。没有证据时返回 inactive:

```text
reason = no_database_context / no_learning_object_identity / no_alignment_event
```

普通当前 turn 内如果没有 DB 上下文, 不会假装有生命周期。

### 5.3 是否直接写答案

没有。

10b trace 保留:

- `writes_answer_directly = False`
- `creates_reply_candidate = False`
- `projection_only = True`

### 5.4 是否符合 AP 哲学

符合。

10b 是主观、可错、可被反馈修正的生命周期投影。它不会把“学会了”当成真理, 而是用复盘、自测、失败、成功和奖惩反馈持续调节行动倾向。

## 6. 验收

新增测试:

```text
tests/test_phase20_10b_learning_object_lifecycle.py
```

结果:

```text
2 passed
```

10a + 10b:

```text
5 passed
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

语法:

```text
python -m py_compile apv3test/runtime/phase20_7/runtime.py
PASS
```

## 7. 当前边界

现在可以证明:

- 同一个学习对象可以跨复盘和自测维持同一个 `learning_object_id`。
- 生命周期会随真实 review/self-test occurrence 推进。
- 自测成功会增强稳定/退场倾向。
- 自测失败会回压到调整/纠错倾向。
- 生命周期调制已经进入 10a 的行动 delta, 因而真实影响后继行动竞争。

仍不能声明:

- 完整 L1/L2/L3 在线嵌入完成。
- 完整范式自学习完成。
- 数学列竖式完成。
- object-centric 视觉想象完成。
- Phase21 视觉教学泛化闭环完成。

## 8. 下一步

下一步建议进入 Phase20.10c:

把学习对象生命周期接入工作台可视化和 tick 回放, 让用户能直接看到某个知识点从“被教”到“复盘、自测、失败/成功、教师退场、冷启动复测”的完整过程。

这一步主要是展示和验收增强, 不应该新增认知实体。展示层必须只读取 RuntimeTickEvent / ExperienceFlow / SSP 中已经存在的 10a/10b trace。
