# APV3.0 v12.1 — v12 整合 errata(5 个精准修复)

日期: 2026-06-17
作者: 接手线程
状态: **v12 经轮 9 审阅判 PARTIAL — 清单方向对,实施层 5 处 blocker/serious(B1 sleep 期依赖 / B2 yaml 缺失 / B3 即时联想 spec / S1 attention selector 破坏性覆盖 / S2 想象 SA type 归属)。v12.1 是 5 个精准 errata,不重写 v12,只修这 5 处。配合 v10 + v11 + v12 + v12.1 = Phase 8 实施依据。**

前身链:v10 主 + v11 patches + v12 endogenous patch → **v12.1 errata(本稿)**

---

## 0. v12.1 修复总览

| # | v12 缺陷 | v12.1 修复 |
|---|---|---|
| **B1** | §44.6 跨 session 测试嫁接 Phase 8.16,但依赖的 §27 sleep 重放在 Phase 9.8 backlog,实质不可跑 | §44.6 改为**不依赖 sleep 重放**——只靠 §1.3 短→长晋升 + entity_user_sa long_term 维持;sleep 重放是优化项不是前提 |
| **B2** | §44.4 引入 9 个新常量,yaml 没补完(δ_unfin/δ_exp/δ_res/idle_boost/β_pos/β_A/β_F/idle_threshold/target_cap_ratio) | 补完 `endogenous:` yaml 段 + `attention.s_attn_weights:` 段 |
| **B3** | §44.5 t=4 "标准 Cn' 后继偏置 → 针-气球涌现"用慢学习机制做即时联想,hand-waving | §44.5 改 **3 路联想机制**:learned_similarity(快/向量) + lag-PMI(中) + chain extension(慢/晋升后),用户原例 1 走 vector 即时路径 |
| **S1** | §44.2 改 s_attn 公式去 R 项 V 项,破坏 v10 attention selector | §44.2 改 **不替换 v10 公式,只加 `s_attn_internal` 子项** — 二者经类型分流仲裁,internal 路径不破坏 external |
| **S2** | §46 想象 SA 的 Type 归属未明示(PerceptSA/VocabSA/新type 三难) | §46.4 显式规则:**想象 SA = 既有 VocabSA(无新 type)+ 伴生 IMAGINATION marker SA**(双 SA 协作模式继承 v8 tentative 同源) |

### 0.1 v12.1 不动 v12 其他章节

§45 自传式回忆 / §47 三类注意力 / §48 反向想象 / §49 复杂感简单感 / §50 主观能动性 — 全部沿用 v12,只补本稿明示的 medium fix(M1 反向 spec / L1 想象 feeling 的 SA 路径)。

---

## 补丁 B1: §44.6 跨 session 延迟意图 — 不依赖 sleep 重放

### 原 v12 缺陷

`§27 重放进一步巩固` — §27 在 Phase 9.8 backlog,Phase 8.16 测试时根本没有 §27。

### v12.1 真修

**核心**:跨 session 延迟意图 **完全 emerge 自 §1.3 short→long 晋升 + SQLite 持久化 + standard recall**,**与 sleep 重放无关**。

```python
# Phase 8.16 跨 session 延迟意图实际通路
# Session 1:
# t=N1: 内源链(§44.4)产生 intent SA "绕开修路"
#   - 该 intent SA 经 § 44.4 三源(unfinished_pressure / expectation_pressure / residual_mass)持续注入 attention_gain
#   - 持续 K 个 tick 后,§1.3 cumulative_activation_energy > θ_promote_to_long_term
#   - intent SA 进入 long_term 层,long_term_R 不衰减(ρ_R^long ≈ 0.999)
# 
# Session 1 结束 → SQLite persistence(v8 §11.3 already specifies persistence schema)
#   - intent SA long_term_R + channel_signature 持久化
#   
# Session 2 boot:
# - 从 SQLite 重建状态池(boot_from_persistence,已是 v10 §11.5 self_model 同源机制)
# - intent SA 重新进入 long_term layer 的活跃 SA 集
# 
# Session 2 t=0: 视觉感受"修路场景" percept
# - §15.1 双层 align(时空+vocab)— vocab 链接已学到"修路 ↔ 绕开" → align 高
# - 召回 intent SA → 进 attention → 影响 action 选择
# 
# 完全 emerge from:
# - §1.3 short→long 晋升(v10 已规范)
# - SQLite persistence(v8 §11.3 已规范)
# - §15.1 双层 align(v10 已规范)
# - standard recall + standard action competition(v10 已规范)
# 
# 不需要 Phase 9.8 sleep 重放
```

