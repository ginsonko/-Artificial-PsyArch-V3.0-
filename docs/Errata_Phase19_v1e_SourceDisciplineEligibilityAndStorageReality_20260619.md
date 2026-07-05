# APV3.0 Phase 19 v1e Errata — Source Discipline Hardening, Eligibility & Local Error, Cold-Start Concepts, and Storage Reality

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿微修订,叠加在 v1 / v1a / v1b / v1c / v1c-audio / v1d 之上 — **七份合读**。
        **这是开工前最后一份**;通过此份后 Codex 可启动 Phase 19.0b0 实施。
Source: 吸收 Codex v1d 对抗审阅全部 13 项(B1-B6 + S1-S7)+ 我自查 2 项(R_int 量化函数 + tentative concept 的 part 初始化)
Principle: 这一份不动 v1d 大架构,只把 13+2 处"会让 AP 犯非人错误 / 工程实现时炸的接口"全部收紧
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

把 v1d **正确方向上**的 15 处工程接口缝隙钉死 — 锁住 source 边界(B2/B3)、修学习信号梯度(B4/B5)、修存储算术(S1)、补冷启动(S3/S6)、修动态衰减(S4)、补周边运动(S5)、分级多模态融合(S7)、修 Phase 顺序(B6)+ 自查补 $R_{\mathrm{int}}$ 量化 + tentative concept 的 part 关联。

---

## 1. 全部修订清单(13 收 Codex + 2 自查)

| ID | 来源 | 内容 | §X |
|---|---|---|---|
| **B1** | Codex | 听觉维度重新精确闭合 | §2 |
| **B2** | Codex | packet_key 加入 source / substrate / receptor_version | §3 |
| **B3** | Codex | R_sketch 禁止叠 Layer-1 recall;改 remembered_overlay | §4 |
| **B4** | Codex | 学习公式加 eligibility trace | §5 |
| **B5** | Codex | $\nabla_w \mathcal{E}_{\mathrm{cog}}$ 改 ablation 局部差分 | §5 |
| **B6** | Codex | Phase 顺序拆 19.0b0(schema)/ 19.0a / 19.0b1(写入) | §11 |
| **S1** | Codex | Layer-1 存储改 quantized + memmap + indexed | §6 |
| **S2** | Codex | k-medoids 改真 medoid(保留 exemplar id) | §6.3 |
| **S3** | Codex | 冷启动 spawn tentative_concept | §7 |
| **S4** | Codex | Layer-3 floor 动态 = base × source_trust × exp(-recent_corrections) | §8 |
| **S5** | Codex | change blindness 只阻细节纹理,不阻 motion/onset/saliency coarse | §9 |
| **S6** | Codex | 多模态先 temporal event binding 再升 concept | §10 |
| **S7** | Codex | McGurk 分级:phoneme fusion / object arbitration / label hearsay | §10.3 |
| **Self-1** | 自查 | $R_{\mathrm{int}}$ 从 marker / pressure / 共情 标量量化函数 | §5.4 |
| **Self-2** | 自查 | tentative_concept 初始化 Layer-3 part associations | §7.3 |

---

## 2. B1 — 听觉维度重新精确闭合

### 2.1 v1d 错算暴露

v1d §2.1 写 `audio_feature_dim = 30497`,但 v1c-audio 原始算式是:

$$
20179 - 16378 + 26700 = 30501
$$

这个 30501 **本身已是 A0..A8 feature 全总维度**,**没说**含 canvas state。v1d 直接 -4 缺根据。

### 2.2 v1e 精确闭合(A0..A8 重新逐项算)

| 通道 | 单 frame 维度 | Frame 数 (1 sec, hop=64) | 子总 |
|---|---:|---:|---:|
| A0 cochlear pyramid 25 tiles × 32 × 32 | 32 × 32 | 25 tiles | **25600** |
| A0 tile phase summary | 2 | 25 | 50 |
| A0 整段 onset salience hi-time | 1 | 250 | 250 |
| A0 整段 F0 + voicing hi-time | 2 | 250 | 500 |
| A0 time-freq cross-layer correlation | — | 300 | 300 |
| **A0 子总** | | | **26700** |
| A1 MFCC + Δ + ΔΔ | 39 | 50 (低 time-res frames) | 1950 |
| A2 Chroma | 12 | 50 | 600 |
| A3 spectral 4-moment | 4 | 50 | 200 |
| A4 ZCR | 1 | 50 | 50 |
| A5 onset 8-bin + 1 BPM | 9 | 50 + 1 | 401 |
| A6 F0 + voicing(low-res frames) | 2 | 50 | 100 |
| A7 RMS multi-scale | 3 | 50 | 150 |
| A8 spectral contrast 7-band | 7 | 50 | 350 |
| **A1..A8 子总** | | | **3801** |
| **audio_receptor_feature_dim** | | | **30501** |

