# APV3.0test Phase5.5 补习闭环报告

日期: 2026-06-16

## 1. 设计

Phase5.5 的目标是把 Phase5.4 的失败归因推进成一个最小补习闭环:

```text
train -> validate -> diagnose -> remediate -> validate
```

核心原则:

- 补习不是运行时答案补丁。
- 失败后只生成 AP-native 教学证据。
- 自然教师和 LLM 标准教师可以来源不同，但都必须写入同构 `CurriculumTeachingStep`。
- 补习后的能力必须重新通过 `IncrementalTickRuntime -> IncrementalParadigmLearner -> ParadigmSA -> Bn/Cn recall -> attention -> draft action` 链路召回。
- 如果当前 focus 和教师期望冲突，不把冲突目标强行固化为长期记忆。

## 2. 审查完善

### 2.1 补习器不能变成答案表

本轮新增 `APV3CurriculumRemediationPlanner`，它只输出 `CurriculumTeachingStep`:

```text
case_id
failure_kind
teaching_steps
rationale
```

它不修改 runtime 输出，不注册关键词规则，不写 answer table。

### 2.2 缺失技能如何补

当验证失败为 `bn_not_recalled`、`cn_successor_weak` 或类似缺证据问题时，补习器生成同 cue / context / expected target 的教师补习 step。

默认补足到 `APV3ParadigmDiscoveryConfig.min_support`，也就是至少两次提交证据，避免单次自发声或单次偶然样本立即暴露为稳定范式。

### 2.3 当前 focus 冲突如何处理

如果验证声明 `allow_current_focus=True`，且当前 focus token 不在 expected target 中，补习器不生成教学 step。

例子:

```text
focus = percept::yellow percept::apple
expected = field::color percept::yellow field::object percept::pear
```

这时如果强行补习，就等价于教系统“看到 apple 时输出 pear”。本轮选择拒绝固化，留下 `current focus tokens conflict with expected target` 的 rationale。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/curriculum_remediation.py`
- `APV3.0test/tests/test_phase5_5_remediation_loop.py`

修改文件:

- `APV3.0test/apv3test/runtime/__init__.py`

新增对象:

- `APV3CurriculumRemediationPlanner`
- `APV3CurriculumRemediationLoop`
- `CurriculumRemediationSuggestion`
- `CurriculumRemediationLoopResult`

文件行数:

```text
curriculum_remediation.py: 157
test_phase5_5_remediation_loop.py: 116
```

## 4. 严谨验收测试

Phase5.5 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase5_5_remediation_loop.py -q
```

结果:

```text
4 passed in 0.29s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
117 passed in 3.15s
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

### 5.1 缺失问候技能的补习

初始验证:

```text
cue = 你 好
expected = 我 在
emitted = <empty>
diagnosis = bn_not_recalled
```

补习建议:

```text
stage = remediate:bn_not_recalled
case_name = skill_greeting
cue = 你 好
reply = 我 在
context = ctx_dialogue
teaching step count = min_support
```

补习后验证:

```text
cue = 你 好
emitted = 我 在
diagnosis = success
```

含义:

- 系统不是在 validation 里直接输出 expected。
- 它先写入补习 observation，再通过 ParadigmSA / Bn / Cn / attention 重新召回。

### 5.2 自然教师与 LLM 标准教师等价

同一个缺失问候 case:

```text
natural final emitted = 我 在
llm_standard_teacher final emitted = 我 在
natural final focus_pid = llm final focus_pid
remediation reply_tokens 相同
state 中没有 llm_policy
```

含义:

- LLM 可以作为教师加速学习。
- LLM 教出来的内容没有特殊学生侧字段。
- 运行时只看到 AP-native evidence。

## 6. 失败 / 拒绝固化样例

当前 focus 冲突:

```text
cue = describe
focus = percept::yellow percept::apple
expected = field::color percept::yellow field::object percept::pear
```

结果:

```text
initial success = false
remediation teaching_steps = <empty>
rationale = current focus tokens conflict with expected target; do not solidify contradictory memory
```

含义:

- 补习器不会为了让测试过，把当前输入 apple 训练成 pear。
- 这类问题应回到教师目标、感受器输入或数据标注层纠错，而不是固化坏记忆。

## 7. 最终汇总报告

Phase5.5 已完成最小补习闭环:

- 失败可被诊断。
- 可补习失败会生成 AP-native 教师证据。
- 补习后通过同一 AP 召回链路重新验证。
- 自然教学与 LLM 标准教学在学生侧行为等价。
- 当前输入冲突不会被盲目固化。

仍不能宣称:

- 复杂多技能冲突的自动课程规划已完成。
- 奖惩补习已经覆盖所有 failure_kind。
- 完整自由中文开放对话底座已经完成。
- Fresh300 或旧 GL 全技能迁移已经完成。

下一步建议 Phase5.6:

```text
多技能冲突补习与奖惩细化
```

重点验证:

- 相同 cue / 不同 context 下是否能区分回复。
- 错误范式被惩罚后是否降低竞争力。
- 正确范式经过奖励后是否更容易进入 attention focus。
- 补习仍然只通过 AP-native evidence，不新增关键词分支。
