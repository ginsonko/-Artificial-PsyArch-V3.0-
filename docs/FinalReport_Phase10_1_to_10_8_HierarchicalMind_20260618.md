# APV3 Phase 10.1-10.8 Final Report: Hierarchical Mind Layer

日期: 2026-06-18

状态: 通过

## 1. Design

Phase 10 的目标是把 Phase 8 的多模态地基和 Phase 9 的主动心智深度，推进到 5-8 岁层级心智的最小结构:

- 10.1 Narrative SA: lag-PMI 学到时序事件链。
- 10.2 Anonymous super-cluster: 共享 slot/channel 的匿名概念聚合。
- 10.3 Counterfactual CDE: 受控直接效应，不偷换成 total effect。
- 10.4 Causal SA: 只有 passing CDE trace 才能固化为因果关系。
- 10.5 Theory of Mind: 他人信念与现实分离，支持最小假信念测试。
- 10.6 Hierarchy SA: 匿名 cluster 后命名，支持 is-a/part-of。
- 10.7 Trust prior: 熟悉性与教学准确率合成信任先验，并允许反证降级。
- 10.8 Reading pipeline: streaming/reading 共用字符感受器，source 字段区分来源。

## 2. Review

本阶段延续 v14.1 审计纪律:

- 不使用关键词路线、答案表、正则路线、隐藏求解器、学生侧 LLM 或整句宏。
- 所有新增认知结构都是 StateItem、MarkerEvent、ledger、SDPL 或已有 long-term 体系中的一等信号。
- 常量进入 `config/apv3_constants.yaml`。
- 非平凡 runtime/cognitive 函数保留 `@op_count`。
- 反事实机制明确写成 `controlled_direct_effect`，不夸大为完整因果。

## 3. Landing

新增或使用的主要 runtime:

- `runtime/cognitive/narrative/lag_pmi.py`
- `runtime/cognitive/hierarchy/anonymous_cluster.py`
- `runtime/cognitive/counterfactual/simulator.py`
- `runtime/cognitive/causal/causal_sa.py`
- `runtime/cognitive/theory_of_mind/belief_model.py`
- `runtime/cognitive/hierarchy/hierarchy_sa.py`
- `runtime/cognitive/trust/trust_prior.py`
- `runtime/cognitive/reading/reading_pipeline.py`

新增测试:

- `tests/test_phase10_1_narrative_lag_pmi.py`
- `tests/test_phase10_2_anonymous_super_cluster.py`
- `tests/test_phase10_3_counterfactual_cde.py`
- `tests/test_phase10_4_causal_sa.py`
- `tests/test_phase10_5_theory_of_mind_belief.py`
- `tests/test_phase10_6_hierarchy_sa.py`
- `tests/test_phase10_7_trust_prior.py`
- `tests/test_phase10_8_reading_pipeline.py`

## 4. Validation

计划并执行的验收命令:

```text
python -m pytest -q tests/test_phase10_*.py
python scripts/red_line_check_v14.py --phase 10.1
python scripts/red_line_check_v14.py --phase 10.2
python scripts/red_line_check_v14.py --phase 10.3
python scripts/red_line_check_v14.py --phase 10.4
python scripts/red_line_check_v14.py --phase 10.5
python scripts/red_line_check_v14.py --phase 10.6
python scripts/red_line_check_v14.py --phase 10.7
python scripts/red_line_check_v14.py --phase 10.8
python scripts/red_line_check_v14.py
python scripts/check_constant_governance.py
python -m compileall apv3test runtime tests -q
python -m pytest -q
```

结果:

- Phase 10.1-10.8 targeted: 28 passed
- Phase 10 deliverable gates: PASS
- v14 red-line check: PASS
- constants governance: PASS, 229 numeric constants governed
- compileall: PASS
- full suite: 385 passed

## 5. Boundary

Phase 10 证明的是最小层级心智探针闭环: 叙事、匿名概念聚合、受控反事实、因果 SA、假信念、层级命名、信任先验和阅读单管道。它仍不能宣称完整成人心智理论、通用因果科学、自然长篇阅读理解、完整开放中文对话产品或真实硬件多模态系统完成。

## 6. Next

下一步建议 Phase 11: 8-12 岁元认知层，包括 meta-cognition、abstract vocab、goal horizon、deliberative virtual track 和 self model。推进前仍应先做设计审查，而不是把 Phase 10 的成功当成自动通行证。
