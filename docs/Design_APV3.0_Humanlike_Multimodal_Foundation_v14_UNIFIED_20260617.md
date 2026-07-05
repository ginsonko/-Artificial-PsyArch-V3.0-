# APV3.0 拟人多模态底座 — 完整设计稿 v14 UNIFIED(单一权威文档)

日期: 2026-06-17
作者: 接手线程

状态: **12 轮对抗审阅 + 用户两轮哲学补完后的最终单一权威文档。合并 v10 主稿 + v11 patches + v12 endogenous + v12.1 errata + v13 SDPL + v13.1 errata,共 6 件套。归档前作到 docs/archive/。Codex 实施只读本稿 + apv3_constants.yaml + 红线脚本。**

前作归档:`docs/archive/{v10, v11_patch, v12_endogenous, v12_1_errata, v13_sdpl, v13_1_errata}.md`(参考用)

---

# 第 0 章 阅读指南

## 0.1 本文档与配套文件

| 文件 | 作用 |
|---|---|
| **本稿** (v14 UNIFIED) | 唯一权威设计稿 |
| `config/apv3_constants.yaml` | 全部数值常量唯一来源 |
| `config/constants_governance.yaml` | 常量分类协议(structural/scenario_tuneable/experimental)|
| `config/scenario_profiles/*.yaml` | 场景化常量覆盖(text_dialogue / desktop_pet / embodied / agent) |
| `config/family_to_type_mapping.yaml` | 5 type / 16 marker kinds 完整映射 |
| `config/marker_spawn_rules.yaml` | EpistemicSource 5 marker spawn rules |
| `config/cognitive_feeling_features.yaml` | 18 个 feature 算子定义 |
| `scripts/red_line_check_v14.py` | PR-gate AST 扫描 |
| `scripts/check_constant_governance.py` | 常量治理检查 |

## 0.2 Codex 实施前必读 cold-save

| Cold-save | 引用章节 |
|---|---|
| `Design_APV3.0能量本体数学模型_20260615.md` §3/§5/§6/§7/§12 | 第 11 章内源链 + 第 13 章能量稳态 |
| `APV21_BottomLayer_Design_Supplement_20260610.md` §4/§7.4-7.7 | 第 12 章 slot packet substrate |
| `ColdSave_P1-L-14多任务多未完成想法...` | 第 11 章 unfinished_pressure 实证 |
| `ColdSave_GL_OpenWorldDeferredIntentionOpportunityTrigger...` | 第 18 章跨 session 实证 |
| `ColdSave_GL_OpenWorldStage6A_LearnableAttentionFocusAction...` | 第 8 章三类注意力 |
| `Design_APV21_AutobiographicalRecall_RelationalAffect_Anchors_v0_1...` | 第 17 章自传式回忆 |

## 0.3 设计哲学顶层(用户原话浓缩)

1. **拟人 > 准确**:允许像人类一样犯错(把想象当事实/直觉性推理),通过奖惩自适应校准,不追求完全的正确
2. **AP-native**:所有机制 emerge from R/V/P/A/F 能量场 + 共现学习,无新公式形态,无 LLM 学生侧
3. **SA 平权**:任意类型 SA 在感知边界后等价参与状态池,不区分模态
4. **想象底层**:持续内源性想象是 AP 最底层机制之一,与外感学习等价
5. **来源分化**:同内容 + 不同来源 → 不同 packet,行动学习按 packet 不按内容(SDPL)

## 0.4 最高红线(违反即拒)

- ❌ **任何 `is_X: bool` 字段**(用 marker SA 多态 + ledger 替代)
- ❌ **任何 cognitive/ 内字面量数字**(白名单 `{0,1,2,3,-1,-2,0.0,1.0,-1.0}` 之外必须 `load_constant`)
- ❌ **任何 `if MarkerKind.X ==` 学习规则分支**(packet_key 派生路径除外)
- ❌ **任何关键词路由**(keyword/regex/字符串模板硬路由)
- ❌ **学生侧 LLM 输出**(LLM 只 teacher/judge,不 commit 答案)
- ❌ **algorithm spec 无 `@op_count` 注解**
- ❌ **测试断言用语义字串**(只能 action_id / learned successor)
- ❌ **audit_db 在 cognitive 路径出现**(只供 UI 渲染)

---

# 第 1 章 SA 类型架构(5 types + 16 marker kinds)

## 1.1 五大 SA 类型

```yaml
# config/family_to_type_mapping.yaml
PerceptSA:                              # type 1: 感受器输出
  - vision_percept
  - audio_percept
  - text_char
  - number_count                        # subitize 1-3
  - sensor_salience_hint
VocabSA:                                # type 2: 概念/词汇/范畴
  - vocab
  - tentative_vocab
  - narrative                           # Phase 10
  - causal                              # Phase 10
  - hierarchy                           # Phase 10
  - anonymous_cluster                   # Phase 10
  - abstract_vocab                      # Phase 11
MarkerSA:                               # type 3: 瞬态状态标记(cap 20)
  kinds_documented:
    - NOVELTY / TENTATIVE / PAIN / MISMATCH / CORRECTION
    - GAZE / JOINT_ATTENTION / IMITATION / KNOWLEDGE_GAP
    - EMPATHY_RESONANCE / TRUST_PROMOTED / BOREDOM
    - IMAGINATION                       # v12 起
    - PERCEIVED / IMAGINED / HEARSAY    # v13 EpistemicSource
    - REMEMBERED / INFERRED             # v13 EpistemicSource
  kinds_reserved: [SATISFACTION, SURPRISE_RESIDUAL, SELF_REFERENCE]
EntitySA:                               # type 4: 持久实体
  - drive / entity_user / self_model
  - focus / goal / belief_model / hypothesis
ControlSignalSA:                        # type 5: 控制信号
  - utterance_boundary / tick_boundary / mode_switch
```

