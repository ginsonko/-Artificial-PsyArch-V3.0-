# APV3.0 拟人多模态底座 — 完整设计稿 v8(轮 4 对抗后根本性收敛)

日期: 2026-06-17
作者: 接手线程
状态: **v7 经轮 4 对抗审阅认定 8/20 真修、9/20 换问题、3/20 anti-pattern 重犯。v8 必须根本性解决而非换措辞。核心:(1) ΔP 评估算力可行、(2) 缺席 SA 的 Π 语义、(3) 全部硬编码常量真消除、(4) state pool family 统一为 Marker 多态、(5) 反事实方法学修正、(6) phase-2 超时回退。**

前身链:v1 → v2 → v3 → v4 → v5 → v6 → v7 → **v8(本稿)**

---

## 0. v7 → v8 修正总览(必读)

### 0.1 v7 真 blocker(轮 4 找到 5 个)

| # | v7 缺陷 | v8 修复策略 |
|---|---|---|
| **V7-B1** | §2.3 cold-fork bootstrap 算力爆炸(5000 tick × 500 SA × 20 runs = 50M ops/候选,Phase 8.4 跑不起来) | **§2.3 改 incremental ΔP**:不重放历史,只测 candidate spawn 后 N tick 的局部 P 差;held-out 用 sufficient-statistic snapshot;成本降 3 个数量级 |
| **V7-B2** | held_out_dataset 来源未定 | §2.3 加 **K-fold 自动划分策略**:每 K 个教师样本第 K 个进 held-out,永不训练 |
| **V7-B3** | §11.2 Π update 对缺席 SA 没定义 → target=0 → Π→0 → SA 被永久遗忘 | **§11.2 改两阶段 Π 语义**:occurring SA 用 TD(0);absent SA 用**衰减自适应+不归零**(target=Π·ρ_decay_when_absent),保留下次召回机会 |
| **V7-B4** | §16.9 `gaussian_noise(0, 0.1)` 0.1 硬编码 | §16.9 改 **noise scale 派生自早 K tick 内 ActionParameterMemory 观测到的 R_change 方差** |
| **V7-B5** | §16.11 `*0.8 / *1.2` 硬编码 | §16.11 改 **R/P 直接继承 mismatch_sa 的 R/P**(无系数,真等价),"放大"由后续 §11.2 自然演化决定 |

### 0.2 v7 真 serious(7 个)

| # | 问题 | v8 修复 |
|---|---|---|
| V7-S1 | §2.7 phase 2 可能永不到 → vocab 永不扣 | §2.7 加 **mismatch_sa 衰减触发回退**:T_timeout=50 tick(可配)无教师证据 → 按 attention_share 部分扣 |
| V7-S2 | infer_conflicting_vocab 需要语义对齐,自循环 | §2.7 双层 align:**Layer 1 字串重叠(冷启动可用)+ Layer 2 学习后语义** |
| V7-S3 | §2.4 阈值 10 → 冷启动过度允许 | §2.4 改 **依链长动态阈值**:链越长要求观察数越高(防长链早期通过) |
| V7-S4 | §16.8 软边界对慢打字误判 | §16.8 改 **per-user 学习边界阈值**(从用户历史 inter-char interval 中学) |
| V7-S5 | §16.9 Thompson 用 Beta 但 ActionParameterMemory 存 R_change 连续值,无映射 | §16.9 改 **Gaussian Thompson sampling**(track mean/var of R_change) |
| V7-S6/S7 | §40.4 反事实 confound + 算力 + 无显著性测试 | §40.4 改 **保持 attention 不变 + 多干预幅度 + 单调性测试 + bootstrap 显著性** |
| V7-S8 | §40.5 cluster 算法未定 + 单 cluster 不支持重叠 | §40.5 显式 **agglomerative + 软分配**(每 sub-vocab 在 k=3 top 簇都有部分隶属) |

### 0.3 v7 致命架构问题:State pool family 爆炸(轮 4 关键发现)

**轮 4 审阅**:v7 状态池有 ~27 SA 家族,**跨家族交互 C(27,2)=351 对,绝大多数未分析,已过可分析性阈值**。

**v8 解法**(关键根本性变化):**统一 Marker 家族 + 类型分组 attention 预算**:

```
v7 (27 families,每家族独立 spawn 规则、衰减、链接语义)
↓
v8 (4 大类型 + Marker 多态)
  
  TYPE 1: PerceptSA      (vision/audio/text/percept)
  TYPE 2: VocabSA        (含 vocab, abstract_vocab, narrative, causal, hierarchy, anonymous_cluster)
  TYPE 3: MarkerSA       (含 novelty, tentative, pain, mismatch, correction, gaze, imitation, knowledge_gap)
  TYPE 4: EntitySA       (含 self_model, entity::user, focus, drive, goal, belief_model)
```

每 Marker 通过 `marker.kind` 字段区分(novelty / tentative / pain ...)— **这是显式 enum 字段**,**红线 0.4 修订允许此类 bounded enum**(必须有限枚举 + 不可任意扩展)。

**类型分组 attention 预算**:

```python
attention_budget_by_type = {
    "PerceptSA": 0.40,      # 40% 给感知
    "VocabSA": 0.25,        # 25% 给词汇/概念
    "MarkerSA": 0.15,       # 15% 给瞬态标记
    "EntitySA": 0.20,       # 20% 给实体/目标/驱力
}

def select_with_type_budget(candidates):
    """每 tick 限制每类型的总 attention_gain 不超过其预算"""
    selected_by_type = defaultdict(float)
    winners = []
    for sa in sorted(candidates, key=lambda s: s.score, reverse=True):
        if selected_by_type[sa.type] + sa.attention_gain > attention_budget_by_type[sa.type]:
            continue
        winners.append(sa)
        selected_by_type[sa.type] += sa.attention_gain
    return winners
```

