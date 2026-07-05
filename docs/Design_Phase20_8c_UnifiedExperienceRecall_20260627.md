# Phase20.8c 统一 ExperienceFlow / SSP 结构召回接口设计

日期: 2026-06-27

## 1. 设计目标

Phase20.8b 已让每个认知 tick 都拥有统一 B/C/C* 审计包, 但 B/C 的候选来源仍分散在多个 helper:

- `_find_structural_b(...)`
- `_select_backward_attribution(...)`
- `_select_alignment_by_backward_neutralization(...)`
- `_select_visual_imagination_recall(...)`

这些 helper 都在扫描 `experience_alignment`, 只是各自重复实现了候选读取、tombstone 过滤、文本/视觉结构展开、reward/punish 偏置和相似度计算。

Phase20.8c 的目标是先建立统一候选层:

```text
Observation / Query
  -> query_experience_alignment_candidates(...)
  -> ExperienceRecallCandidate[]
  -> helper 只做门槛、用途选择、返回结构适配
```

本阶段不直接重写全部召回策略, 而是先把“经验流扫描与结构候选构造”收束为唯一入口, 让后续 Phase20.8d 能继续把 B/C/C* 的真正数学心脏迁入这一层。

## 2. AP 哲学约束

1. 统一召回接口只读 AP 经验流, 不读原始图像、不读文件名、不读标签表。
2. 候选是主观相似经验, 允许错, 后续通过反馈修正。
3. 文本、视觉、组合想象、反向归因都通过同一候选结构表达。
4. 不改变 reply 生成结果, 不引入 hidden solver, 不引入 LLM。
5. 不把“弱证据”伪装成真实召回。只有来自经验流的 alignment 才是 recall candidate。

## 3. 候选结构

新增:

```python
@dataclass(frozen=True)
class ExperienceRecallQuery:
    query_text: str
    text_signature: str | None
    visual_signature: str | None
    input_signature: str | None
    open_reference: bool
    exact_input_allowed: bool

@dataclass(frozen=True)
class ExperienceRecallCandidate:
    alignment_event_id: str
    payload: dict
    input_event_id: str
    output_text: str
    output_chars: tuple[str, ...]
    source_text: str
    reward: float
    punish: float
    text_score: float
    text_coverage_units: tuple[str, ...]
    visual_score: float
    exact_text_match: float
    exact_input_match: bool
    visual_reference_family: bool
    support: float
```

其中 `support` 是通用候选支持度, 不是最终 action drive。各用途仍可按需要增加门槛:

- exact B0 使用 `exact_input_match`
- structural B 使用 `text_score / shared_units / residual_units`
- visual exact 使用 `visual_score`
- visual imagination 使用 `text_coverage_units + visual_signature`

## 4. 数学形式

候选 \(m_i\) 对当前 query \(q_t\) 的基础支持:

\[
s_i =
w_t \cdot sim_T(q_t,m_i)
+ w_v \cdot sim_V(q_t,m_i)
+ w_e \cdot exact(q_t,m_i)
+ w_r \cdot reward_i
- w_p \cdot punish_i
+ w_o \cdot openRef(q_t,m_i)
+ w_{\tau} \cdot recency_i
\]

本阶段默认:

- 文本结构相似来自 `_semantic_text_overlap_with_units`
- 视觉结构相似来自 `_visual_evidence_neutralization`
- recency 只作为弱偏置, 不允许压过结构证据

## 5. 落地步骤

1. 新增 `experience_recall.py`。
2. 迁移候选扫描逻辑。
3. `_find_structural_b(...)` 改为消费统一候选。
4. `_select_alignment_by_backward_neutralization(...)` 改为消费统一候选。
5. `_select_visual_imagination_recall(...)` 改为消费统一候选。
6. 保留现有行为门槛, 用测试确认不漂移。

## 6. 审查结论

该方案是“收束入口”, 不是“新增答案模块”。它符合 AP 主流程, 因为经验流候选本来就是 B/C 的共同来源; 本阶段只是把重复扫描合并, 并让后续所有归因/预测能继续往同一数学接口内硬化。