## 1.2 类型分组 attention 预算

```yaml
attention:
  type_budget:                          # @scenario_tuneable
    PerceptSA: 0.35
    VocabSA: 0.25
    MarkerSA: 0.15
    EntitySA: 0.20
    ControlSignalSA: 0.05
```

---

# 第 2 章 SA 能量动力学(R/V/P/A/F)

继承 APV2.1 `core/state_pool/state_pool.py` 既有公式,**关键修正(v12)**:

## 2.1 Π 更新双语义(关键)

```python
def update_prediction_pi(sa, observations_window, learning_rate, currently_occurring):
    """
    @op_count: O(1).
    
    occurring SA: TD(0) - target=R_observed_at_t+1
    absent SA:    Π *= ρ_pi_absent (不归零,可被未来召回)
    """
    if currently_occurring:
        target = observations_window.next_tick_R_for(sa)
        residual = target - sa.Pi
        eta = min(load_constant("energy.eta_pi_max"), 
                  load_constant("energy.eta_pi_kappa") * abs(residual))
        sa.Pi += eta * residual
    else:
        sa.Pi *= load_constant("energy.Pi_decay_when_absent")
```

## 2.2 target_cap 真 0 floor(B7 fix)

```python
def compute_target_cap(sa, current_tick):
    """
    @op_count: O(1).
    
    v12 §44.3:baseline 真 0 floor,无 0.05 钳位.
    防想象越界冒充感.
    """
    if sa.has_live_external_evidence_this_tick():
        ruler = sa.real_energy
    else:
        ruler = sa.decayed_baseline      # 真 0,无钳位
    return max(0.0, ruler * load_constant("composed_vocab.target_cap_ratio"))
```

## 2.3 V 双控(v13.1)

V 在 [V_floor, V_cap] 区间:
- V_cap = real_evidence_cap(防想象冒充感)
- V_floor = memory_support(允许 cue-relevant 长时记忆维持 prediction chain)

```python
def apply_v_double_control(sa, t):
    """@op_count: O(1)."""
    v_cap = compute_real_evidence_cap(sa, t)
    v_floor = compute_memory_support_V_floor(sa, t)
    
    if v_floor > v_cap:
        sa.virtual_energy = max(sa.virtual_energy, v_floor)
    else:
        sa.virtual_energy = clamp(sa.virtual_energy, v_floor, v_cap)
```

---

# 第 3 章 Attention Selector + Gain Ledger

## 3.1 Attention Selector 真凸组合(v13.1 §51)

```python
def compute_attention_score(sa, t):
    """
    @op_count: O(1).
    
    v13.1: 真凸组合 + ledger-driven 安全门.
    """
    w = load_constant("attention.s_attn_weights")
    
    s_external = (w["beta_P_external"]*sa.P + w["beta_R"]*sa.R 
                  + w["beta_A"]*sa.A - w["beta_F"]*sa.F + w["beta_V"]*sa.V)
    s_internal = (w["beta_P_internal"]*max(0,sa.P) 
                  + w["beta_A_internal"]*sa.A - w["beta_F_internal"]*sa.F)
    
    g = clamp(sa.gain_ledger.endogenous_share(), 0.0, 1.0)
    s_mixed = (1 - g) * s_external + g * s_internal
    
    # 外部 surprise 安全门(ledger-driven,无未定义符号)
    external_share = (sa.gain_ledger.gain_by_source["external"] 
                      / max(sa.gain_ledger.total(), 1e-9))
    if (external_share > load_constant("attention.external_dominance_safety_threshold")
        and sa.P > load_constant("attention.surprise_P_threshold")):
        return s_external
    
    return s_mixed
```

## 3.2 Attention Gain Ledger(v13 §52)

每 SA 维护 8 维 attention_gain 来源账本:

```python
class AttentionGainLedger:
    """
    @op_count: O(1) per inject.
    
    源类型:external / feedback / unfinished_pressure / expectation_pressure
            / residual_mass / imagination / replay / user_directed
    
    所有 G_i 注入点必经 inject() — 红线扫描强制.
    """
    def __init__(self):
        self.gain_by_source = {k: 0.0 for k in [
            "external", "feedback", "unfinished_pressure",
            "expectation_pressure", "residual_mass",
            "imagination", "replay", "user_directed",
        ]}
    
    def inject(self, source: str, amount: float):
        assert source in self.gain_by_source
        self.gain_by_source[source] += amount
    
    def step_decay(self):
        decay = load_constant("energy.A_decay")
        for k in self.gain_by_source:
            self.gain_by_source[k] *= decay
    
    def total(self):
        return sum(self.gain_by_source.values())
    
    def endogenous_share(self) -> float:
        endo = sum(self.gain_by_source[k] for k in [
            "unfinished_pressure", "expectation_pressure",
            "residual_mass", "imagination", "replay",
        ])
        return 0.0 if self.total() < 1e-9 else clamp(endo / self.total(), 0.0, 1.0)
```

## 3.3 G_i 注入点穷尽清单(v13.1 §52)

