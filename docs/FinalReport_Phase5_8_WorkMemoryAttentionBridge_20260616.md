# APV3.0test Phase5.8 工作记忆接入 Bn/Cn/attention 报告

日期: 2026-06-16

## 1. 设计

Phase5.8 的目标是把 Phase5.7 的工作记忆从独立观察模块接入 APV3 主运行链:

```text
idle work-memory recall
  -> recalled sa_bundle
  -> Bn/Cn recall
  -> attention focus
  -> low-granularity draft action
```

本阶段吸收了外部评估中的三个建议:

- 工作记忆容量不能按 LIFO 截断，应按压力和近因保留。
- WorkMemoryItem 应作为状态池一等 PoolEntry，而不是平行任务 store。
- 打断/延续的相似性判断应为后续 learned-vector 语义相似度留口子。

## 2. 审查完善

### 2.1 容量淘汰从 LIFO 改为压力/近因

原先:

```text
rows.insert(0, row)
del rows[max_items:]
```

问题: 低压力新噪声可能挤掉稍旧但高压力的未完成项。

修正:

```text
retention_score = decayed_pressure * recency_gain
```

容量满时保留得分更高的未闭合项。

### 2.2 WorkMemoryItem 进入 state_field_items

每个工作记忆 item 会写入:

```text
sa_type = work_memory_unfinished
energy.P = pressure
energy.A = pressure
energy.R = pressure
```

含义:

- 工作记忆不再只是平行 store。
- 未闭合压力可以作为状态池一等 SA 被后续注意力链路读取。

### 2.3 工作记忆只供焦点，不直接答题

新增 `APV3WorkMemoryAttentionBridge`:

- idle tick 调用 `APV3WorkMemoryRuntime`。
- 若 recall 出未闭合 item，把 `sa_bundle` 作为 cue/focus 交给 `IncrementalTickRuntime`。
- 后续仍由 Bn/Cn/attention/draft action 决定是否行动。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/work_memory_attention.py`
- `APV3.0test/tests/test_phase5_8_work_memory_attention_bridge.py`

修改文件:

- `APV3.0test/apv3test/config/work_memory_config.py`
- `APV3.0test/apv3test/runtime/work_memory.py`
- `APV3.0test/apv3test/runtime/__init__.py`

新增对象:

- `APV3WorkMemoryAttentionBridge`
- `WorkMemoryAttentionBridgeResult`

文件行数:

```text
work_memory.py: 303
work_memory_attention.py: 55
test_phase5_8_work_memory_attention_bridge.py: 104
```

观察: `work_memory.py` 已略超 300 行，暂未形成 god-object，但后续若继续增长，应拆出 pool-entry 写入或相似度工具。

## 4. 严谨验收测试

Phase5.7/5.8 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase5_7_work_memory_recovery.py APV3.0test\tests\test_phase5_8_work_memory_attention_bridge.py -q
```

结果:

```text
8 passed in 0.36s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
129 passed in 2.84s
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
test_phase4_1_small_skill_reproduction.py: test name contains answer_table
test_phase5_5_remediation_loop.py: assertion checks answer_table not in suggestion
test_phase5_7_work_memory_recovery.py: assertion checks if text not in state
draft_action.py: buffer non-empty check
```

审查: 均非 runtime 作弊分支。

## 5. 成功样例

### 5.1 工作记忆恢复并继续行动

教学:

```text
case = skill_resume_math
cue = goal::solve item::math
reply = continue::math
```

工作记忆:

```text
tick10 focus = goal::solve item::math
pressure = 0.95
```

idle 恢复:

```text
tick12 idle recall = goal::solve item::math
tick13 Bn/Cn focus = p:discovered:skill_resume_math
emitted = continue::math
```

含义:

- 工作记忆没有直接生成 `continue::math`。
- 它只把未闭合 SA bundle 交给 Bn/Cn/attention。

### 5.2 WorkMemoryItem 是 PoolEntry

```text
sa_type = work_memory_unfinished
sa_bundle = goal::solve item::math
energy.P = 0.95
energy.A = 0.95
```

### 5.3 容量保留高压力未完成项

配置:

```text
max_items = 1
```

输入:

```text
tick1 goal::cook pressure = 0.95
tick2 noise::brief pressure = 0.05
```

结果:

```text
retained = goal::cook
```

含义:

- 容量限制下不是“新来的都留下”，而是高压力未完成项优先。

### 5.4 无工作记忆时不行动

```text
idle recall = <none>
recall_result = <none>
dialogue_result = <none>
```

## 6. 最终汇总报告

Phase5.8 已完成:

- 工作记忆 idle recall 接入 Bn/Cn/attention。
- WorkMemoryItem 写入状态池，成为 `work_memory_unfinished` PoolEntry。
- 容量淘汰按压力和近因，不再 LIFO。
- 无工作记忆时不会凭空输出。

仍不能宣称:

- 完整能量本体 R/V/P/A/F 动力学已经统一。
- 工作记忆已完全接入自由中文开放对话 runtime。
- 长程多任务恢复、主动教师召唤、复杂计划恢复已经完成。

下一步建议 Phase5.9:

```text
工作记忆 + 奖惩补习 + 多技能冲突的组合验收
```

重点:

- 被打断后恢复到正确技能。
- 恢复后若行动失败，通过 Phase5.5 补习闭环补证据。
- 多个未闭合任务竞争时，pressure / recency / reward 共同决定焦点。
