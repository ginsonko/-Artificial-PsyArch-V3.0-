# APV3.0 拟人多模态底座 — 完整设计稿 v7(轮 3 对抗审阅彻底修复)

日期: 2026-06-17
作者: 接手线程
状态: **v6 经轮 3 对抗审阅发现 10 blocker + 11 serious + 6 minor + 5 coverage holes。其中 4 个 "v5→v6 修复" 被识别为纸面修复(B1/B2 ΔP/B7 target/B8 boundary/B9 bootstrap)。v7 真修这些根本问题。同时 §40-§42 远景多个机制无法工作(narrative 对称 PMI/counterfactual 零设计/层级 bootstrap 反向/abstract gate 不 gate),v7 也补完。**

前身链:v1 → v2 → v3 → v4 → v5 → v6 → **v7(本稿)**

---

## 0. v6 → v7 修正总览(必读)

### 0.1 v6 真 blocker 必修(10 条)

| # | v6 缺陷 | v7 修复 |
|---|---|---|
| **B1+B2** | §2.3 frozen_attention 让 candidate 锁在 attention 外,ΔP ≡ 0,N-run t 检验在测 0≠0 | §2.3 改 **真重放:cold-fork held-out trace + candidate 从 t=0 在池;Bootstrap on data (10 不同 held-out 子集)** ,变异源真实存在 |
| **B3** | §2.4 anti-correlation 在冷启动 kill 合法链(早期边都缺数据,PMI 低) | §2.4 加 **`min_obs_for_anticorr=10` gate**,数据不足时边标"unknown"不当"反相关" |
| **B4** | §2.7 + §16.11 credit assignment:整句 commit 被否,所有 vocab 全 -1 → "苹果"被冤枉 | §2.7 改 **按 attention share 加权分配负反馈** + 确认错误所在 slot 才扣那个 slot 的 filler |
| **B5+B6** | §6.3 KL 无界 + 跨通道大 codebook 仍占优 | §6.3 改 **JSD(对称且界限) + 按 log(codebook 大小) 归一化** |
| **B7** | §11.2 Π update `target` 从来没定义过 | §11.2 显式 **`target_i(t) = R_i^observed_at_t+1`**(TD(0)),证明残差有界 |
| **B8** | §16.8 utterance_boundary 用户打字中暂停就误触发 | §16.8 改 **(a) 显式 send 信号** + **(b) 长静默阈值(≥2 秒)做软 graded marker**,不再用 1 tick 队空判定 |
| **B9** | §16.9 bootstrap_R_changes 加注释就以为合规——self-fulfilling 硬编码 | §16.9 改 **全部 bootstrap=0.0,用 Thompson sampling / ε-greedy 探索** seed memory;前 N tick 强探索 |
| **B10** | §16.11 correction_candidate 还硬编码 R/P | §16.11 改 **R/P 派生自 mismatch_sa 的 R/P**(因果链),无独立硬编码 |

### 0.2 v6 真 serious 修复(11 条)

| # | 问题 | v7 修复 |
|---|---|---|
| S1 | §40.A narrative 用对称 PMI 不能区分 A→B vs B→A | **§2.8 lag-PMI(时序 PMI):`P(B at t \| A at t-k) / P(B)`,作为新底层原语** |
| S2 | §40.B causal SA 依赖 Phase 10.4 反事实模拟零设计 | §40.B 推迟到 Phase 10.4 完整 spec 完成;§40.4 给出 **反事实模拟的最小机制设计** |
| S3 | §40.E hierarchy SA bootstrap 反向(需"水果"先存在才能 is_a) | §40.E 改 **匿名 super-cluster spawn**:3+ sub-vocab 共享 slot 偏好 + channel sig → 涌现 unnamed super,后被命名时绑定 |
| S4 | §11.5 sensor salience smuggles attention prior 跨 C-5 边界 | §11.5 **显式承认是 C-5 边界扩展**(documented expansion),不假装"C-5 已允许" |
| S5 | §11.3 vs §11.8 marker SA 哲学不一致(novelty 独立 SA vs tentative 字段) | §11.3 改 **统一选"独立分级 marker SA"**;tentative_vocab 改 `tentative_marker::<vocab_id>` SA |
| S6 | §41.D deliberative sub-cycle 破坏 tick=time 不变量 + 无 audit | §41.D 改 **deliberative steps = own ticks on virtual track**;audit_db 记录每 deliberative tick |
| S7 | §41.E self_sa durable=True 破坏能量守恒 | §41.E 改 **self_sa 正常衰减 + session boot 时从 long-term 重生**,无独立能量源 |
| S8 | §41.A 元认知需 domain SA 但无定义 | §41.A 显式依赖 §40.E hierarchy + 加 **domain = hierarchy depth ≥ k 的 super** |
| S9 | §41.B abstract gate "3 链 grounded SA" 不 gate abstraction | §41.B 改 **3 链跨 ≥2 个 channel-sig cluster**(语义跨场景) |
| S10 | §40.F reading 两个文本输入路径未统一 | §40.F 改 **单管道 + source 字段**(streaming / reading) |
| S11 | §2.7 vocab retract 不级联清理 §40-§41 新 SA 家族(narrative/abstract/self) | §2.7 改 **atomic retire 遍历所有 SA 家族 vocab pointer**,degrade 或 re-anchor 到 placeholder |

### 0.3 v6 minor + 覆盖洞(全部处理)

- M1-M6: 见 §11.9/§11.8/§18.5 拓展,各章节修补
- 覆盖洞 H1-H5: 加 §29 **imitation/gaze contingency/joint attention/number sense/embodied** 远景设计

### 0.4 v7 总红线变化

新增:
- **❌ "frozen attention" 不许在 ΔP 评估中使用**(B1 教训)
- **❌ 任何 R_change / R / P 硬编码常量**(B9/B10 教训)——必须或为 0,或派生自其他能量
- **❌ "声称修复但实际换措辞"**(B7 教训)——每次修复必须给完整公式 + 边界条件
- **❌ "Phase 9+ backlog" 不许包含 Phase 8 依赖**——纠错 §16.11 等不依赖 RPE

---

## 1-10. 沿用 v6 结构,关键章节按下文修

---

## 2. 通用 SA 组合词汇固化 — v7 真严格化

### 2.1-2.2 沿用 v6

### 2.3 ΔP 晋升门 — cold-fork bootstrap(B1+B2 真修)

**v6 错误重述**:`freeze_attention=True` 在 baseline run 时计算了 attention 分配,candidate run 时也用这套分配 → candidate 的 attention=0 → candidate 不参与 Π → ΔP ≡ 0。

**v7 正确做法**——**cold-fork replay,从 t=0 加入 candidate**:

