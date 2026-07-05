# APV3.0test Phase6.6 教学迭代闭环报告

日期: 2026-06-16

## 1. 设计

Phase6.6 的目标是在吸收 Claude 对 Phase6.5 的纠偏后，继续推进主动教学闭环:

```text
RepeatedEvidenceCourseProposal
  -> APV3CurriculumRunner
  -> recall-only validation
  -> diagnosis
  -> TeachingPlanContext
  -> next RepeatedEvidenceCourseProposal
```

设计边界:

- 使用纠偏后的 `RepeatedEvidenceCourseProposal`，不恢复“真实差异化多轮课程”的旧叙事。
- loop 属于教师侧编排，不是学生侧推理器。
- 学生侧仍只接收 AP-native `CurriculumTeachingStep` 和 `CurriculumValidationCase`。
- 失败诊断只变成下一轮 `TeachingPlanContext`，不变成 runtime 答案路由。

## 2. 审查完善

### 2.1 为什么新增独立 loop 文件

`teaching_protocol_selector.py` 已到 366 行。继续往里塞迭代流程会让它变成新的大对象。

因此新增:

```text
APV3.0test/apv3test/runtime/teaching_iteration_loop.py
```

职责分离:

- `teaching_protocol_selector.py`: 生成 proposal。
- `curriculum.py`: 执行 AP-native teaching/validation。
- `teaching_iteration_loop.py`: 串接 proposal -> runner -> diagnosis -> next proposal。

### 2.2 失败如何进入下一轮

当 validation 失败:

```text
CurriculumValidationResult.diagnosis.failure_kind
CurriculumValidationResult.diagnosis.detail
CurriculumValidationResult.focus_pid
```

会被转换为:

```text
TeachingPlanContext(
  failure_kind,
  failure_detail,
  current_focus_pid,
  competing_pids
)
```

然后生成下一轮 `RepeatedEvidenceCourseProposal`。

### 2.3 state 接力约束

Phase6.5 纠偏后，proposal trace 已显式带:

```text
was_exposed_at_check_time
state_handoff_contract = caller_must_use_runner_returned_state_for_next_proposal
```

Phase6.6 测试验证:

```text
first proposal:  was_exposed_at_check_time = false
second proposal: was_exposed_at_check_time = true
```

这说明 loop 使用了 runner 返回的新 state，而不是旧 state。

## 3. 通过落地

新增文件:

```text
APV3.0test/apv3test/runtime/teaching_iteration_loop.py
APV3.0test/tests/test_phase6_6_teaching_iteration_loop.py
```

修改文件:

```text
APV3.0test/apv3test/runtime/__init__.py
```

新增对象:

```text
TeachingIterationInput
TeachingIterationResult
APV3TeachingIterationLoop
```

文件规模:

```text
teaching_iteration_loop.py: 104 lines
test_phase6_6_teaching_iteration_loop.py: 135 lines
teaching_protocol_selector.py: 366 lines
```

## 4. 严谨验收测试

Phase6.6 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_6_teaching_iteration_loop.py -q
```

结果:

```text
4 passed in 0.32s
```

Phase6.0-6.6 组合测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_0_active_teacher_request.py APV3.0test\tests\test_phase6_1_active_learning_bridge.py APV3.0test\tests\test_phase6_2_active_learning_trend.py APV3.0test\tests\test_phase6_3_teaching_protocol_selector.py APV3.0test\tests\test_phase6_4_diagnostic_teaching_plan.py APV3.0test\tests\test_phase6_5_multiround_teacher_course.py APV3.0test\tests\test_phase6_6_teaching_iteration_loop.py -q
```

结果:

```text
30 passed in 0.63s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
163 passed in 3.19s
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

- 该命中是草稿 buffer 非空检查，不是文本模态特权。

额外扫描:

```powershell
rg -n "most_common_reply|_observations_for_bucket|remediate:|if percept|if audio|if action|if text|if vision|if task|task_queue|answer_table|llm_policy|propose_multiround|MultiRoundTeacherCourseProposal|TeacherCourseRound" APV3.0test\apv3test APV3.0test\tests
```

结果:

- 命中均为测试名、防泄漏断言或 `draft_action.py` buffer 非空检查。
- 旧的 `propose_multiround` / `MultiRoundTeacherCourseProposal` / `TeacherCourseRound` 无 runtime 残留。

## 5. 成功/失败样例

### 5.1 无教师证据时等待

输入:

```text
reply_tokens = ()
failure_kind = bn_not_recalled
```

结果:

```text
proposal.status = awaiting_teacher_evidence
run_result = None
next_proposal = None
state unchanged
```

含义:

- 没有教师证据时不运行学生教学。

### 5.2 成功后停止

输入:

```text
reply_tokens = teacher::answer
case_name = skill_teacher_answer
expected_pid = p:discovered:skill_teacher_answer
```

结果:

```text
validation success = True
next_context.failure_kind = ""
next_proposal = None
```

含义:

- 已通过验证，不继续追加补习。

### 5.3 失败后生成下一轮 context/proposal

输入:

```text
case_name = skill_wrong
expected_pid = p:discovered:skill_teacher_answer
```

结果:

```text
validation success = False
next_context.failure_kind = attention_wrong
next_context.current_focus_pid = p:discovered:skill_wrong
next_proposal.previous_failure_kind = attention_wrong
next_proposal.failure_followup_repeats = 1
```

含义:

- 验证失败会进入下一轮教师侧 proposal。
- 补习仍是 AP-native evidence。

### 5.4 使用 runner 返回 state

第一次:

```text
was_exposed_at_check_time = False
initial_support_repeats = 2
```

第二次使用第一次 `run_result.state`:

```text
was_exposed_at_check_time = True
initial_support_repeats = 1
```

含义:

- state 接力约束成立。
- 学会后重复强度自然下降。

## 6. 最终汇总报告

Phase6.6 已完成:

- 多轮/重复证据 proposal 已接入实际 runner。
- validation 失败能生成下一轮 `TeachingPlanContext`。
- 下一轮 proposal 能携带 previous failure 并追加 AP-native 补习 evidence。
- 成功时不生成下一轮 proposal。
- state handoff 约束通过测试。

仍不能宣称:

- AP 能自己生成教师答案。
- AP 能自己选择教师。
- 已实现真实差异化多轮课程。
- 完整主动课程规划系统完成。
- 自由中文开放对话底座完成。

下一步建议 Phase6.7:

```text
把教学迭代 loop 接回 active_learning_bridge:
  teacher_request SA
  -> RepeatedEvidenceCourseProposal
  -> run/validate
  -> failure context
  -> next proposal
  -> success suppresses further request

仍然要求:
  学生侧只接收 AP-native evidence
  不引入答案表/关键词路由/学生侧 LLM
```
