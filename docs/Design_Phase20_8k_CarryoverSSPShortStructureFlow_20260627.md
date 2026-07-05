# Phase20.8k C* Carryover 下沉 SSP 短期结构流设计

日期: 2026-06-27

## 1. 目标

Phase20.8j 已证明 StatePool 中的 C* `V/P/replay` 可以影响后继 tick 的
B/C/C* 与 action competition。Phase20.8k 继续把这条后继效应下沉到 SSP /
ExperienceFlow 的 occurrence/edge 层，让它不只是 runtime 内的场调制，而是成为
可回放、可追溯、可被后继 idle_think 沿着边继续的短期结构流。

目标链条：

```text
tick t: C* -> StatePool.V/P/replay
tick t+1: carryover -> B/C/C*/action modulation
tick t+1: carryover -> SSP cognitive occurrences + short_structure_next edge
tick t+2: idle_think / later recall can see previous short_structure_flow
```

## 2. 白皮书约束

1. 不新增数据库表，不新增答案表，不新增关键词/正则路由。
2. 不把 SSP flow 当成回复来源；它只能是 AP 认知流的证据。
3. occurrence/edge 是已有 AP 基础实体，可以承载短期结构池的线性、时序、
   预测、归因关系。
4. carryover flow 的能量来自 StatePool 的 `V/P/replay`，不能伪装为外部实能量。
5. idle_think 的叙事化想法必须写入短期结构流，而不是只写 UI 文本或 payload。

## 3. 数学形式

对上一阶段的 carryover top slots：

```text
carry_i = f(V_i, A_i, |P_i|, replay_i)
```

写入 SSP：

```text
source_occ_i:
  sa_type = original SA id
  R = 0
  V = carry_i
  A = carry_i * 0.42
  P = -carry_i

flow_occ:
  sa_type = short_structure_flow::cstar::{hash(top_slots)}
  R = 0
  V = max(carry_i)
  A = total_carry
  P = -max(carry_i)

edge(source_occ_i -> flow_occ):
  edge_type = cstar_carryover_to_short_flow
  weight = carry_i
```

与上一条短期结构流连接：

```text
edge(previous_flow_occ -> flow_occ):
  edge_type = short_structure_next
  weight = min(1, previous_support * current_support)
```

idle_think 叙事也写入同一类 flow occurrence：

```text
idle_flow_occ:
  sa_type = short_structure_flow::idle::{hash(narrative_text)}
  R/A/P = unfinished pressure and narrative salience
  edge(previous_flow_occ -> idle_flow_occ) = short_structure_next
```

## 4. 审查要点

1. `cstar_carryover_flow` 只由已有 StatePool carryover 生成，不读取 teacher answer。
2. `short_structure_next` 只表达时序和后继偏置，不直接决定回复。
3. unknown weak tick 可以写 flow，但不能制造 fake B。
4. Stage0 无 SSP carryover flow。
5. idle_think 的叙事文本继续保持 private thought，不进入 chat reply。

## 5. 验收标准

1. exact/structural B 的后继 write tick 会写入 `cstar_carryover_to_short_flow`
   edge 和 `short_structure_flow::cstar::*` occurrence。
2. 连续后继 tick 会形成 `short_structure_next` edge。
3. idle_think tick 会写入 `short_structure_flow::idle::*` occurrence，并在重复 idle
   时沿 `short_structure_next` 延续。
4. RuntimeTickEvent 的 `ssp_active_summary` 能看到对应 occurrence/edge refs。
5. 不出现 answer table / direct reply / hidden solver / student-side LLM 等红线命中。

