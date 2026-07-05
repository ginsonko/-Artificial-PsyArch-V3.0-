# APV3.0test Phase5.4 后理论纠偏吸收报告

日期: 2026-06-16

## 1. 设计

本轮发生在 Phase5.5 补习闭环之前，目标不是继续堆新能力，而是先审查 Phase5.0-5.4 是否悄悄产生了新的脚手架。

审查基准仍然是 APV3.0test 的主目标:

- 实时学习必须写入 AP-native evidence，而不是写答案表。
- 自然教学和 LLM 标准教学可以有不同教师来源，但学生侧证据结构必须等价。
- 范式阶段是能力连续谱上的表现，不应变成 runtime 硬枚举。
- Cn 应尽量来自 token-level / column-level 后继统计，不应退化为整句 reply 回放。
- recall-only 验证不能预填答案候选池。
- 当前外界输入、感知 token、题目 token 可以作为合法 focus SA 进入工作记忆，因为它们是“积木”，不是答案脚手架。

## 2. 审查完善

### 2.1 吸收: 课程阶段不能是人工 schema

Claude 指出 `CURRICULUM_STAGES` 和 `_validate_stage()` 会把六段学习过程硬塞成教师 schema。这个判断成立。

修正:

- `CURRICULUM_STAGES` 改为 `CURRICULUM_TRACE_LABELS`。
- 删除 `_validate_stage()` 的硬校验。
- `stage_counts` 改成动态记录。
- 未知教师标签例如 `teacher_custom_trace` 允许记录，但不参与 runtime 决策。

边界:

- 六段教学仍可作为教师侧 trace 和报告结构。
- runtime 不读取 stage 标签决定答案、召回、范式角色或补习路径。

### 2.2 吸收: recall-only 不能有答案候选池

Claude 指出 `candidate_pool` 在 curriculum validation 中会留下作弊门。这个判断成立。

修正:

- `CurriculumValidationCase` 移除 `candidate_pool` 字段。
- runner 在验证 tick 中固定传入 `candidate_pool=()`。

### 2.3 部分反驳: focus_tokens 不能一律为空

Claude 建议 recall-only 强制 `focus_tokens=()`。这一点需要区分:

- 如果 focus 是教师预填答案候选，那确实不允许。
- 如果 focus 是当前感受器输入或题目输入，例如 `percept::yellow percept::apple`、`7 2 9`，它是 AP 当前状态池里的合法外源 SA。

因此本轮采用折中但更符合 AP 的边界:

- `allow_current_focus=False` 为默认值。
- 只有验证用例显式声明 `allow_current_focus=True` 时，当前输入才可进入 focus。
- 即使允许 focus，`candidate_pool` 仍然为空。

这保证颜色/数学槽填充不是凭空生成词，而是用当前输入的 SA 当积木填槽。

### 2.4 吸收: Cn 不能只是整句 reply 回放

Claude 指出 `ParadigmSA.successor_tokens` 容易变成整句回放。这个风险成立。

修正:

- `ParadigmRecallAttention.cn_candidate()` 优先读取 `paradigm_stats[bucket]["columns"]`。
- Cn successor 由 `fixed_anchor` / `shared_fragment` column 的 `anchor_label` 聚合得到。
- slot column 不作为固定后继，留给当前 focus 填充。
- 只有 column-level token 不可用时，才 fallback 到观察中的常见 reply。

新增反伪科学测试:

```text
教 5 条同 cue、不同头部、共享尾 token 的 reply:
stem -> a shared_tail
stem -> b shared_tail
stem -> c shared_tail
stem -> d shared_tail
stem -> e shared_tail

验证:
cue = stem
focus = z
Cn = shared_tail
emitted = z shared_tail
且不能等于任何一条原始整句 reply
```

这证明当前 Cn 至少已从“整句回放”推进到“column-level 共享后继”。

### 2.5 吸收: 预防 incremental_paradigm god-object

Claude 指出 `incremental_paradigm.py` 已有 god-object 苗头。这个判断成立。

修正:

