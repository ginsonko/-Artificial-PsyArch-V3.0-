# APV3.0test Phase7.1 不能决共享片段生成边界修复报告

日期: 2026-06-16

## 1. 设计

Phase7.0 暴露了一个关键边界:

```text
三顾 -> 茅庐
三顾 -> 草庐之中

teacher-off cue = 三顾
Cn successor = 庐
old emitted = 庐 庐 庐 庐
```

这说明 token-level Cn 已经能抽出共享后继 `庐`，但生成行动层把它当成普通槽候选，机械填进多个未解决槽。

Phase7.1 的设计目标不是让系统“天然知道完整成语”，而是引入最小拟人式“不能决”范式:

```text
当系统只能收束出共享片段，但不能决定缺失槽内容时:
  共享片段可以进入草稿/想法
  不能被当成普通槽候选重复填槽
  不能自动 commit 成确定回答
```

这对应人类心理图景:

- 人想起了一个关键片段，如“庐”。
- 但无法确定是“茅庐”还是“草庐之中”。
- 这个片段可以浮现为想法或草稿。
- 但不应该自信地把它当成完整答案发出去。

## 2. 审查完善

### 2.1 AP-native 路线

本阶段禁止:

- 按 `case_name` 分支。
- 按中文关键词分支。
- 使用答案表。
- 使用 regex 或 full sentence macro。
- 使用学生侧 LLM。

采用的机制:

1. `ParadigmSlotFiller` 记录未解决槽数量。
2. 如果前面存在未解决槽，后续锚点/共享片段会带上:

```text
anchor_meta.undecidable_fragment = true
source += "+undecidable_fragment"
```

3. `MinimalDialogueRuntime` 允许该片段进入草稿行动竞争。
4. 但如果草稿中存在 `undecidable_fragment`，即使 `commit_after_draft=True`，也不自动 commit。
5. `IncrementalTickRuntime` 在 teacher-off recall 时不再把 Cn successor 自动伪装成 `focus_tokens/candidate_pool`，避免共享片段被当成槽候选反复使用。

### 2.2 为什么不是直接禁用 shared Cn

不能决并不等于“什么都不想”。共享片段是有证据的 Cn 结果，应该进入状态/草稿/注意力链路。问题只在于它的确定性不足，不能作为完整回复提交。

因此本阶段保留:

```text
emitted = 庐
```

但阻止:

```text
emitted = 庐 庐 庐 庐
committed_text = 庐
```

### 2.3 已决定 successor 不受影响

为了防止过度谨慎，新增保护测试:

```text
你好 -> 我在
teacher-off cue = 你好
emitted = 我 在
committed_text = 我在
```

即: 只有不能决片段不自动提交；已决定回复仍可提交。

## 3. 通过落地

修改文件:

```text
APV3.0test/apv3test/runtime/paradigm_fill.py
APV3.0test/apv3test/runtime/dialogue_runtime.py
APV3.0test/apv3test/runtime/incremental_tick_runtime.py
```

新增文件:

```text
APV3.0test/tests/test_phase7_1_undecidable_shared_fragment.py
```

关键变化:

```text
ParadigmSlotFiller:
  unresolved_slots += 1 when a slot has no candidate
  anchor/shared fragments after unresolved slots are marked undecidable

MinimalDialogueRuntime:
  if any draft has undecidable_fragment:
    do not auto-commit

IncrementalTickRuntime:
  teacher-off Cn successor is no longer inserted into focus/candidate_pool as a slot candidate
```

## 4. 严谨验收测试

Phase7.1 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase7_1_undecidable_shared_fragment.py -q
```

结果:

```text
2 passed in 0.66s
```

Phase7/Recall/Slot-fill 组合测试:

```powershell
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py APV3.0test\tests\test_phase7_1_undecidable_shared_fragment.py APV3.0test\tests\test_phase5_2_recall_attention_runtime.py APV3.0test\tests\test_phase2_6_percept_slot_fill.py -q
```

结果:

```text
17 passed in 1.27s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
178 passed in 4.12s
```

编译检查:

```powershell
python -m py_compile APV3.0test\apv3test\runtime\paradigm_fill.py APV3.0test\apv3test\runtime\dialogue_runtime.py APV3.0test\apv3test\runtime\incremental_tick_runtime.py APV3.0test\tests\test_phase7_1_undecidable_shared_fragment.py
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
rg -n "most_common_reply|_observations_for_bucket|remediate:|if percept|if audio|if action|if text|if vision|if task|task_queue|answer_table|llm_policy|propose_multiround|MultiRoundTeacherCourseProposal|TeacherCourseRound|case_name.*phase7|三顾|茅庐|草庐" APV3.0test\apv3test APV3.0test\tests\test_phase7_1_undecidable_shared_fragment.py
```

结果:

- `case_name` 只命中测试训练样例。
- runtime 无 case_name 分支。
- 无中文关键词规则。
- 无答案表/学生侧 LLM/旧 fallback。

## 5. 成功/边界样例

### 5.1 不能决共享片段

训练:

```text
三 顾 -> 茅 庐
repeat = 30

三 顾 -> 草 庐 之 中
repeat = 30
```

teacher-off 验证:

```text
cue = 三 顾
reply_tokens = ()
focus_tokens = ()
candidate_pool = ()
```

结果:

```text
Cn successor = 庐
emitted = 庐
committed_text = ""
draft.anchor_meta.undecidable_fragment = true
draft.anchor_meta.source includes undecidable_fragment
```

含义:

- 系统不是完全空白，而是能想到共享片段。
- 但它知道当前片段不足以作为确定回答提交。
- 重复填槽问题已修复。

### 5.2 已决定 successor 仍可提交

训练:

```text
你 好 -> 我 在
repeat = 50
```

teacher-off 验证:

```text
cue = 你 好
reply_tokens = ()
focus_tokens = ()
candidate_pool = ()
```

结果:

```text
emitted = 我 在
committed_text = 我在
all drafts undecidable_fragment = false
```

含义:

- 不能决门不会让系统变成“什么都不敢提交”。
- 证据收束充分时仍可正常输出和提交。

## 6. 最终汇总报告

Phase7.1 已完成:

- 修复 multi-reply 共享 Cn 被机械填入多个槽的问题。
- 建立最小 “不能决共享片段” 语义。
- teacher-off 多义场景下，共享片段可进入草稿/想法，但不自动提交成确定回复。
- 已决定 successor 自答和提交不受影响。
- 感知槽填充、Phase5.2 recall、Phase7.0 三阶里程碑、全量测试均保持通过。
- 未引入 case_name 路由、中文关键词规则、答案表、regex、full-sentence macro 或学生侧 LLM。

可以宣称:

- APV3.0test 当前具备最小“不能决片段”处理能力。
- 多义聚合从 `庐庐庐庐` 改进为 `庐` 进入草稿但不提交。
- teacher-off echo/successor 自答仍成立。

仍不能宣称:

- 系统能自然说出“茅庐还是草庐之中?”。
- 系统能主动发起澄清问题。
- 系统能根据更丰富上下文选择完整 reply。
- 完整自由中文开放对话底座完成。

下一步建议 Phase7.2:

```text
把不能决片段升级为主动澄清/求教触发:
  undecidable_fragment + cognitive_pressure
  -> teacher_request or clarification_intent SA
  -> 不确定问题范式
  -> 外部教师/上下文补充后再收束
```

目标是让“不能决”不仅停在不提交，还能进入拟人式应对流程: 犹豫、回读、求澄清、请求教学。
