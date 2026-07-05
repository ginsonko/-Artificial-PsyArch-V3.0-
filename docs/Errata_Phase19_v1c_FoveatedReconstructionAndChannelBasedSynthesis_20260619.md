# APV3.0 Phase 19 v1c Errata — Foveated Sampling, Multi-Tick Sensory Canvas, Saccadic Stitching, and Channel-Based Prototype Synthesis

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿微修订(v1c micro errata),叠加在 v1 + v1a + v1b 之上。**这是 Phase 19.0a 子阶段的设计正本**。
Trigger: 银子老师审查 Codex 已落地的 Phase 19.0 渲染,发现 sensory_sketch / prototype_imagination 都是占位级实现 — 焦点处没接近原图分辨率,周边没渐变模糊,多 tick 看久不更清楚,R_proto 完全没用 V3-V9。Codex 已确认根因是 v1 / v1a / v1b 没把"拟人视觉重建"完整数学化。
Principle: **效果第一,性能不管**(银子老师明确)。**视焦点不从压缩图采**,直接从原图采;其他区域逐层降分辨率(银子老师明确)。
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

把 v1 / v1a / v1b 没数学化的 6 块"拟人视觉重建关键效果"全部补完:

1. **Foveated 采样**:focus 区从原图取像素(分辨率 = 原图),周边逐层降分辨率(径向 dyadic 金字塔)
2. **ClarityField**:像素清晰度作为连续场,焦点处 = 1,随极坐标距离指数衰减
3. **SensoryCanvas**:多 tick 累积画布,看久了更清楚的数学模型
4. **Patch Fusion**:每 tick 新的 focus patch 按 source confidence 写入 canvas
5. **Saccadic Stitching**:视焦点移动后,多个清晰区域拼接成完整认知画面
6. **Channel-Based Prototype Synthesis**:R_proto 严格用 V3 LBP + V4 HOG + V5 radial gradient + V6 shape + V7 parts + V9 fg/bg 合成,不再只取主色画 blob

---

## 1. 根因诊断(不重复审查,直接进 fix)

| v1 / v1a / v1b 缺口 | 后果 | v1c §X |
|---|---|---|
| V0 只定义"全局 8×8 + 32×32 focus patch",没说 focus patch **从原图哪里采** | Codex 实现就直接从 resize 后的低清 RGB 取,focus 区也是低清 | §2 |
| 没有 ClarityField 连续场公式 | 渲染只能"内部清外部糊"硬边界,不拟人 | §3 |
| 没有 SensoryCanvas 多 tick 累积模型 | 单 tick 渲染,看久了也不会更清楚 | §4 |
| 没有 PatchFusion 数学(权重 / 衰减 / 冲突仲裁) | 多 tick 重叠 patch 谁覆盖谁不定 | §4.3 |
| 没有视焦点移动算法 + 拼图模型 | 不能扫视 → 拼成全图认知 | §5 |
| R_proto 没指定如何从 V3-V9 生成轮廓/纹理/部件 | Codex 只画了带主色的圆 blob | §6 |
| SSIM gate 没分场(focus 区 vs 周边) | "整体 SSIM 0.55" 可由模糊 + 颜色对就过,但 focus 区可能比周边还糊 | §7 |
| R_sketch 与 R_proto 在 v1a 双模式上没拆开渲染逻辑 | 共用一份代码就成了同质实现 | §6.4 |

---

## 2. 高分辨率 Foveated Sampling(从原图直接采)

### 2.1 核心原则(银子老师明确)

**不允许**任何"先把原图 resize 到固定分辨率,再从 resize 后取 focus patch"的实现。focus 区必须**直接从原图原始分辨率上采样**;周边区域才允许降分辨率(径向 dyadic pyramid)。

### 2.2 数学定义:Foveated Radial Pyramid

给定原图 $I \in \mathbb{R}^{H \times W \times 3}$ 和当前视焦点像素坐标 $\mathbf{c}_t = (c_x, c_y)$($t$ 是当前 tick),定义 **径向距离环**:

$$
\mathcal{R}_n = \{(x,y) : 2^{n-1} \cdot r_0 \leq \|(x,y) - \mathbf{c}_t\|_2 < 2^n \cdot r_0\}, \quad n = 0, 1, \dots, L-1
$$

其中:
- $r_0 = $ `vision_sensor.foveal_base_radius_px` = 16(@structural,原图坐标系下焦点核心半径)
- $L = $ `vision_sensor.foveal_layer_count` = 6(@structural,6 层 dyadic)
- 第 0 层是 focus core,$\|p - c\| < r_0$,$2^0 \cdot r_0 = 16$px → 半径 16px 圆形区域

