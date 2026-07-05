# APV3 Phase20.7 开放自由对话底座工程数学硬化与落地设计

版本: 2026-06-26 v1a  
状态: Phase20.7 实施前置设计正本, 已补入 Stage 依赖闭合、AP-native 未闭合推导、SQLite provenance、RuntimeTickEvent 审计链、完整发布 demo 与自审结论。  
依据: `AP_Bottom_Principles_Whitepaper_20260626.txt` v0.4、`ColdSave_AP_LatestPhilosophy_RuntimeAndLearningStandard_20260621.md`、`AP_Master_Understanding_Authoritative_20260621.md`、Phase20.6 Stage0 实施报告。  
目标: 把 AP 底层原理白皮书落成可编码、可验收、可复用的 APV3 本地开放中文对话底座。

---

## 0. 总裁定

Phase20.7 的目标不是做一个更会聊天的模板系统, 也不是做一个前端更漂亮的 demo。它的目标是把 APV3 主对话路径重建为:

```text
感受器
  -> StatePool 类型场
  -> ShortStructurePool occurrence 流
  -> 统一经验流与可重建索引
  -> B 现状召回
  -> C_forward 预测 / C_backward 追溯
  -> C* 结构化回灌
  -> 认知感受与情绪慢量
  -> 行动竞争
  -> DraftGrid / 视焦点 / 听觉焦点 / 请求教师 / 停止 / 工具行动
  -> 行动反馈与奖惩
  -> 下一 tick
```

所有 UI、TTS、画布、记忆包、Agent API、桌宠接入、视觉识别、听觉输入都必须是这条闭环的感受器、行动器、索引、审计视图或产品壳。任何直接答案表、独立图片标签表、预生成回复切片、整图 label、隐藏 LLM、关键词规则路由, 都不属于 Phase20.7。

---

## 1. 目标重新定义: 会学的 3-5 岁小孩级自由对话

### 1.1 不是目标

Phase20.7 不追求:

1. 像 LLM 一样已经知道所有话题。
2. 一次输入就输出成人级长篇答案。
3. 用外部 LLM 替 AP 学生侧代答。
4. 用答案表覆盖“不知道”的状态。
5. 用前端假 tick 伪装思考过程。

### 1.2 是目标

Phase20.7 追求:

1. 不会时能诚实表达不确定。
2. 会主动问用户学习。
3. 学过的东西进入统一经验流, 后续 tick/turn 可召回。
4. 能把新知识与旧经验做粗糙但拟人的类比。
5. 能过度泛化、误解、纠正, 并在后天经验中逐渐修正。
6. 能在闲时被未闭合感拉回, 继续想刚才没弄懂的事。
7. 能在多模态中学习: 文本、图片、画板、声音都作为一等公民 occurrence。
8. 能作为本地对话底座被其它项目调用, 返回真实 tick trace、记忆 delta 和行动结果。

### 1.3 3-5 岁级验收定义

这里的“3-5 岁”是行为目标, 不是儿童心理学精确宣称。最低验收:

1. 词汇/短语: 初始可用 2000-3500 个基础词/片段目标, 由种子语料和教学逐步积累。
2. 句长: 默认 3-12 个汉字/词片段, 可有停顿、重复、跑题和自我修正。
3. 学习: 用户教 1-3 次后能在相似上下文中召回, 但允许误泛化。
4. 主动询问: 不懂且有未闭合感时会问, 但有冷却, 不烦人。
5. 闲时思考: 无外部输入时, 能从未闭合对象中选一个做低频 B/C/C* 推演, 并把结果写回经验流。
6. 视觉: 能通过多 tick 视焦点采样形成局部证据, 不靠整图 label。
7. 听觉: 初期至少能把音频作为 audit/节奏/响度/焦点证据进入闭环, 以后升级到识别。
8. 工具/画板: 画板、DraftGrid、键鼠等行动必须有读回反馈。

---

## 2. 当前 Phase20.6 边界

Phase20.6 Stage0 已经有价值:

1. 引入 `phase20_6_runtime.py`。
2. 取消 Phase20 主对话中的整图 `enumerate_objects_in_image` 依赖。
3. 把可见回复提交放到 DraftGrid 后面。
4. RuntimeTickEvent 暴露 recall/action/draft/state/thought 等字段。
5. 记忆包、TTS、画布、录音、教师焦点等已经作为入口出现。

但 Phase20.6 仍不是最终 AP 底座:

1. StatePool 仍偏静态快照, 没有完整能量动力学。
2. SSP occurrence 流不是主数据库真相源。
3. B/C/C* 没有按白皮书的结构召回和回灌实现。
4. DraftGrid 仍需要成为每 tick 行动 substrate, 而不是候选回复的可视化。
5. 视觉内心画面还需要 patch payload、clarity field、R/V sketch 和 source mask。
6. 闲时未闭合思考、主动询问、拟人放弃、反例松动还未形成可验收闭环。

所以 Phase20.7 必须是核心重建, 不是 Phase20.6 UI 修补。

---

## 3. 核心数据结构

### 3.1 SAType

SAType 是认知对象类型投影, 不是一次发生。

```python
SAType(
    sa_type_id: str,
    substrate: Literal["text", "vision", "audio", "draft_grid", "action", "affect", "tool", "reward", "punish"],
    modality: str,
    canonical_hint: str | None,
    vector_l1: bytes | None,
    vector_l2: bytes | None,
    vector_l3: bytes | None,
    created_tick: int,
    updated_tick: int,
)
```

约束:

1. `canonical_hint` 只用于 UI 可读提示, 不能作为答案路由。
2. 文本 SA 可按需细化, 初次可整句, 后续由预测误差切分。
3. 视觉 SA 最低分辨率是像素/patch, 可向形状、纹理、颜色、部件逐步形成 type。
4. 听觉 SA 最低分辨率是周期/频段, 可逐步形成节奏、音素、词、声线 type。

### 3.2 StatePoolItem

StatePool 是无序类型场。

```python
StatePoolItem(
    sa_type_id: str,
    R: float,
    V: float,
    A: float,
    F: float,
    P: float,
    latest_occurrence_id: str | None,
    supporting_occurrence_ids: list[str],
    dominant_structure_id: str | None,
    source_tags: list[str],
)
```

含义:

1. R: 实能量。
2. V: 虚能量。
3. A: 注意能量。
4. F: 疲劳/重复抑制。
5. P = R - V: 认知压方向量。

StatePool 可以聚合同一 type 的多 occurrence, 但重复感、计数感、空间位置、顺序不能由 StatePool 聚合字段决定, 必须由 SSP occurrence 结构决定。

### 3.3 ShortStructurePool

SSP 是 occurrence 结构流, 是短期认知真相源。

```python
Occurrence(
    occurrence_id: str,
    sa_type_id: str,
    tick: int,
    substrate: str,
    position: StructurePosition,
    R: float,
    V: float,
    A: float,
    P: float,
    clarity: float,
    source_ref: str | None,
    payload_ref: str | None,
)

StructureEdge(
    src_occurrence_id: str,
    dst_occurrence_id: str,
    edge_type: Literal["temporal", "spatial", "draft_grid", "audio_time", "causal_hypothesis", "repeat_candidate", "count_candidate", "self_feedback"],
    weight: float,
    learned_weight: float,
    created_tick: int,
)
```

`StructurePosition` 支持:

1. 文本线性位置。
2. DraftGrid 二维格子。
3. 视觉二维 patch/像素位置。
4. 听觉时间/频段位置。
5. 工具或身体动作的时空位置。

### 3.4 UnifiedExperienceEvent

统一经验流是长期真相源。

