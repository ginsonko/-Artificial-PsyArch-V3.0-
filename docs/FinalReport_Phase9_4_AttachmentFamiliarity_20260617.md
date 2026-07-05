# Phase 9.4 Final Report: Attachment / Familiarity Preference

日期: 2026-06-17

状态: 通过

## 1. 设计

Phase 9.4 把长期互动对象建成 `EntitySA::user::*`。熟悉性和 OXY-like tone 随交互累积，形成“老用户更熟悉”的最小依恋偏好。

## 2. 审查完善

- entity_user 是状态池一等实体。
- 重复互动提高 familiarity。
- positive affect 提高 OXY-like tone。
- 偏好来自状态能量，不来自用户名硬编码。

## 3. 通过落地

- `runtime/cognitive/social/attachment.py`
- `tests/test_phase9_4_attachment_familiarity.py`
- `config/apv3_constants.yaml`

## 4. 严谨验收测试

已执行:

```text
python -m pytest -q tests/test_phase9_4_attachment_familiarity.py
python scripts/red_line_check_v14.py --phase 9.4
python scripts/red_line_check_v14.py
python scripts/check_constant_governance.py
python -m compileall apv3test runtime tests -q
python -m pytest -q
```

结果:

- Phase 9.4 targeted: 4 passed
- Phase 9.4 deliverable gate: PASS
- v14 red-line check: PASS
- constants governance: PASS
- compileall: PASS
- full suite after Phase 9: 357 passed

## 5. 边界

本阶段证明熟悉性偏好，不证明复杂亲密关系、伦理策略或多用户权限系统。

## 6. 下一步

Phase 9.5: 共同注意 / 镜像。
