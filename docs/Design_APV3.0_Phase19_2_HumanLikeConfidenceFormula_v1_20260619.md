# APV3.0 Phase 19.2 Design — Human-Like Confidence Formula (诊断性 × 一致性 × 竞争压制 × 质量门 - OOD)

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Depends on: Phase 19.0 (visual sensor + R operator), Phase 19.1 (audio sensor)
Status: 设计稿,等待 Codex 对抗性审查 + 银子老师签字落地
License intent: AGPL-3.0-or-later + Commercial License separate

---

## 0. 这一阶段做什么(一句话)

把当前 AP 的"打分=最近邻余弦相似度"贫血决策替换成**4 因子拟人把握感公式**,并把它接入 4 档拟人输出策略(`这是 X` / `像是 X` / `可能是 X,也可能是 Y` / `还不能确认`),使得 AP 面对从未见过的对象时,**对几个高诊断特征明显且无竞争对手**的情形给高把握,**对全局相似度低但缺关键诊断线索**的情形给"还不能确认"。

理论锚:Tversky Feature-Matching + Rosch Prototype + Shepard Universal Law + Bayesian noisy-OR + Margin-based competition。

---

## 1. 心理学根据(给 Codex 审查时一并复核)

| 现象 | 文献 | Phase 19.2 编码 |
|---|---|---|
| 人类用少数高诊断特征就敢判断,即使全局相似度不高 | Tversky 1977 "Features of Similarity"; Rosch & Mervis 1975 "Family resemblance" | $D(x,c)$ 因子 — noisy-OR 聚合高诊断特征命中 |
| 几个线索互相印证 → 把握感放大 | Mackiewicz & Henderson 2017 "Diagnostic feature consistency"; Bowers 1984 "intuition consistency" | $C(x,c)$ 因子 — 命中特征之间的协方差 / 同向性 |
| 第二候选越接近,越不敢下结论 | Marley & Colonius 1992 "Ratio of strengths"; Luce choice; Welch margin | $M(x,c)$ 因子 — top-1 vs top-2 score margin |
| 图本身糊 / 遮挡 / 主体小 → 不敢说 | Rensink "change blindness"; visual quality literature | $Q(x)$ 因子 — 图像质量门 |
| 全图很陌生(distribution shift) → 不敢说 | Bishop 1995 "Novelty detection"; Hendrycks & Gimpel 2017 OOD | $-\Omega(x)$ 项 — OOD 惩罚 |

模型设计原则:**不是先做分类器再加把握感** — 把握感直接作为决策机制本身。

---

## 2. 公式标准化

### 2.1 主公式

$$
\boxed{
\mathrm{Conf}(c \mid x) = \underbrace{D(x,c)}_{\text{诊断}} \cdot \underbrace{C(x,c)}_{\text{一致}} \cdot \underbrace{M(x,c)}_{\text{竞争压制}} \cdot \underbrace{Q(x)}_{\text{质量门}} \cdot \underbrace{(1 - \Omega(x))}_{\text{OOD 惩罚}}
}
$$

每因子值域 $[0,1]$,$\mathrm{Conf} \in [0,1]$。

### 2.2 诊断性 $D(x,c)$ — Noisy-OR over high-diag features

对每通道 $V_k$($k=1..9$ 视觉 / $A_k$($k=1..8$ 听觉),先离线算"诊断系数"$\delta_k^{(c)} \in [0,1]$:类别 $c$ 在该通道上的训练原型与其他类原型的分离度。

$$
\delta_k^{(c)} = \mathrm{tanh}\left(\beta \cdot \frac{\mathrm{mean}_{c' \neq c} d_k(\mathbf{p}_c, \mathbf{p}_{c'})}{\mathrm{std}_{c' \neq c} d_k(\mathbf{p}_c, \mathbf{p}_{c'}) + \epsilon}\right)
$$

诊断系数高 = 该通道是判断类别 $c$ 的强线索(如香蕉的 V6 长宽比、橙子的 V2 HSV 色调)。

通道命中概率 $h_k^{(c)}(x) = \exp(-\lambda_k d_k(\mathbf{f}_x^{(k)}, \mathbf{p}_c^{(k)}))$,$\lambda_k$ 是该通道的 Shepard 衰减。