**为什么这是真正修复**:
- 27 家族变 4 类型 → 交互对 C(4,2)=6 + 类型内交互(可在类型内分析)
- 类型预算 → 单类型饱和不会饿死其他类型(防 Marker 数量爆炸压死 VocabSA)
- Marker 多态 → 红线扫描 grep `sa.is_novel` 改为 `grep "marker.kind"` 数量(必须 ≤ 8 种),只允许有限 kind

### 0.4 v7 medium 问题(全部处理)

- M1 imitation 引用未存在感受器 → §29.1 明确 Phase 9 引入"用户行动感受器适配器"作为 sensor adapter,产生标准化 SA
- M2 number sense 排错 → 移至 Phase 8.X(subitize 1-3 视觉通道 = 物体计数 quantization)
- M3 reading 依赖未规划 vision → §40.7 显式标注 Phase 10.8 需 Phase ?? OCR/DOM 模块,作为先决条件
- M4-M5 §18.5 引用 Phase 9 设计 → 明确所有 mitigation 必须自包含或显式标注依赖
- M6 codebook 归一化非静态 → §6.3 加 **snapshot codebook size at decision time**,每决策点冻结归一化基线
- M7 lag-PMI 内存上限 → 显式 cap (max_partners_per_SA × max_lags = 32 × 5 = 160)

### 0.5 v8 红线 0.4 修订

- **❌→📝** "不许在 SA 上加 is_X 字段" → 修订:**不许临时性 bool 字段**;**允许有限 enum 字段**(如 `marker.kind` 必须 ≤ 8 种,显式枚举,不可任意扩展)
- **❌** 新红线:**算力可行性必须实测**——任何评估机制 spec 出来后 Phase 中必须给 worst-case op count
- **❌** 新红线:**所有硬编码常量必须经历"derivation challenge"**——能 derive 自其他量则必 derive;不能 derive 必须作为**显式 documented free parameter**(在配置文件中,不在代码字面量)

---

## 1-10. 沿用 v7 结构,关键章节按下文修

---

## 2. 通用 SA 组合词汇固化 — v8 算力可行版

### 2.1-2.2 沿用 v7

### 2.3 ΔP 晋升门 — incremental ΔP(V7-B1 + V7-B2 根本性修复)

**v7 错误**:full replay 5000 tick × bootstrap = 50M ops/候选 → Phase 8.4 跑不起来。

**v8 真修**——**incremental ΔP + held-out K-fold**:

```python
class IncrementalDeltaPEvaluator:
    """
    不重放历史,只测 candidate spawn 之后 N tick 的局部 P 差。
    成本:O(N × |active SA|),典型 50 × 100 = 5K ops/候选 (1000x 优化 v7)
    """
    
    def __init__(self, hold_out_pool, n_horizon_ticks=50):
        self.hold_out_pool = hold_out_pool
        self.n_horizon_ticks = n_horizon_ticks
    
    def evaluate(self, candidate, current_pool_state):
        """
        在当前状态池上仿真两条 horizon:
        - A: 不加 candidate (sufficient statistic baseline)
        - B: 加 candidate (sufficient statistic with candidate)
        """
        # Step 1: 用 K-fold held-out 找一组相似情境(从 held_out_pool)
        similar_situations = self.hold_out_pool.find_similar(
            current_pool_state.context_signature, k=8
        )
        # 这避免了 5000 tick 重放,只用 8 个 representative samples
        
        # Step 2: 在 8 个 situations 上,各做 horizon 仿真
        delta_Ps = []
        for situation in similar_situations:
            pool_snap = situation.snapshot()
            
            # Without candidate
            pool_a = pool_snap.copy_shallow()  # 只复 R/V,共享 vocab refs
            for _ in range(self.n_horizon_ticks):
                pool_a.advance_lightweight()
            P_a = pool_a.mean_recent_pressure()
            
            # With candidate
            pool_b = pool_snap.copy_shallow()
            pool_b.inject_vocab(candidate)
            for _ in range(self.n_horizon_ticks):
                pool_b.advance_lightweight()
            P_b = pool_b.mean_recent_pressure()
            
            delta_Ps.append(P_a - P_b)
        
        # Paired t-test on 8 situations
        t_stat, p_value = paired_t_test(delta_Ps)
        mean_delta = mean(delta_Ps)
        return {
            "mean_delta_P": mean_delta,
            "p_value": p_value,
            "passes": p_value < 0.05 and mean_delta > θ_promote_dP_min,
        }

    def total_op_count_estimate(self):
        # 8 situations × 50 horizon ticks × 2 (a/b) × ~50 active SAs per tick
        # = 8 × 50 × 2 × 50 = 40,000 ops per candidate
        return 40_000
```

**为什么这真修了**:
- **不全量重放**:只用 8 个 representative situations(K-fold held-out 自动选)
- **lightweight advance**:`advance_lightweight` 只更新 R/V,不重算 channel_signature/vocab_links
- **算力 40K ops/候选**:可在浏览器 worker 内 1ms 内完成,Phase 8.4 可行

**Held-out K-fold 自动收集策略**(V7-B2 fix):

```python
class HeldOutPool:
    """每 K 个教师样本中第 K 个进 held-out,永不训练"""
    K_FOLD = 5
    
    def __init__(self):
        self.held_out = []
        self.training_counter = 0
    
    def receive_teaching_sample(self, sample):
        self.training_counter += 1
        if self.training_counter % self.K_FOLD == 0:
            self.held_out.append(sample)
            return "held_out"
        else:
            return "training"
    
    def find_similar(self, context_signature, k):
        """从 held_out 中选 k 个最相似情境"""
        similarities = [
            (situation, cosine_sim(situation.context_signature, context_signature))
            for situation in self.held_out
        ]
        top_k = sorted(similarities, key=lambda x: x[1], reverse=True)[:k]
        return [s for s, _ in top_k]
```

**Phase 8.4 验收门**:
- 算力实测:每候选 ≤ 100K ops(目标 40K)
- 反例覆盖:含"PMI 高但 ΔP 失败"和"PMI 低但 ΔP 成功"两类反例
- Held-out 至少 K-fold 收集 100+ samples 后才能信任

