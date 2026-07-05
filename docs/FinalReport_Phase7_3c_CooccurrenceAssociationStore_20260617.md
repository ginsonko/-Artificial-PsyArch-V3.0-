# APV3 Phase7.3c CooccurrenceAssociationStore 最终报告

日期: 2026-06-17
阶段: Phase7.3c
状态: 通过

## 1. 设计

本阶段实现 V3.1 路线中的 Phase7.3c:最小共现关联 store。它服务于后续“内省 feeling SA 与外部表达 token 共现学习”,但本阶段仍不接入 reply_pressure 或 expression rebind。

核心原则:

- 共现学习写入稀疏 association evidence,不写关键词规则、答案表或表达策略。
- `teacher_reply`、`perception_other`、`self_emission` 只作为 provenance 权重来源;学生侧 store schema 不含 “LLM said so” 路由字段。
- 同一个 `(feeling_label, expression_token)` 自然观察和教师教学会写入同构 pair evidence。
- `self_emission` 默认 `gamma=0`,自发声不抬 cooccurrence support。
- 直接维护 `(feeling_label, paradigm_id)` 聚合,不引入未定义的 `find_by_cue_token`。

## 2. 审查完善

本阶段吸收 V3.1 指定的 7.3c 修正:

- B3:实现 normative SQLite DDL、import/export 契约、warm-load parity、import 幂等和不重锚 tick。
- B5:取消未定义的 `find_by_cue_token`,由 `CooccurrenceAssociationStore` 直接维护 paradigm 聚合。
- S3:新增目标表达 vs 干扰 token 的时间规律性测试;两者使用相同 attention,不靠测试硬塞权重。
- S4:实现 `compact(current_tick)` 与 `retire_label()`;prototype 退役时可对称清理关联。
- M6:保留 `_by_b` 反向索引并在 `retire_label()` 中使用,不是死字段。

## 3. 通过落地

新增:

- `apv3test/runtime/cooccurrence_store.py`
- `apv3test/runtime/cooccurrence_learning.py`
- `tests/test_phase7_3c_cooccurrence_association_store.py`

更新:

- `apv3test/config/introspection_config.py`
- `apv3test/runtime/__init__.py`

核心接口:

- `CooccurrenceAssociationStore.observe()`
- `CooccurrenceAssociationStore.observe_paradigm()`
- `similarity()` / `similarity_paradigm()`
- `nearest_by_label()` / `nearest_paradigms_by_label()`
- `compact()`
- `retire_label()`
- `export_to_sqlite()` / `import_from_sqlite()`
- `observe_feeling_expression_cooccurrence()`

## 4. 严谨验收测试

已执行:

```text
python -m py_compile APV3.0test\apv3test\runtime\cooccurrence_store.py APV3.0test\apv3test\runtime\cooccurrence_learning.py APV3.0test\tests\test_phase7_3c_cooccurrence_association_store.py
python -m pytest APV3.0test\tests\test_phase7_3c_cooccurrence_association_store.py -q
python -m pytest APV3.0test\tests\test_phase7_3b_draft_introspection_observer.py APV3.0test\tests\test_phase7_3c_cooccurrence_association_store.py APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py APV3.0test\tests\test_phase7_1_undecidable_shared_fragment.py APV3.0test\tests\test_phase7_2_learned_uncertainty_expression.py -q
python -m pytest APV3.0test\tests -q
rg -n "find_by_cue_token|must_reply|undecidable_feeling_tokens|feeling::undecidable|case_name|expr::uncertain|if .*text|if .*vision|startswith\(|endswith\(|__contains__|getattr\(" APV3.0test\apv3test\runtime\cooccurrence_store.py APV3.0test\apv3test\runtime\cooccurrence_learning.py
```

结果:

- Phase7.3c target: `8 passed`
- Phase7.3b + 7.3c + Phase7.0-7.2 regression: `26 passed`
- Full suite: `199 passed`
- Redline scan for 7.3c runtime: no matches

重点样例:

- 成功样例 A:feeling 与 expression 多次共现后,相似度相对增量上升,`nearest_by_label()` 可召回目标表达。
- 成功样例 B:self-emission token 不增加 association support。
- 成功样例 C:目标表达与 feeling_a 稳定共现,干扰 token 在 feeling_a/feeling_b 间随机翻转;目标得分显著高于干扰。
- 成功样例 D:观察时携带 `paradigm_id`,store 直接聚合 `(feeling_label, paradigm_id)`,无需 `find_by_cue_token`。
- 成功样例 E:SQLite warm-load 后 token similarity、nearest fanout、paradigm fanout 行为等价。
- 成功样例 F:import 不重锚 tick,同一连接同 tick import 幂等。
- 成功样例 G:sub-floor 行被 import/compact 驱逐。
- 成功样例 H:`retire_label()` 同时删除 token pair 与 paradigm pair,不影响其他 feeling。

## 5. 最终汇总

Phase7.3c 已完成最小 AP-native 共现关联层。现在可以说 APV3.0test 具备了“内省 feeling SA 与外部表达 token/表达范式之间的稀疏共现证据存储和召回索引”。

仍不能宣称:

- 还没有 reply_pressure SA。
- 还没有 expression recall/rebind。
- 还没有端到端 learned uncertainty expression 替换 Phase7.2。
- 还没有跨模态 adapter 验收。

阶段性审阅建议:

现在可以把 Phase7.3b + Phase7.3c 的结果交给 Claude 做一次阶段性审阅,重点审:

- 7.3b 的 observer-only 内省 feeling 是否仍符合拟人原则。
- 7.3c 的 association store 是否真正避免了 `find_by_cue_token` 和答案表。
- SQLite import/export 是否满足“不重锚 tick”和 warm-load parity。
- 目标表达 vs 干扰 token 的验收是否足够抗测试串通。

如果要审“完整表达学习链路”,建议等 Phase7.3d/7.3e 完成后再做第二轮,因为 reply_pressure 与 rebind 还未接入。

下一步建议 Phase7.3d:实现从状态池 SA 涌现的 reply_pressure,迁移 Phase7.2 的 `must_reply` 测试入口,并验证 pressure SA 衰减、silence reset、`sa_kind` 结构属性和 provenance out-of-band trace。