```python
ExperienceEvent(
    event_id: str,
    tick: int,
    session_id: str,
    event_kind: str,
    occurrence_deltas: list[OccurrenceDelta],
    state_deltas: list[StateDelta],
    structure_edge_deltas: list[EdgeDelta],
    action: ActionRecord | None,
    reward: float,
    punish: float,
    feeling_vector: FeelingVector,
    emotion_vector: EmotionVector,
    source_packet: SourcePacket,
    created_at_ms: int,
)
```

原则:

1. 核心数据库是 append-only event log。
2. ANN/Zvec/倒排/rolling hash 都是可重建索引。
3. 审计近期快照是旁路, 不参与语义真相。
4. 记忆包导出的是经验流子图 + 索引元数据, 不是答案包。

---

## 4. 工程数学硬化

本节把白皮书中的框架公式硬化为 Phase20.7 默认可编码版本。参数不是最终真理, 是第一版可调初值。所有参数变化都必须进入自适应调参器审计。

### 4.1 能量更新 A1-A3

每 tick 对每个 StatePoolItem:

```text
R_i(t+1) = clamp01(lambda_R_i * R_i(t) + input_R_i + feedback_R_i + verify_R_i)
V_i(t+1) = clamp01(lambda_V_i * V_i(t) + cstar_V_i + imagination_V_i + recall_V_i)
A_i(t+1) = clamp01(lambda_A_i * A_i(t) + attention_boost_i - attention_cost_i)
F_i(t+1) = clamp01(lambda_F_i * F_i(t) + fatigue_input_i - novelty_release_i)
P_i(t+1) = R_i(t+1) - V_i(t+1)
```

默认值:

| 参数 | 默认 | 范围 | 拟人解释 |
|---|---:|---:|---|
| `lambda_R` | 0.82 | 0.65-0.95 | 现实刺激退去后仍短暂留在心里 |
| `lambda_V` | 0.88 | 0.70-0.98 | 预期比现实残影更持久 |
| `lambda_A` | 0.76 | 0.55-0.92 | 注意力会滑走, 但强任务可维持 |
| `lambda_F` | 0.94 | 0.80-0.995 | 疲劳/重复感衰减慢 |

全局 soft budget:

```text
active_mass = sum_i (0.55*R_i + 0.35*V_i + 0.75*A_i)
budget = B_base + B_emotion_boost + B_task_boost - B_fatigue

if active_mass > budget:
    scale_low_attention_items by budget / active_mass
```

默认:

```text
B_base = 36
B_emotion_boost in [0, 12]
B_task_boost in [0, 16]
B_fatigue in [0, 18]
```

这不是固定 Miller 7±2, 而是“高注意对象少、背景对象可多”的拟人预算。

中和与反例松动:

```text
matched_i = min(R_i, V_i) * neutralize_rate
counter_i = unfulfilled_prediction_i + observed_without_predicted_i + failed_action_outcome_i + teacher_correction_i

belief_support_i(t+1) =
    lambda_belief * belief_support_i(t)
  + neutralize_rate * matched_i
  - unlearning_rate * counter_i * contradiction_gate_i
```

默认:

```text
neutralize_rate = 0.18
unlearning_rate = 0.06
lambda_belief = 0.985
contradiction_gate = sigmoid(2.5 * evidence_conflict + 1.5 * source_trust - 1.0)
```

解释: 人更容易相信被验证的经验, 不会被单个反例立刻推翻; 但重复反例和可信纠正会松动信念。

### 4.2 SSP occurrence 流 B1-B3

Occurrence 进入 SSP 的门:

```text
enter_score =
    0.35*R + 0.25*abs(P) + 0.25*A + 0.10*novelty + 0.05*teacher_saliency

enter if enter_score >= theta_ssp
```

默认:

```text
theta_ssp = 0.22
max_active_occurrence = 220
max_high_attention_occurrence = 30
```

若超预算:

```text
evict_score =
    0.45*A + 0.25*abs(P) + 0.15*recency + 0.10*reward_trace + 0.05*unclosed_link

淘汰 evict_score 低者
```

边权更新:

```text
w_e(t+1) =
    clamp01(lambda_edge*w_e(t)
            + coactive_strength
            + reward_credit
            - contradiction_penalty)
```

默认边:

| edge_type | 初始权重 | lambda | 说明 |
|---|---:|---:|---|
| temporal | 0.45 | 0.96 | 线性后继 |
| spatial | 0.40 | 0.97 | 视觉/二维空间 |
| draft_grid | 0.55 | 0.98 | 草稿格关系 |
| audio_time | 0.45 | 0.96 | 音频时间/频段 |
| self_feedback | 0.65 | 0.985 | 自己写出/看回 |
| causal_hypothesis | 0.20 | 0.995 | 拟人伪因果允许形成但慢变 |
| repeat_candidate | 0.35 | 0.96 | 重复/节奏 |
| count_candidate | 0.30 | 0.97 | 数量候选 |

StatePool/SSP 同步 invariant:

```text
StatePool[type_id].supporting_occurrence_ids = top_k SSP occurrences with same type_id by support
StatePool[type_id].R approximately weighted_sum(R_occurrences, recency, attention)
StatePool[type_id].latest_occurrence_id = newest occurrence
```

但:

```text
count(type_id) != StatePool occurrence_count alone
count(type_id) = separable occurrence structure under temporal/spatial/draft/audio edges
```

### 4.3 B / C / C* 召回 C1-C4

当前查询:

```text
Q_t = top_structures(SSP, by=A + abs(P) + U + reward_trace)
```

结构相似度:

```text
sim(Q, H) =
    0.22*type_overlap
  + 0.16*order_alignment
  + 0.14*spatial_alignment
  + 0.12*energy_profile_similarity
  + 0.10*affect_similarity
  + 0.10*source_similarity
  + 0.08*action_context_similarity
  + 0.08*unclosed_goal_similarity
```

权重可由调参器学习, 但必须保持每项可审计。

召回温度:

```text
tau = clamp(0.12, 1.20,
            tau_base + 0.35*(1 - attention_focus) + 0.25*uncertainty - 0.30*grasp_prior)
tau_base = 0.55
```

高注意/高把握时更集中, 低注意/低把握时更弥散。

B 候选:

```text
B_k.weight = softmax(sim(Q,H_k)/tau) * source_trust_k * freshness_gate_k
```

C_forward:

```text
C_forward = propagate(H_k, direction=+1, distance=d_f, decay=lambda_forward)
```

C_backward:

```text
C_backward = propagate(H_k, direction=-1, distance=d_b, decay=lambda_backward)
```

默认:

```text
d_f = 1-8 occurrence steps
d_b = 1-6 occurrence steps
lambda_forward = 0.72
lambda_backward = 0.68
```

C* 结构:

```python
CStarPacket(
    prediction_slots: list[PredictionSlot],
    explanation_slots: list[ExplanationSlot],
    contradiction_slots: list[ContradictionSlot],
    action_affordance_slots: list[ActionAffordanceSlot],
    feeling_inputs: FeelingInputs,
)
```

整合:

```text
slot_score =
    support_sum
  * source_trust
  * recency_gate
  * (1 - fatigue)
  * structure_fit

conflict_entropy = entropy(normalize(slot_scores by mutually exclusive group))
grasp = sigmoid(4.0*(top1_score - top2_score) + 1.5*support_count - 2.0*conflict_entropy)
```

若 `grasp < theta_grasp_low`, 不应硬写答案, 应更倾向观察、询问、低把握表达或闲时继续想。

默认:

```text
theta_grasp_low = 0.42
theta_grasp_commit = 0.62
theta_grasp_firm = 0.78
```

### 4.4 未闭合感与闲时思考 D1-D4

