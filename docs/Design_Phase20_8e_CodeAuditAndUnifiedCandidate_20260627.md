# Phase20.8e 代码级审计与统一经验候选设计

日期: 2026-06-27

## 1. 设计目标

本阶段不是继续堆 UI 或增加识别捷径，而是回答一个底层问题:

当前 Phase20.7/20.8 runtime 是否真的在向 AP 白皮书要求的主流程收束，而不是靠最后图片、答案表、标签表或局部 helper 假装能力?

Phase20.8e 的目标是:

1. 做一次代码级红线审计。
2. 将 `ExperienceRecallCandidate` 与 `ExperienceFlowCandidate` 收束到同一种 `UnifiedExperienceCandidate`。
3. 将 alignment 经验和 recent structure flow 的 support 统一到同一个可审计公式。
4. 让视觉想象 tick、近期归因 tick 都显示统一候选槽。
5. 明确哪些能力已经可证明，哪些仍不能声称完成。

## 2. 审查结论

代码审计结论:

- 没有发现 Phase20.7 runtime 中使用 `visual_environment_frame_payload`、`environment_frame`、`label_map`、`answer_table`、`hidden_solver`、`student_side_llm` 等红线 marker。
- 视觉想象路径仍以 visual patch payload refs 为来源，`raw_source_asset_used_for_render` 保持 false。
- 旧的 alignment helper 与 recent flow helper 仍存在，但已经开始通过统一候选入口进入同一个候选集合，不再各自私下决定。
- 六阶段学习协议、L1/L2/L3 在线嵌入、完整范式自学习、列竖式数学、画板行动范式尚未贯通，不能声称完成。

## 3. 数学与数据结构

新增统一候选:

```python
UnifiedExperienceCandidate(
    candidate_id,
    candidate_kind,
    event_id,
    source_kind,
    text_signature,
    visual_signature,
    occurrence_ids,
    edge_ids,
    payload_refs,
    alignment_event_id,
    support,
    support_terms,
    support_formula,
)
```

统一 support 公式:

```text
support =
  0.30 * structural_similarity
  + 0.62 * visual_similarity
  + 0.18 * exact_text
  + 0.24 * exact_input
  + 0.08 * open_reference
  + 0.62 * occurrence_energy
  + 0.18 * recency
  + 0.08 * payload_presence
  + 0.10 * modality_match
  + 0.12 * reward
  - 0.12 * punish
```

审计字段:

- `support_formula = apv3_phase20_8e_unified_support/v1`
- `support_terms`
- `occurrence_count`
- `edge_count`
- `payload_ref_count`
- `alignment_event_id`

这不是新增认知实体，只是把已有经验流候选包装成同一种候选证据对象。

## 4. 落地策略

新增文件:

- `apv3test/runtime/phase20_7/experience_candidate.py`

修改文件:

- `experience_recall.py`: alignment candidate 使用统一 support 公式并携带 `support_terms`。
- `experience_flow.py`: recent flow candidate 使用统一 support 公式并携带 `support_terms`。
- `runtime.py`: 增加 `_unified_experience_candidates_for_observation(...)` 和 `_unified_experience_candidates_for_input_signature(...)`。
- `vision.py`: `visual_imagination_recall` tick 接收并写出统一候选审计槽。
- `tests/test_phase20_8e_code_audit_and_unified_candidate.py`: 新增专项测试。

## 5. 关键行为

文本触发视觉想象:

```text
text occurrence -> unified candidates -> experience_alignment -> visual patch refs -> inner picture
```

近期指代归因:

```text
"刚刚图片是啥" -> recent structure flow candidates -> recent_visual_window -> C_backward cause slot
```

idle successor:

```text
unclosed source signature -> unified alignment candidates -> successor continuation
```

## 6. 阶段边界

本阶段可以证明:

- 候选层已出现统一候选类型。
- alignment 和 recent flow support 已统一到同一个审计公式。
- 视觉想象 tick 能显示支撑它的统一候选。
- 近期视觉指代能显示 `recent_visual_window` 统一候选。
- 内心画面仍由 patch payload refs 重建，不读最后原图资产。

本阶段不能证明:

- 六阶段学习协议已经贯通。
- L1/L2/L3 在线嵌入已经真实收敛。
- 任意模态任意距离归因已经完成。
- 黄色苹果已经达到 object-centric 的轮廓/颜色拆分生成。
- 数学列竖式、画板动作范式、完整范式自学习已经完成。

下一阶段应继续把旧 helper 的消费逻辑迁移为统一候选的 B/C/C* 心脏，而不是另起识别模块。