每层的**有效采样分辨率**:

$$
\rho_n = \rho_0 \cdot 2^{-n}, \quad \rho_0 = \rho_{\mathrm{native}}
$$

层 0(focus core)= 原图分辨率 $\rho_{\mathrm{native}}$;层 1 = 原图 1/2;层 2 = 1/4;层 5 = 1/32。这是真正的"焦点处接近原图,周边逐层模糊"。

### 2.3 工程实现 — 多分辨率金字塔切片

```python
def build_foveated_pyramid(image_native: np.ndarray, focus_xy: tuple[int, int],
                            base_radius_px: int = 16, layer_count: int = 6
                            ) -> list[FoveatedLayer]:
    """
    层 0: 从原图直接裁剪以 focus_xy 为中心的 (2*r0) x (2*r0) 块,保持原分辨率
    层 1..L-1: 对原图先按 2^n 下采样,然后裁出该层对应的环形 ROI
    每层保留: (level_index, downsample_factor, layer_pixels, layer_mask_in_canvas)
    """
    layers = []
    H, W, _ = image_native.shape
    cx, cy = focus_xy

    # 层 0: focus core
    r0 = base_radius_px
    core = image_native[
        max(0, cy - r0): min(H, cy + r0),
        max(0, cx - r0): min(W, cx + r0)
    ].copy()  # 原分辨率,不 resize
    layers.append(FoveatedLayer(level=0, downsample=1, pixels=core, ring=None))

    # 层 1..L-1
    for n in range(1, layer_count):
        ds = 2 ** n
        # 直接从原图按 ds 下采样(box average,避免 aliasing,但是不破坏 focus 区因为 focus 区单独存在层 0)
        down = _downsample_box(image_native, ds)
        # 该层负责的极坐标环,在 down 分辨率下计算
        inner_r = (2 ** (n - 1)) * r0 // ds
        outer_r = (2 ** n) * r0 // ds
        ring_mask = _annulus_mask(down.shape[:2], (cx // ds, cy // ds), inner_r, outer_r)
        layers.append(FoveatedLayer(level=n, downsample=ds, pixels=down, ring=ring_mask))

    return layers
```

### 2.4 V0 升级:Native Foveated Pyramid

替换 v1a §3.1 的 V0 schema(原 v1a 是固定 8×8 全局 + 32×32 patch,bottlenecked)。

| Tile 类型 | 来源 | 分辨率 | 维度 |
|---|---|---|---|
| 层 0 focus core | 原图直采,$2 r_0 \times 2 r_0$ = 32×32 px,3 通道 | 原分辨率 | 3072 |
| 层 1 ring 32×32 px(下采样 1/2) | 原图 1/2 下采样后 ring 切片(取环上有效像素) | 1/2 | 3072 |
| 层 2 ring 32×32 px(下采样 1/4) | 1/4 | 1/4 | 3072 |
| 层 3 ring 32×32 px(下采样 1/8) | 1/8 | 1/8 | 3072 |
| 层 4 ring 32×32 px(下采样 1/16) | 1/16 | 1/16 | 3072 |
| 层 5 ring 32×32 px(下采样 1/32) | 1/32 | 1/32 | 3072 |
| 各层 edge tile(同尺寸 32×32 单通道 Sobel mag) | 各层 | | 6 × 1024 = 6144 |

V0 子总 = 6 × 3072 + 6144 = **24576**。比 v1a 的 4544 多很多,但银子老师明确"效果第一不管性能"。

新常量:

```yaml
vision_sensor:
  foveal_base_radius_px: 16        # @structural - 焦点核心半径(原图坐标系)
  foveal_layer_count: 6            # @structural - 6 层 dyadic 金字塔
  v0_layer_tile_px: 32             # @structural - 每层 ROI 切片尺寸
  feature_vector_dim: 27842        # @structural - 7807 - 4544 (旧 V0) + 24576 (新 V0)
```

(注:旧 7807 - 旧 V0 4544 + 新 V0 24576 = 27838,加上后续 §4 / §5 新增的 canvas state 占位,锁 **27842** 整数。具体由 Codex 实现时 assert。)

---

## 3. ClarityField — 像素清晰度连续场

### 3.1 数学定义

给定当前视焦点 $\mathbf{c}_t$,定义画布上像素 $(x,y)$ 的 **clarity score**:

$$
\boxed{
\phi_t(x, y) = \exp\left(-\frac{\|(x,y) - \mathbf{c}_t\|_2^2}{2 \sigma_{\mathrm{focus}}^2}\right) + \phi_{\min}
}
$$

