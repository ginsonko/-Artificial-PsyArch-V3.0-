# Phase 9.1 Final Report: Drive SA Homeostasis

日期: 2026-06-17

状态: 通过

## 1. 设计

Phase 9.1 的目标是把 APV3 从“有输入才响应”的被动模式，推进到最小主动心智层: 内部驱力本身成为一等 SA。

本阶段落地 5 类初始 drive:

- hunger
- curiosity
- exploration
- social
- completion

它们不是中文关键词路由，也不是回复脚本，而是统一的 `EntitySA::drive::*` 状态项。每个 drive 的压力来自 `config/apv3_constants.yaml` 中的 feature 权重，例如 body deficit、novelty gap、idle norm、social absence、unfinished pressure。runtime 只执行同一套加权公式。

## 2. 审查完善

关键审查点:

- drive 必须进入状态池，具备 R/V/P/A/F 字段。
- attention gain 必须经 `AttentionGainLedger.inject("drive_pressure", ...)`，并纳入 endogenous share。
- 无外部输入时只能产生 drive/action proposal，不能直接生成中文回复。
- satisfaction 只能降低匹配 drive，不能把其它 drive 的压力一起清掉。
- 5 类初始 drive 的权重在 YAML 中，避免把未来扩展写死在认知路径。

## 3. 通过落地

新增/修改:

- `runtime/cognitive/drive/homeostatic_drive.py`
- `runtime/cognitive/drive/__init__.py`
- `runtime/cognitive/state_pool/attention_gain_ledger.py`
- `config/apv3_constants.yaml`
- `tests/test_phase9_1_drive_homeostasis.py`
- `scripts/red_line_check_v14.py`
- `reports/APV3_Phase9_1_DriveSAHomeostasis_Showcase_20260617.html`

## 4. 严谨验收测试

已执行:

```text
python -m pytest -q tests/test_phase9_1_drive_homeostasis.py
python scripts/red_line_check_v14.py --phase 9.1
python scripts/red_line_check_v14.py
python scripts/check_constant_governance.py
python -m compileall apv3test runtime tests -q
python -m pytest -q
```

结果:

- Phase 9.1 targeted: 5 passed
- Phase 9.1 deliverable gate: PASS
- v14 red-line check: PASS
- constants governance: PASS
- compileall: PASS
- full suite: 326 passed

## 5. 边界

本阶段只证明 drive SA / 内稳态压力 / drive proposal 的最小闭环。它还不证明:

- RPE / dopamine analog 已接入。
- 受挫、习得性无助已经完成。
- 依恋、共同注意、共情已经完成。
- drive proposal 已接入最终 Web 对话行动选择器。
- 系统已经会像真实儿童一样长期规划。

## 6. 下一步

最稳的下一步是 Phase 9.2: RPE / dopamine analog。把 reward prediction error 作为独立学习信号接入 SDPL Q 更新，使 drive 产生的行动不只是“有压力”，而是能根据结果调整学习率和注意力竞争。
