# APV3.0 Phase 19 v1a Errata — Anthropomorphic Corrections + Engineering Closure

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿修订(errata),不替换 v1 设计稿,叠加在其上。落地时以 v1 + v1a 两份合读。
Source: 吸收 [AdversarialReview v1](AdversarialReview_APV3_Phase19_ReceptorConfidence_v1_20260619.md) 中**纯工程严谨**项 + [AdversarialReview v2](AdversarialReview_APV3_Phase19_ReceptorConfidence_v2_Anthropomorphic_20260619.md) 拟人化方向的全部 blocker / serious 项
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

把 Phase 19 v1 设计稿按"**AP 是拟人系统,不是绝对正确机器**"的原则修订一遍 — 允许 AP 像人一样从碎片线索脑补出典型苹果/橙子/香蕉(这是拟人的核心能力,**不是 bug**),但要求 AP **知道这是想的还是看到的**;同时把 v1 三处真正的工程不闭合(维度数学、noisy-OR 饱和、margin 在 top1=top2 给 0.5)修死。

**核心修订原则**:

> 设计问题不是 "AP 可能错",而是 "AP 错得不像人,或者它不知道自己错在哪一类(感知 / 想象 / 推理 / 听说)"。

---

## 1. v1 与 v2 审阅吸收清单(逐条裁定)

| 审阅项 | 来源 | 裁定 | v1a 处理 |
|---|---|---|---|
| 重建 = 信息充分性证明? | v1 B1 + v2 corrected | **v2 对**:重建是"感知/想象草图审计",不是客观正确性证明 | §2 改名 + 引入 source mode |
| 维度数学不闭合 | v1 B2 | **真工程 bug** | §3 闭合 schema |
| Noisy-OR 9 通道 0.2 → 0.866 误饱和 | v1 B3-P1 + v2 B3-P1 | **真 bug**(不是正确性,是公式行为不拟人) | §4 改 thresholded top-m |
| 一致性反向惩罚少强线索 | v1 B3-P2 + v2 B3-P2 | **真 bug** | §4 改 active-cue only |
| Margin 在 top1=top2 给 0.5 | v1 B3-P3 | **真 bug** | §4 改 shifted margin |
| Diagnosticity 忽略最近竞争 | v1 B3-P3 | **真 bug** | §4 改 nearest-negative |
| OOD 强制 no_call 不拟人 | v2 B3-P3 | **v2 对** | §4 改降级而非 force no_call |
| 19.3 混淆 train/heldout 与 clean→real 两种 | v1 B4 + v2 corrected | **v1 工程拆分对**,**v2 解释方式对**(失败 = 拟人发展限制,不是无效) | §5 拆 19.3a / 19.3b,失败定性按 v2 |
| 前景分割是隐藏前提 | v1 S1 | **真工程** | §3 闭合分割算法 + 多假设 mask + Q 因子 |
| STOI 不适合非语音 | v1 S2 + v2 S4 | **对** | §6 听觉按声音家族分指标 |
| Inner voice 不能宣称 TTS | v1 S2 + v2 S4 | **对** | §6 改名 `inner_voice_sketch` |
| 渲染需 source marking | v1 S3 + v2 B1 | **v2 升级为核心 blocker** | §2 强制 `render_mode` + `epistemic_source` |
| Percept-retrieval 不能只靠重建 | v1 S4 + v2 S3 | **对** | §7 加 Recall@K + family resemblance |
| 12 张图不够全证 | v1 S5 | **v2 修正**:作为 Phase 19 内部诊断集合理,不当全证 | §5 措辞,不变规模 |
| 错误分类法 (人类可信 vs 非人) | v2 S1 | **关键拟人** | §8 错误 taxonomy |
| Source confusion 是非人错误 | v2 B1 | **关键拟人** | §2 + §8 强制源分离 |
| V0 高带宽空间通道 | v2 B2(v1 B1 同义) | **关键** | §3 加 V0 foveated retinal pyramid |
| 公式改 `prototype_pull × coherence × competitor_gap × source_quality × novelty_tension` | v2 B3 | **关键拟人重写** | §4 全部按 v2 重写 |
| 反馈对 source-specific 修正 | v2 final | **关键** | §9 加 feedback gate |

---

## 2. 双模式渲染 + 源标记(吸收 v2 B1 + v1 S3)

### 2.1 渲染算子分两种模式