其中:
- $\sigma_{\mathrm{focus}} = $ `vision_sensor.clarity_focus_sigma_px` = 24(@experimental,在 canvas 渲染分辨率下的像素)
- $\phi_{\min} = $ `vision_sensor.clarity_floor` = 0.05(@structural,周边最低保底清晰度)

性质:
- 焦点处 $\phi = 1 + 0.05 = 1.05$,clip 到 1
- 距焦点 24px → $\phi = e^{-0.5} + 0.05 \approx 0.66$
- 距焦点 48px → $\phi \approx 0.18$
- 距焦点 96px → $\phi \approx 0.05$(只剩 floor)

### 3.2 多焦点 ClarityField(同 tick 多焦点 / 累积焦点扫视)

当 tick $t$ 已经存在多个历史 fixation $\mathbf{c}_{t_1}, \dots, \mathbf{c}_{t_k}$(每个 fixation 已发生在过去的 $t_i$ tick),每个 fixation 的 clarity 贡献还要乘**时间衰减**:

$$
\phi_{t,\mathrm{multi}}(x,y) = \max_{i \in \{1,\dots,k\}} \left[ \phi_{t_i}(x,y) \cdot \exp\left(-\frac{t - t_i}{\tau_{\mathrm{memory}}}\right) \right] + \phi_{\min}
$$

其中 $\tau_{\mathrm{memory}} = $ `vision_sensor.sensory_memory_tau_ticks` = 30(@experimental,30 tick 后衰减到 1/e)。

性质:
- 多个 fixation 不会通过 sum 误饱和(用 max)
- 老 fixation 慢慢淡掉(时间衰减)
- 不同位置的多个 fixation 可拼成更广清晰区

### 3.3 ClarityField 应用 — 决定每个像素从哪层金字塔取色

给定金字塔 $\{\rho_n\}_{n=0}^{L-1}$ 和 $\phi(x,y)$,像素 $(x,y)$ 的有效层为:

$$
n^*(x,y) = \arg\min_n |\phi(x,y) - \phi_n|, \quad \phi_n = 2^{-n}
$$

也就是:
- $\phi \approx 1$(焦点)→ 取层 0(原分辨率)
- $\phi \approx 0.5$ → 取层 1(原 1/2)
- $\phi \approx 0.25$ → 取层 2
- ...

像素值:

$$
\hat{I}_{\mathrm{sketch}}(x, y) = \mathrm{Bilinear}\left(\mathrm{Pyramid}[n^*(x,y)], (x,y)\right)
$$

这就让"焦点处接近原图分辨率,周边渐变模糊"成为**数学必然**,不是渲染实现细节。

---

## 4. SensoryCanvas — 多 tick 累积模型

### 4.1 状态

```python
@dataclass
class SensoryCanvas:
    canvas_pixels: np.ndarray             # H_c × W_c × 3, float [0,1]
    canvas_clarity: np.ndarray            # H_c × W_c, float [0,1],累积 clarity
    canvas_confidence: np.ndarray         # H_c × W_c, float [0,1],source-aware confidence
    canvas_freshness: np.ndarray          # H_c × W_c, float ticks since last write
    last_fixation_xy: tuple[int, int]
    tick: int
```

canvas 分辨率 $H_c \times W_c$ 等于原图原分辨率(确保焦点处不损失;`vision_sensor.canvas_match_native = true` @structural)。

### 4.2 单 tick 更新公式

新 tick 的 fixation 是 $\mathbf{c}_t$,新 patch pixels 从 §2 的金字塔层 0(原分辨率焦点 patch)取。

对每个 canvas 像素 $(x,y)$:

```
phi_new(x,y)        = exp(-||(x,y)-c_t||^2 / (2 sigma^2)) + phi_min       # 本 tick 的 clarity
src_conf_new(x,y)   = phi_new(x,y) * Q(x)                                  # 配 §1c Q gate(v1a §4.5)
patch_value(x,y)    = pyramid_sample(x, y)                                 # §3.3 公式

# 累积融合(下方 §4.3 详)
canvas_pixels[x,y]   <-  fuse_pixels(canvas_pixels[x,y], patch_value(x,y),
                                       canvas_confidence[x,y], src_conf_new(x,y))
canvas_clarity[x,y]  <-  max(canvas_clarity[x,y] * exp(-1/tau_memory), phi_new(x,y))
canvas_confidence[x,y] <- max(canvas_confidence[x,y] * exp(-1/tau_memory), src_conf_new(x,y))
canvas_freshness[x,y] <- 0 if phi_new(x,y) >= phi_min + epsilon else canvas_freshness[x,y] + 1
```

`vision_sensor.epsilon_freshness = 0.01` @structural。

### 4.3 PatchFusion 数学(冲突仲裁)

