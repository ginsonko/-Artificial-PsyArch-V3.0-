# APV3 Phase7.4 Multifeeling Expression Generalization 最终报告
日期: 2026-06-17
阶段: Phase7.4
状态: 通过

## 1. 设计

Phase7.4 从 Phase7.3 的单一 learned uncertainty expression,推进到"多类结构性内省 feeling -> 多类表达关联"的广度探针。

本阶段不新增 runtime 策略,不新增每类感受的专用分支,只复用:

- `emit_draft_introspection_feelings()`
- `IntrospectionPrototypeStore`
- `CooccurrenceAssociationStore`
- `observe_feeling_expression_cooccurrence()`
- teacher-off replay 时的 `nearest_by_label()` / `nearest_paradigms_by_label()`

验收目标:

- 250 tick 多结构日志中自然涌现至少 3 个稳定 prototype; 实际目标设置为 5 类结构态。
- 每个 prototype 通过 AP-native 共现学习到不同 expression token 和 expression paradigm id。
- teacher-off 重放同类结构时,不提供外部表达输入,仍能召回对应表达。
- 干扰表达存在时,目标关联强度显著高于最强干扰。
- 改变内部 feeling label 字面后,经双射归一外部召回行为保持一致。

## 2. 审查完善

吸收 Claude 审阅建议:

- 不预设"哪种感受叫什么名字"; 测试只提供结构事实和外部表达共现。
- 不让系统读取 expression token 的语义; token 使用 `expr::band_*` 这类无语义探针。
- 不让 runtime 出现 `structure_*` 或 `expr::band_*` 路由。
- 不用 LLM 标注 prototype id,不把 teacher 变成 student-side policy。

边界收窄:

- Phase7.4 验证的是"结构性内省原型的多类表达关联能力",不是证明所有人类情绪/心绪都已覆盖。
- 这里的 5 类结构态来自 draft structure phi 的不同维度组合,仍不是自然长篇中文对话语料。

## 3. 通过落地

新增:

- `tests/test_phase7_4_multifeeling_expression_generalization.py`

测试结构:

- 5 个 `_StructuralEpisode`,分别由不同 draft structural facts 触发:
  - unresolved slot + shared fragment
  - all filled but very low commit readiness
  - high paradigm competition
  - high recent punishment resemblance
  - sparse unresolved slots without shared fragment
- 250 tick curriculum,每 tick 只有当前结构产生的 feeling label 进入共现学习。
- 目标表达 attention 高,干扰表达和噪声 token attention 低但持续存在。
- teacher-off replay 只重放结构,不再调用 `observe_feeling_expression_cooccurrence()`。

实际 trace 摘要:

```text
active_prototypes 5
structure_0 feeling::draft::proto_0 expr::band_0 p:expr:band_0 target=3.3903 best_other=0.4786
structure_1 feeling::draft::proto_1 expr::band_1 p:expr:band_1 target=3.3903 best_other=0.4786
structure_2 feeling::draft::proto_2 expr::band_2 p:expr:band_2 target=3.3903 best_other=0.4786
structure_3 feeling::draft::proto_3 expr::band_3 p:expr:band_3 target=3.3903 best_other=0.4786
structure_4 feeling::draft::proto_4 expr::band_4 p:expr:band_4 target=3.3903 best_other=0.4786
```

## 4. 严谨验收测试

已执行:

```text
python -m pytest APV3.0test\tests\test_phase7_4_multifeeling_expression_generalization.py -q
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py APV3.0test\tests\test_phase7_1_undecidable_shared_fragment.py APV3.0test\tests\test_phase7_2_learned_uncertainty_expression.py APV3.0test\tests\test_phase7_3b_draft_introspection_observer.py APV3.0test\tests\test_phase7_3c_cooccurrence_association_store.py APV3.0test\tests\test_phase7_3d_reply_pressure_sa.py APV3.0test\tests\test_phase7_3e_expression_recall_rebind.py APV3.0test\tests\test_phase7_3f_invariants_replay.py APV3.0test\tests\test_phase7_4_multifeeling_expression_generalization.py -q
python -m pytest APV3.0test\tests -q
python -m compileall APV3.0test\apv3test APV3.0test\tests -q
rg -n "expr::band_|structure_|must_reply|undecidable_feeling_tokens|feeling::undecidable|find_by_cue_token|_most_common_reply|pressure_type_weights|student_side_llm|answer_table|LLM policy" APV3.0test\apv3test\runtime
```

结果:

- Phase7.4 targeted: `5 passed`
- Phase7.0-7.4 combined: `46 passed`
- Full suite: `219 passed`
- `compileall`: passed
- runtime-only redline scan: no matches

## 5. 最终汇总

Phase7.4 说明: 当前内省 feeling 机制不是只会做 Phase7.3 的单一"不能决"特例。默认参数下,同一套结构事实 -> 原型涌现 -> 共现关联 -> teacher-off recall 机制,已经能在 5 类结构态上稳定分化并学习不同表达。

可交给 Claude 审阅的重点:

- 5 类结构态是否真的由 structural facts 触发,而不是内容 token 或语义 label。
- `expr::band_*` 是否只出现在测试,没有进入 runtime。
- teacher-off replay 是否真的不再提供外部表达输入。
- 目标/干扰混淆矩阵是否足以证明共现区分,而非随机命中。
- label-bijection 是否足以说明内部 feeling label 仍是 opaque key。

仍不能宣称:

- 所有人类内省感受或情绪表达都已覆盖。
- 自然中文长对话中的真实表达风格已经学会。
- vision/audio 等跨模态 adapter 已经完成同等泛化。
- 长期运行中 prototype 漂移、遗忘、表达风格再学习已经验收。
- 完整 APV3.0 中文开放自由对话底座已经完成。

下一步建议 Phase7.5: 把多类内省表达从纯测试结构日志推进到最小 dialogue runtime 组合场景,让不同工作记忆/奖惩/主动求教压力共同触发不同结构态,继续验证表达选择仍只来自 AP-native 共现而非策略表。
