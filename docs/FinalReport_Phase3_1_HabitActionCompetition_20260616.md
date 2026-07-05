# APV3.0test Phase3.1 habit 候选接行动竞争 trace 报告

日期: 2026-06-16

## 1. 设计

Phase3.0 已经证明行动后果记忆可以读出 fast habit candidate。Phase3.1 的目标是继续闭合一层: 让 habit candidate 进入同一 tick 的行动竞争 trace。

这一步仍然不是完整执行层, 而是 pre-execution trace:

- 不执行行动器。
- 不写长期记忆。
- 不生成回复文本。
- 不绕过同一行动器互斥。

理论对齐:

- 行动/想法都是一等 SA, 都可以成为 `ActionProposal`。
- `source_system=fast_habit` 只是来源 trace, 不是策略特权。
- `drive` 来自 Phase3.0 的 habit evidence 和 lambda_fast。
- 每个 `actuator_id` 是一个冲突域, 同一 tick 只能保留一个赢家。
- 不同行动器可以并存, 为“一个 tick 多个兼容行动/想法”提供基础。
- `slow_review_pressure > 0` 时, trace 标记 `requires_slow_review`, 但不直接阻止候选。

拟人原则:

- 熟练动作会先冒出来。
- 如果同一只“手”只能做一个动作, 就让最强动作先占位。
- 但注意力聚焦这种“心里动作”和草稿编辑这种“文本动作”可以同时准备。
- 模糊、惊、压力高时, 快反应仍可出现, 但需要慢系统复核。

## 2. 审查完善

审查重点:

1. **候选来源不能变成策略层。**
   - `fast_habit` 只写在 trace 里。
   - 排序只按候选自身 drive, 没有因为来源而额外加权。

2. **同 tick 多行动必须尊重行动器边界。**
   - 同一 `actuator_id` 只选 drive 最高者。
   - 不同 `actuator_id` 的候选可以并存。

3. **慢系统复核不是硬禁令。**
   - `requires_slow_review` 是 trace 标记。
   - 后续 Phase4 tick loop 可以据此让慢系统监督/修订, 但 Phase3.1 不直接剔除候选。

4. **持久化等价性必须保留。**
   - 保存恢复后, 同一输入参数下竞争 trace 必须完全一致。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/action_competition.py`
- `APV3.0test/tests/test_phase3_1_habit_action_competition.py`

更新文件:

- `APV3.0test/apv3test/runtime/__init__.py`

新增 API:

- `ActionProposal`
- `ActuatorCompetitionDecision`
- `ActionCompetitionTrace`
- `ActionCompetition`

核心链路:

```text
action_outcomes
  -> FastHabitSystem.candidates()
  -> ActionProposal.from_habit_candidate()
  -> ActionCompetition.compete()
  -> per-actuator selected/rejected trace
```

## 4. 严谨验收测试

已运行 Phase3.1 专门测试:

```powershell
python -m pytest APV3.0test\tests\test_phase3_1_habit_action_competition.py -q
```

结果:

```text
5 passed in 0.24s
```

已运行全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
72 passed in 1.50s
```

已运行编译检查:

```powershell
python -m py_compile APV3.0test\apv3test\runtime\action_competition.py APV3.0test\apv3test\runtime\__init__.py
```

结果: 通过。

runtime 源码禁用通道扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro|黄色苹果" APV3.0test\apv3test
```

结果: 无命中。

临时脚手架词扫描:

```powershell
rg -n "TODO|FIXME|hardcode|shortcut|route|magic" APV3.0test\apv3test\runtime\action_competition.py APV3.0test\tests\test_phase3_1_habit_action_competition.py
```

结果: 无命中。

测试覆盖:

- habit candidate 可以进入 action competition trace。
- 同一行动器冲突时, 低 drive 候选被 rejected。
- 不同行动器的 action/thought 可以同 tick 并存。
- 高慢系统压力会标记 `requires_slow_review`。
- SQLite 保存恢复后, competition trace 完全复现。

## 5. 最终汇总

本阶段可以确认:

- APV3.0test 已经把 fast habit candidate 接进行动竞争前 trace。
- 快系统习惯不是孤立读数, 已可进入同一 tick 的冲突域选择。
- 同一行动器互斥和不同行动器兼容并存都成立。
- 慢系统复核压力能被保留为 trace, 不硬禁、不硬放行。
- 持久化恢复后, 同一输入下 trace 等价。

仍不能宣称:

- 完整 tick loop 已完成。
- 行动器真实并行执行已完成。
- 自由中文开放对话底座已完成。
- 旧 GL 技能已在 APV3.0test 全量复现。

下一步建议:

Phase4 应做小型自由中文开放对话 runtime skeleton, 把已经通过的组件串成一个可跑 tick 链:

```text
外部/感知输入 -> 边界/跨 tick 分段 -> Bn/Cn 与范式候选 -> slot fill -> habit candidates -> action competition trace -> 草稿行动器逐 token 执行 -> commit 后学习写入 -> SQLite 保存恢复
```

Phase4 通过后, 再进入旧 GL 成功技能小批复现和 Fresh 测试。
