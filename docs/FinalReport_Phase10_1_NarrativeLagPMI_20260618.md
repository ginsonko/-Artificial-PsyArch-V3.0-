# APV3 Phase 10.1 Final Report: Narrative Lag-PMI

日期: 2026-06-18

状态: 通过

## Design

Phase 10.1 的目标是让多个事件 SA 在真实时序共现中形成最小叙事链。实现使用 lag-PMI，而不是文本脚本或故事模板。只有当 A->B、B->C 的正向时序关联反复出现，并且正向 PMI 明显高于反向 PMI 时，才生成 `family="narrative"` 的 StateItem。

## Review

审查重点是避免把单次序列、反向序列或纯共现误判成叙事。实现要求有最小链长、最小 pair count、正向 PMI 阈值和反向 margin 四个门。

## Landing

落地文件:

- `runtime/cognitive/narrative/lag_pmi.py`
- `tests/test_phase10_1_narrative_lag_pmi.py`

## Validation

验收覆盖:

- 重复前向事件链生成 narrative SA。
- 反向链被 directional margin 拒绝。
- 单次样本不足时不生成叙事。
- `red_line_check_v14.py --phase 10.1` 交付物门。

## Boundary

这一步证明的是最小时序叙事链的形成，不宣称自然长故事理解、成人叙事规划或语言级故事生成完成。

## Next

Phase 10.2 将在 vocab profile 之间生成匿名 super-cluster，作为后续命名层级的前置结构。