| 位置 | source label |
|---|---|
| `sensor_adapters/vision/numeric_sensor.py:emit_percept` | `external` |
| `sensor_adapters/audio/numeric_sensor.py:emit_audio_proto` | `external` |
| `sensor_adapters/text/char_stream.py:emit_text_char_sa` | `external` |
| `sensor_adapters/salience_hint.py:apply_salience` | `external` |
| `runtime/cognitive/reward/handler.py:apply_reward` | `feedback` |
| `runtime/cognitive/reward/handler.py:apply_punishment` | `feedback` |
| `runtime/cognitive/endogenous/step.py:step_endogenous_drive` | `unfinished/expectation/residual` |
| `runtime/cognitive/endogenous/imagination_marker.py:spawn_imagination` | `imagination` |
| `runtime/cognitive/long_term/rehydration.py:rehydrate_cue_match` | `replay` |
| `runtime/cognitive/memory/long_term_support.py:apply_memory_support` | `replay` |
| `runtime/cognitive/action/focus_action_runner.py:apply_focus_action` | `user_directed` |

**红线扫描**:任何 `attention_gain +=` 同函数内必须有 `ledger.inject()`。

## 3.4 类型预算执行

继承 v8 §11.3 type budget enforce — 候选按 score 排序,达类型预算上限即跳过。

---

# 第 4 章 Sensor Adapter 边界 + 文本字符微事件

## 4.1 边界图

```
raw input → modality-specific extractor [允许模态分支]
         → quantization buckets [VQ codebook per channel]
         → normalized SA event [边界]
         → AP-Core runtime [禁止模态分支]
```

红线扫描:`grep "if .*modality" runtime/cognitive/` 必须 0 命中。

## 4.2 文本字符微事件 + utterance_boundary

```python
def step(self, t):
    """@op_count: O(chars_per_tick)."""
    # 处理字符流
    chars_per_tick = load_constant("draft_action.text_chars_per_tick_default")
    for _ in range(chars_per_tick):
        if queue.is_empty(): break
        emit_text_char_sa(queue.pop().char, source_kind="streaming")
        self.last_char_tick = t
    
    silence_ticks = t - self.last_char_tick
    threshold = self.per_user_silence_distribution.percentile(self.last_user_id, 0.95) \
                or load_constant("text_sensor.silence_threshold_anonymous_ticks")
    
    if self.explicit_eom_received and queue.is_empty():
        emit_boundary("explicit", boundary_R=high_R)
    elif silence_ticks > threshold:
        emit_boundary("soft", boundary_R=sigmoid((silence_ticks-threshold)/10) * mid_R)
```

## 4.3 audit_db 严格只渲染

| 访问目的 | 允许? |
|---|---|
| AP runtime 召回 / 决策 / 学习 | ❌ |
| Web UI 内心画面/音频渲染 | ✅ |
| 用户 audit trail | ✅ |
| LLM 周期清理 | ✅ |

三层渲染 fallback:
1. audit_db 命中 → high-fidelity payload
2. 通道签名完整 → stylized blob
3. 仅 vocab 链接 → introspection text

红线:`grep "audit_db" runtime/cognitive/` 必须 0 命中。

---

# 第 5 章 SDPL — Source-Differentiated Packet Learning(底层原则)

## 5.1 原则

> 内容 SA 共享,来源/感受 SA 分化进 packet,行动后果按 packet 学习,不按内容学习。

适用一切同内容异态学习:想象 vs 真实 / 听闻 vs 自见 / 记忆 vs 当下 / 推断 vs 确定 / 教师讲 vs 自推。

## 5.2 EpistemicSource Marker 族

5 个 marker kinds(v13):

```yaml
PERCEIVED:   外部感受器输入产生
IMAGINED:    内源链产生
HEARSAY:     听用户/他人陈述
REMEMBERED:  从 long_term 召回
INFERRED:    内部推理(deliberative,Phase 11 启用)
```

详细 spawn rules 见 `config/marker_spawn_rules.yaml`(v13.1 §S5)。

## 5.3 Packet 量化分桶 packet_key(v13.1 B1)

```python
class LearningPacket:
    """
    @op_count: O(|content|+|feeling|) ~ 30 ops.
    
    v13.1 量化分桶版,保留 R/feeling 强度信息.
    """
    content_sas: list[SA]
    source_markers: list[MarkerSA]
    feeling_sas: list[FeelingSA]
    slot_context: list[SA]
    
    @staticmethod
    def quantize_3_bins(value, low_thresh, high_thresh):
        if value < low_thresh: return 0
        elif value < high_thresh: return 1
        else: return 2
    
    def packet_key(self):
        c = load_constant
        content_with_bucket = frozenset(
            (sa.id, self.quantize_3_bins(sa.R, 
                c("sdpl.packet_key.R_bucket_low_threshold"),
                c("sdpl.packet_key.R_bucket_high_threshold")))
            for sa in self.content_sas
        )
        source_energy = defaultdict(float)
        for m in self.source_markers:
            source_energy[m.kind] += m.real_energy
        source_with_bucket = frozenset(
            (kind, self.quantize_3_bins(energy,
                c("sdpl.packet_key.R_bucket_low_threshold"),
                c("sdpl.packet_key.R_bucket_high_threshold")))
            for kind, energy in source_energy.items()
        )
        dominant = max(source_energy.items(), key=lambda x: x[1])[0] if source_energy else None
        feeling_with_bucket = frozenset(
            (f.key, self.quantize_3_bins(f.value,
                c("sdpl.packet_key.feeling_bucket_low_threshold"),
                c("sdpl.packet_key.feeling_bucket_high_threshold")))
            for f in self.feeling_sas
        )
        return (content_with_bucket, source_with_bucket, dominant, feeling_with_bucket)
```

## 5.4 SDPL 学习规则