把 v1 的"反向重建算子 $\mathcal{R}$"明确拆为**两种 render mode**,共享底层 primitives,但语义不同:

$$
\mathcal{R}_{\mathrm{sketch}}: \mathbf{f}_x \to \hat{I}_{\mathrm{sketch}} \quad \text{(感知草图,只从该图本身的 V0+V1..V9 traces 出发)}
$$

$$
\mathcal{R}_{\mathrm{proto}}: \mathbf{p}_c \to \hat{I}_{\mathrm{proto}} \quad \text{(原型想象,从类别原型出发,可见到典型苹果/橙子)}
$$

### 2.2 渲染产物的强制元数据

每张渲染输出必须带:

```python
metadata = {
    "render_mode": "sensory_sketch" | "prototype_imagination",
    "input_trace_hash": <hex>,           # sensory_sketch 时是 f_x 的 sha256
    "prototype_trace_hash": <hex or null>, # prototype_imagination 时是 p_c 的 sha256;sketch 模式必为 null
    "evaluator_label_accessed": False,    # 永远 False(若为 True 就是 leak)
    "epistemic_source": "PERCEIVED_SENSORY_SKETCH" | "IMAGINED_PROTOTYPE_SKETCH"
                       | "REMEMBERED_SKETCH" | "INFERRED_SKETCH",
    "source_confidence": float,           # 对源本身的把握(感知 vs 想象的把握感)
}
```

### 2.3 状态池 SA 族细分

v1 的 `family="inner_picture"` 不变,但 SA id 升级:

```
StateItem(
    sa_id=f"inner_picture::sensory::<input_hash>::{tick}"      # 感知草图
    sa_id=f"inner_picture::imagined::<proto_hash>::{tick}"     # 原型想象
    sa_id=f"inner_picture::remembered::<memory_hash>::{tick}"  # 回忆草图
    sa_id=f"inner_picture::inferred::<chain_hash>::{tick}"     # 推理草图
    family="inner_picture",
    channel_signature=("vision", "imagined" | "perceived" | "remembered" | "inferred", "sketch"),
    ...
)
```

听觉对应 `inner_voice_sketch::sensory|imagined|remembered|inferred::*`。

### 2.4 红线(v1a 新增)

| RL | 描述 |
|---|---|
| RL-19v1a-S01 | 任意 audit pass 必为 `render_mode == "sensory_sketch"`,prototype_imagination 不能被记为 audit 通过 |
| RL-19v1a-S02 | `evaluator_label_accessed=True` 直接 audit 失败,无论 SSIM/legibility 多高 |
| RL-19v1a-S03 | 反馈对 `IMAGINED_PROTOTYPE_SKETCH` 路径的削弱**不得**直接削弱 `PERCEIVED_SENSORY_SKETCH` 路径(source-aware correction) |
| RL-19v1a-S04 | 同一 tick 不允许 sensory 和 imagined 的 SA 共享 sa_id |

---

## 3. V0 高带宽原始通道 + 维度数学闭合(吸收 v1 B2 + v2 B2)

### 3.1 V0 Foveated Retinal Pyramid(新增,放在 V1..V9 之前)

V0 **不是语义特征**,是高带宽近原始感受器轨迹,目的是让重建能基于原图信息而非全靠原型补脑。

| Tile 类型 | 尺寸 | 分辨率 | 维度贡献 |
|---|---|---|---|
| 全局低分辨率 RGB | 8×8 (固定) | 64 tiles × 3 channels | 192 |
| 全局低分辨率 Lab | 8×8 | 64 × 3 | 192 |
| 全局边缘 grid | 8×8 | 64 × 1 (Sobel mag) | 64 |
| 注视焦点高分辨率 patch | 32×32 (1 个,可移动) | 1024 × 3 | 3072 |
| 注视焦点边缘 patch | 32×32 | 1024 × 1 | 1024 |

V0 子总维度 = **4544**。这是高带宽 raw channel。

短期感官记忆 decay:V0 的全局低分辨率 tiles 每 tick 衰减 `vision_sensor.v0_decay_rate = 0.85`(@experimental),focus patch 每 fixation 替换。这是拟人"瞥一眼留印象,焦点处看得清楚,周边模糊"。

### 3.2 V1..V9 维度精确闭合

废弃 v1 的"feature_vector_dim ≈ 1800"模糊估计。**严格按通道乘以 region 数算**:

| 通道 | 单 region 维度 | Region 计数(放在哪些尺度) | 子总维度 |
|---|---:|---|---:|
| V1 RGB hist | 24 (8×3) | $S_0+S_1+S_2$ = 1+2+9 = 12 | 288 |
| V2 HSV hist | 128 (8×4×4) | $S_0+S_1+S_2$ = 12 | 1536 |
| V3 LBP 3 scales | 30 (10×3) | $S_0+S_1+S_2+S_3$ = 1+2+9+25 = 37 | 1110 |
| V4 HOG-lite | 8 | $S_0+S_1+S_2+S_3$ = 37 | 296 |
| V5 radial | 16 | $S_0$ only = 1 | 16 |
| V6 shape geometry | 5 (5 scalars) | $S_0$ on object mask = 1 | 5 |
| V7 part prototypes | 4 (top-K=4 coverage)| $S_4$ SLIC summary = 1 | 4 |
| V8 spatial layout | 5 (重心 2 + 偏移 1 + 占比 1 + focus_traj_summary 1) | $S_0$ = 1 | 5 |
| V9 fg/bg KL | 3 (V1/V2/V3 三个 KL) | $S_0$ on obj vs bg = 1 | 3 |
| **V0 retinal pyramid** | 见 §3.1 | — | **4544** |
| **小计 V0..V9** | | | **7807** |

锁 `vision_sensor.feature_vector_dim = 7807` @structural。不再有"PCA to 256 storage 但红线用原始"的歧义。

### 3.3 前景分割算法显式定义(吸收 v1 S1)

V6/V7/V8/V9 都依赖 $M_{\mathrm{obj}}$。**多假设 mask**,不是单 mask:

```
mask_hypotheses(I) -> List[Mask]:
  1. Saliency mask: 颜色对比 (LAB ΔE) + 边缘闭合度 + 中心先验
  2. Color cluster mask: 主色聚类的最大连通块
  3. Edge closure mask: Canny → 闭合轮廓填充
  4. Center prior mask: 图中心 60% 半径椭圆(fallback)
返回 4 个 mask 假设 + 每个的 segmentation_confidence ∈ [0,1]
```

V6/V8/V9 计算时**在所有 hypotheses 上算并取分布**(均值 + 方差),`segmentation_confidence` 进 §4 的 `source_quality` 因子。若所有 mask hypothesis 的 confidence < `vision_sensor.seg_conf_min = 0.3`(@experimental),Q 因子降到 0.3,自动压低把握。

### 3.4 Ablation gate(v1 S1 要求)

| Gate | 描述 |
|---|---|
| G-19v1a-Ablation-01 | 高背景干扰图 → Q 显著下降(不输出 firm 错答案) |
| G-19v1a-Ablation-02 | 中心干净卡片 → 重建草图与原图相似 |
| G-19v1a-Ablation-03 | mask 假设全部低信心时 → 不输出 firm |

---

## 4. 拟人把握感公式 v1a 重写(吸收 v1 B3 + v2 B3)

### 4.1 主公式(v2 拟人版)

$$
\boxed{
\mathrm{Conf}(c \mid x) = \mathrm{TierMap}\Big(\underbrace{\Pi(c|x) \cdot \Gamma(c|x) \cdot Q(x)}_{\text{ascend}},\; \underbrace{\mu(c|x)}_{\text{rival}},\; \underbrace{\nu(x)}_{\text{novelty}}\Big)
}
$$

5 个因子,各自含义:

- $\Pi(c|x)$ — **prototype_pull**:active diagnostic cues 在类别 $c$ 上的 thresholded top-m noisy-OR
- $\Gamma(c|x)$ — **coherence over active cues only**
- $Q(x)$ — **source_quality**(focus clarity + 分割 confidence + 新鲜度 + 不遮挡)
- $\mu(c|x)$ — **competitor_gap**(top-1 vs top-2 的 shifted margin)
- $\nu(x)$ — **novelty_tension**(降级而非 force no_call)

### 4.2 Diagnosticity — Nearest-negative separation

$$
\delta_k^{(c)} = \mathrm{sigmoid}\left(\beta \cdot \frac{d_k(\mathbf{p}_c, \mathbf{p}_{c^-(c,k)}) - r_k^{(c)}}{r_k^{(c)} + \epsilon}\right)
$$

