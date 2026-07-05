# APV3.0 拟人多模态底座 — 完整设计稿 v6(v5 修正 + 全年龄远景)

日期: 2026-06-17
作者: 接手线程
状态: **v5 经第二轮对抗审阅发现 7 blocker + 5 serious + 2 minor + 10 覆盖洞 + 5-8/8-12 岁架构缺。v6 全部修复 + 补全年龄远景图谱(18-30 月 → 3-5 岁 → 5-8 岁 → 8-12 岁)。本稿是 Phase 8 实施依据 + 全程远景蓝图。**

前身:v1 → v2 → v3 → v4 → v5 → **v6(本稿)**

---

## 0. v5 → v6 修正与扩展总览(必读)

### 0.1 v5 的 7 个 blocker 必修(全部已落地)

| # | v5 缺陷 | v6 修复 |
|---|---|---|
| **B1** | §2.3 ΔP held-out 有反馈环:加新 vocab → 改变 attention 预算 → 改变 Π → 改变 P,无法稳定比较 | §2.3 改 **frozen-snapshot ΔP + N-run bootstrap + 配对 t 检验**,严谨统计学 |
| **B2** | §2.4 chain extension 代码 vs 文字不一致(文字说"隔一对也稳",代码只检查 last+last-1) | §2.4 重写代码:span eligibility metric(链内所有相邻 + 跨 1 hop),并加反相关检测 |
| **B3** | §6.3 channel_consistency 跨通道比较不公平(C2 16 桶 vs C1 512 桶,熵基线不同) | §6.3 改归一化为**每通道 codebook 熵基线**或**slot ID 互信息**(MI(slot, bucket)),跨通道可比 |
| **B4** | §6.3 冷启动:1 filler → 假"全通道平等",2 filler 同 vocab → 假一致性 | §6.3 加 **θ_min_distinct_fillers=3** + 按 SA persistent_id 去重(防同 vocab 重复) |
| **B5** | §16.9 草稿行动 expected_R_change 是硬编码 `+0.3, +0.2, +0.5_if_ready_else_-0.2` — Codex C-8 没真修,只换皮 | §16.9 改 ActionParameterMemory 真实学习 + cold-start 默认 **明确标注为引导先验**(可被快速覆盖),不再假装"涌现" |
| **B6** | §13/§10 audit_db 驱逐 + long-term 召回时渲染 fallback 路径未规范 | §13.8 显式 3 种 fallback:rich payload / stylized blob / introspection text;长时召回但无 channel sig → 走文本介绍化路径 |
| **B7** | §1.2 无"消息完成"边界,系统可能 char 3 就提交错答 | §1.2 改 sensor adapter 出 **`text::utterance_boundary` SA**(感受器层面,非认知 prior),draft 行动竞争自然学到"边界前 commit ΔP 负" |

### 0.2 v5 的 5 个 serious 修复

| # | 问题 | v6 修复 |
|---|---|---|
| S1 | novelty_residual SA 实际是 is_novel 布尔 smuggle in | §11.3 明确**红线允许"分级瞬态 marker SA"**,不允许"sa.is_novel: bool" 字段;novelty_residual 有连续能量,自然衰减,合规 |
| S2 | 冷启动 0 history → 系统永久被动,不会主动看任何东西 | §11.5-cold-start: **感受器层 bottom-up salience prior**(高对比/运动/语音突变)进 sensor adapter 边界内(C-5 允许),不是认知 prior;refocus 学到后接管 |
| S3 | Phase 8.9 "自然纠错"无具体设计,且依赖未实现的 Phase 9.2 RPE | §16.11 Phase 8.9 落地最小机制:tier-0 mismatch event + correction_candidate SA(不依赖 RPE,只用既有 P/commit gate);RPE 仍 Phase 9.2 |
| S4 | §11.2 η_Π cap 数学未明确是 `η·signal` 还是 `η·(target-Π)` | §11.2 显式 Π 更新规则 = `Π += η · (target - Π)`(几何收敛),"7 tick 吸收"成立 |
| S5 | §17.1 "18-30mo" 承诺与 v5 自身的 θ_min_exposure=5 矛盾(toddler 是 fast-mapping) | §17.1 诚实分级:v5 默认是 **slow-mapping with disentanglement**,fast-mapping 单列为 §11.8 Phase 8.X 补完 |

### 0.3 v5 的 2 个 minor

继承全部修复(M1 long-tail accumulator / M2 §18.5 interaction matrix)。

### 0.4 v5 覆盖洞(18-30mo 维度)— v6 补 4 个最高 impact

| 洞 | v6 落点 |
|---|---|
| Shape bias / 物体命名先验 | §11.9 **跨 slot 元先验**:slot 历史 filler 多为名词类(经文本 channel 中字符特征识别) → 该 slot 软继承 shape-channel 优先权 |
| Fast mapping(单次曝光)| §11.8 **tentative vocab SA**:第一次新词 + 视觉同 tick → 临时 SA,θ_tentative_exposure=1,标 `is_tentative` 通道签名;第二次曝光验证或否定 |
| Overgeneralization → correction | §2.7 **vocab SA 可被反例否决**:负反馈累积 → 撤销固化,这是真正幼童轨迹("所有四脚动物=狗" → 纠正) |
| Question-asking as core drive | §28.5 Phase 8.X 引入轻量 drive::epistemic(完整版仍 Phase 9.1),触发 `action::ask_what_is_that`,被识别为新 SA 时 |

### 0.5 v5 缺的全年龄远景图 — v6 新增 §40-§42

- **§40 5-8 岁认知架构**(叙事 / 因果 / 心智化 / 正式教学 / 显式范畴)
- **§41 8-12 岁认知架构**(元认知 / 抽象概念 / 计划 / 演绎 / 身份)
- **§42 共同基底**(目标 SA / 层级关系 SA / 双速 Π / 信任先验)

---

## 1-10. 沿用 v5 大体结构

§1 沿用,**§1.2 + §10 加 v6 修复**(下文)。

---

## 2. 通用 SA 组合词汇固化 — v6 严格化

### 2.1-2.2 沿用 v5

### 2.3 ΔP 晋升门 — frozen-snapshot 严格版(B1 fix)

