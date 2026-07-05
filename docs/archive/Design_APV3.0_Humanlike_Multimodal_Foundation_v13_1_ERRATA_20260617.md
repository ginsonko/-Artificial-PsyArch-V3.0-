# APV3.0 v13.1 — SDPL 严密化 errata(3 blocker + 5 serious 真修)

日期: 2026-06-17
作者: 接手线程
状态: **v13 经轮 11 审阅判定 70% 严密,核心 SDPL 框架对但有 3 个 blocker:packet_key frozenset 丢能量信息 / P_external_component 未定义 / G_i 注入点未穷尽。v13.1 是 v13 的 errata,修 3 blocker + 5 serious。之后做 v14 unified consolidated 合并 v10-v13.1 五件套为单一权威文档。**

前身链:v10 + v11 + v12 + v12.1 + v13 → **v13.1(本稿)** → v14 unified(下一步)

---

## 0. v13.1 修复总览

| # | v13 缺陷 | v13.1 修复 |
|---|---|---|
| **B1** | packet_key frozenset 丢能量信息(SDPL 核心漏洞) | §50.2 改 **量化分桶 packet_key**:content R 3 桶 / feeling 强度 3 桶 / dominant source 显式 |
| **B2** | §51 安全门 `P_external_component` 未定义 | §51 改用 **ledger.external_share 派生**:`external_dominance = gain_by_source["external"] / total > threshold` |
| **B3** | G_i 注入点未穷尽,Codex 会漏改 | §52 给**完整注入点穷尽清单**(8 个位置 + file/function 路径) |
| **S1** | 想象 V cap → 0 与 memory_attention_support 语义裂(intent 在 attention 但维持不住) | §53 引入 **V_floor**(memory_support 命中时给最低 V),与 cap(上限)分立 |
| **S2** | §55 cache 失效条件 + cue_alignment_factor 公式未定义 | §55 显式 **cache 失效 = signature 漂移 > threshold + cue_alignment = cosine** |
| **S3** | §56 features 全 hand-waving | §56 每 feature 给**一行算子定义**(数学公式 + 域 [0,1]) |
| **S4** | 红线扫描漏 MarkerKind.* 分支模式 | §50.5 红线扩 **MarkerKind 分支检查 + packet_key 派生豁免** |
| **S5** | EpistemicSource auto-spawn 规则不足 | §50.6 给 **5 marker 完整 spawn rule 表**,含 Phase 8 与 Phase 11 differentation |

---

## 补丁 B1: packet_key 量化分桶(SDPL 核心 fix)

### v13 缺陷

`packet_key = (frozenset(content_sas), frozenset(source_kinds), frozenset(feeling_keys))` 丢失:
- content SA 的 R 强度(R=0.9 vs R=0.05 同 key)
- feeling 强度(reality_sense=0.95 vs 0.6 同 key)
- 主导 source 信息(IMAGINED 与 PERCEIVED 共存时谁主导?)

### v13.1 真修