其中:
- $c^-(c,k) = \arg\min_{c' \neq c} d_k(\mathbf{p}_c, \mathbf{p}_{c'})$:在通道 $k$ 上 $c$ 的最近邻竞争类
- $r_k^{(c)} = \mathrm{mean}_{i: y_i=c} d_k(\mathbf{f}_i^{(k)}, \mathbf{p}_c^{(k)})$:类内通道散度(positive radius)

**性质**:某通道能把 $c$ 与近邻竞争类拉开 ≫ 类内散度 → $\delta_k^{(c)} \to 1$;某通道只能拉开远类却分不开近邻 → $\delta_k^{(c)} \to 0.5$,公式自动 down-weight。这就是 v1 B3-P3 要的。

### 4.3 Prototype Pull — Thresholded top-m noisy-OR(吸收 v1 B3-P1)

通道命中:$h_k^{(c)}(x) = \exp(-\lambda_k d_k(\mathbf{f}_x^{(k)}, \mathbf{p}_c^{(k)}))$

evidence 单元(只算超过通道基线 $h_0^{(k)}$ 的部分):

$$
e_k^{(c)}(x) = \max\left(0, \delta_k^{(c)} \cdot (h_k^{(c)}(x) - h_0^{(k)})\right)
$$

只对 top-m 通道(`vision_sensor.evidence_top_m = 4` @structural)聚合 noisy-OR:

$$
\Pi(c|x) = 1 - \prod_{k \in \mathrm{TopM}(e^{(c)})} (1 - e_k^{(c)}(x))
$$

**性质**:9 个 weak 0.2 通道,但通道 baseline $h_0 \approx 0.2$ → 单元 $e_k \approx 0$ → top-m 取 0 → $\Pi \approx 0$,不再误饱和(v1 B3-P1 fix)。

而 2-3 个强诊断通道高命中(`e_k ≈ 0.7`)→ top-m 取这 2-3 个 → $\Pi \approx 0.97$,**少数强线索就敢说**(v1 B3-P2 fix)。

### 4.4 Active-cue Coherence(吸收 v1 B3-P2 + v2 B3-P2)

active set:

$$
\mathcal{A}(c, x) = \{k : \delta_k^{(c)} \geq \delta_{\min} \wedge h_k^{(c)}(x) \geq h_{\min}\}
$$

常量 `vision_sensor.delta_min = 0.5`、`vision_sensor.h_min = 0.4` @experimental。

若 $|\mathcal{A}| < 2$:$\Gamma = 0.3$(单线索仅允许 soft / ambig)。

若 $|\mathcal{A}| \geq 2$:

$$
\Gamma(c|x) = \frac{\left(\sum_{k \in \mathcal{A}} e_k^{(c)}\right)^2}{|\mathcal{A}| \cdot \sum_{k \in \mathcal{A}} (e_k^{(c)})^2}
$$

**性质**:2-4 个 active cue 同向命中 → $\Gamma \to 1$;1 个 cue 极强其他无关 → 通过 active set 过滤后只剩 1 个,触发 $|\mathcal{A}| < 2$ 分支,$\Gamma = 0.3$。这正是"少数强线索 + 无竞争 → 高把握,但不能只靠一条"。

### 4.5 Source Quality $Q(x)$

$$
Q(x) = Q_{\mathrm{focus}}(x) \cdot Q_{\mathrm{seg}}(x) \cdot Q_{\mathrm{occlusion}}(x) \cdot Q_{\mathrm{freshness}}(x)
$$

各项:

- $Q_{\mathrm{focus}}$:V0 focus patch 的边缘锐度(模糊图低)
- $Q_{\mathrm{seg}}$:§3.3 multi-hypothesis mask 的最大 segmentation_confidence
- $Q_{\mathrm{occlusion}}$:V9 fg/bg KL 高 → 主体凸显 → $Q$ 高
- $Q_{\mathrm{freshness}}$:V0 short-term sensory memory 的 decay(久前看过的低)

### 4.6 Competitor Gap — Shifted margin(吸收 v1 B3-P3)

raw score $s(x,c) = \Pi(c|x) \cdot \Gamma(c|x)$,排序后 $s_{(1)} \geq s_{(2)} \geq \dots$。

$$
\mu(c^*|x) = \mathrm{sigmoid}\left(\kappa \cdot \left(\frac{s_{(1)} - s_{(2)}}{s_{(1)} + \epsilon} - \mu_0\right)\right)
$$