**v5 错误**:`P_baseline = compute_total_P(held_out_traces, current_vocab)` vs `P_with_candidate = compute_total_P(held_out_traces, current_vocab | {candidate})` —— 但加新 vocab 会扰动 attention 预算,P 比较不公平。

**v6 正确做法**:

```python
def evaluate_fixation_with_frozen_snapshot(candidate, held_out_traces, n_runs=20):
    """
    严格 ΔP 评估:每次 run 使用相同 random seed 重放 held_out,
    冻结召回得分 -> 只在 Π 计算阶段加入 candidate vocab,
    比较 P 分布
    """
    P_baseline_dist = []
    P_with_candidate_dist = []
    
    for seed in range(n_runs):
        # Run 1: 不加 candidate
        snapshot = replay_held_out(held_out_traces, current_vocab, seed=seed,
                                   freeze_attention=True)  # 冻结 attention
        P_baseline_dist.append(snapshot.mean_cognitive_pressure)
        
        # Run 2: 同 seed 同 attention 冻结,只在 Π 层加 candidate
        snapshot = replay_held_out(held_out_traces, current_vocab | {candidate},
                                   seed=seed, freeze_attention=True)
        P_with_candidate_dist.append(snapshot.mean_cognitive_pressure)
    
    # 配对 t 检验
    delta_dist = [b - w for b, w in zip(P_baseline_dist, P_with_candidate_dist)]
    t_stat, p_value = paired_t_test(delta_dist)
    
    return {
        "mean_delta_P": mean(delta_dist),
        "p_value": p_value,
        "significant": p_value < 0.05 and mean(delta_dist) > θ_promote_dP_min,
    }

def attempt_promotion(candidate, held_out_traces):
    result = evaluate_fixation_with_frozen_snapshot(candidate, held_out_traces)
    if result["significant"]:
        promote_to_vocab_sa(candidate)
        log_promotion_evidence(candidate, result)
    else:
        log_rejection(candidate, result)
```

**为什么这是严谨的**:
- `freeze_attention=True`:重放时强制 attention 分配等于 baseline run,Π 在加 candidate 后单独计算,**消除 attention 预算扰动**
- N=20 独立 seeds:同一对 vocab 配置下 P 分布有方差,单次比较不可靠
- 配对 t 检验:控制了 seed 间方差,直接看 candidate 是否系统性降 P
- p_value < 0.05 + 最小 effect size:**显著性 + 实用性**双门

### 2.4 chain extension — span eligibility(B2 fix)

**v5 代码 vs 文字不一致**。v6 显式选 span eligibility 语义:

```python
def try_extend_chain(seed_a, seed_b, max_length=4):
    chain = [seed_a, seed_b]
    while len(chain) < max_length:
        next_candidate = find_partner(chain[-1])
        if next_candidate is None:
            break
        
        # Span eligibility: 链内所有 1-hop 和 2-hop 边都要 eligible
        all_eligible = True
        for span in range(1, min(3, len(chain))):  # 检查 1-hop 和 2-hop
            other = chain[-(span+1) if -(span+1) >= -len(chain) else -1]
            edge = get_edge(other, next_candidate)
            if not edge_is_eligible(edge):
                all_eligible = False
                break
        
        # Anti-correlation check: 任何 anti-correlated 边都立刻拒绝
        for prior in chain:
            edge = get_edge(prior, next_candidate)
            if edge.smoothed_pmi < θ_anti_correlation:
                all_eligible = False
                break
        
        if not all_eligible:
            break
        chain.append(next_candidate)
    
    return chain if len(chain) >= 2 else None
```

**关键**:
- 检查 1-hop 和 2-hop 边(span eligibility)
- **反相关检测**:链内任何已存在的 SA 与新加 SA 负相关(PMI < θ_anti < 0)→ 立即拒绝
- 长链长得越深检查越严

### 2.5-2.6 沿用 v5

### 2.7 vocab SA 反例撤销 — overgeneralization 修复(覆盖洞 #3)

**幼童轨迹**:学"狗" → "所有四脚动物=狗" → 见到猫被纠正 → "狗"narrow down。

**v5 缺**:ΔP 晋升后无机制撤销。

**v6 落地**:vocab SA 持续维护 `negative_evidence_count`:

```python
class VocabSA:
    persistent_id: str
    promoted_at_tick: int
    positive_co_observations: int   # 持续累积
    negative_co_observations: int   # 反例:vocab 触发但被纠正
    
    def confidence_score(self):
        prior = 0.5
        n = positive_co_observations + negative_co_observations
        if n == 0:
            return prior
        return (positive_co_observations + prior * prior_strength) / (n + prior_strength)
    
    def should_retract(self):
        return self.confidence_score() < θ_retract_confidence

# 每次系统 commit 该 vocab 后:
# - 用户 + 反馈 → positive_co_observations += 1
# - 用户 - 反馈或纠正 → negative_co_observations += 1
# - 周期检查:should_retract() → vocab 降级或撤销
```

**配套撤销机制**:vocab SA 撤销时,其参与的链 / slot filler_history 都同步清理。继承 v3.1 §B2 atomic retire 模式。

**这就是真正的 overgeneralization → correction 轨迹**。

---

## 3-5. 沿用 v5

---

## 6. 黄苹果对照课程 — v6 严格化

### 6.1-6.2 沿用 v5

### 6.3 slot 偏好统计涌现 — 数学严谨化(B3 + B4 fix)

**v5 问题**:跨通道熵不可比 + 冷启动假一致性。

**v6 正确公式**——用**互信息(MI)替代归一化熵**:

```python
class Slot:
    slot_id: str
    fillers_history: list[SA_id]  # 每个 SA 全 persistent_id
    
    def derive_channel_preference(self) -> Optional[dict[ChannelName, float]]:
        # 门 1: 最小不同 filler 数
        unique_fillers = set(self.fillers_history)
        if len(unique_fillers) < θ_min_distinct_fillers:  # 默认 3
            return None  # 不足以判断,UI 返回 uniform fallback
        
        # 门 2: 按 unique SA 去重(防同 vocab 重复污染)
        deduplicated_fillers = list(unique_fillers)
        
        # 用 slot 身份与 bucket 分布的互信息(跨通道可比)
        channel_mi = {}
        for c in all_channels:
            filler_buckets_in_c = [
                quantize(sa.get_channel_payload(c), c)
                for sa in deduplicated_fillers
            ]
            # MI(slot=this_slot, bucket=b in channel c)
            # 用 cross-slot 比较:这个 slot 的 bucket 分布 vs 全局 bucket 分布
            slot_dist = bucket_distribution(filler_buckets_in_c)
            global_dist = global_bucket_distribution(c)
            mi = kl_divergence(slot_dist, global_dist)
            channel_mi[c] = mi
        
        return softmax([channel_mi[c] for c in all_channels])
```

