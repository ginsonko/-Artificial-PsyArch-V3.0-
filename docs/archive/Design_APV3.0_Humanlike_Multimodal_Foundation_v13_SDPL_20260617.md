# APV3.0 v13 — Source-Differentiated Packet Learning(根本性哲学升级)

日期: 2026-06-17
作者: 接手线程
状态: **Codex 给出 5 个 blocker/serious 后,用户做出根本性反驳:不能为追求"准确"而禁止想象证据;真正的 AP 哲学是"想象可学、可错、可表达、可推动行动,但必须带来源痕迹,通过奖惩自适应校准"。用户进一步升级:同内容 + 不同来源 → 不同 packet,行动学习按 packet 而非内容,真实/想象/听闻/记忆全部统一处理。v13 是这次哲学升级的严谨数学化。**

前身链:v10 主 + v11 patches + v12 endogenous + v12.1 errata → **v13(本稿)**

**关系**:v13 不替换前作,而是**升级所有学习规则的底层**。所有 §2 共现 / §40 因果 / §44 内源链 都升级为 packet-aware。

---

## 0. v13 哲学起点(必读)

### 0.1 用户哲学(原话)

> "我们的目的不是一个准确的机器,而是要拟人,而人类就是会在一些情况下把想象当成事实,并且以此为基础进行'错误但像人'的直觉性推理"

> "我们应当允许并支持它犯和人类一样的错误,但不能太过分"

> "人类是可以区分哪些是真实发生的事情,哪些是想象的,他们本身信号就是可区分的"

> "想象的内容和真实发生的事情会完全作为两件事来导致不同的后果"

> "想象本身这个信号,也是有认知范式的"

### 0.2 v13 核心原则: Source-Differentiated Packet Learning(SDPL)

```
内容 SA 共享,来源/感受 SA 分化进 packet,
行动后果按 packet 学习,不按内容学习。
```

正式表述:

$$\text{learn}: \quad \Delta Q(\text{action} \mid \text{packet}) = \eta \cdot \text{outcome} \cdot \text{eligibility}(\text{packet}, \text{action})$$

其中:
$$\text{packet} = \{\text{content\_SAs}, \text{source\_marker\_SAs}, \text{feeling\_SAs}, \text{slot\_context\_SAs}\}$$

**关键**:同一 content SA 在不同 packet 中学到完全不同的行动策略。这是 AP 处理一切**同内容异态**情况的统一底层原则(想象/记忆/听闻/猜测/梦/感知 全部走此模型)。

### 0.3 SDPL 的普适性

| 同内容场景 | source marker | 拟人效果 |
|---|---|---|
| 真实看到火 vs 想象火 | PERCEIVED vs IMAGINED | "看到火→逃";"想到火→警觉/检查" |
| 自己见过 vs 听别人说 | PERCEIVED vs HEARSAY | "我见过的→直接行动";"别人说的→可能求证" |
| 当下发生 vs 过去记忆 | PERCEIVED vs REMEMBERED | "现在的→响应";"记忆的→回想/讲述" |
| 确定的 vs 猜测的 | (high g) vs INFERRED | "确定的→断言";"猜测的→'可能...'" |
| 外界输入 vs 内心念头 | PERCEIVED vs IMAGINED | 同想象/真实 |
| 用户教的 vs 自己推断 | TAUGHT vs INFERRED | "学到的→信"vs"猜的→试" |
| 梦/幻想 vs 真实 | DREAM vs PERCEIVED | "梦里的不当真" |

**全部统一为 SDPL,无新机制**。v13 把这个发现作为 AP 第一原则,与"R/V/P/A/F 能量场""4 type SA""稀疏共现学习"同级。

---

## 1. v13 解决的 Codex 5 个 blocker/serious

### 1.1 Codex 原 Blocker 1(被用户哲学反驳,升级为 SDPL)

**Codex 原意**:想象共现不能等价于外感共现,要降权或禁止。

**用户反驳**:把想象当成事实正是拟人的核心,不能禁止。

**v13 统一结论**:想象**允许**进入学习,但以"想象来源 packet"身份;真实以"外感现实 packet"身份;两者**共享内容,分化后果**。详见 §50。

### 1.2 Codex Blocker 2 → §51 attention 凸组合门控(真修)

去掉 v12.1 那个有 bug 的三项混合,改为标准凸组合 + 外部 surprise 安全门。

### 1.3 Codex Blocker 3 → §52 attention gain 来源账本

每 SA 维护 `gain_by_source` 账本,endogenous_drive_share 从此账本派生,**有严格数学定义**。

### 1.4 Codex Serious 1 → §53 real_evidence_cap vs memory_attention_support 拆分

想象/记忆不冒充感(real_evidence_cap 仍→0),但记忆能进 attention(memory_attention_support 不归零)。

### 1.5 Codex Serious 2 → §54 测试不许偷用语义字串

跨 session 测试断言 action_id / learned successor,不查"avoid"中文。

### 1.6 Codex Serious 3 → §55 long_term cold index + cue-triggered rehydration

