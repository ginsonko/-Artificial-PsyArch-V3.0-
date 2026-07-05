# APV3 Phase8.0b Minimal CLI 最终报告
日期: 2026-06-17
阶段: Phase8.0b
状态: 通过

## 1. 设计

Phase8.0b 的目标是提供第一个真实可玩的本地入口:

```text
python -m apv3test.chat
```

这个 CLI 不是新的问答脚本，也不是关键词 demo。它是 Phase7.9/7.11 已验证 dialogue flow 的薄壳:

- 普通用户输入进入 `MinimalistDialogueFlowRuntime`。
- 输入如果匹配 seed corpus 中已有短表达，才作为后天共现证据。
- 输入如果不在词库内，不新增 phrase，不倒灌 LLM 句式。
- 输出仍来自 `ExpressionPhraseMemory + CooccurrenceAssociationStore + style_safe_tokens`。
- 每轮结束后用 `SQLiteRuntimeStore` 保存状态。
- 重启后 warm-load 最新状态，继续沿用已学到的表达倾向。

## 2. 审查完善

本阶段特别区分两类通道:

- 学生侧认知 runtime: 不读答案表，不按输入字面分支，不调用 LLM，不动态造句。
- CLI 控制壳: `:top/:mode/:+/:-/:quit` 只用于体验和调试，不作为学生侧回答策略。

因此，`APV3MinimalistChatSession.say()` 的普通路径始终只做:

1. 取当前结构态 view。
2. 检查输入是否等于某个 seed phrase 的 token 序列。
3. 调用 `MinimalistDialogueFlowRuntime.run_turn()`。
4. style gate 检查输出。
5. SQLite 保存状态。

## 3. 通过落地

新增:

- `apv3test/chat.py`
- `tests/test_phase8_0b_minimal_cli_entry.py`
- `docs/FinalReport_Phase8_0b_MinimalCLI_20260617.md`
- `reports/APV3_Phase8_0_RuntimeProfile_MinimalCLI_Showcase_20260617.html`

CLI 支持:

- 连续输入中文。
- `:top` 查看当前 top phrase。
- `:mode uncertain|flow|request|corrective` 切换结构态。
- `:+` 对上一轮输出给轻微奖励。
- `:-` 对上一轮输出给轻微惩罚。
- `--state-db` 指定 SQLite 状态路径。
- `--once` 用于一次性启动和自动化验收。

## 4. 严谨验收测试

已执行:

```text
python -m pytest tests\test_phase8_0a_runtime_profile.py tests\test_phase8_0b_minimal_cli_entry.py -q
python -m pytest tests\test_phase7_8_minimalist_expression_corpus.py tests\test_phase7_9_minimalist_multiturn_dialogue_flow.py tests\test_phase7_10_longrun_stability.py tests\test_phase7_11_user_style_mirroring.py tests\test_phase8_0a_runtime_profile.py tests\test_phase8_0b_minimal_cli_entry.py -q
```

结果:

- Phase8.0 targeted: `7 passed`
- Phase7.8-8.0 combined: `32 passed`

覆盖点:

- CLI session 能写入 SQLite。
- 重启后 top phrase 与重启前一致。
- 未知词库外长句不会进入 phrase memory。
- `python -m apv3test.chat --once 嗯` 可以真实启动并写入 runtime DB。
- runtime/chat 红线扫描没有发现 answer table、student-side LLM、whole-reply fallback 或用户特例路由。

## 5. 最终汇总

Phase8.0b 证明了 APV3.0test 已经有了最小真实体验入口。现在它不再只是测试里的机制，而是可以通过本地 CLI 连续运行、保存、重启、继续学习用户表达倾向的最小中文对话底座。

默认正式状态路径:

```text
APV3.0test/state/apv3_minimalist_cli.sqlite
```

测试仍使用 `tmp_path` 或 `--state-db` override，不污染正式 runtime DB。
