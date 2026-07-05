# Phase20.8j C* 回灌影响后继 tick 设计

日期: 2026-06-27

## 1. 目标

Phase20.8i 已证明 C* 最小误差整合可以把虚能量真实写回 StatePool 的
`V/P/A/gain_ledger.replay`。Phase20.8j 的目标是让这份回灌不只在本 tick
可审计，而是能在后继 tick 中真实参与：

1. B 召回支持度调制。
2. C_forward / C_backward 的后继预测与归因整合。
3. C* 的最小误差计算。
4. 行动竞争 drive 的调制。

## 2. 白皮书约束

1. 不新增答案表、不新增关键词/正则路由、不新增隐藏求解器。
2. 不让 C* carryover 直接写 `reply_text`。
3. 不把 carryover 伪装成外部实能量 `R`，它只能来自上一 tick 的 `V/P/replay`。
4. 不创建独立“后继控制器”。carryover 是 StatePool 能量场的后继效应，不是新模块。
5. B/C/C* 仍以统一经验流、SSP、StatePool 为来源；索引只负责加速，不是真相来源。

## 3. 数学形式

对每个 StatePool item 读取上一 tick 以前留下的 C* 回灌痕迹：

```text
is_cstar_feedback(item) =
  item.metadata.cstar_statepool_feedback == Phase20.8i
  and item.metadata.cstar_feedback_tick < current_tick
  and (item.V > 0 or item.gain_ledger.replay > 0)
```

单个 SA 的 carryover 显著性：

```text
carry_i = clamp(
  0.62 * V_i
  + 0.22 * A_i
  + 0.10 * |P_i|
  + 0.06 * replay_i,
  0, 1
)
```

汇总量：

```text
C_max  = max(carry_i)
C_sum  = clamp(sum(carry_i) / sqrt(n + 1), 0, 1)
C_pred = max(carry_i where family == memory_prediction)
C_curr = max(carry_i where slot_kind startswith cstar_backward)
```

B 支持度调制只作用于已经存在的经验候选：

```text
support' = clamp(support + min(0.08, C_obs * 0.10), 0, 1)
```

C_forward carryover：

```text
if C_pred > 0:
  add C row: statepool_virtual_prediction_carryover
  support = C_pred
```

C_backward carryover：

```text
if C_max > 0:
  add C row: statepool_virtual_pressure_carryover
  cause_grasp = max(C_curr, C_max * 0.72)
```

行动竞争调制：

```text
drive'(action) = clamp(drive(action) + delta(action, carryover), 0, 1)
```

其中 `write_cell/commit_reply` 主要受 `C_pred` 调制，`idle_think/request_teacher`
主要受未中和压力 `|P|` 调制，已选行动只获得少量惯性调制。调制不改变 selected 标记，
但会改变当前 tick 的 C* 能量计算和审计曲线。

## 4. 审查要点

1. carryover 只读 StatePool 已有能量，不读 teacher answer，不从文本关键词推答案。
2. carryover 可以提高已有 candidate 的 support，但不能凭空生成 B candidate。
3. unknown tick 仍不能出现 fake B。
4. Stage0 仍无 C* completion/carryover。
5. 后继 tick 的 `feelings.cstar_statepool_carryover`、`c_forward`、`c_backward`、
   `action_competition` 必须能白箱看到这条因果链。

## 5. 验收标准

1. 观察 tick 之后的 StatePool V 会作为 observation support bias 进入 exact/structural B 的 support terms。
2. 第一轮预测写入后，下一写入 tick 的 `c_forward` 包含
   `statepool_virtual_prediction_carryover`。
3. 同一 tick 的 `c_backward` 包含 `statepool_virtual_pressure_carryover`。
4. 后继 tick 的 action competition 中至少一个行动带有
   `cstar_carryover_drive_delta > 0`。
5. unknown weak tick 不创建 fake B，不创建 reply candidate。
6. 指定 Phase20.7/20.8 回归链通过，红线扫描无命中。