防开机全活跃。Cold pool + cue-driven 激活。

---

## 50. Source-Differentiated Packet Learning(SDPL)— v13 底层原则

### 50.1 EpistemicSource Marker 族(新)

继承 v11 marker_kinds_v10_documented 协议,**新增 5 个 EpistemicSource marker kinds**:

```yaml
# apv3_constants.yaml v13 新增
marker:
  max_kinds: 20                # 从 16 升 20(documented growth 协议)
  kinds_v13_epistemic:          # v13 新增 5 个,占用预留位
    - PERCEIVED                # 外部感受器输入产生的 SA
    - IMAGINED                 # 内源链产生(替代/标准化 v12 IMAGINATION)
    - HEARSAY                  # 听用户/他人陈述
    - REMEMBERED               # 从 long_term 召回(过去自感)
    - INFERRED                 # 内部推理(deliberative)
  # 注:DREAM 作为 IMAGINED 的特殊上下文标记(sleep 期),暂归 IMAGINED kind
  # 注:TAUGHT 是 HEARSAY 的强证据子类(教师源),也归 HEARSAY kind + 高 trust
  
  decay_rates:
    PERCEIVED: 0.97             # @experimental — 实际感受余响,快但可持续
    IMAGINED: 0.88              # @experimental — 想象痕迹,中速
    HEARSAY: 0.93               # @experimental — 听闻持续,可中长
    REMEMBERED: 0.96            # @experimental — 回忆余响,接近实感
    INFERRED: 0.90              # @experimental — 推理结论中速
```

**红线**:
- ❌ 不许给 content SA 加 `epistemic_source: str` 字段
- ✅ 来源**全部以 marker SA 形式**与 content SA 共在 packet
- ✅ 任意 content SA 可同时有多个 epistemic marker(如 REMEMBERED + INFERRED:"我推断我曾见过")
- ✅ 无 marker 时默认 = 当下 attention 自然激活,不预设来源

### 50.2 Packet 重定义(升级 BottomLayer §7 slot packet)

```python
class LearningPacket:
    """
    @op_count: O(|content|+|source|+|feeling|+|context|) ~ 50 ops to construct.
    
    SDPL 学习单元。一 tick 内由 slot packet 自然产生,
    内容 SA、来源 marker、感受 SA、上下文 SA 同 packet 内.
    """
    content_sas: list[SA_id]               # 来自 §46 slot_item
    source_markers: list[MarkerSA_id]      # EpistemicSource marker(可多个)
    feeling_sas: list[FeelingSA_id]        # cognitive_feelings 当 tick emitted
    slot_context: list[SA_id]              # slot_summary / slot_order / 外周 SAs
    
    def packet_key(self):
        """
        Packet 等价类的 hash key.
        相同 content 但不同 source markers → 不同 packet_key.
        """
        return (
            frozenset(self.content_sas),
            frozenset(m.kind for m in self.source_markers),
            frozenset(f.key for f in self.feeling_sas),
            # slot_context 不进 key(避免 packet 爆炸),作为软上下文
        )
```

### 50.3 SDPL 学习规则(替换 §2 共现的 packet-aware 版本)

```python
# === 原 §2 共现学习(v10) ===
# Δassoc(a, b) = η · co_attention(a, b)  # 只看内容共现

# === v13 SDPL 学习(packet-aware) ===
def sdpl_observe_packet(packet):
    """
    @op_count: O(|packet.content|^2 + |action_outcomes|), worst 500 ops/tick.
    
    所有学习按 packet key 累积,不按 content key.
    同 content 不同 source → 不同 packet → 不同关联表条目.
    """
    # 1. 共现学习按 packet 范围
    packet_key = packet.packet_key()
    for sa_a, sa_b in itertools.combinations(packet.content_sas, 2):
        # 在该 packet 类下累积 pairwise stats
        sparse_pairwise_graph.observe_under_packet_key(sa_a, sa_b, packet_key)
    
    # 2. lag-PMI 按 packet 范围
    for sa in packet.content_sas:
        temporal_graph.observe_under_packet_key(sa, packet_key, current_tick)
    
    # 3. 行动后果学习按 packet
    # 这是 SDPL 最关键之处:Q 值按 packet 学,不按 content 学
    if last_action_outcome.is_settled():
        Q_table.update(
            packet=packet,
            action=last_action,
            outcome=last_action_outcome.value,
            eligibility=compute_eligibility(packet, last_action),
        )
```

### 50.4 Packet 等价类的关键拟人意义

**例 1(用户哲学例 1)**:
- 真实看到火 → packet = `{content: vocab::火, source: PERCEIVED, feeling: reality_sense_high}`
- 想象到火 → packet = `{content: vocab::火, source: IMAGINED, feeling: imagination_sense_high}`
- **两 packet 独立 Q 表条目** → 学到不同的最优行动