`vision_sensor.margin_kappa = 6.0`,`vision_sensor.margin_midpoint = 0.25` @experimental。

**性质**:相对 margin = 0(top1=top2)时,$\mathrm{sigmoid}(-1.5) \approx 0.18$,把握显著被压(不再是 0.5)。相对 margin = 0.5 时 sigmoid(1.5) ≈ 0.82。

### 4.7 Novelty Tension — 降级而非 force no_call(吸收 v2 B3-P3)

$$
\nu(x) = 1 - \exp(-\gamma \cdot \min_c d(\mathbf{f}_x, \mathbf{p}_c))
$$

它不直接乘 Conf,而是改变 tier_map 的门槛:

```
tier_map(ascend, rival, novelty):
  raw_tier =
    "firm"   if ascend * rival >= tau_firm
    "soft"   if ascend * rival >= tau_soft
    "ambig"  if ascend * rival >= tau_ambig
    "no_call" otherwise

  # novelty 降级一档
  if novelty >= novelty_strong (e.g. 0.7):
    tier = downgrade_one(raw_tier)        # firm -> soft -> ambig -> no_call

  # 极端 OOD 才直接 no_call
  if novelty >= novelty_extreme (e.g. 0.9) and prototype_pull < 0.2:
    tier = "no_call"
  return tier
```

`vision_sensor.novelty_strong = 0.7` @experimental
`vision_sensor.novelty_extreme = 0.9` @experimental

**性质**:绿橙子(色调 OOD 但形状仍橙)→ $\nu \approx 0.5$ → 不降级,Conf 落在 soft;完全没见过的水果(熊掌瓜)→ $\nu \approx 0.95$ + $\Pi < 0.2$ → no_call。

---

## 5. Phase 19.3 拆分为 19.3a / 19.3b(吸收 v1 B4 + v2 corrected)

### 5.1 拆分

| 子阶段 | 训练集 | 测试集 | 测什么 |
|---|---|---|---|
| **Phase 19.3a** Real-photo train/held-out | 用户真实照片 train split (~7 张) | 用户真实照片 held-out (~5 张) | **真照片域内** visual-only no-leak 学习 |
| **Phase 19.3b** Clean-card → real-photo transfer | Phase 18.0 干净卡片 train | 用户真实照片全 12 张 | 跨域迁移(干净卡 → 真照片) |

### 5.2 失败定性(v2 拟人原则)

- 19.3a 失败 → 富感受器**域内**仍不够,加 V0 通道精度或调 $\lambda_k$
- 19.3b 失败 → "卡片→真照片"对 AP 是**拟人发展限制**(就像小孩从简笔画过渡到真物有困难),不一定是设计 bug。Final Report 可写"AP 当前发展阶段对 clean→real transfer 仅 X/12,符合早期人类幼儿水平"

### 5.3 失败时禁用 "no firm + wrong",改用 §8 错误 taxonomy

---

## 6. 听觉同等深化(吸收 v1 S2 + v2 S4,扩展到与视觉对等设计)

### 6.1 A0 Cochlear Pyramid(新增,放在 A1..A8 之前)

A0 是听觉的高带宽近原始感受器轨迹:

| Tile 类型 | 尺寸 / 时间 | 维度 |
|---|---|---|
| Gammatone 滤波器组 mag tiles | 64 bands × 50 frames (1 sec) | 3200 |
| Lin-spaced STFT mag tiles | 257 bins × 50 frames | 12850 |
| 短时能量包络 multi-scale | 3 scales × 50 frames | 150 |
| Onset salience 序列 | 50 frames | 50 |
| Attention focus high-res patch | 16 bands × 8 frames | 128 |

A0 子总 = **16378**。听觉感官记忆 decay `audio_sensor.a0_decay_rate = 0.80`。

### 6.2 A1..A8 维度闭合

按 1 秒输入、50 frames 计:

| 通道 | 单 frame 维度 | Frame 数 | 子总维度 |
|---|---:|---:|---:|
| A1 MFCC + Δ + ΔΔ | 39 | 50 | 1950 |
| A2 Chroma | 12 | 50 | 600 |
| A3 Spectral 4-moment | 4 | 50 | 200 |
| A4 ZCR | 1 | 50 | 50 |
| A5 Onset / Tempo env | 8 + 1 BPM | 50 + 1 | 401 |
| A6 F0 + voicing | 2 | 50 | 100 |
| A7 RMS multi-scale | 3 | 50 | 150 |
| A8 Spectral contrast | 7 | 50 | 350 |
| **A0 cochlear pyramid** | — | — | **16378** |
| **小计 A0..A8** | | | **20179** |

