# APV3.0 Phase 19.0 Design — Visual Sensor Enrichment + Reconstruction Audit + Inner Picture Reify

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿,等待 Codex 对抗性审查 + 银子老师签字落地
License intent: AGPL-3.0-or-later + Commercial License separate
Original architect: 银子老师 (笔名)
Real name handling: 全文件 grep 真名 = 0(继承 Phase 16/17/18 红线)

---

## 0. 这一阶段做什么(一句话)

把当前贫血的视觉感受器(只输出全局颜色均值/粗略形状/单一能量)升级成 **9 通道 AP-native 富感受器**,并用"**反向重建**"作为感受器充分性的**信息论标准**;同时让这条反向重建管线**复用为底座的"内心实时画面"**通道 — 状态池里的 imagined SA / fast_mapping reverse_imagination / DraftCharFocus 想象都通过同一组算子合成可被人类一眼看懂的内部图像。

---

## 1. 三个目标(不能少其一)

### G-Receptor 富化:输入端不再贫血
9 通道并行采集,所有通道纯 numpy/scipy 实现,不调外部预训练模型(CNN/CLIP/SAM 一律禁止)。

### G-Audit 反向重建:充分性可量化证明
对任意输入图,9 通道特征向量 $\mathbf{f}$ 必须能通过反向重建算子 $\mathcal{R}$ 合成低分辨率近似图 $\hat{I} = \mathcal{R}(\mathbf{f})$,使得 $\mathrm{SSIM}(I, \hat{I}) \geq \theta_{\mathrm{SSIM}}$ 且人眼可辨度评分 $L \geq L_{\min}$。重建失败 = 该通道集信息不足 = 红线触发,加通道或提精度。

### G-Inner 内心实时画面接入:状态池可视化
状态池里所有 `family="percept"` 且 `source in {reverse_imagination, imagined_marker_spawn, conclusion_reify}` 的 SA,都能通过 $\mathcal{R}$ 渲染成对应的"内心画面"PNG,供展示页 / 桌宠界面 / 调试器实时显示。**这不是新增一条通道,是 G-Audit 的算子复用**。

---

## 2. 9 通道感受器清单(锁清单,严禁运行时增删)

### 通道维度命名
将单张 RGB 图 $I \in \mathbb{R}^{H \times W \times 3}$ 切成 5 个空间尺度:
- $S_0$ 全图整体 (1 region)
- $S_1$ 中心 vs 周边 (2 regions, 中心 60% 半径)
- $S_2$ 3×3 网格 (9 regions, Phase 8.6 既有)
- $S_3$ 5×5 网格 (25 regions)
- $S_4$ SLIC 超像素聚类 (≤ 32 regions, k = 24 默认)

每个 region 同时算 V1..V9,每张图最终产 $\mathbf{f}_I \in \mathbb{R}^D$,$D$ 锁在 `vision_sensor.feature_vector_dim`(预估 ≈ 1800,常量治理收敛后给定)。

### V1 — Color Histogram (RGB)
对每 region 计 3 通道 8-bin 直方图,归一化为概率密度。

$$
H_R^{(r)}[b] = \frac{1}{|r|} \sum_{(x,y) \in r} \mathbb{1}\left[\left\lfloor \frac{I_R(x,y)}{32} \right\rfloor = b\right], \quad b \in \{0,\dots,7\}
$$

同理 $H_G, H_B$。共 $24 \times \sum_s |S_s| \approx 1600$ 维(主要承担量,可用 PCA 投影到 256 维做存储但红线计算用原始)。

### V2 — Color in HSV space
HSV 8×4×4 = 128 bin 联合直方图,关键解决"绿橙子 vs 红苹果":H 通道把橙色 / 红色 / 黄绿 分离,S 通道区分"褪色绿橙" vs "新鲜橙"。

### V3 — Local Texture (LBP)
Local Binary Pattern,uniform-rotation-invariant (uniform2),3 scales: $(P,R) \in \{(8,1),(16,2),(24,3)\}$,每尺度 10 bin。共 30 bin × region 数。

$$
\mathrm{LBP}_{P,R}(c) = \sum_{p=0}^{P-1} s(g_p - g_c) \cdot 2^p, \quad s(x) = \mathbb{1}[x \geq 0]
$$

### V4 — Edge Orientation Histogram (HOG-lite)
Sobel 算子 $G_x, G_y \to$ 幅值 $M = \sqrt{G_x^2 + G_y^2}$,方向 $\theta = \arctan_2(G_y, G_x)$。8 方向 bin,每 region 投票:

$$
E^{(r)}[k] = \sum_{(x,y) \in r} M(x,y) \cdot \mathbb{1}\left[\theta(x,y) \in \left[\frac{k\pi}{4} - \frac{\pi}{8}, \frac{k\pi}{4} + \frac{\pi}{8}\right)\right]
$$

L2 归一化。

### V5 — Radial Gradient Profile (从中心到边缘的颜色/亮度渐变)
$$
g(\rho) = \frac{1}{|R_\rho|} \sum_{(x,y) \in R_\rho} \|\nabla I(x,y)\|, \quad R_\rho = \{(x,y) : \rho - \frac{\Delta}{2} \leq d_{\mathrm{center}}(x,y) < \rho + \frac{\Delta}{2}\}
$$

16 个 radial bin,关键解决"球状/弯曲/带尖端"的不变量。

### V6 — Shape Geometry (主体掩码上的形状量)
先用 V1+V4 估计主体掩码 $M_{\mathrm{obj}}$(GrabCut-lite,纯 numpy 实现,不调 cv2),再算:

- 长宽比 $\alpha = w/h$
- 凸包度 $\eta = |M_{\mathrm{obj}}| / |\mathrm{ConvexHull}(M_{\mathrm{obj}})|$
- 圆形度 $\gamma = 4\pi |M_{\mathrm{obj}}| / P_{\mathrm{obj}}^2$,$P_{\mathrm{obj}}$ 为周长
- 主轴方向 $\phi \in [0, \pi)$
- 对称性 $\sigma = 1 - \frac{|M_{\mathrm{obj}} \triangle \mathrm{Flip}(M_{\mathrm{obj}})|}{2|M_{\mathrm{obj}}|}$

5 个标量,语义稳定。

### V7 — Part Prototypes via SLIC + Affinity
SLIC 超像素 → 每超像素 (V1+V2+V3+V4) 拼接成 part feature → 在线 k-medoids 聚类 → 每图产 top-K 部件原型($K = 4$ 默认)及其覆盖率。

$$
\mathrm{PartCoverage}^{(r)}_{k} = \frac{|\{p : \mathrm{cluster}(p) = k\}|}{|r|}
$$

关键解决"苹果有梗 vs 橙子有蒂"的局部差异。

### V8 — Spatial Layout (主体在画面的位置)
主体掩码的重心 $(\bar{x}, \bar{y})$、相对图心偏移、占画面比例 $\rho_{\mathrm{obj}}$、注意焦点轨迹 $\tau_{\mathrm{focus}}$(继承 Phase 8.7 visual_attention)。

### V9 — Foreground / Background Contrast
主体 region 与背景 region 在 V1/V2/V3 上的 KL 散度:

$$
D_{\mathrm{KL}}^{(c)}(M_{\mathrm{obj}} \| M_{\mathrm{bg}}) = \sum_b H^{(c)}_{\mathrm{obj}}[b] \log \frac{H^{(c)}_{\mathrm{obj}}[b] + \epsilon}{H^{(c)}_{\mathrm{bg}}[b] + \epsilon}, \quad c \in \{V1,V2,V3\}
$$

低对比 = 主体融在背景里(典型 Wikimedia 实景照片的失败案例)。

---

## 3. 反向重建算子 $\mathcal{R}$ 标准化

### 3.1 形式定义

$$
\hat{I} = \mathcal{R}(\mathbf{f}) : \mathbb{R}^D \to \mathbb{R}^{H' \times W' \times 3}
$$

输出分辨率 $H' \times W' = 64 \times 64$(低分辨率,够人眼辨主体即可)。

### 3.2 重建管线

$\mathcal{R}$ 是 **5 步退火 + 投影回填**,不调神经网络:

**Step 1 — Color anchor**:从 V1 (RGB hist) 取主色 top-3 + V2 (HSV hist) 主色调,初始化 64×64 像素的均匀颜色采样图 $\hat{I}_0$。

**Step 2 — Layout anchor**:用 V8 主体重心和占比,在 $\hat{I}_0$ 上画一个椭圆 mask $\hat{M}_0$,内部用主色填,外部用背景色填(V9 对比给出)。

