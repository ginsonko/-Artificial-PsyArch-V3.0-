# APV3 Phase7.5 Runtime Context Multifeeling Integration 最终报告
日期: 2026-06-17
阶段: Phase7.5
状态: 通过

## 1. 设计

Phase7.5 把 Phase7.4 的多类结构性内省 feeling 表达泛化,从纯结构日志推进到最小 runtime 组合场景。

本阶段仍不新增表达策略表,不为每类 feeling 写专用分支,不让 runtime 读取 expression token 或场景名。它只验证已有 AP-native runtime 事件能成为结构事实来源:

- teacher-off dialogue 不能决草稿
- work memory 未完成压力
- active teacher_request SA
- punishment observation
- rewarded smooth commit

这些事件分别提供不同的 structural facts 组合,再进入同一条:

`runtime event -> structural draft-introspection feeling -> cooccurrence association -> teacher-off expression recall`

## 2. 审查完善

落地时发现并修正了两个测试设计问题:

- 不能把 `punish_delta > 0` 直接等同于"范式立刻 exposed=false"; 改为检查 `paradigm_observations[*].punish_delta` 这一真实惩罚证据。
- `work_memory_unfinished` 是 runtime 合法 SA 类型,不是红线; redline 只禁止测试场景名、表达 token、旧字段和后门路线进入 runtime。

审查边界:

- 本阶段测试中的 `expr::runtime_*` 只作为外部教师/旁人表达 token,不得进入 runtime。
- teacher-off replay 不调用 `observe_feeling_expression_cooccurrence()`,store snapshot 必须不变。
- 主动求教使用不同 cue 避免 cooldown 吞掉组合场景,但表达学习仍不读取 cue 语义。

## 3. 通过落地

新增:

- `tests/test_phase7_5_runtime_context_multifeeling_integration.py`

测试覆盖:

- 5 类 runtime context 触发 5 类结构事实。
- 每类结构事实在 150 tick curriculum 中形成稳定 feeling label。
- 外部表达通过 `CooccurrenceAssociationStore` 形成 `(feeling_label, expression_token/paradigm_id)` 关联。
- teacher-off replay 只重放 runtime context 和 structural facts,不再喂表达。
- runtime-only redline scan 确认测试表达/场景没有进入运行时代码。

实际 trace 摘要:

```text
situations 5
dialogue_uncertain dialogue_undecidable_draft feeling::draft::proto_0 expr::runtime_dialogue p:expr:runtime_dialogue target=0.4075 best_other=0.0589
work_memory_unfinished work_memory_unfinished_pool_entry feeling::draft::proto_1 expr::runtime_work_memory p:expr:runtime_work_memory target=0.4075 best_other=0.0589
teacher_request_pressure teacher_request_sa feeling::draft::proto_2 expr::runtime_teacher_request p:expr:runtime_teacher_request target=0.4075 best_other=0.0589
recent_punishment punished_action_outcome feeling::draft::proto_3 expr::runtime_punishment p:expr:runtime_punishment target=0.4075 best_other=0.0589
rewarded_flow rewarded_smooth_commit feeling::draft::proto_4 expr::runtime_flow p:expr:runtime_flow target=0.4075 best_other=0.0589
```

## 4. 严谨验收测试

已执行:

```text
python -m pytest APV3.0test\tests\test_phase7_5_runtime_context_multifeeling_integration.py -q
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py APV3.0test\tests\test_phase7_1_undecidable_shared_fragment.py APV3.0test\tests\test_phase7_2_learned_uncertainty_expression.py APV3.0test\tests\test_phase7_3b_draft_introspection_observer.py APV3.0test\tests\test_phase7_3c_cooccurrence_association_store.py APV3.0test\tests\test_phase7_3d_reply_pressure_sa.py APV3.0test\tests\test_phase7_3e_expression_recall_rebind.py APV3.0test\tests\test_phase7_3f_invariants_replay.py APV3.0test\tests\test_phase7_4_multifeeling_expression_generalization.py APV3.0test\tests\test_phase7_5_runtime_context_multifeeling_integration.py -q
python -m pytest APV3.0test\tests -q
python -m compileall APV3.0test\apv3test APV3.0test\tests -q
rg -n "expr::runtime_|dialogue_uncertain|teacher_request_pressure|rewarded_flow|must_reply|undecidable_feeling_tokens|feeling::undecidable|find_by_cue_token|_most_common_reply|pressure_type_weights|student_side_llm|answer_table|LLM policy" APV3.0test\apv3test\runtime
```

结果:

- Phase7.5 targeted: `3 passed`
- Phase7.0-7.5 combined: `49 passed`
- Full suite: `222 passed`
- `compileall`: passed
- runtime-only redline scan: no matches

## 5. 最终汇总

Phase7.5 说明: 多类内省表达已经不只是纯结构日志里的离线探针。工作记忆、奖惩、主动求教、对话不能决、顺畅奖励这些已有 runtime 事件,可以作为结构事实来源进入同一内省 feeling + 共现表达学习通道。

这进一步支撑 APV3.0test 的拟人原则:

- 系统不会天然知道"该说什么"; 它先形成内部结构性感受。
- 周围人/教师表达与当下内部感受共现后,才形成可复用表达范式。
- 下次相似内部状态出现时,表达召回来自 AP-native association,不是关键词或策略表。

仍不能宣称:

- 完整开放中文自由对话底座已完成。
- 真实自然长对话中所有工作记忆/奖惩/求教场景都能稳定表达。
- 表达风格已经从自然中文语料中学会。
- 跨模态 adapter 已经把视觉/听觉等同等接入这些内省表达。
- 长期运行中的 prototype 漂移、表达遗忘、再学习和大规模 SQLite 压测已完成。

下一步建议 Phase7.6 或 Phase8 preflight:

- 做更长的 mixed runtime episode,让 teacher_request proposal、work_memory recovery、reply_pressure、reward/punish 和 expression recall 在同一连续 episode 中反复交替。
- 若 Phase7.6 继续通过,进入 Phase8: 从内省表达机制转向更大范围的开放中文对话底座组合验收,但仍保持 teacher-off、无预填答案、无 student-side LLM、无关键词路线。
