# APV3.0test Phase6.5 多轮教师课程草案报告

日期: 2026-06-16

## 1. 设计

Phase6.5 的目标是把 Phase6.4 的教师侧 `plan_outline` 扩展成可审计的多轮课程 proposal 草案:

```text
teacher_request SA
  -> TeachingPlanContext
  -> teacher-side plan_outline
  -> multi-round course draft
  -> CurriculumEpisode
  -> AP-native teaching evidence
  -> recall-only validation
```

多轮草案的最小结构:

```text
cue_context_support
  先补 cue/context/target 的稳定支持

successor_evidence
  再补 token-level 后继分布证据

recall_only_validation
  只给 cue/context 验证，不给答案候选池

remediate_on_failure
  若前一轮验证失败，再追加 AP-native 补习证据
```

设计边界:

- 课程轮次只属于教师侧 `protocol_trace`。
- 学生侧不读取 `course_rounds`。
- 学生侧不读取 `plan_outline`。
- 学生侧只接收普通 `CurriculumTeachingStep`。
- 没有教师 `reply_tokens` 时，仍然不生成教学证据。

## 2. 审查完善

### 2.1 为什么是教师侧草案

多轮教学是老师的组织方式，不是学生脑内的捷径。按 AP 哲学，学生真正能学到的是:

- SA 序列
- cue/context
- reply successor
- commit
- reward/punishment
- recall-only validation 的后果

所以新增对象:

```text
TeacherCourseRound
MultiRoundTeacherCourseProposal
```

它们只描述教师侧课程轮廓。最终落到学生侧时，仍然是同一种 AP-native evidence。

### 2.2 不引入阶段路由

课程轮次名包括:

```text
cue_context_support
successor_evidence
recall_only_validation
remediate_on_failure
```

但实际 `CurriculumTeachingStep.stage` 仍统一为:

```text
teacher_response
```

这保证学生侧不会按课程轮次名分支执行，也不会把课程结构当答案路由。

### 2.3 失败后补习

`previous_failure_kind` 只影响教师侧是否追加一轮 AP-native evidence:

```text
previous_failure_kind = cn_successor_weak
  -> remediate_on_failure.teaching_step_count = 1
```

它不会写入学生 state 作为 runtime 决策字段。

## 3. 通过落地

修改文件:

```text
APV3.0test/apv3test/runtime/teaching_protocol_selector.py
APV3.0test/apv3test/runtime/__init__.py
```

新增文件:

```text
APV3.0test/tests/test_phase6_5_multiround_teacher_course.py
```

新增对象:

```text
TeacherCourseRound
MultiRoundTeacherCourseProposal
APV3TeachingProtocolSelector.propose_multiround()
```

文件规模:

```text
teaching_protocol_selector.py: 366 lines
test_phase6_5_multiround_teacher_course.py: 152 lines
```

工程提示:

- `teaching_protocol_selector.py` 暂时仍可控。
- 如果后续继续扩课程编排，建议拆成 selector、course proposal、trace helpers，避免形成新的大对象。

## 4. 严谨验收测试

Phase6.5 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_5_multiround_teacher_course.py -q
```

结果:

```text
5 passed in 0.36s
```

Phase6.0-6.5 组合测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_0_active_teacher_request.py APV3.0test\tests\test_phase6_1_active_learning_bridge.py APV3.0test\tests\test_phase6_2_active_learning_trend.py APV3.0test\tests\test_phase6_3_teaching_protocol_selector.py APV3.0test\tests\test_phase6_4_diagnostic_teaching_plan.py APV3.0test\tests\test_phase6_5_multiround_teacher_course.py -q
```

结果:

```text
26 passed in 0.57s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
159 passed in 3.11s
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

### 5.1 没有教师 tokens 时仍等待

输入:

```text
reply_tokens = ()
failure_kind = bn_not_recalled
```

结果:

```text
proposal.status = awaiting_teacher_evidence
course_rounds = await_teacher_evidence
teaching_steps = ()
validation_cases = ()
```

含义:

- 多轮课程草案不会自己生成答案。
- 没有教师证据时不写学生记忆。

### 5.2 冷启动多轮课程可运行

输入:

```text
reply_tokens = teacher::answer
case_name = skill_teacher_answer
failure_kind = cn_successor_weak
```

结果:

```text
course_rounds:
  cue_context_support      teaching_step_count = 2
  successor_evidence       teaching_step_count = 1
  recall_only_validation   validation_case_count = 1
  remediate_on_failure     teaching_step_count = 0

total teaching_steps = 3
validation success = True
emitted = teacher::answer
```

含义:

- 先补支持，再补后继，再验证的最小闭环成立。

### 5.3 前轮失败后追加补习

输入:

```text
previous_failure_kind = cn_successor_weak
```

结果:

```text
remediate_on_failure.trigger = cn_successor_weak
remediate_on_failure.teaching_step_count = 1
total teaching_steps = 4
```

含义:

- 失败后的补习仍是 AP-native teaching evidence。
- 没有新增关键词规则或答案表。

### 5.4 课程轮次不泄漏到学生 state

断言:

```text
cue_context_support not in student_state
successor_evidence not in student_state
recall_only_validation not in student_state
remediate_on_failure not in student_state
llm_policy not in student_state
answer_table not in student_state
```

含义:

- 课程结构只属于教师侧。
- 学生侧没有课程标签路由。

### 5.5 已暴露范式降低 cue/context 支持轮

第一次:

```text
cue_context_support.teaching_step_count = 2
```

目标范式暴露后:

```text
cue_context_support.teaching_step_count = 1
total teaching_steps = 2
```

含义:

- 初学需要更多证据。
- 已学会后只需弱补强。

## 6. 最终汇总报告

Phase6.5 已完成:

- `plan_outline` 已扩展为多轮教师课程草案。
- 支持 cue/context support、successor evidence、recall-only validation、remediate-on-failure 四轮轮廓。
- 无教师证据时仍不生成教学。
- 有教师证据时可生成 AP-native `CurriculumEpisode` 并通过验证。
- 前一轮失败可追加 AP-native 补习 evidence。
- 课程轮次标签不会进入学生 state。

仍不能宣称:

- 完整主动课程规划系统完成。
- AP 能自己生成教师答案。
- AP 能自己选择教师。
- 多技能长期课程自动优化完成。
- 自由中文开放对话底座完成。

下一步建议 Phase6.6:

```text
做多轮课程 proposal 与实际 train -> validate -> diagnose -> remediate 的闭环整合:
  初始 course proposal
  运行 CurriculumRunner
  若 validation 失败，生成新的 TeachingPlanContext
  再产出下一轮 course proposal
  验证请求/课程/补习可以连续迭代

仍然要求:
  学生侧只接收 AP-native evidence
  不引入答案表/关键词路由/学生侧 LLM
```