新 patch 的可信度 $w_{\mathrm{new}} = $ src_conf_new,旧 canvas 的累积可信度 $w_{\mathrm{old}} = $ canvas_confidence。**Confidence-weighted Bayesian blending**:

$$
\boxed{
\mathrm{canvas\_pixels}'(x,y) = \frac{w_{\mathrm{old}} \cdot \mathrm{canvas\_pixels}(x,y) + w_{\mathrm{new}} \cdot \mathrm{patch\_value}(x,y)}{w_{\mathrm{old}} + w_{\mathrm{new}} + \epsilon}
}
$$

`vision_sensor.fusion_epsilon = 1e-6` @structural。

性质:
- 新 fixation 在新位置 ($w_{\mathrm{old}} \approx 0$, $w_{\mathrm{new}}$ 高) → 新像素占主导
- 重复 fixation 同位置($w_{\mathrm{old}}$ 高且接近 $w_{\mathrm{new}}$)→ 加权平均,降噪
- 老 fixation 的位置,新 tick 不看那里 → $w_{\mathrm{old}}$ 通过 §4.2 的时间衰减自然降低 → 后续若有新 fixation 经过会自动接管

### 4.4 多 tick 累积 SSIM 单调性 gate

给定同一张图连续注视 $T = 10$ tick(每 tick 视焦点小幅移动或固定),定义:

$$
\mathrm{SSIM}_t = \mathrm{SSIM}(I, \mathrm{render\_from\_canvas}(\mathrm{canvas}_t))
$$

**Gate 19.0a-MT-01(多 tick 单调)**:

$$
\mathrm{SSIM}_{t+1} \geq \mathrm{SSIM}_t - \delta_{\mathrm{tol}}, \quad \delta_{\mathrm{tol}} = 0.02
$$

允许小幅波动,但整体趋势必须上升。

**Gate 19.0a-MT-02(累积下界)**:

$$
\mathrm{SSIM}_T \geq \mathrm{SSIM}_0 + 0.15
$$

看 10 tick 后,整体 SSIM 至少提升 0.15。

### 4.5 SensoryCanvas 衰减 gate

不看图后,SensoryCanvas 必须按 $\tau_{\mathrm{memory}}$ 衰减:

$$
\mathrm{canvas\_clarity}_{t+\Delta t}(x,y) = \mathrm{canvas\_clarity}_t(x,y) \cdot \exp(-\Delta t / \tau_{\mathrm{memory}})
$$

`vision_sensor.sensory_memory_tau_ticks = 30` @experimental。即"30 tick 没看,记忆中的清晰度降到 1/e"。

---

## 5. Saccadic Stitching — 视焦点移动 → 拼图

### 5.1 视焦点移动算法

每 tick 由 attention 系统选择下个 fixation $\mathbf{c}_{t+1}$。在 Phase 19.0a 内**暂用确定性扫描**(等 Phase 19.6 active perception 升级为学习驱动):

```
def choose_next_fixation(canvas: SensoryCanvas, mask_hypotheses: list[Mask]) -> tuple[int, int]:
    """
    扫描策略 v1c (简单稳健):
    1. 找出 mask_hypotheses 综合主体掩码 (mean across hypotheses)
    2. 在主体掩码内,选 clarity 最低的像素作为下一焦点
    3. 若主体掩码外仍有 confidence < 0.1 区域,以 lambda_curiosity 概率切到该区(配 §1c.4.3 ν_context)
    """
```

`vision_sensor.fixation_inside_object_bias = 0.7` @experimental — 70% 概率落在主体内补充细节,30% 探索周边。

### 5.2 多焦点 ClarityField 已在 §3.2 给出

不同 tick 的 fixation 形成的 clarity 通过 max + 时间衰减融合,自然就是**多个清晰区域拼接成更完整画面**。

### 5.3 Stitching gate

**Gate 19.0a-Stitch-01**:连续 5 tick 在不同位置 fixation 后,canvas 上**高清区域**($\phi > 0.5$)的总覆盖面积:

$$
A_{\mathrm{clear}}(T=5) \geq 2.5 \times A_{\mathrm{clear}}(T=1)
$$

也即多 fixation 后的高清区至少是单 fixation 的 2.5 倍。

**Gate 19.0a-Stitch-02**:扫视 5 个不同位置后,$\mathrm{SSIM}(\hat{I}_{\mathrm{canvas}}, I) \geq 0.75$(主体清晰区)。

---

## 6. Channel-Based Prototype Synthesis — R_proto 严格用 V3-V9 生成

### 6.1 根因