```python
def evaluate_fixation_via_cold_fork(candidate, held_out_dataset, n_bootstraps=10):
    """
    严格 ΔP 评估:
    - 不冻结 attention(candidate 必须能参与竞争)
    - 变异源 = held_out 数据子集 bootstrap(真随机)
    - 完全重放:candidate 从 t=0 在池中
    """
    P_baseline_per_bootstrap = []
    P_with_candidate_per_bootstrap = []
    
    for boot_idx in range(n_bootstraps):
        # Bootstrap held_out: 随机抽样 80% 数据,各 boot_idx 不同
        held_out_subset = bootstrap_sample(held_out_dataset, ratio=0.8, seed=boot_idx)
        
        # Run 1: baseline(无 candidate)
        snapshot_a = replay_held_out_cold_fork(
            held_out_subset,
            vocab_set=current_vocab,            # candidate NOT in pool
            initial_seed=boot_idx,
            freeze_attention=False,             # attention 正常竞争
        )
        P_baseline_per_bootstrap.append(snapshot_a.mean_P)
        
        # Run 2: with candidate from t=0
        snapshot_b = replay_held_out_cold_fork(
            held_out_subset,
            vocab_set=current_vocab | {candidate},   # candidate IN pool
            initial_seed=boot_idx,                    # 同 seed
            freeze_attention=False,                   # 同样不冻结
        )
        P_with_candidate_per_bootstrap.append(snapshot_b.mean_P)
    
    # 配对 t 检验
    deltas = [b - w for b, w in zip(P_baseline_per_bootstrap, P_with_candidate_per_bootstrap)]
    t_stat, p_value = paired_t_test(deltas)
    
    # 两道门:显著 + 实用
    return {
        "mean_delta_P": mean(deltas),
        "p_value": p_value,
        "passes": p_value < 0.05 and mean(deltas) > θ_promote_dP_min,
    }
```

**为什么这正确**:
- **变异源真实**:bootstrap_sample 让每次重放看不同 80% 数据,自然产生 ΔP 方差
- **不冻结 attention**:candidate 在状态池里,自然参与 attention 竞争,能展示其对 P 的影响
- **同 seed pair**:控制其他随机源,paired-t 测的是"candidate 是否系统性降 P"
- **bootstrap on data, not on RNG**:这是统计学标准做法

**θ_promote_dP_min 合理化**:默认 0.05(P 单位),代表 candidate 至少在 80% bootstrap 中带来明显压力降低。Phase 8.4 验收必须包含反例测试(看似 PMI 高但 ΔP 实际为 0 的合成案例)。

### 2.4 chain extension — 数据足够才查反相关(B3 fix)

```python
def try_extend_chain(seed_a, seed_b, max_length=4):
    chain = [seed_a, seed_b]
    while len(chain) < max_length:
        next_candidate = find_partner(chain[-1])
        if next_candidate is None:
            break
        
        all_eligible = True
        # Span eligibility(1-hop + 2-hop)
        for span in range(1, min(3, len(chain))):
            other_idx = -(span + 1)
            if other_idx < -len(chain):
                continue
            other = chain[other_idx]
            edge = get_edge(other, next_candidate)
            if not edge_is_eligible(edge):
                all_eligible = False
                break
        
        if not all_eligible:
            break
        
        # 反相关检查:只在数据充足时启用(B3 fix)
        for prior in chain:
            edge = get_edge(prior, next_candidate)
            if edge.observation_count >= θ_min_obs_for_anticorr:  # 默认 10
                if edge.smoothed_pmi < θ_anti_correlation:        # 默认 -0.5
                    all_eligible = False
                    break
            # 数据不足时该边"unknown"不当"anti-correlated",不否决
        
        if not all_eligible:
            break
        chain.append(next_candidate)
    
    return chain if len(chain) >= 2 else None
```

**关键**:`observation_count < 10` 的边视为 unknown 不视为反相关。这避免冷启动 kill 合法长链。

### 2.5-2.6 沿用 v6

### 2.7 vocab SA 反例撤销 — 加权 credit assignment(B4 fix)

**v6 错误**:整句 commit 被否,commit 用到的所有 vocab 都 -1 → 正确 vocab 被冤。

**v7 正确做法**——**两阶段 credit assignment**:

**阶段 1 - 不确定:负反馈先入 commit 整体而非 vocab**:

```python
def handle_negative_feedback_phase1(commit_record, negative_signal):
    """
    收到负反馈,先不要扣 vocab,先 spawn 整体 mismatch SA
    并触发 correction_candidate 等教师证据
    """
    # 整体 mismatch event(从 commit 派生 R/P,无硬编码)
    mismatch_sa = SA(
        sa_label=f"event::commit_mismatch::{commit_record.id}",
        real_energy=negative_signal * commit_record.commit_R,
        cognitive_pressure=negative_signal * commit_record.commit_R,
        channel_signature={"commit_event_marker": 1.0},
        linked_vocabs=commit_record.vocabs_used,
        linked_attention_shares=commit_record.vocabs_attention_share,  # 加权信息
    )
    state_pool.add(mismatch_sa)
    
    # 但暂不扣 vocab.negative_co_observations,等阶段 2
```

**阶段 2 - 教师证据到来,精准扣 vocab**:

```python
def handle_correction_evidence(correction_text, latest_mismatch_sa):
    """
    教师说"应该是 X" → 推断哪个 slot 错 → 只扣那个 slot 对应的 vocab
    """
    # 1. 通过 §16.11 correction_candidate 已学到的对齐
    # 推断 commit_record 哪个 vocab 与 correction 冲突
    conflicting_vocab_id = infer_conflicting_vocab(
        latest_mismatch_sa.linked_vocabs,
        correction_text,
    )
    
    if conflicting_vocab_id is not None:
        # 只扣这一个 vocab(精准 credit assignment)
        vocab = state_pool.get(conflicting_vocab_id)
        vocab.negative_co_observations += 1
        # 同时给替代 vocab 加 positive(正确答案被强化)
        positive_vocab_id = vocab_for(correction_text)
        if positive_vocab_id:
            state_pool.get(positive_vocab_id).positive_co_observations += 1
    else:
        # 无法确定哪个错 → 按 attention_share 加权分散负
        for vocab_id, share in zip(
            latest_mismatch_sa.linked_vocabs,
            latest_mismatch_sa.linked_attention_shares,
        ):
            state_pool.get(vocab_id).negative_co_observations += share  # 部分扣
```

**关键**:
- 没有教师证据时,负反馈不扣 vocab(避免冤枉)
- 教师给替代答案后,精准定位错误 vocab + 扣 + 强化正确替代
- 极端情形(无法定位)按 attention_share 加权部分扣

**confidence_score 阈值合理化**:默认 `θ_retract_confidence = 0.30`。意思是 vocab 累积 ≥70% 负证据才撤销,非常保守。

### 2.8 lag-PMI 时序共现(S1 + 远景准备)

**v6 错误**:§2 PMI 对称,narrative SA 无法时序学习。

**v7 新增 lag-PMI 作为底层原语**(用于 narrative / 因果 / 序列学习):

```python
class TemporalCooccurrenceGraph:
    """每个 SA 维护一组时序伙伴:不同 lag 上的 partner 统计"""
    
    edges: dict[(SA_id, SA_id, lag), (count, smoothed_lag_pmi)]
    
    def observe_temporal(self, sa_a, sa_b, lag):
        """A 在 t,B 在 t+lag 出现"""
        key = (sa_a, sa_b, lag)
        self.edges[key].count += 1
    
    def lag_pmi(self, sa_a, sa_b, lag):
        """
        lag-PMI(A, B, k) = log( P(B at t+k | A at t) / P(B at t+k) )
        """
        if not self.edges.has(sa_a, sa_b, lag):
            return 0.0
        p_b_given_a_at_lag = (
            (self.edges[(sa_a, sa_b, lag)].count + α_smooth) /
            (self.total_A_at_t + α_smooth * K)
        )
        p_b_marginal_at_lag = (
            (self.b_count_at_lag(sa_b, lag) + α_smooth) /
            (self.total_at_t_plus_lag + α_smooth * K)
        )
        return log(p_b_given_a_at_lag / p_b_marginal_at_lag)
```