**Step 3 — Shape carving**:用 V6 (长宽比/凸包度/圆形度/对称性) 把椭圆 mask $\hat{M}_0$ 修形成 $\hat{M}_1$ — 圆形度高就更圆,长宽比 > 1 就拉长,对称性低就单边突出。

**Step 4 — Edge injection**:用 V4 (8 方向边缘直方图) + V5 (radial gradient) 在 $\hat{M}_1$ 边缘处加边界纹理,内部按 V3 LBP 主模式叠加纹理 patch。

**Step 5 — Part stamping**:用 V7 part prototypes 在主体区域内按 PartCoverage 比例盖印部件原型(例如"果柄"贴顶部,"果蒂"贴底部)。

输出 $\hat{I}_5 = \hat{I}$。

### 3.3 充分性度量

**SSIM 门槛**:

$$
\mathrm{SSIM}(I_{\mathrm{down}}, \hat{I}) = \frac{(2\mu_I \mu_{\hat{I}} + c_1)(2\sigma_{I\hat{I}} + c_2)}{(\mu_I^2 + \mu_{\hat{I}}^2 + c_1)(\sigma_I^2 + \sigma_{\hat{I}}^2 + c_2)}
$$

其中 $I_{\mathrm{down}}$ 是原图 down-sample 到 64×64。常量:

$$
\theta_{\mathrm{SSIM}} = 0.55 \quad \text{(@structural — } 0.55 \text{ 是 SSIM 文献里 "粗略可辨" 与 "无法辨认" 的经验分界)}
$$

**人眼可辨度门槛**:每张测试图独立标注 $L \in \{1,2,3,4,5\}$(1=完全看不出,5=一眼看出来),银子老师签收。

$$
L_{\min} = 3 \quad \text{(@structural — 至少 "能看出主体类别")}
$$

**通过条件**(逻辑与):

$$
G_{\mathrm{Audit}} = \mathbb{1}\left[\mathrm{SSIM}(I, \hat{I}) \geq \theta_{\mathrm{SSIM}}\right] \wedge \mathbb{1}\left[L \geq L_{\min}\right]
$$

**对 12 张用户真实图的批量门槛**:

$$
\frac{1}{N} \sum_{i=1}^{N} G_{\mathrm{Audit}}^{(i)} \geq 0.75
$$

(@scenario_tuneable — 12 张图至少 9 张通过)

---

## 4. 内心实时画面接入(关键设计 — 您今天点名的)

### 4.1 接入点(底座既有,不新增管线)

| 状态池 SA source | 已有机制 | Phase 19.0 接入 |
|---|---|---|
| `reverse_imagination` | `runtime/cognitive/fast_mapping/mapper.py:55` | 不再只返回 1 个 vocab id,而是查 prototype codebook 给 $\mathbf{f}$,渲染成 $\hat{I}$ |
| `imagined_marker_spawn` | `runtime/cognitive/endogenous/imagined_marker_spawn.py` | IMAGINED marker 触发时,从相关 percept SA 聚合 $\mathbf{f}_{\mathrm{imagined}}$,渲染 |
| `conclusion_reify` | `runtime/cognitive/deliberative/conclusion_reify.py:46` | 推理结论实化时,如果有视觉 vocab 链,合成内心画面 |
| `narrative.lag_pmi` 链 | `runtime/cognitive/narrative/lag_pmi.py:44` | 叙事链每个 vocab 节点对应一张内心画面,串成"内心实时画面流" |

### 4.2 内心画面 SA 新族(状态池侧)

新增 `family="inner_picture"`(不破坏 v14 marker_kinds cap=20,因为这是 percept family 子类,不增 marker kind):

```
StateItem(
    sa_id=f"inner_picture::{source_sa_id}::{tick}",
    family="inner_picture",
    source="reconstruction_R",
    channel_signature=("vision", "imagined", "reconstruction"),
    real_energy=confidence,           # 来自 Phase 19.2 把握感
    cognitive_pressure=1.0 - confidence,
    metadata={
        "rendered_png_bytes_sha256": <hex>,
        "rendered_png_path": <path>,        # 落盘路径 (audit-only, 非 SA id)
        "source_sa_id": <upstream>,
        "feature_vector_sha256": <hex>,     # 不入 SA id,只 audit
    }
)
```

**红线**: `inner_picture::*` SA id **不得**编码具体类别 / label / 真名 / 用户原文。`source_sa_id` 可以是 opaque hash。

### 4.3 与"叙事化想法"的协同(为 Phase 19.1 预留)