锁:
```yaml
audio_sensor:
  audio_receptor_feature_dim: 30501       # @structural - 精确闭合
  audio_canvas_state_dim: 4               # @structural - 独立存储(同视觉)
  audio_render_audit_dim: 8               # @structural - 独立存储
```

audio_receptor_feature_dim 与 audio_canvas_state_dim、audio_render_audit_dim 三者**分离存储**,不再混。

---

## 3. B2 — packet_key 加入 source / substrate / receptor_version

### 3.1 v1d 错误暴露

v1d §2.1 写 "packet_key 只依赖 sensory_feature_block,canvas/render 仅 audit" — 漏了 source/substrate/version。同一视觉内容的 PERCEIVED / IMAGINED / REMEMBERED / INFERRED **会撞同一 packet_key**,污染前面 v1a/v1b 守住的 source 分离。

### 3.2 v1e 修正

```python
packet_key = sha256(
    sensory_feature_signature,           # opaque hash of (V0..V9) or (A0..A8)
    epistemic_source,                     # PERCEIVED / IMAGINED / REMEMBERED / INFERRED
    substrate,                            # EXTERNAL_VISUAL / SELF_DRAFT_GRID / AUDIO_INPUT / etc.
    receptor_version,                     # v1: phase19_0_substrate, v2: phase19_0a_foveated
).hex()
```

**红线**:

```
RL-19v1e-B2-01: packet_key 必须含全部 4 个字段
                grep test: packet_key 不接 4 元组 → fail
RL-19v1e-B2-02: 同 sensory_feature_signature 不同 epistemic_source 必产生不同 packet_key
                单测覆盖
RL-19v1e-B2-03: canvas_state_block / render_audit_block 必须 audit-only,不进 packet_key
```

continuation 接 v14 既有 SDPL packet 设计 — v14 packet 已经有 substrate 字段;v1e 把 epistemic_source 也升为 first-class。

---

## 4. B3 — R_sketch 禁叠 Layer-1 recall,改 remembered_overlay

### 4.1 v1d 错误暴露

v1d §4.1 R_sketch 写 "可选叠加 Layer-1 召回的相似 episodic vectors 的 canvas"。这会让 AP 把"我想起的苹果纹理"当成"我眼前看见的纹理" — source confusion(违反 v1a B1 核心红线)。

### 4.2 v1e 三层 overlay 显式分离

```
SensoryCanvas               source = PERCEIVED_SENSORY_SKETCH
       ↑
       │ 只从当前感受器输入 + clarity + source_reliability 更新

RememberedOverlay            source = REMEMBERED_SKETCH
       ↑
       │ 从 Layer-1 召回的相似 episodic 渲染,作为独立画布

PredictionOverlay            source = INFERRED_SKETCH
       ↑
       │ 从 Layer-3 expected ConceptPrototype 走 R_proto,作为独立画布
```

每一层是独立 family / 独立 state SA。展示页可以三层叠加显示(给人看),audit 必须能单独关闭。

### 4.3 v1d §4.1 重写

```python
def R_sketch(canvas: SensoryCanvas, target_size: int) -> tuple[Image, Image, Image]:
    """
    严格只产 PERCEIVED sensory_sketch 一张图。
    不读取 Layer-1。
    不读取 Layer-3。
    红线 RL-19v1e-B3-01: grep test, R_sketch 函数体不可调用 layer1_b_recall / layer3_lookup
    """
    sketch = bilinear_render(canvas.canvas_pixels, target_size)
    return sketch  # source=PERCEIVED_SENSORY_SKETCH


def R_remembered(query_input_trace_hash, target_size: int) -> Image:
    """
    REMEMBERED 模式:从 Layer-1 召回与当前感受相似的 episodic instances,
    取它们的 canvas snapshot,合成 remembered_overlay。
    红线 RL-19v1e-B3-02: 输出必为 source=REMEMBERED_SKETCH
    """
    similar = layer1_b_recall(query_input_trace_hash, top_k=5)
    return blend_canvases([s.canvas_snapshot for s in similar], target_size)


def R_prediction(top_concepts, target_size: int) -> Image:
    """
    INFERRED 模式:走 R_proto 但显式标记为 prediction overlay。
    红线 RL-19v1e-B3-03: 输出必为 source=INFERRED_SKETCH
    """
    return R_proto(top_concepts[0].concept_uuid, target_size)  # source 在 metadata 改
```

### 4.4 新 SA 族

