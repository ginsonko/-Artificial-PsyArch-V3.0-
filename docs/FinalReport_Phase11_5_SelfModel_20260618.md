# APV3 Phase 11.5 Final Report: Self Model

日期: 2026-06-18

状态: 通过

## Design

Phase 11.5 实现最小 self model：`EntitySA::self::ap_self` 作为可衰减但可 heartbeat 拉回的持续身份锚点。

## Review

审查重点是不要新增未经设计的 marker kind。实现只使用 self_model StateItem 和 ledger 注入，不抢用 reserved marker。

## Landing

- `runtime/cognitive/self_model/heartbeat.py`
- `tests/test_phase11_5_self_model.py`

## Validation

- self model 作为 persistent EntitySA 存在。
- 低 real_energy 时 heartbeat reactivation 生效。
- phase gate 11.5 PASS。

## Boundary

这一步证明最小持续自我锚点成立，不宣称完整人格、自传式自我叙事或长期身份安全策略完成。

## Next

Phase 12: demo substrate。
