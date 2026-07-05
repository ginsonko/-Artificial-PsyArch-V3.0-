# APV3 Phase7.3f Invariants + Black-box Replay 最终报告
日期: 2026-06-17
阶段: Phase7.3f
状态: 通过

## 1. 设计

Phase7.3f 不新增能力模块,而是作为 Phase7.3b/c/d/e 交给外部审阅前的锁门验收。

本阶段验证四个核心不变量:

- 内部 introspection feeling label 必须行为不透明: 换一套 label minter 后,只要存在双射,外部输出和运行行为应保持一致。
- reply pressure 只表示"是否有回复压力",不携带表达内容、不携带 provenance/sources/dominant_source 进入 SA 本体。
- learned uncertainty expression 必须来自 `(feeling_label, paradigm_id)` AP-native 共现证据,不是 `case_name`、中文关键词、答案表、cue token 反查或 LLM policy。
- 至少一条端到端黑盒 replay 必须证明: 先失败并保留不能决内省 feeling,随后观察外部表达形成共现,下次相似条件下通过同一关联召回表达范式。

## 2. 审查完善

审查 7.3d/e 路径时发现一个拟人一致性小缺口:

- 旧行为: 有回复压力 + 不能决草稿 + 尚无 learned expression association 时,runtime 临时生成 introspection feeling,但找不到表达范式后返回原始草稿结果,导致 observed_state 丢失。
- 问题: 这会让系统无法像人一样把"我当时的不能决感受"和随后旁人说出的疑惑表达形成共现。
- 修正: `_run_learned_expression_reply()` 在无 association 时仍返回同一草稿结果,但 state 携带这次 observer-only introspection feeling; 不改变 emitted token 和 commit 行为。

这不是让系统更会答题的捷径,只是保留内部感受证据,让后续 AP-native 共现学习有对象。

## 3. 通过落地

更新:

- `apv3test/runtime/incremental_tick_runtime.py`
  - 无 learned expression association 时保留 observed introspection state。
- `tests/test_phase7_3f_invariants_replay.py`
  - 新增 black-box replay。
  - 新增 3 组 label-bijection 行为不透明测试。
  - 新增 runtime redline/AST 扫描。
  - 新增 extract_facts/rebind 内容隔离 AST 检查。

关键样例:

- 成功样例: `三 顾` 多回复训练后 teacher-off 只召回共享片段 `庐`,因不能决不提交; 外部教师/旁人表达 `expr::uncertain` 与当下 introspection feeling 共现; 下一次相似 query 下输出 `expr::uncertain + 庐` 并提交。
- 负例边界: 第一次无 association 时仍只产生 `庐` 且不 commit; 不会凭压力或 hardcoded feeling 自动生成疑惑表达。
- 标签不透明样例: `opaqueA::0`、`opaqueB::0`、`draft-affect/0` 等不同内部 label 字面经双射归一后行为一致。

## 4. 严谨验收测试

已执行:

```text
python -m pytest APV3.0test\tests\test_phase7_3f_invariants_replay.py -q
python -m pytest APV3.0test\tests\test_phase7_2_learned_uncertainty_expression.py APV3.0test\tests\test_phase7_3b_draft_introspection_observer.py APV3.0test\tests\test_phase7_3c_cooccurrence_association_store.py APV3.0test\tests\test_phase7_3d_reply_pressure_sa.py APV3.0test\tests\test_phase7_3e_expression_recall_rebind.py APV3.0test\tests\test_phase7_3f_invariants_replay.py -q
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py APV3.0test\tests\test_phase7_1_undecidable_shared_fragment.py APV3.0test\tests\test_phase7_2_learned_uncertainty_expression.py APV3.0test\tests\test_phase7_3b_draft_introspection_observer.py APV3.0test\tests\test_phase7_3c_cooccurrence_association_store.py APV3.0test\tests\test_phase7_3d_reply_pressure_sa.py APV3.0test\tests\test_phase7_3e_expression_recall_rebind.py APV3.0test\tests\test_phase7_3f_invariants_replay.py -q
python -m pytest APV3.0test\tests -q
python -m compileall APV3.0test\apv3test APV3.0test\tests -q
rg -n "must_reply|undecidable_feeling_tokens|feeling::undecidable|find_by_cue_token|_most_common_reply|pressure_type_weights|student_side_llm|answer_table|regex|LLM policy|proto_0|proto_1" APV3.0test\apv3test\runtime
```

结果:

- Phase7.3f targeted: `6 passed`
- Phase7.2 + Phase7.3b-f combined: `36 passed`
- Phase7.0-7.3f combined: `41 passed`
- Full suite: `214 passed`
- `compileall`: passed
- runtime-only redline scan: no matches

宽扫命中过测试中的禁止断言文本和 7.3c 的测试常量,不属于 runtime 行为路径。

## 5. 最终汇总

Phase7.3b/c/d/e/f 现在形成了更完整的最小闭环:

`teacher-off undecidable draft -> observer-only introspection feeling -> AP-native cooccurrence with external expression -> reply pressure gate -> expression paradigm rebind -> committed concise uncertainty expression`

现在可以把 Phase7.3b/c/d/e/f 整套结果交给 Claude 做端到端审阅。建议重点审:

- label opacity: 内部 label 是否仍可能被 runtime 语义解析。
- pressure non-policy: reply pressure 是否只决定"要不要回应",不决定"说什么"。
- association non-answer-table: 共现 store 是否仍可能退化为答案表或 cue 反查。
- expression rebind non-hardcoded: 是否存在 `case_name`、中文关键词、固定答案或 LLM policy 后门。
- replay behavior: 失败、感受保留、外部表达共现、后续召回是否真的在 AP-native evidence 层闭合。

仍不能宣称:

- 完整 APV3.0 中文开放自由对话底座已完成。
- 任意中文场景都能主动澄清或稳定表达不确定。
- 所有 introspection feeling 都已泛化学习。
- 跨模态 adapter 和任意模态一等 SA 混合学习已完成。
- 长期自然对话学习、遗忘/淘汰、10G 级 SQLite 运行已经验收。

下一步建议在 Claude 审阅通过后,进入 Phase7.4: 把 learned uncertainty expression 从单一疑惑表达扩展到多类内部感受表达的 teacher-off 泛化 probe,仍保持所有表达只来自后天观察与 AP-native 共现。
