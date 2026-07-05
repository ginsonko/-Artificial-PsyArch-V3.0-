# APV3 Phase7.3b 草稿内省原型 Observer-only 最终报告

日期: 2026-06-17
阶段: Phase7.3b
状态: 通过

## 1. 设计

本阶段只落地 V3.1 路线中的 Phase7.3b:内省原型 observer-only。目标是让系统从草稿结构事实中自动涌现 draft-introspection feeling SA,并写入独立子池 `introspection_feelings`,但不接入共现学习、不触发表达召回、不改变现有 teacher-off 发声行为。

本阶段遵守的关键边界:

- 不使用 `feeling::undecidable` 外部预置标签。
- 不使用 `must_reply` 作为新触发源。
- 不接入 expression recall/rebind。
- 不写入 `state_field_items`,避免扰动既有状态池能量和 Phase7.0/7.1 行为。
- 特征抽取只读 `role / is_filled / occupancy / fit_margin / commit_readiness` 协议字段,不读 token 内容、label、case_name 或 anchor_meta。

## 2. 审查完善

本阶段吸收 V3.1 指定的 7.3b 修正:

- B1:原型衰减改为每 tick 单步衰减,避免 `decay ** age` 超指数塌陷。
- B2:prototype `next_id` 作为一等状态持久化,即使所有原型被驱逐也不重用旧 id。
- B6:原型持久化记录 `phi_pooling_schema_version`,schema 不匹配时只失效 phi6 维度,避免几何漂移静默污染。
- S1:内省 feeling 写入 `introspection_feelings` 子池,不进入 `state_field_items`。
- S7:tau 更新先用旧 mu 计算 residual,再移动 mu,避免 tau 系统性低估。
- S8:`DraftSAEnergyView` 使用 `is_filled`,不暴露 `filler` 内容字段;新增 AST 白名单测试。
- S9:`emit_draft_introspection_feelings` 显式自增 `state["tick"]`。

## 3. 通过落地

新增:

- `apv3test/config/introspection_config.py`
- `apv3test/runtime/draft_introspection.py`
- `tests/test_phase7_3b_draft_introspection_observer.py`

更新:

- `apv3test/runtime/__init__.py`

核心行为:

- `extract_facts()` 从草稿结构计算 7 维 phi。
- `IntrospectionPrototypeStore.respond_or_spawn()` 使用 `min_distance > theta_spawn` 判定新原型,softmax 只负责旧原型间响应分配。
- `DraftIntrospectionFeeling` 只携带 opaque `sa_label`,不携带 `prototype_id` 并行通道。
- `emit_draft_introspection_feelings()` 作为 observer-only 入口,只更新内省子池和原型 store。

## 4. 严谨验收测试

已执行:

```text
python -m py_compile APV3.0test\apv3test\config\introspection_config.py APV3.0test\apv3test\runtime\draft_introspection.py APV3.0test\tests\test_phase7_3b_draft_introspection_observer.py
python -m pytest APV3.0test\tests\test_phase7_3b_draft_introspection_observer.py -q
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py APV3.0test\tests\test_phase7_1_undecidable_shared_fragment.py APV3.0test\tests\test_phase7_2_learned_uncertainty_expression.py -q
python -m pytest APV3.0test\tests -q
```

结果:

- Phase7.3b target: `11 passed`
- Phase7.0-7.2 regression: `7 passed`
- Full suite: `191 passed`

重点样例:

- 成功样例 A:未教学情况下,`slot(unfilled) -> shared_fragment(filled)` 草稿结构自动产生 `draft_introspection_feeling`,并设置 `draft_commit_blocked=True`。
- 成功样例 B:同结构不同内容复用同一原型 label,证明当前机制看结构而非 token 内容。
- 成功样例 C:只有一个旧原型时,远距离 phi 仍能 spawn 新原型,不被 softmax `r=1` 吸附。
- 成功样例 D:prototype id 在 mu 漂移后保持稳定。
- 成功样例 E:所有原型被驱逐后 warm-load 继续使用持久化 `next_id`,不重用旧 label。
- 成功样例 F:AST 白名单验证 `extract_facts()` 未读取 `filler/value/cue/label/anchor_meta` 等内容字段。

## 5. 最终汇总

Phase7.3b 已完成 observer-only 内省原型门。现在可以说 APV3.0test 具备了“从草稿结构事实自动涌现内省 feeling SA 的最小机制”,但仍不能宣称已经完成 learned uncertainty expression 或自由对话表达学习。

仍不能宣称:

- 还没有共现关联 store。
- 还没有 `teacher_reply/perception_other/self_emission` provenance 学习。
- 还没有 reply_pressure SA。
- 还没有 expression recall/rebind。
- 还没有跨模态 adapter 验收。

下一步建议 Phase7.3c:实现 `CooccurrenceAssociationStore`,包含 pair association、`nearest_paradigms_by_label` 聚合、SQLite warm-load parity、compact/retire_label,并验证目标表达共现增量显著高于干扰 token。

