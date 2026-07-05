# APV3.0test Phase6.9 teacher_request 持久化恢复 parity 报告

日期: 2026-06-16

## 1. 设计

Phase6.9 的目标是验证 Phase6.8 的主动求教闭环不仅在内存态成立，也能进入 SQLite 持久化恢复语义:

```text
failure / teacher_request / external teacher evidence / learned ParadigmSA / work_memory item
  -> SQLiteRuntimeStore.save_state()
  -> SQLiteRuntimeStore.load_state()
  -> warm-loaded state continues runtime
  -> same cue recall succeeds
  -> no repeated teacher_request
```

设计边界:

- `load_state()` 恢复出的完整 state blob 是权威运行态。
- `load_ontology_projection()` 只用于检查范式、观察、统计等 ontology projection 是否同步写出，不把 projection 当运行态。
- 不新增学生侧规则、答案表、关键词分支或 LLM 策略。
- 持久化恢复后必须继续跑 APV3 runtime，而不是只比较 JSON。

## 2. 审查完善

### 2.1 SQLite 现状审查

`SQLiteRuntimeStore` 当前采用双层语义:

```text
runtime_states.blob = authoritative full runtime state
projection tables = online_embedding / transitions / paradigm_sa / action_outcomes / percept_prototypes / paradigm_observations / paradigm_stats / role_transition_stats
```

因此 Phase6.9 的 parity 判据分成两层:

- 完整 `load_state()` 必须保留 `teacher_requests`、`working_memory_items`、`state_field_items`、`paradigms`、`paradigm_stats`、`paradigm_observations`。
- projection 必须能看到 `paradigm_sa`、`paradigm_observations`、`paradigm_stats`。

### 2.2 状态纯度问题

目标测试第一次运行时暴露了一个真实问题:

```text
APV3WorkMemoryRuntime.run_tick()
  previous: _ensure_work_memory_state(dict(state))
```

这是浅拷贝，会复用传入 state 的嵌套 list/dict。工作记忆空闲恢复会追加 `working_memory_trace`，从而污染调用者传入的 state，破坏保存前/恢复后严格 parity。

修复:

```text
APV3WorkMemoryRuntime.run_tick()
  now: _ensure_work_memory_state(deepcopy(dict(state)))
```

这是 AP runtime 的状态契约修复，不是为某个答案增加捷径。修复后工作记忆与 `IncrementalTickRuntime`、`APV3ActiveTeacherRequestRuntime` 一样保持纯函数式输入状态语义。

### 2.3 工程观察

`work_memory.py` 目前约 305 行，略过 300 行心理线。本阶段只新增深拷贝修复，不做拆分；后续如果继续扩展工作记忆，应考虑拆出 trace/state-field/projection helpers，避免形成小型 god-object。

## 3. 通过落地

修改文件:

```text
APV3.0test/apv3test/runtime/work_memory.py
```

新增文件:

```text
APV3.0test/tests/test_phase6_9_teacher_request_persistence_parity.py
```

新增 2 个 parity probe:

1. `test_phase6_9_direct_teacher_request_survives_sqlite_warm_load`
2. `test_phase6_9_work_memory_teacher_request_survives_sqlite_warm_load`

## 4. 严谨验收测试

Phase6.9 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_9_teacher_request_persistence_parity.py -q
```

结果:

```text
2 passed in 0.52s
```

工作记忆相关回归:

```powershell
python -m pytest APV3.0test\tests\test_phase5_7_work_memory_recovery.py APV3.0test\tests\test_phase5_8_work_memory_attention_bridge.py APV3.0test\tests\test_phase5_9_work_memory_remediation_conflict_combo.py -q
```

结果:

```text
12 passed in 0.36s
```

Phase6.0-6.9 组合测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_0_active_teacher_request.py APV3.0test\tests\test_phase6_1_active_learning_bridge.py APV3.0test\tests\test_phase6_2_active_learning_trend.py APV3.0test\tests\test_phase6_3_teaching_protocol_selector.py APV3.0test\tests\test_phase6_4_diagnostic_teaching_plan.py APV3.0test\tests\test_phase6_5_multiround_teacher_course.py APV3.0test\tests\test_phase6_6_teaching_iteration_loop.py APV3.0test\tests\test_phase6_7_active_learning_teaching_bridge.py APV3.0test\tests\test_phase6_8_active_learning_end_to_end.py APV3.0test\tests\test_phase6_9_teacher_request_persistence_parity.py -q
```

