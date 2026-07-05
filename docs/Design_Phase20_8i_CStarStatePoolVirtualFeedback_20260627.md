# Phase20.8i C* 按 SA 粒度回灌 StatePool 设计

日期: 2026-06-27

## 1. 设计目标

Phase20.8h 已经让 C* packet 具备统一最小误差审计公式, 但它还主要停留在 tick 回放字段。Phase20.8i 的目标是把 C* 的虚能量真正写回当前 `StatePoolItem.V`, 让后续 tick 的状态池快照能看到 C* 影响。

目标路径:

```text
Runtime tick B/C/C*
  -> C* virtual energy
  -> target SA slots
  -> StatePoolItem.V += virtual_energy
  -> StatePoolItem.P = R - V
  -> StatePool snapshot / later tick
```

## 2. 白皮书约束

1. C* 是唯一回灌包。B 不是回灌对象, 只提供证据。
2. 回灌必须落在 SA/occurrence 粒度, 不能直接改 `reply_text`。
3. 回灌使用虚能量 `V`, 不能伪装成外部 `R`。
4. 允许使用已有 `memory_prediction` SA 表达后继预测, 因为旧 Stage3 已经用它承载 structural B 的预测字符。
5. 当前 observation 的已存在 text SA 可以接收解释/归因方向的虚能量。
6. 不新增数据库表、不新增 answer table、keyword/regex route、hidden solver、student-side LLM。

## 3. 落地边界

本阶段只做 runtime 内存中的 StatePool 回灌, 不做:

- 持久化新表。
- L1/L2/L3 在线嵌入更新。
- 六阶段学习协议状态机。
- 直接改变回复选择。
- 视觉 object-centric 细粒度 part codebook。

## 4. 数学形式

使用与 Phase20.8h 同源的支持量:

```text
S_forward  = support(C_forward or predicted output units)
S_backward = grasp(C_backward)
S_action   = selected action drive
H_conf     = action competition entropy

Cstar_V = max(S_forward, S_backward, S_action) * (1 - 0.35 * H_conf)
```

方向分配:

```text
alpha_forward  = S_forward  / (S_forward + S_backward + eps)
alpha_backward = S_backward / (S_forward + S_backward + eps)
```

目标槽:

```text
forward slots:
  predicted output chars -> memory_prediction::hash(char)::index

backward/current slots:
  current utterance SA    -> text_utterance::{signature}
  current text unit SA    -> text_unit::{hash(char)}
```

能量注入:

```text
target.V += slot_energy
target.A += slot_energy * 0.35
target.P  = target.R - target.V
target.gain_ledger.replay += slot_energy
```

如果目标 SA 不存在:

- `memory_prediction` 可创建, 但只以很低 `R=0.01` 作为 carrier, 主要能量仍进入 `V`。
- 当前 observation text SA 不新建, 因为它应当已经由 text receptor 写入; 若不存在则跳过。

## 5. 审查完善点

1. 旧 `_inject_cstar_virtuals(...)` 只支持 structural B。20.8i 必须收束为通用 `_apply_cstar_statepool_feedback(...)`。
2. structural B 不能双重注入。旧调用必须去掉, 由 `_tick_event(...)` 统一调用。
3. exact B0 也应有后继预测虚能量, 但这不改变它是否回复, 只改变 StatePool V。
4. unknown/weak tick 不能制造回答候选, 但可让当前 observation SA 获得低量解释性 V。

## 6. 验收标准

1. structural B tick 的 `memory_prediction` SA 仍进入 `state_pool_top`, 且 `V > 0`。
2. exact B0 tick 也会产生 `memory_prediction` SA 虚能量回灌。
3. unknown weak tick 没有 `b_candidates`, 但当前 text SA 的 `V > 0`, 且不会生成 reply candidate。
4. tick feelings 中包含 `cstar_statepool_feedback` 审计字段。
5. Phase20.7/20.8 指定回归链通过。
6. 红线扫描无命中。

## 7. 审查补充：预测 occurrence 的显著性下限

落地自审时发现一个边界问题：C* 已经把 forward prediction 写入 `memory_prediction`
SA 的 `V`，但如果把同一轮 C* virtual energy 机械平均到多个预测字符，structural B
的每个预测 occurrence 会被摊薄到 `state_pool_top` 之外。这样并不违反“已经写入
StatePool”，但会让白箱审计看起来像预测没有进入认知场。

按 AP 白皮书语义，预测不是一份全局物质量被字符平均瓜分，而是每个被 C* 选中的
occurrence 都拥有自己的虚能量显著性。一个有把握的 B/C/C* 匹配，应该能在后继预测
SA 上留下可被注意力看见的 `V/P/A` 痕迹。因此落地时对 leading prediction window
保留一个由 `b_support` 调制的 occurrence-level 下限：

```text
slot_V = clamp(
  max(forward_budget / n, b_support * 0.18, 0.02),
  0.0,
  0.32
)
```

这个修正不新增实体、不创建回复候选、不改 `reply_text`，只保证已经进入 C* 的
预测 occurrence 在 StatePool 审计视图中不是“数学上存在、白箱上不可见”的幽灵量。
