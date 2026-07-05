# Phase20.8h 统一 C* 最小误差整合设计

日期: 2026-06-27

## 1. 设计目标

Phase20.8g 已让 exact B0 索引回读与 weak B/C 默认补齐进入统一候选审计。本阶段继续推进 C*:

```text
B evidence
C_forward prediction
C_backward attribution
UnifiedExperienceCandidate statistics
Action competition
        -> same C* min-error integration formula
        -> cstar_packet
```

目标不是新增一个 C* 模块, 而是把每 tick 已存在的 B/C/行动证据统一归一化, 让 `cstar_packet` 不再只是展示若干统计字段, 而是给出同一套可审计的 `E_forward`、`E_backward`、`E_b`、`E_action`、`E_conflict`、`E_total` 与 `grasp`。

## 2. 白皮书约束

1. C* 是 C_forward 与 C_backward 叠加、裁剪、归一化后的唯一回灌包。
2. B 是现状认知波, 不能直接当回灌; B 只作为 C* 整合的证据来源。
3. 每 tick 都应有预测和归因, 熟悉场景可以低显性, 但不能跳过。
4. 索引和候选统计是审计与加速层, 不是真相源。
5. 本阶段不新增数据库表、不新增认知实体、不新增 keyword/regex/answer table/hidden solver/student-side LLM。

## 3. 数学形式

令:

```text
S_b      = support(B or weak_tick_evidence_B)
S_f      = max support(C_forward)
S_bwd    = max grasp(C_backward)
S_u      = max support(UnifiedExperienceCandidate slots)
D_action = selected_action_drive
H_conf   = action_competition_entropy
```

误差:

```text
E_forward  = 1 - S_f
E_backward = 1 - S_bwd
E_b        = 1 - max(S_b, S_u)
E_action   = 1 - D_action
E_conflict = H_conf

E_total =
  0.30 * E_forward
+ 0.30 * E_backward
+ 0.18 * E_b
+ 0.12 * E_conflict
+ 0.10 * E_action
```

整合把握:

```text
grasp = 1 - E_total
```

C* 虚能量审计量:

```text
Cstar_virtual_energy =
  max(S_f, S_bwd, S_u, S_b) * (1 - 0.35 * H_conf)
```

方向权重:

```text
alpha_forward  = S_f   / (S_f + S_bwd + eps)
alpha_backward = S_bwd / (S_f + S_bwd + eps)
```

这些字段进入 `cstar_packet.cstar_min_error_integration`。同时为了兼容 UI 和旧测试, top-level 继续保留 `grasp`、`e_forward`、`e_backward`、`conflict_entropy`, 并新增 `e_total`、`cstar_formula_id`、`cstar_virtual_energy`。

## 4. 审查完善点

1. 已有 `bccstar_stage3_packet` 要保留原始 packet kind 与已有 `support_formula`, 但必须补入统一 C* 整合公式。
2. default weak C* 不得生成假 `b_candidates`, 只能使用 `tick_evidence_b` 与已有审计槽。
3. `candidate_count=0` 时不把候选缺失当作新候选, 只体现为 `E_b` 由 weak B 支撑。
4. Stage0 仍不补 C*。

## 5. 验收标准

1. exact B0 recall tick 的 `cstar_packet.cstar_formula_id == apv3_phase20_8h_cstar_min_error/v1`。
2. structural B tick 保留 `support_formula`, 且新增统一 `cstar_min_error_integration`。
3. unknown/default weak tick 有统一 C* 整合字段, 但仍没有 `b_candidates`。
4. 每个非 Stage0 cognitive tick 都有 `e_total`、`cstar_virtual_energy`、`alpha_forward`、`alpha_backward`。
5. Phase20.7/20.8 指定回归链通过。
6. 红线扫描无命中。
