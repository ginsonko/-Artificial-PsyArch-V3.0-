# APV3.0test Phase1.3 小型 teacher protocol episode 报告

日期: 2026-06-16

## 1. 设计

本轮目标是把 Phase1.0/1.1/1.2 串成一条最小闭环:

> 学习证据写入 -> 逐字草稿 -> 回读 -> 修改 -> commit -> 保存到 SQLite -> 恢复 -> 再召回。

本轮仍不接完整自由对话主链, 不跑 Fresh300, 不把编排器做成策略层。它只验证已有 AP-native 组件是否能按 teacher protocol episode 顺序协同。

核心设计:

- `TeacherProtocolRunner` 只做顺序编排, 不决定教什么, 不选择回复, 不绕过草稿行动边界。
- 学习证据仍由 `LearningEpisodeWriter` 写入。
- 草稿行动仍由 `DraftActionRunner` 执行。
- commit 后才生成 `text_commit` 行动后果 episode。
- 再召回仍由 `run_parity_probe` 验证。

最小 episode:

- cue: `春天`
- learned successor: `春天来了。`
- paradigm: `p:spring_reply`
- Bn candidate: `memory:spring_reply_pair`
- draft actions: `type_text` -> `type_text` -> `reread` -> `replace_tail` -> `commit`
- commit outcome: `text_commit`

## 2. 审查完善

审查结论:

- Phase1.1 已证明结构化教学证据可写入、保存、恢复、再召回。
- Phase1.2 已证明草稿行动可持久化, 且未提交草稿不会固化为正向长期技能。
- Phase1.3 只需新增编排层, 不需要新增持久化表或策略函数。

风险边界:

- 编排层不能变成回复策略。
- 无 commit 时不能写入 `text_commit` 行动后果。
- 中间回读草稿不能被投影成 learned token。
- 保存恢复后 probe 结果必须与内存态一致。

## 3. 通过落地

新增/更新文件:

- `APV3.0test/apv3test/runtime/teacher_protocol.py`
- `APV3.0test/apv3test/runtime/__init__.py`
- `APV3.0test/tests/test_phase1_3_teacher_protocol_episode.py`

新增 API:

- `TeacherProtocolEpisode`
- `TeacherProtocolResult`
- `TeacherProtocolRunner`

新增测试:

- `test_teacher_protocol_runs_learning_draft_commit_and_recall`
- `test_teacher_protocol_survives_sqlite_restore_and_recall`
- `test_teacher_protocol_projection_contains_only_committed_learning_boundary`
- `test_teacher_protocol_without_commit_does_not_write_commit_outcome`

## 4. 严谨验收测试

已运行:

```powershell
python -m pytest APV3.0test/tests -q
```

结果:

```text
35 passed in 1.59s
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

验收覆盖:

- 学习证据写入后, `spring_reply` probe 能召回 Bn/Cn/ParadigmSA/learned tokens。
- 草稿读回记录为中间文本 `春天来了`。
- 修改后 commit 文本为 `春天来了。`。
- commit 后草稿清空。
- SQLite 恢复后 probe 结果与内存态一致。
- projection 中保留 committed learning boundary:
  - `春天来了。` 是教学证据 token。
  - 中间草稿 `春天来了` 没有被投影为 token。
  - `春天 -> 春天来了。` 后继边存在。
  - `text_commit.reward_support = 1.0`。
- 无 commit 的 episode 不写入 `text_commit` 行动后果。

## 5. 最终汇总

Phase1.3 已通过。

这说明 APV3.0test 已完成一条最小持久化学习闭环:

- 可写入后天教学证据。
- 可逐字草稿、回读、修改、提交。
- 可将 commit 行动后果写入长期运行本体。
- 可保存到 SQLite 并恢复。
- 可恢复后再次召回同一学习结果。
- 未提交中间草稿不会被误固化。

边界声明:

- 这还不是完整自然语言教师协议自动解析。
- 这还不是完整自由中文开放对话底座。
- 这还没有接旧 APV2.1 主链。
- 这还没有做旧 GL 成功技能包真实复现。
- 这还没有跑 Fresh300。

## 6. 下一步

建议下一轮进入 Phase2.0: 旧 GL 成功技能小批复现。

先只挑 3-5 个最小、已验证、边界清楚的技能:

1. 问候: `你好 -> 我在。`
2. 成语后继: `三顾 -> 茅庐`
3. 简单数学过程: 一个加法或乘法 step template, 不导入答案表。
4. 黄色苹果泛化: 颜色+对象范式。
5. 打断恢复压力: 未完成任务被打断后恢复。

验收要求:

- 每个技能转换为 AP-native `LearningEpisode` / `TeacherProtocolEpisode`。
- 保存到 SQLite 后恢复。
- 再召回时 Bn/Cn/ParadigmSA/ActionOutcome/草稿提交边界都保持一致。
- 不允许整句捷径、答案表、学生侧 LLM、旧硬编码策略进入 APV3.0test 核心。