Codex 现有 `_render_proto_image` 只画了带主色的圆 blob,**完全没用 V3 LBP / V4 HOG / V5 radial gradient / V6 shape / V7 parts / V9 fg/bg**。v1 §3.2 的"5 步管线"是 prose,没数学。v1c §6 把每一步严格数学化。

### 6.2 算子链条(R_proto 6 步,严格按通道注入)

输入:类原型特征 $\mathbf{p}_c = (\mathbf{p}_c^{V1}, \mathbf{p}_c^{V2}, \dots, \mathbf{p}_c^{V9})$
输出:64×64 RGB 内心想象图 $\hat{I}_{\mathrm{proto}}$

```
Step 1: Color anchor (用 V1 + V2)
Step 2: Shape carving (用 V6 + V8)
Step 3: Edge structure (用 V4 + V5)
Step 4: Texture overlay (用 V3 LBP codebook)
Step 5: Part stamping (用 V7 part prototypes)
Step 6: Foreground/background contrast (用 V9 KL)
```

逐步数学化:

### 6.3 Step 1 — Color Anchor

V1 RGB hist + V2 HSV hist 给出主色 top-3。对每主色 $(R_i, G_i, B_i, p_i)$:

```
canvas_color_init(x,y) =
   sum_{i=1..3} p_i * (R_i, G_i, B_i)         # 归一概率加权初值
```

初始化 $\hat{I}_{\mathrm{proto}}^{(1)}$ 全图 = 加权平均色。

### 6.4 Step 2 — Shape Carving

V6 给出长宽比 $\alpha$、凸包度 $\eta$、圆形度 $\gamma$、主轴方向 $\phi$、对称性 $\sigma$。V8 给出主体重心 $(\bar{x}, \bar{y})$、占比 $\rho_{\mathrm{obj}}$。

构造**主体掩码** $\hat{M}_{\mathrm{obj}}$ — Superformula(广义椭圆,可表达圆 / 椭 / 三角 / 倒水滴):

$$
r(\theta) = \left[\left|\frac{\cos\theta}{a}\right|^{n_2} + \left|\frac{\sin\theta}{b}\right|^{n_3}\right]^{-1/n_1}
$$

参数对应:
- $a/b = \alpha$(长宽比)
- $n_1 = 2 / \eta$(凸包度低 → $n_1$ 大 → 更"瘦"或更"碎")
- $n_2 = n_3 = 2 \gamma$(圆形度高 → 接近圆)

掩码生成:

```
\hat{M}_{\mathrm{obj}}(x,y) = 1  if  d_{\mathrm{ellipse-rotated}}(x,y; \bar{x},\bar{y},\phi,a,b,n_1,n_2,n_3) ≤ 1
                              else  0
```

掩码面积归一到原型记录的 $\rho_{\mathrm{obj}}$:对生成的 mask 做面积匹配缩放。

对称性 $\sigma$ 低 → 在主轴一侧加非对称凸起(如苹果的果蒂偏置)。

### 6.5 Step 3 — Edge Structure

V4 给出 8 方向 HOG 直方图 $\{E_k\}_{k=0}^{7}$,V5 给出径向梯度 profile $g(\rho)$。

**主体外轮廓**:沿 $\hat{M}_{\mathrm{obj}}$ 边界,按 V4 各方向比例,**采样并描画**边缘像素:

```python
boundary_pixels = trace_boundary(M_obj)
for pixel in boundary_pixels:
    local_angle = local_normal_direction(pixel)
    k = int(local_angle / (pi/4))
    intensity = E_k  # 该方向 HOG 强度
    # 在 boundary 邻域 +/-1 像素绘制对应强度的边缘
    draw_edge_stroke(canvas, pixel, k, intensity * edge_render_strength)
```

`vision_sensor.edge_render_strength = 0.7` @experimental。

**内部径向梯度**:V5 的 16 个 radial bin $g(\rho_n)$ 给出从中心到边缘的亮度/颜色变化:

```python
for rho_index in range(16):
    rho_low, rho_high = rho_index/16, (rho_index+1)/16  # 归一化半径环
    ring_mask = annulus_mask(M_obj, rho_low, rho_high)
    # 当前环的颜色 = 初始色 * (1 + g_factor * (g(rho_n) - g_mean))
    canvas[ring_mask] *= (1.0 + radial_gradient_render_strength * (g[rho_index] - g.mean()))
```

`vision_sensor.radial_gradient_render_strength = 0.4` @experimental。

### 6.6 Step 4 — Texture Overlay(用 V3 LBP codebook)

V3 LBP 3 scales × 10 uniform bins / scale → 30 维 LBP 直方图 $\{l_b\}_{b=0}^{29}$。

