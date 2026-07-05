# APV3.0test Phase6.5 Claude 纠偏吸收报告

日期: 2026-06-16

## 1. 设计

本轮目标是在进入 Phase6.6 前，吸收 Claude 对 Phase6.5 的三点纠偏:

1. `propose_multiround` 把同一份 `(cue, reply, context)` 证据重复 N 次，却叙述成“多轮差异化课程”，有叙事美化风险。
2. `_plan_outline` 按 `failure_kind` 做 if/elif 映射，虽然只在 trace 中，但有发展成诊断标签路由的风险。
3. selector 读取 `paradigms[].exposed` 决定重复次数，但不写 state，需要显式暴露 state handoff 约束。

本次选择采纳 Claude 建议的 A 路线:

```text
不假装已经实现真正差异化多轮课程。
把它诚实改成“同形 AP-native evidence 的重复课程草案”。
```

原因:

- 真实差异化课程需要更完整的课程设计模型。
- 现在硬做 successor 尾部 token、对比 context 等，很容易重新引入硬编码。
- 当前最符合 AP 边界的做法，是明确学生侧看到的是同形证据重复。

## 2. 审查完善

### 2.1 纠偏一: 多轮叙事改为重复证据

旧命名:

```text
TeacherCourseRound
MultiRoundTeacherCourseProposal
propose_multiround()
course_rounds
```

新命名:

```text
TeacherEvidenceRepeatBand
RepeatedEvidenceCourseProposal
propose_repeated_evidence_course()
repeat_bands
```

新增 trace:

```text
student_evidence_shape = same_cue_reply_context_repeated
```

含义:

- 教师侧可以把重复分配到不同 band 解释。
- 学生侧实际收到的是同形 AP-native evidence。
- 报告和测试不再宣称真实差异化多轮课程已经完成。

### 2.2 纠偏二: plan_outline 去掉诊断标签应对表

旧逻辑:

```text
bn_not_recalled           -> increase_cue_context_support
cn_successor_weak         -> strengthen_successor_distribution
attention_wrong           -> teach_context_disambiguation
work_memory_resume_failed -> bind_unfinished_bundle_to_successor
```

新逻辑:

```text
failure_kind -> address:<failure_kind>
work_memory_bundle -> include:work_memory_bundle
competing_pids -> include:competing_pids
pressure_sources -> include:pressure_sources
has_teacher_evidence -> provide:committed_successor_evidence
```

含义:

- selector 不再内置“某诊断该怎么教”的策略表。
- 具体怎么教留给教师侧智能体。
- 这降低了后续把诊断标签变成 runtime schema 路由的风险。

### 2.3 纠偏三: exposed 状态检查显式化

新增 trace:

```text
was_exposed_at_check_time
state_handoff_contract = caller_must_use_runner_returned_state_for_next_proposal
```

含义:

- selector 仍不写学生 state，这是正确边界。
- 但调用方必须把 `CurriculumRunner.run()` 返回的新 state 传给下一次 proposal。
- 如果调用方复用旧 state，`was_exposed_at_check_time` 会持续为 false，重复次数不会下降。

## 3. 通过落地

修改文件:

```text
APV3.0test/apv3test/runtime/teaching_protocol_selector.py
APV3.0test/apv3test/runtime/__init__.py
APV3.0test/tests/test_phase6_4_diagnostic_teaching_plan.py
APV3.0test/tests/test_phase6_5_multiround_teacher_course.py
```

主要变化:

- 移除误导性 `MultiRoundTeacherCourseProposal` / `TeacherCourseRound` / `propose_multiround` 命名。
- 新增 `RepeatedEvidenceCourseProposal` / `TeacherEvidenceRepeatBand` / `propose_repeated_evidence_course`。
- `plan_outline` 改成通用 `address:` / `include:` 字段。
- 测试显式断言同形证据重复。
- 测试显式断言 `was_exposed_at_check_time` 从 false 变为 true。

当前文件规模:

```text
teaching_protocol_selector.py: 366 lines
test_phase6_5_multiround_teacher_course.py: 156 lines
```

工程提示:

- `teaching_protocol_selector.py` 已到 366 行。
- Phase6.6 前后若继续扩展，建议拆分 selector、proposal dataclasses、trace helpers。

## 4. 严谨验收测试

纠偏相关测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_3_teaching_protocol_selector.py APV3.0test\tests\test_phase6_4_diagnostic_teaching_plan.py APV3.0test\tests\test_phase6_5_multiround_teacher_course.py -q
```

结果:

```text
13 passed in 0.63s
```

Phase6.5 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_5_multiround_teacher_course.py -q
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
159 passed in 3.31s
```

误导性命名扫描:

```powershell
rg -n "MultiRoundTeacherCourseProposal|TeacherCourseRound|propose_multiround|course_rounds|cue_context_support|successor_evidence|remediate_on_failure|increase_cue_context_support|strengthen_successor_distribution|teach_context_disambiguation|contrast_competing_paradigms_with_feedback|bind_unfinished_bundle_to_successor" APV3.0test\apv3test APV3.0test\tests
```

结果:

```text
APV3.0test\apv3test\runtime\teaching_protocol_selector.py:343:
  outline.append("provide:committed_successor_evidence")
```

审查:

- 该命中不是旧的硬编码诊断策略表。
- 它只表示教师 evidence 已存在时，可提供普通 committed successor evidence。

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

## 5. 成功/失败样例

### 5.1 同形证据重复被显式标注

测试断言:

```text
student_evidence_shape = same_cue_reply_context_repeated
len({(cue_tokens, reply_tokens, context_tokens)}) == 1
```

含义:

- 不再假装学生侧收到三种不同课程证据。
- 这只是同形 AP-native evidence 的重复 schedule。

### 5.2 plan_outline 不再内置应对策略

输入:

```text
failure_kind = cn_successor_weak
```

输出:

```text
address:cn_successor_weak
provide:committed_successor_evidence
```

含义:

- selector 只传递诊断事实。
- “怎么教”不在 selector 内部硬编码。

### 5.3 state handoff 约束显式可见

第一次 proposal:

```text
was_exposed_at_check_time = false
initial_support_repeats = 2
```

用 runner 返回 state 后第二次 proposal:

```text
was_exposed_at_check_time = true
initial_support_repeats = 1
```

含义:

- 调用方必须使用最新 state。
- 否则重复次数不会自然下降。

## 6. 最终汇总报告

本轮纠偏已完成:

- 采纳 Claude 关于“多轮叙事美化”的核心意见。
- 采纳 Claude 关于 `_plan_outline` 诊断标签路由风险的意见。
- 采纳 Claude 关于 exposed state handoff 显式化的意见。
- 保留教师侧 trace 的价值，但不再夸大为学生侧差异化课程。

仍不能宣称:

- 已实现真正差异化多轮课程设计。
- selector 能决定每种失败应该如何教学。
- 完整主动课程规划系统完成。

下一步再进入 Phase6.6:

```text
RepeatedEvidenceCourseProposal
  -> CurriculumRunner
  -> validation diagnosis
  -> TeachingPlanContext
  -> next repeated-evidence proposal
```

继续保持:

- 学生侧只接收 AP-native evidence。
- 教师侧可以组织教学，但不能把答案表、关键词路由、学生侧 LLM 写入 runtime。