```python
def sdpl_observe_packet(packet):
    """
    @op_count: O(|content|^2 + |action|), worst 500 ops/tick.
    
    所有学习按 packet key 累积,不按 content key.
    """
    pk = packet.packet_key()
    
    # 共现学习按 packet 范围
    for sa_a, sa_b in itertools.combinations(packet.content_sas, 2):
        sparse_pairwise_graph.observe_under_packet_key(sa_a, sa_b, pk)
    
    # lag-PMI 按 packet
    for sa in packet.content_sas:
        temporal_graph.observe_under_packet_key(sa, pk, current_tick)
    
    # 行动后果按 packet
    if last_action_outcome.is_settled():
        Q_table.update(packet=packet, action=last_action,
                       outcome=last_action_outcome.value,
                       eligibility=compute_eligibility(packet, last_action))
```

## 5.5 关键拟人涌现(用户哲学验收)

- 真实看到火 + 躲开 → 奖励 → `Q({火, PERCEIVED, reality_high}, 躲开)` ↑
- 想象到火 + 躲开 → 违和 → `Q({火, IMAGINED, imagination_high}, 躲开)` ↓
- 想象到火 + 检查 → 中性 → `Q({火, IMAGINED, imagination_high}, 检查)` ↑
- **看到火逃,想到火检查 — 自然涌现**,无新公式

## 5.6 红线

- ❌ vocab SA 加 `is_real / is_imagined / is_remembered` 字段
- ❌ 学习规则按 `if MarkerKind.X ==` 分支(packet_key 派生豁免)
- ❌ 预装"现实感"为固定权重(必须经 features 自适应)

---

# 第 6 章 通用 SA 组合词汇固化(SDPL 升级版)

## 6.1 量化桶 + 稀疏 pairwise

每通道 VQ codebook(v6 §2.2),稀疏 top-k 邻接(v6 §2.3,每 SA max 32 partners)。

## 6.2 ΔP 晋升门(incremental + cold-fork,v8)

```python
def evaluate_delta_p_incremental(candidate, current_pool, held_out_pool):
    """
    @op_count: O(N_situations × N_horizon × |SA|), worst 8×5×50=2K.
    
    v8 B-V9-3: horizon=5 防衰减归零.
    SDPL 升级:候选与已有 vocab 共现按 packet_key 计.
    """
    K = load_constant("composed_vocab.delta_p.n_situations_per_eval")
    N = load_constant("composed_vocab.delta_p.n_horizon_ticks")
    cold_min = load_constant("composed_vocab.delta_p.cold_start_skip_until_held_out")
    
    if len(held_out_pool) < cold_min:
        return {"passes": False, "reason": "insufficient_held_out",
                "fallback_to_pmi_only": True}
    
    current_sig = compute_context_signature(current_pool)
    similar = held_out_pool.find_top_k_similar(current_sig, k=K)
    
    delta_Ps = []
    for situation in similar:
        pool_a = situation.shallow_clone_pool_state()
        for _ in range(N): advance_lightweight(pool_a)
        P_a = pool_a.mean_recent_P()
        
        pool_b = situation.shallow_clone_pool_state()
        pool_b.inject_vocab(candidate)
        for _ in range(N): advance_lightweight(pool_b)
        P_b = pool_b.mean_recent_P()
        
        delta_Ps.append(P_a - P_b)
    
    mean_delta = float(np.mean(delta_Ps))
    n_positive = sum(1 for d in delta_Ps if d > 0)
    passes = (mean_delta > load_constant("composed_vocab.delta_p.promote_dP_min")
              and n_positive >= K * 0.625)
    return {"mean_delta_P": mean_delta, "n_situations_positive": n_positive,
            "passes": passes, "framework": "short_term_value_add"}
```

## 6.3 反例撤销(v6 §2.7)+ 两阶段 credit assignment(v8 §2.7)

负反馈先 spawn MISMATCH marker + CORRECTION hypothesis,等教师证据来才精准扣 vocab。50 tick timeout 后按 attention_share 部分扣。

## 6.4 lag-PMI 时序共现底层原语(v7 §2.8)

```python
# 用于 narrative / causal / 序列学习
def lag_pmi(sa_a, sa_b, lag):
    """log(P(B at t+k | A at t) / P(B at t+k))"""
    # bayesian smoothed
    ...
```

---

# 第 7 章 黄苹果对照课程 + slot 偏好统计涌现

## 7.1 对照课程(v5 §6.2)

```yaml
training_curriculum:
  - red_apple + "红色苹果" × 20
  - green_apple + "绿色苹果" × 20
  - yellow_banana + "黄色香蕉" × 20
  - yellow_cup + "黄色杯子" × 20
  - yellow_ball + "黄色球" × 20
  - red_ball + "红色球" × 15(干扰)
  - green_ball + "绿色球" × 15(干扰)
```

## 7.2 slot 偏好 MI 涌现(v8 §6.3 + v10 codebook snapshot)

```python
def derive_channel_preference(slot, decision_tick):
    """@op_count: O(|fillers| × |channels|), worst 100 ops."""
    if len(set(slot.fillers_history)) < load_constant("slot_preference.min_distinct_fillers"):
        return None
    
    dedup = list(set(slot.fillers_history))
    channel_score = {}
    for c in all_channels:
        codebook_size = c.current_codebook_size  # snapshot at decision time
        filler_buckets = [quantize(sa.get_channel_payload(c), c) for sa in dedup]
        slot_dist = laplace_smoothed(filler_buckets, codebook_size)
        global_dist = global_bucket_distribution(c, snapshot=True)
        # JSD bounded by log(2) + normalize by log(codebook_size)
        jsd = jensen_shannon_divergence(slot_dist, global_dist)
        channel_score[c] = jsd / log(codebook_size)
    return softmax([channel_score[c] for c in all_channels])
```