未闭合对象:

```text
U_i(t+1) =
    lambda_U * U_i(t)
  + pressure_from_reward_prediction_i
  + pressure_from_punish_prediction_i
  + pressure_from_innate_rule_i
  + pressure_from_unmatched_Cstar_i
  + pressure_from_interrupted_action_i
  - closure_i
  - release_i
```

默认:

```text
lambda_U = 0.992
theta_idle_think = 0.38
theta_request_teacher = 0.58
```

AP-native 展开:

```text
pressure_from_reward_prediction_i =
    predicted_reward_i * (1 - observed_reward_match_i) * self_action_relevance_i

pressure_from_punish_prediction_i =
    predicted_punish_avoidance_i * (1 - safety_resolution_i) * self_action_relevance_i

pressure_from_innate_rule_i =
    innate_weight(rule_j) * rule_activation_j * reward_or_punish_projection_j

pressure_from_unmatched_Cstar_i =
    abs(P_i) * explanation_gap_i * grasp_gap_i

pressure_from_interrupted_action_i =
    unfinished_action_trace_i * action_commitment_i * affordance_waiting_i
```

约束:

1. `task_pressure` 不是新实体, 只能由 reward/punish 预测、先天规则、C* 预测不验、行动未完成派生。
2. `curiosity` 不是新实体, 是 `pressure_from_unmatched_Cstar` 在先天求知规则和奖惩投影下的表现。
3. 未闭合项必须引用至少一个 `source_event_id`、`prediction_slot_id`、`action_trace_id` 或 `innate_rule_id`; 无来源引用的 U 不允许进入 idle_think。
4. 放弃/解除同样必须有来源: cancellation evidence、impossibility evidence、cost revaluation、source removal、teacher correction 或 pressure source disappearance。

闭合与释放:

```text
closure_i =
    observed_expected_outcome_i
  + observed_expected_action_feedback_i
  + reward_received_i
  + punish_avoided_i

release_i =
    cancellation_evidence_i
  + impossibility_evidence_i
  + cost_revaluation_i
  + source_removed_i
  + teacher_release_i
  + pressure_source_disappeared_i
```

这样 AP 可以像人一样完成一件事, 也可以像人一样放下、取消、改主意或因为条件不具备而暂存。

闲时调度:

```text
if no_external_input and not actuator_busy:
    idle_candidate_i = U_i * (1 - fatigue_i) * recency_gap_i * grasp_gap_i
    choose top candidate with probability softmax(idle_candidate / tau_idle)
```

默认:

```text
tau_idle = 0.35
idle_tick_rate = min(2 tick/s, runtime_budget_remaining)
idle_burst_max = 24 ticks
idle_cooldown_after_user_input = 1500 ms
```

主动询问:

```text
should_ask =
    sigmoid(
        2.0*abs(P_target)
      + 1.8*(1 - grasp_target)
      + 1.3*U_target
      + 0.8*recent_failed_recall
      - 1.4*recent_asked_same_topic
      - 1.0*user_busy_signal
      - 0.7*ask_fatigue
    ) > theta_ask
```

默认:

```text
theta_ask = 0.64
recent_asked_same_topic window = 20 turns
ask_fatigue lambda = 0.97
```

举一反三/抽象槽形成:

```text
abstract_ready =
    support_count >= 3
    and slot_variance <= 0.35 for shared parts
    and difference_energy >= 0.20 for variable parts
    and teacher_or_reward_support >= 1
```

例: “猫是动物”“狗是动物”“兔子是动物”支持 `X 是动物` 槽, 但 `X` 的泛化范围仍低把握, 可问用户确认。

### 4.5 视觉 patch_payload 与内心画面 E1-E3

视觉每 tick 不是整图识别, 而是:

```text
action_competition selects move_focus / maintain_focus / widen_focus
  -> foveated sampling
  -> patch payload
  -> visual occurrence
  -> StatePool/SSP
  -> B/C/C*
```

采样概率:

```text
p_sample(x,y) =
    clamp01(
      p_min
    + (p_focus - p_min) * exp(-dist((x,y), focus)^2 / (2*sigma_focus^2))
    + saliency_boost(x,y)
    + mismatch_boost(x,y)
    + teacher_focus_boost(x,y)
    )
```

默认:

```text
p_min = 0.03
p_focus = 0.92
sigma_focus = 0.14 * image_diag
teacher_focus_boost <= 0.30
```

视焦点候选:

```text
focus_drive(region) =
    0.24*saliency(region)
  + 0.22*mismatch(region)
  + 0.18*unclosed_need(region)
  + 0.14*expected_information_gain(region)
  + 0.12*teacher_focus(region)
  + 0.10*fatigue_release(region)
```

约束:

1. `focus` 必须由 `move_focus` / `maintain_focus` / `widen_focus` 行动竞争给出。
2. teacher focus 只提升 saliency, 不绑定 label。
3. 固定螺旋、固定网格、固定小方块巡航只能作为低优先级先天探索候选, 不能压过 mismatch/U/saliency。

payload 档位:

```text
payload_score = 0.40*A_focus + 0.25*abs(P_patch) + 0.20*teacher_focus + 0.15*novelty
```

| 档位 | 条件 | 保存 |
|---|---|---|
| high | score >= 0.72 | 32x32 或 48x48 RGB patch + mask + V0-V12 |
| medium | 0.42-0.72 | 16x16 RGB + dominant colors + edges + V0/V7/V10 |
| weak | 0.20-0.42 | 8x8 sketch + color/edge summary |
| none | < 0.20 | 只保留结构位置和 saliency |

clarity merge:

```text
clarity_new(x,y) = max(lambda_clarity * clarity_old(x,y), observed_clarity(x,y))
```

默认:

```text
lambda_clarity = 0.965 per visual tick
```

R/V sketch:

```text
inner_pixel =
    normalize(
      R_weight * observed_patch_color
    + V_weight * predicted_patch_color
    )

R_weight = source_confidence * R_patch
V_weight = grasp * V_patch * (1 - contradiction)
```

内心画面必须显示:

1. 焦点附近更清楚。
2. 周边稀疏但非空。
3. 多 tick 后 clarity 累积更丰富。
4. R_sketch 和 V_sketch 来源可审计。
5. 不能直接贴原图缩略图。

性能预算:

```text
max_patch_payload_per_turn = 12 MB initial
max_high_patch_per_visual_tick = 8
max_total_patch_per_visual_tick = 64
```

超预算时通过行动竞争选择 `move_focus_less`, `lower_periphery_sampling`, `request_teacher_focus`, `idle_visual_wait`, 而不是整图 label。

### 4.6 听觉输入与内心音频

Phase20.7 起步三档:

1. `audio_audit_only`: 保存响度、时长、频谱粗图、节奏峰, 不识别语义。
2. `phase19_1_basic`: 周期/频段 SA, 可形成听觉焦点。
3. `phase19_4_recognition`: 后续语音/声线/词学习, 仍走共现与经验流。

音频 occurrence:

```python
AudioOccurrence(
    occurrence_id,
    time_window_ms,
    freq_band,
    loudness_R,
    predicted_loudness_V,
    rhythm_phase,
    payload_ref,
)
```

听觉焦点:

```text
audio_focus_score =
    0.35*loudness_surprise
  + 0.25*rhythm_mismatch
  + 0.20*teacher_audio_focus
  + 0.20*unclosed_audio_link
```

内心音频初期可显示为频谱/节奏 sketch, 不冒充语音识别。

### 4.7 学习信号 F1-F4

奖惩范围:

```text
reward_mag, punish_mag in [0, 1]
signed_valence = reward_mag - punish_mag
effective_feedback(t, target_tick) =
    signed_valence * exp(-(t-target_tick)/tau_feedback)
```

