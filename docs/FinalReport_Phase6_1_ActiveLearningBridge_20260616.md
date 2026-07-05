# APV3.0test Phase6.1 主动学习桥接报告

日期: 2026-06-16

## 1. 设计

Phase6.1 的目标是把 Phase6.0 的 `teacher_request` 接到真实失败信号:

```text
work_memory idle recall
  -> Bn/Cn/attention 失败
  -> teacher_request SA
  -> 教师响应
  -> AP-native evidence
  -> 原工作记忆任务恢复
```

同时支持直接 Bn/Cn recall 失败生成 `teacher_request`。

边界:

- 桥接器只观察失败并创建求教 SA。
- 不直接调用教师。
- 不生成答案。
- 不修改 Bn/Cn 或工作记忆的内部规则。

## 2. 审查完善

### 2.1 桥接而非侵入

新增 `APV3ActiveLearningBridge`，它组合:

- `APV3WorkMemoryAttentionBridge`
- `APV3ActiveTeacherRequestRuntime`

这样工作记忆、注意力、主动学习仍各自保持单一职责。

### 2.2 初跑失败与修正

初跑时“教师响应后原工作记忆任务恢复”失败。

原因:

- 测试把教师响应放得太晚。
- 工作记忆压力按设计自然衰减到恢复阈值以下。

修正:

- 采用连续教学时间线。
- 不强行抬高工作记忆压力。

含义:

- Phase6.1 证明的是连续求教-教学-恢复链路。
- 长时间等待后的再激活，应交给后续能量/期待机制，而不是在本阶段硬补。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/active_learning_bridge.py`
- `APV3.0test/tests/test_phase6_1_active_learning_bridge.py`

修改文件:

- `APV3.0test/apv3test/runtime/__init__.py`

新增对象:

- `APV3ActiveLearningBridge`
- `ActiveLearningBridgeResult`

文件行数:

```text
active_learning_bridge.py: 85
test_phase6_1_active_learning_bridge.py: 144
```

## 4. 严谨验收测试

Phase6.0/6.1 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_1_active_learning_bridge.py APV3.0test\tests\test_phase6_0_active_teacher_request.py -q
```

结果:

```text
9 passed in 0.33s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
142 passed in 3.02s
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

命中均为测试名/测试断言和草稿 buffer 检查，非 runtime 作弊分支。

## 5. 成功样例

### 5.1 工作记忆恢复失败自动求教

输入:

```text
work_memory = goal::ask
context = ctx_work
```

结果:

```text
work_memory recalled = goal::ask
dialogue_result = <none>
teacher_request.reason = remediation_needed
teacher_request.cue_tokens = goal::ask
```

### 5.2 教师响应后原任务恢复

过程:

```text
teacher_request generated
llm_standard_teacher responds through CurriculumRemediationLoop
skill_teacher_answer learned as AP-native evidence
work_memory idle recall again
```

结果:

```text
emitted = teacher::answer
teacher_request_result = <none>
state 中没有 llm_policy
```

含义:

- 教师响应后，原工作记忆任务可以继续。
- 成功后不再生成新的求教请求。

### 5.3 直接 Bn/Cn 失败自动求教

输入:

```text
cue = goal::ask
context = ctx_work
emit_reply = true
```

无已学技能时:

```text
dialogue_result = <none>
teacher_request.reason = remediation_needed
```

### 5.4 成功召回不求教

当 `goal::ask -> teacher::answer` 已学会:

```text
emitted = teacher::answer
teacher_request_result = <none>
```

## 6. 最终汇总报告

Phase6.1 已完成:

- 工作记忆 bridge 失败自动生成 `teacher_request`。
- 直接 Bn/Cn recall 失败自动生成 `teacher_request`。
- 教师响应仍走 AP-native 补习链。
- 教师响应后，原工作记忆任务可恢复并输出。
- 成功召回不会继续求教。

仍不能宣称:

- 完整主动课程设计完成。
- 长时间衰减后的任务再激活完成。
- 自由中文开放对话底座完成。
- 教师选择策略完成。

下一步建议 Phase6.2:

```text
主动学习请求与补习强度衰减的长期趋势探针
```

重点:

- 同一技能多次成功后 teacher_request 频率下降。
- 多次失败时 remediation_intensity / teacher_request 仍可上升。
- 继续保持教师响应 AP-native、学生侧无 LLM 策略字段。