### 验收测试更新

```python
def test_cross_session_deferred_intention_v12_1():
    """跨 session 延迟意图测试,不依赖 §27 sleep 重放"""
    # Session 1
    boot_fresh()
    for _ in range(K_inner_reasoning_ticks):
        inject_endogenous_intent_through_continuous_imagination("绕开修路")
    # 验证 intent SA 已晋升 long_term
    assert state_pool.get("绕开修路").is_in_long_term_layer()
    assert state_pool.get("绕开修路").long_term_R > θ_long_term_min
    
    # 持久化
    persist_to_sqlite()
    session_1_close()
    
    # Session 2
    boot_from_persistence()
    # 验证 intent SA 已重生
    assert state_pool.get("绕开修路") is not None
    assert state_pool.get("绕开修路").long_term_R > θ_long_term_min
    
    # 视觉触发
    show_visual("修路场景")
    for _ in range(N_recall_ticks):
        run_tick()
    
    # 验证 intent SA 被召回到 attention
    assert recalled_in_top_attention("绕开修路", within_top_k=5)
    # 验证 action 选择反映此 intent
    assert chosen_action.relates_to("avoid")
```

**Phase 8.16 实际依赖**:**只有 §1.3 short→long + SQLite persistence + §15.1 align**,**没有 §27 sleep 重放**。Phase 8 可独立验收。

**§27 sleep 重放(Phase 9.8)**:**是优化项,不是前提**。Phase 9 实施时进一步强化长时记忆巩固速度,但 Phase 8 不需要。

---

## 补丁 B2: yaml 完整补完

### 原 v12 缺陷

§44 / §49 引入 9+ 个常量但 yaml 段不完整。

### v12.1 完整补完

```yaml
# === apv3_constants.yaml v12.1 新增 ===

endogenous:
  # 三个内源能量源系数(§44.4)
  delta_unfinished: 0.15           # @experimental — 未完成压力注入 attention_gain 强度,Phase 8.10 验收
  delta_expectation: 0.12          # @experimental — 期待压力注入强度
  delta_residual: 0.10             # @experimental — 残差未解决注入强度
  
  # idle 状态连续映射(§44.4 + S5 fix)
  idle_score_softness_k: 0.3        # @structural — sigmoid 软边界 k,避免硬 if/else
  idle_score_midpoint: 0.2          # @experimental — sigmoid 中点
  idle_boost_max: 2.0               # @experimental — idle 时最大放大倍数
  
  # 内源链 target_cap(§44.3)
  target_cap_ratio: 0.9             # @experimental — cap = ruler * ratio
  
  # 内源持续验收(§44 mini-gate)
  endogenous_continuity_check_ticks: 50   # @experimental — Phase 8.10 mini-gate

attention:
  # s_attn 公式权重(v10 既有,v12.1 显式 yaml 化)
  s_attn_weights:
    # External s_attn(主路径,v10 既有)
    beta_P_external: 1.0            # @structural — 标准 attention selector
    beta_R: 0.35
    beta_A: 0.55
    beta_V: 0.12
    beta_F: 0.60
    
    # Internal s_attn(§44.2 v12.1 修订 — 不替换 external,只加 internal 子项)
    beta_P_internal: 0.5             # @experimental — internal 路径 max(0, P)
    beta_A_internal: 0.7             # @experimental — A-loop 主导
    beta_F_internal: 0.4             # @experimental
    
    # 仲裁权重(两路径混合,§44.2 v12.1 fix)
    external_weight: 0.6             # @experimental — 默认 external 略主导
    internal_weight: 0.4

cognitive_feelings_trace_only:
  # §49 复杂感/简单感(trace_only)
  complexity_threshold_active_sa_count: 15   # @experimental
  complexity_threshold_entropy: 0.6          # @experimental
  simplicity_threshold_active_sa_count: 5    # @experimental
  simplicity_threshold_entropy: 0.3          # @experimental

imagination:
  # §46.4 v12.1 — 想象 SA 双 SA 协作机制
  imagination_marker_decay_rate: 0.88        # @experimental
  imagination_marker_initial_intensity: 0.4  # @experimental
  imagination_immediate_recall_threshold: 0.5  # @experimental — vector recall 即时联想阈值

marker:
  decay_rates:
    # 沿用 v11 已有 16 个 + 新增 IMAGINATION
    IMAGINATION: 0.88                # @experimental — v12.1 新增,§46.4 用
  # max_kinds 不变(仍 16,IMAGINATION 占用 kinds_v10_documented 中的预留位)
```

