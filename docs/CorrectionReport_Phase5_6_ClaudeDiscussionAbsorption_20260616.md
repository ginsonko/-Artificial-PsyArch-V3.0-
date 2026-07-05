# APV3.0test Phase5.6 后 Claude 讨论吸收与理论核对报告

日期: 2026-06-16

## 1. 设计

本轮目标是在进入 Phase5.7 前，再次核对 Phase5.5/5.6 是否偏离 APV3.0 的学习哲学。

本轮形成的关键边界:

- 教师可以存在，且婴儿期重复教学是合法学习方式。
- LLM 标准教师可以作为加速器，但学生侧必须只看到 AP-native evidence。
- 重复教学不等于答案表，前提是它经过 commit / reward / support / ParadigmSA / Bn/Cn / attention / draft action 全链路。
- runtime 召回期不能用整句 fallback 偷懒。教学期可重复，推理期不能回退到字面回放。
- 补习强度应具有动力学: 冷启动可以强，已学会的同类范式应降低补习强度。

## 2. 审查完善

### 2.1 对 Claude 第一判断的修正

Claude 最初认为补习器把 `expected_tokens` 重复 `min_support` 次就是答案重灌。这个判断过严。

修正理解:

```text
答案表硬编码:
if input == "你好": return "我在"

合法重复教学:
teacher observation -> commit/reward -> support 累加 -> ParadigmSA -> Bn/Cn recall -> draft action
```

人类婴幼儿的早期学习也依赖重复模仿。APV3 的六阶段里 `echo_imitation` 本身就允许教师反复给同一模式。

因此本轮没有删除冷启动重复教学。

### 2.2 吸收: 补习需要动力学

虽然重复教学合法，但“补习强度恒定”确实不够拟人。教师干预应随能力增长自然减弱。

落地:

- `CurriculumRemediationSuggestion` 新增 `evidence_repeats`。
- `CurriculumRemediationSuggestion` 新增 `remediation_intensity`。
- 冷启动 / 未暴露范式: 补到 `min_support`。
- 已存在且 exposed 的同类范式: 只补 1 次。

这对应:

```text
婴儿期: 教师重复强
已会阶段: 教师提示弱
```

### 2.3 吸收: Cn runtime fallback 必须删除

Claude 对 Cn fallback 的判断成立。

原问题:

```text
token-level successor 失败
-> fallback 到 most_common_reply
```

这是 runtime 推理期的整句回放后门，和教学期重复不同。

落地:

- 删除 `paradigm_recall.py` 中 `_most_common_reply` fallback。
- `_token_level_successor_from_columns()` 失败时，Cn 返回空。
- 冷启动或列统计不足会显式暴露为 recall 失败，而不是悄悄走整句回放。

### 2.4 吸收: stage 不拼诊断标签

`stage = f"remediate:{failure_kind}"` 虽然目前只是 trace，但容易给未来按 stage 字符串分支留口子。

落地:

- stage 固定为 `remediate`。
- 诊断类型只保留在 `failure_kind` / `diagnosis` 字段里。

## 3. 通过落地

修改文件:

- `APV3.0test/apv3test/runtime/curriculum_remediation.py`
- `APV3.0test/apv3test/runtime/paradigm_recall.py`
- `APV3.0test/tests/test_phase5_5_remediation_loop.py`

关键变化:

```text
curriculum_remediation.py:
  evidence_repeats
  remediation_intensity
  _remediation_repeats()
  _expected_paradigm_is_exposed()
  stage = "remediate"

paradigm_recall.py:
  Cn 只接受 token-level successor 或 explicit transition
  删除 most_common_reply fallback
```

## 4. 严谨验收测试

目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase5_5_remediation_loop.py APV3.0test\tests\test_phase5_6_conflict_reward_punish.py APV3.0test\tests\test_phase5_2_recall_attention_runtime.py -q
```

结果:

```text
15 passed in 0.49s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
121 passed in 2.94s
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

旧后门 / 旧硬地板 / 旧位置先验扫描:

```powershell
rg -n "most_common_reply|_observations_for_bucket|remediate:|max\([^\n]*0\.1|all_slot_confidence_floor|def _emission\(.*prev_role|def _emission\(.*index|last_index|variable_seen|CURRICULUM_STAGES|_validate_stage" APV3.0test\apv3test APV3.0test\tests
```

结果: 无命中。

## 5. 成功样例

### 5.1 冷启动补习仍可重复

```text
initial:
cue = 你 好
diagnosis = bn_not_recalled

remediation:
stage = remediate
failure_kind = bn_not_recalled
evidence_repeats = 2
remediation_intensity = 1.0

final:
emitted = 我 在
diagnosis = success
```

含义:

- 婴儿期重复教学保留。
- 不是答案表，因为仍走 AP 学习链路。

### 5.2 已暴露范式降低补习强度

```text
state 中已有:
p:discovered:skill_greeting exposed = true

remediation:
evidence_repeats = 1
remediation_intensity = 0.5
```

含义:

- 教师干预开始具备“熟练后减弱”的动力学雏形。

### 5.3 Cn 不再整句 fallback

```text
token-level successor 存在 -> 正常召回
token-level successor 不存在 -> Cn 为空
```

含义:

- runtime 不再用 most_common_reply 回放整句。
- 召回失败会显性暴露，后续应通过教学/统计补足。

## 6. 最终汇总报告

本轮理论核对结论:

- Claude 修正版是合理的: 教师重复教学不应被误判为答案表。
- 用户的补充更符合 AP 拟人哲学: 教师是早期加速器和可减弱偏向，不是禁忌。
- 但 runtime 召回期整句 fallback 确实是后门，已删除。
- 补习强度已开始记录并随范式是否已暴露而调整。
- stage 诊断标签已拆开，降低未来被解析成路由的风险。

仍不能宣称:

- 完整主动学习 / 主动召唤教师已经完成。
- 补习强度已经具备完整发展动力学。
- 完整自由中文开放对话底座已经完成。

进入 Phase5.7 前的新标准:

```text
教师可重复教，但必须走 AP-native evidence。
runtime 不做整句回放后门。
补习强度要可观察、可衰减。
未来 Phase6+ 要设计“系统主动召唤教师”，让教师从外部控制器变成可被需要时调用的资源。
```