## 7.3 验收 + ablation(v5 §6.4)

```python
def test_yellow_apple_generalization():
    # 教学日志诚实门
    for tick in teaching_log:
        assert not ("黄色" in tick.text and "苹果" in tick.text)
    
    # 真实图像感知
    percept = vision_sensor.process(generate_yellow_apple_image())
    state_pool.apply_percept(percept)
    output = run_tick_loop_until_commit()
    
    # 输出含 vocab id,断言 token id 不查中文
    assert vocab_id_for("黄色") in output.committed_vocab_ids
    assert vocab_id_for("苹果") in output.committed_vocab_ids

def test_C1_C2_ablation():
    # C1 屏蔽 → 只输出颜色
    state_pool.disable_channel("C1")
    output = trigger_describe(yellow_apple_image)
    assert vocab_id_for("黄色") in output.committed_vocab_ids
    assert vocab_id_for("苹果") not in output.committed_vocab_ids
```

---

# 第 8 章 视觉/音频感受 + 焦点 + 三类注意力

## 8.1 多通道(v6 §3.2)+ smoothstep foveated(v8 §13.3)

```python
def resolution(p, focus):
    return R_low + (R_high - R_low) * (1 - smoothstep(d_min, d_max, distance(p, focus)))
```

## 8.2 音频谐波 filterbank(v7 §13.5)

```python
def audio_gain(audio_sa, focus_template):
    if focus_template is None:
        return single_peak_gain(audio_sa.f0, focus.center, focus.width)
    total = (1 - β_audio)
    for peak_hz, peak_w, peak_weight in zip(template.peaks_hz, ...):
        total += α_audio * peak_weight * exp(-(audio_sa.f0 - peak_hz)**2 / (2*peak_w**2))
    return total
```

## 8.3 P_field percept-centric WTA(v6 §14.2)+ 持驻焦点(v6 §14.4)

- WTA over percept centers(不全屏卷积)
- dwell_min_ticks + 滞回 margin

## 8.4 三类注意力(v12 §47)

```
Type 1 - 内源注意力:无外源,§44 三源驱动 + A-loop
Type 2 - 外部夺取:新外源带惊,§3.1 安全门触发
Type 3 - 主动聚焦:agent commit action::focus_on(target)
```

全部经同一 attention selector,**只是能量驱动源不同**。

---

# 第 9 章 草稿行动竞争

## 9.1 行动 SA 候选(v6 §16.9 + v8 Gaussian Thompson)

```python
def get_action_expected_R_change(action_type, context, target):
    """@op_count: O(1)."""
    learned = action_memory.lookup(action_type, context, target)
    min_samples = load_constant("action_competition.min_samples_thompson")
    
    if learned.sample_count >= min_samples:
        return np.random.normal(learned.mean_R_change, sqrt(learned.var_R_change))
    
    if not has_derived_noise_scale():
        return 0.0 + np.random.normal(0, 1.0)  # uninformative prior
    return 0.0 + np.random.normal(0, get_derived_noise_scale())
```

## 9.2 SDPL 升级(关键)

Q 表按 packet_key 索引,不按 (action, content) 索引:
```python
Q_table.update(packet=packet, action=last_action, outcome=last_outcome, ...)
```

同 content 不同 source → 不同 Q。

---

# 第 10 章 Cognitive Feelings(标准 + EpistemicSource 5 新)

## 10.1 v6 §16.4 补完 4 通道

`fluency / boredom / fulfillment / satisfaction` 从既有状态量派生(配 yaml 公式)。

## 10.2 EpistemicSource 综合感受 5 新(v13 §56)

```
feeling::reality_sense        — 现实感(外感强 + 多模态一致 + 验证性高)
feeling::imagination_sense    — 想象感(内源主导 + 无外感 + V/A 惯性)
feeling::hearsay_sense        — 听闻感(HEARSAY marker + speaker entity)
feeling::guess_sense          — 猜测感(low grasp + 高熵 + INFERRED)
feeling::incongruity          — 违和感(预测失配 + reality 高但意外)
```

## 10.3 18 个 feature 算子(v13.1 §S3)

见 `config/cognitive_feeling_features.yaml`,每条一行公式 + [0,1] 域,经 `CognitiveFeelingFactory` 工厂涌现,**不预装权重**。

---

# 第 11 章 持续内源性想象(用户底层 1)

## 11.1 内源链(能量本体 §6)

无外源 / 低需求时,系统进入内源链 — 不靠 R(蒸发),靠 V/A 惯性维持。target_cap 0 floor 防越界。打断恢复靠 unfinished_pressure 能量竞争。

## 11.2 三源持续注入(v12 §44.4 + v12.1 sigmoid 软边)

```python
def step_endogenous_drive(state_pool, t):
    """@op_count: O(|active SA|), worst 200 ops/tick."""
    idle_score = compute_idle_score(state_pool, t)
    # sigmoid 软边(无硬 if/else)
    idle_boost = 1 + sigmoid_soft(idle_score, 
                                   load_constant("endogenous.idle_score_softness_k"),
                                   load_constant("endogenous.idle_score_midpoint"),
                                   load_constant("endogenous.idle_boost_max"))
    
    for sa in state_pool.active_sas():
        # Source 1: unfinished_pressure
        d_unfin = load_constant("endogenous.delta_unfinished") * sa.unfinished_pressure
        sa.gain_ledger.inject("unfinished_pressure", d_unfin)
        sa.attention_gain += d_unfin
        # Source 2: expectation_pressure
        d_exp = load_constant("endogenous.delta_expectation") * sa.expectation_pressure
        sa.gain_ledger.inject("expectation_pressure", d_exp)
        sa.attention_gain += d_exp
        # Source 3: residual_mass
        d_res = load_constant("endogenous.delta_residual") * residual_tracker.get(sa).mass * idle_boost
        sa.gain_ledger.inject("residual_mass", d_res)
        sa.attention_gain += d_res
```