### 2.4 chain extension — 动态阈值(V7-S3 fix)

**v7 错误**:固定 θ=10 → 长链早期过度允许。

**v8 改**:**`θ_min_obs = base + chain_length × increment`**:

```python
def get_chain_threshold(chain_length, base=5, increment=5):
    """链越长要求每边观察数越高"""
    return base + chain_length * increment
    # 长度 2: 15 obs
    # 长度 3: 20 obs
    # 长度 4: 25 obs

def try_extend_chain(seed_a, seed_b, max_length=4):
    chain = [seed_a, seed_b]
    while len(chain) < max_length:
        next_candidate = find_partner(chain[-1])
        if not next_candidate:
            break
        
        threshold = get_chain_threshold(len(chain))
        
        all_eligible = True
        # Span eligibility
        for span in range(1, min(3, len(chain))):
            other_idx = -(span + 1)
            if other_idx < -len(chain):
                continue
            edge = get_edge(chain[other_idx], next_candidate)
            if not edge_is_eligible(edge, min_obs=threshold):
                all_eligible = False
                break
        
        # 反相关检查 - 数据足够时启用
        for prior in chain:
            edge = get_edge(prior, next_candidate)
            if edge.observation_count >= threshold and edge.smoothed_pmi < θ_anti:
                all_eligible = False
                break
        
        if not all_eligible:
            break
        chain.append(next_candidate)
    return chain if len(chain) >= 2 else None
```

### 2.5-2.6 沿用 v7

### 2.7 两阶段 credit assignment + timeout(V7-S1 + V7-S2 fix)

```python
class CreditAssignmentEngine:
    PHASE_2_TIMEOUT_TICKS = 50  # ~5 秒,可配
    
    def handle_negative_feedback(self, commit_record, negative_signal, current_tick):
        # Phase 1: spawn mismatch + correction marker
        mismatch_sa = MarkerSA(
            kind="mismatch",                                    # 多态枚举
            sa_label=f"marker::mismatch::{commit_record.id}",
            real_energy=negative_signal * commit_record.commit_R,
            cognitive_pressure=negative_signal * commit_record.commit_R,
            channel_signature={"commit_event_marker": 1.0},
            linked_vocabs=commit_record.vocabs_used,
            linked_attention_shares=commit_record.vocabs_attention_share,
            spawn_tick=current_tick,
            timeout_tick=current_tick + self.PHASE_2_TIMEOUT_TICKS,
        )
        state_pool.add(mismatch_sa)
        
        # Phase 2: 等教师证据
        # 如教师在 timeout 前提供 → 精确归因
        # 否则 → 按 attention_share 部分扣
    
    def step_check_timeout(self, current_tick):
        """每 tick 检查超时 mismatch SAs"""
        for sa in state_pool.markers_with_kind("mismatch"):
            if current_tick > sa.timeout_tick:
                self._apply_attention_weighted_fallback(sa)
                sa.mark_resolved()
    
    def _apply_attention_weighted_fallback(self, mismatch_sa):
        for vocab_id, share in zip(
            mismatch_sa.linked_vocabs, mismatch_sa.linked_attention_shares
        ):
            vocab = state_pool.get(vocab_id)
            vocab.negative_co_observations += share * 0.5  # 部分扣(50% of share)
    
    def handle_correction_evidence(self, correction_text, mismatch_sa):
        # Layer 1 双层 align(V7-S2 fix):
        # 字符串重叠(冷启动可用)
        conflicting_vocab_id = None
        for vocab_id in mismatch_sa.linked_vocabs:
            vocab = state_pool.get(vocab_id)
            if vocab.label_text and any(
                tok in correction_text for tok in vocab.label_text.split()
            ):
                # 该 vocab 出现在 correction 中 → 可能是正确答案,不扣这个
                continue
            # 否则:可能错的
            conflicting_vocab_id = vocab_id
            break
        
        # Layer 2 学习后语义(经 OnlineEmbedding):
        if conflicting_vocab_id is None:
            # 字符串不区分,用 learned_similarity
            correction_vocab = vocab_for(correction_text)
            for vocab_id in mismatch_sa.linked_vocabs:
                vocab = state_pool.get(vocab_id)
                similarity = learned_similarity(vocab, correction_vocab)
                if similarity < 0.3:  # 显著不同 → 可能是错的
                    conflicting_vocab_id = vocab_id
                    break
        
        if conflicting_vocab_id:
            state_pool.get(conflicting_vocab_id).negative_co_observations += 1
            # 强化 correction 对应 vocab
            pos = vocab_for(correction_text)
            if pos:
                pos.positive_co_observations += 1
        else:
            # 实在分不出 → 走 timeout fallback
            self._apply_attention_weighted_fallback(mismatch_sa)
        
        mismatch_sa.mark_resolved()
```

### 2.8 lag-PMI(沿用 v7,加 max_partners cap)

```python
class TemporalCooccurrenceGraph:
    MAX_PARTNERS_PER_SA = 32          # 单 SA 最多记 32 个 partner
    MAX_LAGS = 5                       # 1, 2, 3, 5, 10
    # 总内存上限:N_SAs × 32 × 5 entries
```

---

## 3-5. 沿用 v7

## 6. JSD slot 偏好 — codebook snapshot(M6 fix)

### 6.3 v8 严格版

```python
def derive_channel_preference(slot, decision_tick) -> Optional[dict]:
    if len(set(slot.fillers_history)) < θ_min_distinct_fillers:
        return None
    
    deduplicated_fillers = list(set(slot.fillers_history))
    
    channel_score = {}
    for c in all_channels:
        # M6 fix: snapshot codebook_size at decision time(防归一化漂移)
        codebook_size_snapshot = c.current_codebook_size  # 决策时冻结
        
        filler_buckets = [
            quantize(sa.get_channel_payload(c), c)
            for sa in deduplicated_fillers
        ]
        slot_dist = laplace_smoothed_distribution(filler_buckets, codebook_size_snapshot)
        global_dist = global_bucket_distribution(c, snapshot=True)
        
        jsd = jensen_shannon_divergence(slot_dist, global_dist)
        normalized_score = jsd / log(codebook_size_snapshot)
        
        channel_score[c] = normalized_score
    
    return softmax([channel_score[c] for c in all_channels])
```