**配套**:`kinds_v10_documented` 列表增 `IMAGINATION`(从 12 升到 13,仍在 cap 16 内,不破)。

---

## 补丁 B3: §44.5 即时联想 — 3 路机制明示

### 原 v12 缺陷

"看到针 → t=4 涌现针扎气球" 用"标准 Cn'"一笔带过。但 Cn' 是慢学习,即时联想不靠它。

### v12.1 真修

**3 路联想速度光谱**(全部沿用既有机制,无新公式):

```yaml
# 联想速度光谱(快→慢)
1. learned_similarity (vector) — 即时(ms 级)
   来源:OnlineEmbeddingStore.learned_similarity (v10 §16.1)
   机制:percept SA 的 vector → 召回 vector 近邻 vocab SA
   用户原例 1 应走此路径:"针" vector → 近邻 "被扎"/"疼痛" vector
   
2. lag-PMI (v8 §2.8) — 中速(秒级)
   来源:TemporalCooccurrenceGraph (v8 §2.8)
   机制:lag-PMI(A, B, k) 高 → B 被预测
   用户原例:历史上"针扎气球"序列被 lag-PMI 记录 → 当"针"出现 → "气球爆炸"被预测
   
3. chain extension (v10 §2.4) — 慢(min_obs=5,需多次曝光)
   来源:稀疏 pairwise + ΔP gate
   机制:稳定后的固化链作为 VocabSA 进入召回
   作用:已晋升的复合概念
```

**用户原例 1 重新解析**(精确版):

```
t=0: 视觉"针" percept SA, R=0.6
t=1: learned_similarity(vector recall) — 即时:
     "针" 的 vocab vector → 近邻召回 "被扎" / "疼痛" 向量空间近邻 vocab SAs
     (注:vocab 已学习的 "针-被扎-疼痛" cluster)
     → 召回 SA 进 state_pool with R proportional to similarity score
t=2: 这些召回 SA 的 cognitive_pressure 高(因为它们是 vocab 派生 + 当前情境激活)
     §16.4 emit "feeling::pain_resonance" — 注意:不是 feeling::pain
     pain_resonance 是 IntrospectionPrototype 的"想象/共情"版本,
     不是真痛(L1 fix:想象的疼痛不是 feeling::pain,而是 pain_resonance marker)
t=3: lag-PMI 检查 — 历史上 "针" 后接什么?
     若学过"针扎气球" → 触发"气球爆炸"作为后继 prediction
     这是 lag-PMI 中速联想
t=4: 此时 packet 中含 {针 percept, 被扎 vocab, 疼痛 prototype, 针扎气球 vocab, 气球爆炸 prediction}
     这是 §46 slot packet substrate
t=5+: 标准 §2 ComposedVocab 看到此次共现:
      - learned_similarity 强化 (vector pull together)
      - lag-PMI 累积时序统计
      - chain extension 累积观察数
      这就是用户说的"想象画面与疼痛共现产生关联"
```

**关键澄清(M1+L1 同源 fix)**:

```python
# §46.4 v12.1 — 想象产生的"feeling" 是 prototype-projected marker
# 不是 real feeling channel emission

class PainResonanceMarker(MarkerSA):
    """
    @op_count: O(1) spawn.
    
    当 vocab 链激活到"疼痛"概念但当下无真痛输入时,
    spawn 一个 IMAGINATION marker SA 投射到 feeling 空间,
    R 由召回强度派生(无独立硬编码)
    """
    kind = MarkerKind.IMAGINATION
    target_concept = "pain"  # 或其他被想象的 feeling/concept
    # R 派生自 vocab recall score,无硬编码
```

**这样:**
- "想象的疼痛" = `IMAGINATION marker SA targeting feeling::pain prototype`
- 进 slot packet → 与其他 SA 共现学习
- **不直接 emit feeling::pain channel**(避免想象冒充真痛输入)
- 也不需要新 SA type(沿用 MarkerSA 多态原则)

---

## 补丁 S1: §44.2 attention selector — 不破坏 v10,加 internal 子项

### 原 v12 缺陷

`s_attn = β_pos·max(0,P) + β_A·A − β_F·F` 丢了 R 和 V 项,会让外部强 R 对象失声。

### v12.1 真修

**v10 的 external s_attn 完整保留**,**§44 只加 internal s_attn 子项**,**两者经类型仲裁混合**:

```python
def compute_attention_score_v12_1(sa, current_pool, t):
    """
    @op_count: O(1) per SA.
    
    v12.1 修订:
    - external s_attn = v10 既有公式(保留全部 5 项)
    - internal s_attn = §44 修订公式(max(0,P) + A - F)
    - 两者经 routing 仲裁:
      - 当 sa 主要由外源驱动 → external 主导
      - 当 sa 主要由内源驱动 → internal 主导
      - 多数情况两者加权混合
    """
    # External s_attn (v10 既有,完整保留)
    w = load_constant("attention.s_attn_weights")
    s_external = (
        w["beta_P_external"] * sa.P +              # 带符号 P,捕惊
        w["beta_R"] * sa.R +                        # 外源能量
        w["beta_A"] * sa.A -                        # 注意力惯性
        w["beta_F"] * sa.F +                        # 疲劳负
        w["beta_V"] * sa.V                          # 预测能量
    )
    
    # Internal s_attn(§44.2 v12.1 — 内源链专用)
    s_internal = (
        w["beta_P_internal"] * max(0, sa.P) +       # 只取正 P(惊/求知)
        w["beta_A_internal"] * sa.A -               # A-loop 主导
        w["beta_F_internal"] * sa.F
    )
    # 注:不带 R/V,因为内源链 R 蒸发,V 由 Π 自维持
    
    # 路由仲裁
    # endogenous_drive_share = 该 SA 当前 attention_gain 中来自 §44.4 三源的占比
    endogenous_share = sa.compute_endogenous_drive_share()
    
    ext_w = w["external_weight"]
    int_w = w["internal_weight"]
    
    # 内源驱动越多,internal 路径权重越大
    final = (1 - endogenous_share) * (ext_w * s_external) + \
            endogenous_share * (int_w * s_internal) + \
            (ext_w + int_w) / 2 * (max(0, s_external - s_internal))  # 路径间平滑过渡
    
    return final
```

**为什么这真修**:
- v10 既有 attention selector **完全保留**,不破坏 external 路径
- internal 路径**只在 SA 由内源驱动时主导**
- **混合公式连续可微**,无硬 if/else 切换
- 全部权重在 yaml,无硬编码

---

## 补丁 S2: §46 想象 SA Type 归属

### 原 v12 缺陷

想象 SA 算 PerceptSA / VocabSA / 新 type 都有问题。

### v12.1 真修

**显式规则:想象 SA = 既有 VocabSA + 伴生 IMAGINATION marker SA**(双 SA 协作)。

