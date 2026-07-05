# APV3.0test Phase4.1 小批旧技能复现门报告

日期: 2026-06-16

## 1. 设计

Phase4.0 已经有最小自由对话 runtime skeleton。Phase4.1 的目标是验证这条链不是只服务单一 percept 示例, 而是能承载一小批旧 GL 成功能力的 APV3.0test 复现。

本阶段选择 5 类最小技能:

1. 问候后继: `你好 -> 我在。`
2. 成语后继: `三顾 -> 茅庐`
3. 简单数学过程: `2+3 -> 列式:2+3=5`
4. 感知槽填充: `percept::yellow + percept::apple`
5. 打断恢复压力: 未完成任务压力 thought 进入竞争并标记慢系统复核。

设计原则:

- 前 4 类都走同一条 `ParadigmDiscoveryEngine -> MinimalDialogueRuntime -> DraftActionRunner -> commit` 链路。
- 数学只复现过程 token, 不接计算器、不用隐藏 solver、不用答案表。
- 感知槽仍输出 percept token 序列, 不直接输出中文目标串。
- 打断恢复只做压力进入竞争门, 不脚本强制恢复。
- 保存恢复后, commits 与 action outcome 要等价。

## 2. 审查完善

本阶段重点审查三条红线:

1. **旧技能复现不能变成旧 harness 脚本复刻。**
   - 测试不调用 GL harness。
   - 不使用目标答案表。
   - 输出来自已发现范式和逐 token 草稿行动。

2. **数学不能偷渡 solver。**
   - 数学测试只把已教过的过程 trace 作为范式 token 复现。
   - 这不是“会泛化做任意数学题”, 只是证明数学过程范式可以进入 APV3.0test skeleton。

3. **打断恢复不能提前夸大。**
   - 当前只验证 `thought::resume_unfinished_task` 在 idle/unfinished 场景下能成为 fast habit candidate 并进入 attention_focus 竞争。
   - `requires_slow_review=True` 表示它需要后续慢系统接管。
   - 还不能宣称完整多任务打断恢复已经复刻完成。

## 3. 通过落地

新增文件:

- `APV3.0test/tests/test_phase4_1_small_skill_reproduction.py`

没有新增 runtime 模块。Phase4.1 复用现有模块:

- `ParadigmDiscoveryEngine`
- `MinimalDialogueRuntime`
- `FastHabitSystem`
- `ActionCompetition`
- `DraftActionRunner`
- `LearningEpisodeWriter`
- `SQLiteRuntimeStore`

核心复现链路:

```text
重复观测 -> 自发现范式 -> runtime 逐 token 写草稿 -> commit -> 行动后果学习 -> SQLite restore
```

## 4. 严谨验收测试

已运行 Phase4.1 专门测试:

```powershell
python -m pytest APV3.0test\tests\test_phase4_1_small_skill_reproduction.py -q
```

结果:

```text
6 passed in 0.29s
```

已运行全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
82 passed in 1.64s
```

runtime 源码禁用通道扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro|黄色苹果" APV3.0test\apv3test
```

结果: 无命中。

临时脚手架词扫描:

```powershell
rg -n "TODO|FIXME|hardcode|shortcut|route|magic" APV3.0test\tests\test_phase4_1_small_skill_reproduction.py
```

结果: 无命中。

测试覆盖:

- `test_reproduces_greeting_successor_through_minimal_runtime`
- `test_reproduces_idiom_successor_without_literal_answer_table`
- `test_reproduces_simple_math_process_tokens_as_paradigm_not_solver`
- `test_reproduces_percept_color_object_slot_skill`
- `test_interruption_recovery_pressure_enters_competition_without_forced_resume`
- `test_small_skill_batch_survives_sqlite_restore`

## 5. 最终汇总

本阶段可以确认:

- APV3.0test skeleton 已能复现一小批旧能力。
- 问候、成语、数学过程、感知槽填充都能通过同一 AP-native 链路产生逐 token 草稿并 commit。
- 打断恢复压力可以作为 thought habit 进入竞争, 且在高慢系统需求下标记复核。
- 保存恢复后, 小批 commits 和 action outcome 等价。
- 全量测试从 Phase4.0 的 76 个增加到 82 个, 没有破坏旧门。

仍不能宣称:

- 旧 GL 全量技能已经复现。
- 完整自由中文开放对话底座已完成。
- Fresh300 已通过。
- 数学泛化能力已完成。
- 完整打断恢复任务执行已完成。

下一步建议:

Phase4.2 应做“小型旧技能扩展 + 失败归因”:

- 加入更多中文对话微技能, 包括自我介绍、情绪回应、不会时澄清。
- 加入更真实的数学过程范式, 但仍不使用 hidden solver。
- 加入打断恢复的后续执行链, 从 pressure thought 进入实际草稿续写。
- 每类都要求 SQLite restore 后行为等价。

只有 Phase4.2/Phase5 稳定后, 才进入更大规模训练和 Fresh 测试。