默认:

```text
tau_feedback = 8 ticks for direct correction
tau_feedback = 30 ticks for task outcome
```

对比学习负样本:

```text
positive = target occurrence / corrected occurrence / rewarded action trace
negative = coactive non-target occurrences in same SSP window
hard_negative = high-sim but corrected-away occurrence
```

在线嵌入三层:

| 层 | 目标 | 更新 |
|---|---|---|
| L1 | 感受器局部相似 | patch/token/audio local contrast |
| L2 | 跨模态共现 | text-vision-audio-action coactivation |
| L3 | 行动后果 | state-action-outcome reward/punish |

退火:

```text
lr_l(t) = lr_min + (lr_max-lr_min) * exp(-update_count / tau_lr)
```

默认:

```text
L1 lr_max=0.08 lr_min=0.008 tau=120
L2 lr_max=0.05 lr_min=0.005 tau=200
L3 lr_max=0.04 lr_min=0.004 tau=260
```

source_trust:

```text
source_trust(source, context, modality, t+1) =
    clamp01(lambda_source * source_trust(source, context, modality, t)
      + event_gate * (
          0.08*verified_helpful
        - 0.10*contradicted
        + 0.04*identity_continuity
        + 0.03*teacher_role_signal
        - 0.04*out_of_context_failure
      ))
```

默认:

```text
lambda_source = 0.985
event_gate = 1 only when this source participates in current event, otherwise 0
```

注意:

1. source_trust 是 `source x context x modality` 的局部可信度, 不是全局教师权威标量。
2. source_trust 调制学习强度、召回权重和解释来源透明度, 不直接给答案。
3. teacher_role_signal 只在当前事件有明确教师反馈时参与, 不能每 tick 自动累积。
4. 如果同一 source 在视觉教学可靠, 但在数学教学错误, 两个 context 的 trust 应分开学习。

### 4.8 行动竞争 G1-G3

候选行动:

```python
ActionCandidate(
    action_id,
    action_type,
    target_refs,
    raw_drive,
    eligibility_sources,
    expected_reward_mag,
    expected_punish_mag,
    cost,
    fatigue,
    source_trace,
)
```

eligibility 合并:

```text
eligibility = 1 - product_j(1 - eligibility_j)
```

drive:

```text
drive =
    eligibility
  * sigmoid(raw_drive)
  * (1 + expected_reward_mag - expected_punish_mag)
  * (1 - fatigue)
  - cost
```

Thompson/noise:

```text
noise_sigma = clamp(0.02, 0.30, 0.22*(1-attention_focus) + 0.12*(1-grasp))
sampled_drive = drive + Normal(0, noise_sigma)
```

互斥:

```text
drive_i' = drive_i - sum_j mutual_inhibit(i,j) * max(0, drive_j)
```

核心互斥:

1. `commit_reply` 抑制 `continue_write`。
2. `request_teacher` 抑制低把握 `commit_reply`。
3. `move_focus` 和 `write_cell` 可弱并存, 但同 tick 只能执行一个主行动。
4. `stop_generating` 不提交空回复。

常用 action:

| action | 触发倾向 |
|---|---|
| move_focus | 视觉/听觉/文本错配、saliency、未闭合 |
| write_cell | 有高把握 next token/slot |
| review_grid | 草稿不确定、提交前 |
| revise_cell | 反例、重复疲劳、低把握 |
| commit_reply | grasp 高、闭合感上升、草稿可读 |
| stop_generating | 无继续必要、压力释放 |
| request_teacher | 低把握但 U 高 |
| idle_think | 无外部输入且 U 高 |
| tool_action | 工具 affordance 高 |

### 4.9 自适应调参 H1-H3

调参本身是行动候选:

```text
tune_drive =
    out_of_range_severity
  * expected_stability_gain
  * source_trust_of_metric
  * (1 - tune_fatigue)
  - tune_cost
```

窗口:

```text
eval_window =
    clamp(20, 300,
          base_window * task_complexity * rhythm_slowdown)
```

默认:

```text
base_window = 60 ticks
max_tune_actions_per_100_tick = 5
max_param_delta_per_tune = 0.08 relative
rollback_if_metric_worse_after = 2 eval_windows
```

调参目标:

1. 高注意对象数量在 7-15。
2. 低把握硬提交率下降。
3. 重复表达疲劳有效。
4. 主动询问不过密。
5. 视觉 patch 不爆预算。
6. B/C 召回延迟达标。

---

## 5. SQLite 与文件布局

建议新建 `phase20_7.sqlite` 或在工作台中允许选择隔离底座, 避免污染旧实验。

### 5.1 核心表

```sql
CREATE TABLE phase20_7_sa_types (
  sa_type_id TEXT PRIMARY KEY,
  substrate TEXT NOT NULL,
  modality TEXT NOT NULL,
  canonical_hint TEXT,
  vector_l1 BLOB,
  vector_l2 BLOB,
  vector_l3 BLOB,
  created_tick INTEGER NOT NULL,
  updated_tick INTEGER NOT NULL
);

CREATE TABLE phase20_7_experience_events (
  event_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  tick INTEGER NOT NULL,
  event_kind TEXT NOT NULL,
  source_packet_id TEXT,
  action_record_id TEXT,
  payload_json TEXT NOT NULL,
  reward REAL NOT NULL DEFAULT 0,
  punish REAL NOT NULL DEFAULT 0,
  created_at_ms INTEGER NOT NULL
);

CREATE INDEX idx_phase20_7_events_tick ON phase20_7_experience_events(session_id, tick);

CREATE TABLE phase20_7_occurrences (
  occurrence_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  sa_type_id TEXT NOT NULL,
  tick INTEGER NOT NULL,
  substrate TEXT NOT NULL,
  position_json TEXT NOT NULL,
  R REAL NOT NULL,
  V REAL NOT NULL,
  A REAL NOT NULL,
  P REAL NOT NULL,
  clarity REAL NOT NULL,
  source_ref TEXT,
  payload_ref TEXT
);

CREATE TABLE phase20_7_structure_edges (
  edge_id TEXT PRIMARY KEY,
  src_occurrence_id TEXT NOT NULL,
  dst_occurrence_id TEXT NOT NULL,
  edge_type TEXT NOT NULL,
  weight REAL NOT NULL,
  learned_weight REAL NOT NULL,
  created_tick INTEGER NOT NULL,
  updated_tick INTEGER NOT NULL
);
```

v1a provenance 必备表:

```sql
CREATE TABLE phase20_7_source_packets (
  source_packet_id TEXT PRIMARY KEY,
  source_kind TEXT NOT NULL,
  source_ref TEXT,
  source_context TEXT NOT NULL,
  modality TEXT NOT NULL,
  trust_snapshot REAL NOT NULL,
  created_tick INTEGER NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE phase20_7_action_records (
  action_record_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  tick INTEGER NOT NULL,
  action_type TEXT NOT NULL,
  selected INTEGER NOT NULL,
  drive REAL NOT NULL,
  eligibility_json TEXT NOT NULL,
  target_refs_json TEXT NOT NULL,
  result_event_id TEXT,
  created_at_ms INTEGER NOT NULL
);

CREATE TABLE phase20_7_import_batches (
  import_batch_id TEXT PRIMARY KEY,
  package_id TEXT NOT NULL,
  package_name TEXT NOT NULL,
  imported_at_ms INTEGER NOT NULL,
  source_hash TEXT NOT NULL,
  dedup_policy TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE phase20_7_package_memberships (
  membership_id TEXT PRIMARY KEY,
  import_batch_id TEXT NOT NULL,
  object_kind TEXT NOT NULL,
  object_ref TEXT NOT NULL,
  event_id TEXT,
  occurrence_id TEXT,
  edge_id TEXT,
  sa_type_id TEXT,
  payload_ref TEXT,
  was_new INTEGER NOT NULL,
  dedup_target_ref TEXT
);

CREATE TABLE phase20_7_derived_runtime_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  tick INTEGER NOT NULL,
  rebuildable INTEGER NOT NULL,
  payload_json TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL
);
```

