# APV3.0test Phase5.7 工作记忆与打断恢复报告

日期: 2026-06-16

## 1. 设计

Phase5.7 的目标是最小复刻“工作记忆 / 跨 tick 打断恢复”:

- 多 tick 的连续焦点可以作为一个临时整体进入工作记忆。
- 惊扰输入可以转移当前焦点，但不能擦掉未闭合任务。
- 空闲 tick 时，未闭合压力可以把工作记忆重新拉回焦点。
- 已闭合内容不应污染下一个任务。
- 所有输入都是一等 SA，不区分文本、视觉、听觉、行动等模态。

本阶段不做传统 task queue，不识别任务名，不根据 token 字符串分支，只使用:

```text
focus_tokens
pressure
closure
surprise
idle
```

## 2. 审查完善

### 2.1 第一次失败与修正

初版把相邻 tick 记成两个工作记忆条目:

```text
tick1 = goal::draw object::apple
tick2 = goal::draw color::yellow
```

空闲回忆时选中了压力更高的 tick1，而不是把两次焦点作为整体。

这个失败暴露了真实理论问题: 工作记忆不应只是最近条目列表，而应能把 0.5-2 秒内相关焦点整合成整体。

修正:

- 若新 focus bundle 与未闭合条目有重叠 SA，则合并 bundle。
- 合并时保留顺序并去重。

结果:

```text
goal::draw object::apple
+ goal::draw color::yellow
= goal::draw object::apple color::yellow
```

### 2.2 打断不是删除

当 surprise 足够高且新 focus 与旧未闭合 item 不重叠时:

- 新输入成为当前 active item。
- 旧未闭合 item 记录 `interrupted_by`。
- 旧 item 的 pressure 仍可在 idle tick 恢复。

### 2.3 闭合后不污染

当 closure 达到阈值:

- item 标记为 closed。
- idle recall 跳过 closed item。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/config/work_memory_config.py`
- `APV3.0test/apv3test/runtime/work_memory.py`
- `APV3.0test/tests/test_phase5_7_work_memory_recovery.py`

修改文件:

- `APV3.0test/apv3test/runtime/__init__.py`

新增对象:

- `APV3WorkMemoryConfig`
- `APV3WorkMemoryRuntime`
- `WorkMemoryTickInput`
- `WorkMemoryItem`
- `WorkMemoryTickResult`

文件行数:

```text
work_memory.py: 238
test_phase5_7_work_memory_recovery.py: 75
work_memory_config.py: 16
```

## 4. 严谨验收测试

Phase5.7 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase5_7_work_memory_recovery.py -q
```

结果:

```text
4 passed in 0.32s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
125 passed in 2.96s
```

红线扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro|llm_policy|if vision|if text|黄色苹果" APV3.0test\apv3test
```

结果:

```text
APV3.0test\apv3test\runtime\draft_action.py:126:        if text:
```

审查: 这是草稿 buffer 非空检查，不是文本模态特权。

工作记忆额外扫描:

```powershell
rg -n "most_common_reply|_observations_for_bucket|remediate:|if percept|if audio|if action|if text|if vision|if task|task_queue" APV3.0test\apv3test APV3.0test\tests
```

结果:

```text
APV3.0test\tests\test_phase5_7_work_memory_recovery.py:75:    assert "if text" not in str(recalled.state).lower()
APV3.0test\apv3test\runtime\draft_action.py:126:        if text:
```

审查:

- 测试里的 `"if text"` 是断言状态中没有该字符串。
- `draft_action.py` 仍是草稿 buffer 非空检查。

## 5. 成功样例

### 5.1 跨 tick 合并

输入:

```text
tick1 focus = goal::draw object::apple
tick2 focus = goal::draw color::yellow
tick3 idle = true
```

结果:

```text
recalled = goal::draw object::apple color::yellow
closed = false
```

### 5.2 打断后恢复

输入:

```text
tick1 focus = goal::solve item::math, pressure = 0.95
tick2 focus = interrupt::noise, surprise = 1.0
tick3 idle = true
```

结果:

```text
interrupted_item = goal::solve item::math
recalled_item = goal::solve item::math
interrupted_by = interrupt::noise
```

### 5.3 闭合后不污染

输入:

```text
tick1 focus = goal::reply topic::done, closure = 1.0
tick5 idle = true
```

结果:

```text
recalled_item = <none>
closed = true
```

### 5.4 模态平权

输入:

```text
focus = percept::yellow audio::tone_high action::point
```

结果:

```text
recalled = percept::yellow audio::tone_high action::point
```

含义:

- 工作记忆不关心模态名称。
- 所有 SA 都作为普通 token bundle 处理。

## 6. 最终汇总报告

Phase5.7 已完成最小工作记忆 / 打断恢复门:

- 跨 tick 相关焦点可合并为整体。
- 惊扰打断不会擦掉未闭合项。
- 空闲 tick 可通过压力恢复未闭合项。
- 已闭合项不会污染后续任务。
- 工作记忆模块保持模态平权。

仍不能宣称:

- 完整人类级工作记忆容量和注意控制完成。
- 工作记忆已经接入完整自由对话 runtime。
- 复杂多任务计划恢复完成。

下一步建议 Phase5.8:

```text
工作记忆与 Bn/Cn/attention 对接
```

重点:

- idle recall 的 `sa_bundle` 进入当前 focus。
- 通过 Bn/Cn 召回对应范式。
- 由 action competition 决定是否继续草稿行动。
- 保持工作记忆只供能/供焦点，不直接生成答案。