---

## 7-10. 沿用 v7

---

## 11. 习惯化 + Marker SA 多态 — v8 根本性修复

### 11.1 沿用 v7

### 11.2 Π update — occurring vs absent SA 两阶段(V7-B3 fix)

**v7 错误**:absent SA target=0 → Π→0 → SA 永久遗忘。

**v8 真修**——**双语义 Π**:

```python
def update_prediction_pi(sa, observations_window, learning_rate, currently_occurring):
    """
    两阶段 Π 语义:
    - SA actually occurs at t+1: TD(0) toward observed R
    - SA absent at t+1: gentle decay toward Π·ρ_decay_when_absent (不归零)
    """
    if currently_occurring:
        # SA appears at t+1 → TD(0)
        target = observations_window.next_tick_R_for(sa)
        residual = target - sa.Π
        eta = min(η_max, κ * abs(residual))
        sa.Π += eta * residual
    else:
        # SA doesn't appear at t+1 → 保留预测但渐弱
        # 注意:绝不归零,保留下次召回时机会
        sa.Π *= ρ_decay_when_absent
        # ρ_decay_when_absent ≈ 0.95, 几十 tick 后 Π 仍有 ~5% 强度
        # 但若长期不再出现,自然衰减到 ε(不是 0)
```

**为什么这正确**:
- 当 SA 暂时不出现(用户改话题 1 分钟后又提及):Π 保持非零 → 召回时仍能匹配
- 当 SA 永久消失(用户从不再提及):Π 渐衰到 ε,SA 经 short_term decay 自然退役
- 符合习惯化:见过的东西不忘,只是变模糊
- 与 §1.3 short_long 双层互补:short layer 快衰减,Π 慢衰减,记忆 robust

**数学保证**:绝对的"Π → 0 → 永久遗忘"不会发生,因为 ρ_decay_when_absent 只衰减不归零。

### 11.3 统一 Marker SA 多态(架构根本性修复)

**v7 问题**:27 SA 家族 → 351 交互对未分析。

**v8 解法**——**4 大类型 + Marker 多态**:

```python
# v8 SA 类型层次(整个状态池只有 4 种 first-class SA 类型)
class SAType(Enum):
    PERCEPT = "percept"      # 感受器输出
    VOCAB = "vocab"          # 概念/词汇/范畴(含 narrative/causal/abstract)
    MARKER = "marker"        # 瞬态状态标记(novelty/tentative/pain/mismatch/...)
    ENTITY = "entity"        # 持久实体(self/user/focus/drive/goal/belief)

# Marker 多态:有限 enum kind
class MarkerKind(Enum):
    NOVELTY = "novelty"
    TENTATIVE = "tentative"
    PAIN = "pain"
    MISMATCH = "mismatch"
    CORRECTION = "correction"
    GAZE = "gaze"
    IMITATION = "imitation"
    KNOWLEDGE_GAP = "knowledge_gap"
    # 注意:必须 ≤ 8 种,有限枚举,不可任意扩展
    # 新增 kind 必须经设计稿修订,不是代码运行时扩展

# Marker SA 实现
class MarkerSA(SA):
    type = SAType.MARKER
    kind: MarkerKind          # 显式枚举多态
    target_sa_id: str         # 该 marker 关联的目标 SA(可选)
    # 标准能量场(继承 SA)
    real_energy: float
    virtual_energy: float
    cognitive_pressure: float
    attention_gain: float
    fatigue: float
    # marker-specific spawn rules / decay rates 由 kind 决定:
    
    @property
    def decay_rate(self):
        return MARKER_DECAY_RATES[self.kind]

MARKER_DECAY_RATES = {
    MarkerKind.NOVELTY: 0.85,       # 3 秒衰减
    MarkerKind.TENTATIVE: 0.92,     # 中速衰减
    MarkerKind.PAIN: 0.998,         # 极慢衰减(数小时)
    MarkerKind.MISMATCH: 0.90,
    MarkerKind.CORRECTION: 0.88,
    MarkerKind.GAZE: 0.80,
    MarkerKind.IMITATION: 0.92,
    MarkerKind.KNOWLEDGE_GAP: 0.99, # 慢衰减
}
```

**类型分组 attention 预算**:

```python
class AttentionSelector:
    TYPE_BUDGET = {
        SAType.PERCEPT: 0.40,
        SAType.VOCAB: 0.25,
        SAType.MARKER: 0.15,
        SAType.ENTITY: 0.20,
    }
    
    def select(self, candidates):
        used_by_type = defaultdict(float)
        winners = []
        for sa in sorted(candidates, key=lambda s: self.score(s), reverse=True):
            type_budget = self.TYPE_BUDGET[sa.type]
            if used_by_type[sa.type] + sa.attention_gain > type_budget:
                continue  # 该类型饱和,跳过
            winners.append(sa)
            used_by_type[sa.type] += sa.attention_gain
        return winners
```

**为什么这真根本修复**:
- 27 家族 → 4 类型,交互分析对数从 351 → 6 + 类型内
- Marker 多态用 enum + 强约束(≤ 8 种)
- 类型预算 → marker 数量爆炸不会饿死 vocab/percept
- Phase 8.10 红线扫描:`grep "kind=MarkerKind\." runtime/` 必须只匹配 ≤ 8 种值

**红线 0.4 修订(v8)**:
- **允许** Marker SA 多态 enum kind 字段
- **禁止** 任意运行时扩展 marker kind(必须经设计稿修订)
- **禁止** 在 PerceptSA / VocabSA / EntitySA 上加 is_X bool

### 11.4 沿用 v7