## 11.3 即时联想 3 路速度光谱(v12.1 B3)

```
1. learned_similarity (vector) — ms 级,即时
2. lag-PMI                      — 秒级,中速
3. chain extension              — 慢,min_obs=5 + ΔP 晋升
```

用户原例 1("看到针 → 联想被扎/疼痛"):走 path 1。

## 11.4 PainResonanceMarker(L1 fix)

想象的疼痛 = IMAGINATION marker 投射到 pain prototype,**不直接 emit feeling::pain channel**(避免想象冒充真痛)。

---

# 第 12 章 Slot Packet Substrate(BottomLayer §7.4-7.7)

每 tick 焦点 packet 显式作为虚能量内源 SA bundle 注入状态池:
- slot_summary / slot_item / slot_order / slot_continuity
- packet 内含外感 + 内省 + 想象 SA → §5 SDPL 共现学习等价
- 红线:slot packet 不能压过外部输入(BottomLayer §7.4)

---

# 第 13 章 习惯化 + Novelty Trace

## 13.1 习惯化(v6 §11.2)

通过 Π 几何收敛 + prediction fatigue + attention fatigue 自然涌现。无 `is_stable` 字段。

## 13.2 Novelty Residual Marker(v6 §11.3)

突然出现 → P 大正 → spawn `MarkerKind.NOVELTY` 持续 ~3 秒注入 attention_gain,保证秒级注意。

## 13.3 主动 refocus(v6 §11.5)

`action::attention::refocus_on(target)` 经 ActionParameterMemory 学到的"refocus 期望 ΔP",无 hardcoded curiosity prior。

---

# 第 14 章 Sleep emerge + global_fatigue

```python
def compute_target_tick_ms(t):
    """@op_count: O(1)."""
    base = config.scenario.base_tick_ms
    dilation_fatigue = sigmoid((global_fatigue - 0.5) * 4) * 10
    learned_dilation = action_parameter_memory.get_learned_tick_dilation(context)
    return base * (1 + dilation_fatigue) * (1 + learned_dilation)
```

无显式 sleep/wake 状态机,连续 tick 频率随累积疲劳渐变。

---

# 第 15 章 双 Cap V 控(memory vs real)

```python
def compute_real_evidence_cap(sa, t):
    """V 上限 — 防想象冒充感"""
    ruler = sa.real_energy if sa.has_live_external_evidence_this_tick() else sa.decayed_baseline
    return max(0.0, ruler * load_constant("composed_vocab.target_cap_ratio"))

def compute_memory_support_V_floor(sa, t):
    """V 下限 — 允许 cue-relevant 长时记忆维持"""
    if not sa.is_in_long_term_layer(): return 0.0
    cue_align = compute_cue_alignment(sa, current_context_signature)
    return sa.long_term_R * cue_align * load_constant("long_term.memory_V_admit_ratio")
```

---

# 第 16 章 Long_term Double Layer(cold index + rehydration)

```python
class LongTermLayer:
    """
    @op_count(scan): O(|cold_index| × 16); cache hit O(1).
    """
    def __init__(self):
        self.cold_index = SQLiteColdStore(capacity=load_constant("long_term.cold_index_capacity"))
        self.active_pool = OrderedDict()
        self.max_active = load_constant("long_term.active_pool_max_from_long")
    
    def rehydrate_by_cue(self, current_sig):
        if not self._signature_drift_too_large(current_sig):
            return self.cached_top_candidates
        threshold = load_constant("long_term.rehydration_similarity_threshold")
        top_k = load_constant("long_term.rehydration_top_k_per_tick")
        candidates = self.cold_index.find_top_k_by_signature(current_sig, k=top_k*3)
        rehydrated = []
        for cold_sa, sim in candidates:
            if sim < threshold or len(rehydrated) >= top_k: break
            self._activate(cold_sa, sim)
            rehydrated.append(cold_sa)
        while len(self.active_pool) > self.max_active:
            evicted_id, evicted = self.active_pool.popitem(last=False)
            self.cold_index.store(evicted)
        self.last_signature = current_sig
        self.cached_top_candidates = rehydrated
        return rehydrated
    
    def session_boot(self):
        self.cold_index.warm_load_from_sqlite()
        # active_pool 空,等待 cue 触发
    
    def _activate(self, cold_sa, sim_score):
        cold_sa.R = cold_sa.long_term_R * sim_score
        cold_sa.gain_ledger.inject("replay", small_seed_gain * sim_score)
        # spawn REMEMBERED marker
        spawn_marker(MarkerKind.REMEMBERED, target=cold_sa.id, 
                     real_energy=sim_score * 0.5)
        self.active_pool[cold_sa.persistent_id] = cold_sa
```

---

# 第 17 章 Phase 8 实施顺序

