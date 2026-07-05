# APV3.0test Phase5.9 工作记忆 + 补习 + 多技能冲突组合验收报告

日期: 2026-06-16

## 1. 设计

Phase5.9 的目标是把前几阶段的小能力组合起来验证:

```text
工作记忆恢复
  -> Bn/Cn/attention 多技能竞争
  -> 失败时进入补习闭环
  -> 奖惩细化影响后续恢复
```

设计原则:

- 不新增关键词规则。
- 不新增答案表。
- 不让工作记忆直接生成答案。
- 组合失败时优先暴露真实断点，而不是补脚手架。

## 2. 审查完善

### 2.1 初跑失败与修正

初跑时 `work_memory_failure_can_be_remediated_then_recalled` 失败。

原因:

- 测试把补习流程放到了很远的 tick。
- 工作记忆压力按设计随时间衰减。
- 到再次 idle recall 时，未闭合项已经低于恢复阈值。

这说明系统的压力衰减是生效的，不是 bug。但也暴露一个细节:

```text
工作记忆被 idle recall 拉回焦点时，应刷新 last_tick。
```

修正:

- `_idle_recall()` 现在会更新 `last_tick = tick`。
- 组合测试改成连续时间线，而不是人为跳到远未来。

含义:

- “刚刚想起”会重新进入近因窗口。
- 长时间不再想起的任务仍会自然衰减。

### 2.2 组合验收不改核心 runtime

本阶段主要新增测试。除 `last_tick` 刷新外，没有新增答案策略或召回分支。

## 3. 通过落地

新增文件:

- `APV3.0test/tests/test_phase5_9_work_memory_remediation_conflict_combo.py`

修改文件:

- `APV3.0test/apv3test/runtime/work_memory.py`

测试文件行数:

```text
test_phase5_9_work_memory_remediation_conflict_combo.py: 213
work_memory.py: 304
```

观察:

- `work_memory.py` 已超过 300 行，仍保持单一主题。
- 若 Phase5.10 继续扩展，应优先拆分 pool-entry 写入、retention/scoring 或 bridge 相关工具。

## 4. 严谨验收测试

Phase5.7-5.9 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase5_7_work_memory_recovery.py APV3.0test\tests\test_phase5_8_work_memory_attention_bridge.py APV3.0test\tests\test_phase5_9_work_memory_remediation_conflict_combo.py -q
```

结果:

```text
12 passed in 0.38s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
133 passed in 2.96s
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

额外扫描:

```powershell
rg -n "most_common_reply|_observations_for_bucket|remediate:|if percept|if audio|if action|if text|if vision|if task|task_queue|answer_table" APV3.0test\apv3test APV3.0test\tests
```

命中:

```text
draft_action.py: buffer non-empty check
test_phase4_1_small_skill_reproduction.py: test name contains answer_table
test_phase5_5_remediation_loop.py: assertion checks answer_table not in suggestion
test_phase5_7_work_memory_recovery.py: assertion checks if text not in state
test_phase5_9_work_memory_remediation_conflict_combo.py: assertion checks answer_table not in state
```

审查: 均非 runtime 作弊分支。

## 5. 成功样例

### 5.1 工作记忆恢复后进入多技能竞争

教学:

```text
same cue = goal::resume

ctx_math     -> continue::math
ctx_dialogue -> continue::dialogue
```

工作记忆:

```text
focus = goal::resume
pressure = 0.9
```

验证:

```text
context = ctx_math
focus_pid = p:discovered:skill_resume_math
emitted = continue::math

context = ctx_dialogue
focus_pid = p:discovered:skill_resume_dialogue
emitted = continue::dialogue
```

含义:

- 工作记忆只恢复 cue。
- 具体技能由 Bn/Cn/attention 根据 context 竞争。

### 5.2 恢复失败后可补习再召回

初始:

```text
work_memory recalled = goal::resume
dialogue_result = <none>
```

补习:

```text
validation cue = goal::resume
expected = continue::work
diagnosis = bn_not_recalled
remediation = AP-native teaching steps
```

补习后:

```text
work_memory recalled = goal::resume
emitted = continue::work
```

含义:

- 失败不是运行时补丁。
- 通过补习闭环写入 evidence 后，工作记忆恢复可以继续使用新技能。

### 5.3 奖惩细化影响恢复后的选择

教学:

```text
skill_wrong_resume -> wrong::resume
punish_delta = 12.0

skill_right_resume -> right::resume
reward_delta = 1.0
```

工作记忆:

```text
focus = goal::resume
context = ctx_work
```

结果:

```text
skill_wrong_resume.exposed = false
focus_pid = p:discovered:skill_right_resume
emitted = right::resume
```

### 5.4 多个未闭合任务竞争

教学:

```text
goal::urgent -> do::urgent
goal::minor  -> do::minor
```

工作记忆:

```text
goal::minor  pressure = 0.25
goal::urgent pressure = 0.95
```

结果:

```text
recalled = goal::urgent
emitted = do::urgent
```

## 6. 最终汇总报告

Phase5.9 已完成组合验收:

- 工作记忆恢复可以进入多技能竞争。
- context 可以区分同一个恢复 cue 对应的不同技能。
- 恢复失败可以经由补习闭环学会，再被工作记忆召回。
- 惩罚后的错误范式会退出竞争，奖励后的正确范式可胜出。
- 多个未闭合任务会按压力优先恢复。

仍不能宣称:

- 完整自由中文开放对话底座已经完成。
- 长程多轮任务恢复已经完成。
- 主动教师召唤已经完成。
- 完整 R/V/P/A/F 能量统一调度已经完成。

下一步建议 Phase6.0:

```text
主动学习 / 主动召唤教师最小门
```

重点:

- 当 cognitive pressure 长时间高、反复 recall 失败或补习需求明显时，系统生成 `teacher_request` SA。
- 教师响应仍写入 AP-native evidence。
- 随技能熟练度提升，teacher_request 频率自然下降。
