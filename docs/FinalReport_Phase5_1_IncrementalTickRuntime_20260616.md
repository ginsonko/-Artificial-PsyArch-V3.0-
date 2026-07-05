# APV3.0test Phase5.1 增量式 tick runtime 接入报告

日期: 2026-06-16

## 1. 设计

Phase5.1 的目标是把 Phase5.0 的 `IncrementalParadigmLearner` 接入最小 tick runtime, 让范式学习不再只是独立模块测试, 而是在 tick 链路里发生:

```text
外界/教师 observation -> 暂存
commit 或 feedback -> 增量范式学习
dirty bucket -> 局部维护
ParadigmSA -> 最小对话 runtime 逐 token 写草稿
commit -> action outcome
SQLite -> 保存恢复等价
```

本阶段不新增策略层, 不让 runtime 自己猜答案, 不接学生侧 LLM。它只把已经存在的 AP-native 组件串起来:

- `IncrementalParadigmLearner`
- `RoleTransitionStats`
- `MinimalDialogueRuntime`
- `DraftActionRunner`
- `SQLiteRuntimeStore`

## 2. 审查完善

### 2.1 support 不能输入即增长

未提交、未反馈的 observation 只进入:

```text
pending_paradigm_observations
```

不会进入:

- `paradigm_observations`
- `paradigm_stats`
- `paradigms`
- `state_field_items`

只有满足以下任一条件才交给 `IncrementalParadigmLearner`:

- `commit_observation=True`
- `reward_delta > 0`
- `punish_delta > 0`

这保证“看到/想到/草稿”不会自动固化为长期技能。

### 2.2 idle tick 只做维护, 不改写策略

idle tick 当前只处理一个 dirty bucket:

```text
dirty_paradigm_buckets -> idle_paradigm_maintenance
```

它不新增答案、不提高 support、不强行触发回复。后续可以在这里接后台压缩和低优先级重算, 但不能进入策略捷径。

### 2.3 实时 transition bias

Phase5.1 tick runtime 让后续 tick 的增量范式解码能读取:

```text
RoleTransitionStats.bias_map()
```

该 bias 仍遵守 Phase5.0 边界:

- 只走 promoted learned vector 的 context 相似泛化。
- 未 promoted token 不参与相似 context 泛化。
- 惩罚通过同类半衰期机制压低 bias。

### 2.4 教学等价

自然教学和 LLM 标准教学在 tick runtime 中的区别只保存在 observation provenance:

- `source_kind="natural"`
- `source_kind="llm_standard_teacher"`

进入 runtime 竞争的结果必须等价:

- 同一 `ParadigmSA`
- 同一草稿 token 序列
- 同一 commit 文本
- 不出现 `llm_policy`

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/incremental_tick_runtime.py`
- `APV3.0test/tests/test_phase5_1_incremental_tick_runtime.py`

修改文件:

- `APV3.0test/apv3test/runtime/__init__.py`

新增核心对象:

- `IncrementalTickInput`
- `IncrementalTickResult`
- `IncrementalTickRuntime`

最小运行链路:

```text
IncrementalTickRuntime.run_tick()
  -> 未 commit/feedback: stage pending observation
  -> commit/feedback: IncrementalParadigmLearner.ingest()
  -> discovered + exposed: MinimalDialogueRuntime.run_turn()
  -> commit_after_draft: DraftActionRunner + LearningEpisodeWriter
```

## 4. 严谨验收测试

Phase5.1 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase5_1_incremental_tick_runtime.py APV3.0test\tests\test_phase5_0_incremental_paradigm.py APV3.0test\tests\test_phase4_0_minimal_dialogue_runtime.py -q
```

结果:

```text
17 passed in 0.56s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
96 passed in 2.10s
```

禁用通道扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro|llm_policy|if vision|if text|黄色苹果" APV3.0test\apv3test
```

结果:

```text
APV3.0test\apv3test\runtime\draft_action.py:126:        if text:
```

审查: 这是草稿 commit 时的 buffer 非空检查, 不是文本模态特权分支。

残留硬地板/旧位置语法扫描:

```powershell
rg -n "max\([^\n]*0\.1|all_slot_confidence_floor|def _emission\(.*prev_role|def _emission\(.*index|last_index|variable_seen" APV3.0test\apv3test APV3.0test\tests
```

结果: 无命中。

测试覆盖:

- 未提交 tick 只暂存 observation, 不提高 support。
- commit tick 增量学习, support 足够后生成 `ParadigmSA`。
- 已发现范式可以进入最小对话 runtime, 逐 token 写草稿并提交。
- feedback 后可把暂存 observation 解析为长期学习证据。
- idle tick 整理 dirty bucket, 不改变 `ParadigmSA`。
- 后续 tick 解码读取 `RoleTransitionStats.bias_map()`。
- 自然教学和 LLM 标准教学 runtime 行为等价。
- SQLite 保存恢复后 Phase5.1 状态等价。

## 5. 最终汇总

Phase5.1 已完成:

- `IncrementalParadigmLearner` 已接入最小 tick runtime。
- support 不再是“输入即增长”, 而是 commit/feedback 后才进入长期学习证据。
- dirty bucket 有了 idle tick 维护入口。
- 实时范式解码开始读取 learned transition bias。
- 自然教学与 LLM 标准教学在 tick runtime 中有了行为等价 probe。
- 已发现范式可以复用 Phase4 的低粒度草稿/提交链路。

仍不能宣称:

- 完整 APV3.0 中文开放自由对话底座完成。
- 完整开放对话的 Bn 召回、注意力选择和多技能竞争已经完成。
- LLM 标准教学协议六阶段全流程已经全部接入。
- 所有旧 GL 技能已经在 APV3.0test 中复现。

下一步建议:

进入 Phase5.2: 把 tick runtime 与 Bn/Cn recall 和注意力焦点接起来。

最小目标:

1. 当前输入先通过 Bn recall 找到候选 ParadigmSA。
2. Cn 沿显式 successor edge / paradigm stats 读后继。
3. attention focus 选择当前最相关范式, 但不硬编码技能类别。
4. 同一 actuator 仍保持 tick 内互斥, 不同 actuator 可并行。
5. 用问候、成语、颜色对象、简单数学过程做自然教学 vs LLM 教学等价复现。