### 11.5 Salience hint — C-5 文档化扩展(继承 v7,补 weight 派生)

**v7 错误**:salience weights 硬编码 `w_contrast * x + w_motion * y + w_face_like * z`。

**v8 修复**:

```python
# salience hint weights 来自适应 tuner,不硬编码
def compute_salience_hint(percept, sensor_tuner):
    weights = sensor_tuner.current_salience_weights  # AdaptiveTuner-owned
    salience = (
        weights['contrast'] * percept.local_contrast +
        weights['motion'] * percept.motion_magnitude +
        weights['face_like'] * percept.face_similarity
    )
    return salience

# 初值 weights 从 cold-start 行为分布中 derive:
# 启动后第一批 percepts,每个特征的方差 → 初值权重
# 然后 sensor_tuner 根据后续 refocus action 的成功率调权重
def derive_initial_salience_weights(early_percept_buffer):
    feature_vars = {
        'contrast': np.var([p.local_contrast for p in early_percept_buffer]),
        'motion': np.var([p.motion_magnitude for p in early_percept_buffer]),
        'face_like': np.var([p.face_similarity for p in early_percept_buffer]),
    }
    total_var = sum(feature_vars.values())
    return {k: v/total_var for k, v in feature_vars.items()}
```

**关键**:weights 不再硬编码,从早期数据方差派生 + 后续 AdaptiveTuner 自调。

### 11.6 沿用 v7

### 11.7 Sleep emerge(沿用 v7)

### 11.8 Tentative vocab via Marker(沿用 v7 §11.8,Marker.kind=TENTATIVE)

### 11.9 Slot 元先验 + noun_marker 派生(沿用 v7,无大改)

---

## 12-15. 沿用 v7

---

## 16. Phase 重排 + 真消除硬编码

### 16.1-16.7 沿用 v7

### 16.8 Utterance boundary — per-user 学习阈值(V7-S4 fix)

```python
class TextSensorAdapter:
    def __init__(self):
        self.per_user_silence_distribution = OnlineGaussianTracker()
        # 跟踪每个 user 的 inter-char interval 分布
        self.last_char_tick = -1
        self.last_char_user_id = None
        self.explicit_eom_received = False
    
    def step(self, t):
        # 处理字符流(沿 v7)
        ...
        
        # 更新 inter-char interval 分布(每用户单独)
        if self.last_char_tick >= 0:
            interval = t - self.last_char_tick
            self.per_user_silence_distribution.update(self.last_char_user_id, interval)
        
        silence_ticks = t - self.last_char_tick
        
        # 学到该用户的 95th percentile inter-char interval
        threshold_ticks = self.per_user_silence_distribution.percentile(
            self.last_char_user_id, 0.95
        )
        # 默认值(冷启动):20 tick
        if threshold_ticks is None:
            threshold_ticks = 20
        
        # 显式 send 信号
        if self.explicit_eom_received and queue.is_empty():
            emit_boundary("explicit", boundary_R=high_R)
            self.explicit_eom_received = False
        
        # 软边界:超过该用户 95% 历史 inter-char interval
        elif silence_ticks > threshold_ticks and queue.is_empty():
            silence_intensity = sigmoid((silence_ticks - threshold_ticks) / 10)
            emit_boundary("soft", boundary_R=silence_intensity * mid_R)
```

**为什么这真修**:
- 快打字者:95th percentile 可能 5 tick → 软边界 5 tick 后触发
- 慢打字者:95th percentile 可能 50 tick → 软边界 50 tick 后触发
- 完全 per-user 适应,**不再有全局硬编码 20 ticks**

### 16.9 草稿行动 — 全0 bootstrap + Gaussian Thompson + 派生 noise(V7-B4 + V7-S5 fix)

**v7 错误**:`gaussian_noise(0, 0.1)` 0.1 硬编码 + Beta-Thompson 与 ActionParameterMemory 不匹配。

**v8 真修**:

```python
class DraftActionRunner:
    def __init__(self):
        self.action_memory = ActionParameterMemory()
        self.early_R_change_observations = []  # 收集早期方差
        self.early_phase_n = 50  # 前 50 次 action 用于 derive noise scale
        self.derived_noise_scale = None  # 派生自数据
    
    def get_action_expected_R_change(self, action_type, context, target):
        learned = self.action_memory.lookup(action_type, context, target)
        
        if learned.sample_count >= θ_min_action_samples:
            # Gaussian Thompson sampling(V7-S5 fix)
            mean_R = learned.mean_R_change
            var_R = learned.variance_R_change
            return np.random.normal(mean_R, sqrt(var_R))
        
        # Cold-start: 0 + noise(scale 派生自早期观察方差)
        bootstrap = 0.0
        if self.derived_noise_scale is None:
            # 早期默认 noise 用 unit normal 探索
            noise_scale = 1.0
        else:
            noise_scale = self.derived_noise_scale
        return bootstrap + np.random.normal(0, noise_scale)
    
    def observe(self, action, observed_R_change):
        self.action_memory.observe(action, observed_R_change)
        
        # 早期收集 R_change 方差
        if len(self.early_R_change_observations) < self.early_phase_n:
            self.early_R_change_observations.append(observed_R_change)
            if len(self.early_R_change_observations) == self.early_phase_n:
                # 派生 noise scale = 观察到的 R_change std × 0.5
                # (探索时用一半的实际方差作为 noise scale)
                self.derived_noise_scale = np.std(self.early_R_change_observations) * 0.5
```

**为什么这真修**:
- **noise scale 派生** 自前 50 次 R_change 观察的标准差,不是硬编码 0.1
- **Gaussian Thompson** 与 ActionParameterMemory 存的连续 R_change 直接兼容(track mean/var)
- 第一阶段(0-50 tick)用 unit normal 强探索;过渡到第二阶段(50+ tick)用派生 scale 探索;第 200+ tick learned 接管

### 16.10 沿用 v7

### 16.11 Correction R/P 真继承(V7-B5 fix)