卸载不删除共享 dedup 记忆:

```text
uninstall(package):
    delete rows where package_memberships.import_batch_id = package
      and was_new = 1
      and no other package/session references same object
    keep rows where was_new = 0 or shared_ref_count > 1
```

约束:

1. `phase20_7_experience_events` 是核心真相源。
2. `derived_runtime_snapshots` 是白箱审计/恢复旁路, 可删可重建, 不作为语义权威。
3. 记忆包导入必须记录 `import_batch_id`; 卸载必须只回退该 batch 新增且未共享的对象。
4. 所有教学、奖惩、图片、音频、画板、DraftGrid 行动都必须有 source_packet 或 action_record 可追溯。

### 5.2 视觉/听觉 payload

```sql
CREATE TABLE phase20_7_payload_blobs (
  payload_ref TEXT PRIMARY KEY,
  payload_kind TEXT NOT NULL,
  media_type TEXT NOT NULL,
  bytes BLOB,
  summary_json TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  created_tick INTEGER NOT NULL
);
```

大 payload 可转为文件:

```text
data/phase20_7_payloads/{source_hash}/{payload_ref}.bin
```

SQLite 只存 ref + hash + summary, 防止数据库膨胀。

### 5.3 索引表

```sql
CREATE TABLE phase20_7_index_registry (
  index_name TEXT PRIMARY KEY,
  source_event_highwater INTEGER NOT NULL,
  rebuildable INTEGER NOT NULL,
  config_json TEXT NOT NULL,
  updated_at_ms INTEGER NOT NULL
);
```

索引可删可重建。删除索引后 AP 能慢速运行, 但不能失忆。

---

## 6. Python 模块边界

建议新建:

```text
apv3test/runtime/phase20_7/
  __init__.py
  models.py
  state_pool.py
  short_structure_pool.py
  experience_log.py
  receptors_text.py
  receptors_vision.py
  receptors_audio.py
  recall_bc.py
  cstar.py
  feelings.py
  action_competition.py
  draft_grid.py
  idle_thinking.py
  learning.py
  memory_packages.py
  runtime.py
  api_schema.py
```

主入口:

```python
def run_phase20_7_turn(
    user_text: str,
    media_inputs: list[MediaInput],
    teacher_feedback: TeacherFeedback | None,
    session_id: str,
    db_path: Path,
    max_ticks: int = 32,
    post_commit_idle_ticks: int = 2,
) -> Phase207TurnResult:
    ...
```

闲时入口:

```python
def run_phase20_7_idle(
    session_id: str,
    db_path: Path,
    max_ticks: int = 24,
    budget_ms: int = 1500,
) -> Phase207IdleResult:
    ...
```

Agent API:

```python
def ap_perceive_and_reply(
    text: str,
    images: list[Path] | None = None,
    audio: list[Path] | None = None,
    canvas_png: Path | None = None,
    teacher_feedback: str | None = None,
    session_id: str | None = None,
) -> dict:
    """
    returns:
      reply_text
      committed
      tick_trace
      state_pool_summary
      memory_deltas
      requests_for_teacher
      confidence/grasp/uncertainty
    """
```

---

## 7. RuntimeTickEvent v2

RuntimeTickEvent 是 UI 与外部项目的唯一展示依据。

```python
RuntimeTickEventV2(
    tick: int,
    session_id: str,
    is_projection: Literal[False],
    external_inputs: list[InputTrace],
    receptor_outputs: list[OccurrenceTrace],
    state_pool_top: list[StatePoolTrace],
    ssp_active_summary: SSPSummary,
    query_structures: list[QueryTrace],
    b_candidates: list[BCandidateTrace],
    c_forward: list[CSlotTrace],
    c_backward: list[CSlotTrace],
    cstar_packet: CStarTrace,
    feelings: FeelingVector,
    emotion: EmotionVector,
    unclosed_items: list[UnclosedTrace],
    action_competition: list[ActionCandidateTrace],
    selected_action: ActionTrace,
    draft_grid: DraftGridTrace,
    visual_inner_picture: InnerPictureTrace | None,
    audio_inner_sketch: InnerAudioTrace | None,
    learning_deltas: list[LearningDeltaTrace],
    experience_event_ids_written: list[str],
    source_refs: list[SourceRefTrace],
    action_record_ids: list[str],
    rejected_candidates: list[RejectedCandidateTrace],
    index_query_trace: list[IndexQueryTrace],
    package_delta_refs: list[str],
    timings_ms: TimingTrace,
)
```

红线:

1. UI 若看到 `is_projection != False`, 必须显示警告。
2. UI 不得自己生成 tick 名称、过程、行动或曲线。
3. UI 可中文化解释, 但必须引用 trace 字段。
4. 每个 tick 至少要能回查本 tick 写入了哪些 `ExperienceEvent`; 没有写事件时也要说明 `no_write_reason`。
5. `rejected_candidates` 必须记录高分但未选行动/召回的原因, 用于排查“为什么没问/为什么没写/为什么停”。
6. `index_query_trace` 必须记录索引用了哪些 key、召回了多少候选、重排前后 top 变化, 防止索引变成黑箱。

---

## 8. 阶段实施计划

v1a 阶段依赖原则:

1. 任何 Stage 的验收不得依赖尚未实现的隐藏机制。
2. Stage 1 若要验收“教学不串场”, 就必须包含最小 EventLog 与 exact structural B0 召回; 不能用 teaching shortcut。
3. Stage 2 扩展为完整统一经验流与可重建索引, 不是 Stage 1 之后才第一次写记忆。
4. Stage 3 扩展为相似结构 B/C/C* 与 C* 回灌, 不是 Stage 1/2 的答案来源。
5. 每个 Stage 都必须先有红线单测, 再有功能单测, 最后才接 UI。

### Stage 0: 边界隔离与红线扫描

目标:

1. 新建 Phase20.7 包, 不继续在 Phase20.6 主文件上堆逻辑。
2. 保留 Phase20.6 作为对照与回归边界。
3. 新建隔离 SQLite。
4. 红线扫描禁止旧捷径进入 Phase20.7。

Gate:

1. 禁 `enumerate_objects_in_image` 出现在 Phase20.7 对话语义路径。
2. 禁 `image_label_map`, `teaching_hit`, `taught_answer`, `direct_reply`, `reply_text = taught`。
3. 禁预生成完整回复后逐字切片。
4. 禁 UI 生成假 tick。
5. 禁 OCR/云 TTS/学生侧 LLM。

### Stage 1: StatePool + SSP + 最小 EventLog + DraftGrid 文本闭环

目标:

1. 文本输入进入 StatePool 和 SSP。
2. 每 tick 更新 R/V/A/F/P。
3. DraftGrid 由行动竞争逐 tick 写入。
4. “你好”教学后, “你是谁”不串场。
5. 每 tick 至少写入最小 `ExperienceEvent`。
6. 支持 exact structural B0 召回: 只在当前 SSP query 与历史结构 exact/near-exact 匹配时召回, 不做泛化。

Demo:

```text
用户: 你好啊
AP: 嗯,你好。
用户纠正: 你也好
再次: 你好啊
AP: 你也好 / 嗯,你也好。
用户: 你是谁
AP: 不确定 / 我还不太知道怎么说。
```