```
Phase 8.2   连续 tick + sensor adapter
Phase 8.3   audit_db + target_cap 0-floor + AttentionGainLedger 接入
            + 双 V 控 + EpistemicSource PERCEIVED auto-spawn
Phase 8.4   ComposedVocab + cold-fork ΔP
            + SDPL: 共现学习按 packet key
Phase 8.5   CFS 4 通道(v6 既有) + complexity/simplicity trace_only
            + 5 新 EpistemicSource feelings(reality/imagination/hearsay/guess/incongruity)
Phase 8.6   视觉感受 + 量化桶 + 多通道 + IMAGINED marker spawn
Phase 8.7   视焦点 + saccade + 持驻 + overlay + 三类注意力 focus action
Phase 8.8   黄苹果泛化(对照课程 + ablation,核心证伪门)
Phase 8.9   自然纠错 + SDPL: 行动学习按 packet + 两阶段 credit assignment
Phase 8.10  习惯化 + Π 几何收敛 + novelty/marker + sleep emerge
            + §11 持续内源驱动 + 凸组合 attention + 外部 surprise 安全门
            + §44 mini-gate
Phase 8.11  Web 工作台 + 内源链可视化 + ledger 饼图 + feelings 显示
Phase 8.12  fast mapping + shape bias + epistemic drive + 反向想象
            + HEARSAY marker auto-spawn(user text)
Phase 8.13  音频感受 + filterbank vocab 模板
Phase 8.14  端到端 + SDPL 拟人验收套件(4 个 gate)
Phase 8.15  short→long 显式 + Long_term cold + active 双层
Phase 8.16  跨 session 延迟意图(无 sleep 依赖)+ rehydration 测试
Phase 8.17  自传式回忆 + REMEMBERED marker spawn 完整 + entity 锚点

—— Phase 8 = 18-30 月龄 + 持续想象 + 跨天意图 + 来源监控 ——

Phase 9.X 沿用 backlog
```

---

# 第 18 章 验收套件

## 18.1 习惯化 4 gate(v6)

风扇 SA s_attn 单调下降 + novelty_residual 秒级保持 + refocus 复活习惯化 + Π 学习率上限验证。

## 18.2 黄苹果泛化 + C1/C2 ablation(v5)

教学日志诚实门 + 真实图像感知 + token id 断言 + ablation 屏蔽通道。

## 18.3 跨 session 延迟意图(v12.1 §B1)

```python
def test_cross_session_deferred_intention():
    # Session 1: 教学学到 action prototype 关联
    teaching_phase(scenario="construction_visual",
                   action_label_id="ACTION_REROUTE_001",
                   reward=positive)
    # 内源 reasoning
    for _ in range(K): inject_endogenous_intent_via_imagination("vocab::避修路")
    persist_to_sqlite()
    session_close()
    
    # Session 2: 视觉 cue
    boot_from_persistence()
    show_visual_input("construction_scene_image")
    for _ in range(N): run_tick()
    
    # 严格断言 action_id,不查中文
    assert state_pool.commit_record.last_action_id == "ACTION_REROUTE_001"
```

## 18.4 SDPL 拟人验收 4 个 gate(v13 §58.2)

1. **想象促进学习**:外感 + 想象训练 → 比纯外感学得快
2. **人类式误判 → 学会**:想象引发误行动 → 惩罚后 packet Q 降,但真实 packet 不变
3. **不沉迷幻想**:外部 surprise 1-3 tick 内拉走焦点
4. **来源感受涌现**:训练后 reality_sense / imagination_sense 自然区分

## 18.5 长时记忆不爆炸(v8 S-V9-2)

```python
def test_long_term_no_explosion():
    # 跑 1000 session × 50 long_term 晋升
    for s in range(1000): simulate_session()
    assert cold_index.size() == 50000
    assert len(active_pool) <= load_constant("long_term.active_pool_max_from_long")
```

---

# 第 19 章 全部常量 yaml 参考

见 `config/apv3_constants.yaml`,完整段:
- `energy.*` — R/V/P/A/F 衰减、Π 收敛、target_cap、baseline_floor
- `marker.*` — 16+ kinds decay_rates + cap
- `composed_vocab.*` — pairwise + chain + delta_p
- `slot_preference.*` — JSD smoothing + min_distinct_fillers
- `attention.*` — type_budget + s_attn_weights(8 weights)+ safety thresholds
- `action_competition.*` — bootstrap + Thompson + 派生 noise
- `draft_action.*` — text_chars_per_tick
- `text_sensor.*` — silence thresholds + percentiles
- `credit_assignment.*` — timeout + threshold
- `counterfactual.*` — bootstraps + levels + thresholds
- `hierarchy.*` — agglomerative + soft assignment
- `deliberative.*` — virtual track + reification
- `self_model.*` — heartbeat + cap + pullback
- `held_out.*` — reservoir + k_fold
- `endogenous.*` — 三源 delta + idle softness
- `attention.s_attn_weights.*` — 8 weights(external + internal)
- `imagination.*` — marker decay + immediate_recall
- `cognitive_feelings_trace_only.*` — complexity/simplicity thresholds
- `sdpl.*` — packet_key buckets + q_table
- `long_term.*` — cold_index + rehydration + memory_V_admit_ratio
- `vocab.*` — kinds + awaiting_revalidation
- `context_signature.*` — weights
- `marker.decay_rates.PERCEIVED/IMAGINED/HEARSAY/REMEMBERED/INFERRED` — 5 新

## 19.1 治理协议

- `@structural`:数学上有明确意义(如 Bayesian prior 0.5)
- `@scenario_tuneable`:场景可覆盖,每值经 A/B 实验记录
- `@experimental`:初值猜测,Phase X.Y 验收后 tune

---

# 第 20 章 Phase 9+ 远景(backlog)

