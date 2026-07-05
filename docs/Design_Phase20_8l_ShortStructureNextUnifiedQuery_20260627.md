# Phase20.8l short_structure_next 接入统一 ExperienceFlow Query 设计

日期: 2026-06-27

## 1. 目标

Phase20.8k 已经把 C* carryover 和 idle_think 叙事写入 SSP occurrence/edge，
并形成 `short_structure_next`。Phase20.8l 的目标是让这些边不只可回放，而是被统一
ExperienceFlow query 读到，进入后继 tick 的 B/C/C* candidate 统计。

目标链条：

```text
short_structure_flow occurrence + short_structure_next edge
  -> query_recent_experience_flow_candidates()
  -> ExperienceFlowCandidate(candidate_kind=short_structure_flow_next)
  -> UnifiedExperienceCandidate
  -> B/C/C* unified_candidate_statistics / C_backward cause_slots
```

## 2. 白皮书约束

1. 不新增数据库表。
2. 不让短期结构流直接写 reply。
3. `short_structure_next` 只表达时序、预测、归因偏置，不是答案路径。
4. query 层只能把已有 occurrence/edge 转成候选证据，不能凭空创建 candidate。
5. unknown weak tick 可以看见 flow candidate，但不能生成 fake B 或 reply candidate。

## 3. 数学形式

对每条 `short_structure_next`：

```text
edge_support = clamp(edge.weight * 0.45 + edge.learned_weight * 0.25)
src_energy   = mean(|R| + |V| + |A| + |P| + clarity) / 5
dst_energy   = mean(|R| + |V| + |A| + |P| + clarity) / 5
recency      = 1 / (1 + recency_rank)

support = unified_support(
  occurrence_energy=max(src_energy, dst_energy),
  recency=recency,
  modality_match=1,
  structural_similarity=edge_support
)
```

候选 payload：

```text
{
  "flow_edge_type": "short_structure_next",
  "source_occurrence_id": src,
  "target_occurrence_id": dst,
  "source_text": src_hint,
  "target_text": dst_hint,
  "text": src_hint + " -> " + dst_hint,
  "is_private_thought": true/false
}
```

## 4. 审查要点

1. `ExperienceFlowCandidate` 的 `source_kind` 为 `short_structure_flow_next`。
2. `candidate.audit_slot()` 里能看到 `candidate_kind=short_structure_flow_next`。
3. 它可以进入 C_backward cause slots 和 C* unified_candidate_statistics。
4. 它不能创建 `experience_alignment`，不能写 exact_b0_index，不能生成 output_chars。
5. Stage0 不参与。

## 5. 验收标准

1. 写入 20.8k flow 后，后继 query 能返回 `short_structure_flow_next` candidate。
2. 后继 tick 的 C* `unified_candidate_statistics.candidate_kinds` 包含
   `short_structure_flow_next`。
3. C_backward cause slots 包含 `unified_experience_flow_candidate` 和
   `unified_experience_candidate`。
4. unknown weak tick 仍无 B candidates，无 fake reply。
5. 20.7/20.8 回归链通过，红线扫描无命中。