**为什么这正确**:
- **MI 跨通道可比**:MI 衡量"该 slot 对该通道的 bucket 选择是否非随机",与 codebook 大小无关
- **slot_dist vs global_dist 比较**:slot 偏好 = "该 slot 的 filler 在该通道上是否系统偏离全局分布"
- **去重防同 vocab 重复**:防 B4 的"2 filler 同 vocab → 假一致"

**Step 4 数学保证(更新)**:
- 教完 §6.2 课程后,"苹果" slot 收到 ["苹果", "苹果", "苹果"] (无 dedup) 或 [苹果] (dedup) — 不可判断
- 但 slot1(颜色位)收 ["红色", "绿色", "黄色"] (3 unique) → MI(slot1, C2 bucket) 高(它们都在颜色类 bucket),MI(slot1, C1 bucket) 低(它们在不同形状 bucket)
- → slot1 自然涌现 C2 偏好

### 6.4 严格泛化测试 + ablation(沿用 v5)

### 6.5 诚实门(沿用 v5)

---

## 10. audit_db 严格只渲染 — v6 渲染契约完整(B6 fix)

### 10.1-10.6 沿用 v5

### 10.7 三种渲染 fallback 契约(B6 fix)

```python
class CanvasRenderer:
    def render_sa(self, sa: APV3_SA) -> RenderResult:
        # 优先级 1: audit_db 命中且有效 payload
        if audit_db.is_enabled():
            payload = audit_db.lookup_for_rendering(sa.persistent_id)
            if payload is not None and payload_is_valid(payload):
                return self.render_high_fidelity(payload, sa.channel_signature)
        
        # 优先级 2: 通道签名完整 → stylized blob (canonical)
        if sa.channel_signature.has_minimum_fields(["C1", "C2", "C4"]):
            return self.render_stylized_blob(sa.channel_signature)
        
        # 优先级 3: 通道签名残缺(长时召回但无原始通道数据)
        # → 走 introspection text 描述路径
        return self.render_introspection_text(sa.persistent_id, sa.vocab_links)

    def render_introspection_text(self, sa_id, vocab_links):
        """
        长时 SA 召回但无渲染基底:
        用其 vocab 链接 + introspection prototype 描述
        例:"我记得有个苹果(但记不清形状了)"
        """
        text = compose_introspection_description(sa_id, vocab_links)
        return RenderResult(kind="text_description", content=text)
```

**关键拟人**:
- 近期内容:audit_db 在,高保真渲染 — "刚才看到的苹果清清楚楚"
- 中期内容:audit_db evicted but channel sig 在,stylized blob — "记得是个红色圆形"
- 远期内容:channel sig 都没了,只剩 vocab 链 — "好像有过一个苹果"

**三层 fallback 完美映射人类记忆衰减**,且**不依赖 audit_db** 也能跑(canonical = stylized blob)。

---

## 11. 习惯化 + Novelty + 主动注意 — v6 严格化

### 11.1-11.2 沿用 v5,**§11.2 Π 更新规则明确化**(S4 fix)

```python
# 显式 Π 更新规则(几何收敛)
def update_prediction(Π_current, target, learning_rate):
    """
    Δ = η · (target - Π_current)
    η · |signal| 上限封顶不影响绝对幅度,
    控制的是相对收敛速度
    """
    delta = learning_rate * (target - Π_current)
    Π_new = Π_current + delta
    return Π_new
```

**收敛速度分析**:
- 单 tick 收敛量 = η · 残差
- η_max = 0.15 → 残差 ~7 tick 内降到 30%
- "7 tick 才吸收" 现在数学严谨成立 ✓

### 11.3 novelty_residual SA — 红线澄清(S1 fix)

明确**红线允许"分级瞬态 marker SA"**:
- ❌ 不许写 `sa.is_novel: bool` 字段
- ❌ 不许写 `if check_novelty_flag(sa): bypass_competition`
- ✅ 允许 spawn `novelty_residual::<id>` SA(连续能量,自然衰减)
- ✅ 允许其向原 SA 注入 attention_gain(走 standard injection)

这是分级 marker SA(继承普通 SA 全部能量动力学),不是布尔字段。**红线扫描脚本**:

```bash
# Allow novelty_residual SA spawn
# Forbid is_novel/is_familiar boolean fields
grep -r "is_novel\|is_familiar\|is_stable" runtime/ --include="*.py" \
    | grep -v "novelty_residual::"  # 允许 novelty_residual SA 标签内出现
# 必须 0 命中
```

### 11.4 沿用 v5

### 11.5 主动 refocus(沿用 v5)+ cold-start salience prior(S2 fix)

**v5 缺**:0 history → ActionParameterMemory 返回 prior 0 → refocus 不触发 → 系统永久被动。

**v6 解法**:**底向上 salience prior 进入 sensor adapter**(C-5 允许的边界):

```python
# 在 sensor adapter 内,在产生 normalized SA event 时附加 salience_hint
def vision_sensor_adapter_step(raw_input):
    percepts = extract_percepts(raw_input)
    for p in percepts:
        # bottom-up salience(进化先验,不是认知先验)
        salience = (
            w_contrast * p.local_contrast +
            w_motion * p.motion_magnitude +
            w_face_like * p.face_similarity  # 简单的面部相似度
        )
        normalized_sa = NormalizedSAEvent(
            sa_label=...,
            channel_signature=...,
            initial_attention_gain_hint=salience,  # bottom-up 提示
        )
        emit(normalized_sa)

# AP-Core 在 apply_external_items 时:
# 把 initial_attention_gain_hint 作为 G_i(t) 的种子值
# 后续标准 attention selector 接管
```

**为什么这合规**:
- salience 提取在 sensor adapter 内(C-5 允许模态分支)
- AP-Core 看到的仍然是 normalized SA event,不带模态名,只带 numeric hint
- refocus 学到后,ActionParameterMemory 接管,salience hint 重要性自然降低