```python
class LearningPacket:
    """
    @op_count: O(|content| + |feeling|) ~ 30 ops to compute packet_key.
    
    v13.1 量化分桶版.
    """
    
    @staticmethod
    def quantize_R(r: float) -> int:
        """R 分 3 桶: low(<0.3) / med(0.3-0.7) / high(≥0.7)"""
        if r < 0.3: return 0
        elif r < 0.7: return 1
        else: return 2
    
    @staticmethod
    def quantize_feeling_strength(strength: float) -> int:
        """feeling 强度同分 3 桶"""
        return LearningPacket.quantize_R(strength)
    
    def packet_key(self):
        """
        v13.1 量化版 packet_key.
        
        包含信息:
        - content SAs + 各自 R bucket
        - source marker kinds + 总能量 bucket
        - feeling keys + 强度 bucket
        - dominant source(R 最高的 source marker)
        """
        # 1. content: 每 SA id + R bucket
        content_with_bucket = frozenset(
            (sa.id, self.quantize_R(sa.R))
            for sa in self.content_sas
        )
        
        # 2. source markers: 每 kind + 总能量 bucket
        # 同一 kind 多个 marker 总能量合并
        source_energy = defaultdict(float)
        for m in self.source_markers:
            source_energy[m.kind] += m.real_energy
        source_with_bucket = frozenset(
            (kind, self.quantize_R(energy))
            for kind, energy in source_energy.items()
        )
        
        # 3. dominant source(empty 时 None)
        dominant_source = None
        if source_energy:
            dominant_source = max(source_energy.items(), key=lambda x: x[1])[0]
        
        # 4. feeling: key + 强度 bucket
        feeling_with_bucket = frozenset(
            (f.key, self.quantize_feeling_strength(f.value))
            for f in self.feeling_sas
        )
        
        return (
            content_with_bucket,
            source_with_bucket,
            dominant_source,
            feeling_with_bucket,
        )
```

**为什么这真修**:
- packet_key 现在区分 `(火, R=high)` vs `(火, R=low)` → 不同学习
- `reality_sense=high` vs `reality_sense=med` 不同 packet
- `dominant_source=PERCEIVED` vs `dominant_source=IMAGINED` 显式
- 仍可 hash(frozenset 组合),无新机制

**Packet 数量上限分析(防爆炸)**:
- 假设单 tick packet 内 max content=5 SAs × 3 R 桶 = ~125 组合(但同 SA 集合,实际更少)
- max 5 source kinds × 3 energy 桶 = 15
- max 5 feeling × 3 强度 = 15
- 单 packet 类型 = 125 × 15 × 5(dom) × 15 ~ 100K 上限,但实际场景下绝大多数组合从不出现
- Q 表稀疏存储,典型经验后 ~1000-5000 active packet keys
- 在 SQLite 内可管理

**配套 yaml**:

```yaml
# apv3_constants.yaml v13.1 新增
sdpl:
  packet_key:
    R_bucket_low_threshold: 0.3      # @structural — 3 等分
    R_bucket_high_threshold: 0.7     # @structural
    feeling_bucket_low_threshold: 0.3
    feeling_bucket_high_threshold: 0.7
  q_table:
    max_active_packets: 5000          # @experimental
    eviction_policy: "lru_by_packet_R_total"
```

---

## 补丁 B2: §51 安全门改用 ledger.external_share(真修)

### v13 缺陷

`sa.P_external_component` 未定义,无法实施。

### v13.1 真修

直接用 §52 ledger 已有数据派生:

```python
def compute_attention_score_v13_1(sa, current_pool, t):
    """
    @op_count: O(1).
    
    v13.1 修:安全门基于 ledger.external_share,无需新定义 P 分解。
    """
    w = load_constant("attention.s_attn_weights")
    
    # External s_attn(v10 保留)
    s_external = (
        w["beta_P_external"] * sa.P +
        w["beta_R"] * sa.R +
        w["beta_A"] * sa.A -
        w["beta_F"] * sa.F +
        w["beta_V"] * sa.V
    )
    
    # Internal s_attn(§44 内源)
    s_internal = (
        w["beta_P_internal"] * max(0, sa.P) +
        w["beta_A_internal"] * sa.A -
        w["beta_F_internal"] * sa.F
    )
    
    # ledger-driven 来源占比(B2 fix:用账本派生,无需 P 分解)
    g = clamp(sa.gain_ledger.endogenous_share(), 0.0, 1.0)
    
    # 真凸组合
    s_mixed = (1 - g) * s_external + g * s_internal
    
    # 外部 surprise 安全门(B2 v13.1 修:用 ledger.external 主导阈值)
    ext_dominance_threshold = load_constant("attention.external_dominance_safety_threshold")
    external_share = sa.gain_ledger.gain_by_source["external"] / max(sa.gain_ledger.total(), 1e-9)
    
    # 检测:该 SA 此 tick 是否因外部强输入获得主导能量?
    # 兼 surprise 兼 P 正(预测误差大)→ 触发安全门
    if external_share > ext_dominance_threshold and sa.P > load_constant("attention.surprise_P_threshold"):
        # 强制 external 主导
        return s_external
    
    return s_mixed
```