Stage 1 禁止:

1. 独立教学表直接命中。
2. 把上一条纠正文本作为全局 fallback。
3. 使用完整回复候选。
4. 使用相似度泛化召回回答未覆盖问题。

### Stage 2: 统一经验流 + 索引

目标:

1. 将 Stage 1 最小 EventLog 扩展为完整统一经验流 schema。
2. 建立 ANN/Zvec/rolling hash/倒排等可重建索引。
3. 删除索引可重建。
4. 记忆查看只显示一个本地记忆入口, 内部分为快处理倾向和慢处理痕迹, 不再像两套数据库。
5. 支持 import_batch / package_membership provenance, 为后续记忆包卸载做准备。

### Stage 3: B/C/C* 召回

目标:

1. 用 SSP query 召回历史结构。
2. C_forward 预测后继。
3. C_backward 追溯原因。
4. C* 回灌 StatePool。

验收:

1. 能解释“为什么刚才想回你好”。
2. 能在低把握时请求教师。
3. 能通过反例松动错误共现。

### Stage 4: 未闭合感与闲时思考

目标:

1. 未懂的问题形成 U。
2. 无输入时低频 idle_think。
3. 闲时可以复述、类比、问问题。

Demo:

```text
用户: 猫是一种动物
AP: 嗯,猫,动物。
闲时若 U 高:
AP 内部: 猫=动物。还有什么是动物?
下一次合适时:
AP: 还有别的动物吗?
```

### Stage 5: 视觉感受器与内心画面

目标:

1. foveated sampling 保存 patch payload。
2. 视觉 SA 进入 StatePool/SSP。
3. 通过共现学习“苹果/香蕉”, 不串场。
4. 内心画面由 patch + clarity + R/V sketch 重建。

Demo:

1. 教苹果图是苹果。
2. 教香蕉图是香蕉。
3. 再给苹果, 不因最近香蕉教学而说香蕉。
4. Tick 回放显示多个 fixation, clarity 累积。

### Stage 6: 听觉与 TTS

目标:

1. TTS 是行动器朗读, 不等于内心音频。
2. xiaoyi 本地声音可作为默认朗读 voice。
3. 录音初期作为 audio audit occurrence, 不冒充识别。
4. 后续 Phase19 听觉识别接入同一经验流。

### Stage 7: 工作台与本地底座 API

目标:

1. UI 只读 RuntimeTickEvent。
2. 本地记忆/记忆包统一入口。
3. 支持导入、导出、卸载、删除、搜索、勾选。
4. 支持 Agent/API 调用。
5. 支持桌宠读取状态池、想法云、内心画面、审计曲线。

### Stage-G: 六阶段学习协议与 SDPL 映射

Stage-G 不是额外 runtime 阶段, 而是所有 Stage 的学习事件标注规则。

每个学习相关 `ExperienceEvent` 必须可选携带:

```python
LearningProtocolTrace(
    learning_stage: Literal[
        "exposure",
        "imitation",
        "correction",
        "contrast",
        "generalization",
        "teacher_off_validation",
    ],
    sdpl_packet_key: str | None,
    epistemic_source: Literal[
        "self_perceived",
        "teacher_given",
        "tool_feedback",
        "reward_punish",
        "memory_recalled",
        "imagined_prediction",
    ],
    teacher_off_status: Literal["not_applicable", "teacher_on", "teacher_off_probe", "passed", "failed"],
    leakage_guard: list[str],
)
```

约束:

1. 六阶段学习协议不是课程外壳, 是经验事件的来源与验收标签。
2. SDPL packet 只区分来源、证据和学习阶段, 不提供答案。
3. teacher-off 验收必须证明没有教师文本、答案表、关键词路由、学生侧 LLM。
4. 技能包分享时必须保留 learning_stage 和 epistemic_source, 方便别人检查它是怎么学来的。

---

## 9. 技能路线

Phase20.7 不一次实现所有技能, 但从一开始预留同一闭环接口。

### 9.1 开放中文对话

核心:

1. 文本 SA 按需细化。
2. 风格化回复作为表达经验, 不作为答案表。
3. DraftGrid 逐 tick 写、看、改、提交。

### 9.2 主动学习

核心:

1. request_teacher 是 action。
2. 用户教学进入经验流。
3. 教学纠正分配 reward/punish 信号。
4. 闲时可继续想未懂内容。

### 9.3 视觉学习

核心:

1. 视觉对象不靠文件名/整图 label。
2. 局部 patch 与文本共现。
3. 视焦点移动由 saliency/mismatch/U/teacher focus 学习。

### 9.4 小学数学

核心:

1. 竖式用 DraftGrid 二维空间。
2. 数手指用 occurrence 计数和行动反馈。
3. 进位/借位是结构边和未闭合项, 不是隐藏计算器。

### 9.5 小学语文与识字

核心:

1. 字形来自视觉 SA。
2. 字音来自听觉 SA。
3. 字义来自文本/行动/奖惩/共现。
4. 读写过程走 DraftGrid 和画板读回。

### 9.6 画板与坐标轴

核心:

1. 画板是行动器 + 视觉感受器。
2. AP 画线后必须看回。
3. 坐标轴、辅助线、图形都进入 SSP 空间结构。

### 9.7 键鼠与桌面控制

核心:

1. 键鼠是行动器。
2. 屏幕读回是感受器。
3. 不允许大宏脚本跳过低粒度动作反馈。

---

## 10. 工作台产品要求

工作台要给用户惊艳感, 但惊艳来自真实过程可视化。

必须有:

1. 正常聊天气泡, 显示用户原文、图片缩略图、音频播放器。
2. Tick 回放, 可播放、上一 tick、下一 tick、选择 tick。
3. DraftGrid 二维草稿。
4. StatePool top items, 中文可读, 可展开 occurrence 来源。
5. SSP 结构视图, 显示顺序/空间/图关系。
6. B/C/C* 召回视图, 显示预测和追溯。
7. 内心画面, 随 tick 改变。
8. 内心音频/节奏 sketch。
9. 想法云, 来自状态池非视觉/非听觉高能对象。
10. 审计曲线, 每 tick 多线图, hover 显示数值。
11. 本地记忆/记忆包统一入口。
12. 教学纠正不覆盖聊天内容, 显示“纠正回答『...』 已学习”。
13. 主动询问和闲时思考要能被用户看见 trace。

禁止:

1. 显示英文 SA id 作为主要内容。
2. 用假阶段标题替代真实 tick。
3. 用固定直线假审计曲线。
4. 用原图缩略图冒充内心画面。
5. 把快/慢记忆显示成两套互不相关数据库。

---

## 11. 验收矩阵

### 11.1 文本学习不串场

脚本:

```text
1. 用户: 你好
2. 教学: 你也好
3. 用户: 你是谁
4. 预期: 不应回复“你也好”; 应低把握或请求教师
```

通过条件:

1. 经验流有教学事件。
2. “你好”相关 query 才强召回。
3. “你是谁” query 与 “你好”结构相似不足。
4. action_competition 显示未命中或请求教师。

### 11.2 视觉学习不串场

脚本:

```text
苹果图 + 教“苹果”
香蕉图 + 教“香蕉”
苹果图 again
```

通过条件:

1. 苹果/香蕉视觉 occurrence 的 patch/shape/color/position 证据不同。
2. 苹果图再次召回苹果经验强于香蕉。
3. 若低把握, 可说“像之前那个苹果”, 或请求确认, 但不能因最近教学直接说香蕉。

### 11.3 闲时思考

脚本:

```text
用户教: 猫是一种动物
用户停止输入 10 秒
```

通过条件:

