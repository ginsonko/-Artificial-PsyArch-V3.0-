# APV3.0test Phase7.2 后天学习的不能决表达范式报告

日期: 2026-06-16

## 1. 设计

用户提出一个重要补充:

```text
不能决, 但是又必须有回复时,
可以用一类范式进行简洁疑惑表达:
  不确定 + 高可能对象1 + 高可能对象2 ...
```

Phase7.2 将这个想法形式化为更通用的 AP-native 机制:

```text
undecidable feeling SA
  + high-grasp fragment candidates
  + must_reply pressure
  + learned uncertainty expression paradigm
  -> concise uncertainty reply
```

关键原则:

- 不内置中文“不确定”。
- 不内置固定句式。
- 不用 case_name 路由。
- 不用答案表。
- 只有当系统后天学过“不能决表达范式”时，才会在必须回复场景使用它。
- 没学过时，即使 `must_reply=True`，也不能凭空生成表达，只保留 Phase7.1 的未提交片段。

## 2. 审查完善

### 2.1 拟人哲学解释

在人类学习中，一个孩子并不是先天会说“我不确定，可能是 X”。更合理的路径是:

```text
内部状态:
  不能决 / 犹豫 / 只想起部分片段

外部观察:
  旁边的人在类似状态下说出某类表达

共现学习:
  feeling::undecidable 与表达句式在相邻 tick 中绑定

下次遇到类似状态:
  召回表达范式
  用当前高把握对象填槽
```

因此 Phase7.2 使用一个可学习 cue:

```text
cue = feeling::undecidable
```

以及后天观察得到的表达范式:

```text
feeling::undecidable -> expr::uncertain candidate::a
feeling::undecidable -> expr::uncertain candidate::b
```

该范式会自发现为:

```text
fixed_anchor = expr::uncertain
slot = current high-grasp fragment
```

在真实中文教学中，`expr::uncertain` 可以由教师/环境教成中文 token，如“不 确 定”或“可 能 是”。本测试用抽象 token，是为了证明机制通用，不依赖中文关键词。

### 2.2 Runtime 触发条件

新增到 `IncrementalTickInput`:

```text
must_reply: bool = False
undecidable_feeling_tokens: tuple[str, ...] = ("feeling::undecidable",)
```

触发逻辑:

1. 正常 recall 先运行。
2. 如果生成结果含 `undecidable_fragment`，说明只能决出片段，不能确定完整回复。
3. 如果 `must_reply=False`，保持 Phase7.1 行为: 片段进入草稿但不提交。
4. 如果 `must_reply=True`，尝试用 `undecidable_feeling_tokens` 召回后天学到的表达范式。
5. 若表达范式存在，则把当前高把握片段作为槽候选填入表达范式。
6. 若表达范式不存在，则不凭空生成。

### 2.3 为什么这不是硬编码

runtime 固定的是内部状态通道:

```text
feeling::undecidable
must_reply
```

不是固定表达内容。具体说什么由后天学到的 `ParadigmSA` 决定。

本测试中的输出是:

```text
expr::uncertain 庐
```

这不是学生侧写死的回复，而是由两类后天 evidence 组合而来:

- 多义回复观察抽出 `庐`。
- 不能决表达观察学到 `expr::uncertain + slot`。

## 3. 通过落地

修改文件:

```text
APV3.0test/apv3test/runtime/incremental_tick_runtime.py
```

新增文件:

```text
APV3.0test/tests/test_phase7_2_learned_uncertainty_expression.py
```

依赖 Phase7.1 已完成的修改:

```text
APV3.0test/apv3test/runtime/paradigm_fill.py
APV3.0test/apv3test/runtime/dialogue_runtime.py
```

关键行为:

- `must_reply=True` 时才尝试不能决表达。
- 表达范式不存在时不生成。
- 表达范式存在时，通过 Bn/Cn recall + slot fill 生成简洁回复。

## 4. 严谨验收测试