```python
StateItem(
    sa_id=f"inner_picture::perceived::<input_trace_hash>::{tick}",
    family="inner_picture",
    source="reconstruction_R_sketch",
    epistemic_source="PERCEIVED_SENSORY_SKETCH",
    ...
)
StateItem(
    sa_id=f"inner_picture::remembered::<query_hash>::{tick}",
    family="inner_picture_remembered",                # 独立 family
    source="reconstruction_R_remembered",
    epistemic_source="REMEMBERED_SKETCH",
    ...
)
StateItem(
    sa_id=f"inner_picture::predicted::<concept_uuid>::{tick}",
    family="inner_picture_prediction",                # 独立 family
    source="reconstruction_R_prediction",
    epistemic_source="INFERRED_SKETCH",
    ...
)
```

### 4.5 红线

```
RL-19v1e-B3-04: SensoryCanvas 更新公式中 source_reliability 不允许取自任何 overlay
RL-19v1e-B3-05: 任意 audit 必能分别开关三层显示
RL-19v1e-B3-06: 反馈削弱不许跨层污染(REMEMBERED 错不削 PERCEIVED 权重)
```

---

## 5. B4 + B5 — Eligibility Trace + Ablation 局部差分

### 5.1 v1d 错误暴露

v1d §8 公式:
$$
\Delta w = \eta \left[\alpha_R R_{\mathrm{net}} - \alpha_E \nabla_w \mathcal{E}_{\mathrm{cog}}\right]
$$

两处问题:
- $R_{\mathrm{net}}$ 是**全局标量**,直接乘 $\Delta w$ → 所有当前激活线索(包括背景、误召回碎片、偶然颜色)一起加固。非人。
- $\nabla_w \mathcal{E}_{\mathrm{cog}}$ — R_proto 含 stamping / codebook lookup / noisy-OR / association,**不可微**。写连续梯度会变伪梯度。

### 5.2 v1e 修正(eligibility + local ablation)

逐 $i$(每个 weight,如 part 关联 $w_{\mathrm{part}}(p, c)$ 或 source contribution $w_{\mathrm{source}}(s, c)$):

$$
\boxed{
\Delta w_i = \eta \cdot e_i \cdot \mathrm{credit}_i \cdot \left[\alpha_R \cdot R_{\mathrm{net}} - \alpha_E \cdot L_i\right]
}
$$

各项:

- **$e_i$ — eligibility trace**(谁参与了决策):

$$
e_i(t) = \mathrm{contribution\_to\_Conf}_i(t) \cdot \lambda^{t - t_{\mathrm{last\_active}}(i)}
$$

- contribution_to_Conf$_i$ — 该 part / source 对当前决策的 Conf 贡献(用 noisy-OR 偏导近似)
- $\lambda$ — eligibility decay,`learning.eligibility_lambda = 0.85` @experimental
- $t_{\mathrm{last\_active}}(i)$ — 该 $i$ 最近一次参与决策的 tick

- **credit$_i$**(继承 v1b §3.2):

$$
\mathrm{credit}_i = \frac{\omega_i \cdot \sigma_i}{\sum_j \omega_j \sigma_j}
$$

- **$L_i$ — local error via ablation**(B5 修):

$$
L_i = \mathcal{E}_{\mathrm{cog}}(\text{with } w_i \text{ active}) - \mathcal{E}_{\mathrm{cog}}(\text{with } w_i \text{ ablated})
$$

如果 ablate $i$ 后 $\mathcal{E}_{\mathrm{cog}}$ 下降 → $L_i > 0$ → 该 $i$ 在害事 → $-\alpha_E L_i$ 给 $\Delta w$ 减分。

实施细节:每 update 周期(N=10 tick)只对 top-K active weights 算 ablation(不全维),`learning.ablation_top_k = 16` @experimental。

### 5.3 新红线

```
RL-19v1e-B4-01: 学习公式必含 eligibility_i,Δw 不允许 = η · R_net (无 e_i)
RL-19v1e-B5-01: ∇w E_cog 不允许写出来,只能 L_i = E_cog_active - E_cog_ablated
RL-19v1e-B5-02: ablation 每周期最多对 top-K active weights 做,K 由 constant 限
RL-19v1e-B4-02: 未参与决策的 weights(e_i = 0)不允许被 R_net 加固
```

### 5.4 自查 Self-1 — $R_{\mathrm{int}}$ 量化函数

v1d §8.2 写 $R_{\mathrm{int}}$ 来自 MISMATCH marker / cognitive_pressure / Phase 9.6 共情,但**没说怎么量化**。v1e 补:

