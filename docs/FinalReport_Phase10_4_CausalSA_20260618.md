# APV3 Phase 10.4 Final Report: Causal SA

日期: 2026-06-18

状态: 通过

## Design

Phase 10.4 的目标是只把通过 Phase 10.3 CDE 门的关系生成 causal SA。因果 SA 是普通 StateItem，不是外置规则库；它携带 source、target、framework 和效应强度 metadata。

## Review

审查重点是不能把相关性直接升级为因果。`spawn_causal_sa` 只接受 `passes_threshold=True` 的 CDE trace。

## Landing

落地文件:

- `runtime/cognitive/causal/causal_sa.py`
- `tests/test_phase10_4_causal_sa.py`

## Validation

验收覆盖:

- passing CDE trace 生成 `family="causal"` 的 StateItem。
- failed CDE trace 返回 None。
- metadata 保留 `framework="controlled_direct_effect"`。
- `red_line_check_v14.py --phase 10.4` 交付物门。

## Boundary

这一步证明最小因果 SA 固化成立，不宣称现实世界复杂因果图、社会因果解释或任意反事实问答完成。

## Next

Phase 10.5 将基于反事实视角建立最小他人信念模型。