- `paradigm_types.py`: 保存 `IncrementalParadigmObservation` / `IncrementalParadigmUpdate`。
- `paradigm_stats.py`: 保存 `RoleTransitionStats`、promoted context similarity、证据衰减。
- `paradigm_store.py`: 保存 observation append、dirty bucket、ParadigmSA 入池、state field item 写入。
- `incremental_paradigm.py`: 只保留 `IncrementalParadigmLearner` 在线 ingest 编排。

拆分后行数:

```text
incremental_paradigm.py: 111
paradigm_stats.py: 205
paradigm_store.py: 244
paradigm_types.py: 31
```

## 3. 通过落地

本轮修改文件:

- `APV3.0test/apv3test/runtime/curriculum.py`
- `APV3.0test/apv3test/runtime/__init__.py`
- `APV3.0test/apv3test/runtime/paradigm_recall.py`
- `APV3.0test/apv3test/runtime/incremental_paradigm.py`
- `APV3.0test/apv3test/runtime/paradigm_types.py`
- `APV3.0test/apv3test/runtime/paradigm_stats.py`
- `APV3.0test/apv3test/runtime/paradigm_store.py`
- `APV3.0test/tests/test_phase5_4_curriculum_runner.py`
- `APV3.0test/tests/test_phase5_2_recall_attention_runtime.py`

## 4. 严谨验收测试

目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase5_4_curriculum_runner.py APV3.0test\tests\test_phase5_2_recall_attention_runtime.py APV3.0test\tests\test_phase5_3_small_skill_reproduction.py -q
```

结果:

```text
17 passed in 0.93s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
113 passed in 2.81s
```

红线扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro|llm_policy|if vision|if text|黄色苹果" APV3.0test\apv3test
```

结果:

```text
APV3.0test\apv3test\runtime\draft_action.py:126:        if text:
```

审查: 这是草稿 buffer 非空检查，不是文本模态特权分支。

旧硬地板 / 旧角色位置先验 / 旧课程硬枚举扫描:

```powershell
rg -n "max\([^\n]*0\.1|all_slot_confidence_floor|def _emission\(.*prev_role|def _emission\(.*index|last_index|variable_seen|CURRICULUM_STAGES|_validate_stage" APV3.0test\apv3test APV3.0test\tests
```

结果: 无命中。

## 5. 成功与失败样例

成功样例:

```text
问候:
cue = 你 好
emitted = 我 在
diagnosis = success

成语:
cue = 三 顾
emitted = 茅 庐
diagnosis = success

颜色对象:
cue = describe
focus = percept::yellow percept::apple
candidate_pool = <empty>
emitted = field::color percept::yellow field::object percept::apple
diagnosis = success

简单数学过程:
cue = calc
focus = 7 2 9
candidate_pool = <empty>
emitted = math::lhs 7 math::op + 2 math::eq 9
diagnosis = success

共享后继反伪科学:
cue = stem
focus = z
Cn = shared_tail
emitted = z shared_tail
不是任何一条原始教学 reply
```

失败样例:

```text
未训练 cue:
cue = unknown
emitted = <empty>
diagnosis = bn_not_recalled

槽焦点和期望不一致:
cue = describe
focus = percept::yellow percept::apple
expected = field::color percept::yellow field::object percept::pear
emitted = field::color percept::yellow field::object percept::apple
diagnosis = slot_focus_overridden
```

这些失败没有用关键词规则修复，只作为 Phase5.5 的 AP-native 补习入口。

## 6. 最终汇总报告

本轮纠偏后，Phase5.4 的边界更干净:

- 课程阶段退回教师侧 trace，不再是 runtime schema。
- recall-only 的答案候选池关闭。
- 当前外源 focus 作为合法 SA 保留，但必须显式声明。
- Cn 已有 column-level 共享后继验证，不再只靠整句 reply 回放。
- `incremental_paradigm.py` 已拆分，降低后续补习闭环产生 god-object 的风险。

仍不能宣称:

- 完整中文开放自由对话底座完成。
- 任意跨模态自发范畴发现完成。
- 任意数学计算能力完成。
- Fresh300 或旧 GL 全技能迁移完成。

下一步进入 Phase5.5:

```text
train -> validate -> diagnose -> remediate -> validate
```

失败后只生成 AP-native 补习建议，例如补 successor observation、补区分性 context、补 reward/punishment、补 promoted vector，不新增关键词规则、答案表或硬编码抑制。