```python
def R_int_from_internal_signals(state_pool, current_concept_uuid, tick) -> float:
    """
    AP-native R_int 量化函数:
    把内部既有 marker / pressure / 共情转成 [-1, 1] 标量。
    """
    # 1. 期待匹配:期待画面与感知画面差 → 越接近匹配越正
    pred_canvas = get_prediction_overlay(current_concept_uuid)
    sens_canvas = get_sensory_canvas()
    match_score = -channel_wise_distance(pred_canvas, sens_canvas) / norm_factor
    r_match = clip(match_score, -1, 1)

    # 2. 违和感:MISMATCH marker 强度
    mismatch_intensity = sum(
        m.intensity for m in state_pool.markers
        if m.kind == "MISMATCH" and m.referenced_concept == current_concept_uuid
    )
    r_conflict = -tanh(beta_conflict * mismatch_intensity)

    # 3. 期待压力释放:cognitive_pressure 下降速率
    pressure_delta = state_pool.cognitive_pressure - state_pool.last_tick_pressure
    r_release = clip(-pressure_delta * beta_release, -1, 1)
    # 若 pressure 显著下降(决策出来),释放正向

    # 4. 共情 trust modulation:用户语气强烈/温和 调 r_ext 接收强度(不直接进 r_int)
    # 见 §10 多模态绑定的 reliability 权重

    return (rho_match * r_match
            + rho_conflict * r_conflict
            + rho_release * r_release) / (rho_match + rho_conflict + rho_release)
```

`learning.beta_conflict = 0.5` @experimental
`learning.beta_release = 0.3` @experimental
`learning.rho_match = 0.3, rho_conflict = 0.5, rho_release = 0.4` @experimental(与 v1d §8.2 锁同)

---

## 6. S1 + S2 — 存储算术修正 + medoid 真实化

### 6.1 v1d 错算

v1d §12 写 "1 万实例 × 30 MB = 300 MB"。实际:

$$
27838 \text{ 维} \times 4 \text{ byte (float32)} \approx 111 \text{ KB / 实例}
$$

1 万实例 = 1.1 GB **仅视觉 feature**,加 canvas/metadata/索引会更高。如果真是 30 MB / 实例 → 1 万 = 300 GB。

### 6.2 v1e 存储设计

```yaml
storage:
  layer1_quantization: "uint8_pca_signature"  # @structural
                                              # full feature dim too big
                                              # use 256-dim uint8 PCA signature
                                              # for retrieval; full vec audit-only
  layer1_full_vec_kept_ratio: 0.05            # @scenario_tuneable
                                              # 只对前 5% 高 importance 实例保留 full vec
  layer1_signature_dim: 256                   # @structural - PCA 到 256 维 uint8
  layer1_signature_dtype: "uint8"             # @structural - 0.25 KB / signature
  layer1_storage_format: "memmap_npz_shard"   # @structural
  layer1_shard_size_instances: 1000           # @structural
  layer1_max_instances_default: 10000         # @scenario_tuneable
  layer1_full_vec_path: "data/layer1/full/"   # @structural
  layer1_signature_path: "data/layer1/sig/"   # @structural

  layer2_quantization: "float16"              # @structural
  layer3_quantization: "float16"              # @structural
```

**实际占用**:

- 10 k signature × 256 dim × 1 byte = 2.5 MB(召回常驻)
- 500 full vecs (5% × 10 k) × 27838 × 4 byte = 55 MB(audit 用,memmap)
- 10 k metadata × 2 KB = 20 MB
- **Layer-1 总常驻** ≈ 78 MB(原 v1d 估的 300 MB 错算修正)
- Layer-2 codebook 10 KB × 1024 entries = 10 MB
- Layer-3 association 50 MB
- **三层常驻** ≈ 140 MB,**家用机轻松**

### 6.3 B 召回 / C 召回适配 quantized

```python
def C_recall_visual(query_signature_256_uint8):
    """ 倒排索引:每个 part_uuid 映射到一组 concept_uuid """
    # 1. 从 query signature 提取 part hashes (查 LBP / V7 codebook)
    # 2. 倒排索引 lookup → 候选 concepts
    # 200 μs (only signature math, no full vec)


def B_recall_visual(query_full_vec, candidate_concepts):
    """ 精算只对 candidate concepts 的 5% full-kept 实例做 """
    candidates = []
    for c in candidate_concepts:
        episodics = layer1_lookup_full_kept_for(c)  # may be 0~10
        for ep in episodics:
            full_vec = memmap_load(ep.full_vec_path)  # disk read
            candidates.append(compute_humanlike_conf(query_full_vec, full_vec))
    return rank(candidates)
```

### 6.4 v1d "k-medoids" → 真 medoid(S2 修)

```python
def layer2_online_update(channel, new_patch, exemplars):
    """
    Layer-2 codebook 用真 medoid:
    - 每个 codebook entry 是真实样本的 patch (不是 EMA mean)
    - 新 patch 进来:找最近 medoid;若距离 > theta_new_medoid 则提议
      新 medoid (该新 patch 直接作为新 exemplar)
    - 若容量满:替换最少使用的 medoid
    - EMA 只用于内部跟踪 cluster center,但每隔 N 次 update,
      把 medoid 重置为最接近 EMA center 的 真实 exemplar
    """
    # medoid 总是某个 exemplar 的 id,不是合成 vec
    pass
```

