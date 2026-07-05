# APV3 Phase 10.5 Final Report: Theory of Mind Belief Model

日期: 2026-06-18

状态: 通过

## Design

Phase 10.5 的目标是建立最小他人信念 SA：AP 能同时保存“现实位置”和“某个实体相信的位置”，并在假信念场景下预测对方会按其信念行动。

## Review

审查重点是防止把 AP 自己知道的现实覆盖到他人信念上。belief SA 使用 `belief::other::<entity>::<topic>` 独立 key，并在 metadata 中保留 `counterfactual_dependency`。

## Landing

落地文件:

- `runtime/cognitive/theory_of_mind/belief_model.py`
- `tests/test_phase10_5_theory_of_mind_belief.py`

## Validation

验收覆盖:

- 他人信念位置与现实位置可分离。
- 假信念 trace 预测对方会去 believed location。
- 信念与现实一致时预测现实位置。
- `red_line_check_v14.py --phase 10.5` 交付物门。

## Boundary

这一步证明最小假信念结构成立，不宣称完整心智理论、复杂社交意图理解或成人级心理推断完成。

## Next

Phase 10.6 将把匿名 cluster 与名字、is-a、part-of 关系绑定成层级 SA。