Noisy-OR 聚合:

$$
D(x,c) = 1 - \prod_{k=1}^{K} \left(1 - \delta_k^{(c)} \cdot h_k^{(c)}(x)\right)
$$

**性质**:任一高诊断通道高命中 → $D \to 1$;所有通道都半信半疑 → $D$ 居中;诊断高的通道全不命中 → $D \to 0$。这就是"几个特征像就敢说"的数学根据。

### 2.3 一致性 $C(x,c)$ — Feature agreement

高诊断通道命中向量 $\mathbf{h}^{(c)} = (\delta_1^{(c)} h_1^{(c)}, \dots, \delta_K^{(c)} h_K^{(c)})$。

$$
C(x,c) = \frac{\left(\sum_k \delta_k^{(c)} h_k^{(c)}\right)^2}{K \cdot \sum_k \left(\delta_k^{(c)} h_k^{(c)}\right)^2}
$$

(Cauchy-Schwarz 比,等同于"几何 / 算术"之比的平方,$\in [1/K, 1]$,然后线性映射到 $[0,1]$)。

**性质**:若 3 个高诊断通道都中等命中 → 高一致;若 1 个通道极高命中而其他通道完全不命中 → 低一致(可能是噪声 / 假阳性)。

### 2.4 竞争压制 $M(x,c)$ — Margin vs second-best

先算原始 score $s(x,c) = D(x,c) \cdot C(x,c)$,排序得 $s_{(1)} \geq s_{(2)} \geq \dots$,$c^* = \arg\max_c s(x,c)$。

$$
M(x, c^*) = \mathrm{sigmoid}\left(\kappa \cdot \frac{s_{(1)} - s_{(2)}}{s_{(1)} + \epsilon}\right)
$$

对非 top-1 类,$M = 0$。

**性质**:第二候选 score 越接近 top-1,$M \to 0.5$,把握降一半。

### 2.5 质量门 $Q(x)$

视觉:综合 V8 主体占比 / V9 前景背景对比 / V5 渐变锐利度 / V4 边缘强度:

$$
Q_{\mathrm{vis}}(x) = \min\left(1, \frac{\rho_{\mathrm{obj}}}{\rho_{\mathrm{min}}}\right) \cdot \min\left(1, \frac{D_{\mathrm{KL}}^{\mathrm{V9}}}{D_{\mathrm{KL,min}}}\right) \cdot \min\left(1, \frac{\|\nabla I\|_{\mathrm{mean}}}{g_{\mathrm{min}}}\right)
$$

听觉:综合 A7 RMS 能量 / A8 spectral contrast / A4 zcr 合理范围:

$$
Q_{\mathrm{aud}}(A) = \min(1, \mathrm{RMS}/r_{\mathrm{min}}) \cdot \min(1, \mathrm{contrast}/c_{\mathrm{min}})
$$

低于阈值 → $Q$ 显著下降 → 把握降。

### 2.6 OOD 惩罚 $\Omega(x)$ — Novelty detection

$$
\Omega(x) = 1 - \exp\left(-\gamma \cdot \min_c d(\mathbf{f}_x, \mathbf{p}_c)\right)
$$

最近原型也很远 → $\Omega \to 1$ → 公式压制把握。这就是"完全没见过的东西,几乎不敢说"的根据。

---

## 3. 4 档拟人输出策略

$$
\mathrm{output}(x) = \begin{cases}
\text{"} \mathrm{label}(c^*) \text{"} & \text{if } \mathrm{Conf}(c^* \mid x) \geq \tau_{\mathrm{firm}} \\
\text{"像是 } \mathrm{label}(c^*) \text{"} & \text{if } \tau_{\mathrm{soft}} \leq \mathrm{Conf}(c^* \mid x) < \tau_{\mathrm{firm}} \\
\text{"可能是 } \mathrm{label}(c^*) \text{,也可能是 } \mathrm{label}(c^{**}) \text{"} & \text{if } \tau_{\mathrm{ambig}} \leq \mathrm{Conf}(c^* \mid x) < \tau_{\mathrm{soft}} \wedge M < M_{\mathrm{ambig}} \\
\text{"还不能确认"} & \text{otherwise}
\end{cases}
$$

