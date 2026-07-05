# Phase20.10d 长间隔冷启动复测最终报告

## 1. 目标

Phase20.10d 承接 Phase20.10c。

10c 已经让工作台能看见同一个学习对象的短期生命周期。10d 的目标是把这个生命周期继续推进到“隔一段时间后，AP 自己重新想起并私有复测”的冷启动复测窗口。

这一步不是外部定时考试，不是课程脚本，也不是新增任务表。它把“时间拉开”表达为已有 ExperienceFlow / SSP 里的 tick 间隔证据：

```text
alignment_age_ticks
self_test_gap_ticks
review_gap_ticks
review_count
self_test_count
self_test_success_count
self_test_failure_count
```

然后让这些证据进入已有的：

```text
idle_learning_review -> idle_self_test -> learning_object_lifecycle -> action competition
```

## 2. 设计

新增公式投影：

```text
apv3_phase20_10d_long_interval_cold_retest_window/v1
```

它不是新实体，只是一个运行时投影，挂在 10b 生命周期内：

```text
learning_stage_runtime_progression
  -> learning_object_lifecycle
      -> long_interval_cold_retest_window
```

冷测窗口读取已有证据：

- `experience_alignment`
- `short_structure_flow::learning_review::*`
- `short_structure_flow::self_test::*`
- `teacher_feedback_event`

闲时复盘现在不再只看最近教学对象，而是在已有 alignment 里竞争哪个学习对象更该被冷测。竞争依据是：

- 距离初次学习是否足够久。
- 距离上次自测是否足够久。
- 距离上次复盘是否足够久。
- 之前是否有成功自测作为稳定证据。
- 是否有失败/惩罚导致退行压力。

## 3. 小白例子

先教旧知识：

```text
old cue -> old reply
```

闲时几轮后，再教一个新知识：

```text
fresh cue -> fresh reply
```

继续闲时运行。正常拟人表现应当是：

```text
我刚学了 fresh cue，但 old cue 已经隔了一段时间没测了。
如果 old cue 之前学得比较稳，闲时会把它拉回来复盘。
随后产生一次私有 cold_retest_self_test。
如果还能想起 old reply，稳定度会上升，之后更敢泛化。
如果想错了，退行压力上升，之后更容易复盘/请教/修正。
```

这像人类或儿童：不是老师定闹钟考试，而是脑内某个旧知识点因为“好久没碰但还重要”重新浮上来。

## 4. 落地

修改文件：

- `apv3test/runtime/phase20_7/runtime.py`
- `apv3test/web/static/phase20_7_workbench.js`
- `tests/test_phase20_10d_long_interval_cold_retest.py`

关键落地点：

- 新增 `PHASE20_10D_LONG_INTERVAL_COLD_RETEST_ID`。
- 新增 `_long_interval_cold_retest_window(...)`。
- 新增 `_cold_retest_alignment_for_idle(...)`。
- `_idle_learning_review_metric(...)` 读取长间隔候选，并把其证据写入已有 `idle_learning_review.evidence`。
- `_idle_learning_self_test_from_short_structure_flow(...)` 在长间隔冷测窗口足够强时生成 `cold_retest_self_test`。
- `_learning_object_lifecycle_from_events(...)` 把长间隔冷测窗口并入 10b 生命周期和动作 delta。
- 工作台学习生命周期摘要和审计曲线显示冷测窗口、距自测 tick、距复盘 tick。

## 5. 对抗性审查

### 5.1 是否新增实体

没有。

没有新增 SQLite 表，没有新增冷测任务池，没有新增课程脚本，没有新增外部 scheduler。10d 只是从已有事件与 occurrence 中重建“现在是否该冷测”的主观窗口。

### 5.2 是否伪造冷测通过

没有。

冷测窗口 active 不等于冷测通过。只有已有成功自测证据足够时，生命周期才会进一步接近 `cold_retest_ready`。单纯窗口 active 只表示“该测一测了”。

### 5.3 是否直接写答案

没有。

10d 保留：

```text
writes_answer_directly = False
creates_reply_candidate = False
projection_only = True
```

私有冷测通过 `idle_self_test` 写入短期结构流，不写聊天回复。

### 5.4 是否符合 AP 哲学

符合。

这一步用 AP 原生信息流表达“隔一段时间后重新想起并自测”：

- 当前注意不是外部脚本强拉，而是 ExperienceFlow 中对象竞争出的压力。
- 冷测结果是主观、可错、可被后续反馈修正的。
- 成功会增强稳定和泛化倾向，失败会增强退行、复盘和修正倾向。

### 5.5 仍然可能的不足

10d 仍然是 tick 级和 session 内的冷测窗口。它还不是完整跨天、跨 session、跨设备的长期冷启动复测系统。后续可以把同一逻辑扩展到持久 StatePool 与跨 session 经验包，但仍不能新增外部课程脚本。

## 6. 验收

新增测试：

```text
tests/test_phase20_10d_long_interval_cold_retest.py
```

结果：

```text
2 passed
```

Phase20.10 全组：

```text
9 passed
```

学习相关回归：

```text
tests/test_phase20_9c_learning_loop_metrics.py
tests/test_phase20_9f_idle_learning_review.py
tests/test_phase20_9g_idle_self_test.py
tests/test_phase20_9h_self_test_feedback.py
tests/test_phase20_9i_workbench_learning_lifecycle.py
15 passed
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
python -m py_compile apv3test/runtime/phase20_7/runtime.py apv3test/web_chat.py
PASS

node --check apv3test/web/static/phase20_7_workbench.js
PASS
```

## 7. 当前边界

现在可以证明：

- 闲时 AP 能在已有学习对象中选择更适合长间隔冷测的对象。
- 旧知识点可以在新知识点之后被重新拉回复盘。
- 长间隔证据能进入 `idle_learning_review.evidence`。
- 长间隔窗口足够强时能生成私有 `cold_retest_self_test`。
- 10d trace 能进入 10b 生命周期和工作台审计曲线。
- 没有新增实体、没有写答案、没有绕过 DraftGrid 或 B/C/C*。

仍不能声明：

- 完整跨 session 冷启动复测完成。
- 完整 L1/L2/L3 在线嵌入完成。
- 完整范式自学习完成。
- 数学列竖式完成。
- object-centric 视觉想象完成。
- Phase21 视觉教学泛化闭环完成。

## 8. 下一步

下一步建议进入 Phase20.10e：

把冷测成功/失败继续反向调制“长期稳定感、胆量、谨慎度和泛化阈值”。也就是：冷测成功的知识点，后续低把握相似召回时更敢用；冷测失败的知识点，后续更倾向复盘、请教或局部修正。

这会直接改善用户之前提到的“你好聪明”一类部分匹配泛化：AP 不应该死守固定阈值，而应该从自己过去的成功/失败冷测经验中学出胆量。
