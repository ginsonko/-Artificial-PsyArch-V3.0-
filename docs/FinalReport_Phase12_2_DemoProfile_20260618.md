# APV3 Phase 12.2 Final Report: Demo Profile

日期: 2026-06-18

状态: 通过

## Design

Phase 12.2 定义最小 demo profile，包含四个开源展示场景与 `quiet_girl` 口味标记。它不包含 Phase13 课程内容，只定义体验底座需要知道的场景结构。

## Review

审查重点是 profile schema 必须有版本门，避免未来内容结构变化时静默误读。

## Landing

- `runtime/demo_substrate/profile.py`
- `tests/test_phase12_2_demo_profile.py`

## Validation

- 默认 profile 包含四场景。
- schema_version 不符会拒绝。
- phase gate 12.2 PASS。

## Boundary

这一步证明 demo profile 结构成立，不宣称商业 license、课程包社区协议或最终发布策略已定。

## Next

Phase 12.3: scenario readiness。
