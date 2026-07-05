# APV3.0test Phase4.0 最小自由对话 runtime skeleton 报告

日期: 2026-06-16

## 1. 设计

Phase4.0 的目标是把前面已经通过的组件串成最小可跑 tick 链, 验证 APV3.0test 已经从“单模块能力”进入“自由对话底座骨架”。

本阶段不是完整中文自由对话, 而是最小 skeleton:

```text
当前焦点/候选池
  -> 范式槽填充
  -> 快系统习惯候选
  -> 行动竞争 trace
  -> 草稿行动器逐 token 执行
  -> commit 后学习写入
  -> SQLite 保存恢复
```

关键原则:

- 薄编排, 不重写范式发现、不重写习惯系统、不重写草稿行动器。
- 每个 draft token 都必须在自己的 tick 中竞争赢过 `draft_editor` 冲突域, 才能进入草稿。
- 如果 fast habit 在 `draft_editor` 冲突域赢了, 范式 token 不会被硬写。
- `attention_focus` 这类想法行动可以和 `draft_editor` 并存。
- 只有完整写完草稿后才允许 commit; commit 后才写正向行动后果学习。

拟人原则:

- 话不是一口倒出来, 而是一个个低粒度动作写入。
- 熟练习惯可以打断或压过当前草稿动作。
- 注意力聚焦这种心里动作可以和文本动作同时准备。
- 未提交草稿不固化为正向长期技能。

## 2. 审查完善

本阶段发现并修正一个重要问题:

初版实现把所有草稿 token 放进同一个 tick 的竞争域, 这会和“同一行动器同 tick 只能一个动作”冲突。修正后:

- 每个 token 单独一个 tick。
- 每个 tick 都重新读取 habit candidates。
- 每个 tick 都生成独立 `ActionCompetitionTrace`。
- 只有该 tick 的 `draft_token::*` 赢得 `draft_editor` 才写入。

这使 Phase4.0 更符合 AP 低粒度行动哲学, 也更接近后续真实 tick loop。

同时, 当 fast habit 抢走 `draft_editor` 后, 草稿行动器没有执行写入。为了让“没有写入”的执行面状态也可审计, runtime 在回合开始会初始化 `draft_runtime`, 但不会写入文本或 commit。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/dialogue_runtime.py`
- `APV3.0test/tests/test_phase4_0_minimal_dialogue_runtime.py`

更新文件:

- `APV3.0test/apv3test/runtime/__init__.py`

新增 API:

- `DialogueTurnInput`
- `DialogueTurnResult`
- `MinimalDialogueRuntime`

核心链路:

```text
DiscoveredParadigm
  -> ParadigmSlotFiller.fill()
  -> FastHabitSystem.candidates()
  -> ActionCompetition.compete()
  -> DraftActionRunner.apply(type_text)
  -> DraftActionRunner.apply(commit)
  -> LearningEpisodeWriter.apply(commit outcome)
```

## 4. 严谨验收测试

已运行 Phase4.0 专门测试:

```powershell
python -m pytest APV3.0test\tests\test_phase4_0_minimal_dialogue_runtime.py -q
```

结果:

```text
4 passed in 0.29s
```

已运行全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
76 passed in 1.73s
```

已运行编译检查:

```powershell
python -m py_compile APV3.0test\apv3test\runtime\dialogue_runtime.py APV3.0test\apv3test\runtime\__init__.py
```

结果: 通过。

runtime 源码禁用通道扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro|黄色苹果" APV3.0test\apv3test
```

结果: 无命中。

临时脚手架词扫描:

```powershell
rg -n "TODO|FIXME|hardcode|shortcut|route|magic" APV3.0test\apv3test\runtime\dialogue_runtime.py APV3.0test\tests\test_phase4_0_minimal_dialogue_runtime.py
```

结果: 无命中。

测试覆盖:

- 范式 token 按 tick 逐个写入, 完整后 commit。
- 强 fast habit 可以在同一 `draft_editor` 冲突域压过范式 token, runtime 不硬写。
- `attention_focus` habit 可以与 `draft_editor` token 同 tick 并存。
- commit 后写入 `text_commit` 奖励行动后果。
- SQLite 保存恢复后, 草稿 commit 和行动后果证据不丢失。

## 5. 最终汇总

本阶段可以确认:

- APV3.0test 已经有最小自由对话 runtime skeleton。
- 范式槽填充、快系统习惯、行动竞争、逐 token 草稿、commit 学习和 SQLite 恢复已可串联。
- 同一行动器同 tick 互斥仍成立。
- 不同行动器的行动/想法并存已成立。
- 未提交草稿不会被正向固化。

仍不能宣称:

- 完整自由中文开放对话底座已完成。
- 完整 APV3.0 数学模型全部落地。
- 旧 GL 成功技能已批量复现。
- Fresh300 已通过。
- 自然语言表层化已完成; 当前最小链路仍以 percept token / SA token 为主。

下一步建议:

Phase4.1 应进入“小批旧技能 APV3.0test 复现”:

1. 问候: `你好 -> 我在。`
2. 成语后继: `三顾 -> 茅庐`
3. 感知槽填充: `percept::yellow + percept::apple`
4. 简单数学过程范式: 不用答案表, 只复现过程槽和逐 token 草稿。
5. 打断恢复压力: 空闲 tick 下未完成任务重新进入竞争。

这些通过后, 再进入更大规模中文对话训练和 Fresh 测试。