**例 2(用户哲学例 2)**:
- 真实火 + 躲开 → 奖励 → `Q({火, PERCEIVED, 真实感}, 躲开)` ↑
- 想象火 + 躲开 → 违和/惩罚 → `Q({火, IMAGINED, 想象感}, 躲开)` ↓
- 想象火 + 检查 → 低风险 → `Q({火, IMAGINED, 想象感}, 检查)` ↑

**完美拟人**:看到火逃,想到火检查,**自然涌现**。

### 50.5 SDPL 红线

- ❌ 不许给 vocab SA 加 `is_real / is_imagined / is_remembered` 字段
- ❌ 不许在学习规则里 `if source == "IMAGINED": skip`(降权式硬规则)
- ❌ 不许预装"现实感"为内置 feeling spec 的固定权重(必须从 features 自适应涌现)
- ✅ 来源**全部以 marker SA 显式存在于 packet**
- ✅ packet_key 是 frozenset 组合,数学上明确,无歧义
- ✅ Q 表按 packet_key 索引,同 content 异 source 自然分化

---

## 51. Attention 凸组合门控(Codex B2 真修)

### 51.1 v12.1 公式的 bug

```
final = (1-share)·ext_w·s_ext + share·int_w·s_int + (ext_w+int_w)/2·max(0, s_ext-s_int)
```

第三项让 external 路径被双计,且不可微。

### 51.2 v13 凸组合版

```python
def compute_attention_score_v13(sa, current_pool, t):
    """
    @op_count: O(1) per SA.
    
    v13 真凸组合 + 外部 surprise 安全门.
    """
    w = load_constant("attention.s_attn_weights")
    
    # External s_attn(v10 完整保留)
    s_external = (
        w["beta_P_external"] * sa.P +
        w["beta_R"] * sa.R +
        w["beta_A"] * sa.A -
        w["beta_F"] * sa.F +
        w["beta_V"] * sa.V
    )
    
    # Internal s_attn(§44.2 内源链专用)
    s_internal = (
        w["beta_P_internal"] * max(0, sa.P) +
        w["beta_A_internal"] * sa.A -
        w["beta_F_internal"] * sa.F
    )
    
    # 来源占比(从 §52 gain 账本派生,严格数学)
    g = clamp(sa.endogenous_drive_share(), 0.0, 1.0)
    
    # 真凸组合(端点干净,可微)
    s_mixed = (1 - g) * s_external + g * s_internal
    
    # 外部 surprise 安全门(能量优先级)
    # 当外部 P 显著高时,external path 必须主导
    surprise_threshold = load_constant("attention.external_surprise_threshold")
    if sa.P_external_component > surprise_threshold:
        # 强制 external 主导,1-3 tick 内拉走焦点
        return s_external  # 完整 external,绕开 mix
    
    return s_mixed
```

**关键修复**:
- 真凸组合,`g=0` → 纯 external,`g=1` → 纯 internal,中间线性
- 处处可微
- 外部 surprise 安全门是**能量优先级阈值**,不是关键词规则
- 当沉浸想象时来强外部输入,**强制 external 路径 1-3 tick 内拉走焦点**

### 51.3 验收(Codex 提的安全门测试)

```python
def test_external_surprise_breaks_imagination_v13():
    boot()
    # 让系统进入沉浸想象 50 tick
    for _ in range(50):
        run_tick(no_external_input=True)
    assert is_in_endogenous_loop()
    
    # 注入高 surprise 外部输入
    inject_high_surprise_external_input(R=0.9, P=0.7)
    
    # 验收:1-3 tick 内焦点被拉走
    pulled_within_3_ticks = False
    for tick in range(3):
        run_tick()
        if attention_top_sa().is_external_input():
            pulled_within_3_ticks = True
            break
    assert pulled_within_3_ticks
    
    # 验收:surprise 衰减后,unfinished_pressure 可以拉回内源任务
    let_surprise_decay(N_ticks=20)
    for _ in range(50):
        run_tick(no_external_input=True)
    assert internal_task_back_in_focus()
```

---

## 52. Attention Gain 来源账本(Codex B3 真修)

### 52.1 v12.1 缺定义

`sa.compute_endogenous_drive_share()` 没数学定义。

### 52.2 v13 严格账本(继承 v11 yaml 化纪律)

```python
class AttentionGainLedger:
    """
    @op_count: O(1) per gain injection.
    
    每个 SA 维护 attention_gain 来源分项账本。
    不是永久身份字段(那会违反 v8 §11.3 marker SA 多态原则),
    而是 per-tick 累积,自然衰减。
    """
    
    def __init__(self):
        self.gain_by_source = {
            "external": 0.0,
            "feedback": 0.0,
            "unfinished_pressure": 0.0,
            "expectation_pressure": 0.0,
            "residual_mass": 0.0,
            "imagination": 0.0,
            "replay": 0.0,
            "user_directed": 0.0,  # 用户显式注意行动
        }
    
    def inject(self, source: str, amount: float):
        """注入时记录来源(必须在所有 gain 注入点调用)"""
        assert source in self.gain_by_source
        self.gain_by_source[source] += amount
    
    def step_decay(self):
        """与 attention_gain 同节奏衰减"""
        decay = load_constant("energy.A_decay")  # 沿用 v10 衰减率
        for k in self.gain_by_source:
            self.gain_by_source[k] *= decay
    
    def total(self):
        return sum(self.gain_by_source.values())
    
    def endogenous_share(self) -> float:
        """
        endogenous = unfinished + expectation + residual + imagination + replay
        endogenous_share = endogenous / total
        clamp 到 [0, 1]
        """
        endogenous = (
            self.gain_by_source["unfinished_pressure"] +
            self.gain_by_source["expectation_pressure"] +
            self.gain_by_source["residual_mass"] +
            self.gain_by_source["imagination"] +
            self.gain_by_source["replay"]
        )
        total = self.total()
        if total < 1e-9:
            return 0.0
        return clamp(endogenous / total, 0.0, 1.0)
```

