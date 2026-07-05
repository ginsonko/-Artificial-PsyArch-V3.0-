# APV3 Phase7.3d/e Reply Pressure + Expression Recall/Rebind 最终报告

日期: 2026-06-17
阶段: Phase7.3d + Phase7.3e
状态: 通过

## 1. 设计

Phase7.3d 落地从状态 SA 涌现的 reply_pressure,替代外部 `must_reply` 布尔开关。Phase7.3e 将 reply_pressure、draft-introspection feeling 和 CooccurrenceAssociationStore 串成最小 learned expression recall/rebind 路径。

本阶段严格保持:

- pressure 只决定“是否有回复压力”,不决定“说什么”。
- 表达选择来自 `(feeling_label, paradigm_id)` 共现关联,不来自 hardcoded label、关键词、case_name、答案表或 LLM policy。
- reply_pressure SA 本体不暴露 provenance/sources,贡献明细只进入 out-of-band trace。
- `must_reply`、`undecidable_feeling_tokens`、`feeling::undecidable` 已从 runtime 与 Phase7 测试中移除。

## 2. 审查完善

吸收 V3.1 的 7.3d/e 修正:

- B4:SilenceSA 采用 reset-on-commit + bounded ramp + saturation 后衰减。
- S6:取消开放式 `pressure_type_weights`;pressure 输入 SA 使用结构属性 `sa_kind`。
- S10:Phase7.2 测试迁移到 `incoming_external_query`,不再使用 `must_reply=True`。
- S11:reply pressure 贡献明细走 trace,SA 本体不带 provenance。
- 7.3e:表达召回通过 `CooccurrenceAssociationStore.nearest_paradigms_by_label()`,不绕 `find_by_cue_token`。

## 3. 通过落地

新增:

- `apv3test/runtime/reply_pressure.py`
- `tests/test_phase7_3d_reply_pressure_sa.py`
- `tests/test_phase7_3e_expression_recall_rebind.py`

更新:

- `apv3test/config/introspection_config.py`
- `apv3test/runtime/incremental_tick_runtime.py`
- `apv3test/runtime/cooccurrence_store.py`
- `tests/test_phase7_2_learned_uncertainty_expression.py`
- `apv3test/runtime/__init__.py`

核心行为:

- `incoming_external_query` 铸造 `external_query` pressure input SA。
- `recent_commit` 是瞬态负压,不会累积成负压堆。
- `silence` 随 last_commit_tick 生成,commit 后清零。
- runtime 在不能决 draft + reply_pressure 达阈值时,生成当前 draft introspection feeling。
- runtime 读取 cooccurrence association 的 candidate paradigm id,查找表达范式,用当前高把握 fragment 作为 focus 做 rebind。
- rebind 前清空未提交 draft buffer,避免“旧不能决片段 + 表达句式”机械拼接。

## 4. 严谨验收测试

已执行:

```text
python -m pytest APV3.0test\tests\test_phase7_2_learned_uncertainty_expression.py APV3.0test\tests\test_phase7_3d_reply_pressure_sa.py APV3.0test\tests\test_phase7_3e_expression_recall_rebind.py -q
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py APV3.0test\tests\test_phase7_1_undecidable_shared_fragment.py APV3.0test\tests\test_phase7_2_learned_uncertainty_expression.py APV3.0test\tests\test_phase7_3b_draft_introspection_observer.py APV3.0test\tests\test_phase7_3c_cooccurrence_association_store.py APV3.0test\tests\test_phase7_3d_reply_pressure_sa.py APV3.0test\tests\test_phase7_3e_expression_recall_rebind.py -q
python -m pytest APV3.0test\tests -q
rg -n "must_reply|undecidable_feeling_tokens|feeling::undecidable" APV3.0test\tests APV3.0test\apv3test\runtime
```

结果:

- Phase7.2 migrated + 7.3d + 7.3e target: `11 passed`
- Phase7.0-7.3e combined: `35 passed`
- Full suite: `208 passed`
- `must_reply / undecidable_feeling_tokens / feeling::undecidable` scan: no matches

广域 redline 扫描仍会命中已知无关项:

- `draft_action.py` 中 `if text` 是缓冲区非空检查。
- `paradigm_recall.py` 中 `source` 是 explicit transition source 字段。
- `teaching_protocol_selector.py` 中 `pressure_sources` 是教师侧 trace 字段,不属于学生侧 reply_pressure SA。

## 5. 成功样例

- 外部询问输入后,系统铸造 `external_query` SA,`reply_pressure` 高于阈值。
- `sa_type="external_query"` 但没有 `sa_kind` 的输入不会参与 pressure,证明没有开放策略表。
- external query pressure 随 tick 衰减。
- silence 在沉默时上升,饱和后衰减,commit 后 reset。
- learned expression 正例:不能决 draft + external query + learned feeling-expression association -> 输出 `expr::uncertain + 庐` 并 commit。
- 负例 A:没有 association 时,即使有 query pressure,仍只保留 `庐` 且不 commit。
- 负例 B:有 association 但无 reply_pressure 时,不强行表达。

## 6. 最终汇总

Phase7.3b/c/d/e 已经形成最小闭环:

`draft structure -> introspection feeling -> cooccurrence association -> reply pressure -> expression paradigm recall/rebind`

现在可以把这套结果交给 Claude 做端到端审阅,重点检查:

- 内省 feeling 是否仍只来自结构事实。
- association 是否仍是 AP-native evidence 而非答案表。
- reply_pressure 是否只管压力不管表达内容。
- learned expression rebind 是否存在隐藏 cue/label/case_name 路由。
- 当前端到端样例是否足以证明最小 learned uncertainty expression,以及还缺哪些泛化验收。

仍不能宣称:

- 完整自由中文开放对话底座已完成。
- 所有疑惑/心虚/流畅等内省 feeling 都已泛化。
- 跨模态 adapter 已验收。
- 真实长期自然对话语料中的表达学习已完成。

下一步建议 Phase7.3f:做 property-based label-bijection、不变量红线和端到端 replay 黑盒回归,作为交 Claude 审阅前的最终锁门。