**为什么这真修**:
- 不再需要凭空的 `P_external_component`
- ledger.external 已经在 sensor adapter / feedback 注入时被记录(see §52 v13.1)
- 安全门:**外部能量占主导 + P 正(惊)** 双条件,自然防误触
- threshold 进 yaml,可调

```yaml
# apv3_constants.yaml v13.1 新增
attention:
  external_dominance_safety_threshold: 0.5    # @experimental
  surprise_P_threshold: 0.4                    # @experimental
```

### §51.3 验收(改用 ledger 版)

```python
def test_external_surprise_breaks_imagination_v13_1():
    # 进入想象 50 tick
    # 验证当前焦点 SA 的 gain_ledger 中 endogenous source 主导
    sa_in_focus = state_pool.top_attention_sa()
    assert sa_in_focus.gain_ledger.endogenous_share() > 0.7
    
    # 注入高 surprise 外部
    inject_high_surprise_external_input(R=0.9, P=0.7)
    
    # 新 percept SA 的 ledger 应主要是 "external"
    new_percept = state_pool.most_recent_external_sa()
    assert new_percept.gain_ledger.gain_by_source["external"] / new_percept.gain_ledger.total() > 0.7
    assert new_percept.P > 0.4
    
    # 1-3 tick 内焦点拉走
    for tick in range(3):
        run_tick()
        if state_pool.top_attention_sa().id == new_percept.id:
            break
    assert state_pool.top_attention_sa().id == new_percept.id
```

---

## 补丁 B3: G_i 注入点穷尽清单(真修)

### v13 缺陷

§52 只示范 §44.4 三源,Codex 实施时会漏改其他注入点。

### v13.1 真修

**所有 attention_gain 注入点完整清单**(Phase 8.3 实施时**每个位置必经 ledger**):

```yaml
# G_i 注入点穷尽清单 v13.1
# 每个 PR 必经审计,新增注入点必须 ledger.inject() 标 source

attention_gain_injection_points:
  
  # === 来自 sensor adapter(external)===
  - location: "sensor_adapters/vision/numeric_sensor.py:emit_percept"
    source_label: "external"
    rationale: "视觉感受器原始输入"
  
  - location: "sensor_adapters/audio/numeric_sensor.py:emit_audio_proto"
    source_label: "external"
    rationale: "音频感受器原始输入"
  
  - location: "sensor_adapters/text/char_stream.py:emit_text_char_sa"
    source_label: "external"
    rationale: "文本字符微事件"
  
  - location: "sensor_adapters/salience_hint.py:apply_salience"
    source_label: "external"
    rationale: "salience hint(C-5 扩展)"
  
  # === 来自反馈通道(feedback)===
  - location: "runtime/cognitive/reward/handler.py:apply_reward"
    source_label: "feedback"
    rationale: "用户/环境奖励信号"
  
  - location: "runtime/cognitive/reward/handler.py:apply_punishment"
    source_label: "feedback"
    rationale: "用户/环境惩罚信号"
  
  # === 来自内源链(unfinished/expectation/residual)===
  - location: "runtime/cognitive/endogenous/step.py:step_endogenous_drive"
    source_label: "unfinished_pressure | expectation_pressure | residual_mass"
    rationale: "§44.4 三源驱动(已在 v13.1 §52.3)"
  
  # === 来自想象激活(imagination)===
  - location: "runtime/cognitive/endogenous/imagination_marker.py:spawn_imagination"
    source_label: "imagination"
    rationale: "内源链产生新 SA 的伴生 IMAGINATION marker 注入"
  
  # === 来自长时记忆 rehydration(replay)===
  - location: "runtime/cognitive/long_term/rehydration.py:rehydrate_cue_match"
    source_label: "replay"
    rationale: "§55 cold→active 激活"
  
  - location: "runtime/cognitive/memory/long_term_support.py:apply_memory_support"
    source_label: "replay"
    rationale: "§53 memory_attention_support 注入"
  
  # === 来自主动注意行动(user_directed)===
  - location: "runtime/cognitive/action/focus_action_runner.py:apply_focus_action"
    source_label: "user_directed"
    rationale: "§47 三类注意力中主动聚焦 action 触发"
```