`storage.layer2_medoid_recheck_every_n_updates = 50` @experimental
`storage.layer2_eps_new_medoid = 0.4` @experimental

**Audit 关键**:可以追溯每个 codebook entry 到具体训练样本 id,证明 codebook 没"凭空生成"。

---

## 7. S3 + Self-2 — 冷启动 tentative_concept

### 7.1 v1d 缺陷暴露

v1d §3.2 C 召回流程:Layer-2 parts → Layer-3 association → concept。但新物体第一次出现,**Layer-3 没该 concept**,C 召回返回空 → 系统无候选,只能 no_call。

人类看到陌生东西也会说"像某种圆形水果"或形成"临时印象",不是空返回。开放对话底座必须有这条路径。

### 7.2 v1e 冷启动逻辑

```python
def C_recall_visual_v1e(query_signature):
    candidate_parts = layer2_match_parts(query_signature)  # 总能匹配若干 parts
    if not candidate_parts:
        # 完全没匹配上任何已知 parts → 真新奇 → 升 ν_object
        return [], ColdStartReason.NO_KNOWN_PART

    # 倒排查 Layer-3 中 known concept
    candidate_concepts = layer3_lookup_by_parts(candidate_parts, top_k=5)

    if not candidate_concepts:
        # parts 已知但无 known concept 联想 → 冷启动新概念
        tentative_uuid = spawn_tentative_concept(
            initial_part_associations=candidate_parts,    # Self-2: 初始 part 关联
            epistemic_source="PERCEIVED_UNNAMED",
            spawn_reason=ColdStartReason.NEW_CONCEPT,
            tick=current_tick,
        )
        return [TentativeConcept(tentative_uuid)], ColdStartReason.NEW_CONCEPT

    return candidate_concepts, ColdStartReason.NONE
```

### 7.3 Self-2 — tentative_concept 在 Layer-3 的初始 part associations

新 spawn 的 tentative concept 不是空 — 它带着 C 召回当时激活的 part_uuids 作为初始关联:

```python
def spawn_tentative_concept(initial_part_associations, ...):
    tentative_uuid = generate_opaque_uuid()
    Layer3.add_concept(tentative_uuid, {
        "is_tentative": True,
        "spawn_tick": current_tick,
        "initial_parts": initial_part_associations,  # 关键:从 C 召回带来
        "part_weights": {p.uuid: p.activation_score for p in initial_part_associations},
        "vocab_associations": [],                    # 暂无中文名
        "epistemic_source": "PERCEIVED_UNNAMED",
        "lifetime_observations": 1,
    })
    return tentative_uuid
```

### 7.4 tentative concept 的后续命运

- 多次相似输入 → tentative concept 的 part_weights 增加,observation 累积
- 教师标注("这是某某") → vocab_associations 关联中文名 → tentative_flag 移除
- 长期没相似输入 → tentative concept 衰减到 Layer-3 floor 以下 → 移除

```yaml
concept:
  tentative_promotion_min_observations: 5  # @experimental
  tentative_decay_tau_ticks: 1000          # @experimental
  tentative_floor: 0.05                    # @structural
```

### 7.5 红线

```
RL-19v1e-S3-01: tentative_uuid 是 opaque uuid,不含类别名 / "tentative" 标签 / 文件名
RL-19v1e-S3-02: tentative concept 在 R_proto 时仍走 §4 R_proto(用其 part_weights 合成)
                它能产生"看起来像某种水果"的内心画面,即使没有中文名
RL-19v1e-S3-03: tentative concept 不允许参与 held-out evaluation 作为 ground truth
```

### 7.6 输出文本生成

当 top-1 是 tentative concept,通过 Phase 16 styled corpus 走"模糊指代":
- decision_tier = soft + 主要部件像水果 → "像是某种圆形水果"
- decision_tier = ambig → "可能是水果"

这就是 Codex 说的"像人一样形成临时印象"。

---

## 8. S4 — Layer-3 floor 动态化

### 8.1 v1d 缺陷

v1d 写 `layer3_weight_floor = 0.3`,所有场景固定。反复被纠错的概念仍会顽固影响判断。

### 8.2 v1e 动态 floor

$$
\boxed{
\mathrm{floor}_c = \mathrm{base\_floor} \cdot \mathrm{source\_trust}_c \cdot \exp\left(-\beta_{\mathrm{corr}} \cdot N_{\mathrm{recent\_corrections}}(c)\right)
}
$$

各项:
- `base_floor = 0.3` @structural(同 v1d)
- $\mathrm{source\_trust}_c$:来自 Phase 8 trust_promoted gate,范围 $[0.5, 1.0]$
- $N_{\mathrm{recent\_corrections}}(c)$:最近 100 tick 该 concept 上的 "不对" 反馈次数
- `learning.beta_corr = 0.3` @experimental → 3 次纠错衰减到 ~40%