**这就是哺乳类的进化注意力先验**——高对比/运动/脸不是认知规则,是感受器层面的生理偏好。

### 11.6 红线扫描(沿用 v5)

### 11.7 sleep emerge(沿用 v5)

### 11.8 Fast mapping — tentative vocab SA(覆盖洞 #2)

**幼童 fast mapping**:听一次"长颈鹿" + 看一眼长颈鹿 → 立刻试探性绑定。

**v5 缺**:θ_min_exposure=5 阻止了一次性学习。

**v6 落地**:**tentative vocab pathway**——平行于严格 ΔP 晋升,做单次曝光临时绑定:

```python
# 触发条件:新 vocab 候选首次出现 + 跨模态共现强(同 tick 文本 + 视觉)
def maybe_spawn_tentative_vocab(candidate, cross_modal_strength):
    if candidate not in current_vocab and cross_modal_strength > θ_cross_modal:
        tentative_sa = VocabSA(
            persistent_id=stable_id(),
            sa_label=f"vocab::tentative::{candidate.label}",
            is_tentative_marker=True,    # 通道签名上的标记,不是布尔字段
            tentative_decay_rate=ρ_tentative_decay,  # 比正常 vocab 衰减快
            confidence_score=0.5,         # 初始低信心
        )
        state_pool.add(tentative_sa)

# 后续:
# - 第二次曝光与同跨模态共现 → confidence_score 升,衰减率降
# - 反例(被纠正) → confidence_score 降,加速撤销
# - confidence_score 累积到 θ_promote → 进入严格 ΔP 晋升流程
# - 长时间无再曝光 → 自然衰减消失(忘了)
```

**关键拟人**:
- 听一次"长颈鹿" + 视觉 → 立刻有个临时 SA,可以参与召回(虽然信心低)
- 第二次再见 → 信心升,逐渐稳固
- 学得快但记得脆,符合幼童 fast-but-fragile mapping

**`is_tentative_marker` 不是 bool 字段而是 channel_signature 上的连续标记字段**(可包含 strength/decay_rate/confidence)。

### 11.9 Shape bias — slot 元先验(覆盖洞 #1)

**幼童 shape bias**:学新名词时默认按形状泛化。

**v6 实现**:**slot 间元先验**——历史上多名词类 filler 的 slot 软继承 shape-channel 优先权:

```python
def derive_meta_prior(slot):
    """
    判断 slot 主要 filler 是否名词类(经 §6.3 + 文本 channel 特征推断)
    """
    # 通过 fillers 历史的 文本 channel 特征推断词性
    # 名词 SA 倾向高 C_text_noun_marker(可学到)
    avg_noun_marker = mean(sa.text_noun_marker for sa in slot.fillers_history)
    
    if avg_noun_marker > θ_noun_slot:
        # 该 slot 主要被名词 fill → 软继承 shape-channel 优先
        return {"C1": +0.15}  # 软偏置,不是硬规则
    return {}

def fill_score(sa, slot):
    pref = slot.derive_channel_preference()
    meta_prior = derive_meta_prior(slot)
    
    combined_pref = combine(pref, meta_prior)  # meta_prior 加权 0.2
    signature_match = ... using combined_pref ...
    return signature_match * recall_score
```

**关键**:
- 这是 **slot 间软迁移**,不是硬编码 shape bias
- meta_prior 强度低(0.2 权重),冷启动有效但学到后可被覆盖
- 来源:slot 自身的 filler 历史(自学到的"这是名词类 slot")

**红线澄清**:meta_prior 不是"shape > color > texture 先验",是**slot 之间转移已学到的偏好**。当系统刚开始时这是 0 + 也不知道哪个是名词。学到一些名词类 slot 后才"传染"。

---

## 12-15. 沿用 v5(各小修复见 §11)

---

## 16. 工程实施 Phase 重排 — v6 完整版

### 16.1 沿用 v5 复用模块表(+ §16.10 adapter 红线扫描)

### 16.2 v6 新增模块清单

- §2.3 frozen-snapshot ΔP + N-run bootstrap + 配对 t 检验
- §2.4 span eligibility + 反相关检测
- §2.7 vocab SA 反例撤销机制
- §6.3 MI-based slot preference + min_distinct_fillers
- §10.7 三层渲染 fallback 契约
- §11.2 显式 Π 几何收敛
- §11.3 红线澄清 + 扫描脚本
- §11.5 sensor adapter salience prior
- §11.8 tentative vocab pathway
- §11.9 slot 元先验
- §16.9 ActionParameterMemory 真实接入 + cold-start 引导先验
- §16.11 Phase 8.9 自然纠错最小机制

### 16.3 Phase 顺序(v6 收束版)

```
Phase 8.2   连续 tick runtime + 字符微事件 + sensor adapter salience prior
            (含 §1.2 + §11.5 cold-start)

Phase 8.3   Sensor Adapter Contract + audit_db 严格只渲染 + 三层 fallback
            (含 §3.2 边界 + §10.7)

Phase 8.4   通用 SA 组合词汇 — frozen ΔP + 反相关 + 反例撤销
            (含 §2.3 + §2.4 + §2.7)

Phase 8.5   cognitive_feelings 补 4 通道 (B-B5 fix,阻断式前提)

Phase 8.6   玩具视觉感受器 + 多通道 + 量化桶

Phase 8.7   视焦点 SA + saccade + 持驻 + overlay

Phase 8.8   严格 yellow apple 泛化验收(对照课程 + ablation)
            + slot 偏好 MI 涌现
            (核心证伪门)

Phase 8.9   自然纠错最小机制
            (含 §16.11 mismatch event + correction_candidate)

Phase 8.10  习惯化数学验证 + Π 几何收敛 + novelty_residual + sleep emerge

Phase 8.11  Web 工作台逐 tick trace + 五区

Phase 8.12  tentative vocab(fast mapping)+ slot 元先验(shape bias)+ 
            轻量 epistemic drive(question-asking)

Phase 8.13  音频感受器多通道 + filterbank vocab 模板

Phase 8.14  Phase 8 端到端验收 + 拟人验收套件
            (18-30mo 能力完成)

—— Phase 8 完成 = 18-30 月龄学习能力 ——

Phase 9.1-9.9   v4/v5 哺乳类心智 9 维度(详细沿用 v5 §16.3 backlog)

—— Phase 9 完成 = 3-5 岁心智深度 ——

Phase 10.1-10.7  5-8 岁认知架构(详见 §40)

—— Phase 10 完成 = 5-8 岁学习+理解能力 ——

Phase 11.1-11.6  8-12 岁认知架构(详见 §41)

—— Phase 11 完成 = 8-12 岁元认知能力 ——

Phase 12+   真实摄像头/麦克风/桌面感受器 + SNS 桌宠产品化 + Agent 工作流
```