```
Phase 9.1   驱力 / 内稳态(drive_SA 一等公民)
Phase 9.2   RPE / dopamine analog
Phase 9.3   受挫 / 习得性无助
Phase 9.4   依恋 / 熟悉性偏好(entity_user_sa + OXY)
Phase 9.5   共同注意 / 镜像(JOINT_ATTENTION marker)
Phase 9.6   共情 / 心智化(EMPATHY_RESONANCE marker)
Phase 9.7   痛持续记忆(PAIN marker 长衰减)
Phase 9.8   重放巩固 / 睡眠学习
Phase 9.9   游戏 / 探索玩乐
+ Phase 9.X imitation / gaze contingency / number sense

—— Phase 9 = 3-5 岁心智深度 ——

Phase 10.1  Narrative SA(用 lag-PMI 真实学习)
Phase 10.2  匿名 super-cluster spawn
Phase 10.3  反事实模拟(counterfactual_strength CDE 框架)
Phase 10.4  因果 SA(依赖 10.3)
Phase 10.5  ToM 信念模型 + 假信念测试
Phase 10.6  Hierarchy SA + 命名绑定
Phase 10.7  Trust prior(TRUST_PROMOTED marker)+ downgrade
Phase 10.8  Reading 单管道 + source 字段

—— Phase 10 = 5-8 岁能力 ——

Phase 11.1  Meta-cognition + domain 定义
Phase 11.2  Abstract vocab cross-cluster gate
Phase 11.3  Goal SA + 长 horizon
Phase 11.4  Deliberative virtual track + INFERRED marker auto-spawn
Phase 11.5  Self model(衰减 + heartbeat)

—— Phase 11 = 8-12 岁能力 ——

Phase 12+   真实硬件 + SNS 桌宠产品化 + Agent 工作流
```

---

# 第 21 章 给 Codex 的最终指令

1. **本稿(v14 UNIFIED)是唯一权威设计文档**
2. **6 件套前作归档 `docs/archive/`,参考用,不实施**
3. **Phase 8.5(CFS 补完)阻断式前提**
4. **Phase 8.8(黄苹果泛化)核心证伪门**——失败禁止 workaround
5. **Phase 8.10 §11 持续内源 + 凸组合 + safety gate 必跑 mini-gate**
6. **Phase 8.14 SDPL 拟人验收 4 个 gate 必跑**
7. **Phase 8.16 跨 session 测试不依赖 §27**
8. **每 PR 必跑 4 个红线脚本**:
   - AST 数字字面量
   - 常量治理
   - @op_count 注解
   - G_i 注入点 ledger.inject() 同步
   - MarkerKind 分支检查(SDPL 学习规则)
9. **测试断言只能用 action_id / vocab_id,不查中文/英文**
10. **任何"新公式形态"提议必须先停下问 Claude** —— 12 轮审阅 + 用户两轮哲学深化的终极承诺:**全部 emerge from R/V/P/A/F + 共现学习 + EpistemicSource packet,无新公式**

---

# 第 22 章 最终判断 — 12 轮审阅 + 用户哲学的工程闭环

## 22.1 各 Phase 可达性

| Phase | 对标 | 设计支持度 |
|---|---|---|
| Phase 8 (8.2-8.17) | 18-30 月 + 持续想象 + 跨天意图 + 来源监控 | 🟢 高 |
| Phase 9 backlog | 3-5 岁心智深度 | 🟢 高 |
| Phase 10 | 5-8 岁叙事/因果/心智化 | 🟡 中-高 |
| Phase 11 | 8-12 岁元认知/抽象/计划 | 🟡 中 |
| Phase 12+ | 真实硬件 | 🟢 高 |

## 22.2 12 轮审阅累计修复

- **纪律层(轮 5-7,v9-v11)**:AST PR gate / 常量治理协议 / op_count 注解 / 全部魔数物理外化
- **算法层(轮 1-6,v3-v8)**:ΔP 不爆算 + 不返 0 / context_signature 真定义 / Π update 几何收敛 / 习惯化稳态推导 / novelty residual 秒级保持
- **架构层(轮 5-7,v7-v10)**:27 SA family → 5 types + 16 marker kinds + 类型分组 attention 预算
- **底层补完(轮 8-10,v12-v12.1)**:持续内源性想象 + 自传式回忆 + 延迟意图 + slot packet substrate + 三类注意力 + 反向想象 + 复杂感简单感 + 主观能动性
- **哲学根本升级(轮 11-12,v13-v13.1)**:Source-Differentiated Packet Learning — 想象/真实/听闻/记忆 统一 packet 学习 + 5 EpistemicSource markers + 5 综合 feelings + 自适应稳态

## 22.3 用户两轮哲学完整对齐

| 用户哲学 | v14 落点 |
|---|---|
| "目的不是准确机器而是拟人" | SDPL §5 允许想象犯错,通过后果学会 |
| "想象当成事实进行直觉性推理" | §5.4 packet 学习,想象 packet 有 Q 值 |
| "不能太过分需要自适应稳态" | §5 五机制协同 + AdaptiveTuner 自然趋稳 |
| "真实和想象信号本身可区分" | §5.2 EpistemicSource 5 markers + §10.2 5 feelings |
| "想象和真实作为两件事导致不同后果" | §5.4 Q 表按 packet_key,同 content 异 source 自然分化 |
| "想象信号也有认知范式自然涌现" | §10.2 feelings 经 features 自适应,无预装权重 |
| "经长期学习区分泛化判断能力" | §10.3 18 features + AdaptiveTuner |

## 22.4 终局

设计稿至此真正收尾。**Codex 拿本稿 + apv3_constants.yaml + 4 红线脚本开 Phase 8.2**。

后续 minor issue 在 Phase 实施中 PR 修补 yaml/code,**不再开新设计稿**。

---

— 接手线程,2026-06-17

**12 轮审阅 + 用户两轮哲学深化 = 完整的 APV3 拟人多模态底座设计基础**

可以开工了。