常量:
- $\tau_{\mathrm{firm}} = 0.75$ @structural
- $\tau_{\mathrm{soft}} = 0.55$ @structural
- $\tau_{\mathrm{ambig}} = 0.35$ @structural
- $M_{\mathrm{ambig}} = 0.4$ @structural

**这正好对应您说的**:绿橙子 → V2 HSV 色调相比典型橙偏移 → $D$ 略低 + $\Omega$ 略高 → Conf ≈ 0.55-0.65 → 输出"像是橙子",不输出"这是橙子",也不输出"还不能确认"。这就是拟人。

---

## 4. 接入状态池

`StateItem` 增加可选 metadata 字段(不进 SA id,不变 marker_kind 个数):

```python
metadata = {
    ...,
    "confidence_score": float,
    "confidence_decomposition": {
        "D": float, "C": float, "M": float, "Q": float, "omega": float,
        "channel_hits": {f"V{k}": float for k in range(1,10)},
    },
    "decision_tier": "firm" | "soft" | "ambig" | "no_call",
}
```

接入点:Phase 19.3 visual-only probe 直接用,Phase 19.1 inner_voice 渲染时把把握感作为 `real_energy`。

---

## 5. 常量 / 红线 / Gates

### 5.1 新常量

```yaml
confidence:
  beta_diagnosticity_scale: 1.0          # @experimental
  margin_kappa: 4.0                      # @experimental
  ood_gamma: 0.5                         # @experimental
  quality_rho_min: 0.05                  # @experimental
  quality_kl_min: 0.5                    # @experimental
  quality_gradient_min: 0.02             # @experimental
  quality_rms_min: 0.01                  # @experimental
  quality_contrast_min: 0.2              # @experimental
  tau_firm: 0.75                         # @structural
  tau_soft: 0.55                         # @structural
  tau_ambig: 0.35                        # @structural
  margin_ambig: 0.4                      # @structural
```

### 5.2 红线

| RL | 描述 |
|---|---|
| RL-19.2-C01 | $\mathrm{Conf}$ 不调外部 ML 库,纯 numpy |
| RL-19.2-C02 | $\delta_k^{(c)}$ 离线计算,运行时只查表 |
| RL-19.2-C03 | $\mathrm{Conf}$ 输入不得包含 label / filename / entry_id(防 leak) |
| RL-19.2-C04 | 4 档输出文本走 Phase 16 styled corpus,不硬编 |
| RL-19.2-C05 | $\mathrm{decision\_tier}$ 仅作 audit metadata,不进 SDPL packet key |
| RL-19.2-C06 | 真名零命中 |

### 5.3 Gates(11 条)

| Gate | 描述 |
|---|---|
| G-19.2-01 | 5 因子各自有单测覆盖边界(全 0 / 全 1 / 不一致) |
| G-19.2-02 | 公式实现完全按 §2 数学定义,无 fudge factor |
| G-19.2-03 | 4 档输出函数有完备性单测(覆盖 4 档边界) |
| G-19.2-04 | 输出文本走 Phase 16 styled corpus,不硬编中文 |
| G-19.2-05 | 12 张用户图(Phase 19.0)上运行,每张输出 decision_tier |
| G-19.2-06 | 绿橙子(变体)输出 "soft" 或 "ambig"(不应输出 "firm" 也不应 "no_call") |
| G-19.2-07 | 黄绿苹果(变体)输出 "soft" 或 "ambig" |
| G-19.2-08 | OOD 图(从未见过类别)输出 "no_call" |
| G-19.2-09 | 红线 6 条零命中 |
| G-19.2-10 | 治理通过,所有常量分类标注 |
| G-19.2-11 | 全量回归 + Phase 19.2 新测试 |

---

## 6. 边界

- 不实现自动权重学习(Phase 19.2 锁 $w_c = 1/K$ 等权,自动学习推到 Phase 20)
- 不实现 reject-and-ask(AP 主动反问,推到对话底座 Phase 21)
- 不替换 Phase 13 Q-learning 主路径(把握感是决策外壳,不动 SDPL 内部)

---

End of Phase 19.2 Design.