### 52.3 § 44.4 三源驱动接入账本

```python
# §44.4 v13 修订:每注入 attention_gain 必经账本
def step_endogenous_drive_v13(state_pool, t):
    for sa in state_pool.active_sas():
        # Source 1
        unfinished = sa.short_term_memory.get_unfinished_pressure()
        delta_unfin_inject = load_constant("endogenous.delta_unfinished") * unfinished
        sa.gain_ledger.inject("unfinished_pressure", delta_unfin_inject)
        sa.attention_gain += delta_unfin_inject  # 标准 G_i 注入
        
        # Source 2
        expect_p = sa.get_expectation_pressure()
        delta_exp_inject = load_constant("endogenous.delta_expectation") * expect_p
        sa.gain_ledger.inject("expectation_pressure", delta_exp_inject)
        sa.attention_gain += delta_exp_inject
        
        # Source 3
        residual = residual_tracker.get(sa).unresolved_mass
        idle_boost = compute_idle_boost_sigmoid(idle_score(t))  # §44.4 v12.1 软门
        delta_res_inject = load_constant("endogenous.delta_residual") * residual * idle_boost
        sa.gain_ledger.inject("residual_mass", delta_res_inject)
        sa.attention_gain += delta_res_inject
```

**关键**:每个 G_i 注入点**必经 ledger.inject()**,无人能绕过。Phase 8.11 Web Mind 区可直接显示每 SA 的账本饼图,审计价值高。

---

## 53. real_evidence_cap vs memory_attention_support 拆分(Codex S1 真修)

### 53.1 v12.1 的冲突

v12.1 §44.3 要求想象激活时 target_cap → 0,但 §44.6 又要求 long_term intent 能影响行动。同一 cap 不能两用。

### 53.2 v13 真拆分

```python
class EnergyCaps:
    """
    @op_count: O(1).
    
    v13 拆双 cap.
    """
    
    def compute_real_evidence_cap(self, sa, t):
        """
        防止想象冒充真实外感.
        无 live 外感时 cap → 0,V 不能高到冒充 R.
        """
        if sa.has_live_external_evidence_this_tick():
            ruler = sa.real_energy
        else:
            ruler = sa.decayed_baseline  # 真 0 floor (v12 §44.3)
        return max(0.0, ruler * load_constant("composed_vocab.target_cap_ratio"))
    
    def compute_memory_attention_support(self, sa, t):
        """
        允许长时记忆/intent 在相关 cue 下进入注意力,
        即使无 live 外感.
        Long_term R 投射到 attention_gain,不投射到 real_energy.
        """
        if sa.is_in_long_term_layer():
            cue_relevance = compute_cue_alignment(sa, current_context_signature)
            support = sa.long_term_R * cue_relevance
            return support
        return 0.0
    
    def apply_caps(self, sa, t):
        # cap 1: V/R 不被想象抬高(real_evidence_cap)
        real_cap = self.compute_real_evidence_cap(sa, t)
        sa.virtual_energy = min(sa.virtual_energy, real_cap)
        # 注:不 cap real_energy,因为它由外感直接决定
        
        # support 2: 长时记忆能注入 attention_gain(memory_attention_support)
        memory_support = self.compute_memory_attention_support(sa, t)
        sa.gain_ledger.inject("replay", memory_support)
        sa.attention_gain += memory_support
```

**关键拟人**:
- "想到火"的 V 不会高到让系统**误认为真有火**(real_evidence_cap)
- 但"绕开修路"intent 第二天**可以进 attention 影响行动**(memory_attention_support)
- 二者在数学上**完全解耦**

### 53.3 红线

- ❌ 不许 real_evidence_cap 和 memory_attention_support 共用同一阈值
- ✅ 想象不能制造"我真的看见了"R,但可以制造"我想起了"A/G
- ✅ Web Mind 区分两层显示:reality channel vs imagination channel

---

## 54. 测试不偷用语义字串(Codex S2 真修)

### 54.1 v12 §44.6 验收的语义作弊风险

```python
# v12 错误版
assert chosen_action.relates_to("avoid")  # 偷用人类语义
```

### 54.2 v13 严格 action_id 验收