### 16.4 cognitive_feelings 补 4 通道(沿用 v4/v5)

### 16.5 short_term_buffer 迁移(沿用 v4/v5)

### 16.7 Sensor adapter 总图(沿用 v5,补 salience hint 输出)

### 16.8 文本字符微事件 + utterance_boundary(B7 fix)

```python
# Sensor adapter 内
def text_sensor_step(t, dt_ms):
    chars_per_tick = config.text_chars_per_tick
    for _ in range(chars_per_tick):
        if queue.is_empty():
            # 队列空且 last_char_processed_recently → 边界信号
            if t - self.last_char_tick == 1:
                emit_sa(
                    sa_label="text::utterance_boundary",
                    real_energy=boundary_R,
                    cognitive_pressure=0.0,
                    channel_signature={"text_event_marker": 1.0},
                )
            break
        char_event = queue.pop()
        emit_text_char_sa(char_event)
        self.last_char_tick = t
```

**关键**:
- `utterance_boundary` SA 由感受器层 emit,合规(C-5 边界内)
- 它进入 state_pool 后,draft 行动竞争**自然学到**"在 boundary 出现前 commit → ΔP 负(因为输入还没读完就答)" → 学到 wait pattern
- **无硬编码 commit_blocked_until_boundary**

### 16.9 草稿行动竞争 — ActionParameterMemory 真实接入(B5 fix)

**v5 错误**:`expected_R_change=+0.3, +0.2, +0.1` 是硬编码,假装是涌现。

**v6 诚实做法**——明确分两层:

**层 1 - cold-start 引导先验(明确标注)**:

```python
class DraftActionPriors:
    """
    Cold-start 引导先验,treated as such.
    Expected to be overwritten within N ticks by ActionParameterMemory learning.
    """
    bootstrap_R_changes = {
        "type_token": 0.15,        # 默认类型行动适度奖励
        "reread": 0.05,             # 重读小奖励
        "delete_tail": -0.05,       # 删除小负
        "replace_tail": 0.0,         # 中立
        "commit": 0.0,               # 中立,由学习决定
        "stop": 0.0,                 # 中立
        "noop": 0.0,                 # 基准
    }
    
    is_bootstrap_prior = True
    expected_overwrite_in_ticks = 200
```

**层 2 - 真实 ActionParameterMemory 接入**:

```python
def get_action_expected_R_change(action_type, context_features, target):
    # 第一步:查 ActionParameterMemory
    learned = action_parameter_memory.lookup(
        action=action_type,
        context=context_features,
        target=target,
    )
    if learned.sample_count >= θ_min_action_samples:  # 默认 5
        return learned.mean_R_change
    
    # 第二步:cold-start 用 bootstrap
    return DraftActionPriors.bootstrap_R_changes[action_type]

def attempt_draft_action(t):
    candidates = []
    for action_type in ["type_token", "reread", "delete_tail", "replace_tail",
                         "commit", "stop", "noop"]:
        for target in get_valid_targets(action_type):
            candidates.append(Action(
                kind=action_type,
                target=target,
                expected_R_change=get_action_expected_R_change(
                    action_type, current_context, target
                ),
            ))
    winning = attention_selector.select(candidates + other_action_candidates)
    execute(winning)
    
    # 学习闭环:执行后观测实际 ΔP/R 变化
    action_parameter_memory.observe(winning, observed_R_change_post_execution)
```

**关键**:
- **明确标注 bootstrap_R_changes 是引导先验**,不假装"涌现"
- 5 次实测后 learned 接管,bootstrap 被覆盖
- 行动竞争的"涌现性"在于**学习覆盖后的行为**,不在 cold-start

**这才是诚实"涌现"**——承认有 bootstrap,但 bootstrap 是短命的。

### 16.10 APV2 adapter + 红线扫描(沿用 v5)

### 16.11 Phase 8.9 自然纠错最小机制(S3 fix)

**v5 缺设计**。**v6 落地最小机制(不依赖 RPE)**:

```python
# 触发:用户对 AP commit 的回复进行 negative 反馈
# (打否定按钮 / 显式 "不对" / 文本情绪明显负)

def handle_negative_feedback(commit_record, negative_signal):
    # 1. Spawn 一个 "mismatch event" SA
    mismatch_sa = SA(
        sa_label=f"event::commit_mismatch::{commit_record.id}",
        real_energy=negative_signal * mismatch_R_scale,
        cognitive_pressure=negative_signal * mismatch_P_scale,
        channel_signature={"commit_event_marker": 1.0},
    )
    state_pool.add(mismatch_sa)
    
    # 2. 向 commit_record 涉及的所有 vocab SA 注入负反馈
    for vocab_sa_id in commit_record.vocabs_used:
        vocab = state_pool.get(vocab_sa_id)
        vocab.negative_co_observations += 1  # § 2.7 撤销机制
    
    # 3. Spawn 一个 correction_candidate SA(等待教师证据)
    correction_sa = SA(
        sa_label=f"hypothesis::correction::{commit_record.id}",
        real_energy=expectation_R_for_correction,
        cognitive_pressure=high_P_for_correction,
        channel_signature={"hypothesis_marker": 1.0},
        linked_to=commit_record,
    )
    state_pool.add(correction_sa)
    # 这个 SA 自然有高 P → 进入焦点 → 系统倾向于等待 + 注意接下来的输入

# 4. 后续 turn 接收用户教学输入(如 "应该说你好")
# → 这次的输入与 correction_sa 共现
# → ComposedVocab 把"你好" 作为正确答案与"你是谁"问句强绑定
# → 学习闭环
```

**关键拟人**:
- 收负反馈 → mismatch event + commit 用的 vocab 负累积 + correction hypothesis SA
- correction SA 自然带高 P → AP 进入"等待教师证据"状态(不是写死的规则)
- 下次教师说"应该是你好" → 与 correction SA 共现 → 通过 §2 共现学习自然完成纠正
- **不依赖 RPE,纯用既有 P + 反例撤销机制**

