# APV3 Phase 10.3 Final Report: Counterfactual Controlled Direct Effect

日期: 2026-06-18

状态: 通过

## Design

Phase 10.3 的目标是实现最小反事实模拟框架。它不声明 total causal effect，而是明确标注为 `controlled_direct_effect`：在冻结其他上下文的情况下，改变一个 source SA 的干预水平，观察 target SA 的响应曲线。

## Review

审查重点是术语诚实和单调性门。trace 必须写明 `framework="controlled_direct_effect"`，并且只有 intervention level 从 0 到 1 时 target response 单调、相对效应超过阈值，才算通过。

## Landing

落地文件:

- `runtime/cognitive/counterfactual/simulator.py`
- `tests/test_phase10_3_counterfactual_cde.py`

## Validation

验收覆盖:

- 有直接效应时生成 passing CDE trace。
- 无直接效应时即使事件存在也不通过。
- trace 明确记录 intervention levels、absolute/relative strength 和 framework。
- `red_line_check_v14.py --phase 10.3` 交付物门。

## Boundary

这一步证明的是最小受控直接效应，不宣称完整因果推断、混杂消除、total effect 或成人级反事实推理完成。

## Next

Phase 10.4 将把通过 CDE 的关系固化为 causal SA。