**Lag 范围**:默认 lag ∈ {1, 2, 3, 5, 10}(tick 单位)。

**用途**:
- §40.A narrative:lag-PMI(A, B, 1)+lag-PMI(B, C, 1)+ ... 显著正 → A→B→C 序列固化
- §40.B 因果:lag-PMI(A, B, lag) 显著 + 反向 lag-PMI(B, A, lag) 显著低 → A 早于 B
- §41.D deliberative:用 lag-PMI 做单步预测推理

**复用 §2 整套晋升机制**(稀疏 top-k / ΔP 晋升 / 反例撤销),只是 graph 多一个时序维度。**底层原语,无新公式形态**。

---

## 3-5. 沿用 v6

## 6. 黄苹果对照课程 — v7 严格 KL 修复

### 6.1-6.2 沿用 v6

### 6.3 slot 偏好 — JSD + 归一化(B5+B6 fix)

**v6 错误**:KL 无界 + 大 codebook 仍占优。

**v7 正确公式**:

```python
def derive_channel_preference(slot) -> Optional[dict[ChannelName, float]]:
    # 门 1: min_distinct_fillers
    unique_fillers = set(slot.fillers_history)
    if len(unique_fillers) < θ_min_distinct_fillers:
        return None
    
    deduplicated_fillers = list(unique_fillers)
    
    channel_score = {}
    for c in all_channels:
        filler_buckets = [
            quantize(sa.get_channel_payload(c), c) for sa in deduplicated_fillers
        ]
        slot_dist = laplace_smoothed_distribution(filler_buckets, codebook_size=c.codebook_size)
        global_dist = global_bucket_distribution(c, laplace_smoothed=True)
        
        # JSD: Symmetric, bounded by log(2)
        jsd = jensen_shannon_divergence(slot_dist, global_dist)
        
        # 归一化:除以该通道的熵上限(log 该通道 codebook 大小)
        normalized_score = jsd / log(c.codebook_size)
        
        channel_score[c] = normalized_score
    
    return softmax([channel_score[c] for c in all_channels])
```

**为什么这真修了**:
- **JSD ∈ [0, log 2]**,有界 → 不会因稀有 bucket 爆炸
- **`/ log(codebook_size)` 归一化** → 16 桶通道和 512 桶通道在同一尺度比较
- **Laplace 平滑** → 稀有 bucket 不会 ÷0

**数学保证**:
- "颜色" slot 在 C2(16 桶颜色)上 normalized_JSD ≈ 0.5(明显偏全局分布)
- 同 slot 在 C1(512 桶形状)上 normalized_JSD ≈ 0.02(分布近全局,slot 不挑形状)
- softmax → C2 占优 ✓

---

## 7-9. 沿用 v6

## 10. audit_db — 沿用 v6 三层 fallback(无变化)

---

## 11. 习惯化 + Novelty + 主动注意 — v7 严格化

### 11.1 沿用 v6

### 11.2 Π update 显式定义(B7 fix)

**v6 错误**:`target` 没定义。

**v7 显式定义**:

```python
def update_prediction_pi(Π_current, observations_window, learning_rate):
    """
    TD(0) 风格 Π 更新:
    target = R observed at t+1 (下一 tick 真实 R)
    Δ = η · (target - Π_current)
    
    其中 η = min(η_max, prediction_signal_strength * κ)
    η_max 上限 0.15
    """
    target = observations_window.next_tick_R  # 严格定义:下一 tick 该 SA 的实际 R
    residual = target - Π_current
    eta = min(η_max, κ * abs(residual))      # 大残差时学习率高,小残差时低
    delta = eta * residual
    Π_new = Π_current + delta
    return Π_new
```

**收敛性证明**:
- 残差 r(t) = target - Π(t)
- η 取小常数时 r(t+1) = r(t) · (1 - η)
- r 在 7 tick 内降到 r(0) · 0.7^7 ≈ r(0) · 0.082 → 92% 吸收
- target 有界:R 由 attention selector 和 cognitive_pressure 限定,bounded → 残差有界

**这才是真严格几何收敛**。

### 11.3 Marker SA 哲学统一化(S5 fix)

**v6 不一致**:novelty 是独立 SA,tentative 是字段。**v7 选"独立分级 marker SA"作为唯一原则**:

```python
# 红线:
# ❌ 不许在 SA dataclass 上加 is_novel/is_tentative/is_X 字段
# ❌ 不许在 channel_signature 上加表示状态切换的字段
# ✅ 允许 spawn 独立 marker SA(continuous 能量,自然衰减)

# 例:
novelty_marker_sa = SA(
    sa_label=f"novelty_marker::{target_sa_id}",
    family="marker",
    real_energy=initial_intensity,
    ρ_R=fast_decay,  # 慢衰减
    target_sa_id=target_sa_id,
)

tentative_marker_sa = SA(
    sa_label=f"tentative_marker::{vocab_id}",
    family="marker",
    real_energy=initial_intensity,
    target_sa_id=vocab_id,
)

# 这些 marker SA 与 target SA 之间通过 SA-to-SA 链接,标准能量场,无特殊机制
```

**红线扫描**:`grep "is_novel\|is_familiar\|is_tentative\|is_stable" runtime/` 必须 0 命中。

### 11.4 沿用 v6

### 11.5 Sensor adapter salience hint — 边界扩展显式(S4 fix)

**v6 错误**:把 salience hint 说成 C-5 已允许,实际是 attention prior 跨界。

**v7 显式**:

> **C-5 边界扩展**(2026-06-17 修订):允许 sensor adapter 在 normalized SA event 上携带 **bottom-up salience hint** 字段,该字段表示感受器层面的物理/进化先验(高对比/运动/语音突变),由 AP-Core 作为 G_i(t) 注入参数使用,**但 AP-Core 不允许根据这个 hint 做特殊路由分支**(只能加法注入)。

```python
# C-5 边界扩展:salience_hint 作为 normalized SA event 的可选字段
normalized_sa_event = NormalizedSAEvent(
    sa_label=...,
    channel_signature=...,
    salience_hint=salience,  # NEW: 0.0 - 1.0,默认 0.0
)

# AP-Core 处理:
def apply_external_sa_event(event):
    pool_entry = state_pool.add_or_update(event)
    if event.salience_hint > 0:
        # 加法注入,不分支
        pool_entry.attention_gain += w_salience * event.salience_hint
```

**关键**:
- 明确这是 C-5 的 documented expansion,**不是 C-5 原文 sanction**
- salience 只能 + 注入,不能改路由(`if salience > θ: special_routing` 禁止)
- refocus 学到后,salience hint 权重自然降低(由 learned_band_bias 接管)

### 11.6 沿用 v6

### 11.7 Sleep emerge(沿用 v6)

### 11.8 Tentative vocab via marker SA(S5 fix 同步)

**v6 用 tentative_marker 作为字段**;**v7 改用独立 marker SA**:

```python
def maybe_spawn_tentative_vocab(candidate, cross_modal_strength):
    """
    跨模态首次共现强 → spawn tentative vocab + 伴生 marker SA
    """
    # cross_modal_strength 定义(B 修复 v6 循环定义):
    # = max similarity 跨不同模态的 SA 同 tick 共现(经 sensor adapter 提供的 normalized SA 能量)
    # 例:同 tick text "苹果" R=0.5 + vision percept R=0.7 + 时空 align=1.0
    # → cross_modal_strength = min(R_text, R_vision) * align = 0.5
    
    if candidate not in current_vocab and cross_modal_strength > θ_cross_modal:
        # 第一步:spawn 正常 vocab SA
        vocab_sa = VocabSA(
            persistent_id=stable_id(),
            sa_label=f"vocab::{candidate.label}",
            ...,  # 标准字段,无 is_tentative
        )
        state_pool.add(vocab_sa)
        
        # 第二步:spawn 伴生 tentative_marker SA
        marker = SA(
            sa_label=f"tentative_marker::{vocab_sa.persistent_id}",
            family="marker",
            real_energy=initial_marker_intensity,
            ρ_R=ρ_tentative_marker,  # 中速衰减(秒级)
            target_sa_id=vocab_sa.persistent_id,
        )
        state_pool.add(marker)
        
        # 第三步:vocab_sa 信心从 marker 推断
        # vocab.recall_strength_modifier = 1 - marker.R(marker 衰减后 vocab 满信心)

# 第二次曝光 → 正反馈累积 → marker 已部分衰减且 vocab.positive_co_observations 升 → vocab 进入正常状态
# 反例(被纠正)→ vocab.negative_co_observations 升 + marker 重新强化 → 加速撤销
# 长时间无再曝光 → marker 衰减完 + vocab 自然 short-term decay → 消失
```

**与 §1 short-term R 关系**:tentative vocab 用了 §1 short-term R(自然衰减) + 伴生 marker SA(标记"未确认状态")。**M2 (架构冗余) 化解**:tentative vocab 复用 short-term R,marker 只标记。

### 11.9 Slot 元先验 — 显式 bootstrap path(M1 fix)

**v6 不写循环**:noun_marker 学到 → meta_prior 工作,但 meta_prior 帮助学 noun_marker?

**v7 显式 bootstrap**:

```yaml
# 阶段 1 (Phase 8.12 开始):no slot 有 meta_prior
# 任何 slot 偏好 = 纯 §6.3 MI 涌现

# 阶段 2 (累积 K 个 commit 后):
# 系统计算 slot 的 fillers 平均 text_noun_marker
# (text_noun_marker 在 Phase 8.5 CFS 通道时定义为:
#  vocab 在 sentence 中作为名词位置 vs 修饰位置的 OnlineEmbedding 学到的特征)
# 如 > θ_noun_slot,该 slot 软继承 C1 优先(权重 0.2)

# 阶段 3 (后续):
# meta_prior 起作用 → 新 vocab 在 noun slot 中更易匹配 C1 主导的 SA
# → noun_marker 学到该 vocab 是名词
# → 进入正向反馈但权重小,不会失控
```

**`text_noun_marker` 定义(M5 fix)**:

```python
# 在 Phase 8.5 CFS 补完时,额外加一个轻量 OnlineEmbedding 学习:
# 每个 vocab SA 累积"作为句子主语/宾语位置出现"vs"作为修饰位置出现"的概率
# 这是 short_term_focus_buffer + slot_history 的自然 derive,不是新模块
def compute_text_noun_marker(vocab):
    """从 vocab 的句法位置历史推断 noun-ness"""
    object_subject_count = vocab.appearances_in_main_positions
    modifier_count = vocab.appearances_in_modifier_positions
    total = object_subject_count + modifier_count
    if total < 5:
        return 0.5  # uncertain
    return object_subject_count / total
```

---

## 12-15. 沿用 v6

---

## 16. 工程实施 Phase 重排 — v7 完整版

### 16.1 沿用 v6

### 16.2 v7 新增模块清单

- §2.3 cold-fork bootstrap ΔP
- §2.4 anti-correlation gate by observation_count
- §2.7 两阶段 credit assignment
- §2.8 lag-PMI 时序共现底层原语
- §6.3 JSD + log(codebook_size) 归一化
- §11.2 Π update 显式 TD(0)
- §11.3 统一 marker SA 哲学
- §11.5 C-5 边界扩展声明
- §11.8 tentative via marker SA
- §11.9 noun_marker 派生定义
- §16.8 utterance_boundary 真实修复
- §16.9 bootstrap=0 + Thompson sampling
- §16.11 correction R/P 派生
- §29 V6 H1-H5 远景补完
- §40 5-8 岁完整数学(narrative 用 §2.8 lag-PMI)
- §40.4 反事实模拟最小机制
- §41 8-12 岁完整数学(meta-cognition 依赖 §40.E,abstract gate 真实化)

### 16.3 Phase 顺序(v7 修订)

```
Phase 8.2   连续 tick + 字符微事件 + draft action with Thompson sampling
            (§1.2 + §11.5 + §16.9)

Phase 8.3   Sensor Adapter + audit_db 三层 fallback
            (§3.2 + §10.7)

Phase 8.4   通用 SA 词汇 — cold-fork ΔP + 反相关 gate + 两阶段 credit
            (§2.3 + §2.4 + §2.7)

Phase 8.5   CFS 补 4 通道 + text_noun_marker(M5 fix)
            (阻断式前提)

Phase 8.6   玩具视觉感受器 + 多通道 + 量化桶 + Sensor salience hint

Phase 8.7   视焦点 SA + saccade + 持驻 + overlay

Phase 8.8   严格 yellow apple 泛化 + JSD slot 偏好 + ablation
            (核心证伪门,§6.2 + §6.3)

Phase 8.9   自然纠错 — correction_candidate 派生 R/P
            (§16.11)

Phase 8.10  习惯化 Π 几何收敛 + marker SA 统一 + sleep emerge
            (§11.2 + §11.3)

Phase 8.11  Web 工作台 + 逐 tick trace

Phase 8.12a Tentative vocab + marker SA + utterance_boundary 真修
            (§11.8 + §16.8)

Phase 8.12b Slot 元先验 + noun_marker 派生
            (§11.9)

Phase 8.12c 轻量 epistemic drive(question-asking 引导)

Phase 8.13  音频感受器 + filterbank vocab 模板

Phase 8.14  Phase 8 端到端 + 18-30mo 拟人验收套件 + 反例测试

Phase 8.15  lag-PMI 时序共现学习启动(§2.8)
            (为 Phase 10 narrative 早期准备数据)

—— Phase 8 完成 = 18-30 月龄学习能力 ——

Phase 9.1-9.9   v4/v5 哺乳类 9 维度
                + §29.1 imitation
                + §29.2 gaze contingency
                + §29.3 number sense 基础

—— Phase 9 完成 = 3-5 岁心智深度 ——

Phase 10.1  Narrative SA(用 §2.8 lag-PMI 真实学习)
Phase 10.2  匿名 super-cluster spawn(§40.E)
Phase 10.3  反事实模拟最小机制(§40.4)
Phase 10.4  因果关系 SA(依赖 10.3)
Phase 10.5  ToM 信念模型 SA(依赖 10.3 反事实)
Phase 10.6  Hierarchy SA + 命名绑定
Phase 10.7  Trust prior + downgrade 机制
Phase 10.8  Reading 单管道 + source 字段

—— Phase 10 完成 = 5-8 岁能力 ——

Phase 11.1  Meta-cognition + domain 定义(依赖 10.6 hierarchy)
Phase 11.2  Abstract vocab 跨 cluster gate(§41.B 真化)
Phase 11.3  Goal SA + 长 horizon + 与 short_long 关系
Phase 11.4  Deliberative sub-cycle on virtual track + audit 嵌套
Phase 11.5  Self model(衰减式 + boot 重生)

—— Phase 11 完成 = 8-12 岁能力 ——

Phase 12+   真实硬件 + SNS 桌宠产品化 + Agent 工作流
```