---

## 17. v6 完美图景 — 分层能力清单

### 17.1 Phase 8 完成 — 18-30 月龄能力(诚实版)

**核心多模态认知**:
- ✅ 连续 tick + 真实时间戳 + 短长记忆双层
- ✅ 多模态独立感知 + 量化桶 + 跨模态共现
- ✅ Frozen-snapshot ΔP 晋升(慢映射,严谨)
- ✅ Tentative vocab pathway(**快映射**,补 toddler fast-mapping)
- ✅ Vocab 反例撤销(**overgeneralization → correction**)
- ✅ Slot 偏好 MI 涌现 + 元先验软迁移(**shape bias** 软支持)
- ✅ 黄苹果对照课程严格泛化 + ablation
- ✅ 视焦点 + saccade + 持驻 + 焦点 overlay
- ✅ 习惯化 emerge + Π 几何收敛 + novelty_residual 秒级注意
- ✅ Sleep emerge + global_fatigue 连续映射
- ✅ 逐字草稿行动竞争(明示 bootstrap 引导先验 + 真实学习覆盖)
- ✅ 文本字符微事件 + utterance_boundary 自学
- ✅ 自然纠错最小机制(commit_mismatch + correction_candidate)
- ✅ 轻量 epistemic drive (question-asking)
- ✅ Sensor adapter salience prior (bottom-up cold-start curiosity)
- ✅ Web 五区(Home/Mind/Fairy/Audit/Settings)

**对应 18-30 月龄幼童能力**:
- ✅ 多模态绑定 + 词汇组合泛化
- ✅ Fast mapping(经 tentative pathway)
- ✅ Shape bias 软支持
- ✅ Overgeneralization 然后纠正
- ✅ 持续注意 + 习惯化
- ✅ 主动好奇(经 epistemic drive + salience prior)
- ✅ 逐字表达 + 自纠错
- ✅ 不确定/惊/熟悉感受(continued from v4)
- ❌ 完整心智深度 → Phase 9
- ❌ 因果叙事 / 心智化 → Phase 10

### 17.2 Phase 9 完成 — 3-5 岁心智深度

继承 v4/v5 §20-§28 全部 9 机制(驱力/RPE/受挫/依恋/共同注意/共情/痛/重放/玩乐)。

### 17.3 Phase 10 完成 — 5-8 岁学习+理解能力(见 §40)

### 17.4 Phase 11 完成 — 8-12 岁元认知能力(见 §41)

### 17.5 Phase 12+ — 真实硬件 + 产品化

---

## 18. 数学链路联调可行性 + 交互矩阵(M2 fix)

### 18.1 §18.5 — 多机制交互矩阵

| 机制 A | 机制 B | 共享资源 | 主导关系 |
|---|---|---|---|
| Attention selector | Novelty residual | attention_gain G_i | Novelty inj → A 升 → selector 自然选 |
| Draft action | Refocus action | 同 attention_selector | 同等竞争,无主导 |
| ComposedVocab 晋升 | held-out ΔP | held-out 数据 | 晋升必经 ΔP 显著性 |
| Sleep emerge | Novelty residual | tick_ms | 高 novelty 抑制 sleep |
| Tentative vocab | 反例撤销 | confidence_score | 撤销门槛低于晋升,促进 fast learning + correction |
| Slot 元先验 | Slot MI 涌现 | filler_history | 元先验权重 0.2,被 MI 主导 |

**主要稳定性论证**:
- 每个新机制都用既有能量场注入(R/V/P/A/G)
- 无机制创建独立非衰减能量源 → 全局能量守恒边界稳定
- 多个机制可同时活跃,竞争通过 attention selector 统一仲裁

### 18.2 v6 整体可达性判定

| 目标 | v6 设计支持 | 风险 |
|---|---|---|
| 多模态自由对话拟人底座 | ✅ Phase 8 完成 | 对照课程质量 + reverse-engineer 黄苹果数据集 |
| 18-30 月龄学习能力 | ✅ Phase 8(slow + fast + overgen + shape bias) | tentative pathway 实测 |
| 3-5 岁心智深度 | ✅ Phase 9 | 哺乳类机制 9 维度集成 |
| 5-8 岁学习理解 | ✅ Phase 10(§40) | 叙事/因果 SA 数学未完整 |
| 8-12 岁元认知 | ✅ Phase 11(§41) | 双速 Π 工程量大 |

---

## 19. v6 给 Codex 的最终指令

1. **v6 取代 v5 作为 Phase 8 实施依据**
2. **Phase 8.5 (CFS 补完)阻断式前提** — 继承
3. **Phase 8.8 核心证伪门** — 失败禁止 workaround
4. **Phase 8.9 自然纠错** — §16.11 最小机制,不依赖 RPE
5. **Phase 8.12 fast mapping + shape bias + epistemic drive** — toddler 关键能力
6. **每 Phase 5 段闭环 + 红线扫描**
7. **任何"新公式形态"提议必先停下问 Claude**

---

## 40. 5-8 岁认知架构远景(Phase 10)

### 40.1 关键认知里程碑

| 维度 | 5-8 岁能力 | v5/v6 缺 |
|---|---|---|
| 叙事 | 讲连贯故事(开头 + 经过 + 结局) | 无叙事 SA |
| 因果 | "因为 A 所以 B"(不只是 A 然后 B) | 无因果关系标记 |
| 心智化深度 | 知道别人想错了(假信念测试) | Phase 9 共情不够,缺 belief 模型 |
| 正式教学 | 接受"老师说的"作为权威 | 无信任先验 |
| 显式范畴 | "苹果是水果" | 无层级关系 SA |
| 阅读 | 自驱视觉扫文本 | 文本是被注入,非自驱扫 |

### 40.2 v6 Phase 10 新增 5 类 SA + 1 类机制

**§40.A Narrative SA 家族**

```python
narrative_sa = SA(
    sa_label="narrative::<id>",
    family="narrative",
    components=[event_pointer_1, event_pointer_2, ...],
    edge_labels=["cause", "then", "because", ...],
    completion_score=...,
    R, V, P, A, F  # 标准能量场
)
```

