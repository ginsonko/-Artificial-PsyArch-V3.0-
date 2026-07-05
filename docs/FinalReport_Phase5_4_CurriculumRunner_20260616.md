# APV3.0test Phase5.4 标准教学课程 runner 报告

日期: 2026-06-16

## 1. 设计

Phase5.4 的目标是把 Phase5.3 的手写教学样例整理为 APV3 标准教学 episode / curriculum runner。

课程 runner 不替 AP 决策, 只结构化记录:

- 教学阶段
- 教学 observation
- recall-only 验收项
- 成功样例
- 失败样例
- 失败归因

支持六段阶段:

1. `echo_imitation`
2. `successor_prediction`
3. `multi_reply_aggregation`
4. `process_paradigm_binding`
5. `focus_slot_filling`
6. `recall_only_validation`

课程仍然走当前 APV3.0 链路:

```text
CurriculumTeachingStep
  -> IncrementalTickRuntime
  -> IncrementalParadigmLearner
  -> ParadigmSA
  -> Bn/Cn recall
  -> attention focus
  -> low-granularity draft action
```

## 2. 审查完善

### 2.1 runner 不能成为答案脚本

本轮审查边界:

- runner 不根据 `case_id` 决定答案。
- runner 不做关键词分支。
- runner 不写 `llm_policy`。
- runner 不绕过 `IncrementalTickRuntime`。
- 验收仍然只给 cue / context / focus, 不给 teacher reply。

### 2.2 初跑失败与修正

初跑 Phase5.4 时出现 4 个失败, 原因相同:

```text
same actuator already acted in this tick
```

归因:

- curriculum validation 连续执行时, runner 每个验证只把 tick + 1。
- 但逐 token 草稿行动会占用多个 tick, commit 也占一个 tick。
- 后续验证与前一个验证的草稿行动 tick 重叠, 正确触发了同 actuator 同 tick 互斥保护。

修正:

- runner 在每个 validation 后读取 `dialogue_result.action_traces` 和 commit tick。
- 下一个 validation 从已占用最大 tick + 1 开始。

这不是技能失败, 而是课程编排需要尊重低粒度行动耗时。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/curriculum.py`
- `APV3.0test/tests/test_phase5_4_curriculum_runner.py`

修改文件:

- `APV3.0test/apv3test/runtime/__init__.py`

新增核心对象:

- `APV3CurriculumRunner`
- `CurriculumEpisode`
- `CurriculumTeachingStep`
- `CurriculumValidationCase`
- `CurriculumValidationResult`
- `CurriculumDiagnosis`
- `CurriculumRunResult`
- `CURRICULUM_STAGES`

## 4. 严谨验收测试

Phase5.4 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase5_4_curriculum_runner.py APV3.0test\tests\test_phase5_3_small_skill_reproduction.py -q
```

结果:

```text
10 passed in 0.81s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
112 passed in 3.04s
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

## 5. 成功样例

### 5.1 问候

教学:

```text
stage = successor_prediction
cue = 你 好
reply = 我 在
```

验收:

```text
只给 cue = 你 好
emitted = 我 在
diagnosis = success
```

### 5.2 成语

教学:

```text
stage = successor_prediction
cue = 三 顾
reply = 茅 庐
```

验收:

```text
只给 cue = 三 顾
emitted = 茅 庐
diagnosis = success
```

### 5.3 颜色对象槽位

教学:

```text
stage = multi_reply_aggregation / focus_slot_filling
reply examples =
  field::color percept::red field::object percept::apple
  field::color percept::blue field::object percept::cup
  field::color percept::green field::object percept::leaf
  field::color percept::yellow field::object percept::banana
```

验收:

```text
cue = describe
focus = percept::yellow percept::apple
emitted = field::color percept::yellow field::object percept::apple
diagnosis = success
```

### 5.4 简单数学过程

教学:

```text
stage = process_paradigm_binding
reply examples =
  math::lhs 1 math::op + 2 math::eq 3
  math::lhs 2 math::op + 3 math::eq 5
  math::lhs 4 math::op + 1 math::eq 5
```

验收:

```text
cue = calc
focus = 7 2 9
emitted = math::lhs 7 math::op + 2 math::eq 9
diagnosis = success
```

边界: 这证明过程范式和槽位填充, 不证明任意计算能力。

## 6. 失败样例

### 6.1 未训练 cue

验收:

```text
cue = unknown
expected = 我 在
```

结果:

```text
emitted = <empty>
diagnosis = bn_not_recalled
detail = no ParadigmSA entered attention focus
```

含义:

- Bn recall 没有找到足够相关的 `ParadigmSA`。
- 系统没有胡乱输出或提交。

### 6.2 槽位焦点期望不一致

验收:

```text
cue = describe
focus = percept::yellow percept::apple
expected = field::color percept::yellow field::object percept::pear
```

结果:

```text
emitted = field::color percept::yellow field::object percept::apple
diagnosis = slot_focus_overridden
detail = emitted tokens differ from current focus-slot expectation
```

含义:

- 当前 focus 只有 apple, 没有 pear。
- 系统按当前工作记忆积木输出 apple, 而不是凭空生成 pear。

## 7. 最终汇总

Phase5.4 已完成:

- APV3 标准课程 runner 已落地。
- 六段教学阶段已能被结构化记录。
- 成功样例和失败样例能由同一 runner 输出。
- 失败归因至少覆盖:
  - `bn_not_recalled`
  - `attention_wrong`
  - `cn_successor_weak`
  - `slot_focus_overridden`
  - `commit_action_outcome_missing`
  - `success`
- 自然教学与 LLM 标准教学仍保持行为等价。
- SQLite restore 后可继续运行 validation-only 课程。

仍不能宣称:

- 完整 APV3.0 中文开放自由对话底座完成。
- Fresh300 通过。
- 所有旧 GL 技能完成迁移。
- 课程 runner 已覆盖全部教学协议细节。

下一步建议:

进入 Phase5.5: 把 curriculum runner 扩展成可持续训练/补习循环。

最小目标:

1. 课程失败后自动生成补习建议, 但不自动加关键词规则。
2. 针对失败类型选择 AP-native 补习:
   - `bn_not_recalled`: 增加 cue/context 支持样例或 promoted vector 支持。
   - `cn_successor_weak`: 增加 successor observation 或 transition 支持。
   - `attention_wrong`: 增加区分性上下文和奖惩。
   - `slot_focus_overridden`: 增加 focus-slot 对比样例和惩罚旧错误。
   - `commit_action_outcome_missing`: 补 commit/action outcome 训练。
3. 形成一轮 train -> validate -> diagnose -> remediate -> validate 的闭环。