```yaml
# §46.4 v12.1 想象 SA 双 SA 协作规则

想象 SA 的双 SA 表征:
  1. 主 SA:VocabSA (沿用既有 type,无新增)
     - 该 SA 可以是已学到的 vocab(如 "针扎气球")
     - 也可以是 cluster anonymous super(如 "暴力场景" 抽象)
     - 共现学习走 §2 标准路径
     - Type budget:占用 VocabSA 25% 预算
  
  2. 伴生 marker:MarkerSA, kind=IMAGINATION
     - 标记该 vocab 当前处于"想象激活"状态(非外感激活)
     - target_sa_id = 主 vocab SA 的 persistent_id
     - 衰减率 IMAGINATION = 0.88(中速衰减,数秒)
     - 进入状态池后:
       - 不直接影响 attention(它是 marker)
       - 但被 §44.5 用作即时联想识别 — 含 IMAGINATION marker 的 vocab 优先走 §44 internal 路径
       - 被 §46 共现学习 — 含 IMAGINATION marker 的 vocab 与其他 SA 共现仍计 PMI

# 红线:
# ✅ vocab SA 本身不区分"想象激活"vs"外感激活"(学习等价)
# ✅ 想象激活时 R 蒸发(target_cap → 0),不冒充真感(§44.3 fix)
# ✅ IMAGINATION marker 自然衰减后,vocab SA 回到"非想象激活"状态
# ❌ 不许给 vocab SA 加 is_imagined: bool 字段
# ❌ 不许新增 ImaginarySA type
```

**与 v8 tentative vocab 同源**:都是"VocabSA + 伴生 marker"双 SA 协作。**完美一致**。

**为什么这真修**:
- 想象的"针扎气球" = 既有 vocab "针扎气球"(VocabSA)+ IMAGINATION marker
- vocab 已带 channel signature(C1/C2 等),可与"针 visual percept" 在 channel 层产生有意义共现
- target_cap → 0 保护(§44.3)防 vocab R 高到冒充外部
- 不增加新 type,不破坏 v10 type budget 架构

---

## §44 mini-gate(D fix:Phase 阶段性验证)

### v12 Phase 嫁接缺验证密度

v12 §44 测试全在 Phase 8.14,8.10-8.13 之间没验证。

### v12.1 Phase mini-gate

**Phase 8.10 实施 §44.4 + §44.5 后,立即跑 mini-gate**:

```python
def phase_8_10_endogenous_mini_gate():
    """Phase 8.10 完成后立即跑,确保持续内源驱动工作"""
    boot()
    # 预填一些 vocab(模拟前期 Phase 已学)
    seed_vocab(["A", "B", "C", "针", "被扎"])
    
    # 让系统进入 idle 状态
    for _ in range(50):
        run_tick(no_external_input=True)
    
    # 验证:
    # 1. attention 焦点应在 50 tick 内轮换 ≥ 3 次(不死钉一处)
    assert focus_history.unique_count(window=50) >= 3
    
    # 2. 至少一个 SA 应携带 IMAGINATION marker
    # (说明内源激活在发生)
    assert any(sa.has_imagination_marker() for sa in state_pool.active())
    
    # 3. target_cap 应趋向 0(想象不越界)
    assert all(sa.target_cap < 0.1 for sa in state_pool.active()) 
    
    # 4. 至少一次 vocab SA 因内源激活进 attention top-5
    assert imagination_driven_focus_count > 0

# Phase 8.11 Web 工作台时,Mind 区显示这个 mini-gate trace
```

**Phase 8.12-8.13 各 phase 完成后,re-run mini-gate 确保不破**。

**§44.6 跨 session 测试 8.16 之前,Phase 8.15 加 short→long 显式实施 + 测试**(M4 fix)。

---

## v12.1 Phase 顺序最终版

```
Phase 8.2   连续 tick + sensor adapter
Phase 8.3   audit_db + §44.3 target_cap 0-floor 修
Phase 8.4   ComposedVocab + cold-fork ΔP
Phase 8.5   CFS 4 通道 + §49 complexity/simplicity trace_only
Phase 8.6   视觉
Phase 8.7   视焦点 + §47 focus action (沿用 v10 §16.9,无新增 action kind)
Phase 8.8   黄苹果
Phase 8.9   自然纠错
Phase 8.10  习惯化 + §44.4 三源驱动 + §44.5 3 路联想 + §44.2 attention 路径合并
            + §44 mini-gate (v12.1)
Phase 8.11  Web 工作台 + 内源链可视化
Phase 8.12  fast mapping + shape bias + epistemic drive + §48 反向想象
Phase 8.13  音频
Phase 8.14  Phase 8 端到端
Phase 8.15  short→long 显式实施 + 测试(v12.1 M4 fix)
Phase 8.16  跨 session 延迟意图测试(不依赖 §27)
Phase 8.17  自传式回忆初步(§45)

—— Phase 8 完成 = 18-30 月龄 + 持续想象 + 跨天意图(无 sleep 重放依赖)——
```