Phase 19.1 听觉版会做"内心声音流",对应数据结构:

```
StateItem(
    sa_id=f"inner_voice::{source_sa_id}::{tick}",
    family="inner_voice",
    source="reconstruction_R_audio",
    channel_signature=("audio", "imagined", "reconstruction"),
    metadata={
        "rendered_wav_bytes_sha256": <hex>,
        "narrative_chain_sa_ids": [...],     # 来自 narrative.lag_pmi
        "phonetic_estimate": <ipa-like string, audit-only>,
    }
)
```

Phase 19.0 不实现 inner_voice,只为它留接口位。

### 4.4 内心画面的"实时"含义

每 tick 调度器扫描状态池:

1. 取所有 `source in {reverse_imagination, imagined_marker_spawn, conclusion_reify}` 的 SA
2. 选出 attention_energy top-K(`inner_picture.top_k_per_tick = 3` @scenario_tuneable)
3. 调用 $\mathcal{R}(\mathbf{f})$ 合成 64×64 PNG
4. 落盘 `data/inner_picture/tick_{N}_sa_{hash}.png`
5. 在状态池注入 `inner_picture::*` SA(供下一 tick 调用 / 展示页订阅)

调度频率上限:`inner_picture.max_renders_per_second = 10` @structural — 避免硬件爆破。

---

## 5. 数学模型完整 forward pass

### 5.1 单张图前向

$$
\begin{aligned}
\mathbf{f}_I &= \mathrm{Concat}_{s=0}^{4} \mathrm{Concat}_{c=1}^{9} V_c^{(S_s)}(I) \\
\hat{I} &= \mathcal{R}(\mathbf{f}_I) \\
\mathrm{audit\_pass}(I) &= G_{\mathrm{Audit}}(I, \hat{I})
\end{aligned}
$$

### 5.2 类别原型(为 Phase 19.3 visual-only probe 用)

教师标注的训练图集合 $\{I_i^{(c)}\}_{i=1}^{n_c}$ 对每类 $c$,原型 $\mathbf{p}_c$:

$$
\mathbf{p}_c = \mathrm{Medoid}\left(\{\mathbf{f}_{I_i^{(c)}}\}\right) = \arg\min_{\mathbf{f}_j} \sum_{i} d(\mathbf{f}_i, \mathbf{f}_j)
$$

$d$ 是分块加权距离,各通道权重 $w_c$ 由 Phase 19.0 启动时**等权**($w_c = 1/9$),Phase 19.3 才允许小幅自动学习。

### 5.3 测试图打分(给 Phase 19.2 / 19.3 用)

$$
s(I, c) = \exp\left(-\lambda \cdot d(\mathbf{f}_I, \mathbf{p}_c)\right)
$$

$\lambda$ 是 Shepard's universal law of generalization 衰减率,常量 `vision_sensor.shepard_lambda = 2.0` @experimental。

---

## 6. 治理 / 红线 / Schema

### 6.1 新常量(`config/apv3_constants.yaml` 注入)

```yaml
vision_sensor:
  feature_vector_dim: 1800             # @structural - 9 channel × 5 scales × bins
  hsv_h_bins: 8                        # @structural
  hsv_s_bins: 4                        # @structural
  hsv_v_bins: 4                        # @structural
  lbp_radii: [1, 2, 3]                 # @structural
  lbp_points_per_radius: [8, 16, 24]   # @structural
  hog_orientation_bins: 8              # @structural
  radial_bins: 16                      # @structural
  slic_n_segments: 100                 # @scenario_tuneable
  part_prototype_k: 4                  # @scenario_tuneable
  reconstruction_h: 64                 # @structural
  reconstruction_w: 64                 # @structural
  ssim_threshold: 0.55                 # @structural - SSIM "粗略可辨" 经验分界
  human_legibility_min: 3              # @structural - 1-5 Likert, 至少 "能看出主体"
  batch_pass_ratio_min: 0.75           # @scenario_tuneable - 12 张图至少 9 张过
  shepard_lambda: 2.0                  # @experimental - Shepard generalization decay

inner_picture:
  top_k_per_tick: 3                    # @scenario_tuneable
  max_renders_per_second: 10           # @structural
  render_format: "png"                 # @structural
  render_path_root: "data/inner_picture"  # @structural
```

### 6.2 红线(扩展 `red_line_check_v14`)

