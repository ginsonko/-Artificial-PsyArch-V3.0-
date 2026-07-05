# Phase 9.5 Final Report: Joint Attention

日期: 2026-06-17

状态: 通过

## 1. 设计

Phase 9.5 验证 AP 与用户对同一对象形成共同注意。共享焦点产生 `JOINT_ATTENTION` marker，并给目标对象轻微 attention boost。

## 2. 审查完善

- 共同注意基于结构焦点一致，不看中文关键词。
- 低置信度或不同目标不会 spawn marker。
- marker 通过 StatePool 进入统一审计路径。

## 3. 通过落地

- `runtime/cognitive/social/joint_attention.py`
- `tests/test_phase9_5_joint_attention.py`
- `config/apv3_constants.yaml`

## 4. 严谨验收测试

已执行:

```text
python -m pytest -q tests/test_phase9_5_joint_attention.py
python scripts/red_line_check_v14.py --phase 9.5
python scripts/red_line_check_v14.py
python scripts/check_constant_governance.py
python -m compileall apv3test runtime tests -q
python -m pytest -q
```

结果:

- Phase 9.5 targeted: 4 passed
- Phase 9.5 deliverable gate: PASS
- v14 red-line check: PASS
- constants governance: PASS
- compileall: PASS
- full suite after Phase 9: 357 passed

## 5. 边界

本阶段证明共同注意最小 marker，不证明完整他人意图模型或假信念理解。

## 6. 下一步

Phase 9.6: 共情 / 心智化前体。