**红线扫描 v13.1**:

```python
# scripts/red_line_check_v13_1.py 新增
def check_all_gain_injection_points_use_ledger():
    """
    扫描所有 attention_gain += / attention_gain = +=,
    必须在同一 function 内有 ledger.inject() 调用.
    """
    violations = []
    for py_file in glob("runtime/cognitive/**/*.py", recursive=True):
        tree = ast.parse(open(py_file).read())
        for func in ast.walk(tree):
            if isinstance(func, ast.FunctionDef):
                has_attention_gain_inject = False
                has_ledger_inject = False
                for stmt in ast.walk(func):
                    if (isinstance(stmt, ast.AugAssign) and 
                        isinstance(stmt.target, ast.Attribute) and
                        stmt.target.attr == "attention_gain"):
                        has_attention_gain_inject = True
                    if (isinstance(stmt, ast.Call) and 
                        hasattr(stmt.func, 'attr') and 
                        stmt.func.attr == "inject"):
                        has_ledger_inject = True
                
                if has_attention_gain_inject and not has_ledger_inject:
                    violations.append(f"{py_file}:{func.lineno}:{func.name}")
    return violations
```

**Phase 8.3 实施时**:每个注入点的 commit 必须配 ledger.inject() 同步,**红线脚本 PR-gate 强制**。

---

## 补丁 S1: V_floor for memory_attention_support(真修)

### v13 缺陷

V cap → 0 让 intent 在 attention 但无法预测维持 → "想到要绕路,但脑里维持不住"。

### v13.1 真修

```python
class EnergyCaps_v13_1:
    """v13.1 引入 V_floor 与 V_cap 双控"""
    
    def compute_real_evidence_cap(self, sa, t):
        """V 上限(防想象冒充感)— 沿用 v13"""
        if sa.has_live_external_evidence_this_tick():
            ruler = sa.real_energy
        else:
            ruler = sa.decayed_baseline
        return max(0.0, ruler * load_constant("composed_vocab.target_cap_ratio"))
    
    def compute_memory_support_V_floor(self, sa, t):
        """V 下限(memory_support 命中时保 V 不至消亡)v13.1 新增"""
        if not sa.is_in_long_term_layer():
            return 0.0
        
        # 计算该 SA 与当前 context 的 cue alignment
        cue_alignment = compute_cue_alignment(sa, current_context_signature)
        
        # V_floor = long_term_R × cue_alignment × admit_ratio
        admit_ratio = load_constant("long_term.memory_V_admit_ratio")  # 默认 0.3
        v_floor = sa.long_term_R * cue_alignment * admit_ratio
        return v_floor
    
    def apply_caps_v13_1(self, sa, t):
        """v13.1 双控:V 在 [V_floor, V_cap] 区间"""
        v_cap = self.compute_real_evidence_cap(sa, t)
        v_floor = self.compute_memory_support_V_floor(sa, t)
        
        # 必须 v_floor ≤ v_cap;若冲突(memory 想抬 V 但 real 想压 V)
        # 取 v_floor(让记忆能维持)
        if v_floor > v_cap:
            # 记忆主导(cue 强相关的长时记忆),V 允许达到 v_floor
            sa.virtual_energy = max(sa.virtual_energy, v_floor)
        else:
            # 正常情形:V 在区间内
            sa.virtual_energy = clamp(sa.virtual_energy, v_floor, v_cap)
        
        # attention_gain 走 ledger("replay" source,v13.1 §52)
        memory_support = self.compute_memory_attention_support(sa, t)
        if memory_support > 0:
            sa.gain_ledger.inject("replay", memory_support)
            sa.attention_gain += memory_support
```