1. U 中有“猫/动物”未闭合项。
2. idle_think tick 产生 B/C/C*。
3. 不直接打扰用户过多; 若问, 应符合 request_teacher 冷却。

### 11.4 DraftGrid 真写入

通过条件:

1. 每 tick 最多一个主写入/修改行动。
2. commit 文本等于 DraftGrid visible_text。
3. 不能存在完整回复预生成字段。

### 11.5 内心画面

通过条件:

1. visual patch payload 数量随 tick 变化。
2. clarity map 随 fixation 移动和累积。
3. R/V sketch 可切换查看。
4. 周边稀疏非空。

### 11.6 Agent API

通过条件:

1. 外部项目可调用 `ap_perceive_and_reply`。
2. 返回 reply + tick_trace + memory_delta。
3. 不返回隐藏 LLM 答案。

---

## 12. 红线扫描

Phase20.7 必须新增红线:

```text
forbidden:
  enumerate_objects_in_image in phase20_7 dialogue path
  image_label_map
  teaching_hit
  taught_answer
  direct_label_reply
  reply_text = taught
  full_reply_candidate
  candidate_text schedule
  if keyword then answer
  regex route answer
  OpenAI/Google/Edge TTS
  pytesseract/easyocr/paddleocr
  student_side_llm
  workbench_projection
  fake_tick_stage
```

允许:

1. LLM 做教师、课程生成、审计、工程辅助, 但不作为学生侧答案生成。
2. Zvec/ANN 做索引, 但可重建。
3. xiaoyi 本地 TTS 做行动器朗读。
4. UI 做中文解释, 但必须来自 RuntimeTickEvent。

---

## 13. 性能策略

### 13.1 文本 tick

目标:

```text
20-80 ms per tick initial
max 32 active ticks per turn
post_commit_idle_ticks default 2
```

### 13.2 视觉 tick

目标:

```text
100-300 ms per visual tick
max 64 patch per tick
max high patch 8 per tick
max 12 MB payload per turn initial
```

### 13.3 闲时 tick

目标:

```text
idle_tick_rate <= 2 tick/s
idle_burst_max = 24 tick
stop if user input arrives
```

### 13.4 大库召回

必须两阶段:

```text
cheap candidate retrieval -> structural rerank -> C propagation
```

大库性能 Gate:

1. 10k events 下文本 turn p95 < 2s。
2. 100k events 下有索引 p95 < 4s。
3. 删除索引后能慢速运行并提示重建。

---

## 14. 风险与对策

### 14.1 最大风险: 又写成候选短句系统

对策:

1. Stage 1 禁完整回复候选。
2. DraftGrid commit 只能读 visible_text。
3. 单测检查字段。

### 14.2 最大风险: 视觉重建变成贴原图

对策:

1. 内心画面函数只接受 patch payload + clarity + R/V sketch。
2. 禁传原图 path 给 inner_picture renderer。
3. 单测检查 source mask。

### 14.3 最大风险: 主动询问烦人

对策:

1. request_teacher 有 ask_fatigue。
2. 同 topic 20 turn 冷却。
3. UI 允许用户给“先别问”惩罚反馈。

### 14.4 最大风险: 闲时思考耗 CPU

对策:

1. idle_tick_rate 限制。
2. 只处理 U 高对象。
3. 用户输入立即打断。
4. 工作台可开关 idle。

### 14.5 最大风险: 伪因果太强

对策:

1. 保留拟人伪因果形成。
2. 用反例松动、教师纠正、失败行动、重复验证逐渐降低。
3. 不写天生反伪因果硬门。

---

## 15. 交付物

Phase20.7 应交付:

1. `apv3test/runtime/phase20_7/` 新 runtime。
2. `phase20_7.sqlite` schema migration。
3. `tests/test_phase20_7_statepool_ssp.py`
4. `tests/test_phase20_7_text_learning_no_cross_talk.py`
5. `tests/test_phase20_7_bc_cstar.py`
6. `tests/test_phase20_7_idle_thinking.py`
7. `tests/test_phase20_7_visual_learning_no_cross_talk.py`
8. `tests/test_phase20_7_inner_picture_payload.py`
9. `tests/test_phase20_7_redlines.py`
10. `tests/test_phase20_7_source_trust_locality.py`
11. `tests/test_phase20_7_memory_package_uninstall.py`
12. `tests/test_phase20_7_runtime_tick_event_audit_chain.py`
13. `tests/test_phase20_7_release_demo_flow.py`
14. `reports/APV3_Phase20_7_OpenDialogueFoundation_Showcase_YYYYMMDD.html`
15. `reports/APV3_Phase20_7_PerformanceAndRedlineReport_YYYYMMDD.md`
16. `reports/APV3_Phase20_7_ReleaseDemo_UserGuide_YYYYMMDD.md`
17. `FinalReport_Phase20_7_OpenDialogueFoundation_YYYYMMDD.md`
18. `data/phase20_7_demo_assets/` 本地可复现实验素材。

---

## 16. 完整可发布 demo

目标不是做一个最小样例, 而是做一个可以发布给内测用户使用的本地 AP 对话底座。演示应覆盖普通聊天、主动学习、闲时思考、视觉、听觉、画板、记忆包、Agent API 和白箱审计, 让用户一眼看出“这不是 LLM 预训练答案, 这是会成长的 AP”。

### 16.1 发布版用户流程

发布 demo 首页直接进入工作台, 不做营销页。用户可以:

1. 文字聊天。
2. 选择图片或拖入图片。
3. 录音或上传音频。
4. 在画板画图/写字/画坐标轴。
5. 对上一轮回复教学纠正。
6. 查看 tick 回放、DraftGrid、StatePool、SSP、B/C/C*、内心画面、内心音频、想法云、审计曲线。
7. 查看本地记忆, 搜索、删除、导出、导入、卸载记忆包。
8. 开关闲时思考, 查看闲时 tick 和主动询问来源。
9. 复制 Agent API 调用样例。

### 16.2 发布版演示脚本 A: 对话身份与不串场

```text
用户: 你好
AP: 嗯,你好。

用户: 我叫银子
AP: 嗯,银子。

用户: 你记得我叫什么吗?
AP: 银子。

用户: 你是谁?
AP: 我还不太会说自己是谁。你可以教我。
```

验收:

1. `我叫银子` 写入 SSP 和 ExperienceEvent。
2. `银子` 与用户身份上下文共现。
3. “你是谁”不召回“你好/银子”作为直接答案。
4. 低把握触发 request_teacher 或低把握表达。

### 16.3 发布版演示脚本 B: 主动询问与闲时思考

```text
用户: 猫是一种动物
AP: 嗯,猫,动物。

用户停止输入。

AP 闲时内部 tick:
  U: 猫/动物解释未闭合
  C_forward: 可能还有别的动物
  action: request_teacher candidate rising

AP 合适时:
  狗也是动物吗?
```

验收:

1. `猫/动物` 形成 AP-native U, 来源引用 C* gap 和先天求知规则。
2. idle_think 写入经验流, 不是 UI 假日志。
3. request_teacher 有冷却, 不刷屏。
4. 用户回答后, 新知识回到同一经验流。

### 16.4 发布版演示脚本 C: 视觉教学与不串场

```text
用户发苹果图: 这是什么?
AP: 我还不能确认。
用户教: 苹果
AP: 嗯,苹果。

用户发香蕉图: 这个呢?
AP: 我还不能确认。
用户教: 香蕉
AP: 嗯,香蕉。

用户再发苹果图:
AP: 像苹果。
```

验收:

