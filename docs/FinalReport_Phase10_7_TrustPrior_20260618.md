# APV3 Phase 10.7 Final Report: Trust Prior and Downgrade

日期: 2026-06-18

状态: 通过

## Design

Phase 10.7 的目标是把熟悉性依恋和教学准确率合成最小 trust prior。可信实体给出的证据可以生成 `TRUST_PROMOTED` marker；若后续 Delta-P 明显反证，则降低教学准确率并标记 downgrade。

## Review

审查重点是信任不能变成永久免检。trust prior 可以提升注意和证据进入机会，但负 Delta-P 会降级，避免“熟人说什么都对”的硬规则。

## Landing

落地文件:

- `runtime/cognitive/trust/trust_prior.py`
- `tests/test_phase10_7_trust_prior.py`

## Validation

验收覆盖:

- 重复正向互动和高教学准确率生成 TRUST_PROMOTED marker。
- 负 Delta-P 降低 trust，不生成 promoted marker。
- trust_score 由 attachment 和 accuracy 共同决定。
- `red_line_check_v14.py --phase 10.7` 交付物门。

## Boundary

这一步证明最小信任先验成立，不宣称完整人格判断、社会声誉系统或现实用户安全策略完成。

## Next

Phase 10.8 将把 streaming 与 reading 文本输入统一到同一个字符感受器管道。