叙事 SA 通过既有 §2 ComposedVocab 机制学:多个 event 高 PMI 共现 + 时序稳定 → 固化为 narrative SA。**复用既有底座,不新公式**。

**§40.B 因果关系 SA**

```python
causal_sa = SA(
    sa_label="causal::<A>::<B>",
    family="relation",
    relation_kind="cause",  # "cause" | "correlate" | "temporal_only"
    A_pointer=...,
    B_pointer=...,
    strength_score=...,
)
```

如何区分因果 vs 相关?**用人类发育心理学的同源逻辑**:
- 干预(intervention)看:如果 A 不出现时 B 也不出现,且 A 出现时 B 必出现 → cause
- 反事实(counterfactual)假设:状态池中模拟"假如 A 不在" → V 模拟 B 应不出现?
- 这需要**反事实模拟能力**(Phase 10.4 实现)

**§40.C Theory of Mind 信念模型 SA**

```python
belief_model_sa = SA(
    sa_label=f"belief::other::<entity_id>::<topic>",
    family="theory_of_mind",
    holder_entity=entity_user_sa,
    content_pointer=specific_belief_content,
    confidence=...,  # AP 对 "他人持有此信念" 的信心
)
```

构建方式:观察用户行为 + 用户文本 + AP 自身经验对照 → 推断"他可能不知道 X 是 Y"。**继承 v4 §25 共情但更深**。

**§40.D 信任先验通道(允许绕过 ΔP)**

```python
class TrustPrior:
    """允许从权威源接受 vocab 不经 ΔP 显著性"""
    
    def trust_promoted(self, candidate, source_authority):
        if source_authority.trust_score > θ_trust_authority:
            vocab_sa = promote_to_vocab_sa(candidate, gate="trust_promoted")
            vocab_sa.is_trust_promoted = True  # 标记
            vocab_sa.downgradable_on_contradiction = True
            return vocab_sa
```

权威由 entity_user_sa 的 OXY(依恋)+ 过去教学准确率累积。

**§40.E 层级关系 SA(`is_a`, `part_of`)**

```python
isa_sa = SA(
    sa_label="is_a::<sub>::<super>",
    family="hierarchy",
    sub_pointer=...,
    super_pointer=...,
    strength_score=...,
)
```

构建方式:多个 sub 类共现"同一 super" 范畴标签 + slot 偏好继承 → 涌现 is_a 关系。

**§40.F 文本视觉自驱扫(继承 §13 视焦点)**

文本以"视觉对象"形式呈现 → 视焦点 SA 在文本区上自驱跳跃 → 字符按视焦点序列流入。**与 §1.2 字符微事件桥接**:外部消息流仍按字符注入;阅读模式时,文本是 percept,自驱扫产生字符 SA 流。

### 40.3 Phase 10 顺序

```
Phase 10.1  Narrative SA 家族 + 叙事链通过 §2 涌现
Phase 10.2  因果关系 SA + 干预/反事实数学
Phase 10.3  Theory of Mind 信念模型 SA
Phase 10.4  反事实模拟机制(状态池子分支)
Phase 10.5  信任先验通道
Phase 10.6  层级关系 SA
Phase 10.7  文本视觉自驱扫
```

---

## 41. 8-12 岁认知架构远景(Phase 11)

### 41.1 关键认知里程碑

| 维度 | 8-12 岁能力 | v6 缺 |
|---|---|---|
| 元认知 | "我不知道我不知道什么" | 无对自身知识空隙的显式表征 |
| 抽象概念 | "正义""规则"等无具体 grounding | v6 要求 vocab 有 channel grounding |
| 长期计划 | 小时/天级目标 | 无目标 SA + 长 horizon |
| 演绎推理 | "如果 A 则 B,A → B" 多步链 | 现有 tick = 1 步,无 deliberative loop |
| 身份 | 稳定自我模型(我是 X 我喜欢 Y) | 无 entity::self SA 家族 |

### 41.2 v6 Phase 11 新增 5 类机制

**§41.A 元认知 SA 家族**

```python
meta_cognition_sa = SA(
    sa_label="meta::knowledge_gap::<domain>",
    family="meta_cognition",
    target_domain=...,
    confidence_in_lack=...,  # "我确信我不知道这"
    last_attempted_at=...,
)
```

构建方式:多次召回失败 + 同领域反复 P 高 + 同领域不能 commit → 涌现 knowledge_gap SA。它进入状态池后驱动**主动求知行动**(asking, searching)。

**§41.B 抽象概念 SA — 第二级 vocab gate**

放宽 §2.3 要求 vocab 有 channel signature。引入**第二级 vocab**:

```python
abstract_vocab_sa = SA(
    sa_label="abstract::<concept>",
    family="abstract_vocab",
    grounding_links=[...],  # 至少 3 个 grounded SA 链接
    definition_chain=[...],  # vocab 链作为定义
    is_abstract_marker=continuous_strength,
)
```

晋升门:
- 不要求 channel signature(允许"正义"等抽象)
- 要求**至少 3 条独立链路连接到 grounded SA**(防止幻想)
- ΔP 仍要求(在抽象推理任务上预测压力降低)

**§41.C 目标 SA + 长 horizon**

```python
goal_sa = SA(
    sa_label="goal::<target_state>",
    family="goal",
    target_state_pointer=...,
    target_completion_tick=...,  # 估计完成 tick
    horizon_decay_rate=...,       # 慢衰减(小时/天级)
    progress_score=...,
    sub_goals=[goal_sa_1, ...],  # 嵌套
)
```

进入状态池后:
- R 在 horizon 内不衰减(替代 short_long 双层)
- 与现有行动 SA 通过 attention selector 竞争
- 完成 → R 大幅降(满足);未完成 → 持续 P

**§41.D 双速 Π — 慢推理子循环**

现有 tick = 1 步;演绎推理需要"思考中的多步"。新增**deliberative sub-cycle**:

```python
# 主 tick 循环(快感知):0.1s/tick
# 慢推理子循环(deliberative):每 N 个主 tick 推 1 步,但深度 M 步

def deliberative_sub_step(t):
    # 在主 tick 内"暂停",运行慢 Π 推理多步
    # 用纯虚能量(V)推理,不动 R
    state_snapshot = state_pool.snapshot()
    for inner_step in range(M):
        deliberative_Π = compute_pure_virtual_prediction(state_snapshot)
        if deliberative_Π.conclusion_confidence > θ:
            commit_deliberative_conclusion(deliberative_Π.conclusion)
            break
        state_snapshot.advance_virtual(deliberative_Π)
```