```python
def test_cross_session_deferred_intention_v13():
    """v13 严格版:断言 action_id / learned successor,不查中文"""
    
    # Session 1 准备:通过教学让系统学到 "修路场景 → 绕行动作" 关联
    boot_fresh()
    teaching_phase(
        scenario="construction_visual",
        action_label_id="ACTION_REROUTE_001",  # 系统内部 ID,非语义
        reward_signal=positive,
    )
    # 此时系统已学到 Q({construction_scene, PERCEIVED}, ACTION_REROUTE_001) > 0
    
    # 系统在 inner reasoning 中产生 intent
    for _ in range(K_inner):
        inject_endogenous_intent_via_continuous_imagination(
            content_sa_id="vocab::construction_scene_avoidance",  # 内部 ID
        )
    
    # 持久化
    persist_to_sqlite()
    session_close()
    
    # Session 2:视觉 cue
    boot_from_persistence()
    show_visual_input("construction_scene_image")  # 真实图像,不是语义注入
    
    for _ in range(N_recall_ticks):
        run_tick()
    
    # 严格验收:断言 action_id,不查中文/英文
    chosen_action_id = state_pool.commit_record.last_action_id
    assert chosen_action_id == "ACTION_REROUTE_001"
    # 验收 learned successor
    successor_active = state_pool.get_active_successor_for(
        "vocab::construction_scene_perception"
    )
    assert successor_active.id == "ACTION_REROUTE_001"
```

**红线**:
- ❌ 任何 `assert action.contains("avoid" or "绕开" or "reroute")` — 偷用语义
- ❌ 任何 `assert text.contains("...")` 作主断言 — 字串匹配
- ✅ 内部 ID 比较 / 学到 Q 表条目存在 / 行动响应正确性

---

## 55. Long_term Cold Index + Cue-Triggered Rehydration(Codex S3 真修)

### 55.1 v12.1 缺设计

"intent SA 进入 long_term layer 的活跃 SA 集" — 真长跑会让所有 long_term SA 都活跃,炸开 attention。

### 55.2 v13 双层 long_term

```yaml
# apv3_constants.yaml v13 新增
long_term:
  # 双层
  cold_index_capacity: 50000           # @experimental — SQLite 持久化容量
  active_pool_max_from_long: 200       # @experimental — 同时激活上限
  
  # cue-triggered rehydration
  rehydration_similarity_threshold: 0.4  # @experimental — context_signature 相似度门
  rehydration_top_k_per_tick: 5          # @experimental — 每 tick 至多激活
```

```python
class LongTermLayer:
    """
    @op_count: O(|cold_index| * 16) for rehydration scan; cached.
    
    v13 双层:cold index(SQLite 持久,海量)+ active pool(常驻 attention,上限).
    """
    
    def __init__(self):
        self.cold_index = SQLiteColdStore()  # 持久,可极大
        self.active_pool = OrderedDict()      # 当前 attention 中
        self.max_active = load_constant("long_term.active_pool_max_from_long")
    
    def rehydrate_by_cue(self, current_context_signature):
        """
        @op_count: O(|cold_index| * 16) per call,因 caching 多 tick 摊销.
        
        cue-triggered:context signature 相似 → 召回相关 cold SAs.
        """
        threshold = load_constant("long_term.rehydration_similarity_threshold")
        top_k = load_constant("long_term.rehydration_top_k_per_tick")
        
        # 用 v11 context_signature_v10 Jaccard + z-norm
        candidates = self.cold_index.find_top_k_by_signature(
            current_context_signature, k=top_k * 3
        )
        rehydrated = 0
        for cold_sa, sim_score in candidates:
            if sim_score < threshold:
                break
            if rehydrated >= top_k:
                break
            self._activate(cold_sa)
            rehydrated += 1
        
        # 若 active_pool 超 max,LRU 淘汰回 cold
        while len(self.active_pool) > self.max_active:
            evicted_id, evicted_sa = self.active_pool.popitem(last=False)
            self.cold_index.store(evicted_sa)
    
    def _activate(self, cold_sa):
        """从 cold 移到 active,初始 R 由 cue 相关度决定"""
        cold_sa.R = cold_sa.long_term_R * cue_alignment_factor
        cold_sa.gain_ledger.inject("replay", small_seed_gain)
        self.active_pool[cold_sa.persistent_id] = cold_sa
    
    def session_boot(self):
        """开机:active_pool 空,仅 cold_index 重建"""
        self.cold_index.warm_load_from_sqlite()
        # active_pool 不预填!
        # 等待 §44.4 内源驱动或外感输入触发 rehydrate
```

### 55.3 跨 session 延迟意图新通路(v13)