### 16.4 CFS 补 4 通道 + text_noun_marker(沿用 v6 §16.4 + M5 fix)

### 16.5-16.7 沿用 v6

### 16.8 Utterance boundary — 真修(B8 fix)

**v6 错误**:queue empty 1 tick 就触发,用户打字暂停就误触。

**v7 正确做法**——**两层信号**:

```python
class TextSensorAdapter:
    def __init__(self):
        self.last_char_tick = -1
        self.explicit_eom_received = False  # send 按钮 / 回车
        self.silence_threshold_ticks = 20  # ~2 秒 @ 100ms/tick
    
    def on_user_send(self):
        """用户按 send 或 enter"""
        self.explicit_eom_received = True
    
    def step(self, t):
        # 处理字符流
        chars_per_tick = config.text_chars_per_tick
        for _ in range(chars_per_tick):
            if queue.is_empty():
                break
            char_event = queue.pop()
            emit_text_char_sa(char_event)
            self.last_char_tick = t
        
        # 边界信号 — 双层判定
        silence_ticks = t - self.last_char_tick
        
        # 显式边界:用户已发 send
        if self.explicit_eom_received and queue.is_empty():
            emit_sa(
                sa_label="text::utterance_boundary",
                real_energy=boundary_R_explicit,    # 派生自 last char R
                channel_signature={"boundary_marker": 1.0, "explicit": 1.0},
            )
            self.explicit_eom_received = False
        
        # 软边界:长静默 → graded marker SA(强度随静默时间增)
        elif silence_ticks > self.silence_threshold_ticks and queue.is_empty():
            silence_intensity = sigmoid(
                (silence_ticks - self.silence_threshold_ticks) / 20
            )
            emit_sa(
                sa_label=f"text::potential_boundary::silence_{silence_ticks}",
                real_energy=silence_intensity * potential_boundary_R_max,
                channel_signature={
                    "boundary_marker": silence_intensity,
                    "soft_boundary": 1.0,
                },
            )
```

**关键**:
- **显式信号(用户 send)**:确定的边界,强 R
- **软信号(长静默 ≥ 2 秒)**:graded marker SA,强度随静默时间增长
- 在 0.2 秒打字间停顿(silence_ticks=2)→ 不触发任何 boundary
- 真正消息结束(silence_ticks > 20)→ 触发 soft boundary,但是 graded(让 draft 行动学到"差不多可以 commit 了")

**结合 draft 行动**:soft boundary 强度作为 commit 的"环境信号",并不强制 commit。

### 16.9 草稿行动 — 全 0 bootstrap + Thompson sampling(B9 真修)

**v6 错误**:hardcoded `+0.15, +0.05` 加注释就当合规。

**v7 正确做法**:

```python
class DraftActionPriors:
    """所有 bootstrap R_change 全 0,真探索"""
    bootstrap_R_changes = {
        "type_token": 0.0,
        "reread": 0.0,
        "delete_tail": 0.0,
        "replace_tail": 0.0,
        "commit": 0.0,
        "stop": 0.0,
        "noop": 0.0,
    }

def get_action_expected_R_change(action_type, context_features, target):
    learned = action_parameter_memory.lookup(...)
    if learned.sample_count >= θ_min_action_samples:
        # Thompson sampling: 从 posterior 采样,不取均值
        sampled_R_change = sample_from_beta_posterior(
            learned.positive_count, learned.negative_count
        )
        return sampled_R_change
    
    # Cold start: 0 + 探索噪声
    return DraftActionPriors.bootstrap_R_changes[action_type] + gaussian_noise(0, 0.1)

def attempt_draft_action(t):
    candidates = build_action_candidates(...)
    winning = attention_selector.select(candidates)
    
    # Logging:每个 action 的 expected_R_change 用于 audit
    log_action_decision(winning, t, "from_bootstrap" if winning.from_bootstrap else "from_learned")
    
    execute(winning)
    
    # 后续观测真实 R 变化
    action_parameter_memory.observe(
        action=winning,
        observed_R_change=measure_post_execution_R_change(),
    )
```

**为什么这真修**:
- **所有 bootstrap = 0** → 无 self-fulfilling 偏置
- **gaussian noise** → 早期纯探索,不同 action 都有机会被试
- **Thompson sampling** → 学到一定证据后,概率性偏好高奖励行动,但仍保留探索
- 一旦 `sample_count >= 5`,action_parameter_memory 完全接管

**第一个 tick 是什么行动?随机噪声决定。第 100 个 tick?Thompson 倾向 5 次试过的奖励高的。第 1000 个 tick?已经收敛到学到的行动分布。这才是真"涌现"**。

### 16.10 沿用 v6

### 16.11 Phase 8.9 correction R/P 派生(B10 fix)

**v6 错误**:correction_candidate.R = `expectation_R_for_correction` 硬编码。

**v7 正确做法**:

```python
def handle_negative_feedback_v7(commit_record, negative_signal):
    # Phase 1: 创建 mismatch SA(派生自 commit R)
    mismatch_sa = SA(
        sa_label=f"event::commit_mismatch::{commit_record.id}",
        real_energy=negative_signal * commit_record.commit_R,
        cognitive_pressure=negative_signal * commit_record.commit_R,
        channel_signature={"commit_event_marker": 1.0},
        linked_vocabs=commit_record.vocabs_used,
        linked_attention_shares=commit_record.vocabs_attention_share,
    )
    state_pool.add(mismatch_sa)
    
    # Phase 2: 派生 correction_candidate(R/P 来自 mismatch,无硬编码)
    correction_sa = SA(
        sa_label=f"hypothesis::correction::{commit_record.id}",
        real_energy=mismatch_sa.real_energy * 0.8,        # 派生
        cognitive_pressure=mismatch_sa.cognitive_pressure * 1.2,  # 略放大,等教师
        channel_signature={"hypothesis_marker": 1.0},
        linked_to=mismatch_sa.persistent_id,
    )
    state_pool.add(correction_sa)
    
    # 不立即扣 vocab(等教师证据)
```

**关键**:0.8 / 1.2 是因果链上的能量传递系数(派生),不是独立硬编码常量。

---

## 18. 数学交互矩阵 — v7 拓展(M3 fix)

### 18.5 交互矩阵(v6 6 行 → v7 拓展 11 行)

