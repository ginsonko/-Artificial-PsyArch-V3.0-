# APV3.0test Phase1.2 逐字草稿/提交 parity 报告

日期: 2026-06-16

## 1. 设计

本轮目标是验证最小草稿行动链:

> 逐字写入、回读、删除/修改、提交发送在持久化前后保持一致; 未提交草稿不能作为正向长期技能写入; commit 后草稿必须清空; 同一行动器同一 tick 只能执行一个行动。

本轮仍不接旧自由对话主链, 不跑 Fresh300, 不把提交文本变成整句语言技能。它只验证文本行动器的机械面和学习边界。

核心设计:

- `DraftActionRunner` 只执行机械草稿行动, 不决定应该说什么。
- `DraftTextAction` 支持:
  - `type_text`
  - `reread`
  - `delete_chars`
  - `replace_tail`
  - `commit`
- 草稿状态进入 `draft_runtime`, 可随 runtime state 一起保存恢复。
- 未 commit 时, 不生成 `LearningEpisode`。
- commit 后, 只生成 `text_commit` 的 `ActionOutcomeMemory` 证据, 不生成 token、transition、ParadigmSA、Bn candidate。

## 2. 审查完善

审查结论:

- Phase1.1 的 `LearningEpisodeWriter` 已能写入行动后果记忆。
- Phase0.3 的 `SQLiteRuntimeStore` 能保存任意 runtime state envelope, 因此可保存 `draft_runtime`。
- projection 表会投影根层 `action_outcomes`; 因此 commit 后行动后果可以进入 SQLite projection。
- 未提交草稿不能出现在 projection 的正向学习对象中。

风险边界:

- 草稿持久化不是技能固化。
- commit 奖励的是“提交行动后果”, 不是把整句输出写成语言记忆。
- 同 tick 单行动必须由行动器入口检查, 不能靠测试约定。

## 3. 通过落地

新增/更新文件:

- `APV3.0test/apv3test/runtime/draft_action.py`
- `APV3.0test/apv3test/runtime/__init__.py`
- `APV3.0test/tests/test_phase1_2_draft_action_parity.py`

新增 API:

- `DraftTextAction`
- `DraftActionRunner`

关键行为:

- `type_text`: 在 cursor 处写入文本。
- `reread`: 记录当前草稿读回。
- `delete_chars`: 删除 cursor 前若干字符。
- `replace_tail`: 替换草稿尾部片段。
- `commit`: 把当前 buffer 写入 commits, 然后清空 buffer/cursor。
- `learning_episode_from_latest_commit`: 只有 commit 后才返回行动后果 episode。

## 4. 严谨验收测试

已运行:

```powershell
python -m pytest APV3.0test/tests -q
```

结果:

```text
31 passed in 1.54s
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

- 逐字写入、回读、尾部修改、commit 后清空。
- 同一行动器同一 tick 第二个行动会被拒绝。
- 未提交草稿不会生成正向学习 episode。
- commit 前无学习, commit 后才生成 `text_commit` 行动后果 episode。
- commit 后只写行动后果, 不写 learned token / transition。
- 草稿 runtime state 保存到 SQLite 后恢复一致。
- commit 后行动后果进入 SQLite projection。
- 未提交草稿保存恢复后仍不产生 action outcome / token / transition projection。

## 5. 最终汇总

Phase1.2 已通过。

这说明:

- APV3.0test 已具备最小逐字草稿行动链。
- 草稿状态可以持久化恢复。
- 未提交草稿不会被误固化成正向长期技能。
- commit 后草稿清空。
- 同一行动器同一 tick 只能执行一个行动。
- 提交行动的奖励进入 ActionOutcomeMemory, 但不会把整句文本写成语言技能捷径。

边界声明:

- 这还不是完整 TextActionActuator。
- 这还不是自然自由对话 runtime。
- 这还没有做多行动器竞争。
- 这还没有接真实旧 GL 技能包。
- 这还没有跑 Fresh300。

## 6. 下一步

建议下一轮进入 Phase1.3:

1. 把 Phase1.0/1.1/1.2 串成一个小型 teacher protocol episode:
   - 输入 cue
   - 写入学习证据
   - 逐字草稿
   - 回读
   - commit
   - 保存恢复
   - 再召回
2. 验证 episode 结束后:
   - Bn/Cn 可召回
   - 草稿已清空
   - commit 行动后果已写入
   - 未提交中间草稿没有变成长期技能
3. 通过后进入旧 GL 技能包小批复现: 先选 3-5 个最小成功技能, 不直接全量导入。