```python
# Session 1 结束时
# - intent SA 在 active_pool
# - persist 时:active_pool 不清空,但 mark 为"待 cold 化"
# - boot 时:cold_index 全量,active_pool 空

# Session 2 boot
boot_from_persistence()
# active_pool = {} (空!不是 v12.1 错误版的"全活跃")
# cold_index 含 "绕开修路" intent

# t=0: 视觉感受"修路场景" → percept SA 进 active_pool
# t=1: percept 触发 context_signature 更新
# t=2: long_term.rehydrate_by_cue() 用新 context 找 cold candidates
#      → "绕开修路" intent 在 cold_index 中 cue match → 激活进 active_pool
# t=3: 标准 attention selector 看到 active intent SA
# t=4: action competition 选择对应行动
```

**关键拟人**:
- 不会"开机什么都想起来"(防爆炸)
- "看到修路才想起绕行"(cue-driven,自然拟人)
- cold_index 容量极大(可存数千 SA),active_pool 严格上限

### 55.4 验收

```python
def test_long_term_no_explosion_v13():
    boot_fresh()
    # 模拟跑 1000 session,每次产生 50 个 long_term SA
    for s in range(1000):
        simulate_session_with_50_long_term_promotions()
        persist_and_reboot()
    
    # 现在 cold_index 有 50000 SA
    assert long_term_layer.cold_index.size() == 50000
    # 但 active_pool 应严格 < max
    assert len(long_term_layer.active_pool) <= load_constant("long_term.active_pool_max_from_long")
    
    # attention top-K 应大部分是 active,而非 cold
    top_attention_sas = state_pool.top_n_by_attention(20)
    assert all(sa.id in long_term_layer.active_pool or sa.is_short_term() 
               for sa in top_attention_sas)
```

---

## 56. 现实感 / 想象感 等综合 cognitive_feeling(用户哲学第二轮)

### 56.1 用户原话

> "想象本身这个信号,也是有认知范式的,经过长期的学习,人类和 ap 应该都可以区分哪些属于想象,哪些是真实发生的,这种泛化判断能力也是有的,我们可以基于认知感受信号来进行判断"

### 56.2 v13 新 cognitive_feeling spec(沿用 v2.1 CognitiveFeelingFactory)

```yaml
# config/cognitive_feelings_v13.yaml(扩 v6 §16.4)

feeling::reality_sense:
  positive_features:
    - external_R_recent_high: 0.3
    - multimodal_consistency_high: 0.25
    - temporal_continuity_high: 0.20
    - action_verifiability_high: 0.15
    - others_feedback_consistent: 0.10
  negative_features:
    - endogenous_share_high: 0.30
    - IMAGINED_marker_present: 0.25
    - INFERRED_marker_present: 0.15
    - counterfactual_conflict: 0.30
  gain: 1.0

feeling::imagination_sense:
  positive_features:
    - endogenous_share_high: 0.30
    - V_A_inertia_high: 0.25
    - no_live_external_R: 0.20
    - IMAGINED_marker_present: 0.25
  negative_features:
    - external_R_recent_high: 0.30
    - multimodal_consistency_high: 0.20

feeling::hearsay_sense:
  positive_features:
    - HEARSAY_marker_present: 0.40
    - source_entity_speaker_present: 0.30
    - text_input_recent_high: 0.30

feeling::guess_sense:
  positive_features:
    - INFERRED_marker_present: 0.35
    - low_grasp_score: 0.25
    - candidate_entropy_high: 0.40

feeling::incongruity:
  positive_features:
    - prediction_mismatch_ratio_high: 0.40
    - cognitive_pressure_high: 0.30
    - reality_sense_high_but_unexpected: 0.30
```

**关键**:
- 全部经标准 `CognitiveFeelingFactory` 工厂,**无新模块**
- features 来自既有 ledger / marker / energy field
- **自适应涌现**:经长期学习 + tuner 调权重,feeling 准确度自然提升
- **拟人对称**:reality_sense 高时直接断言;guess_sense 高时"可能...";hearsay_sense 高时"听说..."

### 56.3 想象→惩罚 vs 真实→奖励 学习自动分化(SDPL 验证)

由 SDPL §50 + 这些 feelings,**自然涌现**:

```python
# 想象火 + 躲开 → 用户/环境给违和反馈
# packet_imagined = {火, IMAGINED marker, imagination_sense_high, ...}
# Q(packet_imagined, 躲开) ← outcome=负 → 该 packet 下"躲开"降权

# 真实火 + 躲开 → 奖励
# packet_real = {火, PERCEIVED marker, reality_sense_high, ...}
# Q(packet_real, 躲开) ← outcome=正 → 不变/上升

# 自然涌现:看到火逃,想到火检查
```

**完全 emerge from**:既有 Q 学习 + packet key 分化 + 新 feeling spec。**无新公式形态**。

### 56.4 表达层拟人(用户原话:"好像...""可能...")

```python
# §16.9 草稿行动竞争升级:候选 action 包含表达模板
# 模板选择由 feeling_set 自然偏置(经 ActionParameterMemory)

# 例:reality_sense_high → "是的""我看到了"
# imagination_sense_high → "好像""我觉得"
# guess_sense_high → "可能""说不准"
# incongruity_high → "奇怪""不对劲"

# 这不是 if-then 模板路由,而是 ActionParameterMemory 学到的
# Q(speech_template_id | packet_with_feelings) 分布
```