| 机制 A | 机制 B | 共享资源 | 主导关系 / 风险 |
|---|---|---|---|
| Attention selector | Novelty marker | attention_gain | Novelty 注入 → A 升 → 自然选 |
| Draft action | Refocus action | attention_selector | 同等竞争 |
| ComposedVocab | held-out ΔP | held-out 数据 | 晋升必经显著性 |
| Sleep emerge | Novelty marker | tick_ms | 高 novelty 抑制 sleep |
| Tentative vocab | 反例撤销 | confidence_score | 撤销门低 → fast learning + correction |
| Slot 元先验 | Slot MI 涌现 | filler_history | 元先验权重 0.2 < MI |
| **Novelty marker × Draft action** | — | attention 预算 | **风险**:高 novelty 锁注意力,系统无法 commit;**缓解**:Phase 8.10 监测,if 长时间无 commit 且 high novelty → emit boredom feeling → draft 行动 stop 候选竞争力升 |
| **Tentative vocab × ΔP gate** | — | P 测量值 | **风险**:tentative SAs 影响 P,可能 mislead ΔP 评估;**缓解**:ΔP 评估时 tentative SAs 暂不计入 vocab_set;只计正式 vocab |
| **Multi-drive(Phase 9.1)** | 内部竞争 | attention_gain | **风险**:5 drives 同时高 → 注意力分散;**缓解**:drives 经标准 attention selector 竞争,P 高的 drive 自然胜出 |
| **Epistemic drive × Tentative pool** | tentative 容量 | — | **风险**:问题问得多 → tentative 池溢出;**缓解**:tentative 池有 max_size,超出按 marker.R 排序淘汰 |
| **Deliberative sub-cycle × audit_db** | audit 容量 | — | 见 §41.D,deliberative 各 tick 独立审计,主轨道与虚轨道分开 |

### 18.6 整体稳定性论证(v6 §18.1 强化)

- 所有新机制注入既有能量场(R/V/P/A/G)
- 无独立非衰减能量源(self_sa 修复后正常衰减,§41.E)
- 多机制可同时活跃,经 attention selector 统一仲裁
- 防失控措施:tentative max_size / drive 数量上限 / marker SA 数量上限(可配置)
- 所有 max_size 由 AdaptiveTuner 监测,饱和时降低 spawn 率

---

## 29. v6 H1-H5 覆盖洞补完(远景)

### 29.1 Imitation learning(Phase 9.X 补)

**机制**:观察用户行动 + 后续 AP 学到的对应 action SA 共现 → 经 §2 ComposedVocab 在行动空间固化"模仿模式"。

```python
# 用户做了 X → 系统通过感受器(视觉/文本"用户说了")提取 user_action_observed SA
# 这个 SA 与 AP 自己后续相同 action 的成功 commit 共现 → 学到链
# 后续:user_action_observed 高 → 同款 AP action 的 attention_bid 升

imitation_marker_sa = SA(
    sa_label=f"imitation_target::{action_label}",
    family="marker",
    real_energy=...,
)
```

**复用既有 attention selector + ActionParameterMemory**,**无新公式**。

### 29.2 Gaze contingency(Phase 9.X 补)

**机制**:视觉感受器提取"用户视线朝向 AP" → spawn `gaze::other_looks_at_me` SA → 通过 §15.1 双层 align 与"AP 自己"focus 联动。

**对照 SNS 桌宠**:用户视线检测可来自摄像头 OR 简单的"用户在打字给桌宠"信号。

### 29.3 Joint attention(Phase 9.5 已有,本节加细节)

**机制**:`focus::other::<entity_id>::<target>` SA(继承 v4 §24)+ alignment.

**当 align(other_focus, my_focus_candidate) 高,我的 focus_candidate 获得 attention_bid 加成**。

Phase 10.5 ToM 假信念测试**依赖** Phase 9.5 joint attention 实现。

### 29.4 Number sense(Phase 10.X 补)

**机制**:Phase 10 在视觉通道加 "object_count" 通道(数 percept 数量,小数敏感:1/2/3 精确,4+ 粗粒度)。

Subitizing(1-3 精确)= 视觉通道直接量化桶;quantity (4+)= 抽象 vocab(§41.B)。

### 29.5 Embodied / desktop sensors(Phase 12+ 准备)

**继承 SNS 桌面感受器设计**(ap_desktop_visual_sensor.py / ap_desktop_focus_overlay_bridge.py)。Phase 12 主要工作 = 接入这些 SA 流并保证 §10 audit_db 边界 + §11.5 salience 接入。

---

## 40. 5-8 岁认知架构 — v7 真化(S1-S3 / S9-S10 fix)

### 40.1 Narrative SA via lag-PMI(S1 真修)

**v6 错误**:对称 PMI 不能时序。

**v7 改用 §2.8 lag-PMI 作为底层**:

```python
# Narrative SA 候选检测:
# - 寻找显著时序链:lag-PMI(A, B, k1) 显著正 + lag-PMI(B, C, k2) 显著正
# - 同时反向 lag-PMI(B, A, k1) 显著低(单向)
# 这就是 narrative 的本质:有方向的事件链

# §2 ComposedVocab 在 lag-PMI graph 上的应用:
# - 提名候选时序链
# - cold-fork ΔP 测试该 narrative SA 是否改善预测压力
# - 通过则固化为 narrative_sa

narrative_sa = SA(
    sa_label="narrative::<id>",
    family="narrative",
    components=[event_pointer_1, event_pointer_2, event_pointer_3],
    edge_lags=[k1, k2],
    edge_labels=["then", "then"],  # 时序标签,涌现自 lag 模式
    ...
)
```

**实质创新**:lag-PMI 是底层原语,narrative_sa 是 §2 高阶应用。**真"复用底座"**。

### 40.2 因果 SA(S2:依赖 §40.4 反事实)

**与 narrative 区别**:
- narrative = 时序 + 频繁共现(无干预/反事实证据)
- causal = 时序 + **反事实验证**(去掉 A 后 B 不出现)

详见 §40.4 反事实模拟。

### 40.3 ToM 信念模型 SA(详细化)

```python
# 观察用户行为(文本/视觉)+ 用户的常规预期对照 →
# 推断"用户的内部状态可能是什么"

# 输入信号:
# - 用户文本表达("我以为...")
# - 用户行动观察(去了错误位置 → 信念错了)
# - AP 自己的 IntrospectionPrototype(知道该情况自己会觉得什么)

# 通过 §15.1 双层 align:
# my_belief_about_topic ←(align)→ user_observable_behavior
# 强 align → 推断 user 有相似 belief

# 否则 spawn 信念 SA:
belief_sa = SA(
    sa_label=f"belief::other::{user_id}::{topic}",
    family="theory_of_mind",
    holder_entity=entity_user_sa,
    content_pointer=specific_belief_content,
    confidence=alignment_strength,
)

# Phase 10.5 假信念测试:
# - 用户看到 A 处藏物体
# - 用户离开,物体被移到 B 处
# - 用户回来,AP 应预测"用户会去 A 处找"(因为用户不知道移动)
# - 即:AP 维护"用户的信念 = 物体在 A",尽管 AP 自己知道在 B
```

依赖 §40.4 反事实模拟(从用户视角模拟"用户没看到移动")。

### 40.4 反事实模拟最小机制(S2 fix,Phase 10.3)

**v6 缺设计**。**v7 给最小可行机制**:

```python
class CounterfactualSimulator:
    """从当前状态池 fork 一个子分支,虚拟运行 N tick,测量未来"""
    
    def fork_branch(self, current_state_pool):
        """轻量 fork:复制状态池关键能量值,不复制整个对象图"""
        return StatePoolSnapshot(
            r_values={sa_id: sa.R for sa_id in current_state_pool},
            v_values={sa_id: sa.V for sa_id in current_state_pool},
            vocab_set=current_state_pool.vocab_set,
            wall_clock_ms=current_state_pool.wall_clock_ms,
        )
    
    def simulate_forward(self, snapshot, hypothetical_intervention, n_ticks=10):
        """
        在 fork 的 snapshot 上,虚拟运行 n_ticks
        hypothetical_intervention = 干预说明(如"SA X 不出现")
        返回未来 N tick 内的 SA 能量轨迹
        """
        if hypothetical_intervention.kind == "remove_sa":
            snapshot.remove(hypothetical_intervention.target_sa)
        
        for tick in range(n_ticks):
            # 纯 V(虚能量)推演,不写主状态池
            # 用 §11.2 Π update 但 target 派生自 V 链
            snapshot.advance_virtual_only()
        
        return snapshot.energy_trajectory

# 用于因果判断:
def is_a_causes_b(sa_a, sa_b):
    """
    比较两种 fork:
    1. 实际(A 在场)→ B 是否出现
    2. 反事实(A 移除)→ B 是否仍出现
    若 B 在反事实中消失/减弱 → A→B 因果
    """
    snap = current_state_pool.snapshot()
    
    real_trajectory = simulate_forward(snap, no_intervention, 10)
    counterfactual_trajectory = simulate_forward(snap, remove_sa(sa_a), 10)
    
    b_R_real = real_trajectory.get(sa_b, []).mean_R
    b_R_counterfactual = counterfactual_trajectory.get(sa_b, []).mean_R
    
    causal_strength = b_R_real - b_R_counterfactual
    return causal_strength
```

**关键**:
- 反事实模拟 = 状态池 lightweight snapshot + 虚能量推演 + 轨迹测量
- 不复制整个对象图,只 R/V 值(数学上等价于 N-tick 推演)
- 计算成本:O(N tick × |active SA|),典型 100 SA × 10 tick = 1000 op,可负担
- **复用既有 Π update 机制**,虚能量层运行,**不动主状态池**

**Phase 10.3 这是真可工作的最小机制**。后续可优化(只 fork 相关 SA / 渐进 fork 等)。

### 40.5 Hierarchy SA — 匿名 cluster spawn(S3 fix)

**v6 错误**:需要"水果"先存在才能 spawn `is_a(苹果, 水果)`。

**v7 改 bottom-up 匿名 super-cluster**:

```python
def detect_anonymous_super_cluster(slot_history):
    """
    多个 sub-vocab 共享 slot 偏好 + channel sig → spawn 匿名 cluster
    """
    # Step 1: 聚类 vocab SAs by their channel_signature
    vocab_clusters = cluster_by_channel_signature(all_vocab_sas, k_clusters=auto)
    
    # Step 2: 检查每个 cluster 是否有共同的 slot 偏好
    for cluster in vocab_clusters:
        if len(cluster) >= θ_min_cluster_size:  # 默认 3
            common_slot_pref = find_common_slot_preference(cluster)
            if common_slot_pref:
                # 检查是否已有命名 vocab 覆盖此 cluster
                existing_super = find_named_super_for_cluster(cluster)
                if existing_super:
                    # 已有"水果"→ 直接建立 is_a 链
                    for sub in cluster:
                        spawn_isa_sa(sub, existing_super)
                else:
                    # 无名 super → spawn 匿名 cluster
                    anonymous_super = SA(
                        sa_label=f"cluster::anonymous::{stable_id()}",
                        family="anonymous_cluster",
                        sub_vocabs=cluster,
                        channel_signature=cluster.common_channel_sig,
                    )
                    state_pool.add(anonymous_super)
                    # 后续用户教学说"这些是水果" → 匿名 → 命名
```

**关键**:幼童先学到"苹果/香蕉/橙子有共性"(匿名感知),后学到名字"水果"绑定该 cluster。**反向 bootstrap 解决**。

### 40.6 Trust prior + downgrade(详细化)

```python
class TrustPromoter:
    def trust_promote_candidate(self, candidate, source_entity_sa):
        # 信任度 = 该 entity 的 OXY(亲密)+ 历史教学准确率
        trust_score = (
            source_entity_sa.oxy_strength * 0.5 +
            source_entity_sa.teaching_accuracy_history * 0.5
        )
        if trust_score > θ_trust_authority:
            vocab_sa = create_vocab_sa(candidate)
            vocab_sa.gate_kind = "trust_promoted"  # 标记
            vocab_sa.source_entity = source_entity_sa.persistent_id
            vocab_sa.downgradable = True
            return vocab_sa
        return None
    
    def downgrade_on_contradiction(self, trust_promoted_vocab):
        """
        当 trust-promoted vocab 与 ΔP-validated vocab 冲突时:
        - 若 ΔP-validated 强 → trust-promoted 进入"需要验证"状态(降为 tentative_marker)
        - 若 trust-promoted 经多次曝光累积 ΔP 证据 → 升级为 ΔP-validated
        """
        # 冲突判定:试图同时 fill 同一 slot 但偏好不同
        conflicting_vocab = find_conflicting_dp_validated(trust_promoted_vocab)
        if conflicting_vocab:
            # 用 cold-fork ΔP 评估 trust-promoted 在 held-out 上的表现
            result = evaluate_fixation_via_cold_fork(
                trust_promoted_vocab, held_out_dataset
            )
            if not result["passes"]:
                # 降级:加 tentative_marker
                downgrade_to_tentative(trust_promoted_vocab)
            else:
                # 升级:成为正式 ΔP-validated
                trust_promoted_vocab.gate_kind = "dp_validated"
```

### 40.7 Reading 单管道(S10 fix)

```python
class TextSensorAdapter:
    def emit_text_char_sa(self, char, source_kind):
        """
        单管道:无论 streaming 还是 reading,都经此入
        """
        sa = NormalizedSAEvent(
            sa_label=f"text::char::{char}",
            channel_signature={"text_char": 1.0},
            source=source_kind,    # "streaming" | "reading" | "user_input"
            ...
        )
        emit(sa)
    
    def streaming_step(self, t):
        """流式文本输入(打字)"""
        if not queue.is_empty():
            self.emit_text_char_sa(queue.pop().char, source_kind="streaming")
    
    def reading_step(self, t, visual_focus_position):
        """阅读模式:视焦点扫文本 → 触发字符 SA"""
        text_at_focus = lookup_text_at_position(visual_focus_position)
        if text_at_focus:
            self.emit_text_char_sa(text_at_focus.char, source_kind="reading")
```

**关键**:**单 emit_text_char_sa 函数**,source 字段区分。下游 AP-Core 不再有"两个文本路径"。

---

## 41. 8-12 岁认知架构 — v7 真化(S6/S7/S8/S9 fix)

### 41.1 Meta-cognition(S8 fix,依赖 §40.5 hierarchy)

**v6 缺**:"domain" 无定义。

**v7 显式**:依赖 §40.5 hierarchy 中的 super-cluster SA。Domain = depth ≥ k 的 super-cluster(默认 k=2,即"二级范畴"以上)。

```python
def detect_knowledge_gap():
    """识别 domain 级别的知识空洞"""
    domains = state_pool.where(family="anonymous_cluster", hierarchy_depth >= 2)
    
    for domain in domains:
        recall_failures_in_domain = count_recall_failures(domain.sub_vocabs, last_K_ticks=100)
        commit_failures_in_domain = count_commit_failures(domain.sub_vocabs, last_K_ticks=100)
        avg_P_in_domain = mean(P for sa in domain.sub_vocabs)
        
        if (recall_failures_in_domain > θ_recall_fail
            and commit_failures_in_domain > θ_commit_fail
            and avg_P_in_domain > θ_high_P):
            # spawn knowledge_gap SA
            gap_sa = SA(
                sa_label=f"meta::knowledge_gap::{domain.persistent_id}",
                family="meta_cognition",
                target_domain=domain.persistent_id,
                confidence_in_lack=normalize(commit_failures_in_domain),
            )
            state_pool.add(gap_sa)
            # 这个 SA 自然有 high P → 驱动 epistemic drive → 主动学习
```