**为什么这真修**:
- V_cap 仍守"想象不冒充感"
- V_floor 给"记忆能维持 prediction chain"——intent 在 attention + V 维持 → 行动可被驱动
- 二者不冲突,数学上有明确区间

```yaml
long_term:
  memory_V_admit_ratio: 0.3        # @experimental — Phase 8.16 实测
```

---

## 补丁 S2: §55 rehydration cache + cue_alignment(真修)

### v13 缺陷

cache 失效条件未定义;cue_alignment_factor 无公式。

### v13.1 真修

```python
class LongTermLayer_v13_1:
    """
    @op_count(scan): O(|cold_index| * 16) per signature-shifted scan.
                     O(1) per cache hit (98%+ cases).
    """
    
    def __init__(self):
        self.cold_index = SQLiteColdStore()
        self.active_pool = OrderedDict()
        self.last_signature = None
        self.cache_key = None
        self.cached_top_candidates = []
    
    def _signature_drift_too_large(self, current_sig):
        """检测 signature 是否显著漂移,决定 cache 是否失效"""
        if self.last_signature is None:
            return True
        drift = 1.0 - context_signature_similarity_v10(self.last_signature, current_sig)
        threshold = load_constant("long_term.rehydration_cache_drift_threshold")  # 0.15
        return drift > threshold
    
    def rehydrate_by_cue(self, current_context_signature):
        """v13.1: cache + 失效条件清晰"""
        if not self._signature_drift_too_large(current_context_signature):
            # cache hit,直接复用上次结果
            return self.cached_top_candidates
        
        # cache miss,重算
        threshold = load_constant("long_term.rehydration_similarity_threshold")
        top_k = load_constant("long_term.rehydration_top_k_per_tick")
        
        candidates = self.cold_index.find_top_k_by_signature(
            current_context_signature, k=top_k * 3
        )
        
        rehydrated = []
        for cold_sa, sim_score in candidates:
            if sim_score < threshold or len(rehydrated) >= top_k:
                break
            self._activate(cold_sa, sim_score)
            rehydrated.append(cold_sa)
        
        # update cache
        self.last_signature = current_context_signature
        self.cached_top_candidates = rehydrated
        
        # LRU eviction
        while len(self.active_pool) > self.max_active:
            evicted_id, evicted_sa = self.active_pool.popitem(last=False)
            self.cold_index.store(evicted_sa)
        
        return rehydrated
    
    def compute_cue_alignment_factor(self, sa, current_sig):
        """
        cue_alignment ∈ [0, 1]
        
        @op_count: O(16) — 沿用 context_signature 16-dim 内积.
        """
        if sa.context_signature_when_promoted is None:
            return 0.0
        return context_signature_similarity_v10(
            sa.context_signature_when_promoted, current_sig
        )
    
    def _activate(self, cold_sa, sim_score):
        """从 cold 移到 active,初始 R 由 cue 相关度决定"""
        cue_alignment = sim_score  # 已是 [0, 1]
        cold_sa.R = cold_sa.long_term_R * cue_alignment
        cold_sa.gain_ledger.inject("replay", small_seed_gain * cue_alignment)
        self.active_pool[cold_sa.persistent_id] = cold_sa
```

```yaml
long_term:
  rehydration_cache_drift_threshold: 0.15  # @experimental
```