**离线构建 LBP codebook**:每个 LBP code $b$ 对应一个小 patch(如 $5 \times 5$ 灰度纹理图样),这个 codebook 在 Phase 19.0a 启动时由真实图片样本统计 — 每个 code 取**该 code 在样本中出现位置的局部 patch 中位数**。codebook 是离线 deterministic 表,不调外部模型。

`vision_sensor.lbp_codebook_path: "data/lbp_codebook_v1.npz"` @structural。

**纹理注入**:

```python
# 按 LBP 直方图比例,在主体区随机采样位置,贴 codebook patch
target_texel_count = int(M_obj.sum() * texture_density)
positions = random_sample_in_mask(M_obj, target_texel_count, rng_seed=trace.input_trace_hash)
for pos in positions:
    bin_idx = sample_from_distribution(l_b)  # 按直方图比例采 LBP code
    patch = lbp_codebook[bin_idx]            # 5x5 灰度 texture
    # 与当前 canvas 像素做亮度调制(保色)
    canvas[pos_y:pos_y+5, pos_x:pos_x+5] *= (1.0 + tex_strength * (patch - 0.5))
```

`vision_sensor.texture_density = 0.25` @experimental(主体 25% 像素加纹理点)
`vision_sensor.tex_strength = 0.3` @experimental
seed 由 `input_trace_hash` 决定 → **确定性**(同输入同输出,可重复 audit)

### 6.7 Step 5 — Part Stamping(用 V7 parts)

V7 给出 top-K = 4 部件原型(每个原型本身是 RGB 小 patch + 平均位置 + 覆盖率)。

```python
for part in top_k_parts:
    # 部件位置(V7 已记录相对主体的极坐标)
    stamp_x, stamp_y = part_position_in_canvas(part, M_obj, V8_layout)
    # 部件 RGB patch(从 codebook)
    stamp_patch = part_prototype_image[part.prototype_id]
    # 按部件 coverage 决定 alpha
    alpha = part.coverage * part_stamp_alpha
    canvas = alpha_blend(canvas, stamp_patch, (stamp_x, stamp_y), alpha)
```

`vision_sensor.part_stamp_alpha = 0.5` @experimental。

Part prototype codebook 与 LBP codebook 同方式离线构建,存 `data/v7_part_codebook_v1.npz`。

### 6.8 Step 6 — Foreground/Background Contrast(用 V9)

V9 KL 给出主体与背景在 V1/V2/V3 上的散度。**根据 KL 强度调整背景饱和度**:

```python
bg_mask = ~M_obj
bg_color = compute_background_color_from_V0_outer_layers()
# KL 越高,背景越被压暗/去饱和,主体相对突出
desaturation = min(1.0, V9_KL_sum * v9_desat_strength)
canvas[bg_mask] = canvas[bg_mask] * (1.0 - desaturation) + bg_color * desaturation
```

`vision_sensor.v9_desat_strength = 0.2` @experimental。

### 6.9 R_proto 输出

```python
def R_proto(prototype_features: PrototypeFeatures, target_size: int = 64) -> Image:
    canvas = step1_color_anchor(prototype_features.V1, prototype_features.V2)
    M_obj = step2_shape_carving(prototype_features.V6, prototype_features.V8)
    canvas = step3_edge_structure(canvas, M_obj, prototype_features.V4, prototype_features.V5)
    canvas = step4_texture_overlay(canvas, M_obj, prototype_features.V3)
    canvas = step5_part_stamping(canvas, M_obj, prototype_features.V7, prototype_features.V8)
    canvas = step6_fg_bg_contrast(canvas, M_obj, prototype_features.V9)
    return Image.fromarray(np.uint8(np.clip(canvas, 0, 1) * 255))
```

**这才是真正的"内心想象画面"** — 有主色、有形状、有轮廓、有纹理、有部件、有前景背景对比。

---

## 7. SSIM Gate 分场化(替换 v1 §3.3 整体 SSIM)

### 7.1 三档 SSIM

把单一 SSIM 门槛分成三个区,反映 foveated 设计意图:

| 区 | 区域定义 | 门槛 |
|---|---|---|
| Focus(焦点核心) | $\|p - c\| < r_0 = 16$ | $\mathrm{SSIM}_{\mathrm{focus}} \geq 0.75$ |
| Near(近周边) | $r_0 \leq \|p - c\| < 4 r_0$ | $\mathrm{SSIM}_{\mathrm{near}} \geq 0.50$ |
| Far(远周边) | $\|p - c\| \geq 4 r_0$ | $\mathrm{SSIM}_{\mathrm{far}} \geq 0.30$ |

**关键性质**:$\mathrm{SSIM}_{\mathrm{focus}} > \mathrm{SSIM}_{\mathrm{near}} > \mathrm{SSIM}_{\mathrm{far}}$ 必须严格成立(单调),否则说明 foveated 实现失败 — 焦点没比周边清楚。

