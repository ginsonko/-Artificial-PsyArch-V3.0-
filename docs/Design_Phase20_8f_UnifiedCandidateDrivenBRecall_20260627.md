# Phase20.8f 统一候选驱动 B 召回设计

日期: 2026-06-27

## 1. 设计目标

Phase20.8e 已经把 alignment 经验和 recent structure flow 包装成 `UnifiedExperienceCandidate`，并统一了 support 公式。但两个关键 B 召回路径仍有残留:

- `_find_structural_b(...)` 仍直接消费 alignment candidate 并单独计算 structural support。
- `_select_alignment_by_backward_neutralization(...)` 仍直接消费 alignment candidate 并单独计算 visual support。

Phase20.8f 的目标是把这两条路径继续收束:

```text
UnifiedExperienceCandidate
  -> structural B interpretation
  -> visual backward neutralization interpretation
  -> B/C/C* trace
```

这不是新增模块，而是把旧 helper 的候选来源改为同一个候选池。

## 2. AP 哲学约束

1. 不新增答案表、标签表、图片专用路线。
2. 不让 structural B 或 visual B0 跳过统一候选 support。
3. exact / structural / visual recall 可以是不同解释方式，但候选来源必须统一。
4. C_backward 要能显示候选来源、support formula、support terms。
5. 不能声称完整六阶段、L1/L2/L3、范式自学习已经完成。

## 3. 数学形式

对任意 `UnifiedExperienceCandidate u_i`:

```text
B_structural(u_i | q_t):
  source_text = input_event(u_i).text
  sim_seq = structural_similarity(q_text, source_text)
  sim_vis = visual_similarity(q_visual, u_i.visual_signature)
  support = unified_support(
      structural_similarity = sim_seq,
      visual_similarity = sim_vis,
      reward/punish = already reflected by u_i support terms
  )
  final_support = max(support, u_i.support * source_alignment_gate)
```

对视觉反向中和:

```text
B_visual(u_i | q_t):
  sim_vis = visual_similarity(q_visual, u_i.visual_signature)
  exact_text = q_text_signature == u_i.text_signature
  open_ref = visual_reference_family
  support = unified_support(sim_vis, exact_text, open_ref)
```

候选被选中后，`B`、`C_backward`、`C*` 里都应出现:

- `support_formula`
- `support_terms`
- `unified_experience_candidate` audit slot

## 4. 落地策略

1. 扩展 `_ExactB0` 和 `_StructuralB`，保留统一候选审计槽。
2. `_find_structural_b(...)` 改为遍历 `_unified_experience_candidates_for_observation(...)`。
3. `_select_alignment_by_backward_neutralization(...)` 改为遍历 `_unified_experience_candidates_for_observation(...)`。
4. `_tick_event(...)` 的 `b_candidates`、`c_backward`、`cstar_packet` 写出统一候选审计字段。
5. 新增 Phase20.8f 专项测试，验证结构 B 与视觉 exact B0 均显示统一候选来源。

## 5. 验收标准

1. Stage3 structural B 行为不回归。
2. Stage5 visual exact B0 行为不回归。
3. structural B 的 `b_candidates` 中出现 `support_formula` 和 `support_terms`。
4. visual exact B0 的 `c_backward.cause_slots` 中出现 `unified_experience_candidate`。
5. 红线扫描无命中。
6. Phase20.7/20.8 指定全量回归通过。
