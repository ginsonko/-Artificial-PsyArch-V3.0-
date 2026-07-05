# APV3.0test Phase7.0 teacher-off 三阶里程碑验收报告

日期: 2026-06-16

## 1. 设计

Phase7.0 吸收 Claude 的战略纠偏: Phase6 连续多个子阶段都在主动求教和教师协议侧推进，虽然工程质量合格，但下一步不应继续精装修教师协议，而应回到 APV3.0 中文开放对话底座的底层问题:

```text
学生侧在 teacher-off 验证 tick 下，能不能纯靠已学 AP-native evidence 自答?
```

因此 Phase7.0 设计为三阶 teacher-off 里程碑验收:

1. echo imitation: 教 `你好 -> 你好`，验证 tick 只给 cue=`你好`，看能否自答 `你好`。
2. successor prediction: 教 `你好 -> 我在`，验证 tick 只给 cue=`你好`，看能否自答 `我在`。
3. multi-reply aggregation: 教 `三顾 -> 茅庐` 与 `三顾 -> 草庐之中`，验证 tick 只给 cue=`三顾`，观察 Cn 是否抽出共享后继，以及草稿行动的真实表现。

验证 tick 的硬门:

- `reply_tokens == ()`
- `focus_tokens == ()`
- `candidate_pool == ()`
- 不使用学生侧 LLM。
- 不使用答案表、关键词路由、regex、整句宏。

## 2. 审查完善

### 2.1 对 Claude 意见的吸收

吸收:

- Phase6 确实已经在教师协议侧连续推进太久。
- Phase7 应转向 teacher-off 学生侧能力验收。
- 不能再用“教师 evidence 接入顺畅”替代“学生能独立召回”。
- 如果 teacher-off 失败，应暴露底层问题，而不是加 fallback 或预填池。

校正:

- 当前项目并不是完全没有 teacher-off 测试。`test_phase5_2_recall_attention_runtime.py` 已经有无 `reply_tokens` 的 Bn/Cn recall、自答 successor、shared-tail 聚合测试。
- 但这些测试还不是正式的“三阶里程碑验收”，也没有把验证 tick 的空 `reply_tokens/focus_tokens/candidate_pool` 写成硬门。因此 Phase7.0 仍然必要。

### 2.2 临时探针发现

落地前用临时探针检查当前底座真实行为:

```text
echo       -> Cn = 你好, emitted = 你好
successor  -> Cn = 我在, emitted = 我在
multi      -> Cn = 庐, emitted = 庐庐庐庐
```

结论:

- echo 与 successor 的 teacher-off 自答链路成立。
- multi-reply 的 token-level Cn 能抽出共享 token `庐`。
- 但多义聚合进入草稿行动时，当前槽填充会把共享 token 重复填入多个槽，暴露“Cn 抽象成功，但生成行动层还不成熟”的边界。

这个边界必须诚实记录，不能包装成“已经会自然说成语”。

## 3. 通过落地

新增文件:

```text
APV3.0test/tests/test_phase7_0_teacher_off_three_stage_milestone.py
```

新增 3 个测试:

1. `test_phase7_0_teacher_off_echo_recall_no_prefilled_pool`
2. `test_phase7_0_teacher_off_successor_recall_no_prefilled_pool`
3. `test_phase7_0_teacher_off_multi_reply_exposes_shared_cn_boundary`

关键实现:

```python
assert recall.reply_tokens == ()
assert recall.focus_tokens == ()
assert recall.candidate_pool == ()
```

中文 token 使用 Unicode escape 写入，避免 PowerShell/终端编码污染。

## 4. 严谨验收测试