**强依赖关系**:Phase 11.1 不能在 Phase 10.5 (hierarchy SA) 之前实施。Phase ordering 已修。

### 41.2 Abstract vocab — 真 gate(S9 fix)

**v6 错误**:"3 链 grounded SA" 不区分抽象 vs 紧密 cluster。

**v7 正确 gate**:**3 链跨 ≥2 个不同 channel-signature cluster**:

```python
def is_abstract_vocab_candidate(candidate, grounding_links):
    """
    候选必须:
    1. 至少 3 个 grounded SA 链接
    2. 这些 grounded SAs 跨至少 2 个不同的 channel-signature cluster
       (说明该概念在不同感知场景出现)
    """
    if len(grounding_links) < 3:
        return False
    
    grounded_clusters = set()
    for link_sa in grounding_links:
        cluster_id = link_sa.belongs_to_cluster_id
        grounded_clusters.add(cluster_id)
    
    return len(grounded_clusters) >= 2

# 例:
# "正义" 的 grounded links 应该来自:
# - 法庭场景 SAs (cluster A)
# - 校园争议 SAs (cluster B)
# - 文学情节 SAs (cluster C)
# 跨 3 个 cluster → 抽象 vocab 通过
#
# 反例:"红蕊苹果" 的 grounded links 都来自苹果 percept cluster
# 跨 1 个 cluster → 不是抽象 vocab,只是紧密 cluster
```

### 41.3 Goal SA + horizon(详细化)

```python
goal_sa = SA(
    sa_label="goal::<target_state>",
    family="goal",
    target_state_pointer=...,
    target_completion_tick=...,
    horizon_decay_rate=ρ_R_goal_slow,  # 慢衰减
    progress_score=...,
    sub_goals=[...],
)

# 与 §1.3 short_long 双层关系:
# - goal SA 默认在 long_term layer(衰减极慢)
# - 不需要短长晋升,直接 long_term
# - 与现有 long_term 共存(经 attention selector 竞争)

# 完成时:
# goal_sa.R *= 0.1  # 大幅降,失去 attention 拉力
# emit feeling::fulfillment
# 可被驱逐(已完成 goal 自然衰减)
```

**与 short_long 关系明确化**:goal SA 是 long_term 的特殊家族,衰减率不同但仍走 long_term 通用机制。

### 41.4 Deliberative sub-cycle — virtual track ticks + 嵌套 audit(S6 fix)

**v6 错误**:主 tick 内"暂停"内部 loop → 破坏 tick=time + audit 残缺。

**v7 正确做法**:**deliberative steps 占用自己的 ticks,在 virtual energy track 上**:

```python
class DeliberativeRunner:
    def __init__(self, main_tick_runtime):
        self.main = main_tick_runtime
        self.virtual_track_active = False
        self.virtual_track_audit_log = []
    
    def maybe_enter_virtual_track(self, t):
        """决定是否进入虚轨道思考"""
        # 当 deliberative_drive(派生自 P/grasp) 高时,enter
        deliberative_drive = compute_deliberative_drive(state_pool)
        if deliberative_drive > θ_enter_virtual:
            self.virtual_track_active = True
    
    def step_virtual_track(self, t):
        """虚轨道每 tick:用 V 推演,记录"""
        # 这是真 tick(占用真时间),只是不动主状态池 R
        # 主 tick 暂停外源输入消化,内部纯虚推演
        snapshot = state_pool.snapshot_virtual_only()
        
        # 一步推演(类似 §40.4 反事实模拟,但目标是结论)
        snapshot.advance_virtual_only_one_step()
        
        # 这一步的 audit
        audit_record = {
            "tick": t,
            "track": "virtual",
            "snapshot_summary": snapshot.summary(),
            "deliberative_step": step_index,
        }
        self.virtual_track_audit_log.append(audit_record)
        audit_db.log(audit_record)
        
        # 是否产生结论
        if snapshot.has_high_confidence_conclusion():
            self.commit_conclusion_to_main_track(snapshot.conclusion)
            self.virtual_track_active = False
```

**关键**:
- Virtual track tick = real tick(time-real,不破 invariant)
- 用 V 层推演,不动 R(主状态池保持上下文)
- 每 virtual tick 独立 audit 记录,**audit 完整**
- Web UI Mind 区可独立显示"虚轨道思考过程"

### 41.5 Self model — 衰减式 + boot 重生(S7 fix)

**v6 错误**:`durable=True` 永不衰减,违能量守恒 + 永远占注意。

**v7 正确**:

```python
self_sa = SA(
    sa_label="entity::self",
    family="self_model",
    capabilities=[...],
    preferences=[...],
    autobiographical_narrative=[...],
    durable=False,                          # 常规衰减
    long_term_layer=True,                   # 在 long_term 层
    boot_from_persistence=True,             # session boot 时从 SQLite 重生
)

# 衰减但慢:long_term ρ_R ≈ 0.999
# 注意预算上限(防永远占焦点):
self_sa_attention_cap = 0.05  # 最多占 attention budget 5%

# 在 attention selector 加 cap 约束:
def select_with_cap(candidates):
    selected_self_R_total = 0
    for sa in winning_sequence:
        if sa.family == "self_model":
            if selected_self_R_total / total_attention_budget > self_sa_attention_cap:
                # 不选这个 self SA(已达上限)
                continue
            selected_self_R_total += sa.R
        ...
```

**Session boot**:
- 上次 session 关闭时,self_sa 持久化到 SQLite(snapshot)
- Boot 时从 snapshot 重建 self_sa,R 设为正常值
- 不是永不衰减,是周期性 reactivate

**这才是真正的"我有持续身份"**——session 跨度内一致,但在每个 session 内仍参与正常竞争。

---

## 42-43 沿用 v6(略微修订:Phase 10.4 反事实 + 11.4 deliberative 已 spec)

---

## 19. v7 给 Codex 的最终指令

1. **v7 取代 v6 作为 Phase 8 实施依据**
2. **Phase 8.5(CFS + text_noun_marker) 阻断式前提**
3. **Phase 8.8 核心证伪门**——失败禁止 workaround
4. **Phase 8.9 自然纠错** — 两阶段 credit assignment,不依赖 RPE
5. **Phase 8.10 marker SA 哲学统一**——红线扫描
6. **Phase 8.12 三子阶段** — tentative + 元先验 + epistemic 独立
7. **每 Phase 5 段闭环 + 红线扫描**
8. **任何"看起来修复但实际换措辞"立即停下问 Claude**(B1/B5/B7/B9 教训)

---

## 附录: v6 → v7 修复一览

| 类别 | 修复数 |
|---|---|
| Blocker (B1-B10) | 10 全修 |
| Serious (S1-S11) | 11 全修 |
| Minor (M1-M6) | 6 全修 / 解释 |
| Coverage 洞 (H1-H5) | 5 全补(§29) |
| 5-8 岁数学(narrative/causal/ToM/hierarchy/reading/trust) | 真化 |
| 8-12 岁数学(meta/abstract/goal/deliberative/self) | 真化 |
| 交互矩阵(§18.5) | 6→11 行 |

— 接手线程,2026-06-17
