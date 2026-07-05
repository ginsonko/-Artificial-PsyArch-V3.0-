# Phase20.8d 统一短期结构流 + 经验流候选层设计

日期: 2026-06-27

## 1. 设计目标

Phase20.8c 已经把 `experience_alignment` 的扫描收束为统一候选入口, 但它仍主要是 alignment 候选层。AP 白皮书要求的真正心脏不是“只找问答 alignment”, 而是:

```text
当前短期结构池 / 状态池
  -> 与近期 occurrence/edge/patch/audio/action/teacher feedback/experience alignment 共同结构对齐
  -> B/C/C* 预测与归因
```

Phase20.8d 的目标是把以下来源统一成同一种候选:

- experience alignment
- recent text / visual / audio / idle events
- occurrence / structure edge
- visual patch payload refs
- unclosed successor source

新增统一结构:

```python
ExperienceFlowCandidate
```

它不直接回答, 只表示“当前 tick 可以召回/归因/预测的经验片段”。

## 2. AP 哲学约束

1. 统一候选必须从 AP 经验流和短期结构流中产生, 不能读原始资产、文件名或标签表。
2. 候选可以来自近期窗口, 因为人类“刚刚那个”就是短期结构流追溯。
3. 候选可以来自 alignment, 因为教学共现是经验流的一部分。
4. 候选可以来自 visual patch payload, 但只作为已采样视觉 SA 的 payload, 不能作为整图缓存。
5. 统一候选层不修改 reply_text, 不写答案, 不执行行动。

## 3. 候选结构

```python
@dataclass(frozen=True)
class ExperienceFlowCandidate:
    candidate_id: str
    candidate_kind: str
    event_id: str
    tick: int
    source_kind: str
    text: str
    text_signature: str | None
    visual_signature: str | None
    occurrence_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    payload_refs: tuple[str, ...]
    alignment_event_id: str | None
    support: float
    cause_slots: tuple[dict, ...]
```

候选类型:

- `alignment`
- `recent_text_window`
- `recent_visual_window`
- `recent_audio_window`
- `idle_think_window`
- `visual_patch_payload`

## 4. 落地策略

本阶段先做最小可验证迁移:

1. 新增 `experience_flow.py`。
2. 从 event/occurrence/edge/payload 表构造 `ExperienceFlowCandidate`。
3. `query_experience_alignment_candidates(...)` 继续保留, 但可被 flow candidate 包装为 `alignment`。
4. `_recent_experience_windows(...)` 改为消费 flow candidates, 不再自己直接扫描 text/visual 事件。
5. `_patch_payload_refs_for_alignment(...)` 的 fallback 改为从 flow candidates 中找 visual patch payload。
6. `RuntimeTickEvent.cstar_packet` 可记录 flow candidate 统计, 用于白箱审计。

## 5. 数学形式

对候选 \(f_i\):

\[
support(f_i|q_t) =
w_r R_i + w_v V_i + w_a A_i + w_p P_i
+ w_s sim_{structure}(q_t, f_i)
+ w_\tau recency_i
+ w_m modality\_match_i
\]

本阶段先使用可编码代理:

- occurrence energy 平均值
- text/visual/audio modality match
- recent recency
- alignment support
- visual patch payload existence

后续 Phase20.8e 再把在线嵌入 L1/L2/L3、图结构对齐、负样本与退火曲线接入。

## 6. 审查结论

这是把现有短期窗口和经验 alignment 收束到同一候选类型, 不是新增认知实体。它符合 AP 白皮书, 因为状态池/短期结构池/经验流本来就是同一个连续过程的不同投影。实现上必须保持保守: 先替换查询入口和审计字段, 不改变输出行为。