Phase7.2 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase7_2_learned_uncertainty_expression.py -q
```

结果:

```text
2 passed in 0.70s
```

Phase7/Recall/Slot-fill 组合测试:

```powershell
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py APV3.0test\tests\test_phase7_1_undecidable_shared_fragment.py APV3.0test\tests\test_phase7_2_learned_uncertainty_expression.py APV3.0test\tests\test_phase5_2_recall_attention_runtime.py APV3.0test\tests\test_phase2_6_percept_slot_fill.py -q
```

结果:

```text
19 passed in 1.96s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
180 passed in 4.47s
```

编译检查:

```powershell
python -m py_compile APV3.0test\apv3test\runtime\paradigm_fill.py APV3.0test\apv3test\runtime\dialogue_runtime.py APV3.0test\apv3test\runtime\incremental_tick_runtime.py APV3.0test\tests\test_phase7_1_undecidable_shared_fragment.py APV3.0test\tests\test_phase7_2_learned_uncertainty_expression.py
```

结果:

```text
passed
```

红线扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro|llm_policy|if vision|if text|黄色苹果" APV3.0test\apv3test
```

结果:

```text
APV3.0test\apv3test\runtime\draft_action.py:126:        if text:
```

审查:

- 该命中是 draft buffer 非空检查，不是文本模态特权。

额外红线扫描:

```powershell
rg -n "most_common_reply|_observations_for_bucket|remediate:|if percept|if audio|if action|if text|if vision|if task|task_queue|answer_table|llm_policy|propose_multiround|MultiRoundTeacherCourseProposal|TeacherCourseRound|case_name.*phase7|三顾|茅庐|草庐|不确定" APV3.0test\apv3test APV3.0test\tests\test_phase7_1_undecidable_shared_fragment.py APV3.0test\tests\test_phase7_2_learned_uncertainty_expression.py
```

结果:

- `case_name` 只命中测试训练样例。
- runtime 无 case_name 分支。
- runtime 无中文“不确定”硬编码。
- 无答案表/学生侧 LLM/旧 fallback。

## 5. 成功/边界样例

### 5.1 学过表达范式时必须回复

训练多义:

```text
三 顾 -> 茅 庐
三 顾 -> 草 庐 之 中
```

训练不能决表达:

```text
feeling::undecidable -> expr::uncertain candidate::a
feeling::undecidable -> expr::uncertain candidate::b
```

teacher-off 验证:

```text
cue = 三 顾
must_reply = true
reply_tokens = ()
focus_tokens = ()
candidate_pool = ()
```

结果:

```text
original Cn successor = 庐
final emitted = expr::uncertain 庐
committed_text = expr::uncertain庐
uncertainty expression slot source = focus
```

含义:

- 系统先从多义范式中抽出高把握共享片段 `庐`。
- 因为必须回复，它召回后天学到的不能决表达范式。
- 当前高把握片段进入表达范式的槽。

### 5.2 没学过表达范式时不凭空生成

训练:

```text
只训练多义, 不训练 feeling::undecidable 表达范式
```

teacher-off 验证:

```text
cue = 三 顾
must_reply = true
```

结果:

```text
emitted = 庐
committed_text = ""
undecidable_fragment = true
```

含义:

- 即使必须回复，系统也不会凭空说“我不确定”。
- 这符合“后天学习句式”的原则。

## 6. 最终汇总报告

Phase7.2 已完成:

- 将用户提出的“不能决但必须回复时用疑惑范式简洁回应”形式化为 AP-native learned uncertainty expression。
- 具体表达内容由后天学到的范式决定，不写死中文。
- `must_reply=True` 只触发表达范式召回，不直接生成文本。
- 学过表达范式时，可输出 `expr::uncertain + 高把握片段`。
- 没学过表达范式时，不凭空生成。
- Phase7.1 的不提交保护仍成立。
- 全量测试与红线扫描通过。

可以宣称:

- APV3.0test 当前具备最小“不能决 + 必须回复 + 后天表达范式”链路。
- 这条链路符合“内部认知感受与外部表达句式共现后可学习”的拟人哲学。

仍不能宣称:

- 已经能自然生成中文“我不确定，可能是 X”。
- 已经能列出多个高可能候选并排序。
- 已经能主动发起澄清问题。
- 已经能在任意开放对话中处理所有不能决状态。

下一步建议 Phase7.3:

```text
多候选不能决表达:
  Cn / Bn / relation overlap 产生多个高把握候选
  -> uncertainty expression paradigm with repeated candidate slots
  -> 简洁表达多个候选
  -> 候选排序来自 grasp/support/coherence, 不来自答案表
```

目标是把当前单片段表达扩展为更拟人的 “不确定: A / B” 多候选表达，同时保持后天学习和 AP-native evidence 路线。