例:
- 新 concept 从教师 trust 高源得来,无纠错 → floor = 0.3 × 1.0 × 1 = 0.3
- 同 concept 被纠错 5 次 → floor = 0.3 × 1.0 × $e^{-1.5}$ ≈ 0.067
- 同 concept 被纠错 10 次 → floor ≈ 0.015,几乎不再影响判断

冲突极高时 floor 可降到接近 0:

```python
if mismatch_marker_intensity(c) > extreme_threshold:
    floor_c = min(floor_c, 0.05)
```

### 8.3 新红线

```
RL-19v1e-S4-01: layer3_weight_floor 必须为 callable,接受 concept_uuid → 动态返回
                不允许写 .layer3_weight_floor = 0.3 这种静态常量调用
```

---

## 9. S5 — change blindness 区分细节 vs 运动/onset/saliency coarse

### 9.1 v1d 缺陷

v1d §9.7 写 "clarity < 0.3 区不更新 PerceptVector"。这阻断了周边运动检测 — 但人类周边视觉对运动**极**敏感。

### 9.2 v1e 拆分

```python
def should_update_layer1_for_pixel(clarity_at_pixel):
    """ 细节纹理只在 clarity 高时更新(change blindness for detail) """
    return clarity_at_pixel >= clarity_min_for_detail_update  # 0.3

def should_update_motion_onset_for_pixel(clarity_at_pixel):
    """ 运动/onset/coarse saliency 即使周边低 clarity 也更新 """
    return clarity_at_pixel >= clarity_min_for_motion_update  # 0.05 (基本只要不是死角都更新)

def should_trigger_attention_for_pixel(motion_magnitude, onset_strength):
    """ 强运动/强 onset 触发 saccade 拉回注意 """
    return motion_magnitude > motion_threshold or onset_strength > onset_threshold
```

```yaml
vision_sensor:
  clarity_min_for_detail_update: 0.3       # @structural - 细节纹理 / V3 LBP / V7 parts
  clarity_min_for_motion_update: 0.05      # @structural - 运动 / onset / coarse saliency
  motion_threshold: 0.4                    # @experimental - 周边运动触发 saccade
  onset_threshold: 0.5                     # @experimental
```

### 9.3 实现注意

motion channel 在 Phase 19.0a 留 stub(返回 0),Phase 19.6 active perception 时才真正用 — 但接口提前预留,避免未来再改。

---

## 10. S6 + S7 — 多模态绑定路径修正

### 10.1 v1d 循环依赖暴露(S6)

v1d §9.9 写 "视觉和音频若激活同 concept,且时间接近,则 association 加强" — 但**早期没有 concept**,这是循环依赖。

### 10.2 v1e — 先 temporal event binding,再升 concept

```python
def temporal_event_bind(tick_now, *modal_percepts):
    """
    在 concept 形成 之前,先按时间窗口绑定:
    - 多个 modal_percept 在 binding_window 内同 tick 进来 → 共享 temporal_event_uuid
    - temporal_event_uuid 是 opaque,带 source markers
    - 之后若反复出现相似多模态共现,promotes 为 ConceptPrototype
    """
    if len(modal_percepts) < 2:
        return None
    if max(p.tick for p in modal_percepts) - min(p.tick for p in modal_percepts) > binding_window_ticks:
        return None
    event_uuid = generate_opaque_uuid()
    Layer3.add_temporal_event(event_uuid, {
        "vision_percept_uuid": next((p.uuid for p in modal_percepts if p.modal == "vision"), None),
        "audio_percept_uuid": next((p.uuid for p in modal_percepts if p.modal == "audio"), None),
        "text_vocab_sa_id": next((p.sa_id for p in modal_percepts if p.modal == "text"), None),
        "tick_window": (min(p.tick for p in modal_percepts), max(p.tick for p in modal_percepts)),
        "lifetime_cooccurrence_count": 1,
    })
    return event_uuid


def promote_event_to_concept(event_uuid):
    """ 反复共现 N 次后,把 temporal event 升级为 ConceptPrototype """
    event = Layer3.get_temporal_event(event_uuid)
    if event.lifetime_cooccurrence_count >= concept_promotion_threshold:
        concept_uuid = spawn_concept_from_event(event)
        Layer3.add_concept_association(concept_uuid, event)
        return concept_uuid
```

```yaml
multimodal:
  binding_window_ticks: 6                       # @experimental (0.6 秒,人类多模态同步窗口)
  concept_promotion_threshold: 4                # @experimental - 4 次共现升 concept
  temporal_event_decay_tau_ticks: 500           # @experimental
```

### 10.3 S7 — McGurk 分级融合(不能泛化到所有概念)

