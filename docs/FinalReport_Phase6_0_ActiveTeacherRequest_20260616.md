# APV3.0test Phase6.0 主动学习 / 主动召唤教师最小门报告

日期: 2026-06-16

## 1. 设计

Phase6.0 的目标是让系统在自身出现明显学习需求时，生成 `teacher_request` SA。

触发来源:

- cognitive pressure 持续较高。
- recall 反复失败。
- remediation need 明显。

设计边界:

- `teacher_request` 只是状态池中的请求 SA。
- 它不直接调用 LLM。
- 它不直接生成答案。
- 教师响应仍必须通过 curriculum / remediation 写入 AP-native evidence。
- 当对应技能已经掌握，请求频率应下降。

## 2. 审查完善

### 2.1 主动求教不是外部控制器

本阶段新增 `APV3ActiveTeacherRequestRuntime`，它只观察失败/压力并写入:

```text
teacher_requests
state_field_items(sa_type = teacher_request)
active_learning_failures
```

它不接管 runtime 输出。

### 2.2 请求应有抑制机制

为避免 spam:

- 单次低压失败不请求。
- 同一 cue/context 在 cooldown 内不重复请求。
- 已掌握的 expected paradigm 不再请求。

### 2.3 教师响应仍走 AP-native evidence

测试中使用 `llm_standard_teacher` 作为教师来源，但它只进入现有补习链:

```text
CurriculumRemediationLoop
  -> CurriculumTeachingStep
  -> IncrementalTickRuntime
  -> IncrementalParadigmLearner
  -> ParadigmSA
```

状态中不出现 `llm_policy`。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/config/active_learning_config.py`
- `APV3.0test/apv3test/runtime/active_teacher_request.py`
- `APV3.0test/tests/test_phase6_0_active_teacher_request.py`

修改文件:

- `APV3.0test/apv3test/config/__init__.py`
- `APV3.0test/apv3test/runtime/__init__.py`

新增对象:

- `APV3ActiveLearningConfig`
- `APV3ActiveTeacherRequestRuntime`
- `TeacherRequestSignal`
- `TeacherRequestSA`
- `TeacherRequestResult`

文件行数:

```text
active_teacher_request.py: 218
test_phase6_0_active_teacher_request.py: 109
active_learning_config.py: 14
```

## 4. 严谨验收测试

Phase6.0 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_0_active_teacher_request.py -q
```

结果:

```text
5 passed in 0.32s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
138 passed in 2.96s
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

额外扫描:

```powershell
rg -n "most_common_reply|_observations_for_bucket|remediate:|if percept|if audio|if action|if text|if vision|if task|task_queue|answer_table|llm_policy" APV3.0test\apv3test APV3.0test\tests
```

命中均为:

- 测试名。
- 测试断言，确认 state 中没有 `llm_policy` / `answer_table`。
- `draft_action.py` 草稿 buffer 非空检查。

审查: 均非 runtime 作弊分支。

## 5. 成功样例

### 5.1 重复召回失败生成 teacher_request

输入:

```text
cue = goal::ask
context = ctx_work
recall_failed = true
pressure = 0.2
```

第一次:

```text
request = <none>
reason = below_request_threshold
```

第二次:

```text
request.reason = repeated_recall_failure
failure_count = 2
state_field_items.sa_type = teacher_request
energy.P > 0
```

### 5.2 高认知压可立即求教

输入:

```text
cognitive_pressure = 0.9
```

结果:

```text
request.reason = high_cognitive_pressure
```

### 5.3 教师响应后请求下降

过程:

```text
teacher_request generated
llm_standard_teacher responds through CurriculumRemediationLoop
skill_teacher_answer learned as AP-native evidence
```

再次观察:

```text
expected_pid = p:discovered:skill_teacher_answer
request = <none>
suppressed_reason = mastered_expected_pid
```

含义:

- 教师可以是 LLM。
- LLM 只作为教师来源。
- 学生侧没有 `llm_policy`。
- 学会后不再反复求教。

### 5.4 cooldown 防止刷屏

同一 cue/context 在 cooldown 内再次高压:

```text
request = <none>
suppressed_reason = request_cooldown
failure_count 仍记录为 2
```

含义:

- 不重复打扰教师。
- 失败统计仍保留。

## 6. 最终汇总报告

Phase6.0 已完成主动学习最小门:

- 系统可以基于压力、失败次数、补习需求生成 `teacher_request` SA。
- `teacher_request` 是状态池一等项。
- 低压单次失败不会请求。
- cooldown 防止重复刷屏。
- 教师响应仍通过 AP-native 证据链。
- 掌握后请求会下降。

仍不能宣称:

- 系统已能自动设计完整课程。
- 系统已能主动选择最佳教师。
- 完整自由中文开放对话底座已经完成。
- 主动学习已经覆盖跨模态、长程多轮、复杂任务。

下一步建议 Phase6.1:

```text
teacher_request 与 work_memory / Bn/Cn 失败信号自动连接
```

重点:

- 工作记忆 bridge 失败时自动生成 teacher_request。
- Bn/Cn recall 失败时自动生成 teacher_request。
- 教师响应后，原工作记忆任务可继续恢复并验证请求减少。
