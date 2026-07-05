# APV3.0test Phase6.3 主动求教到标准教学协议选择器报告

日期: 2026-06-16

## 1. 设计

Phase6.3 的目标是把 Phase6.0-6.2 已经存在的 `teacher_request` SA 接到教师侧标准教学协议选择器:

```text
teacher_request SA
  -> 提取 cue/context/失败诊断/压力来源
  -> 等待教师提供 reply tokens
  -> 生成 teacher episode proposal
  -> CurriculumEpisode
  -> AP-native teaching steps
  -> recall-only validation
```

核心边界:

- 选择器属于教师侧组织器，不属于学生侧推理器。
- 没有教师 tokens 时，选择器只能返回 `awaiting_teacher_evidence`。
- 选择器不能自己生成答案。
- LLM 标准教师和自然教师都只能提供同构的 AP-native evidence。
- 学生运行态仍然只读取 `CurriculumEpisode` 写入的 committed observation、reward 和 validation，不读取 LLM policy。

## 2. 审查完善

### 2.1 为什么不把选择器塞进 teacher_request

`teacher_request` 的语义是状态池里的求教 SA:

```text
我在这个 cue/context 下失败了，而且压力足够高，需要外部教师。
```

它不应该同时负责课程组织。Phase6.3 新增独立模块:

```text
APV3TeachingProtocolSelector
```

这样主动学习链路保持分层:

- `active_teacher_request.py`: 只产生求教 SA。
- `teaching_protocol_selector.py`: 只把教师证据组织成标准教学 episode。
- `curriculum.py`: 只执行 AP-native teaching/validation。

### 2.2 防止选择器变成答案生成器

本阶段测试专门覆盖:

```text
reply_tokens = ()
  -> status = awaiting_teacher_evidence
  -> teaching_steps = ()
  -> validation_cases = ()
```

这保证没有教师证据时，系统不会伪造答案、伪造教学步骤或伪造验证目标。

### 2.3 教师阶段标签仍是 trace

生成的 teaching step 使用:

```text
stage = teacher_response
```

该字段只作为教师侧 trace。当前 `APV3CurriculumRunner` 不按 stage 分支决策，只把它传入 observation trace，因此不构成人工 schema 路由。

## 3. 通过落地

新增文件:

```text
APV3.0test/apv3test/runtime/teaching_protocol_selector.py
APV3.0test/tests/test_phase6_3_teaching_protocol_selector.py
```

修改文件:

```text
APV3.0test/apv3test/runtime/__init__.py
```

新增对象:

```text
TeacherEpisodeProposal
APV3TeachingProtocolSelector
```

文件规模:

```text
teaching_protocol_selector.py: 129 lines
test_phase6_3_teaching_protocol_selector.py: 128 lines
```

## 4. 严谨验收测试

Phase6.3 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_3_teaching_protocol_selector.py -q
```

结果:

```text
4 passed in 0.31s
```

Phase6.0-6.3 组合测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_0_active_teacher_request.py APV3.0test\tests\test_phase6_1_active_learning_bridge.py APV3.0test\tests\test_phase6_2_active_learning_trend.py APV3.0test\tests\test_phase6_3_teaching_protocol_selector.py -q
```

结果:

```text
17 passed in 0.48s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
150 passed in 3.25s
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
rg -n "most_common_reply|_observations_for_bucket|remediate:|if percept|if audio|if action|if text|if vision|if task|task_queue|answer_table|llm_policy" APV3.0test\apv3test APV3.0test\tests
```

结果:

- 命中均为测试名、测试断言、防泄漏断言或 `draft_action.py` buffer 非空检查。
- 未发现 runtime 侧答案表、学生侧 LLM、整句宏、模态特权分支。

## 5. 成功/失败样例

### 5.1 没有教师证据时等待

输入:

```text
teacher_request:
  cue = goal::ask
  context = ctx_work
  reason = remediation_needed

reply_tokens = ()
```

结果:

```text
proposal.status = awaiting_teacher_evidence
teaching_steps = ()
validation_cases = ()
```

含义:

- 求教 SA 不等于答案。
- 选择器不能代替老师生成内容。

### 5.2 教师提供证据后生成标准 episode

输入:

```text
reply_tokens = teacher::answer
case_name = skill_teacher_answer
expected_pid = p:discovered:skill_teacher_answer
```

结果:

```text
proposal.status = ready
teaching_steps = 2
stage = teacher_response
validation success = True
emitted = teacher::answer
focus_pid = p:discovered:skill_teacher_answer
```

含义:

- 教师证据被转成 AP-native teaching steps。
- 通过 recall-only validation 验收，不是答案表回放。

### 5.3 自然教师和 LLM 标准教师等价

对照:

```text
source_kind = natural_teacher
source_kind = llm_standard_teacher
```

结果:

```text
emitted_tokens 相同
focus_pid 相同
student state 中没有 llm_policy
```

含义:

- 两种教师来源只影响外部教学来源记录。
- 学生侧行为由同构 AP-native evidence 决定。

### 5.4 已学技能降低教学重复

第一次:

```text
evidence_repeats = 2
```

目标范式暴露后:

```text
evidence_repeats = 1
```

含义:

- 初学需要更多证据。
- 已学会后只需要弱补强。

## 6. 最终汇总报告

Phase6.3 已完成:

- `teacher_request` 已能被转换为标准教学协议 proposal。
- proposal 会携带 cue/context/失败诊断/压力来源。
- 没有教师 reply tokens 时不会生成教学。
- 教师提供 tokens 后可生成 AP-native `CurriculumEpisode` 并通过 validation。
- 自然教师与 LLM 标准教师在学生侧 evidence 等价。
- 已暴露范式会降低教学重复次数。

仍不能宣称:

- AP 已经能自己决定应该问哪位教师。
- AP 已经能自己生成教师答案。
- 完整主动课程规划系统完成。
- 自由中文开放对话底座完成。

下一步建议 Phase6.4:

```text
把 teacher episode proposal 与失败诊断/工作记忆/多技能冲突组合起来，
验证同一 teacher_request 在不同失败类型下能生成不同的 AP-native 教学计划轮廓，
但仍不在学生侧写入任何硬编码路由。
```