锁 `audio_sensor.feature_vector_dim = 20179` @structural。

### 6.3 双模式渲染(对称视觉)

$$
\mathcal{R}_{\mathrm{aud,sketch}}: \mathbf{f}_A \to \hat{A}_{\mathrm{sketch}}
$$
$$
\mathcal{R}_{\mathrm{aud,proto}}: \mathbf{p}_c^{\mathrm{aud}} \to \hat{A}_{\mathrm{proto}}
$$

`inner_voice` → 全文改名 **`inner_voice_sketch`**(吸收 v2 S4)。

### 6.4 按声音家族分指标(吸收 v1 S2)

| 声音家族 | 评估指标 | 门槛 |
|---|---|---|
| 语音类(说话 / 喊 / 笑 / 哭) | STOI | ≥ 0.45 |
| 音乐类(钢琴 / 铃铛 / 哼唱) | Pitch contour correlation + chroma cosine | ≥ 0.6 / ≥ 0.7 |
| 自然类(雨 / 风 / 水 / 鸟) | Mel-spec correlation + envelope correlation | ≥ 0.5 / ≥ 0.6 |
| 冲击类(敲门 / 咳嗽 / 鼓) | Onset F1 + envelope correlation | ≥ 0.7 / ≥ 0.6 |

人耳可辨度 $L \geq 3$ 跨家族通用,银子老师签收。

### 6.5 拟人把握感公式直接复用 §4

视觉公式中的 $V_k$ → $A_k$,9 通道 → 8+A0 通道。其他不变。

### 6.6 听觉错误 taxonomy(对应 §8)

- `auditory_human_plausible_soft_error`(雨声听成水声)
- `auditory_human_plausible_illusion_error`(模糊语音听错)
- `auditory_nonhuman_artifact_error`(用文件名 / metadata 得答案)
- `auditory_source_confusion_error`(把想象的声音当真听到)

### 6.7 Phase 19.4 听觉 probe(新增,与视觉 19.3 对称)

- **Phase 19.4a** 真实音频 train/held-out
- **Phase 19.4b** 合成 / 干净音 → 真实音频迁移

---

## 7. Percept Retrieval Gate(吸收 v1 S4 + v2 S3)

重建只证 "AP 内心能想出主体",**不证它能从一堆 SA 里召回相似对象**。补 retrieval gate:

```
recall_score(c | x)
  = Π(c|x)                              # prototype pull (诊断证据)
  + α₁ · part_overlap(c, x)             # V7 part prototype 共享
  + α₂ · shape_overlap(c, x)            # V6 形状几何接近
  + α₃ · learned_cooccurrence(c, x)     # SDPL 历史共现支持
  − α₄ · source_conflict_penalty(c, x)  # 来源冲突惩罚
```

常量 `vision_sensor.alpha_part = 0.3`、`alpha_shape = 0.2`、`alpha_cooccur = 0.15`、`alpha_source_conflict = 0.4` @experimental。

测试指标:

- **Recall@1**, **Recall@3** on held-out
- positive rank above contrast by margin ≥ `vision_sensor.recall_margin_min = 0.1` @structural
- high-confidence wrong count(Conf in firm + 错预测) **必须 ≤ § 8 规定**

输出"top-3 候选 + 文本",拟人形态:
- 高把握:"这是 c"
- 中把握 + 双竞争:"可能是 c,也可能是 c'"(top-2 + Phase 16 styled corpus 渲染)
- 低把握:"还不能确认"

---

## 8. 错误分类法(吸收 v2 S1,核心拟人 gate)

替换 v1 的 "no firm + wrong" gate(过于机器化)。新分类:

| 错误类 | 描述 | gate 处理 |
|---|---|---|
| `human_plausible_soft_error` | AP 输出"像是 X",错,但线索足以让人也猜 X | **允许**,Final Report 列入 |
| `human_plausible_illusion_error` | AP 输出 firm X,错,但图像有强误导线索(像照片错觉) | **允许但有上限**:`illusion_firm_wrong_max = 1` per 12 imgs |
| `nonhuman_artifact_error` | 答案来自文件名 / metadata / target_class leak | **必须 0**(红线) |
| `source_confusion_error` | AP 把想象的原型当成真看到的 | **必须 0**(红线) |
| `uncertainty_underreach` | AP 输出 no_call,但大多数人都会给一个 tentative guess | **允许有限**:`underreach_max = 2` per 12 imgs |

每次测试输出含 `error_taxonomy` 字段,Phase 19.3 / 19.4 / 19.5(后续)都以此为 acceptance gate。

---

## 9. Source-Aware Feedback Gate(吸收 v2 final)

反馈机制 v1a 强制:

- 用户告诉 AP "不对",AP 必须识别**错在哪个 source**:
  - 错在 `PERCEIVED_SENSORY_SKETCH` → 削弱该图 sensory 路径权重
  - 错在 `IMAGINED_PROTOTYPE_SKETCH` → 削弱原型想象的拉力 $\Pi$,**不削弱**直接感知路径
  - 错在 `INFERRED_SKETCH` → 调推理链权重
- 同一张图再过来时,Conf 必须降低(可证可测)
- 反馈不**禁止**未来再产生类似 illusion,但**统计上**必须使 illusion_firm_wrong 频率衰减

测试 gate:

| Gate | 描述 |
|---|---|
| G-19v1a-Feedback-01 | 标注 source 错误类型后,对应 source 路径 Q 表 / Π 权重统计降低 |
| G-19v1a-Feedback-02 | 同图再次输入,Conf strictly 降低(≥ 0.1) |
| G-19v1a-Feedback-03 | 反馈不削弱其他独立 SA 的把握感(隔离) |

---

## 10. 修改后的 Deliverable Gates 总表(替换 v1 各 Phase 末尾的 gate 表)

### Phase 19.0 v1a gates(替换 v1 §7)

| Gate | 描述 |
|---|---|
| G-19.0v1a-01 | V0 + V1..V9 全部实现,各通道独立单测 |
| G-19.0v1a-02 | feature_vector_dim = 7807 精确闭合 |
| G-19.0v1a-03 | $\mathcal{R}_{\mathrm{sketch}}$ 与 $\mathcal{R}_{\mathrm{proto}}$ 两种 mode 实现 |
| G-19.0v1a-04 | 每张渲染产物带 §2.2 必备元数据 |
| G-19.0v1a-05 | 12 张用户图每张产 sketch + 类原型 imagination 各一张 |
| G-19.0v1a-06 | multi-hypothesis mask 至少 4 假设,segmentation_confidence 进 Q |
| G-19.0v1a-07 | inner_picture 接入 reverse_imagination / imagined_marker / conclusion_reify(SA id 含 source) |
| G-19.0v1a-08 | RL-19v1a-S01..S04 全过(audit pass 必为 sensory_sketch) |
| G-19.0v1a-09 | 真名 / label / filename leak 全部零命中 |
| G-19.0v1a-10 | Ablation gates 三条(§3.4)全过 |
| G-19.0v1a-11 | 治理通过 |
| G-19.0v1a-12 | 不依赖 cv2/torch/tf/sklearn/librosa |
| G-19.0v1a-13 | 不调外部 API |
| G-19.0v1a-14 | 全量回归 + Phase 19.0 v1a 新测试 |

### Phase 19.2 v1a gates(替换 v1 §5)

| Gate | 描述 |
|---|---|
| G-19.2v1a-01 | 5 因子各有单测覆盖边界 |
| G-19.2v1a-02 | Diagnosticity 用 nearest-negative 公式 |
| G-19.2v1a-03 | $\Pi$ 用 thresholded top-m noisy-OR,9 个 0.2 弱 cue 测出 $\Pi < 0.3$(不饱和) |
| G-19.2v1a-04 | $\Gamma$ 在 2-3 个强 cue 同向情形下 ≥ 0.85 |
| G-19.2v1a-05 | Margin shifted 在 top1=top2 给 $\mu \approx 0.18$(不再 0.5) |
| G-19.2v1a-06 | Novelty 降级而非 force no_call(中度 OOD 仍可输出 soft) |
| G-19.2v1a-07 | 输出文本走 Phase 16 styled corpus |
| G-19.2v1a-08 | 12 张图每张 decision_tier 输出 |
| G-19.2v1a-09 | 绿橙 / 黄绿苹果输出 soft(不 firm 不 no_call) |
| G-19.2v1a-10 | OOD 假图输出 ambig 或 no_call |