```python
def multimodal_decision(visual_conf, audio_conf, text_conf, level):
    """
    分级:
      level = "phoneme":       speech phoneme/口型层 → reliability-weighted fusion (McGurk-like)
      level = "object":        object/category → conflict arbitration (取最高可信)
      level = "label":         text label → hearsay trust × source weight
      level = "generic":       同构特征空间 → reliability-weighted average
    """
    if level == "phoneme":
        # 真 McGurk fusion
        return weighted_average_by_reliability(visual_conf, audio_conf, ...)

    if level == "object":
        # 不平均,arbitration / confirmatory boost only
        conflict_intensity = abs(visual_conf - audio_conf)
        if conflict_intensity > conflict_arbitration_threshold:
            # 选 reliability 高的
            chosen = max([visual_conf, audio_conf, text_conf], key=lambda c: c.reliability)
            return chosen, source="ARBITRATED"
        else:
            # 低冲突只允许"互相确认"式 boost,不允许类别平均成混合物体.
            chosen = max([visual_conf, audio_conf, text_conf], key=lambda c: c.reliability)
            boosted = confirmatory_boost(chosen, supporting=[visual_conf, audio_conf, text_conf])
            return boosted, source="MULTIMODAL_AGREED"

    if level == "label":
        # 文本类别走 hearsay,不直接融合到视觉感知
        return text_conf * hearsay_source_trust  # 仅 boost,不替代

    raise ValueError(f"Unknown fusion level: {level}")
```

```yaml
multimodal:
  conflict_arbitration_threshold: 0.4          # @experimental
  hearsay_source_trust_base: 0.6                # @experimental
```

### 10.4 红线

```
RL-19v1e-S6-01: 多模态绑定必走 temporal_event → 反复共现 → ConceptPrototype 路径
                不允许"两模态激活同 concept 时加强"的循环
RL-19v1e-S7-01: object/label 层禁止用 weighted_average,只允许 arbitration / hearsay
                单测覆盖 (苹果图 + 香蕉语音 → 不输出"混合水果")
RL-19v1e-S7-02: object 层低冲突也只允许 confirmatory_boost(max-reliability choice),
                不允许 weighted_average;低冲突表示"互相确认",不是"融合成混合类别"
```

---

## 11. B6 — Phase 19.0b 拆分 + receptor_version

### 11.1 问题

v1d 顺序:**19.0b 建库 → 19.0a 修 foveated**。但 19.0b 存 v1 V0..V9,19.0a 改 schema,旧数据要迁移。

### 11.2 v1e 拆分

```
Phase 19.0  (substrate ✓) — 已落地 v1 schema (旧 V0..V9, 7807 维)

Phase 19.0b0 (vector substrate schema)
   - 实现 Layer-1/2/3 类与接口
   - 持久化 schema with receptor_version field
   - 暂不写入实际 PerceptVector(待 19.0a 完成新 schema)
   - 测试 schema / 持久化 / B-C 召回算法骨架

Phase 19.0a  (foveated visual repair)
   - 实现 v1c §2-6 foveated sampling + ClarityField + SensoryCanvas + R_sketch / R_proto
   - 固化 visual_feature_v2 (27838 维新 schema with V0 升级)
   - 标记 receptor_version = "phase19_0a_foveated"

Phase 19.0b1 (vector substrate population)
   - 把 Phase 17/18 训练样本走 v2 感受器 → Layer-1 写入
   - 在线 k-medoids 构 Layer-2 codebook
   - 教师标注样本 → Layer-3 concept associations
   - 红线 RL-19v1e-B6-01: Layer-1 写入只接受 receptor_version >= phase19_0a_foveated
                          旧 v1 版本数据不进 Layer-1
```

### 11.3 receptor_version 字段

```python
@dataclass(frozen=True)
class PerceptVector:
    vector_uuid: str
    signature: np.ndarray  # 256 dim uint8
    full_vec_path: Optional[Path]  # may be None for not-kept
    epistemic_source: str
    substrate: str
    receptor_version: str  # 如 "phase19_0a_foveated"
    tick_acquired: int
    importance: float
    metadata: dict
```

### 11.4 受影响的 Gate

```
RL-19v1e-B6-01: 各 Phase 19 gate 必须明确 receptor_version 要求
RL-19v1e-B6-02: 不同 receptor_version 的 vector 不可混入同一 Recall@K 评估
```

---

## 12. 新 Deliverable Gates

### Phase 19.0b0(向量库 schema,新)

| Gate |
|---|
| G-19.0b0-01 Layer-1/2/3 类与接口实现 |
| G-19.0b0-02 持久化 schema with receptor_version |
| G-19.0b0-03 B 召回 / C 召回算法骨架(暂可返回 mock data) |
| G-19.0b0-04 单测覆盖每个 store 的 CRUD |
| G-19.0b0-05 红线 RL-19v1e-B1/B2/B6 全过 |
| G-19.0b0-06 治理 + 真名审计 |

