# APV3.0test Phase6.7 主动学习教学迭代桥接报告

日期: 2026-06-16

## 1. 设计

Phase6.7 的目标是把 Phase6.6 的教学迭代 loop 接回 active learning bridge:

```text
teacher_request SA
  -> external teacher reply_tokens
  -> RepeatedEvidenceCourseProposal
  -> APV3CurriculumRunner
  -> validation
  -> success: stop
  -> failure: next TeachingPlanContext
  -> bounded next iteration
```

设计边界:

- bridge 不生成教师答案。
- bridge 不选择教师。
- bridge 只在外部教师已经提供 `reply_tokens` 后运行教学迭代。
- 教学迭代有最大深度，避免“教不会就无限教”。
- 学生侧仍只接收 AP-native evidence。

拟人原则:

```text
孩子学不会时，老师会试几次；
若持续失败，就暂时停止，等待能力/环境/上下文变化后再教；
不是无限重复直到强行学会。
```

## 2. 审查完善

### 2.1 Claude 小修吸收

本阶段顺手吸收 Claude 的两个小观察:

1. `additional_repeats = 1` 改为配置项:

```text
APV3ParadigmDiscoveryConfig.additional_evidence_band_repeats = 1
```

2. `TeachingIterationLoop._context_from_failure()` 中的 `competing_pids` 做保序去重:

```text
tuple(dict.fromkeys(...))
```

避免同一 `pid` 在 trace 中重复出现，误导后续竞争数量分析。

### 2.2 最大迭代深度

新增配置:

```text
APV3ActiveLearningConfig.max_teaching_iteration_depth = 3
```

bridge 达到上限后返回:

```text
stopped_reason = max_iteration_depth
```

这不是隐藏失败，而是明确告诉教师侧: 当前上下文下继续同形 evidence 重复没有意义，应暂停或等待新输入。

### 2.3 状态接力

每轮迭代都使用上一轮 `APV3CurriculumRunner` 返回的 state:

```text
current_state = result.state
```

因此已暴露范式会被下一轮 proposal 看到，重复强度会下降。

## 3. 通过落地

修改文件:

```text
APV3.0test/apv3test/config/paradigm_config.py
APV3.0test/apv3test/config/active_learning_config.py
APV3.0test/apv3test/runtime/teaching_protocol_selector.py
APV3.0test/apv3test/runtime/teaching_iteration_loop.py
APV3.0test/apv3test/runtime/active_learning_bridge.py
APV3.0test/apv3test/runtime/__init__.py
```

新增文件:

```text
APV3.0test/tests/test_phase6_7_active_learning_teaching_bridge.py
```

新增对象:

```text
ActiveLearningTeachingResult
APV3ActiveLearningBridge.run_teacher_response_iterations()
```

文件规模:

```text
active_learning_bridge.py: 147 lines
teaching_iteration_loop.py: 108 lines
test_phase6_7_active_learning_teaching_bridge.py: 125 lines
```

## 4. 严谨验收测试

Phase6.7 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_7_active_learning_teaching_bridge.py -q
```

结果:

```text
4 passed in 0.37s
```

Phase6.0-6.7 组合测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_0_active_teacher_request.py APV3.0test\tests\test_phase6_1_active_learning_bridge.py APV3.0test\tests\test_phase6_2_active_learning_trend.py APV3.0test\tests\test_phase6_3_teaching_protocol_selector.py APV3.0test\tests\test_phase6_4_diagnostic_teaching_plan.py APV3.0test\tests\test_phase6_5_multiround_teacher_course.py APV3.0test\tests\test_phase6_6_teaching_iteration_loop.py APV3.0test\tests\test_phase6_7_active_learning_teaching_bridge.py -q
```

结果:

```text
34 passed in 0.80s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
167 passed in 3.21s
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
- 无旧多轮叙事命名残留。

## 5. 成功/失败样例

### 5.1 教师响应后成功停止

输入:

```text
teacher_request = goal::ask / ctx_work
reply_tokens = teacher::answer
case_name = skill_teacher_answer
expected_pid = p:discovered:skill_teacher_answer
```

结果:

```text
stopped_reason = validation_success
iterations = 1
validation success = True
student state has learned p:discovered:skill_teacher_answer
```

含义:

- 成功后不继续教学。

### 5.2 没有教师 tokens 时等待

输入:

```text
reply_tokens = ()
```

结果:

```text
stopped_reason = awaiting_teacher_evidence
iterations = 1
run_result = None
state unchanged
```

含义:

- bridge 不生成答案。
- 没有教师证据时不写学生记忆。

### 5.3 持续失败达到最大深度

输入:

```text
case_name = skill_wrong
expected_pid = p:discovered:skill_teacher_answer
max_teaching_iteration_depth = 2
```

结果:

```text
stopped_reason = max_iteration_depth
iterations = 2
each validation success = False
previous_failure_kind = attention_wrong
```

含义:

- 不无限教学。
- 失败会保留为下一轮诊断，但达到深度上限就停。

### 5.4 已学后重复强度下降

第一次:

```text
was_exposed_at_check_time = False
initial_support_repeats = 2
```

第二次使用第一次返回 state:

```text
was_exposed_at_check_time = True
initial_support_repeats = 1
```

含义:

- state 接力有效。
- 已学会后补习强度下降。

## 6. 最终汇总报告

Phase6.7 已完成:

- 教学迭代 loop 已接回 active learning bridge。
- 外部教师提供 tokens 后，bridge 可运行有限深度教学迭代。
- 成功时停止。
- 无教师证据时等待。
- 持续失败时达到配置化最大深度后停止。
- 已学会后重复强度下降。
- 学生侧仍无 `llm_policy` / `answer_table` / 关键词路由。

仍不能宣称:

- AP 能自己生成教师答案。
- AP 能自己选择教师。
- 完整主动课程规划系统完成。
- 自由中文开放对话底座完成。

下一步建议 Phase6.8:

```text
主动求教端到端 episode:
  Bn/Cn or work_memory failure
  -> teacher_request SA
  -> external teacher reply_tokens
  -> bridge teaching iteration
  -> recall succeeds
  -> later same cue 不再 teacher_request
```

目标:

- 把“求教、教学、学会、停止求教”串成完整端到端验收。
