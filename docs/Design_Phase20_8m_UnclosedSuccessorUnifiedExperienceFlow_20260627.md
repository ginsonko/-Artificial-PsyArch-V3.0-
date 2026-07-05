# Phase20.8m 未闭合 idle_think 后继收束统一 ExperienceFlow Query 设计

日期: 2026-06-27

## 1. 目标

Phase20.8l 已经让 `short_structure_next` 进入统一 ExperienceFlow query，并进入
C_backward / C* candidate statistics。Phase20.8m 的目标是继续收束 idle_think：
`_successor_for_unclosed(...)` 不再只看 alignment/input_signature，而是从统一
ExperienceFlow/UnifiedCandidate 中竞争出后继，使未闭合感驱动的叙事续写从同一套
B/C/C* 信息流中长出来。

## 2. 白皮书约束

1. 不新增数据库表，不新增答案表，不新增关键词/正则路由。
2. idle successor 只影响 private thought 的叙事续写，不直接写 `reply_text`。
3. alignment、recent flow、short_structure_flow_next 都只是候选证据，不能绕过 AP 主流程。
4. 未闭合感可以沿经验后继继续想，也可以沿短期结构流继续想；二者用 support 竞争。
5. unknown weak tick 可以有短期结构候选，但不能 fake B。

## 3. 数学形式

候选集合：

```text
S = alignment_by_input_signature(source_signature)
  ∪ recent_experience_flow(session_id)
```

候选后继文本：

```text
alignment: output_chars -> output_text
short_structure_flow_next: payload.target_text or payload.text
idle/flow window: candidate.text
```

竞争：

```text
score = support
      + 0.06 * is_same_source_signature
      + 0.05 * is_short_structure_flow_next
      + 0.04 * has_output_text
```

输出：

```text
successor = {
  output_text,
  support,
  source_kind,
  candidate_id,
  support_formula,
  cause_slots,
  writes_answer_directly: false
}
```

## 4. 审查要点

1. successor 只用于 idle private thought / C_forward，不进入 chat reply。
2. `_successor_for_unclosed(...)` 不能写 exact_b0_index。
3. flow successor 可以来自 `short_structure_flow_next`，但必须保留主观、可错、可被后续中和的性质。
4. 旧 alignment 成功路径仍保留，避免破坏 Stage4 teacher feedback resolve。
5. Stage0 不参与。

## 5. 验收标准

1. 教学后未闭合 idle_think 仍能沿 alignment successor 续写。
2. 连续 idle_think 能沿 `short_structure_flow_next` successor 续写。
3. idle C_forward `idle_successor_continuation` 标明 unified successor source。
4. successor 不写聊天回复，`reply_text == ""`。
5. unknown / weak 路径不创建 fake B。
6. 20.7/20.8 回归链通过，红线扫描无命中。