### Phase 19.3a real-photo train/held-out

| Gate |
|---|
| G-19.3a-01 student payload 无 leak(grep) |
| G-19.3a-02 train 5-7 张,held-out 4-5 张 |
| G-19.3a-03 `nonhuman_artifact_error = 0` |
| G-19.3a-04 `source_confusion_error = 0` |
| G-19.3a-05 `illusion_firm_wrong ≤ 1` |
| G-19.3a-06 `uncertainty_underreach ≤ 2` |
| G-19.3a-07 Recall@3 ≥ 0.6 on held-out |
| G-19.3a-08 每张测试图同步产 inner_picture sensory + imagined 两张 |

### Phase 19.3b clean-card → real-photo transfer

| Gate |
|---|
| G-19.3b-01..07 同 19.3a 替换数据集 |
| G-19.3b-08 Recall@3 ≥ 0.35(发展阶段限制,设低一档) |
| G-19.3b-09 失败时 Final Report 必须明确标记"early developmental limitation, not design failure" |

### Phase 19.4a / 19.4b 听觉 probe(对称 19.3a/b)

平行 19.3a/b,把视觉换成听觉。

### Phase 19.1 v1a gates(替换 v1 §6.3)

| Gate |
|---|
| G-19.1v1a-01 A0 + A1..A8 全实现,独立单测 |
| G-19.1v1a-02 feature_vector_dim = 20179 闭合 |
| G-19.1v1a-03 $\mathcal{R}_{\mathrm{aud,sketch}}$ vs $\mathcal{R}_{\mathrm{aud,proto}}$ 分离 |
| G-19.1v1a-04 4 种声音家族每族评估指标按 §6.4 |
| G-19.1v1a-05 inner_voice_sketch 接入 narrative.lag_pmi / imagined_marker / conclusion_reify |
| G-19.1v1a-06 source marking 元数据(§2.2)强制 |
| G-19.1v1a-07 不调外部音频 ML 库(librosa / torchaudio / whisper / TTS) |
| G-19.1v1a-08 Final Report 明确"inner_voice_sketch 是 auditory imagery,不是 TTS" |

---

## 11. 路线图修订

| 阶段 | v1 | v1a |
|---|---|---|
| 19.0 视觉 | $\mathcal{R}$ 单算子 | $\mathcal{R}_{\mathrm{sketch}}$ / $\mathcal{R}_{\mathrm{proto}}$ 双模式 + V0 retinal pyramid + 闭合维度 + multi-hypothesis mask |
| 19.1 听觉 | $\mathcal{R}_{\mathrm{aud}}$ + STOI | A0 + 双模式 + 4 家族指标 + inner_voice_sketch |
| 19.2 把握感 | $D \cdot C \cdot M \cdot Q \cdot (1-\Omega)$ | $\Pi \cdot \Gamma \cdot Q$ 上升 + $\mu$ + $\nu$ tier_map + 错误 taxonomy |
| 19.3 视觉 probe | 单 probe | 19.3a real-photo train/held-out + 19.3b clean-card → real-photo |
| 19.4 听觉 probe | (v1 未起草) | 19.4a real-audio train/held-out + 19.4b synthetic → real-audio |
| 19.5 Source-aware feedback | 隐含 | §9 显式 gate |

总顺序:**19.0 → 19.2 → 19.3a → 19.3b → 19.1 → 19.4a → 19.4b → 19.5**。

---

## 12. 边界

- v1a 不替换 v1,叠加。落地时以 v1 + v1a 合读。
- 12 张用户图仍为 Phase 19 内部诊断集合,不作开源 release 资产。
- v1a 不实现自动权重学习(等 Phase 20)
- v1a 不实现 active perception / refixation 策略(等 Phase 19.2 落地后做 Phase 19.6)
- 真实世界完整识别仍不在 Phase 19 内宣称范围

---

## 13. 署名

- 原架构设计:银子老师(笔名)
- 数学模型与 v1a 修订:Claude (Anthropic) 在银子老师方向 + 吸收 Codex v1/v2 对抗审阅后产出
- 落地实现:Codex 在 v1a 通过最终审查后执行

End of Phase 19 v1a Errata.