`vision_sensor.ssim_focus_min = 0.75` @structural
`vision_sensor.ssim_near_min = 0.50` @structural
`vision_sensor.ssim_far_min = 0.30` @structural

### 7.2 Sketch 模式 SSIM 测的是 SensoryCanvas

`SSIM_focus / near / far` 都在 `SensoryCanvas` 渲染产物 $\hat{I}_{\mathrm{sketch}}$ 上算,而不是单 tick rendering。这反映"看了几 tick 后,canvas 越来越接近原图"。

### 7.3 Proto 模式不测 SSIM

Proto 是想象,**故意**不像真原图。Proto 模式只测"R_proto 输出含全部 6 步贡献"(§6.10 ablation):

| Ablation gate | 描述 |
|---|---|
| G-19.0a-Proto-Color | 移除 Step 1 → 输出全灰,失败 |
| G-19.0a-Proto-Shape | 移除 Step 2 → mask 全黑,主体不见,失败 |
| G-19.0a-Proto-Edge | 移除 Step 3 → 主体边缘不锐利(L2 边缘强度低于阈值),失败 |
| G-19.0a-Proto-Texture | 移除 Step 4 → 主体内部 LBP 直方图与原型差距 > 0.3,失败 |
| G-19.0a-Proto-Parts | 移除 Step 5 → 部件位置 occupancy = 0,失败 |
| G-19.0a-Proto-Contrast | 移除 Step 6 → V9 KL 不达原型记录值的 60%,失败 |

---

## 8. 双模式渲染入口重写(替换 Codex 当前 _render_sketch_image / _render_proto_image)

### 8.1 R_sketch 入口

```python
def R_sketch(
    canvas: SensoryCanvas,
    target_size: int = 64
) -> Image:
    """
    Sketch 模式:从 SensoryCanvas 取像素,按 ClarityField 加权渲染。
    不是直接从单 tick 焦点 patch 渲染。
    """
    # canvas.canvas_pixels (H_c x W_c x 3) → bilinear resize to target_size
    sketch = resize(canvas.canvas_pixels, (target_size, target_size))
    # 把 clarity field 也 resize,作为视觉化辅助元数据(audit 可看)
    clarity_thumb = resize(canvas.canvas_clarity, (target_size, target_size))
    return Image.fromarray(np.uint8(sketch * 255)), clarity_thumb
```

### 8.2 R_proto 入口

```python
def R_proto(
    prototype_features: PrototypeFeatures,
    target_size: int = 64
) -> Image:
    """ 见 §6.9 """
```

**关键**:两个入口**完全不共享代码**(除底层 primitives 如 alpha_blend / bilinear),从而保证 source 分离。

---

## 9. 状态池注入升级(配合 §4 SensoryCanvas)

每 tick 实际有 SensoryCanvas 写入时,注入两个 SA:

```python
StateItem(
    sa_id=f"sensory_canvas::<canvas_state_hash>::{tick}",
    family="sensory_canvas",
    source="canvas_update",
    metadata={
        "fixation_xy": (cx, cy),
        "patch_size_px": (32, 32),
        "patch_native_resolution": True,        # 必为 True,§2.1 红线
        "clarity_mean": float,
        "confidence_mean": float,
        "tick": tick,
        "ticks_since_first_view": int,
    },
)
StateItem(
    sa_id=f"inner_picture::sensory::<input_trace_hash>::{tick}",
    family="inner_picture",
    source="reconstruction_R_sketch",
    metadata={
        ...,
        "canvas_state_hash": <hex>,
        "ssim_focus": float,
        "ssim_near": float,
        "ssim_far": float,
        "render_mode": "sensory_sketch",
        # ... (continue v1b §2.2)
    },
)
```

---

## 10. 红线扩展

| RL | 描述 |
|---|---|
| RL-19v1c-F01 | focus patch **必须**从原图原分辨率裁取,不允许先 resize 后裁(代码审计 grep `image.resize` 前于 `_focus_patch`) |
| RL-19v1c-F02 | 金字塔下采样**只**用 box average,不允许 bilinear / lanczos(避免高频在 high-clarity 层缺失) |
| RL-19v1c-F03 | R_sketch / R_proto 不共享渲染主函数(只能共享底层 primitives 如 alpha_blend),代码审计 import 图 |
| RL-19v1c-F04 | LBP codebook / Part codebook 必须是离线 deterministic npz,运行时只读,不允许在线 fit / online learn |
| RL-19v1c-F05 | SensoryCanvas 衰减不允许人为 reset(除非显式 tick 跳跃 > 10 × τ_memory) |
| RL-19v1c-F06 | $\mathrm{SSIM}_{\mathrm{focus}} > \mathrm{SSIM}_{\mathrm{near}} > \mathrm{SSIM}_{\mathrm{far}}$ 单调性必为硬 gate |
| RL-19v1c-F07 | 多 tick 累积 SSIM 单调上升(允许 0.02 波动),否则失败 |

