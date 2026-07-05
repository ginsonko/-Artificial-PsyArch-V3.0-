# APV3.0test Phase6.4 诊断上下文教学计划轮廓报告

日期: 2026-06-16

## 1. 设计

Phase6.4 的目标是把 Phase6.3 的 `TeacherEpisodeProposal` 扩展为能携带更多教师侧诊断上下文:

```text
teacher_request SA
  -> failure_kind / failure_detail
  -> work_memory_bundle
  -> competing_pids
  -> pressure_sources
  -> teacher-side plan_outline
  -> AP-native CurriculumEpisode
```

拟人原则上的对应:

- 孩子不会只说“我不会”，还会表现出“不记得题目”“想起了上一个任务”“两个答案搞混了”等状态。
- 老师可以据此调整教学方式。
- 但孩子真正学到的仍是经验、奖惩、上下文和后继，而不是老师内心的教学脚本。

因此本阶段新增的 `plan_outline` 只属于教师侧 proposal trace，不进入学生侧 runtime 决策。

## 2. 审查完善

### 2.1 教师侧诊断不是学生侧路由

新增对象:

```text
TeachingPlanContext
```

包含:

```text
failure_kind
failure_detail
work_memory_bundle
competing_pids
pressure_sources
current_focus_pid
```

这些字段只用于生成 `protocol_trace.plan_outline`。真正写入学生侧的仍是:

```text
CurriculumTeachingStep(
  cue_tokens,
  reply_tokens,
  context_tokens,
  stage="teacher_response",
  reward_delta=1.0,
)
```

### 2.2 不同失败类型的轮廓

当前最小轮廓:

```text
bn_not_recalled             -> increase_cue_context_support
cn_successor_weak           -> strengthen_successor_distribution
attention_wrong             -> teach_context_disambiguation
work_memory_resume_failed   -> bind_unfinished_bundle_to_successor
work_memory_bundle present  -> include_work_memory_resume_cue
competing_pids present      -> contrast_competing_paradigms_with_feedback
pressure_sources present    -> mark_pressure_source_for_teacher
```

审查边界:

- 这些标签不是学生侧分支。
- 它们不会写入 `IncrementalTickRuntime`。
- 它们不会被 `CurriculumRunner` 用来选择答案。
- 它们只是教师组织教学材料时的 trace。

## 3. 通过落地

修改文件:

```text
APV3.0test/apv3test/runtime/teaching_protocol_selector.py
APV3.0test/apv3test/runtime/__init__.py
```

新增文件:

```text
APV3.0test/tests/test_phase6_4_diagnostic_teaching_plan.py
```

新增对象:

```text
TeachingPlanContext
```

文件规模:

```text
teaching_protocol_selector.py: 194 lines
test_phase6_4_diagnostic_teaching_plan.py: 155 lines
```

## 4. 严谨验收测试

Phase6.4 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_4_diagnostic_teaching_plan.py -q
```

结果:

```text
4 passed in 0.41s
```

Phase6.0-6.4 组合测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_0_active_teacher_request.py APV3.0test\tests\test_phase6_1_active_learning_bridge.py APV3.0test\tests\test_phase6_2_active_learning_trend.py APV3.0test\tests\test_phase6_3_teaching_protocol_selector.py APV3.0test\tests\test_phase6_4_diagnostic_teaching_plan.py -q
```

结果:

```text
21 passed in 0.49s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
154 passed in 3.12s
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

### 5.1 Bn/Cn/注意力失败产生不同教师侧轮廓

输入:

```text
failure_kind = bn_not_recalled
failure_kind = cn_successor_weak
failure_kind = attention_wrong
```

结果:

```text
bn_not_recalled   -> increase_cue_context_support
cn_successor_weak -> strengthen_successor_distribution
attention_wrong   -> teach_context_disambiguation
```

含义:

- 教师能看到不同教学建议。
- 但没有 reply_tokens 时，三者都只是 `awaiting_teacher_evidence`。
- 不会生成答案。

### 5.2 工作记忆恢复失败携带未完成 bundle

输入:

```text
failure_kind = work_memory_resume_failed
work_memory_bundle = goal::ask, subgoal::resume
pressure_sources = work_memory_unfinished, teacher_request
```

结果:

```text
plan_outline includes:
  bind_unfinished_bundle_to_successor
  include_work_memory_resume_cue
  mark_pressure_source_for_teacher

teaching_steps = ()
validation_cases = ()
```

含义:

- 未完成任务和压力来源可以作为教师侧诊断信息。
- 没有教师证据时仍不写入学生。

### 5.3 多技能冲突计划仍按普通 AP-native episode 学习

输入:

```text
failure_kind = attention_wrong
competing_pids = skill_wrong, skill_teacher_answer
reply_tokens = teacher::answer
```

结果:

```text
plan_outline includes contrast_competing_paradigms_with_feedback
teaching step stage = teacher_response
validation success = True
emitted = teacher::answer
```

额外断言:

```text
contrast_competing_paradigms_with_feedback not in student state
p:discovered:skill_wrong not in student state
llm_policy not in student state
answer_table not in student state
```

含义:

- 冲突诊断只帮助教师组织材料。
- 学生侧仍只通过普通 evidence 学习。

### 5.4 不同计划上下文保持同一学生 evidence 形状

对照:

```text
work_memory_resume_failed
attention_wrong + competing_pids
```

结果:

```text
plan_outline 不同
teaching_steps 相同
validation_cases 相同
```

含义:

- 教师侧可以差异化理解失败。
- 学生侧不会因为标签不同而获得特殊捷径。

## 6. 最终汇总报告

Phase6.4 已完成:

- `TeacherEpisodeProposal` 已能携带诊断上下文。
- Bn/Cn/注意力/工作记忆/多技能冲突能形成不同教师侧 plan outline。
- 没有教师证据时仍只等待，不生成教学。
- 有教师证据时仍生成普通 AP-native `CurriculumEpisode`。
- 诊断标签不会写入学生 runtime 做答案路由。

仍不能宣称:

- 完整主动课程规划系统完成。
- AP 能自己生成教师答案。
- AP 能自己选择教师。
- 多轮复杂课程自动编排完成。
- 自由中文开放对话底座完成。

下一步建议 Phase6.5:

```text
把 teacher-side plan outline 扩展成多轮课程 proposal 草案:
  先补 cue/context support
  再补 successor evidence
  再做 recall-only validation
  再根据失败进入下一轮 remediation

仍然要求:
  学生侧只接收 AP-native evidence
  不引入答案表/关键词路由/学生侧 LLM
```