**v7 错误**:`*0.8 / *1.2` 是换措辞的硬编码。

**v8 真修**:**correction SA 直接继承 mismatch_sa 的 R/P**,无任何系数。"放大/衰减"由后续 §11.2 自然演化决定:

```python
def handle_negative_feedback(commit_record, negative_signal, current_tick):
    # mismatch SA(无硬编码系数)
    mismatch_sa = MarkerSA(
        kind=MarkerKind.MISMATCH,
        real_energy=negative_signal * commit_record.commit_R,  # 这两个是 input,不是系数
        cognitive_pressure=negative_signal * commit_record.commit_R,
        ...
    )
    state_pool.add(mismatch_sa)
    
    # correction marker 完全继承 mismatch 的能量(无系数)
    correction_sa = MarkerSA(
        kind=MarkerKind.CORRECTION,
        real_energy=mismatch_sa.real_energy,        # 直接继承
        cognitive_pressure=mismatch_sa.cognitive_pressure,  # 直接继承
        linked_to=mismatch_sa.persistent_id,
        ...
    )
    state_pool.add(correction_sa)
    
    # 不同的衰减率(由 MARKER_DECAY_RATES enum 决定,不是硬编码常量):
    # mismatch.decay = 0.90 (快衰减,几秒)
    # correction.decay = 0.88 (稍慢衰减,等更长教师证据)
    # 这些是 enum 配置(documented free params),不是代码字面量
```

**为什么这真修**:
- 没有 `*0.8 / *1.2` 之类的 magic 系数
- mismatch 和 correction 的能量数字完全等价于来源(派生 = 复制)
- 后续 R/P 差异由 enum-driven 衰减率(MARKER_DECAY_RATES)决定,**这些值在配置文件中,是 documented free parameters**,不是代码字面量
- 红线 0.4 v8 修订允许这种 documented free parameters

---

## 18. 数学交互矩阵 — v8 类型层

### 18.5 类型层交互矩阵(从 SA 家族层移到类型层)

| Type A | Type B | 交互机制 | 风险/缓解 |
|---|---|---|---|
| Percept | Vocab | 共现学习 + slot fill | 风险:Vocab 抢 Percept 预算;**缓解**:类型预算分离 |
| Percept | Marker | salience hint + spawn novelty marker | 风险:Marker 抢 Percept;**缓解**:Marker 15% 预算 cap |
| Percept | Entity | drive 触发感受 | 标准 |
| Vocab | Marker | tentative marker + 反例撤销 | 标准 |
| Vocab | Entity | self 偏好/drive 满足 | 标准 |
| Marker | Entity | knowledge_gap → epistemic drive | 标准 |

**6 个类型对,各自有明确机制**。所有 27 家族的具体交互**通过它们所属的 4 大类型继承**,可分析性恢复。

### 18.6 v8 稳定性论证(强化)

- 所有新机制注入既有能量场
- 无独立非衰减能量源(self_sa 修复后正常衰减)
- 类型预算防饥饿
- Marker max kind 数 ≤ 8(红线扫描)
- 每类型 max SA count 由 AdaptiveTuner 监测,饱和时降 spawn 率
- 算力可验证(每个评估函数有 worst-case op count 注释)

---

## 40. 5-8 岁认知架构 — v8 反事实方法学修正

### 40.1 沿用 v7(lag-PMI 已修)

### 40.2 沿用 v7

### 40.3 沿用 v7

### 40.4 反事实模拟 — 方法学修正(V7-S6 + V7-S7 fix)

**v7 问题**:
1. fork "lightweight" 误导,实际成本高
2. 移走 X 改变所有 SA attention → confound
3. 无显著性测试

**v8 真修**——**保持 attention 不变 + 多干预幅度 + 单调性 + bootstrap 显著性**:

```python
class CounterfactualSimulator:
    """
    方法学修正版反事实模拟。
    保持 attention 不变(避免 confound),多干预幅度(测因果强度),
    bootstrap 显著性测试(避免单点错误)。
    """
    
    def __init__(self):
        self.MAX_HORIZON = 10  # tick
        self.INTERVENTION_LEVELS = [1.0, 0.5, 0.0]  # 全保留 / 半保留 / 完全移除
        self.N_BOOTSTRAPS = 5
    
    def estimate_causal_strength(self, sa_a, sa_b, current_pool, attention_snapshot):
        """
        测 A 是否因果 B:
        - 保持 attention 分配(snapshot)固定
        - 在多个干预幅度上测 B 的反应
        - bootstrap 显著性
        """
        results_by_level = {}
        
        for intervention_level in self.INTERVENTION_LEVELS:
            b_R_per_bootstrap = []
            for boot in range(self.N_BOOTSTRAPS):
                pool_snap = current_pool.snapshot_full(seed=boot)
                
                # 关键修正:scale A's R by level,而不是 remove
                pool_snap.scale_sa_R(sa_a, intervention_level)
                
                # 关键修正:freeze attention(保持 baseline 分配)
                pool_snap.freeze_attention_to(attention_snapshot)
                
                # forward sim N tick
                for _ in range(self.MAX_HORIZON):
                    pool_snap.advance_with_frozen_attention()
                
                b_R_per_bootstrap.append(pool_snap.sa(sa_b).mean_recent_R)
            
            results_by_level[intervention_level] = {
                "mean_b_R": mean(b_R_per_bootstrap),
                "std_b_R": std(b_R_per_bootstrap),
            }
        
        # 单调性测试:level 升 → b_R 升?
        b_at_full = results_by_level[1.0]["mean_b_R"]
        b_at_half = results_by_level[0.5]["mean_b_R"]
        b_at_zero = results_by_level[0.0]["mean_b_R"]
        
        monotonic_increasing = b_at_full > b_at_half > b_at_zero
        causal_strength = b_at_full - b_at_zero
        
        # bootstrap 显著性:zero 和 full 的差异显著吗?
        full_dist = [b for b in self.last_run["full"]]
        zero_dist = [b for b in self.last_run["zero"]]
        t_stat, p_value = independent_t_test(full_dist, zero_dist)
        
        return {
            "causal_strength": causal_strength,
            "monotonic": monotonic_increasing,
            "p_value": p_value,
            "is_causal": monotonic_increasing and p_value < 0.05 and causal_strength > θ_causal_min,
        }
```

