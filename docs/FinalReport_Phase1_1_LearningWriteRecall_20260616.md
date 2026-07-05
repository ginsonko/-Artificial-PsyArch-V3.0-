# APV3.0test Phase1.1 学习写入 -> 保存 -> 恢复 -> 再召回 报告

日期: 2026-06-16

## 1. 设计

本轮目标是验证实时学习链路的最小持久化闭环:

> 一个新教学 episode 写入 AP runtime ontology state 后, 保存到 SQLite, 恢复后仍能被 Bn/Cn/ParadigmSA/ActionOutcome/learned token probe 召回。

本轮仍不接旧自由对话主链, 不跑 Fresh300, 不用任何整句回复捷径。它只验证“后天教学证据”是否能作为 AP-native 运行本体被保存和恢复。

教学 episode 写入对象:

- learned token/vector/support
- explicit transition / successor edge
- ParadigmSA
- Bn candidate feature evidence
- ActionOutcomeMemory
- PerceptPrototype
- learning receipt

核心原则:

- `LearningEpisodeWriter` 只是证据写入器, 不选择回复, 不推理路线, 不改变召回策略。
- 奖惩只进入行动后果记忆, 不直接改文本。
- 重复教学合并 support, 不复制重复边。
- 写入后的 state 必须能通过已有 Phase1.0 parity probe 验证。
- SQLite projection 表必须能直接读到新学内容, 不能只靠压缩 blob 往返。

## 2. 审查完善

审查结论:

- Phase1.0 的 `run_parity_probe` 已能读取 Bn/Cn/token/ParadigmSA/ActionOutcome/PerceptPrototype。
- Phase0.3 的 `SQLiteRuntimeStore` 已能保存全真 state envelope 并投影五类运行本体表。
- 因此 Phase1.1 不需要改持久化底层, 只需要新增一个最小学习写入层。

风险边界:

- 写入器不能变成策略层。
- 写入器不能创建回答捷径或规则分支。
- 写入器不能依赖 audit db。
- 写入器不能把重复教学变成重复 edge 噪声。

## 3. 通过落地

新增/更新文件:

- `APV3.0test/apv3test/runtime/learning_writer.py`
- `APV3.0test/apv3test/runtime/__init__.py`
- `APV3.0test/tests/test_phase1_1_learning_write_recall.py`

新增 API:

- `LearningEpisode`
- `LearningEpisodeWriter`
- `LearnedToken`
- `LearnedTransition`
- `LearnedParadigm`
- `LearnedBnCandidate`
- `LearnedActionOutcome`
- `LearnedPerceptPrototype`

最小教学样例:

- episode: `teach:morning_greeting:v1`
- cue: `早安`
- successor: `早安，我在。`
- paradigm: `p:morning_greeting_successor`
- action: `type_char`
- percept prototype: `audio:morning_tone`

## 4. 严谨验收测试

已运行:

```powershell
python -m pytest APV3.0test/tests -q
```

结果:

```text
24 passed in 0.98s
```

已运行:

```powershell
$files = Get-ChildItem -Path APV3.0test\apv3test\config,APV3.0test\apv3test\runtime -Filter *.py | ForEach-Object { $_.FullName }; python -m py_compile @files
```

结果: 通过。

已运行禁用通道扫描:

```powershell
rg -n "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro" APV3.0test\apv3test APV3.0test\tests
```

结果: 无命中。

新增测试覆盖:

- 新教学 episode 写入后, `morning_greeting` probe 可以召回:
  - Bn top: `memory:morning_greeting_pair`
  - Cn: `早安 -> 早安，我在。`
  - learned token: `早安`
  - ParadigmSA: `p:morning_greeting_successor`
  - ActionOutcome: `type_char.reward_support = 2.0`
  - PerceptPrototype: `audio:morning_tone`
- 写入 state 保存到 SQLite 后恢复, probe 结果与内存态一致。
- 重复教学不会复制同一条 transition edge, 而是合并 support。
- 新学内容进入 SQLite projection 表:
  - `online_embedding_tokens`
  - `explicit_transitions`
  - `paradigm_sa`
  - `action_outcomes`
  - `percept_prototypes`

## 5. 最终汇总

Phase1.1 已通过。

这说明:

- APV3.0test 已具备最小“后天学习证据写入 -> 持久化 -> 恢复 -> 再召回”闭环。
- 新学内容不是只存在内存里, 也不是只存在 audit 里, 而是进入 runtime ontology state 和 SQLite projection 表。
- 重复教学可以增加 support, 不会制造重复后继边。
- 学习写入器没有引入新的策略捷径。

边界声明:

- 这还不是自由中文开放对话底座完成。
- 这还不是完整教学协议六阶段训练。
- 当前教学 episode 是结构化最小证据, 还不是自然对话 teacher protocol 自动抽取。
- 还没有验证逐字草稿、回读、修改、发送、commit 清空。
- 还没有接旧 GL 技能包真实复现。

## 6. 下一步

建议下一轮进入 Phase1.2:

1. 建立最小 DraftState / TextAction parity。
2. 验证逐字写入、回读、删除/修改、发送提交。
3. 保存到 SQLite 后恢复, 确认:
   - 未提交草稿不会作为正向长期技能写入。
   - 已提交结果可作为行动结果证据写入。
   - commit 后草稿清空。
   - 同一行动器同一 tick 只能选择一个行动。
4. Phase1.2 通过后, 再进入旧 GL 技能包小批复现。

