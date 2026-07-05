# APV3.0test Phase3.0 快系统习惯候选门报告

日期: 2026-06-16

## 1. 设计

本阶段进入 APV3.0test 的 Phase3: 快系统 habit action / habit thought。目标不是做捷径回复, 而是让已经被奖惩和行动后果支持过的行动/想法, 在低认知压、高把握场景下可以作为快系统候选快速胜出。

理论对齐:

- 习惯来自 AP-native `action_outcomes`, 也就是行动后果记忆。
- 奖励、惩罚、支持量、近因、上下文匹配共同决定 `habit_strength`。
- `lambda_fast` 使用 APV3.0 能量稿中的加性 logit 思路: 熟悉/把握/习惯可以抬高快系统倾向, 慢系统需求会压低快系统倾向。
- 习惯系统只提出候选, 不直接执行, 不替代行动竞争。
- 同一行动器同一 tick 仍只能有一个行动; 不同行动器的兼容候选可以并存, 为后续“一 tick 多行动/多想法”打基础。

拟人原则:

- 熟练且常被奖励的动作会更像“顺手反应”。
- 被惩罚过的动作在相似场景会自然变弱。
- 当前场景不像以前时, 旧习惯不会被硬删, 但会因为上下文不匹配而降权。
- 思维动作也可以是习惯, 例如注意力自动聚焦到某个相关频段。

## 2. 审查完善

本阶段重点防止三个偏离:

1. **不能把 habit 写成答案表或快速路线。**
   - 设计中没有文本匹配路线, 只读 `action_outcomes`。
   - 候选是 action/thought SA, 不是回复句子。

2. **不能破坏行动器互斥。**
   - `FastHabitSystem.select_compatible()` 只保留每个 `actuator_id` 的最高 drive 候选。
   - 不同行动器候选可以并存, 但执行仍由后续行动器层决定。

3. **不能让支持量无限累加成不可逆强迫。**
   - reward / punish / support 都使用有界趋近函数。
   - punishment 可以压低同情境下的 habit drive。
   - context mismatch 会降权, 但不擦除证据。

本阶段没有新增策略层, 只增加一个快系统候选读出层。它属于 Phase3.0 observe/propose gate, 后续接完整 tick loop 前仍需验证与实际 `ΔL'` 的相关性。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/config/habit_config.py`
- `APV3.0test/apv3test/runtime/habit_system.py`
- `APV3.0test/tests/test_phase3_0_fast_habit_system.py`

更新文件:

- `APV3.0test/apv3test/config/__init__.py`
- `APV3.0test/apv3test/runtime/__init__.py`
- `APV3.0test/apv3test/runtime/learning_writer.py`

新增 API:

- `APV3HabitConfig`
- `HabitCandidate`
- `FastHabitSystem`

学习写入扩展:

- `LearnedActionOutcome.support_delta`
- `LearnedActionOutcome.actuator_id`
- `LearnedActionOutcome.outcome_kind`
- `LearnedActionOutcome.context_tags`
- `LearnedActionOutcome.last_tick`

这些字段让习惯候选可以从标准教学协议/实时学习链路写入, 再通过 SQLite 保存恢复, 而不是只靠手工状态。

## 4. 严谨验收测试

已运行 Phase3 专门测试:

```powershell
python -m pytest APV3.0test\tests\test_phase3_0_fast_habit_system.py -q
```

结果:

```text
5 passed in 0.39s
```

已运行全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
67 passed in 1.48s
```

已运行编译检查:

```powershell
python -m py_compile APV3.0test\apv3test\config\habit_config.py APV3.0test\apv3test\runtime\habit_system.py APV3.0test\apv3test\runtime\learning_writer.py APV3.0test\apv3test\runtime\__init__.py APV3.0test\apv3test\config\__init__.py
```

结果: 通过。

runtime 源码禁用通道扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro|黄色苹果" APV3.0test\apv3test
```

结果: 无命中。

临时脚手架词扫描:

```powershell
rg -n "TODO|FIXME|hardcode|shortcut|route|magic" APV3.0test\apv3test\runtime\habit_system.py APV3.0test\apv3test\config\habit_config.py APV3.0test\tests\test_phase3_0_fast_habit_system.py
```

结果: 无命中。

测试覆盖:

- 高奖励/高支持/低慢系统需求时, 快系统习惯候选强。
- 惩罚会压低相似情境下的习惯 drive。
- 上下文不匹配会降权, 但不删除证据。
- 同一行动器同 tick 只保留一个赢家; 不同行动器可并存。
- SQLite 保存恢复后, habit/action outcome 状态仍可读出。

## 5. 最终汇总

本阶段可以确认:

- APV3.0test 已有最小快系统习惯候选门。
- 熟练行动/想法可以由奖惩和行动后果记忆读出, 并进入快系统候选。
- 惩罚、上下文不匹配、慢系统需求都能自然压低习惯倾向。
- 不同行动器兼容候选可以并存, 为后续“一 tick 多行动/多想法”提供 AP-native 基础。
- 持久化恢复后 habit evidence 不丢失。

仍不能宣称:

- 完整快系统 tick loop 已完成。
- 完整自由中文开放对话底座已完成。
- 多行动执行层已经完成。
- 旧 GL 成功技能已在 APV3.0test 全量复现。

下一步建议:

Phase3.1 应做 `fast/slow arbitration trace` 和 `habit candidate -> action competition` 的小闭环, 把 Phase3.0 候选接入草稿行动器/注意力行动器的竞争前 trace。通过后, 再进入 Phase4 小型自由中文开放对话 runtime, 串起范式发现、槽填充、快系统习惯、草稿行动和持久化学习。
