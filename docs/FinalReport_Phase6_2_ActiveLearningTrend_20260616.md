# APV3.0test Phase6.2 主动学习长期趋势探针报告

日期: 2026-06-16

## 1. 设计

Phase6.2 的目标不是新增一条求教策略，而是验证 Phase6.0/6.1 已有机制是否能呈现符合 AP 哲学的长期趋势:

```text
反复失败
  -> failure_count 上升
  -> teacher_request SA 能量上升或维持在上限
  -> 触发求教

AP-native 教师补习后成功召回
  -> 目标 ParadigmSA 暴露
  -> 成功观察让失败 trace 回落
  -> 后续求教下降或被 mastered_expected_pid 抑制

冷启动补习
  -> 证据不足
  -> remediation_intensity 高

已暴露范式补习
  -> 只需少量补充证据
  -> remediation_intensity 下降
```

边界:

- 不新增答案表。
- 不新增关键词路由。
- 不让学生侧调用 LLM。
- 不用固定 suppress 规则伪造“越学会越少求教”。
- LLM 标准教师只能提供 AP-native teaching episode，学生运行态只看到同构证据。

## 2. 审查完善

### 2.1 趋势必须来自 AP-native 证据

本阶段只读取已有字段:

- `active_learning_failures.failure_count`
- `teacher_request` 的状态池 SA 能量
- `paradigms[].exposed`
- `CurriculumRemediationSuggestion.evidence_repeats`
- `CurriculumRemediationSuggestion.remediation_intensity`

这些字段分别对应失败痕迹、状态池压力、范式是否学会、补习证据强度。它们都来自 AP-native tick/commit/feedback 流程。

### 2.2 首次验收失败与修复

首次运行 Phase6.2 目标测试时出现失败:

```text
expected recovered_once.failure_count == 1
actual   recovered_once.failure_count == 0
```

根因:

```text
APV3ActiveTeacherRequestRuntime.observe()
  使用 dict(state) 做浅拷贝
  -> 下一次 observe 会改写上一次结果中的嵌套 active_learning_failures
  -> 长期趋势探针看到的历史结果被后续 tick 污染
```

修复:

```text
observe() 改为 deepcopy(dict(state))
```

含义:

- 这是状态隔离修复，不改变求教策略。
- 每个 tick/result 的失败痕迹都能独立审计。
- 避免长期趋势被后续状态回写污染。

## 3. 通过落地

新增文件:

```text
APV3.0test/tests/test_phase6_2_active_learning_trend.py
```

修改文件:

```text
APV3.0test/apv3test/runtime/active_teacher_request.py
```

核心测试覆盖:

1. 反复失败让 failure_count 上升，并让 teacher_request 状态池能量达到上限。
2. 成功观察让 failure_count 从 2 -> 1 -> 0 回落，不靠硬 suppress。
3. LLM 标准教师响应经过 CurriculumRemediationLoop 后，目标范式暴露，后续 mastered 请求下降。
4. 冷启动补习强度为 1.0，已暴露范式补习强度下降到 0.5。

文件规模:

```text
test_phase6_2_active_learning_trend.py: 145 lines
active_teacher_request.py: 219 lines
```

## 4. 严谨验收测试

Phase6.2 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_2_active_learning_trend.py -q
```

结果:

```text
4 passed in 0.31s
```

Phase6.0-6.2 组合测试:

```powershell
python -m pytest APV3.0test\tests\test_phase6_0_active_teacher_request.py APV3.0test\tests\test_phase6_1_active_learning_bridge.py APV3.0test\tests\test_phase6_2_active_learning_trend.py -q
```

结果:

```text
13 passed in 0.37s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
146 passed in 3.37s
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
- 没有 runtime 侧答案表、学生侧 LLM、整句宏、模态特权分支。

## 5. 成功/失败样例

### 5.1 反复失败后求教上升

输入:

```text
cue = goal::ask
context = ctx_work
failed ticks = 1, 20, 40
```

结果:

```text
failure_count = 3
teacher_request generated
state_field_items.teacher_request.energy.P = 1.0
state_field_items.teacher_request.energy.A = 1.0
```

含义:

- 失败痕迹推动求教压力上升。
- 能量达到上限后不无限累加。

### 5.2 成功观察后求教下降

过程:

```text
失败两次: failure_count = 2
成功一次: failure_count = 1
再成功一次: failure_count = 0
```

结果:

```text
request = None
suppressed_reason = below_request_threshold
```

含义:

- 不是硬压请求。
- 是成功经验让失败 trace 自然回落。

### 5.3 教师补习后 mastered 抑制

过程:

```text
teacher_request generated
llm_standard_teacher supplies CurriculumRemediationLoop episode
goal::ask -> teacher::answer learned as AP-native evidence
```

结果:

```text
validation success = True
after_mastery.request = None
after_mastery.suppressed_reason = mastered_expected_pid
state has no llm_policy
state has no answer_table
```

含义:

- LLM 教师可以加速教学。
- 但学生侧没有 LLM policy，也没有特殊答案表。
- 学会后请求下降来自范式暴露，而不是外部路由。

### 5.4 补习强度动态

冷启动:

```text
evidence_repeats = 2
remediation_intensity = 1.0
```

已暴露范式:

```text
evidence_repeats = 1
remediation_intensity = 0.5
```

含义:

- 不熟时需要更多教学证据。
- 已学会时只需少量补强。

### 5.5 失败样例: 浅拷贝污染趋势

首次测试失败说明:

```text
recovered_once 本应记录第一次成功后的 failure_count = 1
但后续 recovered_twice 又修改了同一个嵌套 dict
导致 recovered_once 被回写为 0
```

修复后:

```text
每次 observe 产生独立 next_state
历史结果不再被后续 tick 污染
```

## 6. 最终汇总报告

Phase6.2 已完成:

- 主动求教请求在反复失败下会上升。
- 成功观察会让失败痕迹下降。
- 教师补习后，目标范式暴露会抑制后续无意义求教。
- 补习强度会随掌握程度从强补习降为弱补习。
- LLM 标准教师路径仍然只是 AP-native evidence 加速器。
- 修复了长期趋势探针发现的浅拷贝历史污染问题。

仍不能宣称:

- 完整主动课程规划已经完成。
- AP 可以自主选择最合适的人类/LLM 教师。
- 长时间遗忘后再学习的全周期策略已经完成。
- 自由中文开放对话底座已经完成。

下一步建议 Phase6.3:

```text
主动学习请求接入标准教学协议选择器:
teacher_request SA -> teacher episode proposal -> AP-native teaching episode -> validation
```

重点:

- 教师仍然在系统外。
- 学生侧只接收 AP-native evidence。
- 请求内容应包含 cue/context/失败诊断/压力来源，而不是直接要求答案表。