1. 苹果/香蕉视觉 occurrence 的 patch、颜色、形状、位置证据不同。
2. 视焦点由 action competition 移动, 不是固定小方块。
3. 内心画面随 tick 清晰区域变化并累积。
4. “像苹果”来自视觉 SA 与文本共现, 不是最近教学答案。

### 16.5 发布版演示脚本 D: 听觉/TTS

```text
用户录音: 一段短音频
AP: 我听到一段声音, 还不能确认内容。
用户文字教: 这是敲桌子的声音
AP: 嗯,敲桌子。
```

验收:

1. 录音初期只形成 audio audit occurrence, 不冒充语音识别。
2. 内心音频显示频谱/节奏 sketch。
3. TTS 使用本地 xiaoyi 朗读已提交回复, 不等于 inner voice。

### 16.6 发布版演示脚本 E: 画板、识字、小学能力入口

```text
用户在画板写/画一个简单图形或坐标轴。
AP 移动视焦点观察局部。
用户教: 这是横线 / 这是 1 / 这是苹果的一笔
AP 在 DraftGrid 或画板上尝试复现。
AP 看回自己画出的结果, 再决定修改或提交。
```

验收:

1. 画板输出进入 SELF_DRAFT_GRID / visual occurrence。
2. AP 画完必须看回, 不能只保存 UI 状态。
3. 竖式数学、数手指、坐标轴、辅助线都走 DraftGrid/SSP 空间结构。

### 16.7 发布版演示脚本 F: 本地记忆与记忆包

用户可以:

1. 搜索“苹果”“猫”“你好”等记忆。
2. 查看每条记忆的人类可读含义、source、tick、learning_stage、support。
3. 删除单条本地记忆。
4. 导出“水果视觉教学包”。
5. 导入一个记忆包。
6. 卸载该包, 验证卸载后状态等同未导入, dedup 共享记忆不被误删。

验收:

1. 导入产生 `import_batch_id`。
2. 卸载只删除 `was_new=1` 且无共享引用的对象。
3. 本地完整记忆与记忆包只是一套入口, 不分裂成多套数据库。

### 16.8 发布版演示脚本 G: Agent API

外部项目调用:

```python
ap_perceive_and_reply(
    text="这是什么?",
    images=["apple.jpg"],
    session_id="demo_user"
)
```

返回:

```json
{
  "reply_text": "像苹果。",
  "committed": true,
  "tick_trace": "...",
  "state_pool_summary": "...",
  "memory_deltas": "...",
  "requests_for_teacher": [],
  "confidence": {"grasp": 0.67}
}
```

验收:

1. API 返回 AP 已提交 DraftGrid 文本。
2. 返回 RuntimeTickEvent v2。
3. 不返回隐藏 LLM 答案。
4. 可被桌宠或其它本地项目作为底座调用。

### 16.9 发布版验收包

发布 demo 必须同时交付:

1. 可运行本地工作台。
2. 隔离测试数据库。
3. 演示素材: 本地生成单苹果/单香蕉/单橙子, 以及少量变形合成图。
4. 自动化验收脚本。
5. 红线扫描报告。
6. 性能报告。
7. Final Report。
8. 一页用户说明: 解释它是“会学的小孩级 AP”, 不是全知 LLM。

---

## 17. 实施优先级

必须顺序:

1. Stage 0 红线隔离。
2. Stage 1 StatePool + SSP + DraftGrid 文本闭环。
3. Stage 2 统一经验流。
4. Stage 3 B/C/C*。
5. Stage 4 闲时思考和主动询问。
6. Stage 5 视觉 patch 与内心画面。
7. Stage 6 听觉/TTS。
8. Stage 7 工作台和 API。
9. Stage 8 完整发布 demo 打包、性能验收、红线验收、用户说明和最终报告。

不能顺序:

1. 先做 UI 美化。
2. 先做记忆包生态。
3. 先做整图识别。
4. 先做长篇对话输出。
5. 先做桌宠接入。
6. 只做最小 demo 就停下验收。

---

## 18. 最终判断

以“会学的 3-5 岁小孩级开放自由对话底座”为目标, APV3 Phase20.7 在逻辑上可行。可行的前提不是让 AP 一开始知道所有东西, 而是把以下三件事做真:

1. 统一经验流能让每次教学、反馈、行动、感受都成为后续可召回经验。
2. B/C/C* 与未闭合感能让 AP 在不知道时继续观察、追溯、询问和闲时思考。
3. DraftGrid 与多模态感受器能让输出、视觉、听觉、画板、工具行动都回到同一闭环。

若这三件事跑通, AP 不会像 LLM 那样“成人式无所不答”, 但可以像一个会成长的小孩: 不懂会问, 学了会记, 记错会被纠正, 闲时会琢磨, 逐渐形成自己的经验、风格和理解。

---

## 19. v1a 自审结论

### 19.1 已补足的关键缺口

1. Stage 依赖闭合: Stage 1 已要求最小 EventLog 与 exact structural B0, 不再用尚未实现的 Stage 3 能力验收教学不串场。
2. 未闭合感 AP-native 化: U 的来源被拆成 reward/punish 预测、先天规则、C* 预测不验、行动未完成和 affordance 等派生量。
3. source_trust 局部化: trust 是 `source x context x modality`, 只在相关事件更新, 不再是全局教师权威。
4. SQLite provenance: 增加 source_packets、action_records、import_batches、package_memberships、derived_runtime_snapshots。
5. RuntimeTickEvent 审计链: 增加 event ids、source refs、action records、rejected candidates、index query trace。
6. 视觉焦点行动化: focus 必须由 action competition 给出, 固定扫描只能是低优先级探索候选。
7. 六阶段/SDPL 映射: 学习事件携带 learning_stage、epistemic_source、teacher_off_status。
8. 发布 demo 升级: 目标从最小 demo 改为完整可发布本地工作台与 API 底座。

### 19.2 仍需实现阶段验证的高风险点

1. 视觉 patch payload 与内心画面质量: 设计已闭合, 但工程质量取决于 payload 保存、clarity merge 和渲染性能。
2. idle_think 是否拟人: 需要调 request_teacher 冷却、ask_fatigue 和 U 阈值, 防止太吵或太迟钝。
3. B/C/C* 性能: 大库召回必须靠可重建索引, 但索引不能成为语义真相源。
4. source_trust 学习: 需要真实反例和跨 context 测试, 防止 teacher trust 泛化过度。
5. 记忆包卸载: 必须做导入/去重/共享引用/卸载后等价性测试。

### 19.3 开工前必须满足

1. Stage 0 先做红线扫描与 Phase20.7 新 runtime 边界。
2. 任何 UI 页面必须等 RuntimeTickEvent v2 字段存在后再做。
3. 不先接桌宠, 不先做长篇输出, 不先做整图识别。
4. 每个 Stage 必须有:
   - 设计引用。
   - 红线测试。
   - 功能测试。
   - RuntimeTickEvent 证据。
   - 经验流写入证据。
   - 最终小报告。

### 19.4 可实现性判断

按本 v1a 路线, “中文自由对话底座”的正确目标可以实现:

1. L1: 真实文本闭环和教学不串场, 可高信心实现。
2. L2: 30 分钟教学后形成稳定局部对话/视觉技能, 可中高信心实现。
3. L3: 本地记忆包分享、卸载、跨 session 技能迁移, 可中等信心实现。
4. L4: 3-5 岁小孩级“会学、会问、会闲时琢磨”的自由对话底座, 理论上可行, 工程成败取决于 Stage 3-5 的 B/C/C*、idle_think 和视觉 payload。

这不是成人 LLM 式的“什么都知道”, 而是 AP-native 的“什么都能进入经验流, 并在后续经验中逐步学会”。这一路线与白皮书一致, 可以进入 Stage 0 实施。
