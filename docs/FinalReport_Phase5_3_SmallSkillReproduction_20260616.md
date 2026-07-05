# APV3.0test Phase5.3 小批技能复现与失败归因报告

日期: 2026-06-16

## 1. 设计

Phase5.3 的目标是用 APV3.0test 当前新链路复现一小批旧 GL 成功技能, 并验证自然教学与 LLM 标准教学在运行行为上等价。

本阶段不复用旧 harness 方案, 而是按当前 APV3.0 流程重新设计教学:

```text
教学 observation
  -> commit / reward feedback
  -> IncrementalParadigmLearner
  -> ParadigmSA
  -> Bn/Cn recall
  -> attention focus
  -> 当前 focus token 填槽
  -> 逐 token 草稿行动
  -> commit
```

技能批次:

1. 问候: `你好 -> 我在`
   - 阶段: successor prediction
   - 复现方式: 只给 cue, 不给 reply, recall 后继。
2. 成语: `三顾 -> 茅庐`
   - 阶段: successor prediction
   - 复现方式: 只给 cue, 不给 reply, recall 后继。
3. 颜色对象: `field::color + percept slot + field::object + percept slot`
   - 阶段: multi-reply aggregation
   - 复现方式: 多样例形成槽位范式, recall tick 用当前 percept focus 填槽。
4. 简单数学过程:
   - 阶段: process-paradigm binding
   - 复现方式: 复现过程范式并用当前 focus token 填槽。
   - 边界: 不接计算器, 不宣称能计算任意新题; 当前结果 token 必须作为积木输入。

自然教学和 LLM 标准教学的差异只允许存在于:

- `source_kind`
- provenance

不允许存在于:

- runtime policy
- answer table
- keyword route
- hidden solver
- full-sentence macro

## 2. 审查完善

### 2.1 第一次测试暴露的问题

Phase5.3 初跑时出现两个失败:

1. 数学槽位被历史 relation 证据压过当前 focus 顺序。
   - 表现: 当前 focus 给出 `7, 2, 9`, 但第一个槽位被历史高关系 token `2` 占据。
   - 原因: 槽填充把当前 focus、历史 relation、successor virtual 叠加求分, 历史关系证据可能盖过工作记忆顺序。
2. 未训练 cue 仅凭 context 召回了问候范式。
   - 表现: `unknown` cue 在 `ctx_dialogue` 下仍召回 greeting。
   - 原因: Bn recall 没有最低 cue grasp 门, context 分足以产生焦点。

### 2.2 AP 风格修正

修正 1: 当前 focus token 优先作为工作记忆积木。

修改 `ParadigmSlotFiller._best_slot_candidate()`:

```text
如果候选已在当前 focus 中, 不再叠加 relation_score / successor_score。
```

含义:

- 历史关系证据负责提供范式结构。
- 当前 focus 负责填入当前槽位。
- successor virtual 只在当前 focus 缺失时补候选。

修正 2: Bn recall 需要 cue grasp。

修改 `ParadigmRecallAttention.bn_candidates()`:

```text
cue_score <= 0 时不生成 Bn candidate。
```

含义:

- context 可以调制召回强度, 但不能在 cue 完全无关时单独把范式拉出来。
- 这避免短期上下文噪声把无关技能拉进注意力焦点。

这两处都不是具体技能规则, 而是 APV3.0 的通用读数边界。

## 3. 通过落地

新增文件:

- `APV3.0test/tests/test_phase5_3_small_skill_reproduction.py`

修改文件:

- `APV3.0test/apv3test/runtime/incremental_tick_runtime.py`
  - recall tick 支持 `focus_tokens` / `candidate_pool`。
- `APV3.0test/apv3test/runtime/paradigm_fill.py`
  - 当前 focus token 不再叠加历史 relation/successor 加成。
- `APV3.0test/apv3test/runtime/paradigm_recall.py`
  - Bn candidate 需要 `cue_score > 0`。

Phase5.3 教学协议:

```text
successor_prediction:
  重复 cue -> reply observation, commit + reward, 形成后继范式。

multi_reply_aggregation:
  同一 cue 下多个 reply 变体, 形成固定锚 + slot 结构。

process_paradigm_binding:
  多个过程样例形成过程槽位结构, 当前 focus 提供填槽积木。

recall-only validation:
  验收时只给 cue / context / 当前 focus, 不给 teacher reply。
```

## 4. 严谨验收测试

Phase5.3 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase5_3_small_skill_reproduction.py APV3.0test\tests\test_phase5_2_recall_attention_runtime.py APV3.0test\tests\test_phase2_6_percept_slot_fill.py -q
```

结果:

```text
16 passed in 0.81s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
107 passed in 2.62s
```

禁用通道扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro|llm_policy|if vision|if text|黄色苹果" APV3.0test\apv3test
```

结果:

```text
APV3.0test\apv3test\runtime\draft_action.py:126:        if text:
```

审查: 这是草稿 commit 时的 buffer 非空检查, 不是文本模态特权分支。

残留硬地板/旧位置语法扫描:

```powershell
rg -n "max\([^\n]*0\.1|all_slot_confidence_floor|def _emission\(.*prev_role|def _emission\(.*index|last_index|variable_seen" APV3.0test\apv3test APV3.0test\tests
```

结果: 无命中。

测试覆盖:

- 自然教学复现问候、成语、颜色对象、简单数学过程。
- LLM 标准教学与自然教学的 recall 行为等价。
- attention 在多技能共存时按 cue/context 选择对应范式。
- SQLite restore 后仍能复现小批技能。
- 未训练 cue 不输出、不提交。
- 失败归因后没有新增关键词规则。

## 5. 最终汇总

Phase5.3 已完成:

- APV3.0test 已能用当前新教学协议复现一小批技能。
- recall-only 验收成立: 只给 cue, 不给 teacher reply, 可以通过 Bn/Cn/attention 召回已学后继。
- 颜色对象类槽位范式可以用当前 percept focus 填槽。
- 简单数学过程可以作为过程范式填槽复现, 但不宣称计算泛化。
- 自然教学与 LLM 标准教学在小批技能上通过行为等价 probe。
- 发现并修正了两个通用读数问题: focus 槽填充优先级、Bn cue grasp 门。

仍不能宣称:

- 完整 APV3.0 中文开放自由对话底座完成。
- Fresh300 通过。
- 任意数学计算能力完成。
- 完整跨模态自由泛化完成。
- 所有旧 GL 技能完成迁移。

下一步建议:

进入 Phase5.4: 将小批复现扩展为小型 curriculum runner。

最小目标:

1. 把 Phase5.3 手写教学样例整理为 APV3 标准教学 episode 格式。
2. 支持 echo imitation / successor prediction / multi-reply aggregation / process-paradigm binding / focus-slot filling / recall-only validation 六段记录。
3. 给每个技能输出失败归因:
   - Bn 未召回
   - Cn 后继弱
   - attention 选错
   - slot focus 被历史证据压过
   - commit/action outcome 未写入
4. 仍只允许通过奖惩、support、promoted vector 和教学样本补习。