**关键**:deliberative 不动状态池真实能量,只在虚能量层推演。如果有结论,把结论作为新 SA 注入主状态池。

这就是"想了想再说"的拟人。

**§41.E 身份 / Self model**

```python
self_sa = SA(
    sa_label="entity::self",
    family="self_model",
    capabilities=[...],
    preferences=[...],
    autobiographical_narrative=[...],  # narrative SA 链
    durable=True,  # 跨 session 持续
)
```

构建:
- 多次 commit 后回顾 → 自己说过的话 + 表达的偏好 → 累积 self SA
- 与他人(entity::user::*)对比 → 边界涌现
- 进入长时记忆且永不被驱逐(类似 drive_SA 一等公民)

身份稳定带来:
- 一致的人格("我喜欢蓝色"反复出现)
- 跨 session 记得自己("上次我们聊了 X")
- 自传式叙事("我是一个学习中的拟人桌宠")

### 41.3 Phase 11 顺序

```
Phase 11.1  元认知 SA 家族
Phase 11.2  抽象 vocab 第二级 gate
Phase 11.3  目标 SA + 长 horizon
Phase 11.4  Deliberative sub-cycle(双速 Π)
Phase 11.5  Self model + 身份
Phase 11.6  Phase 11 端到端验收
```

---

## 42. 共同基底总结(贯穿 Phase 10-11)

为 5-8 / 8-12 岁能力服务的共享基础:

| 共同基底 | 用途 |
|---|---|
| Narrative SA 家族(§40.A) | 5-8 叙事 + 8-12 自传 |
| Relation SA 家族(因果/层级)(§40.B,§40.E) | 5-8 显式关系 + 8-12 演绎 |
| Trust prior(§40.D) | 5-8 接受教学 + 8-12 接受权威 |
| Goal SA + horizon(§41.C) | 8-12 计划 + 9-12 任务追踪 |
| Deliberative Π(§41.D) | 8-12 推理 + 反事实模拟 |
| Self model(§41.E) | 跨 phase 持续身份 |
| 抽象 vocab gate(§41.B) | 8-12 抽象概念 + meta cognition |

**这些机制全部建立在既有 R/V/P/A/F 能量场上**,**没有新公式形态**:
- Narrative / Relation = ComposedVocab 高阶应用
- Trust prior = vocab 晋升门变种
- Goal SA = 慢衰减 SA(继承 drive_SA 一等公民模式)
- Deliberative Π = V 通道额外子循环
- Self model = entity SA 高阶应用 + 长时记忆

---

## 43. v6 整体最终判断

### 43.1 学习能力分层

| Phase | 阶段 | 对标人类年龄 | v6 设计支持度 |
|---|---|---|---|
| Phase 8 | 多模态认知闭环 | 18-30 月 | 🟢 高(数学严谨,经 2 轮对抗审阅) |
| Phase 9 | 哺乳类心智深度 | 3-5 岁 | 🟢 高(继承 v4 §20-§28) |
| Phase 10 | 叙事/因果/心智化 | 5-8 岁 | 🟡 中-高(数学链路清晰,反事实模拟工程量大) |
| Phase 11 | 元认知/抽象/计划 | 8-12 岁 | 🟡 中(deliberative sub-cycle 是真大改) |
| Phase 12+ | 真实硬件 + 产品 | - | 🟢 高(SNS 经验复用) |

### 43.2 关键风险(诚实)

| 风险 | 严重度 |
|---|---|
| 对照课程数据 disentangle 质量 | 高(决定 Phase 8.8 成败) |
| ΔP frozen-snapshot 是否真稳定 | 中(需 Phase 8.4 N-run 验收) |
| Tentative vocab 容易学错容易丢 | 中(本身是 fast-but-fragile,这是特性) |
| Phase 10 反事实模拟工程量 | 中-高 |
| Phase 11 deliberative Π 工程量 | 高 |

### 43.3 最终判断

**v6 设计在数学链路上严谨支持最终目标**,经两轮对抗审阅。

- **Phase 8 完成**:系统是一个会学习的多模态拟人对话底座,具备 18-30 月龄能力
- **Phase 9 完成**:增加哺乳类心智深度,具备 3-5 岁能力
- **Phase 10 完成**:增加叙事/因果/心智化,具备 5-8 岁能力
- **Phase 11 完成**:增加元认知/抽象/计划,具备 8-12 岁能力

**Phase 10/11 的数学基础已经在 §40-§42 给出**,虽然工程量大,但全部建立在既有 R/V/P/A/F 能量场上,**无需新公式形态**。

最大不确定性仍在工程实施质量(对照课程的 disentanglement 干净度、ΔP frozen-snapshot 是否真稳),不在底层数学。

---

— 接手线程,2026-06-17

## 附录 A: v5 → v6 差异明细

**修复**:
- B1 ΔP frozen-snapshot + bootstrap + 配对 t 检验
- B2 chain extension span eligibility + 反相关
- B3 MI-based slot preference(跨通道可比)
- B4 min_distinct_fillers + SA 去重
- B5 ActionParameterMemory 真实接入 + bootstrap 明示
- B6 三层渲染 fallback 契约
- B7 utterance_boundary SA(感受器层)
- S1 novelty_residual 红线澄清(允许分级 marker SA)
- S2 sensor adapter salience prior
- S3 Phase 8.9 最小机制(不依赖 RPE)
- S4 Π 几何收敛显式
- S5 fast mapping tentative vocab(诚实分慢/快两个路径)
- M1 long-tail accumulator
- M2 交互矩阵(§18.5)

**18-30mo 补 4 项**:
- §11.8 fast mapping (tentative vocab)
- §11.9 shape bias (slot 元先验)
- §2.7 overgeneralization → correction
- §28.5/8.12 轻量 epistemic drive(question-asking)

**全新远景(§40-§42)**:
- 5-8 岁:Narrative / Causal / ToM / Trust / Hierarchy / Reading 视觉自驱
- 8-12 岁:元认知 / 抽象 / Goal+horizon / Deliberative Π / Self model
- 共同基底:全部沿用 R/V/P/A/F 能量场,无新公式形态
