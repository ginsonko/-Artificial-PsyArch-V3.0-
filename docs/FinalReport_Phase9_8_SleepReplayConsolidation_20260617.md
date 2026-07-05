# Phase 9.8 Final Report: Sleep Replay Consolidation

日期: 2026-06-17

状态: 通过

## 1. 设计

Phase 9.8 在 idle/sleep-like 阶段从 long-term cold pool 中选择高能量经验进行内部 replay，spawn REMEMBERED marker，并轻微巩固 long_term_R。

## 2. 审查完善

- replay 有 top-k 上限。
- replay 走 REMEMBERED marker，不错标为 IMAGINED。
- replay 是优化项，不作为 Phase 8 跨 session 的前提。

## 3. 通过落地

- `runtime/cognitive/sleep/replay_consolidation.py`
- `tests/test_phase9_8_sleep_replay.py`
- `config/apv3_constants.yaml`

## 4. 严谨验收测试

已执行:

```text
python -m pytest -q tests/test_phase9_8_sleep_replay.py
python scripts/red_line_check_v14.py --phase 9.8
python scripts/red_line_check_v14.py
python scripts/check_constant_governance.py
python -m compileall apv3test runtime tests -q
python -m pytest -q
```

结果:

- Phase 9.8 targeted: 4 passed
- Phase 9.8 deliverable gate: PASS
- v14 red-line check: PASS
- constants governance: PASS
- compileall: PASS
- full suite after Phase 9: 357 passed

## 5. 边界

本阶段证明最小重放巩固，不证明真实睡眠周期、梦境叙事或大规模离线训练。

## 6. 下一步

Phase 9.9: 游戏 / 探索玩乐。