| 红线 ID | 描述 |
|---|---|
| RL-19.0-V01 | runtime/cognitive 不得 `import cv2 / torch / tensorflow / sklearn` |
| RL-19.0-V02 | runtime/cognitive 不得调用任何在线 API(requests / urllib / http) |
| RL-19.0-V03 | `inner_picture::*` SA id 不得包含类别 label / 真名 / 用户原文 / 文件名语义 |
| RL-19.0-V04 | feature vector 不得包含 filename / entry_id / target_class |
| RL-19.0-V05 | $\mathcal{R}$ 渲染落盘路径属 audit-only,不入 SA id |
| RL-19.0-V06 | 真名("银子老师本名"/拼音)零命中(全 Phase 19 文件 grep) |
| RL-19.0-V07 | `_payload_has_private_fields` 黑名单扩展接受 `feature_vector_sha256`(audit-only,白名单) |

### 6.3 治理 schema 扩展

`runtime/cognitive/curriculum/package_schema.py`:`apv3_visual_audit_pack/v1` 新增,phase_id 前缀放宽到 `13./16./17./18./19.`。

---

## 7. Deliverable Gates(Phase 19.0 必经,15 条)

| Gate | 描述 |
|---|---|
| G-19.0-01 | 9 通道感受器全部实现且每通道有独立单测 |
| G-19.0-02 | feature_vector_dim 锁死与 `apv3_constants.yaml` 一致 |
| G-19.0-03 | $\mathcal{R}$ 反向重建管线 5 步完整 |
| G-19.0-04 | 12 张用户真实图(`真实图片测试资产/`)每张产出 $\hat{I}$ |
| G-19.0-05 | $\geq 9/12$ 通过 SSIM $\geq 0.55$ |
| G-19.0-06 | $\geq 9/12$ 通过人眼可辨度 $\geq 3$(银子老师签收 Likert 表) |
| G-19.0-07 | 内心画面通道接入 `reverse_imagination` |
| G-19.0-08 | 内心画面通道接入 `imagined_marker_spawn` |
| G-19.0-09 | 内心画面通道接入 `conclusion_reify` |
| G-19.0-10 | `inner_picture::*` SA id 不包含 label / 真名 / 用户文 |
| G-19.0-11 | 全 7 条红线零命中 |
| G-19.0-12 | 治理通过(新常量全部 @structural / @scenario_tuneable / @experimental 标注) |
| G-19.0-13 | 不依赖 cv2 / torch / tensorflow / sklearn(import 检查) |
| G-19.0-14 | 不调外部 API(grep `requests`/`urllib3`/`http.client`) |
| G-19.0-15 | 全量回归 ≥ 当前 517 + 新增 Phase 19.0 测试 |

---

## 8. 与 Codex 18.2 设计稿的关系(整改建议)

Codex 现有 [Design_APV3.0_Phase18_2_UserRealImageVisualOnlyProbe_v1_20260619.md](Design_APV3.0_Phase18_2_UserRealImageVisualOnlyProbe_v1_20260619.md) 主旨没错(visual-only probe + no-leak),**但建在贫血感受器上**会再次拿不到真泛化。处理:

1. **保留** Codex 18.2 设计稿(它对 leak gate 的设计本身完美)
2. **重命名 Phase 18.2 → Phase 19.3**(顺序后移)
3. **强制 Phase 19.3 复用 Phase 19.0 的 9 通道感受器 + Phase 19.2 的拟人把握感**
4. **不破坏** Errata_Phase18_1_AuditCorrection 的诚实降级(`visual_generalization_valid=false`),它仍然是 Phase 18.1 的最终状态

---

## 9. 边界(Phase 19.0 不做的事)

- 不接听觉感受器(那是 Phase 19.1)
- 不实现拟人把握感公式(那是 Phase 19.2)
- 不做 visual-only probe(那是 Phase 19.3)
- 不调外部预训练 CNN / SAM / DINO / CLIP / 任意 LLM
- 不持久化用户图片原文件(只在 audit 集内部使用,渲染产物落盘 audit-only)
- 不做 inner_voice(为 Phase 19.1 留接口位,不实现)
- 不做实时摄像头采集(纯静态图 audit)

---

## 10. 署名

- 原架构设计:银子老师(笔名,真名不进任何公开文件)
- 数学模型与设计稿:Claude (Anthropic) 在银子老师方向下产出
- Phase 19.0 实现:Codex 在对抗性审查通过后落地
- 风格基线与签收:银子老师

End of Phase 19.0 Design.
