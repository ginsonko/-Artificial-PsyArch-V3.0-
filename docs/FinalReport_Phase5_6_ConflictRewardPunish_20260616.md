# APV3.0test Phase5.6 多技能冲突与奖惩细化报告

日期: 2026-06-16

## 1. 设计

Phase5.6 的目标是验证两个对自由中文开放对话底座很关键的能力:

- 相同 cue 在不同 context 下，应能召回不同技能。
- 错误范式受到惩罚后，应退出 attention 竞争，让正确范式获得行动机会。

本阶段先不新增 runtime 规则。如果现有 AP-native 证据链已经能通过，就不加参数、不加关键词分支、不加特殊抑制。

## 2. 审查完善

审查问题:

1. 同一个 `answer` cue 是否会被写成答案表？
2. context 区分是否来自 promoted context vector，而不是字符串分支？
3. 惩罚是否通过已有 `punish_support / punish_pressure / exposed` 链路影响召回？
4. LLM 标准教师是否仍然只作为教师来源，不写 `llm_policy`？

设计判断:

- 技能区分应由 Bn 的 cue/context/support/conf/energy 评分完成。
- 错误技能惩罚后不应被硬删，而是先从 exposed/attention 竞争中退出。
- 自然教师和 LLM 标准教师训练同一技能时，学生侧行为应等价。

## 3. 通过落地

新增测试:

- `APV3.0test/tests/test_phase5_6_conflict_reward_punish.py`

没有修改 runtime 逻辑。

原因:

- 现有 `ParadigmRecallAttention` 已经使用 promoted context similarity。
- 现有 `update_paradigm_stats()` 已经用 reward/punish pressure 控制 `exposed`。
- 现有 recall 已经跳过 `exposed=False` 的 `ParadigmSA`。

## 4. 严谨验收测试

Phase5.6 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase5_6_conflict_reward_punish.py -q
```

结果:

```text
3 passed in 0.31s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
120 passed in 3.37s
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

旧硬地板 / 旧角色位置先验 / 旧课程硬枚举扫描:

```powershell
rg -n "max\([^\n]*0\.1|all_slot_confidence_floor|def _emission\(.*prev_role|def _emission\(.*index|last_index|variable_seen|CURRICULUM_STAGES|_validate_stage" APV3.0test\apv3test APV3.0test\tests
```

结果: 无命中。

## 5. 成功样例

### 5.1 相同 cue / 不同 context

教学:

```text
skill_a:
cue = answer
context = ctx_a
reply = reply_a

skill_b:
cue = answer
context = ctx_b
reply = reply_b
```

验证:

```text
cue = answer
context = ctx_a
focus_pid = p:discovered:skill_a
emitted = reply_a

cue = answer
context = ctx_b
focus_pid = p:discovered:skill_b
emitted = reply_b
```

含义:

- 区分来自 context evidence 和 attention 竞争。
- 不是根据 cue 字符串写死分支。

### 5.2 错误范式受惩罚退出竞争

教学:

```text
skill_wrong:
cue = answer
context = ctx_a
reply = wrong_reply
后续 punish_delta = 12.0

skill_right:
cue = answer
context = ctx_a
reply = right_reply
reward_delta = 1.0
```

验证:

```text
skill_wrong.exposed = false
Bn candidates 不包含 skill_wrong
focus_pid = p:discovered:skill_right
emitted = right_reply
```

含义:

- 惩罚不是关键字禁用，而是通过 AP 现有奖惩压力影响范式暴露和注意力竞争。

### 5.3 自然教师与 LLM 标准教师等价

验证:

```text
natural emitted = reply_a
llm_standard_teacher emitted = reply_a
state 中没有 llm_policy
```

含义:

- LLM 仍然只是教师来源。
- 学生侧 runtime 不依赖 LLM 策略字段。

## 6. 最终汇总报告

Phase5.6 通过，并且没有新增 runtime 硬编码。

已经确认:

- 同 cue / 不同 context 的小型技能冲突可以被区分。
- 错误范式受惩罚后会退出 attention 竞争。
- 正确范式可以在奖励证据下进入 focus 并输出。
- 自然教师和 LLM 标准教师在学生侧行为等价。

仍不能宣称:

- 所有复杂上下文冲突都已解决。
- 奖惩补习已经覆盖长程、多轮、跨模态场景。
- 完整自由中文开放对话底座已经完成。

下一步建议 Phase5.7:

```text
工作记忆 / 跨 tick 任务恢复最小复刻
```

重点:

- 多 tick 输入作为整体进入短期/工作记忆。
- 打断后未闭合任务保留压力。
- 空闲 tick 后能回到未完成任务。
- 仍然不靠关键词脚本或旧 GL harness。