---

## 11. Phase 19.0a Deliverable Gates(20 条)

| Gate | 描述 |
|---|---|
| G-19.0a-01 | Foveated pyramid 6 层全实现,层 0 = 原图直采(代码审计) |
| G-19.0a-02 | feature_vector_dim = 27842 闭合 |
| G-19.0a-03 | ClarityField 公式实现,焦点 $\phi \approx 1$,周边 96px 处 $\phi \approx 0.05$ |
| G-19.0a-04 | SensoryCanvas H×W = 原图原分辨率 |
| G-19.0a-05 | PatchFusion confidence-weighted Bayesian blending 单测 |
| G-19.0a-06 | 10 tick 累积 SSIM 单调上升 ≥ 0.15(G-19.0a-MT-02) |
| G-19.0a-07 | 单 tick → tick+1 SSIM 至多回退 0.02 |
| G-19.0a-08 | Saccadic stitching 5 tick 后高清区面积 ≥ 2.5× 单 tick |
| G-19.0a-09 | SSIM_focus ≥ 0.75, SSIM_near ≥ 0.50, SSIM_far ≥ 0.30(12 张审计图) |
| G-19.0a-10 | SSIM_focus > SSIM_near > SSIM_far 单调(12 张全过) |
| G-19.0a-11 | R_proto 6 步全实现(代码 import 审计) |
| G-19.0a-12 | R_proto 6 个 ablation gate 全过(§7.3) |
| G-19.0a-13 | LBP / Part codebook 离线 npz 文件存在 |
| G-19.0a-14 | R_sketch / R_proto 不共享渲染主函数(代码审计) |
| G-19.0a-15 | sensory_canvas SA 注入 + inner_picture SA 含 SSIM 分场 |
| G-19.0a-16 | 红线 RL-19v1c-F01..F07 全过 |
| G-19.0a-17 | 治理通过(新增 23 个常量全部分类) |
| G-19.0a-18 | 真名零命中 |
| G-19.0a-19 | 全量回归 ≥ 当前 525 + Phase 19.0a 新测试 |
| G-19.0a-20 | 展示页(由 Codex 做)必须含:原图 / 单 tick canvas / 5 tick canvas / 10 tick canvas / R_proto 输出 — 5 列对比,小白能看出"看久了更清楚" |

---

## 12. 边界

- Phase 19.0a 不实现 active perception 学习版(确定性扫描足够,Phase 19.6 再学)
- Phase 19.0a 不接外部 superpixel / segmentation 库,SLIC / GrabCut-lite 都纯 numpy 实现
- Phase 19.0a 不调外部 diffusion / GAN / VAE / CLIP(R_proto 纯 codebook + 几何)
- LBP / Part codebook 用 Phase 17 真实照片 + Phase 18.0 干净卡片样本离线构建,不用 held-out evaluator sidecar(防 leak)
- 12 张用户图仍为内部诊断集

---

## 13. 落地次序锁死

Phase 19.0 (substrate) → **Phase 19.0a (foveated reconstruction repair)** → Phase 19.2 → 19.3a → 19.3b → 19.1 → 19.4a → 19.4b → 19.5

新插入 19.0a 子阶段。19.2 不再直接接 19.0,**必须先做 19.0a**。

---

## 14. 给 Codex 的实现优先级建议

```
Day 1: §2 Foveated sampling + V0 schema 升级 + §3 ClarityField
Day 2: §4 SensoryCanvas + PatchFusion + multi-tick gate
Day 3: §5 Saccadic stitching
Day 4: §6 R_proto 6 步(可平行做)
Day 5: §10 红线 + §11 gates + 测试 + 展示页
```

效果优先,性能不管。如果 27842 维 feature 跑得慢,可以单测/audit 时跑慢,运行时通过 fast/audit 分路保护(v1b §6 已有)。

---

## 15. 署名

- 原架构设计:银子老师(笔名)
- v1c 数学修订:Claude (Anthropic) 在银子老师明确反馈下产出 — 银子老师亲手指出"focus 区不能从压缩图采"、"清晰度要从焦点渐变"、"看久了要更清楚"、"R_proto 必须用所有通道",这三点是 v1c 的核心
- 落地:Codex 在 v1c 通过最终复核后实施

End of Phase 19 v1c Errata.
