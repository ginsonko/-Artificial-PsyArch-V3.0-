# APV3.0test Phase6.8 主动求教端到端 episode 报告

日期: 2026-06-16

## 1. 设计

Phase6.8 的目标是把前序主动学习模块串成一个完整 episode:

```text
Bn/Cn or work_memory failure
  -> teacher_request SA
  -> external teacher reply_tokens
  -> bridge teaching iteration
  -> AP-native evidence 写入
  -> same cue recall succeeds
  -> later same cue no new teacher_request
```

设计边界:

- 学生侧不生成教师答案。
- 学生侧不读取 `llm_policy`、`answer_table`、关键词路由或整句宏。
- 外部教师只能提供 `reply_tokens` 作为教学 evidence。
- 教师侧 proposal/trace 可以存在，但运行时学生只接收 AP-native teaching episode 产生的统计、support、reward/punish、范式与后继证据。
- 工作记忆恢复必须遵守压力衰减窗口，不用放宽 runtime 来制造“长时间后仍想起”的假象。

## 2. 审查完善

### 2.1 端到端真实性

本阶段不直接调用已学会状态，而是先让 `IncrementalTickRuntime` 或 `APV3WorkMemoryAttentionBridge` 真实失败，再由 `APV3ActiveLearningBridge` 观察失败并生成 `teacher_request SA`。

### 2.2 外部教师边界

`run_teacher_response_iterations()` 只有在外部已经提供 `reply_tokens` 时才运行教学迭代；当 `reply_tokens=()` 时返回:

```text
stopped_reason = awaiting_teacher_evidence
state unchanged
```

### 2.3 工作记忆时间窗

第一次测试把恢复验证放到 tick 60，工作记忆压力按 `0.92^age` 衰减后低于空闲召回阈值，因此这是测试窗口不符合工作记忆模型，而不是 runtime 缺陷。已改为 tick 32，在短时未完成压力仍有效时验证恢复。

### 2.4 有限失败边界

持续教学失败时必须在 `max_teaching_iteration_depth` 停止，避免“教不会就无限教”的循环。

## 3. 通过落地

新增文件:

```text
APV3.0test/tests/test_phase6_8_active_learning_end_to_end.py
```

新增 4 个端到端 probe:

1. `test_phase6_8_direct_failure_ask_teacher_learn_recall_then_stop_asking`
2. `test_phase6_8_work_memory_failure_ask_teacher_then_idle_resume_succeeds`
3. `test_phase6_8_no_external_teacher_evidence_waits_without_learning`
4. `test_phase6_8_persistent_teaching_failure_stops_at_depth_boundary`

未修改学生 runtime 逻辑。Phase6.8 主要是组合验收门。

## 4. 严谨验收测试

目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_8_active_learning_end_to_end.py -q
```

结果:

```text
4 passed in 0.35s
```

Phase6.0-6.8 组合测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_0_active_teacher_request.py APV3.0test\tests\test_phase6_1_active_learning_bridge.py APV3.0test\tests\test_phase6_2_active_learning_trend.py APV3.0test\tests\test_phase6_3_teaching_protocol_selector.py APV3.0test\tests\test_phase6_4_diagnostic_teaching_plan.py APV3.0test\tests\test_phase6_5_multiround_teacher_course.py APV3.0test\tests\test_phase6_6_teaching_iteration_loop.py APV3.0test\tests\test_phase6_7_active_learning_teaching_bridge.py APV3.0test\tests\test_phase6_8_active_learning_end_to_end.py -q
```

结果:

```text
38 passed in 0.73s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
171 passed in 3.09s
```

编译检查:

```powershell
python -m py_compile APV3.0test\tests\test_phase6_8_active_learning_end_to_end.py
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

- 该命中是 draft buffer 非空检查，不是文本模态特权分支。

额外红线扫描:

```powershell
rg -n "most_common_reply|_observations_for_bucket|remediate:|if percept|if audio|if action|if text|if vision|if task|task_queue|answer_table|llm_policy|propose_multiround|MultiRoundTeacherCourseProposal|TeacherCourseRound" APV3.0test\apv3test APV3.0test\tests
```

结果:

- 命中均为测试断言、旧命名防泄漏扫描或 `draft_action.py` buffer 非空检查。
- 无 `most_common_reply` fallback。
- 无旧多轮教师课程命名残留。
- 无学生侧 `llm_policy` / `answer_table`。

## 5. 成功/失败样例

### 5.1 直接 Bn/Cn 失败后求教并学会

输入:

```text
cue = goal::ask
context = ctx_work
initial recall = failed
teacher reply_tokens = teacher::answer
case_name = skill_teacher_answer
expected_pid = p:discovered:skill_teacher_answer
```

结果:

```text
teacher_request.reason = remediation_needed
teaching stopped_reason = validation_success
later recall emitted = teacher::answer
later observe_recall_failure = no teacher_request
```

含义:

- 失败会产生求教。
- 外部教师 evidence 会通过 AP-native 教学 episode 写入。
- 学会后同 cue 的成功召回会抑制重复求教。

### 5.2 工作记忆恢复失败后求教并恢复

输入:

```text
work_memory focus = goal::resume
pressure = 0.92
idle recall before teaching = failed
teacher reply_tokens = continue::resume
```

结果:

```text
work_memory recalled goal::resume
initial Bn/Cn recall failed
teacher_request created
teaching stopped_reason = validation_success
idle resume recall emitted = continue::resume
new teacher_request = None
```

含义:

- 未完成压力可以把旧任务拉回焦点。
- 焦点恢复后如果 Bn/Cn 失败，会主动求教。
- 学会后再次恢复该任务不会继续求教。

### 5.3 无外部教师证据时等待

输入:

```text
reply_tokens = ()
```

结果:

```text
stopped_reason = awaiting_teacher_evidence
run_result = None
state unchanged
paradigms = []
```

含义:

- bridge 不会替教师生成答案。
- 没有 evidence 时不写学生记忆。

### 5.4 持续失败时有限停止

输入:

```text
case_name = skill_wrong_pid
expected_pid = p:discovered:skill_teacher_answer
max_teaching_iteration_depth = 2
```

结果:

```text
stopped_reason = max_iteration_depth
iterations = 2
each validation success = False
```

含义:

- 系统不会无限重复教学。
- 失败被保留为后续诊断上下文，而不是隐藏成成功。

## 6. 最终汇总报告

Phase6.8 已完成:

- 主动求教端到端最小 episode 通过。
- Bn/Cn 失败可以生成 `teacher_request SA`。
- 工作记忆恢复失败可以生成 `teacher_request SA`。
- 外部教师响应可以通过 teaching iteration 写入 AP-native evidence。
- 学会后同 cue 可成功召回，并停止重复求教。
- 无教师证据时等待，不写入学习状态。
- 持续失败时按配置深度停止。
- 红线扫描未发现学生侧 LLM、答案表、关键词路由、旧 Cn 字面 fallback 或模态特权分支。

仍不能宣称:

- AP 能自己生成教师答案。
- AP 能自主选择教师或外部信息源。
- 完整主动课程规划系统已经完成。
- 完整自由中文开放对话底座已经完成。
- 任意跨模态泛化、Fresh300 或真实长期开放对话已经完成。

下一步建议 Phase6.9:

```text
做 teacher_request 与持久化恢复 parity:
  failure/request/teacher evidence/learned paradigm/work_memory item
  -> SQLite save
  -> warm load
  -> same cue recall succeeds
  -> no repeated teacher_request
```

目标是确认主动求教闭环不仅在内存态成立，也能进入持久化中文对话底座所需的热/温/冷层恢复语义。