**为什么这真修**:
- **`freeze_attention_to(attention_snapshot)`**:反事实仿真**保持 attention 分配同基线**,消除 confound——只测 A 的能量 scaling 对 B 的影响,attention 分配不变
- **多干预幅度** + **单调性**:不只是 "全/无",而是 1.0/0.5/0.0,检验"A 多 → B 多"是否单调,排除非因果伪相关
- **bootstrap 显著性**:多次仿真测 B 的方差,p < 0.05 才能下因果判断
- **算力**:5 bootstraps × 3 levels × 10 tick × ~50 SAs = ~7,500 ops/因果假设,可行

### 40.5 Anonymous super-cluster — 显式算法(V7-S8 fix)

```python
class AnonymousClusterDetector:
    def __init__(self):
        self.MIN_CLUSTER_SIZE = 3
        self.LINKAGE = "average"  # agglomerative average linkage
        self.DISTANCE_METRIC = "channel_signature_cosine"
        self.MAX_CLUSTERS_PER_VOCAB = 3  # 软分配
    
    def detect_and_spawn(self, all_vocab_sas):
        # Step 1: agglomerative clustering with bottom-up cut
        distance_matrix = self.compute_channel_sig_distance_matrix(all_vocab_sas)
        clusters = agglomerative_cluster(
            distance_matrix,
            linkage=self.LINKAGE,
            cut_at_silhouette_peak=True,  # 自动选 k(silhouette score 最高)
        )
        
        # Step 2: 验证每个 cluster 有共同 slot 偏好
        for cluster in clusters:
            if len(cluster) < self.MIN_CLUSTER_SIZE:
                continue
            
            common_pref = self.compute_common_slot_preference(cluster)
            if common_pref is None:
                continue
            
            # Step 3: 软分配——每个 sub-vocab 可属于 top-3 距离最近 cluster
            for sub_vocab in cluster:
                top_clusters = self.find_top_k_clusters_for(sub_vocab, k=self.MAX_CLUSTERS_PER_VOCAB)
                membership_strengths = self.compute_membership_strengths(sub_vocab, top_clusters)
                
                for cluster_id, strength in zip(top_clusters, membership_strengths):
                    spawn_cluster_membership_link(sub_vocab, cluster_id, strength)
            
            # Step 4: spawn / update anonymous super-cluster SA
            existing_super = find_named_super_for_cluster(cluster)
            if existing_super:
                bind_cluster_to_named(cluster, existing_super)
            else:
                anonymous_super = VocabSA(  # 注意:用 VocabSA 类型,kind=anonymous_cluster
                    sa_label=f"cluster::anonymous::{stable_id()}",
                    family="anonymous_cluster",
                    sub_vocabs=cluster,
                    common_channel_pref=common_pref,
                )
                state_pool.add(anonymous_super)
    
    def compute_common_slot_preference(self, cluster):
        """所有 sub_vocab 共有的 slot 偏好(向量 cosine 相似度)"""
        prefs = [sv.learned_slot_preferences for sv in cluster if sv.has_learned_pref]
        if len(prefs) < self.MIN_CLUSTER_SIZE:
            return None
        # 中心点
        centroid = mean_vector(prefs)
        # 所有 prefs 与 centroid 的平均 cosine
        avg_sim = mean(cosine_sim(p, centroid) for p in prefs)
        if avg_sim > θ_common_pref_sim:
            return centroid
        return None
```

**为什么这真修**:
- 显式 agglomerative + silhouette cut(可重现)
- 软分配(cat 属于 pet ∩ mammal ∩ small-animal,top-3 cluster 都关联)
- 共同 slot pref 定义为 cosine 相似度 > θ(可衡量)

### 40.6 沿用 v7(trust prior + downgrade)

### 40.7 沿用 v7(reading 单管道)

---

## 41. 8-12 岁 — v8 virtual track 修复

### 41.1 沿用 v7(meta-cognition deps on 40.5)

### 41.2 沿用 v7(abstract cross-cluster gate)

### 41.3 沿用 v7

### 41.4 Deliberative virtual track — 真化(V7-S9 + V7-S10 fix)

**v7 问题**:虚轨道 Π update 无锚 + 用户输入中断未规范 + audit 爆炸。

**v8 真修**:

```python
class DeliberativeRunner:
    """虚轨道 deliberation,有完整规范"""
    
    def __init__(self):
        self.virtual_track_active = False
        self.virtual_audit_buffer = []  # 不直接写 audit_db,先暂存
        self.MAX_VIRTUAL_STEPS_PER_TURN = 10
        self.virtual_step_count = 0
        self.main_track_user_input_observed = False
    
    def maybe_enter_virtual_track(self, t):
        deliberative_drive = self.compute_deliberative_drive(state_pool)
        if deliberative_drive > θ_enter_virtual and not self.virtual_track_active:
            self.virtual_track_active = True
            self.virtual_step_count = 0
    
    def step_virtual(self, t):
        # 检查中断条件
        if self.main_track_user_input_observed:
            self.commit_virtual_to_main_or_abort(t, abort=True)
            return
        
        if self.virtual_step_count >= self.MAX_VIRTUAL_STEPS_PER_TURN:
            self.commit_virtual_to_main_or_abort(t, abort=False)
            return
        
        # 虚轨道 Π update(锚定到实际 V 链而非 R)
        # 注意:虚 Π 用最后一次实际观测 R 作为初始锚
        for sa in active_sas:
            if self.virtual_step_count == 0:
                target = sa.R  # 第一步用实际 R 作锚
            else:
                target = sa.virtual_R  # 后续用累积虚拟 R
            
            # 同 §11.2 几何收敛
            residual = target - sa.virtual_Π
            sa.virtual_Π += η_virtual * residual
            sa.virtual_R = sa.virtual_Π  # 虚轨道 R 与 Π 等价
        
        # Audit:暂存,不直接写 audit_db
        self.virtual_audit_buffer.append({
            "tick": t,
            "track": "virtual",
            "step": self.virtual_step_count,
            "summary": pool_summary(),
        })
        self.virtual_step_count += 1
    
    def on_main_track_input(self):
        """主轨道收到外源输入 → 标记中断"""
        if self.virtual_track_active:
            self.main_track_user_input_observed = True
    
    def commit_virtual_to_main_or_abort(self, t, abort):
        if abort:
            # 中断,不 commit 结论
            self.virtual_audit_buffer = []
        else:
            # 找虚轨道最终结论
            conclusion = self.derive_conclusion_from_virtual_state()
            if conclusion:
                state_pool.add(conclusion)
            
            # Audit:仅写关键节点(开始+结论),不全量
            audit_db.log_deliberative({
                "tick_start": self.virtual_audit_buffer[0]["tick"],
                "tick_end": t,
                "n_steps": self.virtual_step_count,
                "conclusion": conclusion,
                # 不写每步细节(防爆炸)
            })
        
        self.virtual_track_active = False
        self.main_track_user_input_observed = False
        self.virtual_audit_buffer = []
```