### Phase 19.0a v1e 增量

| Gate |
|---|
| G-19.0a-v1e-30 R_sketch 不读 Layer-1 / Layer-3(grep + 流程测) |
| G-19.0a-v1e-31 R_remembered / R_prediction 三层独立 SA |
| G-19.0a-v1e-32 周边低 clarity 区运动/onset 仍触发 saccade 拉回(单测) |
| G-19.0a-v1e-33 packet_key 含 source/substrate/receptor_version(单测撞键) |

### Phase 19.0b1(向量库写入,新)

| Gate |
|---|
| G-19.0b1-01 Phase 17/18 训练样本走 v2 感受器 → Layer-1 |
| G-19.0b1-02 在线 k-medoids 构 Layer-2,1024 entries 实现 |
| G-19.0b1-03 每个 codebook entry 可追溯真实 exemplar id(S2 medoid) |
| G-19.0b1-04 教师标注 → Layer-3 concept associations |
| G-19.0b1-05 Layer-1 quantized signature + full vec 5% 保留 |
| G-19.0b1-06 实际内存占用 < 200 MB 常驻(S1 实测) |

### Phase 19.5 v1e 重写(eligibility + local error)

| Gate |
|---|
| G-19.5-v1e-01 eligibility_i 公式实现 |
| G-19.5-v1e-02 local_error_i = E_cog(active) - E_cog(ablated) 实现 |
| G-19.5-v1e-03 每周期 ablation 限 top-K = 16 |
| G-19.5-v1e-04 未参与决策的 weights(e_i=0)R_net 不加固(单测) |
| G-19.5-v1e-05 5 次纠错后 floor 衰减到 < 0.07 |
| G-19.5-v1e-06 tentative concept 5 次共现升级 |
| G-19.5-v1e-07 多模态 phoneme/object/label 三级融合分别测 |
| G-19.5-v1e-08 R_int 量化函数 self-1 实现:期待匹配/违和/释放分别测 |

---

## 13. 新落地顺序

```
19.0  (substrate ✓)
  ↓
19.0b0 (向量库 schema,新)
  ↓
19.0a  (foveated visual repair, 锁 receptor_version)
  ↓
19.0b1 (向量库 真实写入)
  ↓
19.2  (拟人 Conf)
  ↓
19.3a → 19.3b
  ↓
19.1  → 19.1a  → 19.4a → 19.4b
  ↓
19.5  (eligibility + ablation + 动态 floor + tentative + 多模态绑定)
  ↓
19.6  (active perception, motion channel)
```

---

## 14. 边界

- v1e 不动 v1d 大架构,只闭合 13+2 处接口
- tentative concept 在 Phase 19.0b0 留 spawn 接口,Phase 19.0b1 实测能 spawn,Phase 19.5 接管学习信号
- motion channel 在 Phase 19.0a 留 stub,Phase 19.6 真实启用
- 听觉 echoic 4 秒硬墙不变(继承 v1c-audio + v1d §2.10)
- McGurk 测试在 Phase 19.4b 之后做

---

## 15. 总检查清单(v1+v1a+v1b+v1c+v1c-audio+v1d+v1e 七份合读后)

- [ ] 视觉 feature_dim = 27838,canvas_state_dim = 4 独立
- [ ] 听觉 receptor_feature_dim = 30501,canvas_state_dim = 4 独立
- [ ] packet_key 含 sensory_signature + epistemic_source + substrate + receptor_version
- [ ] R_sketch 不读 Layer-1 / Layer-3
- [ ] R_remembered / R_prediction 三 family 独立
- [ ] 学习公式含 eligibility_i + credit_i + local_error_i
- [ ] $\nabla \mathcal{E}_{\mathrm{cog}}$ 全部改 ablation
- [ ] Layer-3 floor 动态:base × source_trust × exp(-β × N_corr)
- [ ] Layer-1 quantized signature uint8 256 dim + 5% full vec
- [ ] Layer-2 真 medoid(可追溯 exemplar id)
- [ ] 冷启动 tentative_concept spawn + Layer-3 初始 part 关联
- [ ] 多模态先 temporal_event 后 concept promotion
- [ ] McGurk 分级:phoneme fusion / object arbitration / label hearsay
- [ ] change blindness 只阻细节,不阻 motion/onset
- [ ] Phase 19.0b0 / 19.0a / 19.0b1 拆三步,receptor_version 守迁移
- [ ] 真名零命中

---

## 16. 署名

- 原架构设计:银子老师(笔名)
- v1e 修订:Claude (Anthropic) 在 Codex v1d 对抗审阅 13 项 + 自查 2 项基础上产出
- 落地:Codex 在 v1e 通过最终复核后启动 Phase 19.0b0

End of Phase 19 v1e Errata.