结果:

```text
40 passed in 1.04s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
173 passed in 3.35s
```

编译检查:

```powershell
python -m py_compile APV3.0test\apv3test\runtime\work_memory.py APV3.0test\tests\test_phase6_9_teacher_request_persistence_parity.py
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
rg -n "most_common_reply|_observations_for_bucket|remediate:|if percept|if audio|if action|if text|if vision|if task|task_queue|answer_table|llm_policy|propose_multiround|MultiRoundTeacherCourseProposal|TeacherCourseRound" APV3.0test\apv3test APV3.0test\tests
```

结果:

- 命中均为测试反泄漏断言或 `draft_action.py` buffer 非空检查。
- 无 `most_common_reply` fallback。
- 无旧多轮教师课程命名残留。
- 无学生侧 `llm_policy` / `answer_table`。

## 5. 成功/失败样例

### 5.1 直接求教链路持久化恢复

输入:

```text
cue = goal::ask
context = ctx_work
initial recall = failed
teacher_request = created
teacher reply_tokens = teacher::answer
learned pid = p:discovered:skill_teacher_answer
```

保存恢复:

```text
SQLite save_state(learned.state)
SQLite load_state(state_id)
```

结果:

```text
restored == learned.state
restored teacher_requests[0].cue_tokens = goal::ask
warm recall emitted = teacher::answer
after warm recall = no teacher_request
projection.paradigm_sa contains p:discovered:skill_teacher_answer
projection.paradigm_stats contains skill_teacher_answer|goal::ask
```

含义:

- teacher_request 历史、教师 evidence、已暴露范式、范式统计和观察都能跨 SQLite warm-load 保留。
- warm-loaded state 可以继续 APV3 runtime 召回，不依赖内存对象。

### 5.2 工作记忆求教链路持久化恢复

输入:

```text
work_memory focus = goal::resume
pressure = 0.92
idle recall before teaching = failed
teacher_request = created
teacher reply_tokens = continue::resume
learned pid = p:discovered:skill_resume_answer
```

保存恢复:

```text
SQLite save_state(learned.state)
SQLite load_state(state_id)
```

结果:

```text
restored == learned.state
restored working_memory_items[0].sa_bundle = goal::resume
restored teacher_requests[0].cue_tokens = goal::resume
state_field_items contains work_memory_unfinished
state_field_items contains teacher_request
warm idle resume emitted = continue::resume
warm idle resume = no teacher_request
```

含义:

- 未完成任务压力项作为 state blob 的一部分被恢复。
- teacher_request 作为状态场 SA 被恢复。
- warm-load 后工作记忆仍能把任务拉回焦点，并沿 Bn/Cn 召回已学回复。

### 5.3 失败样例: 浅拷贝状态污染

初次目标测试失败:

```text
assert restored == learned.state
```

失败原因:

```text
warm_resume = bridge.run_work_memory_idle(restored, ...)
```

在旧实现里，work memory 的浅拷贝会让嵌套 `working_memory_trace` 被调用过程污染，破坏严格 parity。

修复后:

```text
2 passed in 0.52s
```

## 6. 最终汇总报告

Phase6.9 已完成:

- 主动求教直接链路通过 SQLite warm-load parity。
- 工作记忆求教链路通过 SQLite warm-load parity。
- `teacher_requests`、`working_memory_items`、`state_field_items`、`paradigms`、`paradigm_stats`、`paradigm_observations` 在完整 state blob 中可恢复。
- `paradigm_sa`、`paradigm_observations`、`paradigm_stats` 在 ontology projection 中可审查。
- warm-loaded state 可以继续运行 APV3 runtime，并在同 cue 成功召回后停止重复求教。
- 修复了 `APV3WorkMemoryRuntime` 浅拷贝导致的输入 state 污染问题。

仍不能宣称:

- SQLite 10G 遗忘淘汰系统已完成。
- 热/温/冷层完整策略已完成。
- AP 能自己生成教师答案或选择教师。
- 完整自由中文开放对话底座已完成。
- 任意长期开放对话、Fresh300 或完整旧 GL 技能迁移已完成。

下一步建议 Phase7.0:

```text
做主动学习 + 持久化 + 长期趋势的整合探针:
  repeated failure/request trend
  -> teacher response iterations
  -> SQLite save/load per cycle
  -> support rises and request pressure falls
  -> persistent failure reaches suppression window
```

目标是从单次 warm-load parity 推进到多周期学习曲线和持久化状态演化。