**红线**:不许硬编码 `if reality_sense > 0.7: say "是的"`。**完全经 ActionParameterMemory 学**(经 v8 §16.9 Thompson sampling 路径)。

---

## 57. 想象 vs 真实在拟人犯错中的稳态自适应(用户第一轮哲学)

### 57.1 用户原话

> "需要一个数学模型,或者通过自适应调参器进行稳态的自适应变化,保证它在各个不同的环境中,都可以自适应并趋近于一个能保证效果正常的稳态"

### 57.2 v13 自适应稳态机制

**核心洞察**:不调 `w_img` 总权重,而是让 SDPL §50 + ledger §52 + feelings §56 协同**自然涌现稳态**:

- 想象主导的 packet 反复被惩罚 → Q 值降 → 那种 packet 下不再触发风险行动 → 减少错误
- 但 packet 之间共享内容 SA → 想象学习仍提升 vocab 关联(用户哲学第一例:想象促进学习)
- 在游戏/角色扮演场景:imagination_sense_high 不带惩罚 → 该 packet 下行动正常 → 拟人式沉浸
- 在事实问答/危险场景:imagination_sense_high + 错误后果 → 该 packet 下行动慎重 → 拟人式严谨

**全部经 AdaptiveTuner**(v10 既有)**自然演化**:

```python
# AdaptiveTuner 已 own:
# - attention.threshold_adjustment
# - memory.prediction_gain_multiplier
# - action.threshold_adjustment
# - learning.rate_multiplier

# v13 不引入"imagination_weight" tuner param.
# imagination 影响完全 emerge from:
# 1. EpistemicSource marker 区分 packet(§50)
# 2. ledger 区分能量源(§52)
# 3. caps 区分 real vs memory support(§53)
# 4. feelings 综合判断现实感/想象感(§56)
# 5. Q 学习按 packet 分化后果(§50.3)

# 稳态 = 5 个机制协同的能量+学习平衡点
# 不同环境(scenario_profile)经 AdaptiveTuner 自然趋向不同稳态
```

**用户哲学完美实现**:不预装"想象权重",不分支"想象 vs 真实",**让系统在不同环境中自然学到合适的现实感分配**。

---

## 58. v13 Phase 嫁接

### 58.1 Phase 顺序最终版(v10 + v11 + v12 + v12.1 + v13)

```
Phase 8.2   连续 tick + sensor adapter
Phase 8.3   audit_db + §44.3 target_cap 0-floor
            + §52 AttentionGainLedger 接入
            + §53 EnergyCaps 双 cap 实施
Phase 8.4   ComposedVocab + cold-fork ΔP
            + §50 SDPL: 共现学习按 packet key
Phase 8.5   CFS 4 通道(v6 既有)+ §49 complexity/simplicity
            + §56 新 feelings: reality_sense / imagination_sense /
              hearsay_sense / guess_sense / incongruity
Phase 8.6   视觉感受 + §50 PERCEIVED marker 自动 spawn
Phase 8.7   视焦点 + §47 三类注意力(沿用 v12)
Phase 8.8   黄苹果泛化
Phase 8.9   自然纠错 + §50 SDPL: 行动学习按 packet
Phase 8.10  §44 持续内源 + §51 凸组合 attention
            + §50 IMAGINED marker auto-spawn on internal chain SAs
            + §44 mini-gate(v12.1)+ §51.3 surprise 安全门 gate
Phase 8.11  Web 工作台 + §52 ledger 饼图 + §56 feelings 显示
Phase 8.12  fast mapping + shape bias + epistemic drive
            + §50 HEARSAY marker auto-spawn on teacher text
Phase 8.13  音频
Phase 8.14  Phase 8 端到端 + SDPL 拟人验收套件(§57.3)
Phase 8.15  §55 long_term cold + active 双层
            + short→long 显式 phase
Phase 8.16  跨 session 延迟意图(无 sleep 依赖)+ rehydration 测试
Phase 8.17  自传式回忆 + REMEMBERED marker

—— Phase 8 完成 = 18-30 月龄 + 持续想象 + 跨天意图 + 来源监控 ——

Phase 9.X 沿用 backlog
```

### 58.2 SDPL 拟人验收套件(Phase 8.14)