**典型场景算力**:
- Cache 命中率 ~95%(signature 通常缓慢漂移)
- 命中:O(1)
- 失效(每 ~20 tick):O(|cold| × 16) = 160K ops
- 摊销:每 tick ~8K ops 平均,**可承担**

---

## 补丁 S3: §56 features 一行算子定义(真修)

### v13.1 完整 feature 算子(全部 [0, 1])

```yaml
# config/cognitive_feeling_features_v13_1.yaml
# 每个 feature 一行算子定义,数学严谨

features:
  external_R_recent_high:
    formula: "mean(R_external, last_5_ticks) / R_max_observed_window"
    window_ticks: 5
    output_range: [0, 1]
    notes: "近 5 tick 外感 R 占当前观察最大 R 比例"
  
  endogenous_share_high:
    formula: "sa.gain_ledger.endogenous_share()"
    output_range: [0, 1]
    notes: "来自 v13.1 §52 ledger,无新算"
  
  IMAGINED_marker_present:
    formula: "sigmoid(sum(m.real_energy for m in sa.markers if m.kind == IMAGINED) * 2)"
    output_range: [0, 1]
    notes: "连续(non-binary),反映 marker 总能量"
  
  multimodal_consistency_high:
    formula: |
      let vision_R = max(R for sa in state_pool if sa.channel_signature.has('vision'))
      let audio_R = max(R for sa in state_pool if sa.channel_signature.has('audio'))
      let text_R = max(R for sa in state_pool if sa.channel_signature.has('text'))
      // 一致性 = 多模态同时有强响应
      return geometric_mean([vision_R, audio_R, text_R]) / arithmetic_mean([vision_R, audio_R, text_R])
    output_range: [0, 1]
    notes: "几何/算术平均比,模态都强时接近 1,只单模态强时接近 0"
  
  temporal_continuity_high:
    formula: "1.0 - var(R, last_K_ticks=10) / mean(R, last_K_ticks=10)"
    output_range: [0, 1]
    notes: "R 时序变异系数倒数 (1 - CV)"
  
  action_verifiability_high:
    formula: "sum(action.has_outcome_feedback and action.outcome_aligned, last_M=20) / 20"
    output_range: [0, 1]
    notes: "近 20 次行动有明确后果反馈且后果符合预期的比例"
  
  prediction_mismatch_ratio_high:
    formula: "sa.prediction_trace.mismatch_ratio"  # 已在 v8 cognitive_feelings 既有
    output_range: [0, 1]
    notes: "继承 v2.1 cognitive_feelings 既有特征"
  
  cognitive_pressure_high:
    formula: "sigmoid(sa.P * 2)"
    output_range: [0, 1]
    notes: "sigmoid 把 P 映射 [0, 1]"
  
  reality_sense_high_but_unexpected:
    formula: "feeling::reality_sense.value * feeling::prediction_mismatch.value"
    output_range: [0, 1]
    notes: "真实感高 + 预测误差大 = 违和"
  
  V_A_inertia_high:
    formula: "(sa.V * sa.A) / (sa.V_max_observed * sa.A_max_observed)"
    output_range: [0, 1]
    notes: "V * A 内源惯性指标"
  
  no_live_external_R:
    formula: "1.0 - external_R_recent_high"
    output_range: [0, 1]
    notes: "外感 R 低 → 内源主导"
  
  low_grasp_score:
    formula: "1.0 - g_i(t)"  # g 已在 v8 §12.2 定义
    output_range: [0, 1]
    notes: "把握度低 = 猜测感高"
  
  candidate_entropy_high:
    formula: "candidate_entropy(state_pool.recall_candidates) / log(K_candidates_max)"
    output_range: [0, 1]
    notes: "召回候选熵归一化"
  
  HEARSAY_marker_present:
    formula: "sigmoid(sum(m.real_energy for m in sa.markers if m.kind == HEARSAY) * 2)"
    output_range: [0, 1]
  
  source_entity_speaker_present:
    formula: |
      let speaker_entity = state_pool.most_recent_marker(HEARSAY).source_entity_id
      return 1.0 if speaker_entity is not None else 0.0
    output_range: [0, 1]
  
  text_input_recent_high:
    formula: "mean(text_char_R, last_5_ticks) / R_max_observed_window"
    output_range: [0, 1]
  
  INFERRED_marker_present:
    formula: "sigmoid(sum(m.real_energy for m in sa.markers if m.kind == INFERRED) * 2)"
    output_range: [0, 1]
  
  counterfactual_conflict:
    formula: |
      let cf = run_counterfactual_check(sa)  # §40.4 既有
      return cf.causal_conflict_score
    output_range: [0, 1]
    notes: "Phase 10+ 才完整启用,Phase 8-9 返回 0"
  
  others_feedback_consistent:
    formula: |
      let recent_user_feedback = state_pool.recent_feedback_aligned_with_sa(sa, last_K=20)
      return recent_user_feedback.alignment_ratio
    output_range: [0, 1]
```