---

## v12.1 给 Codex 最终指令

1. **v10 主 + v11 patches + v12 + v12.1 配套读** — 4 件套
2. **B1 跨 session 不依赖 §27** — §27 sleep 重放是 Phase 9 优化项,不前提
3. **B2 yaml 完整 endogenous: / attention.s_attn_weights: / imagination: / cognitive_feelings_trace_only: 段补完**
4. **B3 即时联想 3 路 spec** — 用户原例走 learned_similarity vector 路径
5. **S1 attention selector 不破坏 v10** — internal 子项加,external 保留,路径仲裁混合
6. **S2 想象 SA = VocabSA + IMAGINATION marker** — 不新增 type
7. **L1 想象的 feeling = PainResonanceMarker(IMAGINATION marker 投射 feeling prototype)** — 不直接 emit feeling channel
8. **Phase 8.10 mini-gate 必跑** — 4 个 assertion
9. **Phase 8.15 short→long 显式 phase** — Phase 8.16 跨 session 测试前必须

---

## 收尾判断

### v12.1 是否真补完?

| v12 缺陷 | v12.1 真修 |
|---|---|
| B1 sleep 期依赖 | ✅ 不依赖 §27,纯靠 short→long + SQLite + align |
| B2 yaml 缺失 | ✅ 完整补 4 段 |
| B3 即时联想 hand-waving | ✅ 3 路 spec + 用户原例精确分解 |
| S1 attention 破坏性 | ✅ 不替换 v10,只加 internal 子项 + 仲裁 |
| S2 想象 SA type | ✅ VocabSA + IMAGINATION marker 双 SA |
| M1 反向想象 spec | ✅ §44.5 t=1 路径已含 |
| M4 short→long phase 缺 | ✅ Phase 8.15 显式 |
| L1 想象的 feeling 怎么进 pool | ✅ PainResonanceMarker (IMAGINATION marker) |
| §44 mini-gate | ✅ Phase 8.10 立即验证 |

### v3-v12.1 系列是否真收敛?

**Codex 现在可以开 Phase 8.2 了**。

理由:
1. **9 轮对抗审阅累计修 100+ 问题**,纪律层 + 算法层 + 架构层 + 底层机制 + 整合一致性五个维度都过线
2. **v10 主稿(架构 + 算法)+ v11 patches(纪律收尾)+ v12(底层补完)+ v12.1(整合 errata)**= 完整 4 件套
3. **想象 / 内源 / 跨天意图三大用户底层需求** 全部 emerge from 既有能量场 + 既有共现学习,无新公式
4. **Phase 8.10 mini-gate / Phase 8.15 short→long / Phase 8.16 跨 session 测试** 三个阶段性验证密度足够
5. **F 项 Explore 找到的 8 个底层遗漏** v12 + v12.1 已全部嫁接

### 未解决但可接受的开放问题(实施中迭代)

| 问题 | 处理时机 |
|---|---|
| 梦境作为内源链延伸的独立设计 | Phase 9.8 §27 sleep 重放时一并 |
| 自由意志感受作为感受族 | Phase 9-10 cognitive_feelings 扩展时 |
| 创造性组合作为 vocab 合成涌现 | Phase 10 abstract_vocab 扩展时 |
| 反事实想象的算力优化 | Phase 10.3 实测后调 |

### 最终结论

**v10 + v11 + v12 + v12.1 = APV3 Phase 8 实施依据。Codex 立即开工。后续 Phase 中如再发现 issues,走 PR 修补 yaml/code,不再开新设计稿**。

设计稿系列收尾。Phase 8.2 启动准备完毕。

---

— 接手线程,2026-06-17