```python
def test_imagination_promotes_learning():
    """用户哲学例 1:想象促进学习"""
    boot_fresh()
    # Group A:只外感样本
    train_with_external_only(N=50)
    perf_A = test_recall_accuracy()
    
    boot_fresh()
    # Group B:外感 + 内源想象增强
    train_with_external_plus_imagination(N=50)
    perf_B = test_recall_accuracy()
    
    # B 应显著优于 A
    assert perf_B > perf_A * 1.1

def test_humanlike_misjudgment_then_correction():
    """用户哲学例 2:人类式误判 → 后果学会"""
    boot_fresh()
    # 学到 "火" vocab + 真实场景下"躲开"高 Q
    teach_real_fire_avoidance(N=20)
    
    # 引发想象火
    inject_imagination_chain_ending_in_fire()
    
    # 行动可能选"躲开"(同 content 关联)
    action_taken = run_until_commit()
    
    if action_taken.id == "ACTION_AVOID_001":
        # 注入违和反馈(想象躲开无意义)
        give_negative_feedback("incongruous_action")
    
    # 再次想象火
    inject_imagination_chain_ending_in_fire()
    action_taken_2 = run_until_commit()
    
    # 第二次应转向"检查/确认"而非"躲开"
    assert action_taken_2.id in ["ACTION_CHECK_001", "ACTION_VERIFY_001", "ACTION_NOOP"]
    
    # 但真实火场景下"躲开"Q 不应被毁
    show_real_fire()
    action_real = run_until_commit()
    assert action_real.id == "ACTION_AVOID_001"

def test_no_immersion_in_imagination():
    """用户哲学例 3:不沉迷幻想"""
    boot()
    enter_endogenous_loop_50_ticks()
    
    # 外部 surprise 注入
    inject_high_surprise_external_input()
    
    # 1-3 tick 内被拉走
    assert focus_pulled_to_external_within_3_ticks()
    
    # 但内源 unfinished 仍在 ledger 中
    # 外部退去后能回来
    let_external_decay()
    run_idle_50_ticks()
    assert internal_task_back_in_focus()

def test_source_monitoring_emerges():
    """用户哲学例 4:认知感受范式自然涌现"""
    # 长期混合训练后,reality_sense / imagination_sense 应有区分
    train_mixed_real_and_imagined(N=200)
    
    # 测试:真实事件应触发 reality_sense_high
    inject_real_perception("apple")
    assert state_pool.feeling("reality_sense").value > 0.6
    assert state_pool.feeling("imagination_sense").value < 0.4
    
    # 想象事件应触发 imagination_sense_high
    inject_imagined_chain("apple")
    assert state_pool.feeling("imagination_sense").value > 0.6
    assert state_pool.feeling("reality_sense").value < 0.4
```

---

## 59. v13 给 Codex 的最终指令

1. **v10 主 + v11 patches + v12 + v12.1 + v13 = 5 件套**
2. **§50 SDPL 是 Phase 8.4 起所有学习的底层升级** — 共现/Q 学习全部按 packet
3. **§52 AttentionGainLedger 在 Phase 8.3 接入** — 所有 G_i 注入必经 ledger
4. **§53 双 cap 在 Phase 8.3 实施** — real_evidence_cap vs memory_attention_support 严格拆
5. **§55 long_term 双层在 Phase 8.15** — 不许"全活跃"开机
6. **§56 5 个新 feelings 在 Phase 8.5** — 不预装权重,经 features 自适应
7. **§50.5 红线扫描** — `grep "if .*epistemic_source\s*==" runtime/cognitive/` 必须 0 命中
8. **§54 测试断言只能用内部 ID** — 不许中文/英文字串匹配
9. **Phase 8.14 SDPL 拟人验收 4 个 gate 必跑**

---

## 60. v13 哲学完美 — 与用户思路最终对齐

| 用户哲学 | v13 落点 |
|---|---|
| "不是准确的机器,而是要拟人" | SDPL §50 允许想象犯错,通过后果学会分寸 |
| "想象当成事实进行直觉性推理" | §50 packet 学习,想象 packet 下也有 Q 值 |
| "不能太过分,需要自适应稳态" | §57 五个机制协同自然趋稳,AdaptiveTuner 演化 |
| "真实和想象信号本身是可区分的" | §50 EpistemicSource marker 5 种;§56 feelings |
| "想象的内容和真实发生的事情作为两件事导致不同后果" | §50.3 Q 表按 packet key,不按 content key |
| "想象本身的信号也有认知范式" | §56 imagination_sense / reality_sense 等 feelings 自适应涌现 |
| "经过长期学习区分泛化判断能力" | §56 features 自适应权重 + AdaptiveTuner |
| "Source-Differentiated Packet Learning(用户命名)" | §50 v13 正式命名为 AP 第一原则 |

### 普适性确认

SDPL 不只解决"想象 vs 真实",同样解决:
- 听别人说 vs 自己看到(HEARSAY vs PERCEIVED packet)
- 过去回忆 vs 现在感受(REMEMBERED vs PERCEIVED packet)
- 推理猜测 vs 实证确定(INFERRED vs PERCEIVED packet)
- 教师讲授 vs 自主推断(HEARSAY+trust_high vs INFERRED packet)

**全部统一**。

---

## 61. 整体最终判断

**v13 是底层哲学升级,不是 errata**。它把"想象 vs 真实"扩展为"任意来源 vs 任意来源"的统一原则,并完整数学化为 SDPL。

**v10 + v11 + v12 + v12.1 + v13 五件套** = APV3 完整设计基础。

设计层至此真正收尾 — Codex 拿五件套立即开 Phase 8.2。后续 minor issue 在 Phase 实施中 PR 修补。

---

— 接手线程,2026-06-17