Phase7.0 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py -q
```

结果:

```text
3 passed in 0.64s
```

Recall 相关回归:

```powershell
python -m pytest APV3.0test\tests\test_phase5_2_recall_attention_runtime.py APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py -q
```

结果:

```text
10 passed in 1.01s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
176 passed in 3.81s
```

编译检查:

```powershell
python -m py_compile APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py
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
rg -n "most_common_reply|_observations_for_bucket|remediate:|if percept|if audio|if action|if text|if vision|if task|task_queue|answer_table|llm_policy|propose_multiround|MultiRoundTeacherCourseProposal|TeacherCourseRound|focus_tokens=\(LU|candidate_pool=.*LU|reply_tokens=\(LU" APV3.0test\apv3test APV3.0test\tests
```

结果:

- 命中均为测试反泄漏断言或 `draft_action.py` buffer 非空检查。
- 无旧 `most_common_reply` fallback。
- 无学生侧 `llm_policy` / `answer_table`。
- 无给 Phase7.0 验证 tick 预填 `LU` 的路径。

## 5. 成功/边界样例

### 5.1 echo teacher-off 自答

训练:

```text
cue = 你 好
reply = 你 好
repeat = 50
```

验证:

```text
cue = 你 好
reply_tokens = ()
focus_tokens = ()
candidate_pool = ()
```

结果:

```text
focused pid = p:discovered:phase7_echo
Cn successor = 你 好
emitted = 你 好
```

含义:

- echo 阶段 teacher-off 自答成立。

### 5.2 successor teacher-off 自答

训练:

```text
cue = 你 好
reply = 我 在
repeat = 50
```

验证:

```text
cue = 你 好
reply_tokens = ()
focus_tokens = ()
candidate_pool = ()
```

结果:

```text
focused pid = p:discovered:phase7_successor
Cn successor = 我 在
emitted = 我 在
```

含义:

- successor prediction teacher-off 自答成立。
- 当前 APV3.0test 不是只能在教师 tokens 在场时输出。

### 5.3 multi-reply teacher-off 边界

训练:

```text
三 顾 -> 茅 庐
repeat = 30

三 顾 -> 草 庐 之 中
repeat = 30
```

验证:

```text
cue = 三 顾
reply_tokens = ()
focus_tokens = ()
candidate_pool = ()
```

结果:

```text
focused pid = p:discovered:phase7_multi_reply
Cn successor = 庐
emitted = 庐 庐 庐 庐
```

含义:

- token-level Cn 的共享后继抽象成立。
- 但生成行动层尚未学会“共享后继只作为不确定收束/片段提示”，而是把共享 token 重复填进多个槽。
- 这不是完整 multi-reply 语言生成能力，只是暴露了一个关键中间能力与一个明确待修边界。

## 6. 最终汇总报告

Phase7.0 已完成:

- 从 Phase6 教师协议路线切回学生侧 teacher-off 核心能力验收。
- echo teacher-off 自答通过。
- successor teacher-off 自答通过。
- multi-reply teacher-off 的共享 Cn 抽象通过。
- multi-reply 的草稿行动生成边界被明确暴露: 当前会重复填充共享 token。
- 未引入答案表、关键词路由、学生侧 LLM、预填 focus/candidate pool 或旧 fallback。

可以宣称:

- APV3.0test 当前已经有最小 teacher-off echo/successor 自答能力。
- APV3.0test 当前能在多 reply 情况下抽出共享 token-level Cn。

仍不能宣称:

- 完整 multi-reply 聚合语言生成已经完成。
- 不确定时能自然表达“茅/草庐?” 或选择上下文最合适回复。
- 完整自由中文开放对话底座完成。
- Fresh300、任意中文开放对话或旧 GL 完整迁移完成。

下一步建议 Phase7.1:

```text
修复 multi-reply 生成边界:
  区分 Cn shared successor fragment 与 slot fill candidate
  防止同一个共享后继被机械填入多个槽
  输出策略应允许:
    - 只输出共享片段
    - 或输出带不确定性的片段
    - 或在上下文证据足够时选一条完整 reply
  严禁通过 case_name / 中文关键词 / answer table 解决
```

目标是让多义聚合从“Cn 抽象成立”推进到“行动层对不确定共享片段的处理更像人”。