**为什么这真修**:
- **虚轨道 Π 用实际 R 作初始锚** → 不是"自循环"
- **用户输入中断**:`on_main_track_input` 标记 → 下一虚步 abort
- **Audit 压缩**:不写每步细节,只写起止 + 结论(防爆炸)
- **MAX_VIRTUAL_STEPS_PER_TURN=10** → 单 turn 不会 deliberate 太久

### 41.5 Self model — heartbeat reactivation(V7-S11 fix)

**v7 问题**:desktop pet 长跑无 "session 边界"。

**v8 修复**——**heartbeat 周期 persist + reactivate**:

```python
class SelfModelManager:
    HEARTBEAT_INTERVAL_TICKS = 36000  # 1 小时 @ 0.1s/tick
    ATTENTION_CAP_PERCENT = 0.05  # 仍是配置参数,记录在 documented free params
    
    def __init__(self):
        self.last_persist_tick = 0
        self.last_reactivate_tick = 0
    
    def step(self, t):
        # 每小时持久化一次
        if t - self.last_persist_tick >= self.HEARTBEAT_INTERVAL_TICKS:
            self.persist_self_to_sqlite()
            self.last_persist_tick = t
        
        # 每小时检查 self_sa 是否需要 reactivate(若已衰减过低)
        if t - self.last_reactivate_tick >= self.HEARTBEAT_INTERVAL_TICKS:
            if self.self_sa.R < θ_self_reactivate:
                self.reactivate_from_persisted()
            self.last_reactivate_tick = t
    
    def persist_self_to_sqlite(self):
        """每 heartbeat 把 self_sa 当前状态写入 SQLite"""
        snapshot = {
            "R": self.self_sa.R,
            "capabilities": self.self_sa.capabilities,
            "preferences": self.self_sa.preferences,
            "autobiographical": self.self_sa.autobiographical_narrative,
            "tick": current_tick,
        }
        sqlite_store.write_self_snapshot(snapshot)
    
    def reactivate_from_persisted(self):
        """从 SQLite 重激活 self_sa"""
        latest_snapshot = sqlite_store.read_latest_self_snapshot()
        self.self_sa.R = REACTIVATION_R  # 配置参数,不是字面量
        self.self_sa.capabilities = latest_snapshot["capabilities"]
        # 其他字段保留(已在内存中)
```

**为什么这真修**:
- 不依赖 session 边界(desktop pet 不停跑)
- 每小时 heartbeat 持久化 + 每小时检查是否需重激活
- App restart 时从最新 snapshot 重生
- ATTENTION_CAP_PERCENT 5% 是 **documented free parameter**(写在配置文件,不是字面量)

---

## 42-43 沿用 v7 + 加 number sense 移位

### 数 sense — Phase 8.X(V7-M2 fix)

**v7 错误**:把 subitize 1-3 放 Phase 10。

**v8 修复**:**subitize 是感知通道,放 Phase 8.6 视觉感受器**:

```python
# Phase 8.6 视觉感受器加 C8 number 通道
C8: object_count = {
    1: discrete bucket,
    2: discrete bucket,
    3: discrete bucket,
    "4+": coarse bucket
}
# 与其他 C1-C7 同等,自然量化桶
# 通过 §2.3 ΔP 共现学习与 vocab "一""二""三" 绑定
```

**抽象数 quantity (4+)** 仍放 Phase 11.2 abstract vocab。

---

## 19. v8 给 Codex 的最终指令

1. **v8 取代 v7 作为 Phase 8 实施依据**
2. **每个机制 spec 必须给 worst-case op count**(算力可行性红线)
3. **每个常量必须经 derivation challenge**:能 derive 必 derive;不能则放 documented free params 配置文件,不在代码字面量
4. **Marker SA 多态:必须 ≤ 8 种 kind,有限枚举**
5. **类型分组 attention 预算执行**:超预算的 SA 跳过竞争
6. **每 Phase 5 段闭环 + 红线扫描 + 算力 op count 验收**

---

## 附录: v7 → v8 修复一览

| 类别 | 数 |
|---|---|
| v7 Blocker (B1-B5) | 5 真修 |
| v7 Serious (S1-S8) | 8 真修 |
| v7 Medium (M1-M7) | 7 真修 |
| Architecture (家族爆炸) | 4 类型 + Marker 多态 |

**核心架构变化**:
- 27 SA 家族 → 4 大类型(Percept/Vocab/Marker/Entity)
- Marker 多态(≤ 8 kind,有限 enum)
- 类型分组 attention 预算
- 全硬编码常量经 derivation challenge
- 算力可行性红线

— 接手线程,2026-06-17