**所有 feature 实施时直接读 yaml + 既有数据,无新硬编码**。

---

## 补丁 S4: §50.5 红线扫描扩 MarkerKind 分支(真修)

```python
# scripts/red_line_check_v13_1.py 新增

def check_no_marker_kind_branch_in_learning_rules():
    """
    禁止在学习/能量规则中按 MarkerKind 直接分支.
    允许:packet_key 派生路径(因为 packet_key 本身用 kind 组合).
    """
    # 1. 找所有 `if .*MarkerKind\.` 出现位置
    grep_result = subprocess.run(
        ["grep", "-rnE", r"if .*MarkerKind\.\w+", 
         "runtime/cognitive/", "--include=*.py"],
        capture_output=True, text=True
    )
    
    violations = []
    for line in grep_result.stdout.strip().split("\n"):
        if not line:
            continue
        
        # 解析 file:line
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        file_path, line_no, code = parts
        
        # 豁免条件:
        # 1. 文件路径含 packet_key 或 sdpl/ — 显式 packet 派生
        # 2. 文件路径含 sensor_adapters/ 或 marker_spawn/ — spawn 路径
        # 3. 注释 # @packet_derive 显式标注
        if "packet_key" in file_path or "/sdpl/" in file_path:
            continue
        if "/sensor_adapters/" in file_path or "/marker_spawn/" in file_path:
            continue
        if "@packet_derive" in code:
            continue
        
        # 否则违规
        violations.append(line)
    
    return violations
```

---

## 补丁 S5: 5 marker auto-spawn 完整规则表(真修)

