# APV3.0test Phase5.2 Bn/Cn recall 与 attention focus 接入报告

日期: 2026-06-16

## 1. 设计

Phase5.2 的目标是把当前输入接入 AP-native recall 链路:

```text
当前输入 cue_tokens
  -> Bn recall: 当前场像以前哪个 ParadigmSA
  -> Cn successor: 沿显式 successor / paradigm observations 读取后继
  -> attention focus: 选择当前最有把握的范式
  -> MinimalDialogueRuntime: 逐 token 草稿行动与 commit
```

本阶段不引入:

- 关键词路由
- 答案表
- 正则分支
- 学生侧 LLM policy
- 特定技能名硬编码
- 整句宏动作

Bn/Cn/attention 是读数层, tick runtime 只负责调用它和执行低粒度行动。

## 2. 审查完善

### 2.1 Bn recall 不按技能类别分支

Bn 对所有暴露的 `ParadigmSA` 统一计算:

- cue token 序列相似度
- promoted learned vector context 相似度
- support
- conf
- `ParadigmSA.energy` 中的注意力读数

它不检查“这是问候/成语/数学/视觉”之类类别, 因此不构成技能路由。

### 2.2 Cn successor 不存答案表

Cn 读取两类 AP-native 后继证据:

1. `paradigm_observations`
   - 同一 bucket 下已提交 observation 的 reply token 后继。
2. `transitions`
   - 显式 successor edge。

当显式 successor 支持更高时, Cn 会把它作为更强后继来源; 否则使用范式观察中的后继。

### 2.3 attention focus 只选焦点, 不生成答案

attention focus 合成:

- Bn score
- Cn score
- ParadigmSA energy attention

它只选择当前最值得聚焦的范式, 不直接写草稿、不提交、不绕过 actuator competition。

### 2.4 教学等价

自然教学和 LLM 标准教学只允许 provenance/source 不同。Phase5.2 验证的是:

- 二者学到的 `ParadigmSA` 可被同一 recall 链路召回。
- 二者产生同一后继 token。
- 二者进入同一逐 token 草稿行动链。
- 不出现 `llm_policy`。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/paradigm_recall.py`
- `APV3.0test/tests/test_phase5_2_recall_attention_runtime.py`

修改文件:

- `APV3.0test/apv3test/config/paradigm_config.py`
- `APV3.0test/apv3test/runtime/incremental_tick_runtime.py`
- `APV3.0test/apv3test/runtime/__init__.py`

新增核心对象:

- `ParadigmRecallAttention`
- `BnParadigmCandidate`
- `CnSuccessorCandidate`
- `AttentionFocusCandidate`
- `ParadigmRecallResult`

Phase5.2 运行方式:

```text
IncrementalTickRuntime.run_tick(... emit_reply=True, reply_tokens=())
  -> ParadigmRecallAttention.recall()
  -> focus.cn.successor_tokens
  -> MinimalDialogueRuntime.run_turn()
```

也就是说, recall tick 不需要 teacher reply tokens。

## 4. 严谨验收测试

Phase5.2 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase5_2_recall_attention_runtime.py APV3.0test\tests\test_phase5_1_incremental_tick_runtime.py APV3.0test\tests\test_phase5_0_incremental_paradigm.py -q
```

结果:

```text
19 passed in 0.64s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
102 passed in 2.39s
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

- 教学后 recall tick 在不给 teacher reply tokens 的情况下输出已学后继。
- 多个技能共存时 attention focus 选择 cue/context 最匹配的 `ParadigmSA`。
- Cn 能读取显式 successor edge 作为后继支持来源。
- 未学范式不输出、不提交。
- 自然教学和 LLM 标准教学在 recall runtime 行为上等价。
- SQLite 保存恢复后仍可 recall 并输出。

## 5. 最终汇总

Phase5.2 已完成:

- 当前输入已经能通过 Bn recall 找到候选 `ParadigmSA`。
- Cn 已能沿 `paradigm_observations` 和显式 `transitions` 读取后继。
- attention focus 已能选择当前最相关范式。
- tick runtime 已能在没有 teacher reply tokens 的情况下, 召回已学范式并逐 token 回复。
- 自然教学与 LLM 标准教学在 recall 行为上通过最小等价 probe。

仍不能宣称:

- 完整 APV3.0 中文开放自由对话底座完成。
- 完整 Fresh300 或旧 GL 全技能复现完成。
- 注意力已经具备完整跨任务、跨模态、快慢系统竞争能力。
- Bn/Cn recall 已覆盖大规模长期记忆和复杂上下文。

下一步建议:

进入 Phase5.3: 扩展小批技能复现与失败归因。

最小目标:

1. 问候、成语、颜色对象、简单数学过程都用自然教学和 LLM 标准教学各训一遍。
2. 只给 cue, 不给 reply, 通过 Bn/Cn/attention 自动召回后继。
3. 检查多技能干扰时 attention 是否选择正确范式。
4. 如果失败, 只通过奖惩、support、promoted vector 和教学样本补习, 不新增关键词规则。
5. SQLite restore 后重复同样测试。