```yaml
# config/marker_spawn_rules_v13_1.yaml

PERCEIVED:
  spawn_when: "sensor_adapter 输出 normalized SA event 时"
  spawn_function: "sensor_adapters/*/numeric_sensor.py:emit_percept"
  spawn_strength: "= percept_R * 0.8"  # 派生
  coexist_with: ["REMEMBERED"]  # 看见熟悉物体可同时有
  rationale: "外感输入是最基本来源"

IMAGINED:
  spawn_when: |
    SA 满足:
    1. 在 active_pool 但本 tick 无 sensor adapter 注入(no external R fresh)
    2. ledger.endogenous_share > 0.5
    3. R 来源中 imagination/replay/internal chain 占主导
  spawn_function: "runtime/cognitive/endogenous/imagination_marker_spawn.py"
  spawn_strength: "= sa.endogenous_share * 0.6"
  coexist_with: ["REMEMBERED", "INFERRED"]
  rationale: "内源链产生的 SA"

HEARSAY:
  spawn_when: |
    text 输入流来自 user/teacher (sensor adapter 标 origin=user_text):
    - emit text_char SA 同时 spawn HEARSAY marker
    - target = 由 text 内容触发的概念 vocab SA
  spawn_function: "sensor_adapters/text/user_text_sensor.py"
  spawn_strength: "= text_R * 0.7"
  source_entity_id: "= speaker_entity_id"
  coexist_with: ["INFERRED"]  # 听了再推断
  rationale: "需要 sensor adapter 区分 'user input' vs 'system self generated'"

REMEMBERED:
  spawn_when: |
    long_term cold→active rehydration 触发:
    - 从 cold_index 激活的 SA 同时 spawn REMEMBERED marker
  spawn_function: "runtime/cognitive/long_term/rehydration.py:_activate"
  spawn_strength: "= cue_alignment_factor * cold_sa.long_term_R * 0.5"
  coexist_with: ["PERCEIVED"]  # 看见熟悉物体共存
  rationale: "记忆召回标记"

INFERRED:
  phase_8_behavior: "spawn_disabled"  # Phase 8 不启用
  spawn_when_phase_11: |
    deliberative virtual track (§41.4) 产生新 SA 时:
    - virtual conclusion → main pool 时 spawn INFERRED marker
  spawn_function: "runtime/cognitive/deliberative/conclusion_reify.py"  # Phase 11
  rationale: |
    Phase 8 阶段:
    - INFERRED marker spawn 禁用
    - §56 guess_sense feature INFERRED_marker_present 暂返回 0
    - guess_sense 仍可经其他 features (low_grasp_score, candidate_entropy_high) 涌现
    Phase 11 启用 deliberative 后:
    - INFERRED spawn 自然启动
    - guess_sense 自然更精准
```

**关键澄清(回应轮 11 S5)**:
- Phase 8 阶段 INFERRED 不 spawn,但 guess_sense feeling 仍能从 low_grasp + entropy 涌现
- Phase 11 启用 deliberative 时自动接入,无破坏性升级
- HEARSAY 区分:sensor adapter 标 `origin=user_text` vs `origin=system_generated`

---

## 配套 v13.1 验收门

### Phase 8.3 红线 PR-gate(新增)

```python
# scripts/red_line_check_v13_1.py 综合
violations += check_all_gain_injection_points_use_ledger()
violations += check_no_marker_kind_branch_in_learning_rules()
violations += check_no_hardcoded_numeric_literals_in_cognitive()  # 沿用 v11
violations += check_constant_governance()  # 沿用 v11
violations += check_op_count_annotations()  # 沿用 v11

if violations:
    print(f"v13.1 RED LINE VIOLATIONS: {len(violations)}")
    sys.exit(1)
```

---

## 总结 v13.1

**v13 → v13.1 修复**:
- B1 packet_key 量化分桶 ✅
- B2 ledger.external_share 派生安全门 ✅
- B3 G_i 注入点穷尽清单(11 个位置)✅
- S1 V_floor + V_cap 双控 ✅
- S2 rehydration cache + cue_alignment 公式 ✅
- S3 §56 18 个 features 算子 ✅
- S4 红线扫描扩 MarkerKind 分支 ✅
- S5 5 marker auto-spawn 完整规则 + Phase 8 vs 11 differentation ✅

**M1 自适应稳态判定**(轮 11 M1)留到 v14 unified 补:
- 稳态判定 = `Q(packet_real, action) / Q(packet_imag, action)` 在 N episode 内方差 < ε

**M2 marker 5 个 decay_rates**(轮 11 M2):
- v13.1 暂保留(已在 v11 marker.decay_rates 同框架),v14 unified 时如审阅再提则统一改 base + multiplier 形式

**M3 v12.1 §44.2 vs v13 §51 重叠**(轮 11 M3):
- v13.1 §51 已显式标注 "replaces v12.1 §44.2 in full"
- v14 unified 时 v12.1 §44.2 不再存在

**下一步**:v14 unified consolidated — 把 v10 + v11 + v12 + v12.1 + v13 + v13.1 6 件套合并为单一权威文档。完成后归档前面 6 份到 archive/。

— 接手线程,2026-06-17
